"""File-based job queue for docking dispatch to local worker."""

import json
import logging
import os
import re
import threading
import time
import uuid

logger = logging.getLogger(__name__)

# Every job id that reaches this module can come straight from a client URL
# (status/cancel/structure routes). Ids we mint are uuid4().hex[:12], but path
# safety must not depend on the caller: reject anything that is not a plain
# token before it reaches os.path.join. (Flask routing already 404s '%2F'-
# style separators — verified against both werkzeug and gunicorn — so this is
# defense in depth against traversal, NUL bytes and oversized ids.)
_JOB_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def valid_job_id(job_id) -> bool:
    """True when job_id is safe to embed in queue file paths."""
    return isinstance(job_id, str) and bool(_JOB_ID_RE.match(job_id))


def _atomic_dump(obj, path: str):
    """Write JSON via temp file + os.replace — readers never see a half dump."""
    tmp = f"{path}.tmp{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(obj, f)
    os.replace(tmp, path)

QUEUE_DIR = os.environ.get("DOCKING_QUEUE_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docking_queue"))
PENDING_DIR = os.path.join(QUEUE_DIR, "pending")
RUNNING_DIR = os.path.join(QUEUE_DIR, "running")
COMPLETE_DIR = os.path.join(QUEUE_DIR, "complete")
FAILED_DIR = os.path.join(QUEUE_DIR, "failed")

_lock = threading.Lock()

def _ensure_dirs():
    for d in (PENDING_DIR, RUNNING_DIR, COMPLETE_DIR, FAILED_DIR):
        os.makedirs(d, exist_ok=True)

def create_job(sequence: str, ligand_smiles_list: list, top_n: int = 50, pdb_content: str = "", box: dict | None = None) -> str:
    _ensure_dirs()
    job_id = uuid.uuid4().hex[:12]
    job = {
        "job_id": job_id,
        "status": "pending",
        "type": "docking",
        "sequence": sequence,
        "ligand_smiles_list": ligand_smiles_list,
        "top_n": top_n,
        "pdb_content": pdb_content,  # Optional: uploaded PDB file (skips ESMFold)
        "box": box,  # Optional: search-box override (manual/residue/blind)
        "created_at": time.time(),
        "updated_at": time.time(),
        "result": None,
        "error": None,
    }
    with _lock:
        path = os.path.join(PENDING_DIR, f"{job_id}.json")
        _atomic_dump(job, path)
    logger.info("Docking job %s created (%d ligands)", job_id, len(ligand_smiles_list))
    try:
        from primerforge.docking_db import save_job as db_save
        db_save(job_id, sequence, ligand_smiles_list, top_n)
    except Exception:
        pass
    return job_id

def get_job(job_id: str) -> dict | None:
    if not valid_job_id(job_id):
        return None
    for directory in (PENDING_DIR, RUNNING_DIR, COMPLETE_DIR, FAILED_DIR):
        path = os.path.join(directory, f"{job_id}.json")
        if os.path.exists(path):
            try:
                with open(path) as f:
                    return json.load(f)
            except (OSError, ValueError) as e:
                # Truncated/corrupt record (writer crashed mid-dump): report it
                # as missing so the status route 404s and the UI clears its
                # stored run, instead of raising on every poll for the client's
                # full ~17-minute attempt budget.
                logger.error("Unreadable docking job file %s: %s", path, e)
                return None
    return None

def claim_job(job_id: str) -> bool:
    if not valid_job_id(job_id):
        return False
    _ensure_dirs()
    with _lock:
        src = os.path.join(PENDING_DIR, f"{job_id}.json")
        if not os.path.exists(src):
            return False
        dst = os.path.join(RUNNING_DIR, f"{job_id}.json")
        try:
            with open(src) as f:
                job = json.load(f)
        except FileNotFoundError:
            # Cancelled (or cleaned) between exists() and read.
            return False
        except (OSError, ValueError) as e:
            # Corrupt pending record — unreadable, so drop it instead of
            # re-claiming (and failing) it every poll cycle forever.
            logger.error("Dropping corrupt pending docking job %s: %s", src, e)
            _remove_quiet(src)
            return False
        job["status"] = "running"
        job["updated_at"] = time.time()
        _atomic_dump(job, dst)
        try:
            os.remove(src)
        except FileNotFoundError:
            # cancel_job() failed this job while we were claiming it — undo
            # our running copy so its "Stopped by user." record wins.
            try:
                os.remove(dst)
            except OSError:
                pass
            return False
    return True

def complete_job(job_id: str, result: dict, error: str = None) -> bool:
    if not valid_job_id(job_id):
        return False
    _ensure_dirs()
    with _lock:
        src = os.path.join(RUNNING_DIR, f"{job_id}.json")
        if not os.path.exists(src):
            return False
        dst_dir = FAILED_DIR if error else COMPLETE_DIR
        dst = os.path.join(dst_dir, f"{job_id}.json")
        try:
            with open(src) as f:
                job = json.load(f)
        except (OSError, ValueError) as e:
            # Corrupt running record — remove it so the job can't loop through
            # stale-release forever; status then 404s and the UI clears.
            logger.error("Dropping corrupt running docking job %s: %s", src, e)
            _remove_quiet(src)
            return False
        job["status"] = "failed" if error else "completed"
        job["updated_at"] = time.time()
        job["result"] = result
        job["error"] = error
        _atomic_dump(job, dst)
        os.remove(src)
    try:
        from primerforge.docking_db import complete_job as db_complete
        db_complete(job_id, result, error)
    except Exception:
        pass
    return True

def list_pending_jobs() -> list[dict]:
    _ensure_dirs()
    jobs = []
    for fname in os.listdir(PENDING_DIR):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(PENDING_DIR, fname)) as f:
                    jobs.append(json.load(f))
            except Exception as e: logger.debug("Suppressed exception: %s", e)
    return jobs

def list_running_jobs() -> list[dict]:
    _ensure_dirs()
    jobs = []
    for fname in os.listdir(RUNNING_DIR):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(RUNNING_DIR, fname)) as f:
                    jobs.append(json.load(f))
            except Exception as e: logger.debug("Suppressed exception: %s", e)
    return jobs

def release_stale_jobs(max_age_minutes: float = 10.0):
    """Move running jobs older than max_age_minutes back to pending.

    This handles the case where a worker crashes mid-job, leaving the
    job stuck in 'running' state forever. The next polling cycle will
    pick it up again.
    """
    _ensure_dirs()
    now = time.time()
    cutoff = now - max_age_minutes * 60
    released = 0
    for fname in os.listdir(RUNNING_DIR):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(RUNNING_DIR, fname)
        try:
            mtime = os.path.getmtime(path)
            if mtime < cutoff:
                try:
                    with open(path) as f:
                        job = json.load(f)
                except (OSError, ValueError) as e:
                    # Corrupt running record: drop it (status 404s → the UI
                    # clears) instead of re-reading the same garbage each cycle.
                    logger.error("Dropping corrupt running docking job %s: %s", path, e)
                    os.remove(path)
                    continue
                job["status"] = "pending"
                job["updated_at"] = now
                dst = os.path.join(PENDING_DIR, fname)
                _atomic_dump(job, dst)
                os.remove(path)
                released += 1
                logger.info("Released stale job %s back to pending", job.get("job_id"))
        except Exception as e: logger.debug("Suppressed exception: %s", e)
    if released:
        logger.info("Released %d stale running job(s) back to pending", released)
    return released


# ── User-initiated stop ("Stop run") ───────────────────────────────────────

def _cancel_marker_path(job_id: str) -> str:
    """Filesystem flag written by cancel_job() for a running job.

    Survives worker crashes/restarts: if the queue releases the job back to
    pending, _process_job()'s pre-spawn check sees the marker and fails the
    job as stopped instead of re-running it.
    """
    return os.path.join(RUNNING_DIR, f"{job_id}.cancel")


def _remove_quiet(path: str):
    try:
        os.remove(path)
    except OSError:
        pass


def cancel_job(job_id: str) -> str:
    """Stop a docking run on user request.

    Returns one of:
      'not_found' — no job with this id anywhere
      'cancelled' — still pending: failed immediately, never runs
      'stopping'  — running: marker written; the queue's wait loop kills the
                    worker process tree within ~1s and fails the job
      'finished'  — already completed/failed; nothing to stop
    """
    if not valid_job_id(job_id):
        return "not_found"
    _ensure_dirs()
    pending = os.path.join(PENDING_DIR, f"{job_id}.json")
    running = os.path.join(RUNNING_DIR, f"{job_id}.json")
    with _lock:
        # ── pending: atomically-as-possible win over claim_job ──────────
        if os.path.exists(pending):
            try:
                with open(pending) as f:
                    job = json.load(f)
            except FileNotFoundError:
                job = None  # claimed by the worker while we read
            except (OSError, ValueError) as e:
                # Unreadable record: drop it (claim_job would too) and let the
                # caller see 'not_found' instead of a 500.
                logger.error("Dropping corrupt pending docking job %s: %s", pending, e)
                _remove_quiet(pending)
                job = None
            if job is not None:
                failed_dst = os.path.join(FAILED_DIR, f"{job_id}.json")
                job["status"] = "failed"
                job["error"] = "Stopped by user."
                job["updated_at"] = time.time()
                _atomic_dump(job, failed_dst)
                try:
                    os.remove(pending)
                except FileNotFoundError:
                    # Worker claimed it first — take its running file instead.
                    _remove_quiet(failed_dst)
                else:
                    _remove_quiet(_cancel_marker_path(job_id))
                    logger.info("Job %s cancelled while pending", job_id)
                    try:
                        from primerforge.docking_db import complete_job as db_complete
                        db_complete(job_id, None, "Stopped by user.")
                    except Exception:
                        pass
                    return "cancelled"

        # ── running: flag it; the queue wait-loop does the kill ─────────
        if os.path.exists(running):
            marker = _cancel_marker_path(job_id)
            with open(marker, "w"):
                pass  # touch
            logger.info("Job %s stop requested (running)", job_id)
            return "stopping"

    for d in (COMPLETE_DIR, FAILED_DIR):
        if os.path.exists(os.path.join(d, f"{job_id}.json")):
            return "finished"
    return "not_found"

# ── Local worker thread ──────────────────────────────────────────────────
# Processes pending docking jobs directly on this server instead of waiting
# for an external Azure worker. Spawned by start_local_worker().
_LOCAL_WORKER_RUNNING = False

# Stage-3 GNINA budget terms for _job_timeout_seconds. Mirrored from
# consensus_pipeline (importing that module here would drag rdkit into every
# queue import) — tests/test_gnina_phase1.py asserts the two stay in sync.
GNINA_REFINE_TOP_K = 10
GNINA_SECONDS_PER_LIGAND = 45

def _job_timeout_seconds(sequence: str, n_ligands: int, has_pdb: bool) -> int:
    """Dynamic subprocess budget (was a flat 300s that killed long jobs).

    Base covers worker cold start + receptor prep + queue jitter; +8s per
    ligand covers obabel prep + Vina screening (two run concurrently);
    sequence mode adds 0.25s/residue for the web-API fold (≤400 aa → ≤100s;
    a 400-aa fold measured ~27s); +45s per GNINA refine covers stage 3's CNN
    re-score (top-K=10, single-model crossdock measured 37s/ligand under
    x86_64 emulation on the official v1.1 binary → ~15-25s native expected;
    45s is the conservative first estimate). GNINA_SECONDS_PER_LIGAND is
    recorded per candidate as `gnina_time` in results for tuning against
    real prod runs. PDB-upload mode skips folding entirely.
    Clamped to [300, 900] — the frontend polls ~1000s, so every job fits
    inside the UI budget. Small runs (≤10 ligands) screen at exhaustiveness
    8 instead of 2 (see consensus_pipeline._stage2_exhaustiveness) — the
    300s base + GNINA term absorb the deeper screening, and n≥10 is already
    clamped at the 900s ceiling.
    """
    n = max(0, int(n_ligands))
    seq_cost = 0 if has_pdb else int(0.25 * len(sequence or ""))
    gnina_cost = GNINA_SECONDS_PER_LIGAND * min(GNINA_REFINE_TOP_K, n)
    return int(max(300, min(300 + 8 * n + seq_cost + gnina_cost, 900)))


# Cancel/timeout check cadence inside _process_job's wait loop.
# Module-level so tests can shrink it (real runs poll once per second).
_WAIT_POLL_SECONDS = 1.0


def _kill_process_tree(proc):
    """SIGKILL the worker AND its descendants (vina/obabel/esmfold children).

    The worker is spawned with start_new_session=True, so its process group is
    its own pid — killpg can never reach the queue/gunicorn group. Falls back
    to killing just the worker if the group is already gone.
    """
    import signal
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.kill()
        except Exception:
            pass


def _process_job(job: dict):
    """Run the consensus pipeline in a SEPARATE OS process.

    If the pipeline segfaults or OOMs, only the subprocess dies — gunicorn survives.
    The subprocess writes results directly to disk (no primerforge imports for I/O).

    Waits with a 1s poll loop instead of subprocess.run(): each tick checks the
    user "Stop run" marker (running/<id>.cancel) and the dynamic budget, and
    kills the worker's whole process tree (vina/obabel children included — the
    worker gets its own session via start_new_session=True).
    """
    import subprocess
    import sys as _sys

    job_id = job["job_id"]
    sequence = job["sequence"]
    smiles_list = (job.get("ligand_smiles_list") or [])
    top_n = job.get("top_n", 50)
    pdb_content = job.get("pdb_content", "")
    box = job.get("box")  # optional search-box override (advanced panel)

    budget = _job_timeout_seconds(sequence, len(smiles_list), bool(pdb_content))
    logger.info("Spawning subprocess for job %s (%d ligands, %d aa, budget %ds)",
                job_id, len(smiles_list), len(sequence), budget)

    cancel_path = _cancel_marker_path(job_id)

    # Re-claimed after a stale release + stop: die before spawning anything.
    if os.path.exists(cancel_path):
        _remove_quiet(cancel_path)
        if complete_job(job_id, None, "Stopped by user."):
            logger.info("Job %s was stopped before it started", job_id)
        return

    job_input = json.dumps({
        "job_id": job_id,
        "sequence": sequence,
        "ligand_smiles_list": smiles_list,
        "top_n": top_n,
        "pdb_content": pdb_content,
        "box": box,
    })

    worker_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docking_worker.py")

    # Job JSON via temp file, not stdin: payloads can carry a 5MB PDB, which
    # would block on the 64KB pipe across communicate(timeout=…) retries.
    input_path = os.path.join(RUNNING_DIR, f"{job_id}.input")
    with open(input_path, "w") as f:
        f.write(job_input)

    start = time.time()
    try:
        proc = subprocess.Popen(
            [_sys.executable, worker_script, "--job-file", input_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
            start_new_session=True,  # own process group → killpg can't hit ours
        )
    except Exception as e:
        logger.error("Failed to spawn worker for job %s: %s", job_id, e)
        _remove_quiet(input_path)
        complete_job(job_id, None, f"Failed to start docking worker: {e}")
        return

    cancelled = False
    timed_out = False
    while True:
        try:
            _, err = proc.communicate(timeout=_WAIT_POLL_SECONDS)
            break
        except subprocess.TimeoutExpired:
            if os.path.exists(cancel_path):
                cancelled = True
                _kill_process_tree(proc)
                _, err = proc.communicate()
                break
            if time.time() - start >= budget:
                timed_out = True
                _kill_process_tree(proc)
                _, err = proc.communicate()
                break

    # Marker read AFTER the loop: a stop that raced a normal completion still
    # resolves to the stop outcome if the worker died non-zero.
    marker_present = os.path.exists(cancel_path)
    _remove_quiet(cancel_path)
    _remove_quiet(input_path)

    if cancelled:
        if complete_job(job_id, None, "Stopped by user."):
            logger.info("Job %s stopped by user request (worker process tree killed)", job_id)
        else:
            logger.info("Job %s finished before the stop request took effect", job_id)
        return

    if timed_out:
        # The job never wrote a result — fail it with actionable guidance
        # instead of "Internal worker error".
        logger.error("Job %s exceeded the %ds budget — failed", job_id, budget)
        complete_job(job_id, None,
                     f"Docking timed out after {budget // 60} minutes. "
                     "Try fewer ligands (≤100) or a shorter sequence (≤400 aa).")
        return

    # Worker writes results to disk directly. Just log what happened.
    if proc.returncode != 0:
        # The worker moves the job file itself; if it never got that far
        # (segfault/OS OOM-kill), fail it HERE — otherwise the job would sit
        # in running/ and be re-claimed every 5 minutes forever.
        logger.error("Worker failed (rc=%d): %s", proc.returncode, (err or "")[-500:])
        if marker_present:
            complete_job(job_id, None, "Stopped by user.")
            return
        tail = (err or "").strip().splitlines()[-1][:200] if (err or "").strip() else ""
        complete_job(job_id, None,
                     f"Docking worker crashed (exit {proc.returncode}). {tail}".strip())
    else:
        logger.info("Worker completed job %s", job_id)
        logger.debug("Worker stderr: %s", (err or "")[-200:])


def _local_worker_loop(interval: float = 5.0):
    """Background loop: poll pending, claim, process.

    CRITICAL: This runs inside gunicorn. Any unhandled exception here
    can kill the gunicorn worker. Every operation is wrapped in try/except.
    """
    global _LOCAL_WORKER_RUNNING
    logger.info("Local docking worker started (poll interval: %gs)", interval)
    _cleanup_counter = 0
    while _LOCAL_WORKER_RUNNING:
        try:
            _cleanup_counter += 1
            if _cleanup_counter >= 60:
                _cleanup_counter = 0
                try:
                    cleanup_old_jobs(2.0)
                except Exception:
                    pass

            try:
                release_stale_jobs(max_age_minutes=5.0)
            except Exception:
                pass

            try:
                pending = list_pending_jobs()
            except Exception:
                pending = []

            for job in pending:
                if not _LOCAL_WORKER_RUNNING:
                    break
                job_id = job.get("job_id", "")
                try:
                    if claim_job(job_id):
                        _process_job(job)
                except Exception as e:
                    logger.error("Worker failed on job %s: %s", job_id, e)
                    try:
                        complete_job(job_id, None, "Internal worker error")
                    except Exception:
                        pass
        except Exception as e:
            logger.debug("Local worker cycle error: %s", e)
        time.sleep(interval)
    logger.info("Local docking worker stopped")


def start_local_worker(interval: float = 5.0):
    """Start the local worker thread as a daemon."""
    global _LOCAL_WORKER_RUNNING
    if _LOCAL_WORKER_RUNNING:
        logger.info("Local worker already running")
        return
    _LOCAL_WORKER_RUNNING = True
    t = threading.Thread(target=_local_worker_loop, args=(interval,), daemon=True)
    t.start()
    logger.info("Local worker thread started")


def stop_local_worker():
    """Signal the local worker to stop."""
    global _LOCAL_WORKER_RUNNING
    _LOCAL_WORKER_RUNNING = False
    logger.info("Local worker stop signal sent")


def cleanup_old_jobs(max_age_hours: float = 1.0):
    """Remove completed/failed jobs older than max_age_hours to prevent disk bloat."""
    _ensure_dirs()
    now = time.time()
    cutoff = now - max_age_hours * 3600
    removed = 0
    for directory in (COMPLETE_DIR, FAILED_DIR):
        for fname in os.listdir(directory):
            if not (fname.endswith(".json") or ".json.tmp" in fname):
                continue
            path = os.path.join(directory, fname)
            try:
                mtime = os.path.getmtime(path)
                if mtime < cutoff:
                    os.remove(path)
                    removed += 1
            except Exception as e: logger.debug("Suppressed exception: %s", e)
    # Orphaned stop markers / worker input files (queue died mid-flight).
    # Active ones are minutes old — never swept against the hour-scale cutoff.
    for fname in os.listdir(RUNNING_DIR):
        if not (fname.endswith(".cancel") or fname.endswith(".input")):
            continue
        path = os.path.join(RUNNING_DIR, fname)
        try:
            if os.path.getmtime(path) < cutoff:
                os.remove(path)
                removed += 1
        except Exception as e: logger.debug("Suppressed exception: %s", e)
    if removed:
        logger.info("Cleaned up %d old docking job(s) (>%sh old)", removed, max_age_hours)

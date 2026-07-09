"""File-based job queue for docking dispatch to Azure worker."""

import json
import os
import time
import uuid
import threading
import asyncio
import logging

logger = logging.getLogger(__name__)

QUEUE_DIR = os.environ.get("DOCKING_QUEUE_DIR", "/tmp/docking_queue")
PENDING_DIR = os.path.join(QUEUE_DIR, "pending")
RUNNING_DIR = os.path.join(QUEUE_DIR, "running")
COMPLETE_DIR = os.path.join(QUEUE_DIR, "complete")
FAILED_DIR = os.path.join(QUEUE_DIR, "failed")

_lock = threading.Lock()

def _ensure_dirs():
    for d in (PENDING_DIR, RUNNING_DIR, COMPLETE_DIR, FAILED_DIR):
        os.makedirs(d, exist_ok=True)

def create_job(sequence: str, ligand_smiles_list: list, top_n: int = 50) -> str:
    _ensure_dirs()
    job_id = uuid.uuid4().hex[:12]
    job = {
        "job_id": job_id,
        "status": "pending",
        "type": "docking",
        "sequence": sequence,
        "ligand_smiles_list": ligand_smiles_list,
        "top_n": top_n,
        "created_at": time.time(),
        "updated_at": time.time(),
        "result": None,
        "error": None,
    }
    with _lock:
        path = os.path.join(PENDING_DIR, f"{job_id}.json")
        with open(path, "w") as f:
            json.dump(job, f)
    logger.info("Docking job %s created (%d ligands)", job_id, len(ligand_smiles_list))
    return job_id

def get_job(job_id: str) -> dict | None:
    for directory in (PENDING_DIR, RUNNING_DIR, COMPLETE_DIR, FAILED_DIR):
        path = os.path.join(directory, f"{job_id}.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    return None

def claim_job(job_id: str) -> bool:
    _ensure_dirs()
    with _lock:
        src = os.path.join(PENDING_DIR, f"{job_id}.json")
        if not os.path.exists(src):
            return False
        dst = os.path.join(RUNNING_DIR, f"{job_id}.json")
        with open(src) as f:
            job = json.load(f)
        job["status"] = "running"
        job["updated_at"] = time.time()
        with open(dst, "w") as f:
            json.dump(job, f)
        os.remove(src)
    return True

def complete_job(job_id: str, result: dict, error: str = None) -> bool:
    _ensure_dirs()
    with _lock:
        src = os.path.join(RUNNING_DIR, f"{job_id}.json")
        if not os.path.exists(src):
            return False
        dst_dir = FAILED_DIR if error else COMPLETE_DIR
        dst = os.path.join(dst_dir, f"{job_id}.json")
        with open(src) as f:
            job = json.load(f)
        job["status"] = "failed" if error else "completed"
        job["updated_at"] = time.time()
        job["result"] = result
        job["error"] = error
        with open(dst, "w") as f:
            json.dump(job, f)
        os.remove(src)
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
                with open(path) as f:
                    job = json.load(f)
                job["status"] = "pending"
                job["updated_at"] = now
                dst = os.path.join(PENDING_DIR, fname)
                with open(dst, "w") as f:
                    json.dump(job, f)
                os.remove(path)
                released += 1
                logger.info("Released stale job %s back to pending", job.get("job_id"))
        except Exception as e: logger.debug("Suppressed exception: %s", e)
    if released:
        logger.info("Released %d stale running job(s) back to pending", released)
    return released

# ── Local worker thread ──────────────────────────────────────────────────
# Processes pending docking jobs directly on this server instead of waiting
# for an external Azure worker. Spawned by start_local_worker().
_LOCAL_WORKER_RUNNING = False

def _process_job(job: dict):
    """Run the consensus pipeline for a single job and save result."""
    job_id = job["job_id"]
    sequence = job["sequence"]
    smiles_list = job.get("ligand_smiles_list") or []
    top_n = job.get("top_n", 50)

    logger.info("Local worker processing job %s (%d ligands)", job_id, len(smiles_list))

    try:
        from primerforge.pipelines.consensus_pipeline import run_consensus_pipeline
        result = asyncio.run(run_consensus_pipeline(sequence, smiles_list, top_n))
        if result.get("status") == "success":
            complete_job(job_id, result)
            logger.info("Local worker completed job %s", job_id)
        else:
            error = result.get("message", "Pipeline failed")
            complete_job(job_id, None, error)
            logger.error("Local worker failed job %s: %s", job_id, error)
    except Exception as e:
        complete_job(job_id, None, str(e))
        logger.error("Local worker exception on job %s: %s", job_id, e)


def _local_worker_loop(interval: float = 5.0):
    """Background loop: poll pending, claim, process."""
    global _LOCAL_WORKER_RUNNING
    logger.info("Local docking worker started (poll interval: %gs)", interval)
    while _LOCAL_WORKER_RUNNING:
        try:
            release_stale_jobs(max_age_minutes=2.0)
            pending = list_pending_jobs()
            for job in pending:
                if not _LOCAL_WORKER_RUNNING:
                    break
                job_id = job["job_id"]
                if claim_job(job_id):
                    _process_job(job)
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
            if not fname.endswith(".json"):
                continue
            path = os.path.join(directory, fname)
            try:
                mtime = os.path.getmtime(path)
                if mtime < cutoff:
                    os.remove(path)
                    removed += 1
            except Exception as e: logger.debug("Suppressed exception: %s", e)
    if removed:
        logger.info("Cleaned up %d old docking job(s) (>%sh old)", removed, max_age_hours)

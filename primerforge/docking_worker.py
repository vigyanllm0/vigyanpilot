#!/usr/bin/env python3
"""
Standalone docking worker — runs in a SEPARATE OS process from gunicorn.
If this crashes (OOM, segfault), gunicorn survives.

Called by docking_queue.py via subprocess.Popen.
Reads job JSON from a --job-file path (or stdin), writes result to job files on disk.
DOES NOT import primerforge.* — uses raw file I/O to avoid import chain.
"""

import asyncio
import json
import os
import resource
import sys
import threading
import time

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Hard memory limit: 600MB. Above this, Python raises MemoryError (catchable)
# instead of the OS sending SIGKILL (kills gunicorn).
try:
    resource.setrlimit(resource.RLIMIT_AS, (600 * 1024 * 1024, 600 * 1024 * 1024))
except Exception:
    pass

# Log to stderr for debugging (captured by subprocess.run)
def log(msg):
    print(f"[docking-worker] {msg}", file=sys.stderr, flush=True)


def _queue_base() -> str:
    """Queue directory (env override matches docking_queue.py exactly)."""
    return os.environ.get("DOCKING_QUEUE_DIR") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docking_queue")


def _start_heartbeat(job_id: str, interval: float = 20.0):
    """Touch running/<job>.json every `interval` seconds while this worker lives.

    release_stale_jobs() uses the RUNNING file's mtime as its ONLY liveness
    signal (the status endpoint never rewrites the file). Without this beat,
    any job running longer than the stale threshold (5 min) would be re-queued
    and executed a second time alongside the first.
    """
    path = os.path.join(_queue_base(), "running", f"{job_id}.json")
    stop = threading.Event()

    def _beat():
        while not stop.wait(interval):
            try:
                os.utime(path, None)
            except OSError:
                pass  # job already moved to complete/failed — nothing to touch

    threading.Thread(target=_beat, daemon=True).start()
    return stop


def write_result(job_id, result=None, error=None):
    """Write result directly to disk — NO primerforge imports."""
    base = _queue_base()
    running = os.path.join(base, "running", f"{job_id}.json")
    complete = os.path.join(base, "complete", f"{job_id}.json")
    failed = os.path.join(base, "failed", f"{job_id}.json")

    if not os.path.exists(running):
        log(f"WARNING: job {job_id} not in running/ — nothing to move")
        return

    with open(running) as f:
        job = json.load(f)

    job["status"] = "failed" if error else "completed"
    job["updated_at"] = time.time()
    job["result"] = result
    job["error"] = error

    dst = failed if error else complete
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    # Atomic write: readers (status polls, get_job) must never see the
    # truncated empty file between open("w") and json.dump() — an empty read
    # is reported as a 404 and makes the UI abandon a run that is actually
    # finishing. Same tmp+os.replace pattern as docking_queue._atomic_dump
    # (kept import-free by design).
    tmp = f"{dst}.tmp{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(job, f)
    os.replace(tmp, dst)
    os.remove(running)
    log(f"Job {job_id} → {'failed' if error else 'complete'}")


def main():
    log("Worker process started")
    if len(sys.argv) >= 3 and sys.argv[1] == "--job-file":
        with open(sys.argv[2]) as f:
            job = json.load(f)
    else:
        job = json.loads(sys.stdin.read())
    job_id = job["job_id"]
    sequence = job["sequence"]
    smiles_list = (job.get("ligand_smiles_list") or [])
    top_n = job.get("top_n", 50)
    pdb_content = job.get("pdb_content", "")

    log(f"Job {job_id}: {len(sequence)}aa, {len(smiles_list)} ligands")

    # Keep running/<job>.json mtime fresh for release_stale_jobs — without
    # it, any job longer than the 5-min stale threshold would be re-queued
    # and run twice. Stopped in finally so a crash stops the beat.
    heartbeat_stop = _start_heartbeat(job_id)

    try:
        # Try to import the pipeline (heavy — may OOM on small instances)
        try:
            from primerforge.pipelines.consensus_pipeline import run_consensus_pipeline
            log("Pipeline imported OK")
        except MemoryError:
            write_result(job_id, error="Server cannot load docking engine — not enough RAM.")
            return
        except ImportError as e:
            write_result(job_id, error=f"Docking engine not available: {e}")
            return
        except Exception as e:
            write_result(job_id, error=f"Failed to load docking engine: {str(e)[:300]}")
            return

        # Run the pipeline
        try:
            log("Starting pipeline...")
            result = asyncio.run(run_consensus_pipeline(sequence, smiles_list, top_n, pdb_content=pdb_content))
            log(f"Pipeline finished: status={result.get('status', 'unknown')}")
            if result.get("status") == "success":
                write_result(job_id, result=result)
            else:
                write_result(job_id, error=result.get("message", "Pipeline failed"))
        except MemoryError:
            write_result(job_id, error=(
                "Docking ran out of memory on the server. Try fewer ligands (≤100) "
                "and a shorter sequence (≤400 aa), or upload a smaller PDB."))
        except Exception as e:
            log(f"Pipeline error: {e}")
            write_result(job_id, error=f"Docking error: {str(e)[:300]}")
    finally:
        heartbeat_stop.set()
        log("Worker process exiting")


if __name__ == "__main__":
    main()

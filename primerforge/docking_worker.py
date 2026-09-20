#!/usr/bin/env python3
"""
Standalone docking worker — runs in a SEPARATE OS process from gunicorn.
If this crashes (OOM, segfault), gunicorn survives.

Called by docking_queue.py via subprocess.Popen.
Reads job JSON from stdin, writes result to job files on disk.
DOES NOT import primerforge.* — uses raw file I/O to avoid import chain.
"""

import asyncio
import json
import os
import sys
import resource
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


def write_result(job_id, result=None, error=None):
    """Write result directly to disk — NO primerforge imports."""
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docking_queue")
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
    with open(dst, "w") as f:
        json.dump(job, f)
    os.remove(running)
    log(f"Job {job_id} → {'failed' if error else 'complete'}")


def main():
    log("Worker process started")
    raw = sys.stdin.read()
    job = json.loads(raw)
    job_id = job["job_id"]
    sequence = job["sequence"]
    smiles_list = (job.get("ligand_smiles_list") or [])[:5]
    top_n = job.get("top_n", 50)
    pdb_content = job.get("pdb_content", "")

    log(f"Job {job_id}: {len(sequence)}aa, {len(smiles_list)} ligands")

    # Try to import the pipeline (heavy — may OOM on small instances)
    try:
        from primerforge.pipelines.consensus_pipeline import run_consensus_pipeline
        log("Pipeline imported OK")
    except MemoryError:
        write_result(job_id, error="Server cannot load docking engine — not enough RAM (need GPU instance).")
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
        write_result(job_id, error="Docking ran out of memory. Try shorter sequence (< 200 aa) and fewer ligands (< 3).")
    except Exception as e:
        log(f"Pipeline error: {e}")
        write_result(job_id, error=f"Docking error: {str(e)[:300]}")

    log("Worker process exiting")


if __name__ == "__main__":
    main()

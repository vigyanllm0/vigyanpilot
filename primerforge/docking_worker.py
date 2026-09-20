#!/usr/bin/env python3
"""
Standalone docking worker — runs in a SEPARATE OS process from gunicorn.
If this crashes (OOM, segfault), gunicorn survives.

Called by docking_queue.py via subprocess.Popen.
Reads job JSON from stdin, writes result to job files.
"""

import json
import os
import sys
import resource

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# HARD memory limit: kill ourselves before we OOM the host
# t3.micro has 908MB total; gunicorn needs ~200MB; leave 600MB for us
try:
    # RLIMIT_AS: virtual memory limit in bytes (600MB)
    resource.setrlimit(resource.RLIMIT_AS, (600 * 1024 * 1024, 600 * 1024 * 1024))
except Exception:
    pass  # May fail on some systems


def main():
    job = json.loads(sys.stdin.read())
    job_id = job["job_id"]
    sequence = job["sequence"]
    smiles_list = (job.get("ligand_smiles_list") or [])[:5]
    top_n = job.get("top_n", 50)
    pdb_content = job.get("pdb_content", "")

    # Import AFTER setting memory limit so we get MemoryError instead of SIGKILL
    try:
        import asyncio
        from primerforge.docking_queue import complete_job
        from primerforge.pipelines.consensus_pipeline import run_consensus_pipeline
    except MemoryError:
        _fail(job_id, "Server cannot load the docking engine — not enough RAM. The GPU instance is needed for this feature.")
        return
    except ImportError as e:
        _fail(job_id, f"Docking engine not available on this server: {e}")
        return

    try:
        result = asyncio.run(run_consensus_pipeline(sequence, smiles_list, top_n, pdb_content=pdb_content))
        if result.get("status") == "success":
            complete_job(job_id, result)
        else:
            _fail(job_id, result.get("message", "Pipeline failed"))
    except MemoryError:
        _fail(job_id, "Docking ran out of memory. Try a shorter sequence (< 200 residues) and fewer ligands (< 3).")
    except Exception as e:
        _fail(job_id, f"Docking error: {str(e)[:300]}")


def _fail(job_id, msg):
    try:
        from primerforge.docking_queue import complete_job
        complete_job(job_id, None, msg)
    except Exception:
        pass


if __name__ == "__main__":
    main()

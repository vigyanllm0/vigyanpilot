#!/usr/bin/env python3
"""
Standalone docking worker — runs in a SEPARATE process from gunicorn.
If this crashes (OOM, segfault), gunicorn survives.

Called by docking_queue.py via subprocess.Popen.
Reads job JSON from stdin, writes result JSON to stdout.
"""

import asyncio
import json
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    job = json.loads(sys.stdin.read())
    job_id = job["job_id"]
    sequence = job["sequence"]
    smiles_list = job.get("ligand_smiles_list", [])[:5]  # Cap to 5
    top_n = job.get("top_n", 50)
    pdb_content = job.get("pdb_content", "")

    try:
        from primerforge.pipelines.consensus_pipeline import run_consensus_pipeline
        result = asyncio.run(run_consensus_pipeline(sequence, smiles_list, top_n, pdb_content=pdb_content))
        # Write result to job file
        from primerforge.docking_queue import complete_job
        if result.get("status") == "success":
            complete_job(job_id, result)
            print(json.dumps({"ok": True}), file=sys.stderr)
        else:
            complete_job(job_id, None, result.get("message", "Pipeline failed"))
            print(json.dumps({"ok": False, "error": result.get("message")}), file=sys.stderr)
    except MemoryError:
        from primerforge.docking_queue import complete_job
        complete_job(job_id, None, "Server ran out of memory. Try with fewer ligands.")
        print(json.dumps({"ok": False, "error": "OOM"}), file=sys.stderr)
    except Exception as e:
        from primerforge.docking_queue import complete_job
        complete_job(job_id, None, f"Pipeline error: {str(e)[:300]}")
        print(json.dumps({"ok": False, "error": str(e)[:300]}), file=sys.stderr)


if __name__ == "__main__":
    main()

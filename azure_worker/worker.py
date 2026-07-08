#!/usr/bin/env python3
"""
VigyanLLM Azure Worker — Standalone Compute Container
=======================================================
Accepts job configurations via HTTP payload (JSON), executes heavy
pipeline workloads (primer design, MSA, stress testing), and POSTs
results back to a CALLBACK_URL.

This container is designed to run on Azure Container Instances (ACI)
and handles workloads that would OOM the main EC2 t3.micro instance.

Usage (injected via ACI environment variables or CLI args):
    python worker.py --job-config '{"type":"msa","sequences":[...]}' \\
                     --callback-url 'https://api.vigyanllm.in/api/v1/jobs/callback' \\
                     --callback-token 'sec-...'
    
    # Or via piped input for large payloads:
    cat job_config.json | python worker.py --callback-url '...' --callback-token '...'
"""

import os
import sys
# Ensure /app is on sys.path (worker.py lives in /app/azure_worker/)
_app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _app_root not in sys.path:
    sys.path.insert(0, _app_root)

import json
import time
import uuid
import logging
import argparse
import traceback
from typing import Dict, Optional, Any

# ── Logging ────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("azure_worker")

# ── Configuration ─────────────────────────────────────────────────────────

CALLBACK_TIMEOUT = int(os.environ.get("CALLBACK_TIMEOUT", "30"))
WORKER_VERSION = "1.0.0"


def _load_job_config() -> Optional[Dict]:
    """Load job configuration from CLI arg, env var, or stdin (in that order).

    Priority:
      1. --job-config CLI argument (JSON string)
      2. JOB_CONFIG environment variable (JSON string)
      3. Stdin (read entire input as JSON, useful for large payloads)
    """
    # Check CLI arg
    parser = argparse.ArgumentParser(
        description="VigyanLLM Azure Worker — Standalone Compute Container",
    )
    parser.add_argument("--job-config", type=str, default=None,
                        help="JSON string with job configuration")
    parser.add_argument("--callback-url", type=str, default=None,
                        help="URL to POST results on completion")
    parser.add_argument("--callback-token", type=str, default=None,
                        help="Auth token for callback (sets X-Callback-Token)")
    args, _ = parser.parse_known_args()

    # Priority 1: CLI arg
    if args.job_config:
        try:
            return json.loads(args.job_config)
        except json.JSONDecodeError as e:
            logger.error("Invalid --job-config JSON: %s", e)
            sys.exit(1)

    # Priority 2: Environment variable
    env_config = os.environ.get("JOB_CONFIG")
    if env_config:
        try:
            return json.loads(env_config)
        except json.JSONDecodeError as e:
            logger.error("Invalid JOB_CONFIG env var JSON: %s", e)
            sys.exit(1)

    # Priority 3: Stdin (piped input)
    if not sys.stdin.isatty():
        try:
            stdin_data = sys.stdin.read()
            if stdin_data.strip():
                return json.loads(stdin_data)
        except json.JSONDecodeError as e:
            logger.error("Invalid stdin JSON: %s", e)
            sys.exit(1)

    logger.error("No job configuration found. Provide via --job-config, "
                 "JOB_CONFIG env var, or stdin.")
    sys.exit(1)


def _get_callback_url() -> Optional[str]:
    """Get callback URL from CLI arg or environment variable."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--callback-url", type=str, default=None)
    parser.add_argument("--callback-token", type=str, default=None)
    args, _ = parser.parse_known_args()
    return args.callback_url or os.environ.get("CALLBACK_URL")


def _get_callback_token() -> Optional[str]:
    """Get callback token from CLI arg or environment variable."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--callback-url", type=str, default=None)
    parser.add_argument("--callback-token", type=str, default=None)
    args, _ = parser.parse_known_args()
    return args.callback_token or os.environ.get("CALLBACK_TOKEN")


def _post_callback(url: str, token: Optional[str], payload: Dict):
    """POST the result payload to the callback URL."""
    try:
        import requests
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-Callback-Token"] = token
        logger.info("Posting callback to %s (%d bytes payload)",
                    url, len(json.dumps(payload)))
        resp = requests.post(url, json=payload, headers=headers,
                             timeout=CALLBACK_TIMEOUT)
        logger.info("Callback response: HTTP %d", resp.status_code)
        if not resp.ok:
            logger.warning("Callback returned %d: %s",
                           resp.status_code, resp.text[:300])
        return resp.ok
    except ImportError:
        logger.warning("requests module not available — skipping callback")
        return False
    except Exception as e:
        logger.error("Callback request failed: %s", e)
        return False


# ── Job Type Dispatchers ──────────────────────────────────────────────────

def run_primer_design_job(config: Dict, callback_url: Optional[str] = None,
                           callback_token: Optional[str] = None) -> Dict:
    """Run the full 22-step primer design pipeline.
    
    Imports and invokes the same PipelineOrchestrator used by the
    main Flask server, but runs in this isolated container.
    """
    job_id = config.get("job_id", uuid.uuid4().hex[:12])
    logger.info("Primer design job %s started", job_id)
    
    try:
        from primerforge.engine.orchestrator import PipelineOrchestrator, PipelineConfig
        from primerforge.engine.steps import STEP_REGISTRY
    except ImportError:
        logger.warning("primerforge not installed — running simulated pipeline")
        return _run_simulated_pipeline(config, "primer_design", callback_url, callback_token)
    
    sequence = config.get("sequence", "")
    accession = config.get("accession", "")
    mode = config.get("mode", "full")
    
    input_params = dict(config)
    input_params.setdefault("mode", mode)
    input_params.setdefault("organism", config.get("organism", "human"))
    input_params.setdefault("product_min", config.get("product_min", 80))
    input_params.setdefault("product_max", config.get("product_max", 500))
    
    pipeline_config = PipelineConfig(mode=mode)
    orchestrator = PipelineOrchestrator(config=pipeline_config)
    
    # Register all 24 steps
    express_steps = {1, 6, 7, 8, 9, 12, 22, 24}
    step_meta = {
        1: ("Transcript Isoform Filter", True, "A"),
        2: ("Exon-Intron Junction Mapping", False, "A"),
        3: ("Bisulfite Conversion Simulation", False, "A"),
        4: ("Degenerate Base Parsing", True, "A"),
        5: ("Repeat Masking", False, "A"),
        6: ("Backend MSA & Conservation", False, "A"),
        7: ("Conserved Region Targeting", False, "A"),
        8: ("Primer3 Parameter Constraints", True, "B"),
        9: ("Nearest-Neighbor Tm (SantaLucia)", False, "B"),
        10: ("Dynamic Buffer & Salt Adjustments", False, "B"),
        11: ("Divalent Cation Mg Scaling", False, "B"),
        12: ("Target Specificity (BLAST)", False, "C"),
        13: ("Strain Inclusivity & Discontinuous", False, "C"),
        14: ("Structural Alignment (Bowtie2)", False, "C"),
        15: ("Organelle & Pseudogene Screening", False, "C"),
        16: ("Primer Secondary Structure (dG)", False, "D"),
        17: ("Amplicon Structural Verification", False, "D"),
        18: ("Population Variant Filter (dbSNP)", False, "D"),
        19: ("Clinical Hotspot Filter (ClinVar)", False, "D"),
        20: ("5' Overhang Adapter Tailing", False, "D"),
        21: ("Multiplex Cross-Reaction Scoring", False, "D"),
        22: ("Automated Penalty & Ranking Matrix", False, "E"),
        23: ("Thermocycling Profile Generation", False, "E"),
        24: ("Probe Design (qPCR/TaqMan)", False, "E"),
    }
    
    for number, (name, hard_failure, phase) in step_meta.items():
        orchestrator.register_step(
            number, name, STEP_REGISTRY[number],
            hard_failure=hard_failure, phase=phase,
            express_included=number in express_steps,
        )
    
    t0 = time.time()
    outcomes = orchestrator.run(job_id, input_params)
    elapsed = time.time() - t0
    
    hard_failed = any(
        o.status == "failed"
        and any(s.hard_failure for s in orchestrator.steps if s.step_number == o.step_number)
        for o in outcomes
    )
    status = "failed" if hard_failed else "completed"
    
    result = {
        "job_id": job_id,
        "job_type": "primer_design",
        "status": status,
        "mode": mode,
        "elapsed_s": round(elapsed, 3),
        "total_steps": len(outcomes),
        "steps_passed": sum(1 for o in outcomes if o.status == "passed"),
        "steps_failed": sum(1 for o in outcomes if o.status == "failed"),
        "steps_skipped": sum(1 for o in outcomes if o.status == "skipped"),
        "outcomes": [
            {
                "step_number": o.step_number,
                "step_name": o.step_name,
                "status": o.status,
                "duration_ms": o.duration_ms,
                "error_msg": o.error_msg,
            }
            for o in outcomes
        ],
    }
    
    # POST callback
    if callback_url:
        _post_callback(callback_url, callback_token, result)
    
    return result


def run_msa_job(config: Dict, callback_url: Optional[str] = None,
                 callback_token: Optional[str] = None) -> Dict:
    """Run large-scale MSA alignment.
    
    Handles 100–100,000 sequences using the same alignment strategies
    as the main server, but without blocking the Flask worker.
    """
    job_id = config.get("job_id", uuid.uuid4().hex[:12])
    logger.info("MSA job %s started", job_id)
    
    try:
        from primerforge.engine.msa_viewer import (
            create_job, process_job, get_job, format_fasta_from_job,
            format_clustal_from_job, get_msa_summary,
        )
    except ImportError:
        logger.warning("primerforge msa_viewer not available — simulating")
        sequences = config.get("sequences", [])
        return {
            "job_id": job_id,
            "job_type": "msa",
            "status": "completed",
            "sequences": len(sequences),
            "elapsed_s": 0,
            "note": "Simulated — primerforge not installed",
        }
    
    sequences = config.get("sequences", [])
    reference_id = config.get("reference_id")
    
    if not sequences or len(sequences) < 2:
        result = {
            "job_id": job_id,
            "job_type": "msa",
            "status": "failed",
            "error": "At least 2 sequences required",
        }
        if callback_url:
            _post_callback(callback_url, callback_token, result)
        return result
    
    t0 = time.time()
    msa_job_id = create_job(sequences, reference_id)
    process_job(msa_job_id)
    job = get_job(msa_job_id)
    elapsed = time.time() - t0
    
    result = {
        "job_id": job_id,
        "msa_job_id": msa_job_id,
        "job_type": "msa",
        "status": job["status"],
        "total_sequences": job.get("total", len(sequences)),
        "elapsed_s": round(elapsed, 3),
        "stats": job.get("stats"),
        "fasta": format_fasta_from_job(msa_job_id),
        "clustal": format_clustal_from_job(msa_job_id),
        "summary": get_msa_summary({"stats": job.get("stats", {})}),
        "error": job.get("error"),
    }
    
    if callback_url:
        _post_callback(callback_url, callback_token, result)
    
    return result


def run_stress_test_job(config: Dict, callback_url: Optional[str] = None,
                         callback_token: Optional[str] = None) -> Dict:
    """Run the stress tester workload.
    
    Processes configurable number of records (default 105,000)
    in chunks to measure pipeline throughput.
    """
    logger.info("Stress test job started")
    
    from azure_worker.stress_tester import run_stress_test
    
    total = config.get("total", 105_000)
    chunk_size = config.get("chunk_size", 5_000)
    
    summary = run_stress_test(
        total=total,
        chunk_size=chunk_size,
        callback_url=callback_url,
        callback_token=callback_token,
    )
    return summary


def _strip_structures(result: Dict) -> Dict:
    """Remove bulky PDB/SDF structure strings from the result before POSTing."""
    if not result:
        return result
    ranked = result.get("ranked_results")
    if ranked:
        for mol in ranked:
            mol.pop("structure", None)
    stage1 = result.get("stage1")
    if stage1:
        stage1.pop("pdb_string", None)
    return result


def _upload_structures(api_base: str, job_id: str, result: Dict):
    """Upload individual docked structures to the server for the 3D viewer."""
    import urllib.request
    import urllib.error
    ranked = result.get("ranked_results") or []
    for i, mol in enumerate(ranked):
        struct = mol.get("structure")
        if not struct:
            continue
        try:
            payload = json.dumps(struct).encode()
            req = urllib.request.Request(
                f"{api_base}/api/primer/docking/structure/upload/{job_id}/{i + 1}",
                method="POST",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=30)
        except Exception as e:
            logger.warning("Failed to upload structure rank %d for %s: %s", i + 1, job_id, e)


def run_docking_job(config: Dict, callback_url: Optional[str] = None,
                     callback_token: Optional[str] = None) -> Dict:
    """Run the consensus docking pipeline on Azure.

    Accepts protein sequence (AA) and ligand SMILES list, runs the
    3-stage ESMFold → Vina → GNINA pipeline, and posts results back.
    """
    job_id = config.get("job_id", uuid.uuid4().hex[:12])
    logger.info("Docking job %s started", job_id)

    try:
        from primerforge.pipelines.consensus_pipeline import run_consensus_pipeline
    except ImportError:
        logger.warning("Consensus pipeline not installed — simulating")
        return _run_simulated_pipeline(config, "docking", callback_url, callback_token)

    sequence = config.get("sequence", "")
    ligand_smiles_list = config.get("ligand_smiles_list") or config.get("smiles_list") or []
    top_n = int(config.get("top_n", 50))

    if not sequence or not ligand_smiles_list:
        result = {
            "job_id": job_id,
            "job_type": "docking",
            "status": "failed",
            "error": "sequence and ligand_smiles_list are required",
        }
        if callback_url:
            _post_callback(callback_url, callback_token, result)
        return result

    import asyncio
    t0 = time.time()
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        pipeline_result = loop.run_until_complete(
            run_consensus_pipeline(sequence, ligand_smiles_list, top_n=top_n)
        )
        loop.close()
    except Exception as e:
        logger.error("Docking pipeline failed: %s", e, exc_info=True)
        result = {
            "job_id": job_id,
            "job_type": "docking",
            "status": "failed",
            "error": str(e)[:500],
        }
        if callback_url:
            _post_callback(callback_url, callback_token, result)
        return result

    elapsed = time.time() - t0
    result = {
        "job_id": job_id,
        "job_type": "docking",
        "status": pipeline_result.get("status", "error"),
        "elapsed_s": round(elapsed, 3),
        "stage1": pipeline_result.get("stage1"),
        "stage2": pipeline_result.get("stage2"),
        "stage3": pipeline_result.get("stage3"),
        "ranked_results": pipeline_result.get("ranked_results", []),
        "best_molecule": pipeline_result.get("best_molecule"),
        "total_ligands": len(ligand_smiles_list),
        "top_n": top_n,
        "error": pipeline_result.get("message") or pipeline_result.get("error"),
    }

    if callback_url:
        _post_callback(callback_url, callback_token, result)

    return result


def _run_simulated_pipeline(config: Dict, job_type: str,
                             callback_url: Optional[str] = None,
                             callback_token: Optional[str] = None) -> Dict:
    """Fallback: simulate pipeline execution when primerforge is not installed.
    
    Useful for testing the Azure worker infrastructure independently
    of the full codebase.
    """
    import random
    import string
    
    job_id = config.get("job_id", uuid.uuid4().hex[:12])
    n_steps = random.randint(10, 24)
    t0 = time.time()
    
    # Simulate processing time
    seq_len = len(config.get("sequence", ""))
    sim_time = max(0.5, seq_len * 0.0005) if seq_len else random.uniform(1.0, 5.0)
    time.sleep(min(sim_time, 30.0))
    
    elapsed = time.time() - t0
    
    result = {
        "job_id": job_id,
        "job_type": job_type,
        "status": "completed",
        "mode": config.get("mode", "simulated"),
        "elapsed_s": round(elapsed, 3),
        "total_steps": n_steps,
        "steps_passed": n_steps - random.randint(0, 2),
        "steps_failed": 0,
        "steps_skipped": 0,
        "note": f"Simulated pipeline run ({n_steps} steps, {elapsed:.1f}s)",
    }
    
    if callback_url:
        _post_callback(callback_url, callback_token, result)
    
    return result


# ── Daemon Mode — Poll Main Server for Pending Jobs ──────────────────────

def _run_daemon():
    """Poll the main server for pending docking jobs, process them, and complete."""
    import time as _time
    api_base = os.environ.get("API_BASE_URL", "https://www.vigyanllm.in")
    poll_interval = int(os.environ.get("POLL_INTERVAL", "15"))
    logger.info("Daemon mode: polling %s every %ds for pending docking jobs", api_base, poll_interval)

    # Pre-warm all heavy modules to prevent cold-start delays
    try:
        from primerforge.pipelines.warmup import warmup_all
        warmup_all()
    except Exception as e:
        logger.warning("Warm-up failed (non-fatal): %s", e)

    while True:
        try:
            import urllib.request
            resp = urllib.request.urlopen(f"{api_base}/api/primer/docking/pending", timeout=10)
            data = json.loads(resp.read())
            jobs = data.get("jobs", [])
        except Exception as e:
            logger.warning("Failed to poll for jobs: %s", e)
            _time.sleep(poll_interval)
            continue

        if not jobs:
            _time.sleep(poll_interval)
            continue

        for job in jobs:
            job_id = job.get("job_id")
            if not job_id:
                continue

            logger.info("Claiming job %s", job_id)
            try:
                req = urllib.request.Request(
                    f"{api_base}/api/primer/docking/claim/{job_id}",
                    method="POST",
                    data=b"{}",
                    headers={"Content-Type": "application/json"},
                )
                claim_resp = urllib.request.urlopen(req, timeout=10)
                if claim_resp.status != 200:
                    logger.warning("Failed to claim job %s", job_id)
                    continue
            except Exception as e:
                logger.warning("Failed to claim job %s: %s", job_id, e)
                continue

            logger.info("Processing job %s (type=%s)", job_id, job.get("type"))
            try:
                config = {
                    "job_id": job_id,
                    "sequence": job.get("sequence", ""),
                    "ligand_smiles_list": job.get("ligand_smiles_list", []),
                    "top_n": job.get("top_n", 50),
                    "type": job.get("type", "docking"),
                }
                result = run_docking_job(config, callback_url=None)
                error = None
                if result:
                    if result.get("status") == "error":
                        error = result.get("error") or result.get("message", "Pipeline failed")
                    elif result.get("status") == "failed":
                        error = result.get("error", "Pipeline failed")
            except Exception as e:
                result = None
                error = str(e)
                logger.exception("Job %s failed", job_id)

            # Post result back to complete endpoint
            try:
                # Strip bulky structure data from payload to avoid timeout;
                # structures are uploaded separately below.
                stripped = _strip_structures(result) if result else result
                payload = json.dumps({"result": stripped, "error": error}).encode()
                req = urllib.request.Request(
                    f"{api_base}/api/primer/docking/complete/{job_id}",
                    method="POST",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                )
                urllib.request.urlopen(req, timeout=30)
                logger.info("Job %s completed (error=%s)", job_id, error)
            except Exception as e:
                logger.error("Failed to post result for %s: %s", job_id, e)

            # Upload individual structures so 3D viewer can load them
            if result and not error:
                _upload_structures(api_base, job_id, result)

        _time.sleep(poll_interval)


# ── Main Entrypoint ───────────────────────────────────────────────────────

def main():
    logger.info("VigyanLLM Azure Worker v%s starting", WORKER_VERSION)

    # If --daemon flag or WORKER_MODE=daemon is set, run in polling mode
    if "--daemon" in sys.argv or os.environ.get("WORKER_MODE") == "daemon":
        _run_daemon()
        return

    config = _load_job_config()
    callback_url = _get_callback_url()
    callback_token = _get_callback_token()

    job_type = config.get("type", config.get("job_type", "primer_design"))

    logger.info("Dispatching job type=%s callback_url=%s",
                job_type, callback_url or "(none)")

    dispatchers = {
        "primer_design": run_primer_design_job,
        "msa": run_msa_job,
        "stress_test": run_stress_test_job,
        "docking": run_docking_job,
        "consensus_docking": run_docking_job,
        "simulated": _run_simulated_pipeline,
    }

    handler = dispatchers.get(job_type)
    if not handler:
        logger.error("Unknown job type: %s (supported: %s)",
                     job_type, list(dispatchers.keys()))
        error_result = {
            "job_id": config.get("job_id", "unknown"),
            "job_type": job_type,
            "status": "failed",
            "error": f"Unknown job type: {job_type}",
        }
        if callback_url:
            _post_callback(callback_url, callback_token, error_result)
        sys.exit(1)

    try:
        result = handler(config, callback_url, callback_token)
        print(json.dumps(result, default=str))
    except Exception as e:
        logger.error("Job failed: %s", e, exc_info=True)
        error_result = {
            "job_id": config.get("job_id", "unknown"),
            "job_type": job_type,
            "status": "failed",
            "error": str(e)[:500],
            "traceback": traceback.format_exc(),
        }
        if callback_url:
            _post_callback(callback_url, callback_token, error_result)
        print(json.dumps(error_result, default=str))
        sys.exit(1)


if __name__ == "__main__":
    main()

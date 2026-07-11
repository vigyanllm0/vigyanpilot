"""
Celery Tasks for VigyanLLM Pipeline Engine
============================================
Async task definitions for primer design pipeline execution.

Step registration configuration:
  Phase A (Sequence & Consensus): Steps 1-7, express: steps 1, 6
    Step 1:  Transcript Isoform Filter       (express included)
    Step 6:  Backend MSA & Conservation      (express included) ★
  Phase B (Thermodynamic): Steps 8-11, express: steps 8, 9
  Phase C (Specificity & Inclusivity): Steps 12-16, express: step 12
    Step 13: Strain Inclusivity              ★
  Phase D (Structural & Multiplex): Steps 17-22, express: none
  Phase E (Ranking & Export): Steps 23-24, express: step 22, 24

Hard failure steps: 1, 4, 8 (old 6)
Soft failure: all others

MSA and strain inclusivity steps can be heavy — queued asynchronously
by the Celery broker or ThreadPoolExecutor fallback.
"""

import logging

from primerforge.celery_app import celery_app

logger = logging.getLogger("primerforge.engine.tasks")


@celery_app.task(bind=True, name="primerforge.engine.tasks.run_pipeline")
def run_pipeline(self, job_id: str):
    """
    Execute the primer design pipeline for a given job.
    Runs all steps sequentially via the PipelineOrchestrator.
    """
    logger.info("Pipeline started for job_id=%s", job_id)

    from primerforge.database import execute as db_execute
    from primerforge.database import fetch_one

    from .orchestrator import PipelineConfig, PipelineOrchestrator
    from .steps import (
        step01_execute,
        step02_execute,
        step03_execute,
        step04_execute,
        step05_execute,
        step06_execute,
        step07_execute,
        step08_execute,
        step09_execute,
        step10_execute,
        step11_execute,
        step12_execute,
        step13_execute,
        step14_execute,
        step15_execute,
        step16_execute,
        step17_execute,
        step18_execute,
        step19_execute,
        step20_execute,
        step21_execute,
        step22_execute,
        step23_execute,
        step24_execute,
    )
    job = fetch_one("SELECT input_params FROM pipeline_jobs WHERE id = %s", (job_id,))
    if not job:
        logger.error("Job %s not found in database", job_id)
        return {"job_id": job_id, "status": "failed", "error": "Job not found"}

    input_params = job["input_params"] if isinstance(job["input_params"], dict) else {}
    pipeline_mode = input_params.get("mode", "full")
    if pipeline_mode not in ("full", "express"):
        pipeline_mode = "full"

    config = PipelineConfig(mode=pipeline_mode)
    orchestrator = PipelineOrchestrator(config=config)

    # ─── Phase A: Sequence Processing & Consensus (Steps 1-7) ───────────
    orchestrator.register_step(1, "Transcript Isoform Filter",      step01_execute,      hard_failure=True,  phase="A", express_included=True)
    orchestrator.register_step(2, "Exon-Intron Junction Mapping",   step02_execute,      hard_failure=False, phase="A", express_included=False)
    orchestrator.register_step(3, "Bisulfite Conversion Simulation", step03_execute,      hard_failure=False, phase="A", express_included=False)
    orchestrator.register_step(4, "Degenerate Base Parsing",        step04_execute,      hard_failure=True,  phase="A", express_included=False)
    orchestrator.register_step(5, "Repeat Masking",                  step05_execute,      hard_failure=False, phase="A", express_included=False)
    orchestrator.register_step(6, "Backend MSA & Conservation",     step06_execute,      hard_failure=False, phase="A", express_included=True)
    orchestrator.register_step(7, "Conserved Region Targeting",     step07_execute,      hard_failure=False, phase="A", express_included=False)

    # ─── Phase B: Thermodynamic Validation (Steps 8-11) ─────────────────
    orchestrator.register_step(8,  "Primer3 Parameter Constraints",    step08_execute, hard_failure=True,  phase="B", express_included=True)
    orchestrator.register_step(9,  "Nearest-Neighbor Tm (SantaLucia)", step09_execute, hard_failure=False, phase="B", express_included=True)
    orchestrator.register_step(10, "Dynamic Buffer & Salt Adjustments", step10_execute, hard_failure=False, phase="B", express_included=False)
    orchestrator.register_step(11, "Divalent Cation Mg\u00b2\u207a Scaling", step11_execute, hard_failure=False, phase="B", express_included=False)

    # ─── Phase C: Specificity & Inclusivity (Steps 12-16) ──────────────
    orchestrator.register_step(12, "Target Specificity (BLAST + Viewer)", step12_execute, hard_failure=False, phase="C", express_included=True)
    orchestrator.register_step(13, "Strain Inclusivity & Discontinuous",  step13_execute, hard_failure=False, phase="C", express_included=False)
    orchestrator.register_step(14, "Structural Alignment (Bowtie2)",      step14_execute, hard_failure=False, phase="C", express_included=False)
    orchestrator.register_step(15, "Organelle & Pseudogene Screening",    step15_execute, hard_failure=False, phase="C", express_included=False)
    orchestrator.register_step(16, "Primer Secondary Structure (\u0394G)", step16_execute, hard_failure=False, phase="D", express_included=False)

    # ─── Phase D: Structural & Multiplex Analysis (Steps 17-22) ────────
    orchestrator.register_step(17, "Amplicon Structural Verification",  step17_execute, hard_failure=False, phase="D", express_included=False)
    orchestrator.register_step(18, "Population Variant Filter (dbSNP)", step18_execute, hard_failure=False, phase="D", express_included=False)
    orchestrator.register_step(19, "Clinical Hotspot Filter (ClinVar)", step19_execute, hard_failure=False, phase="D", express_included=False)
    orchestrator.register_step(20, "5' Overhang Adapter Tailing",       step20_execute, hard_failure=False, phase="D", express_included=False)
    orchestrator.register_step(21, "Multiplex Cross-Reaction Scoring",  step21_execute, hard_failure=False, phase="D", express_included=False)
    orchestrator.register_step(22, "Automated Penalty & Ranking Matrix", step22_execute, hard_failure=False, phase="E", express_included=True)

    # ─── Phase E: Profiling & Export (Steps 23-24) ─────────────────────
    orchestrator.register_step(23, "Thermocycling Profile Generation", step23_execute, hard_failure=False, phase="E", express_included=False)
    orchestrator.register_step(24, "Probe Design (qPCR/TaqMan)",       step24_execute, hard_failure=False, phase="E", express_included=True)

    total_steps = 24
    db_execute("UPDATE pipeline_jobs SET status = 'running', started_at = NOW() WHERE id = %s", (job_id,))

    outcomes = orchestrator.run(job_id, input_params)

    import json as json_mod

    from primerforge.crypto_utils import encrypt_data
    for outcome in outcomes:
        try:
            plain = json_mod.dumps(outcome.output_data) if outcome.output_data else '{}'
            encrypted = encrypt_data(plain)
            # encrypted is a plain string — wrap in json.dumps so it's valid
            # for the PostgreSQL json column (psycopg2 deserializes it back
            # to a plain string on read, where _decrypt_output detects it by
            # the "gAAAAA" Fernet prefix)
            db_execute(
                """INSERT INTO pipeline_results (job_id, step_number, step_name, status, output_data, duration_ms, phase)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (job_id, outcome.step_number, outcome.step_name, outcome.status,
                 json_mod.dumps(encrypted), outcome.duration_ms, outcome.phase)
            )
        except Exception as e:
            logger.error("Failed to save step %d result: %s", outcome.step_number, e)

    hard_failed = any(
        o.status == "failed" and any(s.hard_failure for s in orchestrator.steps if s.step_number == o.step_number)
        for o in outcomes
    )
    final_status = "failed" if hard_failed else "completed"

    error_log = None
    if hard_failed:
        errors = [f"Step {o.step_number} ({o.step_name}): {o.error_msg}" for o in outcomes if o.status == "failed"]
        error_log = "; ".join(errors)

    db_execute(
        "UPDATE pipeline_jobs SET status = %s, completed_at = NOW(), current_step = %s, error_log = %s WHERE id = %s",
        (final_status, total_steps, error_log, job_id)
    )

    return {
        "job_id": job_id,
        "status": final_status,
        "mode": pipeline_mode,
        "steps_passed": sum(1 for o in outcomes if o.status == "passed"),
        "steps_failed": sum(1 for o in outcomes if o.status == "failed"),
        "steps_skipped": sum(1 for o in outcomes if o.status == "skipped"),
    }

"""
Celery Tasks for VigyanLLM Pipeline Engine
============================================
Async task definitions for 22-step pipeline execution.

Step registration configuration:
  Phase A (Sequence Processing): Steps 1-5, express: step 1 only
  Phase B (Thermodynamic Validation): Steps 6-9, express: steps 6, 7
  Phase C (Specificity & Variant Filtering): Steps 10-12, express: step 10
  Phase D (Structural & Multiplex Analysis): Steps 13-18, express: none
  Phase E (Ranking, Profiling & Export): Steps 19-22, express: steps 19, 22

Hard failure steps: 1, 4, 6
Soft failure: all others
"""

import logging

from primerforge.celery_app import celery_app

logger = logging.getLogger("primerforge.engine.tasks")


@celery_app.task(bind=True, name="primerforge.engine.tasks.run_pipeline")
def run_pipeline(self, job_id: str):
    """
    Execute the 22-step primer design pipeline for a given job.
    Runs all steps sequentially via the PipelineOrchestrator.

    The pipeline mode (full/express) is derived from the job's input_params.
    """
    logger.info(f"Pipeline started for job_id={job_id}")

    from .orchestrator import PipelineOrchestrator, PipelineConfig
    from .steps import (
        step01_isoform_filter,
        step02_exon_intron_junction,
        step03_bisulfite_conversion,
        step04_degenerate_bases,
        step05_repeat_masking,
        step06_primer3_design,
        step07_thermodynamic_refinement,
        step08_buffer_salt,
        step09_mg_correction,
        step10_blast_specificity,
        step11_bowtie2_alignment,
        step12_organelle_screening,
        step13_secondary_structure,
        step14_amplicon_structure,
        step15_dbsnp_filter,
        step16_clinical_hotspots,
        step17_adapter_tailing,
        step18_multiplex_scoring,
        step19_ranking,
        step20_thermocycling,
        step21_manufacturing,
        step22_probe_design,
    )

    # Get job input params from database
    from primerforge.database import fetch_one, execute as db_execute
    job = fetch_one("SELECT input_params FROM pipeline_jobs WHERE id = %s", (job_id,))
    if not job:
        logger.error(f"Job {job_id} not found in database")
        return {"job_id": job_id, "status": "failed", "error": "Job not found"}

    input_params = job["input_params"] if isinstance(job["input_params"], dict) else {}

    # Derive pipeline mode from input_params (default: "full")
    pipeline_mode = input_params.get("mode", "full")
    if pipeline_mode not in ("full", "express"):
        logger.warning(
            f"VigyanLLM: Invalid pipeline mode '{pipeline_mode}' for job {job_id}, defaulting to 'full'"
        )
        pipeline_mode = "full"

    config = PipelineConfig(mode=pipeline_mode)

    # Build orchestrator with PipelineConfig
    orchestrator = PipelineOrchestrator(config=config)

    # ─── Phase A: Sequence Processing (Steps 1-5) ────────────────────────
    orchestrator.register_step(
        1, "Transcript Isoform Filter",
        step01_isoform_filter.execute,
        hard_failure=True, phase="A", express_included=True,
    )
    orchestrator.register_step(
        2, "Exon-Intron Junction Mapping",
        step02_exon_intron_junction.execute,
        hard_failure=False, phase="A", express_included=False,
    )
    orchestrator.register_step(
        3, "Bisulfite Conversion Simulation",
        step03_bisulfite_conversion.execute,
        hard_failure=False, phase="A", express_included=False,
    )
    orchestrator.register_step(
        4, "Degenerate Base Parsing",
        step04_degenerate_bases.execute,
        hard_failure=True, phase="A", express_included=False,
    )
    orchestrator.register_step(
        5, "Repeat Masking",
        step05_repeat_masking.execute,
        hard_failure=False, phase="A", express_included=False,
    )

    # ─── Phase B: Thermodynamic Validation (Steps 6-9) ───────────────────
    orchestrator.register_step(
        6, "Primer3 Parameter Constraints",
        step06_primer3_design.execute,
        hard_failure=True, phase="B", express_included=True,
    )
    orchestrator.register_step(
        7, "Nearest-Neighbor Tm (SantaLucia)",
        step07_thermodynamic_refinement.execute,
        hard_failure=False, phase="B", express_included=True,
    )
    orchestrator.register_step(
        8, "Dynamic Buffer & Salt Adjustments",
        step08_buffer_salt.execute,
        hard_failure=False, phase="B", express_included=False,
    )
    orchestrator.register_step(
        9, "Divalent Cation Mg²+ Scaling",
        step09_mg_correction.execute,
        hard_failure=False, phase="B", express_included=False,
    )

    # ─── Phase C: Specificity & Variant Filtering (Steps 10-12) ──────────
    orchestrator.register_step(
        10, "Target Specificity (BLAST)",
        step10_blast_specificity.execute,
        hard_failure=False, phase="C", express_included=True,
    )
    orchestrator.register_step(
        11, "Structural Alignment (Bowtie2)",
        step11_bowtie2_alignment.execute,
        hard_failure=False, phase="C", express_included=False,
    )
    orchestrator.register_step(
        12, "Organelle & Pseudogene Screening",
        step12_organelle_screening.execute,
        hard_failure=False, phase="C", express_included=False,
    )

    # ─── Phase D: Structural & Multiplex Analysis (Steps 13-18) ──────────
    orchestrator.register_step(
        13, "Primer Secondary Structure (ΔG)",
        step13_secondary_structure.execute,
        hard_failure=False, phase="D", express_included=False,
    )
    orchestrator.register_step(
        14, "Amplicon Structural Verification",
        step14_amplicon_structure.execute,
        hard_failure=False, phase="D", express_included=False,
    )
    orchestrator.register_step(
        15, "Population Variant Filter (dbSNP)",
        step15_dbsnp_filter.execute,
        hard_failure=False, phase="D", express_included=False,
    )
    orchestrator.register_step(
        16, "Clinical Hotspot Filter (ClinVar)",
        step16_clinical_hotspots.execute,
        hard_failure=False, phase="D", express_included=False,
    )
    orchestrator.register_step(
        17, "5' Overhang Adapter Tailing",
        step17_adapter_tailing.execute,
        hard_failure=False, phase="D", express_included=False,
    )
    orchestrator.register_step(
        18, "Multiplex Cross-Reaction (PrimerPooler)",
        step18_multiplex_scoring.execute,
        hard_failure=False, phase="D", express_included=False,
    )

    # ─── Phase E: Ranking, Profiling & Export (Steps 19-22) ──────────────
    orchestrator.register_step(
        19, "Automated Penalty & Ranking Matrix",
        step19_ranking.execute,
        hard_failure=False, phase="E", express_included=True,
    )
    orchestrator.register_step(
        20, "Thermocycling Profile Generation",
        step20_thermocycling.execute,
        hard_failure=False, phase="E", express_included=False,
    )
    orchestrator.register_step(
        21, "Manufacturing Feasibility Screening",
        step21_manufacturing.execute,
        hard_failure=False, phase="E", express_included=False,
    )
    orchestrator.register_step(
        22, "Probe Design (qPCR/TaqMan)",
        step22_probe_design.execute,
        hard_failure=False, phase="E", express_included=True,
    )

    # Mark as running
    db_execute("UPDATE pipeline_jobs SET status = 'running', started_at = NOW() WHERE id = %s", (job_id,))

    # Run the pipeline
    outcomes = orchestrator.run(job_id, input_params)

    # Persist each step result
    import json as json_mod
    for outcome in outcomes:
        try:
            db_execute(
                """INSERT INTO pipeline_results (job_id, step_number, step_name, status, output_data, duration_ms, phase)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (job_id, outcome.step_number, outcome.step_name, outcome.status,
                 json_mod.dumps(outcome.output_data) if outcome.output_data else '{}',
                 outcome.duration_ms, outcome.phase)
            )
        except Exception as e:
            logger.error(f"Failed to save step {outcome.step_number} result: {e}")

    # Determine final status
    hard_failed = any(
        o.status == "failed" and any(s.hard_failure for s in orchestrator.steps if s.step_number == o.step_number)
        for o in outcomes
    )
    final_status = "failed" if hard_failed else "completed"

    # Update job completion
    error_log = None
    if hard_failed:
        errors = [f"Step {o.step_number} ({o.step_name}): {o.error_msg}" for o in outcomes if o.status == "failed"]
        error_log = "; ".join(errors)

    db_execute(
        "UPDATE pipeline_jobs SET status = %s, completed_at = NOW(), current_step = 22, error_log = %s WHERE id = %s",
        (final_status, error_log, job_id)
    )

    return {
        "job_id": job_id,
        "status": final_status,
        "mode": pipeline_mode,
        "steps_passed": sum(1 for o in outcomes if o.status == "passed"),
        "steps_failed": sum(1 for o in outcomes if o.status == "failed"),
        "steps_skipped": sum(1 for o in outcomes if o.status == "skipped"),
    }

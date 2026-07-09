#!/usr/bin/env python3
"""
VigyanLLM Pipeline API Endpoints
==================================
REST endpoints for submitting, monitoring, and retrieving 22-step pipeline results.

Endpoints:
  POST /api/pipeline/submit     — Submit new 22-step pipeline job
  GET  /api/pipeline/status/:id — Get job status + progress
  GET  /api/pipeline/result/:id — Get completed job results (with compliance & orders)
  GET  /api/pipeline/jobs       — List user's pipeline jobs
"""

import json
import logging
import os
import socket
import uuid
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from functools import wraps

from flask import Blueprint, request, jsonify, Response, g

from ..pg_auth import require_auth, require_admin, check_usage, consume_token
from ..database import fetch_one, fetch_all, execute, execute_returning
from ..crypto_utils import decrypt_data
from .branding import brand_response, brand_error

logger = logging.getLogger("primerforge.engine.pipeline_routes")


def _route_error_handler(f):
    """Decorator: catch any unhandled exception and return structured 500 JSON."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as exc:
            logger.error("Route %s failed: %s", f.__name__, exc, exc_info=True)
            return jsonify(brand_response({
                "error": brand_error(f"Internal error: {str(exc)[:200]}"),
                "code": "INTERNAL_ERROR",
            })), 500
    return wrapper


def _decrypt_output(row: dict, key: str = "output_data") -> dict:
    """Decrypt the output_data field of a pipeline result row in-place.

    Handles:
      - psycopg2-deserialized plain string (gAAAAAB...)
      - raw JSON-encoded string from DB ("gAAAAAB...")
      - legacy unencrypted JSON objects/arrays
    """
    raw = row.get(key)
    if isinstance(raw, str):
        # Strip JSON string wrapping if present (psycopg2 sometimes returns
        # raw JSON text instead of deserialized value depending on connection
        # configuration)
        stripped = raw
        if stripped.startswith('"') and stripped.endswith('"'):
            try:
                stripped = json.loads(stripped)
            except (json.JSONDecodeError, TypeError):
                stripped = raw
        if not isinstance(stripped, str):
            row[key] = stripped
            return row
        if stripped.startswith("gAAAAA"):  # Fernet ciphertext marker
            decrypted = decrypt_data(stripped)
            if decrypted:
                try:
                    row[key] = json.loads(decrypted)
                    return row
                except Exception as e: logger.debug("Suppressed exception: %s", e)
        # Plain JSON string (legacy / non-encrypted data)
        try:
            row[key] = json.loads(stripped)
        except Exception as e: logger.debug("Suppressed exception: %s", e)
    elif isinstance(raw, (dict, list)):
        pass  # Already a JSON object — legacy data, nothing to do
    return row

pipeline_bp = Blueprint("pipeline", __name__)

_BACKGROUND_EXECUTOR = ThreadPoolExecutor(max_workers=2)


def _celery_broker_available(timeout: float = 0.25) -> bool:
    """Return True when the configured Redis broker can accept connections.
    Only returns True if REDIS_URL is explicitly set (not the default fallback)."""
    broker_url = os.environ.get("REDIS_URL", "")
    if not broker_url:
        return False  # Redis not configured — always run synchronously
    parsed = urlparse(broker_url)
    if parsed.scheme not in {"redis", "rediss"}:
        return False
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _run_pipeline_background(job_id: str, reason: str) -> None:
    """Run the pipeline in a background thread. Updates DB as it goes."""
    logger.info("VigyanLLM: Running pipeline in background for job %s: %s", job_id, reason)
    try:
        from .tasks import run_pipeline

        result = run_pipeline(job_id)
        status = result.get("status", "unknown") if isinstance(result, dict) else "unknown"
        logger.info("VigyanLLM: Pipeline %s completed in background: %s", job_id, status)
    except Exception as bg_err:
        logger.error("VigyanLLM: Background pipeline run failed for %s: %s", job_id, bg_err)
        execute(
            "UPDATE pipeline_jobs SET status = 'failed', error_log = %s, completed_at = NOW() WHERE id = %s",
            (str(bg_err), job_id),
        )


def _coerce_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalise_order_pair(pair: dict, index: int) -> dict:
    """Convert pipeline ranking output into order serializer pair shape."""
    forward = pair.get("forward") or pair.get("forward_primer") or {}
    reverse = pair.get("reverse") or pair.get("reverse_primer") or {}

    if isinstance(forward, str):
        forward = {"sequence": forward}
    if isinstance(reverse, str):
        reverse = {"sequence": reverse}

    pair_id = pair.get("pair_id") or pair.get("rank") or index + 1
    fwd_seq = forward.get("sequence", "")
    rev_seq = reverse.get("sequence", "")

    return {
        "forward": {
            **forward,
            "name": forward.get("name") or f"VL_{pair_id}_FWD",
            "sequence": fwd_seq,
        },
        "reverse": {
            **reverse,
            "name": reverse.get("name") or f"VL_{pair_id}_REV",
            "sequence": rev_seq,
        },
    }


def _normalise_order_probe(probe: dict, index: int) -> dict:
    """Convert pipeline probe output into order serializer probe shape."""
    labels = probe.get("labels") or {}
    return {
        **probe,
        "name": probe.get("name") or probe.get("probe_id") or f"VL_PROBE_{index + 1}",
        "sequence": probe.get("sequence", ""),
        "5_prime_modification": (
            probe.get("5_prime_modification")
            or probe.get("reporter_5prime")
            or labels.get("reporter_5prime")
            or "FAM"
        ),
        "3_prime_modification": (
            probe.get("3_prime_modification")
            or probe.get("quencher_3prime")
            or labels.get("quencher_3prime")
            or "BHQ-1"
        ),
        "dye_specification": probe.get("dye_specification") or "FAM/BHQ-1",
    }


@pipeline_bp.route("/api/pipeline/submit", methods=["POST"])
@_route_error_handler
@require_auth
def submit_pipeline():
    """
    Submit a new 22-step pipeline job.

    Request body:
    {
        "sequence": "ATCG..." or null (if using accession),
        "accession": "NM_007294" or null (if using raw sequence),
        "organism": "human",
        "targeting_mode": "common_exon" | "isoform_specific",
        "design_mode": "standard" | "bisulfite" | "multiplex",
        "adapter_platform": "illumina_nextera" | "illumina_truseq" | "ion_torrent" | null,
        "probe_mode": "taqman" | "sybr" | null,
        "polymerase_type": "taq" | "hifi",
        "buffer_conditions": {
            "monovalent_mm": 50, "divalent_mm": 1.5,
            "dntp_mm": 0.2, "oligo_conc_nm": 250
        },
        "template_ng": 100,
        "mode": "full" | "express",
        "multiplex": false,
        "product_min": 80,
        "product_max": 500,
        "min_tm": 58,
        "max_tm": 65
    }

    Returns:
        {"job_id": "uuid", "status": "queued", "system": "VigyanLLM"}
    """
    data = request.get_json(silent=True) or {}

    # Validate required inputs
    sequence = data.get("sequence", "")
    accession = data.get("accession", "")

    if not sequence and not accession:
        return jsonify(brand_response(
            {"error": brand_error("Either 'sequence' or 'accession' is required.")}
        )), 400

    # Validate mode field
    mode = data.get("mode", "full")
    if mode not in ("full", "express"):
        return jsonify(brand_response(
            {"error": brand_error("'mode' must be 'full' or 'express'.")}
        )), 400

    product_min = _coerce_int(data.get("product_min"), 80)
    product_max = _coerce_int(data.get("product_max"), 500)
    min_tm = _coerce_float(data.get("min_tm"), 58.0)
    max_tm = _coerce_float(data.get("max_tm"), 65.0)

    if product_min < 50:
        return jsonify(brand_response(
            {"error": brand_error("Minimum PCR product length must be at least 50 bp.")}
        )), 422
    if product_max > 5000:
        return jsonify(brand_response(
            {"error": brand_error("Maximum PCR product length cannot exceed 5,000 bp.")}
        )), 422
    if product_min > product_max:
        return jsonify(brand_response(
            {"error": brand_error("Minimum PCR product length must be less than or equal to maximum.")}
        )), 422
    if min_tm >= max_tm:
        return jsonify(brand_response(
            {"error": brand_error("Minimum primer Tm must be lower than maximum primer Tm.")}
        )), 422

    # Build input params for 22-step pipeline
    input_params = {
        "sequence": sequence,
        "accession": accession,
        "sequence_source": data.get("sequence_source", ""),
        "organism": data.get("organism", "human"),
        "targeting_mode": data.get("targeting_mode", "common_exon"),
        "design_mode": data.get("design_mode", "standard"),
        "adapter_platform": data.get("adapter_platform"),
        "probe_mode": data.get("probe_mode"),
        "polymerase_type": data.get("polymerase_type", "taq"),
        "buffer_conditions": data.get("buffer_conditions", {
            "monovalent_mm": 50.0,
            "divalent_mm": 1.5,
            "dntp_mm": 0.2,
            "oligo_conc_nm": 250.0,
        }),
        "template_ng": data.get("template_ng", 100),
        "mode": mode,
        "multiplex": data.get("multiplex", False),
        "specificity_check": bool(data.get("specificity_check", True)),
        "ncbi_api_key": data.get("ncbi_api_key") or None,
        "ncbi_email": data.get("ncbi_email") or None,
        "product_min": product_min,
        "product_max": product_max,
        "min_tm": min_tm,
        "max_tm": max_tm,
        "design_params": {
            "tm_min": min_tm,
            "tm_max": max_tm,
            "product_size_min": product_min,
            "product_size_max": product_max,
        },
    }

    user_id = g.user.get("user_id")
    is_admin = g.user.get("role") == "admin"

    # Quota check: skip for admin users, reject if regular user exceeded monthly quota
    if not is_admin:
        try:
            quota_row = fetch_one(
                """SELECT quota_used, monthly_quota FROM user_quotas
                   WHERE user_id = %s AND month = date_trunc('month', CURRENT_DATE)""",
                (user_id,)
            )
            if quota_row and quota_row.get("monthly_quota") is not None:
                quota_used = quota_row.get("quota_used", 0)
                monthly_quota = quota_row["monthly_quota"]
                if quota_used >= monthly_quota:
                    logger.warning(
                        "VigyanLLM: Quota exceeded for user %s (%d/%d)",
                        user_id, quota_used, monthly_quota,
                    )
                    return jsonify(brand_response({
                        "error": brand_error(
                            f"Monthly pipeline quota exceeded ({quota_used}/{monthly_quota}). "
                            "Please upgrade your plan or wait until next month."
                        ),
                        "quota_used": quota_used,
                        "monthly_quota": monthly_quota,
                    })), 429
        except Exception as e:
            logger.debug("VigyanLLM: Monthly quota check skipped: %s", e)

        # Daily quota: 2 free designs per day. Beyond that, consume a token.
        consumed_daily_token = False
        try:
            today_count = fetch_one(
                """SELECT COUNT(*) AS cnt FROM pipeline_jobs
                   WHERE user_id = %s
                     AND created_at >= CURRENT_DATE
                     AND created_at < CURRENT_DATE + INTERVAL '1 day'
                     AND status IN ('queued', 'running', 'completed')""",
                (user_id,)
            )
            daily_used = today_count["cnt"] if today_count else 0
            if daily_used >= 2:
                if not consume_token(user_id, g.user["email"]):
                    logger.warning(
                        "VigyanLLM: Daily quota exceeded for user %s (%d/2) and no tokens",
                        user_id, daily_used,
                    )
                    return jsonify(brand_response({
                        "error": brand_error(
                            f"Daily pipeline quota reached ({daily_used}/2). "
                            "Claim academic access for 10 free designs, or upgrade to a paid plan."
                        ),
                        "daily_used": daily_used,
                        "daily_limit": 2,
                        "needs_payment": True,
                    })), 429
                consumed_daily_token = True
        except Exception as e:
            logger.debug("VigyanLLM: Daily quota check skipped: %s", e)

    # Create job in database with 22-step defaults
    job = execute_returning(
        """INSERT INTO pipeline_jobs (user_id, status, input_params, total_steps, mode)
           VALUES (%s, 'queued', %s, 22, %s)
           RETURNING id, status, created_at""",
        (user_id, json.dumps(input_params), mode)
    )

    if not job:
        return jsonify(brand_response(
            {"error": brand_error("Failed to create pipeline job.")}
        )), 500

    job_id = str(job["id"])

    # Audit log: pipeline submission
    try:
        from ..database import log_audit
        log_audit("pipeline_submit", accession=input_params.get("accession",""),
                  job_id=job_id, gene_symbol=input_params.get("organism",""),
                  source=input_params.get("sequence_source",""),
                  details=f"mode={mode}, organism={input_params.get('organism','')}",
                  user_id=user_id)
    except Exception as e:
        logger.debug("Suppressed exception: %s", e)

    # Enqueue Celery task only when Redis broker is reachable. Local/dev mode
    # often has no Redis, and Celery can otherwise spend seconds retrying.
    # Fallback: ThreadPoolExecutor runs the pipeline in a background thread.
    if _celery_broker_available():
        try:
            from .tasks import run_pipeline
            run_pipeline.delay(job_id)
            logger.info("VigyanLLM: Pipeline job %s queued for user %s (mode=%s)", job_id, user_id, mode)
        except Exception as e:
            _BACKGROUND_EXECUTOR.submit(_run_pipeline_background, job_id, f"Celery enqueue failed: {e}")
            logger.warning("VigyanLLM: Celery enqueue failed for %s, falling back to ThreadPoolExecutor: %s", job_id, e)
    else:
        _BACKGROUND_EXECUTOR.submit(_run_pipeline_background, job_id, "Redis broker unavailable")
        logger.info("VigyanLLM: Pipeline job %s dispatched to background thread (mode=%s)", job_id, mode)

    return jsonify(brand_response({
        "job_id": job_id,
        "status": "queued",
        "mode": mode,
        "total_steps": 22,
        "message": "Pipeline job submitted. Poll /api/pipeline/status for progress.",
    })), 202
@pipeline_bp.route("/api/pipeline/status/<job_id>", methods=["GET"])
@_route_error_handler
@require_auth
def get_pipeline_status(job_id: str):
    """Get current status and progress of a pipeline job."""
    user_id = g.user.get("user_id")
    is_admin = g.user.get("role") == "admin"

    # Fetch job (user can only see their own, admin sees all)
    if is_admin:
        job = fetch_one("SELECT * FROM pipeline_jobs WHERE id = %s", (job_id,))
    else:
        job = fetch_one(
            "SELECT * FROM pipeline_jobs WHERE id = %s AND user_id = %s",
            (job_id, user_id)
        )

    if not job:
        return jsonify(brand_response(
            {"error": brand_error("Job not found.")}
        )), 404

    # Get step results
    steps = fetch_all(
        """SELECT step_number, step_name, status, duration_ms, created_at
           FROM pipeline_results WHERE job_id = %s ORDER BY step_number""",
        (job_id,)
    )

    return jsonify(brand_response({
        "job_id": job_id,
        "status": job["status"],
        "mode": job.get("mode", "full"),
        "phase": job.get("phase"),
        "current_step": job.get("current_step", 0),
        "total_steps": job.get("total_steps", 22),
        "created_at": str(job["created_at"]) if job.get("created_at") else None,
        "started_at": str(job["started_at"]) if job.get("started_at") else None,
        "completed_at": str(job["completed_at"]) if job.get("completed_at") else None,
        "error": job.get("error_log"),
        "steps": steps,
    })), 200


@pipeline_bp.route("/api/pipeline/result/<job_id>", methods=["GET"])
@_route_error_handler
@require_auth
def get_pipeline_result(job_id: str):
    """Get full results of a completed pipeline job, including compliance and order payloads."""
    user_id = g.user.get("user_id")
    is_admin = g.user.get("role") == "admin"

    if is_admin:
        job = fetch_one("SELECT * FROM pipeline_jobs WHERE id = %s", (job_id,))
    else:
        job = fetch_one(
            "SELECT * FROM pipeline_jobs WHERE id = %s AND user_id = %s",
            (job_id, user_id)
        )

    if not job:
        return jsonify(brand_response(
            {"error": brand_error("Job not found.")}
        )), 404

    if job["status"] not in ("completed", "failed"):
        return jsonify(brand_response({
            "error": brand_error("Job not yet completed."),
            "status": job["status"],
            "current_step": job.get("current_step", 0),
            "total_steps": job.get("total_steps", 22),
        })), 202

    # Get all step results with full output data
    steps = fetch_all(
        """SELECT step_number, step_name, status, output_data, duration_ms
           FROM pipeline_results WHERE job_id = %s ORDER BY step_number""",
        (job_id,)
    )
    for s in steps:
        _decrypt_output(s)

    # Get compliance screening result
    compliance = fetch_one(
        """SELECT status, sequences_screened, matched_organism, matched_gene,
                  percent_identity, alignment_length, screened_at
           FROM compliance_screening WHERE job_id = %s
           ORDER BY screened_at DESC LIMIT 1""",
        (job_id,)
    )

    # Get order payloads
    order_payloads = fetch_all(
        """SELECT vendor, payload, order_id, oligo_count, scale, created_at
           FROM order_payloads WHERE job_id = %s ORDER BY created_at""",
        (job_id,)
    )

    return jsonify(brand_response({
        "job_id": job_id,
        "status": job["status"],
        "mode": job.get("mode", "full"),
        "input_params": job.get("input_params"),
        "steps": steps,
        "compliance_status": job.get("compliance_status"),
        "compliance_details": compliance,
        "order_payloads": order_payloads,
        "total_duration_ms": sum(s.get("duration_ms", 0) for s in steps if s.get("duration_ms")),
    })), 200


@pipeline_bp.route("/api/pipeline/result/<job_id>/step/<int:step_number>", methods=["GET"])
@_route_error_handler
@require_auth
def get_raw_step_output(job_id: str, step_number: int):
    """Get raw output data for a specific pipeline step."""
    user_id = g.user.get("user_id")
    is_admin = g.user.get("role") == "admin"

    if is_admin:
        job = fetch_one("SELECT id FROM pipeline_jobs WHERE id = %s", (job_id,))
    else:
        job = fetch_one(
            "SELECT id FROM pipeline_jobs WHERE id = %s AND user_id = %s",
            (job_id, user_id)
        )
    if not job:
        return jsonify({"error": "Job not found"}), 404

    step = fetch_one(
        """SELECT step_number, step_name, status, output_data, duration_ms
           FROM pipeline_results WHERE job_id = %s AND step_number = %s""",
        (job_id, step_number)
    )
    if not step:
        return jsonify({"error": "Step not found"}), 404

    _decrypt_output(step)

    return jsonify({
        "job_id": job_id,
        "step_number": step["step_number"],
        "step_name": step["step_name"],
        "status": step["status"],
        "output_data": step["output_data"],
        "duration_ms": step.get("duration_ms"),
    }), 200


@pipeline_bp.route("/api/pipeline/result/<job_id>/raw", methods=["GET"])
@_route_error_handler
@require_auth
def get_raw_pipeline_export(job_id: str):
    """Export all pipeline step results as raw JSON for user download."""
    user_id = g.user.get("user_id")
    is_admin = g.user.get("role") == "admin"

    if is_admin:
        job = fetch_one("SELECT * FROM pipeline_jobs WHERE id = %s", (job_id,))
    else:
        job = fetch_one(
            "SELECT * FROM pipeline_jobs WHERE id = %s AND user_id = %s",
            (job_id, user_id)
        )
    if not job:
        return jsonify({"error": "Job not found"}), 404

    steps = fetch_all(
        """SELECT step_number, step_name, status, output_data, duration_ms, phase, error_msg
           FROM pipeline_results WHERE job_id = %s ORDER BY step_number""",
        (job_id,)
    )

    export = {
        "job_id": job_id,
        "status": job.get("status"),
        "mode": job.get("mode"),
        "input_params": job.get("input_params"),
        "created_at": str(job.get("created_at", "")),
        "completed_at": str(job.get("completed_at", "")),
        "steps": [],
    }
    for s in steps:
        _decrypt_output(s)
        export["steps"].append({
            "step_number": s["step_number"],
            "step_name": s["step_name"],
            "status": s["status"],
            "phase": s.get("phase"),
            "duration_ms": s.get("duration_ms"),
            "error_msg": s.get("error_msg"),
            "output_data": s["output_data"],
        })

    raw = json.dumps(export, indent=2, default=str)
    return Response(
        raw,
        mimetype="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=vigyanpilot_raw_{job_id[:8]}.json",
            "Content-Type": "application/json",
        }
    ), 200


@pipeline_bp.route("/api/pipeline/jobs", methods=["GET"])
@_route_error_handler
@require_auth
def list_pipeline_jobs():
    """List all pipeline jobs for the current user."""
    user_id = g.user.get("user_id")
    is_admin = g.user.get("role") == "admin"

    if is_admin:
        jobs = fetch_all(
            """SELECT id, status, mode, current_step, total_steps, created_at, completed_at
               FROM pipeline_jobs ORDER BY created_at DESC LIMIT 50"""
        )
    else:
        jobs = fetch_all(
            """SELECT id, status, mode, current_step, total_steps, created_at, completed_at
               FROM pipeline_jobs WHERE user_id = %s ORDER BY created_at DESC LIMIT 20""",
            (user_id,)
        )

    return jsonify(brand_response({"jobs": jobs, "count": len(jobs)})), 200


# ═══════════════════════════════════════════════════════════════════════════
# COMPLIANCE & ORDER SERIALIZATION ENDPOINTS
# Requirements: 27.8, 28.6, 25.7
# ═══════════════════════════════════════════════════════════════════════════


@pipeline_bp.route("/api/pipeline/order/<job_id>", methods=["POST"])
@_route_error_handler
@require_auth
def trigger_order_serialization(job_id: str):
    """
    Trigger order serialization for a completed pipeline job.

    Requires biosecurity_cleared compliance status. Runs IGSC compliance
    screening, then serializes the order for the specified vendor.

    Query params:
        vendor: 'idt' or 'twist' (default: 'idt')
        application_type: scale type (default: 'standard_pcr')

    Returns:
        Order payload JSON with order_id, vendor, oligos, etc.
    """
    user_id = g.user.get("user_id")
    is_admin = g.user.get("role") == "admin"

    # Fetch job
    if is_admin:
        job = fetch_one("SELECT * FROM pipeline_jobs WHERE id = %s", (job_id,))
    else:
        job = fetch_one(
            "SELECT * FROM pipeline_jobs WHERE id = %s AND user_id = %s",
            (job_id, user_id)
        )

    if not job:
        return jsonify(brand_response(
            {"error": brand_error("Job not found.")}
        )), 404

    if job["status"] != "completed":
        return jsonify(brand_response(
            {"error": brand_error("Job must be completed before order serialization.")}
        )), 400

    # Parse query parameters
    vendor = request.args.get("vendor", "idt").lower()
    application_type = request.args.get("application_type", "standard_pcr")

    if vendor not in ("idt", "twist"):
        return jsonify(brand_response(
            {"error": brand_error("'vendor' must be 'idt' or 'twist'.")}
        )), 400

    # Gather primer/probe sequences from pipeline results
    step_results = fetch_all(
        """SELECT step_number, step_name, output_data
           FROM pipeline_results WHERE job_id = %s ORDER BY step_number""",
        (job_id,)
    )
    for sr in step_results:
        _decrypt_output(sr)

    # Extract sequences for compliance screening and primer pairs for serialization
    sequences_to_screen = []
    primer_pairs = []
    probes = []

    for step in step_results:
        output = step.get("output_data")
        if not output:
            continue
        if isinstance(output, str):
            try:
                output = json.loads(output)
            except (json.JSONDecodeError, TypeError):
                continue

        # Collect primer pairs from design steps
        if isinstance(output, dict):
            for pair in output.get("primer_pairs", []):
                normalised = _normalise_order_pair(pair, len(primer_pairs))
                primer_pairs.append(normalised)
                fwd_seq = normalised.get("forward", {}).get("sequence", "")
                rev_seq = normalised.get("reverse", {}).get("sequence", "")
                if fwd_seq:
                    sequences_to_screen.append(fwd_seq)
                if rev_seq:
                    sequences_to_screen.append(rev_seq)

            for pair in output.get("ranked_pairs", []) or output.get("top_pairs", []):
                normalised = _normalise_order_pair(pair, len(primer_pairs))
                primer_pairs.append(normalised)
                fwd_seq = normalised.get("forward", {}).get("sequence", "")
                rev_seq = normalised.get("reverse", {}).get("sequence", "")
                if fwd_seq:
                    sequences_to_screen.append(fwd_seq)
                if rev_seq:
                    sequences_to_screen.append(rev_seq)

            for probe in output.get("probes", []):
                normalised_probe = _normalise_order_probe(probe, len(probes))
                probes.append(normalised_probe)
                probe_seq = normalised_probe.get("sequence", "")
                if probe_seq:
                    sequences_to_screen.append(probe_seq)

            for probe in output.get("probe_candidates", []) or output.get("candidate_probes", []):
                normalised_probe = _normalise_order_probe(probe, len(probes))
                probes.append(normalised_probe)
                probe_seq = normalised_probe.get("sequence", "")
                if probe_seq:
                    sequences_to_screen.append(probe_seq)

            # Also screen amplicon sequences
            for amplicon in output.get("amplicons", []):
                amp_seq = amplicon.get("sequence", "")
                if amp_seq:
                    sequences_to_screen.append(amp_seq)

    if not sequences_to_screen:
        return jsonify(brand_response(
            {"error": brand_error("No primer/probe sequences found in job results.")}
        )), 400

    # Run IGSC compliance screening (Requirement 27.8)
    try:
        from .compliance import IGSCComplianceModule
        compliance_module = IGSCComplianceModule()
        compliance_result = compliance_module.screen(sequences_to_screen, job_id)
    except Exception as e:
        logger.error("Compliance screening failed for job %s: %s", job_id, e)
        return jsonify(brand_response(
            {"error": brand_error(f"Compliance screening failed: {str(e)}")}
        )), 500

    # Save compliance result to database
    try:
        execute(
            """INSERT INTO compliance_screening
               (job_id, status, sequences_screened, matched_organism, matched_gene,
                percent_identity, alignment_length)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (
                job_id,
                compliance_result.status,
                compliance_result.sequences_screened,
                compliance_result.matched_organism,
                compliance_result.matched_gene,
                compliance_result.percent_identity,
                compliance_result.alignment_length,
            )
        )
    except Exception as e:
        logger.warning("Failed to save compliance result: %s", e)

    # Check compliance status — must be biosecurity_cleared
    if compliance_result.status != "biosecurity_cleared":
        return jsonify(brand_response({
            "error": brand_error(
                f"Order blocked — compliance status: {compliance_result.status}"
            ),
            "compliance_status": compliance_result.status,
            "matched_organism": compliance_result.matched_organism,
            "matched_gene": compliance_result.matched_gene,
        })), 403

    # Serialize order (Requirement 28.6)
    try:
        from .order_serializer import OrderSerializer, ValidatedDesign

        design = ValidatedDesign(
            job_id=job_id,
            compliance_status=compliance_result.status,
            primer_pairs=primer_pairs,
            probes=probes,
            application_type=application_type,
        )

        serializer = OrderSerializer()
        if vendor == "idt":
            order_payload = serializer.serialize_idt(design)
        else:
            order_payload = serializer.serialize_twist(design)

    except ValueError as e:
        return jsonify(brand_response(
            {"error": brand_error(str(e))}
        )), 403
    except Exception as e:
        logger.error("Order serialization failed for job %s: %s", job_id, e)
        return jsonify(brand_response(
            {"error": brand_error(f"Order serialization failed: {str(e)}")}
        )), 500

    # Save order payload to database
    try:
        execute(
            """INSERT INTO order_payloads
               (job_id, vendor, payload, order_id, oligo_count, scale)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (
                job_id,
                vendor,
                json.dumps(order_payload),
                order_payload.get("order_id", ""),
                order_payload.get("oligo_count", 0),
                order_payload.get("scale", ""),
            )
        )
    except Exception as e:
        logger.warning("Failed to save order payload: %s", e)

    return jsonify(brand_response({
        "order": order_payload,
        "compliance_status": compliance_result.status,
        "job_id": job_id,
        "vendor": vendor,
    })), 200


@pipeline_bp.route("/api/pipeline/compliance/<job_id>", methods=["GET"])
@_route_error_handler
@require_auth
def get_compliance_result(job_id: str):
    """
    Get the latest compliance screening result for a pipeline job.

    Returns the most recent compliance_screening record for the given job_id.
    """
    user_id = g.user.get("user_id")
    is_admin = g.user.get("role") == "admin"

    # Verify job ownership
    if is_admin:
        job = fetch_one("SELECT id FROM pipeline_jobs WHERE id = %s", (job_id,))
    else:
        job = fetch_one(
            "SELECT id FROM pipeline_jobs WHERE id = %s AND user_id = %s",
            (job_id, user_id)
        )

    if not job:
        return jsonify(brand_response(
            {"error": brand_error("Job not found.")}
        )), 404

    # Fetch latest compliance record
    compliance = fetch_one(
        """SELECT status, sequences_screened, matched_organism, matched_gene,
                  percent_identity, alignment_length, screened_at
           FROM compliance_screening WHERE job_id = %s
           ORDER BY screened_at DESC LIMIT 1""",
        (job_id,)
    )

    if not compliance:
        return jsonify(brand_response({
            "job_id": job_id,
            "compliance": None,
            "message": "No compliance screening has been performed for this job.",
        })), 200

    return jsonify(brand_response({
        "job_id": job_id,
        "compliance": {
            "status": compliance["status"],
            "sequences_screened": compliance["sequences_screened"],
            "matched_organism": compliance.get("matched_organism"),
            "matched_gene": compliance.get("matched_gene"),
            "percent_identity": compliance.get("percent_identity"),
            "alignment_length": compliance.get("alignment_length"),
            "screened_at": str(compliance["screened_at"]) if compliance.get("screened_at") else None,
        },
    })), 200

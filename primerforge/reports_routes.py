#!/usr/bin/env python3
"""
VigyanLLM Reports, Academic Claims & Feedback Routes
======================================================
Endpoints:
  POST /api/reports/save              — Save a completed pipeline result as a named report
  GET  /api/reports/history           — Get user's full report history (real DB data only)
  GET  /api/reports/<id>/download     — Download a specific report as JSON
  GET  /api/reports/<id>/csv          — Download a specific report as CSV
  DELETE /api/reports/<id>            — Delete a report
  POST /api/academic/claim            — Submit academic free-access claim
  GET  /api/academic/status           — Check academic claim status
  POST /api/feedback                  — Submit tool feedback
  POST /api/auth/check-ip             — IP uniqueness enforcement (called on login/register)
"""

import csv
import io
import json
import logging
import os
import secrets
import hmac
import hashlib
import time
import base64
from datetime import datetime, timezone
from pathlib import Path
from flask import Blueprint, request, jsonify, g, make_response
from werkzeug.utils import secure_filename

from .pg_auth import require_auth, require_admin
from .database import fetch_one, fetch_all, execute, execute_returning

logger = logging.getLogger("primerforge.reports")

reports_bp = Blueprint("reports", __name__)

# ── Secure Download Tokens ─────────────────────────────────────────────────
# Short-lived (5 min), single-use, HMAC-signed tokens for report downloads.
# Replaces any prior pattern of embedding long-lived bearer tokens in URLs.

_DOWNLOAD_TOKEN_EXPIRY = 300  # 5 minutes
_DOWNLOAD_TOKEN_SECRET = os.environ.get("PRIMERFORGE_SECRET", "")
_USED_DOWNLOAD_TOKENS = set()


def _generate_download_token(report_id: int, user_id: int) -> str:
    """Generate a short-lived, single-use download token."""
    payload = json.dumps({
        "report_id": report_id,
        "user_id": user_id,
        "iat": int(time.time()),
        "exp": int(time.time() + _DOWNLOAD_TOKEN_EXPIRY),
        "purpose": "download",
    })
    sig = hmac.new(_DOWNLOAD_TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=") + "." + sig


def _verify_download_token(token: str, report_id: int, user_id: int) -> bool:
    """Verify a download token. Returns True if valid, fresh, and single-use."""
    if not token or not isinstance(token, str):
        return False
    if token in _USED_DOWNLOAD_TOKENS:
        return False
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return False
        payload_b64, sig = parts
        payload = base64.urlsafe_b64decode(payload_b64 + "==").decode()
        expected_sig = hmac.new(_DOWNLOAD_TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return False
        data = json.loads(payload)
        if data.get("purpose") != "download":
            return False
        if data.get("report_id") != report_id:
            return False
        if data.get("user_id") != user_id:
            return False
        if data.get("exp", 0) < time.time():
            return False
        _USED_DOWNLOAD_TOKENS.add(token)
        if len(_USED_DOWNLOAD_TOKENS) > 10000:
            _prune_used_tokens()
        return True
    except Exception:
        return False


def _prune_used_tokens():
    """Remove expired tokens from the used-token set periodically."""
    now = time.time()
    to_remove = set()
    for t in _USED_DOWNLOAD_TOKENS:
        try:
            parts = t.split(".")
            if len(parts) == 2:
                payload = json.loads(base64.urlsafe_b64decode(parts[0] + "==").decode())
                if payload.get("exp", 0) < now:
                    to_remove.add(t)
        except Exception:
            to_remove.add(t)
    _USED_DOWNLOAD_TOKENS.difference_update(to_remove)


# ── IP enforcement: stored in login_logs, checked at auth time ─────────────

def get_registered_ip(user_id: int) -> str:
    """
    Return the IP address this account first registered/logged in from.
    Uses the first successful login_log entry.
    """
    try:
        row = fetch_one(
            """SELECT ip_address::text FROM login_logs
               WHERE user_id = %s AND result = 'success'
               ORDER BY logged_at ASC LIMIT 1""",
            (user_id,)
        )
        return row["ip_address"] if row else None
    except Exception:
        return None


def check_ip_allowed(user_id: int, current_ip: str, role: str = "user") -> dict:
    """
    Check if the current IP is allowed for this account.
    Admin accounts are exempt. First login registers the IP.
    Returns {allowed: bool, registered_ip: str|None, message: str}
    """
    if role == "admin":
        return {"allowed": True, "registered_ip": None, "message": "Admin exempt"}

    registered_ip = get_registered_ip(user_id)

    if not registered_ip:
        # First login — no restriction yet
        return {"allowed": True, "registered_ip": None, "message": "First login"}

    # Compare IPs (strip ::ffff: IPv4-mapped IPv6 prefix and CIDR suffix from PostgreSQL INET type)
    def normalize(ip: str) -> str:
        if not ip:
            return ""
        # PostgreSQL INET returns values like "127.0.0.1/32" — strip subnet suffix
        ip = ip.split("/")[0].strip()
        # Strip IPv4-mapped IPv6
        if ip.startswith("::ffff:"):
            ip = ip[7:]
        # Treat IPv6 loopback same as IPv4 loopback
        if ip in ("::1", "127.0.0.1", "localhost"):
            return "127.0.0.1"
        return ip

    if normalize(registered_ip) == normalize(current_ip):
        return {"allowed": True, "registered_ip": registered_ip, "message": "IP match"}

    return {
        "allowed": False,
        "registered_ip": registered_ip,
        "message": (
            f"This account is registered to a different IP address. "
            f"For security, each account can only be accessed from the IP it was registered on. "
            f"If you've changed networks, contact support."
        )
    }


# ── Public Stats ────────────────────────────────────────────────────────────

@reports_bp.route("/api/stats/public", methods=["GET"])
def public_stats():
    """Public platform stats for the homepage counter."""
    row1 = fetch_one("SELECT COUNT(*) as c FROM users")
    row2 = fetch_one("SELECT COALESCE(SUM(balance), 0) as c FROM token_balances")
    row3 = fetch_one("SELECT COUNT(*) as c FROM user_reports")
    total_users = row1["c"] if row1 else 0
    total_designs = row2["c"] if row2 else 0
    total_reports = row3["c"] if row3 else 0
    row4 = fetch_one(
        "SELECT COUNT(*) as c FROM users WHERE last_active_at > NOW() - INTERVAL '1 day'"
    )
    active_today = row4["c"] if row4 else 0
    return jsonify({
        "total_users": total_users,
        "total_designs": total_designs,
        "active_today": active_today,
        "total_reports": total_reports,
    }), 200


# ── Report History ─────────────────────────────────────────────────────────

@reports_bp.route("/api/reports/save", methods=["POST"])
@require_auth
def save_report():
    """Save a pipeline result as a named report in the user's history."""
    data = request.get_json(silent=True) or {}
    user_id = g.user["user_id"]

    job_id = data.get("job_id")
    if not job_id:
        return jsonify({"error": "job_id is required"}), 400

    # Verify the job belongs to this user
    job = fetch_one(
        "SELECT id, input_params FROM pipeline_jobs WHERE id = %s AND user_id = %s",
        (job_id, user_id)
    )
    if not job:
        return jsonify({"error": "Job not found or access denied"}), 404

    # Get step 19 (ranking) output for top pair data
    ranking_step = fetch_one(
        """SELECT output_data FROM pipeline_results
           WHERE job_id = %s AND step_number = 19 LIMIT 1""",
        (job_id,)
    )

    top_score = None
    top_forward = None
    top_reverse = None
    amplicon_size = None
    pair_count = 0

    if ranking_step and ranking_step.get("output_data"):
        output = ranking_step["output_data"]
        if isinstance(output, str):
            try:
                output = json.loads(output)
            except Exception:
                output = {}

        pairs = output.get("ranked_pairs") or output.get("top_pairs") or []
        pair_count = len(pairs)
        if pairs:
            top = pairs[0]
            top_score = top.get("score") or (
                max(0, 100 - top["total_penalty"]) if top.get("total_penalty") is not None else None
            )
            fwd = top.get("forward") or {}
            rev = top.get("reverse") or {}
            top_forward = (fwd if isinstance(fwd, str) else fwd.get("sequence", ""))[:80]
            top_reverse = (rev if isinstance(rev, str) else rev.get("sequence", ""))[:80]
            amplicon_size = top.get("amplicon_size") or top.get("product_size")

    input_params = job.get("input_params") or {}
    if isinstance(input_params, str):
        try:
            input_params = json.loads(input_params)
        except Exception:
            input_params = {}

    gene_input = data.get("gene_input") or input_params.get("accession") or ""
    seq_len = len(input_params.get("sequence", "")) or data.get("sequence_length") or 0
    title = data.get("title") or (
        f"{gene_input or 'Design'} — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
    )
    pipeline_mode = input_params.get("mode", "full")
    design_mode = input_params.get("design_mode", "standard")

    # Store the full result payload (all steps) for complete download later
    all_steps = fetch_all(
        """SELECT step_number, step_name, status, output_data, duration_ms
           FROM pipeline_results WHERE job_id = %s ORDER BY step_number""",
        (job_id,)
    )
    full_result = {
        "job_id": str(job_id),
        "input_params": input_params,
        "steps": [
            {
                "step_number": s["step_number"],
                "step_name": s["step_name"],
                "status": s["status"],
                "duration_ms": s["duration_ms"],
                "output_data": s["output_data"],
            }
            for s in all_steps
        ],
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }

    report = execute_returning(
        """INSERT INTO user_reports
           (user_id, job_id, title, gene_input, sequence_length, pair_count,
            top_score, top_forward, top_reverse, amplicon_size,
            pipeline_mode, design_mode, full_result)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           RETURNING id, created_at""",
        (
            user_id, job_id, title, gene_input, seq_len, pair_count,
            top_score, top_forward, top_reverse, amplicon_size,
            pipeline_mode, design_mode, json.dumps(full_result)
        )
    )

    return jsonify({
        "success": True,
        "report_id": report["id"],
        "title": title,
        "created_at": str(report["created_at"]),
    }), 201


@reports_bp.route("/api/reports/history", methods=["GET"])
@require_auth
def get_history():
    """Return the user's full report history from the database. No mock data."""
    user_id = g.user["user_id"]
    limit = min(int(request.args.get("limit", 50)), 100)
    offset = int(request.args.get("offset", 0))

    reports = fetch_all(
        """SELECT id, job_id, title, gene_input, sequence_length, pair_count,
                  top_score, top_forward, top_reverse, amplicon_size,
                  pipeline_mode, design_mode, created_at
           FROM user_reports
           WHERE user_id = %s
           ORDER BY created_at DESC
           LIMIT %s OFFSET %s""",
        (user_id, limit, offset)
    )

    total = fetch_one(
        "SELECT COUNT(*) AS cnt FROM user_reports WHERE user_id = %s",
        (user_id,)
    )

    return jsonify({
        "reports": [
            {
                "id": r["id"],
                "job_id": str(r["job_id"]) if r.get("job_id") else None,
                "title": r["title"],
                "gene_input": r["gene_input"],
                "sequence_length": r["sequence_length"],
                "pair_count": r["pair_count"],
                "top_score": float(r["top_score"]) if r.get("top_score") is not None else None,
                "top_forward": r["top_forward"],
                "top_reverse": r["top_reverse"],
                "amplicon_size": r["amplicon_size"],
                "pipeline_mode": r["pipeline_mode"],
                "design_mode": r["design_mode"],
                "created_at": str(r["created_at"]),
            }
            for r in reports
        ],
        "total": total["cnt"] if total else 0,
        "limit": limit,
        "offset": offset,
    }), 200


@reports_bp.route("/api/reports/<int:report_id>/request-download", methods=["POST"])
@require_auth
def request_download_token(report_id: int):
    """Generate a short-lived, single-use download token for this report.

    Returns the token which can be used as ?token=<value> on the download
    endpoints. Token expires in 5 minutes and can only be used once.
    This replaces any pattern of embedding long-lived bearer tokens in URLs.
    """
    user_id = g.user["user_id"]

    report = fetch_one(
        "SELECT id FROM user_reports WHERE id = %s AND user_id = %s",
        (report_id, user_id)
    )
    if not report:
        return jsonify({"error": "Report not found"}), 404

    token = _generate_download_token(report_id, user_id)
    return jsonify({
        "token": token,
        "expires_in_seconds": _DOWNLOAD_TOKEN_EXPIRY,
        "download_urls": {
            "json": f"/api/reports/{report_id}/download?token={token}",
            "csv": f"/api/reports/{report_id}/csv?token={token}",
        },
    }), 200


def _resolve_download_user(report_id: int):
    """Resolve (user_id, error_response) for download access.

    Supports three authentication modes:
    1. Standard auth (Authorization header or pf_token cookie).
    2. Short-lived download token (?token= query parameter) — secure share flow.
    3. JWT auth token (?token= query parameter) — direct download from frontend.
    """
    from .pg_auth import verify_token, get_current_user

    token_param = request.args.get("token", "")
    if token_param:
        user = get_current_user()
        if not user:
            return None, (jsonify({"error": "Authentication required", "code": "AUTH_REQUIRED"}), 401)
        user_id = user.get("user_id")
        if not user_id:
            return None, (jsonify({"error": "Authentication required", "code": "AUTH_REQUIRED"}), 401)
        # First try as short-lived download token
        if _verify_download_token(token_param, report_id, user_id):
            return user_id, None
        # Fallback: try as JWT auth token (direct download from frontend)
        jwt_user = verify_token(token_param)
        if jwt_user and jwt_user.get("user_id") == user_id:
            return user_id, None
        return None, (jsonify({"error": "Invalid or expired download token", "code": "BAD_TOKEN"}), 403)

    user = get_current_user()
    if not user:
        return None, (jsonify({"error": "Authentication required", "code": "AUTH_REQUIRED"}), 401)
    return user.get("user_id"), None


@reports_bp.route("/api/reports/<int:report_id>/download", methods=["GET"])
def download_report_json(report_id: int):
    """Download a report as full JSON including all pipeline step outputs.

    Accepts either standard auth (Authorization header) or a short-lived
    download token (?token= query parameter).
    """
    user_id, error = _resolve_download_user(report_id)
    if error:
        return error

    report = fetch_one(
        "SELECT * FROM user_reports WHERE id = %s AND user_id = %s",
        (report_id, user_id)
    )
    if not report:
        return jsonify({"error": "Report not found"}), 404

    full_result = report.get("full_result") or {}
    if isinstance(full_result, str):
        try:
            full_result = json.loads(full_result)
        except Exception:
            full_result = {}

    payload = {
        "vigyanllm_report": True,
        "report_id": report["id"],
        "title": report["title"],
        "gene_input": report["gene_input"],
        "sequence_length": report["sequence_length"],
        "pair_count": report["pair_count"],
        "top_score": float(report["top_score"]) if report.get("top_score") is not None else None,
        "top_forward": report["top_forward"],
        "top_reverse": report["top_reverse"],
        "amplicon_size": report["amplicon_size"],
        "pipeline_mode": report["pipeline_mode"],
        "design_mode": report["design_mode"],
        "created_at": str(report["created_at"]),
        "full_pipeline_result": full_result,
    }

    safe_title = "".join(c if c.isalnum() or c in "-_ " else "_" for c in (report["title"] or "report"))[:50]
    filename = f"vigyanllm_{safe_title}_{report['id']}.json"

    response = make_response(json.dumps(payload, indent=2, default=str))
    response.headers["Content-Type"] = "application/json"
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@reports_bp.route("/api/reports/<int:report_id>/csv", methods=["GET"])
def download_report_csv(report_id: int):
    """Download top primer pairs from a report as CSV.

    Accepts either standard auth (Authorization header) or a short-lived
    download token (?token= query parameter).
    """
    user_id, error = _resolve_download_user(report_id)
    if error:
        return error

    report = fetch_one(
        "SELECT * FROM user_reports WHERE id = %s AND user_id = %s",
        (report_id, user_id)
    )
    if not report:
        return jsonify({"error": "Report not found"}), 404

    full_result = report.get("full_result") or {}
    if isinstance(full_result, str):
        try:
            full_result = json.loads(full_result)
        except Exception:
            full_result = {}

    # Extract pairs from step 19 output
    pairs = []
    for step in full_result.get("steps", []):
        if step.get("step_number") == 19:
            output = step.get("output_data") or {}
            if isinstance(output, str):
                try:
                    output = json.loads(output)
                except Exception:
                    output = {}
            pairs = output.get("ranked_pairs") or output.get("top_pairs") or []
            break

    output_buf = io.StringIO()
    writer = csv.writer(output_buf)

    writer.writerow([
        "Rank", "Pair_ID", "Score", "Status",
        "Forward_Sequence", "Forward_Tm", "Forward_GC",
        "Reverse_Sequence", "Reverse_Tm", "Reverse_GC",
        "Amplicon_Size", "Delta_Tm", "Cross_Dimer_dG",
        "Total_Penalty", "Design_Date", "Job_ID"
    ])

    for i, p in enumerate(pairs):
        fwd = p.get("forward") or {}
        rev = p.get("reverse") or {}
        if isinstance(fwd, str):
            fwd = {"sequence": fwd, "tm": p.get("forward_tm", ""), "gc": ""}
        if isinstance(rev, str):
            rev = {"sequence": rev, "tm": p.get("reverse_tm", ""), "gc": ""}

        writer.writerow([
            p.get("rank", i + 1),
            p.get("pair_id", i + 1),
            p.get("score", ""),
            p.get("overall_status", ""),
            fwd.get("sequence", ""),
            fwd.get("tm", "") or fwd.get("tm_nn", ""),
            fwd.get("gc", ""),
            rev.get("sequence", ""),
            rev.get("tm", "") or rev.get("tm_nn", ""),
            rev.get("gc", ""),
            p.get("amplicon_size") or p.get("product_size", ""),
            p.get("delta_tm_nn") or p.get("delta_tm", ""),
            p.get("cross_dimer_dg", ""),
            p.get("total_penalty", ""),
            str(report["created_at"]),
            str(report.get("job_id") or ""),
        ])

    safe_title = "".join(c if c.isalnum() or c in "-_ " else "_" for c in (report["title"] or "report"))[:50]
    filename = f"vigyanllm_{safe_title}_{report['id']}.csv"

    response = make_response(output_buf.getvalue())
    response.headers["Content-Type"] = "text/csv"
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@reports_bp.route("/api/reports/<int:report_id>", methods=["DELETE"])
@require_auth
def delete_report(report_id: int):
    """Delete a report from the user's history."""
    user_id = g.user["user_id"]
    rowcount = execute(
        "DELETE FROM user_reports WHERE id = %s AND user_id = %s",
        (report_id, user_id)
    )
    if rowcount == 0:
        return jsonify({"error": "Report not found"}), 404
    return jsonify({"success": True, "message": "Report deleted"}), 200


# ── Academic Access ────────────────────────────────────────────────────────

# Blocked free-mail domains — academic offer requires institutional email
_FREE_MAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "yahoo.in", "yahoo.co.in",
    "hotmail.com", "outlook.com", "live.com", "msn.com",
    "rediffmail.com", "icloud.com", "proton.me", "protonmail.com",
    "yopmail.com", "mailinator.com", "guerrillamail.com",
    "sharklasers.com", "guerrillamailblock.com", "grr.la",
    "aol.com", "me.com", "mac.com",
}


def _is_academic_email(email: str) -> bool:
    """
    Return True only if the email belongs to an institutional/academic domain.
    Rejects all free personal mail providers.
    """
    if not email or "@" not in email:
        return False
    domain = email.rsplit("@", 1)[1].lower().strip()
    # Reject known free-mail domains
    if domain in _FREE_MAIL_DOMAINS:
        return False
    # Reject subdomains of free-mail providers
    for free in _FREE_MAIL_DOMAINS:
        if domain.endswith("." + free):
            return False
    # Accept: must have at least one dot (e.g. iitd.ac.in, university.edu, aiims.edu)
    if "." not in domain:
        return False
    return True


_UPLOAD_DIR = Path(os.environ.get("ACADEMIC_UPLOAD_DIR", "/var/log/vigyan/uploads"))
_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}


@reports_bp.route("/api/academic/upload-document", methods=["POST"])
@require_auth
def upload_academic_document():
    """Upload a university document as proof of academic affiliation.

    Returns a UUID file reference instead of the raw filesystem path to
    prevent information disclosure of the server directory layout.
    """
    user_id = g.user["user_id"]
    if "document" not in request.files:
        return jsonify({"error": "No document file provided."}), 400
    file = request.files["document"]
    if not file.filename:
        return jsonify({"error": "Empty filename."}), 400
    ext = Path(file.filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        return jsonify({"error": f"Unsupported file type. Allowed: {', '.join(_ALLOWED_EXTENSIONS)}"}), 400
    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_uuid = secrets.token_hex(16)
    safe = secure_filename(f"{user_id}_{file_uuid}{ext}")
    path = _UPLOAD_DIR / safe
    file.save(str(path))
    # Return only a UUID reference — never expose the server filesystem path
    return jsonify({"file_ref": file_uuid, "filename": safe}), 200


@reports_bp.route("/api/academic/claim", methods=["POST"])
@require_auth
def claim_academic():
    """
    Submit an academic free-access claim.
    Two proof methods:
      - email: provide institutional email -> auto-approved, 10 tokens
      - document: upload proof document -> pending, admin reviews, grants tokens
    """
    user_id = g.user["user_id"]
    data = request.get_json(silent=True) or {}

    institution = (data.get("institution") or "").strip()[:256]
    department = (data.get("department") or "").strip()[:256]
    use_case = (data.get("use_case") or "").strip()[:2000]
    email_edu = (data.get("email_edu") or "").strip().lower()[:320]
    proof_method = (data.get("proof_method") or "email").strip()
    document_path = (data.get("document_path") or data.get("file_ref") or "").strip()

    if not institution:
        return jsonify({"error": "Institution name is required."}), 400

    # Check for existing claim
    existing = fetch_one(
        "SELECT id, status, tokens_granted FROM academic_claims WHERE user_id = %s",
        (user_id,)
    )
    if existing:
        return jsonify({
            "success": False,
            "already_claimed": True,
            "status": existing["status"],
            "tokens_granted": existing["tokens_granted"],
            "message": f"You already submitted an academic claim (status: {existing['status']}).",
        }), 200

    if proof_method == "document":
        if not document_path:
            return jsonify({"error": "Document proof required. Upload a document first via /api/academic/upload-document."}), 400
        status, tokens = "pending", 0
    else:
        if not email_edu:
            return jsonify({"error": "Institutional email is required for email proof."}), 400
        if not _is_academic_email(email_edu):
            return jsonify({
                "error": (
                    "Personal email addresses (Gmail, Yahoo, Hotmail, etc.) are not accepted. "
                    "Please provide your official university or institutional email "
                    "(e.g. yourname@iitd.ac.in, yourname@aiims.edu)."
                ),
                "code": "NON_ACADEMIC_EMAIL",
            }), 400
        status, tokens = "approved", 10

    claim = execute_returning(
        """INSERT INTO academic_claims
           (user_id, institution, department, use_case, email_edu, document_path, proof_method, status, tokens_granted)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
           RETURNING id, created_at""",
        (user_id, institution, department, use_case, email_edu, document_path, proof_method, status, tokens)
    )

    if tokens > 0:
        execute(
            """UPDATE token_balances
               SET balance = balance + %s, total_purchased = total_purchased + %s
               WHERE user_id = %s""",
            (tokens, tokens, user_id)
        )

    logger.info("Academic claim %s — user %s, institution: %s, method: %s, tokens: %d",
                status, user_id, institution, proof_method, tokens)

    return jsonify({
        "success": True,
        "claim_id": claim["id"],
        "tokens_granted": tokens,
        "status": status,
        "message": (
            "Academic access approved! 10 free design runs have been credited."
            if status == "approved" else
            "Your academic claim has been submitted with document proof. "
            "An administrator will review it shortly."
        ),
    }), 201 if status == "approved" else 202


@reports_bp.route("/api/academic/status", methods=["GET"])
@require_auth
def academic_status():
    """Check if the user has submitted an academic claim."""
    user_id = g.user["user_id"]
    claim = fetch_one(
        """SELECT id, institution, status, tokens_granted, created_at
           FROM academic_claims WHERE user_id = %s""",
        (user_id,)
    )
    if not claim:
        return jsonify({"claimed": False}), 200
    return jsonify({
        "claimed": True,
        "status": claim["status"],
        "institution": claim["institution"],
        "tokens_granted": claim["tokens_granted"],
        "created_at": str(claim["created_at"]),
    }), 200


# ── Referral Program ───────────────────────────────────────────────────────

import secrets as _secrets


def _generate_referral_code(user_id: int) -> str:
    """Generate a unique 10-character referral code."""
    return f"VL{user_id:04d}{_secrets.token_urlsafe(4).upper()[:6]}"


@reports_bp.route("/api/referral/code", methods=["GET"])
@require_auth
def get_referral_code():
    """
    Get or create the user's referral code.
    Each user has one permanent referral code.
    """
    user_id = g.user["user_id"]

    # Check for existing code
    existing = fetch_one(
        "SELECT referral_code, status FROM referrals WHERE referrer_id = %s AND referred_id IS NULL LIMIT 1",
        (user_id,)
    )
    if existing:
        code = existing["referral_code"]
    else:
        # Create a new referral entry for this user (pending = not yet referred anyone)
        code = _generate_referral_code(user_id)
        # Ensure uniqueness — retry once if collision
        try:
            execute_returning(
                """INSERT INTO referrals (referrer_id, referral_code, status)
                   VALUES (%s, %s, 'active') RETURNING id""",
                (user_id, code)
            )
        except Exception:
            code = _generate_referral_code(user_id) + _secrets.token_hex(2).upper()[:2]
            execute_returning(
                """INSERT INTO referrals (referrer_id, referral_code, status)
                   VALUES (%s, %s, 'active') RETURNING id""",
                (user_id, code)
            )

    # Get referral stats
    stats = fetch_one(
        """SELECT
             COUNT(*) FILTER (WHERE referred_id IS NOT NULL AND status='completed') AS successful,
             COUNT(*) FILTER (WHERE referred_id IS NOT NULL) AS total,
             COALESCE(SUM(tokens_awarded) FILTER (WHERE status='completed'), 0) AS tokens_earned
           FROM referrals
           WHERE referrer_id = %s""",
        (user_id,)
    )

    return jsonify({
        "referral_code": code,
        "referral_url": f"https://vigyanllm.in/r/{code}",
        "tokens_per_referral": 5,
        "stats": {
            "successful_referrals": stats["successful"] if stats else 0,
            "total_referred": stats["total"] if stats else 0,
            "tokens_earned": int(stats["tokens_earned"]) if stats else 0,
        },
    }), 200


@reports_bp.route("/api/referral/apply", methods=["POST"])
def apply_referral():
    """
    Apply a referral code during registration.
    Called right after a new user registers with ?ref=CODE in URL.
    Awards 5 tokens to the referrer on first successful design.
    Public endpoint — no auth needed (called from registration flow).
    """
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip().upper()
    new_user_email = (data.get("email") or "").strip().lower()

    if not code or not new_user_email:
        return jsonify({"error": "code and email are required"}), 400

    # Find the referral record
    ref = fetch_one(
        """SELECT r.id, r.referrer_id, r.status
           FROM referrals r
           WHERE r.referral_code = %s AND r.referred_id IS NULL AND r.status = 'active'
           LIMIT 1""",
        (code,)
    )
    if not ref:
        return jsonify({"valid": False, "message": "Referral code not found or already used"}), 200

    # Find the new user
    new_user = fetch_one("SELECT id FROM users WHERE email = %s", (new_user_email,))
    if not new_user:
        return jsonify({"valid": False, "message": "User not found"}), 200

    new_user_id = new_user["id"]
    referrer_id = ref["referrer_id"]

    # Prevent self-referral
    if new_user_id == referrer_id:
        return jsonify({"valid": False, "message": "Cannot refer yourself"}), 200

    # Link referred user to the referral record
    execute(
        """UPDATE referrals
           SET referred_id = %s, referred_email = %s, status = 'pending_design',
               completed_at = NULL
           WHERE id = %s""",
        (new_user_id, new_user_email, ref["id"])
    )

    return jsonify({
        "valid": True,
        "message": "Referral code applied! Your referrer will receive 5 bonus runs when you complete your first design.",
    }), 200


@reports_bp.route("/api/referral/complete", methods=["POST"])
@require_auth
def complete_referral():
    """
    Called internally after a referred user completes their first pipeline run.
    Awards 5 tokens to the referrer.
    """
    user_id = g.user["user_id"]

    # Find a pending referral where this user is the referred person
    ref = fetch_one(
        """SELECT id, referrer_id FROM referrals
           WHERE referred_id = %s AND status = 'pending_design'
           LIMIT 1""",
        (user_id,)
    )
    if not ref:
        return jsonify({"rewarded": False}), 200

    # Award 5 tokens to referrer
    execute(
        """UPDATE token_balances
           SET balance = balance + 5,
               total_purchased = total_purchased + 5
           WHERE user_id = %s""",
        (ref["referrer_id"],)
    )

    # Mark referral as completed
    execute(
        """UPDATE referrals
           SET status = 'completed', tokens_awarded = 5, completed_at = NOW()
           WHERE id = %s""",
        (ref["id"],)
    )

    logger.info("Referral completed — referrer_id=%s awarded 5 tokens (referred_id=%s)",
                ref["referrer_id"], user_id)

    return jsonify({"rewarded": True, "referrer_tokens_awarded": 5}), 200


# ── Admin: Academic Claims Review ──────────────────────────────────────────

@reports_bp.route("/api/admin/academic/list", methods=["GET"])
@require_admin
def admin_academic_list():
    """List pending academic claims for admin review."""
    claims = fetch_all(
        """SELECT ac.id, ac.user_id, u.email, u.full_name, ac.institution, ac.department,
                  ac.use_case, ac.email_edu, ac.document_path, ac.proof_method,
                  ac.status, ac.tokens_granted, ac.created_at
           FROM academic_claims ac
           JOIN users u ON u.id = ac.user_id
           ORDER BY ac.created_at DESC
           LIMIT 100"""
    )
    return jsonify({"claims": claims}), 200


@reports_bp.route("/api/admin/academic/review", methods=["POST"])
@require_admin
def admin_academic_review():
    """Approve or reject a pending academic claim. Grants tokens on approval."""
    data = request.get_json(silent=True) or {}
    claim_id = data.get("claim_id")
    action = (data.get("action") or "").strip().lower()

    if not claim_id or action not in ("approve", "reject"):
        return jsonify({"error": "claim_id and action (approve|reject) are required"}), 400

    claim = fetch_one(
        "SELECT id, user_id, status FROM academic_claims WHERE id = %s",
        (claim_id,)
    )
    if not claim:
        return jsonify({"error": "Claim not found"}), 404
    if claim["status"] != "pending":
        return jsonify({"error": f"Claim is already {claim['status']}"}), 400

    admin_id = g.user["user_id"]

    if action == "approve":
        tokens = 10
        execute(
            """UPDATE academic_claims
               SET status = 'approved', tokens_granted = %s, reviewed_by = %s, reviewed_at = NOW()
               WHERE id = %s""",
            (tokens, admin_id, claim_id)
        )
        execute(
            """UPDATE token_balances
               SET balance = balance + %s, total_purchased = total_purchased + %s
               WHERE user_id = %s""",
            (tokens, tokens, claim["user_id"])
        )
        logger.info("Academic claim %s approved by admin %s — %d tokens granted to user %s",
                    claim_id, admin_id, tokens, claim["user_id"])
        return jsonify({"success": True, "status": "approved", "tokens_granted": tokens}), 200
    else:
        execute(
            """UPDATE academic_claims
               SET status = 'rejected', reviewed_by = %s, reviewed_at = NOW()
               WHERE id = %s""",
            (admin_id, claim_id)
        )
        logger.info("Academic claim %s rejected by admin %s", claim_id, admin_id)
        return jsonify({"success": True, "status": "rejected"}), 200


# ── Feedback ───────────────────────────────────────────────────────────────

@reports_bp.route("/api/feedback", methods=["POST"])
def submit_feedback():
    """Submit tool feedback. Works for both authenticated and anonymous users."""
    data = request.get_json(silent=True) or {}

    message = (data.get("message") or "").strip()[:5000]
    rating = data.get("rating")
    context = (data.get("context") or "general")[:64]
    email = (data.get("email") or "").strip().lower()[:320]

    if not message:
        return jsonify({"error": "Feedback message is required"}), 400

    if rating is not None:
        try:
            rating = int(rating)
            if not (1 <= rating <= 5):
                rating = None
        except (TypeError, ValueError):
            rating = None

    # Get user_id if authenticated
    user_id = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        from .pg_auth import verify_token
        user_data = verify_token(auth_header[7:])
        if user_data:
            user_id = user_data.get("user_id")
            if not email:
                user = fetch_one("SELECT email FROM users WHERE id = %s", (user_id,))
                if user:
                    email = user["email"]

    execute(
        """INSERT INTO feedback_submissions (user_id, email, rating, message, context)
           VALUES (%s, %s, %s, %s, %s)""",
        (user_id, email or None, rating, message, context)
    )

    return jsonify({
        "success": True,
        "message": "Thank you for your feedback! It helps us improve VigyanLLM.",
    }), 201

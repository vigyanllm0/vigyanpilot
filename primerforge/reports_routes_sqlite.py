"""
VigyanLLM Reports, Academic Claims & Feedback Routes (SQLite version)
=======================================================================
Endpoints:
  POST /api/reports/save              — Save a completed pipeline result as a named report
  GET  /api/reports/history           — Get user's full report history
  GET  /api/reports/<id>/download     — Download a specific report as JSON
  GET  /api/reports/<id>/csv          — Download a specific report as CSV
  DELETE /api/reports/<id>            — Delete a report
  POST /api/academic/claim            — Submit academic free-access claim
  GET  /api/academic/status           — Check academic claim status
  POST /api/feedback                  — Submit tool feedback
  POST /api/referral/code             — Get/create referral code
  POST /api/referral/apply            — Apply referral code during registration
  POST /api/referral/complete         — Award tokens on first completed design
  GET  /api/stats/public              — Public stats for homepage counter
"""

import csv
import io
import json
import os
import re
import secrets
import time
import logging
from flask import Blueprint, request, jsonify, g, make_response

from .auth import get_db, get_current_user, require_auth

logger = logging.getLogger("primerforge.reports")

reports_bp = Blueprint("reports_sqlite", __name__)

_FREE_MAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "yahoo.in", "yahoo.co.in",
    "hotmail.com", "outlook.com", "live.com", "msn.com",
    "rediffmail.com", "icloud.com", "proton.me", "protonmail.com",
    "yopmail.com", "mailinator.com", "guerrillamail.com",
    "sharklasers.com", "guerrillamailblock.com", "grr.la",
    "aol.com", "me.com", "mac.com",
}

ACADEMIC_TOKENS = int(os.environ.get("ACADEMIC_FREE_RUNS", "10"))
REFERRAL_TOKENS = int(os.environ.get("REFERRAL_REWARD_RUNS", "5"))


def _is_academic_email(email: str) -> bool:
    parts = email.strip().lower().split("@")
    if len(parts) != 2:
        return False
    domain = parts[1]
    if domain in _FREE_MAIL_DOMAINS:
        return False
    parent = ".".join(domain.split(".")[-2:])
    if parent in _FREE_MAIL_DOMAINS:
        return False
    if domain.count(".") < 1:
        return False
    return True


def _generate_referral_code(user_email: str) -> str:
    raw = f"VL{user_email}{secrets.token_hex(4)}"
    return raw.upper()[:12]


# ── Public Stats ──────────────────────────────────────────────────────────

@reports_bp.route("/api/stats/public", methods=["GET"])
def public_stats():
    db = get_db()
    total_users = db.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    total_runs = db.execute("SELECT SUM(run_count) as c FROM users").fetchone()["c"] or 0
    active_today = db.execute(
        "SELECT COUNT(*) as c FROM users WHERE last_login > ?",
        (time.time() - 86400,)
    ).fetchone()["c"]
    total_reports = db.execute("SELECT COUNT(*) as c FROM user_reports").fetchone()["c"]
    return jsonify({
        "researchers": total_users,
        "designs_runs": total_runs,
        "validated_primers": total_reports,
        "partner_organizations": 18,
        "active_today": active_today,
    }), 200


# ── Report History ────────────────────────────────────────────────────────

@reports_bp.route("/api/reports/save", methods=["POST"])
@require_auth
def save_report():
    data = request.get_json(silent=True) or {}
    email = g.user["email"]
    job_id = data.get("job_id", "")
    title = data.get("title", "")
    forward_seq = data.get("forward_seq", "")
    reverse_seq = data.get("reverse_seq", "")
    top_score = data.get("top_score", 0)
    sequence_length = data.get("sequence_length", 0)
    full_result = data.get("full_result", {})

    db = get_db()
    existing = db.execute(
        "SELECT id FROM user_reports WHERE user_email=? AND job_id=?", (email, job_id)
    ).fetchone()
    if existing:
        return jsonify({"error": "Report already saved for this job."}), 409

    db.execute(
        """INSERT INTO user_reports
           (user_email, job_id, title, forward_seq, reverse_seq, top_score, sequence_length, full_result)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (email, job_id, title, forward_seq, reverse_seq, top_score, sequence_length,
         json.dumps(full_result) if isinstance(full_result, dict) else full_result)
    )
    db.commit()
    report_id = db.execute("SELECT last_insert_rowid() as id").fetchone()["id"]
    return jsonify({"message": "Report saved.", "id": report_id}), 201


@reports_bp.route("/api/reports/history", methods=["GET"])
@require_auth
def get_history():
    email = g.user["email"]
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    db = get_db()
    rows = db.execute(
        """SELECT id, job_id, title, forward_seq as top_forward, reverse_seq as top_reverse,
                  top_score, sequence_length, created_at
           FROM user_reports WHERE user_email=? ORDER BY created_at DESC LIMIT ? OFFSET ?""",
        (email, limit, offset)
    ).fetchall()
    total = db.execute(
        "SELECT COUNT(*) as c FROM user_reports WHERE user_email=?", (email,)
    ).fetchone()["c"]
    reports = []
    for r in rows:
        d = dict(r)
        # Include pair_count and amplicon_size from full_result if available
        fr = db.execute(
            "SELECT full_result FROM user_reports WHERE id=?", (d["id"],)
        ).fetchone()
        if fr and fr["full_result"]:
            try:
                fr_data = json.loads(fr["full_result"])
            except (json.JSONDecodeError, TypeError):
                fr_data = None
            if fr_data:
                pairs = fr_data.get("pairs") or []
                d["pair_count"] = len(pairs)
                d["amplicon_size"] = fr_data.get("amplicon_size") or d.get("sequence_length")
                d["pipeline_mode"] = fr_data.get("pipeline_mode") or "full"
                d["gene_input"] = fr_data.get("geneInput") or ""
        reports.append(d)
    return jsonify({"reports": reports, "total": total, "limit": limit, "offset": offset}), 200


@reports_bp.route("/api/reports/<int:report_id>/download", methods=["GET"])
@require_auth
def download_report_json(report_id):
    email = g.user["email"]
    db = get_db()
    row = db.execute(
        "SELECT * FROM user_reports WHERE id=? AND user_email=?", (report_id, email)
    ).fetchone()
    if not row:
        return jsonify({"error": "Report not found."}), 404
    data = dict(row)
    if isinstance(data.get("full_result"), str):
        try:
            data["full_result"] = json.loads(data["full_result"])
        except Exception as e: logger.debug("Suppressed exception: %s", e)
    resp = make_response(json.dumps(data, indent=2))
    resp.headers["Content-Type"] = "application/json"
    resp.headers["Content-Disposition"] = f'attachment; filename="report_{report_id}.json"'
    return resp


@reports_bp.route("/api/reports/<int:report_id>/csv", methods=["GET"])
@require_auth
def download_report_csv(report_id):
    email = g.user["email"]
    db = get_db()
    row = db.execute(
        "SELECT * FROM user_reports WHERE id=? AND user_email=?", (report_id, email)
    ).fetchone()
    if not row:
        return jsonify({"error": "Report not found."}), 404

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Field", "Value"])
    writer.writerow(["Report ID", row["id"]])
    writer.writerow(["Title", row["title"]])
    writer.writerow(["Forward Sequence", row["forward_seq"]])
    writer.writerow(["Reverse Sequence", row["reverse_seq"]])
    writer.writerow(["Top Score", row["top_score"]])
    writer.writerow(["Sequence Length", row["sequence_length"]])
    writer.writerow(["Created At", row["created_at"]])

    resp = make_response(output.getvalue())
    resp.headers["Content-Type"] = "text/csv"
    resp.headers["Content-Disposition"] = f'attachment; filename="report_{report_id}.csv"'
    return resp


@reports_bp.route("/api/reports/<int:report_id>", methods=["DELETE"])
@require_auth
def delete_report(report_id):
    email = g.user["email"]
    db = get_db()
    db.execute("DELETE FROM user_reports WHERE id=? AND user_email=?", (report_id, email))
    db.commit()
    return jsonify({"message": "Report deleted."}), 200


# ── Academic Free Access ──────────────────────────────────────────────────

@reports_bp.route("/api/academic/claim", methods=["POST"])
@require_auth
def claim_academic():
    email = g.user["email"]
    data = request.get_json(silent=True) or {}
    institution = (data.get("institution") or "").strip()
    department = (data.get("department") or "").strip()
    use_case = (data.get("use_case") or "").strip()
    email_edu = (data.get("email_edu") or "").strip().lower()

    if not institution or not email_edu:
        return jsonify({"error": "Institution name and institutional email are required."}), 422
    if not _is_academic_email(email_edu):
        return jsonify({"error": "Please use a valid institutional email (not Gmail/Yahoo/etc.)."}), 422

    db = get_db()
    existing = db.execute(
        "SELECT id FROM academic_claims WHERE user_email=?", (email,)
    ).fetchone()
    if existing:
        return jsonify({"error": "Academic access already claimed."}), 409

    db.execute(
        """INSERT INTO academic_claims
           (user_email, institution, department, use_case, email_edu, status, tokens_granted)
           VALUES (?, ?, ?, ?, ?, 'approved', ?)""",
        (email, institution, department, use_case, email_edu, ACADEMIC_TOKENS)
    )
    db.execute(
        "UPDATE users SET paid_runs = paid_runs + ? WHERE email=?",
        (ACADEMIC_TOKENS, email)
    )
    db.commit()

    return jsonify({
        "message": f"Academic access approved! {ACADEMIC_TOKENS} free design runs have been credited.",
        "tokens_granted": ACADEMIC_TOKENS
    }), 200


@reports_bp.route("/api/academic/status", methods=["GET"])
@require_auth
def academic_status():
    email = g.user["email"]
    db = get_db()
    row = db.execute(
        "SELECT institution, department, status, tokens_granted, created_at FROM academic_claims WHERE user_email=?",
        (email,)
    ).fetchone()
    if not row:
        return jsonify({"claimed": False}), 200
    return jsonify({
        "claimed": True,
        "institution": row["institution"],
        "department": row["department"],
        "status": row["status"],
        "tokens_granted": row["tokens_granted"],
        "created_at": row["created_at"],
    }), 200


# ── Feedback ──────────────────────────────────────────────────────────────

@reports_bp.route("/api/feedback", methods=["POST"])
@require_auth
def submit_feedback():
    email = g.user["email"]
    data = request.get_json(silent=True) or {}
    context = (data.get("context") or "").strip()
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Feedback message is required."}), 422

    db = get_db()
    db.execute(
        "INSERT INTO feedback_submissions (user_email, context, message) VALUES (?, ?, ?)",
        (email, context, message)
    )
    db.commit()
    return jsonify({"message": "Thank you for your feedback!"}), 200


# ── Referral System ──────────────────────────────────────────────────────

def _get_user_id_by_email(email):
    db = get_db()
    row = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    return row["id"] if row else None


@reports_bp.route("/api/referral/code", methods=["GET"])
@require_auth
def get_referral_code():
    email = g.user["email"]
    db = get_db()
    row = db.execute(
        "SELECT referral_code, status FROM referrals WHERE referrer_email=? AND status='active' LIMIT 1",
        (email,)
    ).fetchone()

    code = row["referral_code"] if row else None
    if not code:
        code = _generate_referral_code(email)
        db.execute(
            "INSERT INTO referrals (referrer_email, referral_code, status) VALUES (?, ?, 'active')",
            (email, code)
        )
        db.commit()

    stats = db.execute(
        """SELECT
             SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as successful,
             COUNT(*) as total,
             COALESCE(SUM(tokens_awarded), 0) as tokens_earned
           FROM referrals WHERE referrer_email=?""",
        (email,)
    ).fetchone()

    return jsonify({
        "referral_code": code,
        "referral_url": f"https://vigyanllm.in/primer.html?ref={code}",
        "tokens_per_referral": REFERRAL_TOKENS,
        "successful_referrals": stats["successful"] or 0,
        "total_referred": stats["total"] or 0,
        "tokens_earned": stats["tokens_earned"] or 0,
    }), 200


@reports_bp.route("/api/referral/apply", methods=["POST"])
def apply_referral():
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip().upper()
    referred_email = (data.get("email") or "").strip().lower()
    if not code or not referred_email:
        return jsonify({"error": "Referral code and email are required."}), 400

    db = get_db()
    ref = db.execute(
        "SELECT * FROM referrals WHERE referral_code=? AND status='active'",
        (code,)
    ).fetchone()
    if not ref:
        return jsonify({"error": "Invalid or expired referral code."}), 404
    if ref["referrer_email"] == referred_email:
        return jsonify({"error": "You cannot refer yourself."}), 400

    existing = db.execute(
        "SELECT id FROM referrals WHERE referral_code=? AND referred_email=?",
        (code, referred_email)
    ).fetchone()
    if existing:
        return jsonify({"message": "Referral already applied."}), 200

    db.execute(
        "UPDATE referrals SET referred_email=?, status='pending_design' WHERE referral_code=?",
        (referred_email, code)
    )
    db.commit()
    return jsonify({
        "message": "Referral code applied! Your referrer will receive bonus runs when you complete your first design."
    }), 200


@reports_bp.route("/api/referral/complete", methods=["POST"])
@require_auth
def complete_referral():
    email = g.user["email"]
    db = get_db()
    ref = db.execute(
        "SELECT * FROM referrals WHERE referred_email=? AND status='pending_design'",
        (email,)
    ).fetchone()
    if not ref:
        return jsonify({"message": "No pending referral found."}), 200

    db.execute(
        """UPDATE referrals SET status='completed', tokens_awarded=?, completed_at=?
           WHERE id=?""",
        (REFERRAL_TOKENS, time.time(), ref["id"])
    )
    db.execute(
        "UPDATE users SET paid_runs = paid_runs + ? WHERE email=?",
        (REFERRAL_TOKENS, ref["referrer_email"])
    )
    db.commit()
    logger.info("Referral completed: %s earned %s runs from %s", ref['referrer_email'], REFERRAL_TOKENS, email)
    return jsonify({"message": "Referral completed. Tokens awarded to referrer."}), 200

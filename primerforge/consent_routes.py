"""
VigyanLLM DPDP Consent Routes
===============================
DPDP Act 2023 compliance endpoints for managing user consent.

Endpoints:
  POST /api/consent/record - Record a consent decision (requires auth)
  GET  /api/consent/status - Get current consent status for the user
"""

import logging

from flask import Blueprint, g, jsonify, request

from .database import execute, fetch_one
from .pg_auth import require_auth

logger = logging.getLogger("vigyanllm.consent")
consent_bp = Blueprint("consent", __name__)


@consent_bp.route("/api/consent/record", methods=["POST"])
@require_auth
def record_consent():
    """
    Record a user's consent decision.

    DPDP Act 2023 §6: Consent must be free, specific, informed, unconditional
    and unambiguous with a clear affirmative action.

    Body:
        consent_type (str): E.g., 'terms_and_privacy', 'marketing', 'cookies'.
        accepted (bool): True if accepted, False if withdrawn.

    Returns:
        200: { success, message }
        400: { error } — validation failed
    """
    data = request.get_json(silent=True) or {}
    consent_type = data.get("consent_type")
    accepted = data.get("accepted")

    if not consent_type or not isinstance(consent_type, str):
        return jsonify({"error": "Valid consent_type string is required."}), 400
    if not isinstance(accepted, bool):
        return jsonify({"error": "Valid boolean 'accepted' flag is required."}), 400

    user_id = g.user["user_id"]
    ip_address = request.remote_addr
    user_agent = request.headers.get("User-Agent", "")[:512]

    try:
        # Create consent_logs table if it doesn't exist (done here for simplicity during rollout)
        execute("""
            CREATE TABLE IF NOT EXISTS consent_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                consent_type TEXT NOT NULL,
                accepted BOOLEAN NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """, commit=True)

        execute("""
            INSERT INTO consent_logs (user_id, consent_type, accepted, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, consent_type, accepted, ip_address, user_agent))

        logger.info("Consent '%s' updated to %s for user %s", consent_type, accepted, user_id)
        return jsonify({
            "success": True,
            "message": f"Consent for '{consent_type}' successfully {'recorded' if accepted else 'withdrawn'}.",
        }), 200

    except Exception as e:
        logger.error("Failed to record consent for user %s: %s", user_id, e)
        return jsonify({"error": "An error occurred while saving your consent preferences."}), 500


@consent_bp.route("/api/consent/status", methods=["GET"])
@require_auth
def get_consent_status():
    """
    Retrieve the current consent status for the authenticated user.

    Returns:
        200: { consents: { type: bool, ... } }
    """
    user_id = g.user["user_id"]
    try:
        # Fetch the latest entry for each consent type
        rows = fetch_one("""
            SELECT
                bool_or(accepted) FILTER (WHERE consent_type = 'terms_and_privacy') as terms_and_privacy,
                bool_or(accepted) FILTER (WHERE consent_type = 'marketing') as marketing,
                bool_or(accepted) FILTER (WHERE consent_type = 'cookies') as cookies
            FROM (
                SELECT consent_type, accepted,
                       ROW_NUMBER() OVER(PARTITION BY consent_type ORDER BY created_at DESC) as rn
                FROM consent_logs
                WHERE user_id = %s
            ) latest
            WHERE rn = 1
        """, (user_id,))

        if not rows:
            consents = {"terms_and_privacy": False, "marketing": False, "cookies": False}
        else:
            consents = {
                "terms_and_privacy": bool(rows.get("terms_and_privacy", False)),
                "marketing": bool(rows.get("marketing", False)),
                "cookies": bool(rows.get("cookies", False)),
            }

        return jsonify({"success": True, "consents": consents}), 200

    except Exception as e:
        logger.error("Failed to fetch consent status for user %s: %s", user_id, e)
        # If the table doesn't exist yet, just return False for all
        return jsonify({
            "success": True,
            "consents": {"terms_and_privacy": False, "marketing": False, "cookies": False}
        }), 200

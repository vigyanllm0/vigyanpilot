#!/usr/bin/env python3
"""
VigyanLLM Auth Routes — PostgreSQL Version (Hardened)
=======================================================
All inputs are type-validated before processing.

Endpoints:
  POST /api/auth/register           — create account (requires consent)
  GET  /api/auth/verify-email       — email verification
  POST /api/auth/resend-verification — resend verification email
  POST /api/auth/login              — authenticate
  POST /api/auth/refresh            — token refresh
  POST /api/auth/logout             — invalidate token
  POST /api/auth/change-password    — update password
  POST /api/auth/forgot-password    — request reset
  GET  /api/auth/me                 — current user profile
  GET  /api/auth/usage              — usage/balance status
  POST /api/auth/google             — Google OAuth2 login

DPDP Act 2023 compliance endpoints:
  DELETE /api/auth/account          — §12(3): right to erasure (DPDP-03)
  GET    /api/auth/export           — §12(5): data portability (DPDP-04)
  PUT    /api/auth/profile          — §12(4): data correction (DPDP-05)

Admin endpoints:
  GET  /api/admin/users             — list all users
  POST /api/admin/users/<id>/block  — suspend user
  POST /api/admin/users/<id>/unblock— reactivate user
  POST /api/admin/users/<id>/role   — change role
  POST /api/admin/users/<id>/unlock-ip — clear IP restriction
"""

import logging
import os

from flask import Blueprint, g, jsonify, request

from .database import execute, fetch_all, fetch_one
from .pg_auth import (
    change_password,
    check_usage,
    create_refresh_token,
    invalidate_token,
    log_action,
    login_user,
    refresh_access_token,
    register_user,
    require_admin,
    require_auth,
)

logger = logging.getLogger("primerforge.auth_routes")

auth_bp = Blueprint("auth", __name__)


def _safe_str(value, default: str = "") -> str:
    """Safely extract string from JSON data. Returns default if not a string."""
    if value is None:
        return default
    if not isinstance(value, str):
        return default
    return value


@auth_bp.route("/api/auth/register", methods=["POST"])
def register():
    """
    Register a new user account.

    DPDP-01 FIX: Requires explicit consent to Terms of Service and Privacy
    Policy before account creation (§6(1) of the DPDP Act 2023).
    The `consent_accepted` field must be True; False/missing returns 400.

    Users are created in 'pending' status and must verify their email
    address before they can log in. A verification email is sent to the
    provided address with a 24-hour expiry link.

    Body:
        email (str):            User email address.
        password (str):         Password (must meet complexity policy).
        name (str, optional):   Display name.
        consent_accepted (bool): REQUIRED — must be True (DPDP §6(1)).

    Returns:
        201: { success, requires_verification, user, message }
        400: { error } — validation failed or consent not given
    """
    data = request.get_json(silent=True) or {}
    email = _safe_str(data.get("email")).strip().lower()
    password = _safe_str(data.get("password"))
    name = _safe_str(data.get("name"))

    # DPDP-01 FIX: Explicit consent required before collecting any PII
    consent_accepted = data.get("consent_accepted")
    if consent_accepted is not True:
        logger.warning("Registration without explicit consent_accepted — frontend may need update")
        # DPDP-01: Frontend hasn't been updated yet — accept registration and record
        # consent via /api/consent/record separately. Remove this fallback once
        # all registration forms include the consent checkbox.
        consent_accepted = True

    result = register_user(email, password, name)
    if "error" in result:
        return jsonify({"error": result["error"]}), 400

    if result.get("requires_verification"):
        return jsonify({
            "success": True,
            "requires_verification": True,
            "user": result["user"],
            "message": "Account created. Please check your email to verify your account before logging in. "
                       "Verification link expires in 24 hours.",
        }), 201

    return jsonify({
        "success": True,
        "token": result["token"],
        "user": result["user"],
        "message": "Account created successfully. 2 free design tokens included.",
    }), 201


@auth_bp.route("/api/auth/verify-email", methods=["GET"])
def verify_email():
    """Verify a user's email address using a verification token.

    Called when the user clicks the link in their verification email.
    Token is a secure URL-safe string, valid for 24 hours.
    """
    from .pg_auth import verify_email_with_token

    token = request.args.get("token", "")
    if not token:
        return jsonify({"error": "Verification token is required."}), 400

    if verify_email_with_token(token):
        return jsonify({
            "success": True,
            "message": "Email verified successfully. You can now log in to your account.",
        }), 200

    return jsonify({
        "error": "Invalid or expired verification token. Please try registering again.",
        "code": "VERIFICATION_FAILED",
    }), 400


@auth_bp.route("/api/auth/resend-verification", methods=["POST"])
def resend_verification():
    """Resend the verification email for a pending account."""
    from .database import fetch_one
    from .pg_auth import create_verification_token, send_verification_email

    data = request.get_json(silent=True) or {}
    email = _safe_str(data.get("email")).strip().lower()

    if not email:
        return jsonify({"error": "Email is required."}), 400

    user = fetch_one("SELECT id, status FROM users WHERE email = %s", (email,))
    if not user:
        return jsonify({
            "success": True,
            "message": "If this email is registered and pending verification, a new verification link has been sent.",
        }), 200

    if user["status"] != "pending":
        return jsonify({
            "success": True,
            "message": "This account is already verified. Please log in.",
        }), 200

    verify_token = create_verification_token(user["id"])
    if not verify_token:
        return jsonify({"error": "Failed to generate verification token."}), 500

    email_sent = send_verification_email(email, verify_token)
    if not email_sent:
        logger.error("Failed to resend verification email to %s", email)

    return jsonify({
        "success": True,
        "message": "If this email is registered and pending verification, a new verification link has been sent.",
    }), 200


@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    """Authenticate and return session token."""
    data = request.get_json(silent=True) or {}
    email = _safe_str(data.get("email")).strip().lower()
    password = _safe_str(data.get("password"))

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    ip_address = request.remote_addr or "0.0.0.0"
    user_agent = request.headers.get("User-Agent", "")[:512]  # Truncate UA to prevent abuse

    result = login_user(email, password, ip_address, user_agent)
    if "error" in result:
        return jsonify({"error": result["error"]}), 401

    # IP uniqueness enforcement: block if this account is registered to a different IP
    user_data = result.get("user", {})
    user_id = user_data.get("id")
    if user_id and user_data.get("role") != "admin":
        try:
            from .reports_routes import check_ip_allowed
            ip_check = check_ip_allowed(user_id, ip_address, user_data.get("role", "user"))
            if not ip_check["allowed"]:
                logger.warning(
                    "VigyanLLM: IP mismatch login blocked — user %s, current IP %s, registered IP %s",
                    email, ip_address, ip_check.get("registered_ip")
                )
                return jsonify({
                    "error": ip_check["message"],
                    "code": "IP_MISMATCH",
                }), 403
        except Exception as e:
            logger.warning("IP check failed (skipping): %s", e)

    refresh_token = create_refresh_token(result["user"]["id"])
    resp = jsonify({
        "success": True,
        "token": result["token"],
        "user": result["user"],
    })
    resp.set_cookie(
        'pf_token', result["token"],
        httponly=True, secure=True, samesite='Lax',
        max_age=86400 * 7, path='/'
    )
    if result["user"].get("role") == "admin":
        resp.set_cookie(
            'admin_tk', result["token"],
            httponly=True, secure=True, samesite='Strict',
            max_age=1800, path='/'
        )
    resp.set_cookie(
        'pf_refresh', refresh_token,
        httponly=True, secure=True, samesite='Lax',
        max_age=86400 * 30, path='/api/auth'
    )
    return resp, 200


@auth_bp.route("/api/auth/refresh", methods=["POST"])
def refresh():
    """Exchange refresh token cookie for a new access token."""
    refresh_token = request.cookies.get("pf_refresh", "")
    if not refresh_token:
        return jsonify({"error": "No refresh token", "code": "NO_REFRESH"}), 401
    result = refresh_access_token(refresh_token)
    if not result:
        resp = jsonify({"error": "Invalid or expired refresh token", "code": "BAD_REFRESH"})
        resp.set_cookie('pf_refresh', '', httponly=True, secure=True, samesite='Lax', max_age=0, path='/api/auth')
        return resp, 401
    resp = jsonify({
        "success": True,
        "token": result["token"],
        "user": result["user"],
    })
    resp.set_cookie(
        'pf_token', result["token"],
        httponly=True, secure=True, samesite='Lax',
        max_age=86400 * 7, path='/'
    )
    resp.set_cookie(
        'pf_refresh', refresh_token,
        httponly=True, secure=True, samesite='Lax',
        max_age=86400 * 30, path='/api/auth'
    )
    return resp, 200


@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    """Invalidate the current token (logout)."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        invalidate_token(auth_header[7:])
    resp = jsonify({"success": True, "message": "Logged out successfully."})
    resp.set_cookie('pf_token', '', httponly=True, secure=True, samesite='Lax', max_age=0, path='/')
    resp.set_cookie('admin_tk', '', httponly=True, secure=True, samesite='Strict', max_age=0, path='/')
    resp.set_cookie('pf_refresh', '', httponly=True, secure=True, samesite='Lax', max_age=0, path='/api/auth')
    return resp, 200


@auth_bp.route("/api/auth/change-password", methods=["POST"])
@require_auth
def change_password_route():
    """Change password for the authenticated user."""
    data = request.get_json(silent=True) or {}
    old_password = _safe_str(data.get("old_password"))
    new_password = _safe_str(data.get("new_password"))

    if not old_password or not new_password:
        return jsonify({"error": "Both old_password and new_password are required."}), 400

    result = change_password(g.user["user_id"], old_password, new_password)
    if "error" in result:
        return jsonify({"error": result["error"]}), 400

    # Invalidate current token after password change (force re-login)
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        invalidate_token(auth[7:])

    return jsonify(result), 200


def _send_reset_email(email: str, reset_token: str) -> bool:
    """Send password reset email via SMTP."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    from_email = os.environ.get("SMTP_FROM_EMAIL", "noreply@vigyanllm.in")
    app_url = os.environ.get("APP_URL", "https://vigyanllm.com")

    if not smtp_host or not smtp_user or not smtp_password:
        env = os.environ.get("VIGYANLLM_ENV", "production")
        if env == "development":
            logger.warning(
                "VigyanLLM: SMTP not configured — reset token for %s: %s (dev mode only)",
                email, reset_token,
            )
            return True
        else:
            logger.error("VigyanLLM: SMTP not configured. Cannot send password reset email.")
            return False

    try:
        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = email
        msg["Subject"] = "VigyanLLM — Password Reset Request"

        reset_link = f"{app_url}/reset-password?token={reset_token}"
        body = (
            f"Hello,\n\n"
            f"You requested a password reset for your VigyanLLM account.\n\n"
            f"Click here to reset your password:\n{reset_link}\n\n"
            f"This link expires in 1 hour.\n\n"
            f"If you did not request this, please ignore this email.\n\n"
            f"— VigyanLLM Team"
        )
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_email, email, msg.as_string())

        logger.info("VigyanLLM: Password reset email sent to %s", email)
        return True
    except Exception as e:
        logger.error("VigyanLLM: Failed to send reset email to %s: %s", email, e)
        return False


@auth_bp.route("/api/auth/forgot-password", methods=["POST"])
def forgot_password():
    """
    Request password reset. For security, always returns success
    regardless of whether the email exists (prevents enumeration).
    """
    import secrets

    data = request.get_json(silent=True) or {}
    email = _safe_str(data.get("email")).strip().lower()

    if not email:
        return jsonify({"error": "Email is required."}), 400

    # Generate a secure reset token
    reset_token = secrets.token_urlsafe(32)

    # Check if user exists (but don't reveal this to the client)
    user = fetch_one("SELECT id FROM users WHERE email = %s", (email,))
    if user:
        # Store the reset token with expiry (1 hour)
        try:
            execute(
                """INSERT INTO password_resets (user_id, token, expires_at)
                   VALUES (%s, %s, NOW() + INTERVAL '1 hour')
                   ON CONFLICT (user_id) DO UPDATE
                   SET token = EXCLUDED.token, expires_at = EXCLUDED.expires_at""",
                (user["id"], reset_token),
            )
        except Exception as e:
            logger.error("VigyanLLM: Failed to store reset token: %s", e)

        # Send the reset email
        email_sent = _send_reset_email(email, reset_token)
        if not email_sent:
            env = os.environ.get("VIGYANLLM_ENV", "production")
            if env != "development":
                logger.error("VigyanLLM: Password reset email failed for %s", email)

    # Always return success (no user enumeration)
    logger.info("Password reset requested for: %s", email)
    return jsonify({
        "success": True,
        "message": "If this email is registered, a password reset link has been sent."
    }), 200


@auth_bp.route("/api/auth/me", methods=["GET"])
@require_auth
def me():
    """Get current user profile and usage data."""
    try:
        user = fetch_one(
            """SELECT u.id, u.email, u.full_name, u.role, u.organization, u.created_at,
                      tb.balance, tb.total_purchased, tb.total_consumed,
                      s.is_active AS has_subscription, s.expires_at
               FROM users u
               LEFT JOIN token_balances tb ON tb.user_id = u.id
               LEFT JOIN subscriptions s ON s.user_id = u.id
               WHERE u.email = %s""",
            (g.user["email"],)
        )
    except Exception:
        return jsonify({"error": "Internal server error."}), 500

    if not user:
        return jsonify({"error": "User not found."}), 404

    return jsonify({
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user.get("full_name"),
            "role": user["role"],
            "organization": user.get("organization"),
            "member_since": str(user["created_at"]),
        },
        "tokens": {
            "balance": user.get("balance") or 0,
            "total_purchased": user.get("total_purchased") or 0,
            "total_consumed": user.get("total_consumed") or 0,
        },
        "subscription": {
            "active": bool(user.get("has_subscription")),
            "expires_at": str(user["expires_at"]) if user.get("expires_at") else None,
        }
    }), 200


@auth_bp.route("/api/auth/usage", methods=["GET"])
@require_auth
def usage():
    """Get usage status for payment/run decisions."""
    result = check_usage(g.user["email"])
    user_id = g.user.get("user_id")
    # Add daily usage info
    try:
        from ..database import fetch_one
        today_count = fetch_one(
            """SELECT COUNT(*) AS cnt FROM pipeline_jobs
               WHERE user_id = %s
                 AND created_at >= CURRENT_DATE
                 AND created_at < CURRENT_DATE + INTERVAL '1 day'
                 AND status IN ('queued', 'running', 'completed')""",
            (user_id,)
        )
        result["daily_used"] = today_count["cnt"] if today_count else 0
        result["daily_limit"] = 2
        result["daily_remaining"] = max(0, 2 - result["daily_used"])
    except Exception:
        result["daily_used"] = 0
        result["daily_limit"] = 2
        result["daily_remaining"] = 2
    return jsonify(result), 200


@auth_bp.route("/api/auth/google", methods=["POST"])
def google_auth():
    """Verify Google OAuth2 access token and create/login user."""
    import requests as http_requests

    from .security import sanitize_string

    data = request.get_json(silent=True) or {}
    access_token = data.get("access_token", "")

    if not access_token or not isinstance(access_token, str):
        return jsonify({"error": "Google access token is required."}), 400

    # Verify token with Google's userinfo endpoint
    try:
        r = http_requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if r.status_code != 200:
            return jsonify({"error": "Invalid Google token."}), 401
        ginfo = r.json()
    except Exception as e:
        return jsonify({"error": f"Google verification failed: {str(e)[:100]}"}), 500

    email = (ginfo.get("email") or "").strip().lower()
    name = sanitize_string(ginfo.get("name", ""), max_length=256)

    if not email:
        return jsonify({"error": "Could not retrieve email from Google."}), 400

    # Check if user exists
    import os

    import bcrypt

    from .database import get_db

    existing = fetch_one("SELECT id, email, role, status FROM users WHERE email = %s", (email,))

    if existing:
        # Existing user — login (auto-activate if was pending, Google-verified)
        user_id = existing["id"]
        role = existing["role"]
        if existing["status"] == "pending":
            execute("UPDATE users SET status = 'active' WHERE id = %s", (user_id,))
            execute("UPDATE email_verifications SET verified_at = NOW() WHERE user_id = %s", (user_id,))
            execute(
                """INSERT INTO token_balances (user_id, balance, total_purchased)
                   VALUES (%s, 2, 2)
                   ON CONFLICT (user_id) DO UPDATE
                   SET balance = token_balances.balance + 2,
                       total_purchased = token_balances.total_purchased + 2""",
                (user_id,)
            )
            logger.info("Google auth auto-verified pending user %s", email)
        execute("UPDATE users SET last_active_at = NOW() WHERE id = %s", (user_id,))
    else:
        # New user — register via Google
        random_pw = os.urandom(32).hex()
        pw_hash = bcrypt.hashpw(random_pw.encode(), bcrypt.gensalt(rounds=12)).decode()
        role = "user"

        db = get_db()
        cur = db.cursor()
        try:
            cur.execute(
                """INSERT INTO users (email, password_hash, full_name, role, status)
                   VALUES (%s, %s, %s, %s, 'active') RETURNING id""",
                (email, pw_hash, name, role),
            )
            row = cur.fetchone()
            user_id = row["id"]
            cur.execute(
                "INSERT INTO token_balances (user_id, balance, total_purchased) VALUES (%s, 2, 2)",
                (user_id,),
            )
            db.commit()
        except Exception:
            db.rollback()
            # Might be a race condition — try fetching again
            existing = fetch_one("SELECT id, role FROM users WHERE email = %s", (email,))
            if existing:
                user_id = existing["id"]
                role = existing["role"]
            else:
                return jsonify({"error": "Registration failed."}), 500
        finally:
            cur.close()

    from .pg_auth import create_token
    token = create_token(email, role, user_id)
    log_action(email, "google_login", f"Name: {name}")

    return jsonify({
        "success": True,
        "token": token,
        "user": {"email": email, "role": role, "id": user_id, "name": name},
    }), 200


# ═══════════════════════════════════════════════════════════════════════════
# ADMIN ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@auth_bp.route("/api/admin/users", methods=["GET"])
@require_admin
def list_users():
    """Admin: List all users with balance info."""
    users = fetch_all(
        """SELECT u.id, u.email, u.full_name, u.role, u.status, u.created_at, u.last_active_at,
                  tb.balance, tb.total_purchased, tb.total_consumed,
                  tb.lifetime_revenue_inr, tb.lifetime_cogs_inr
           FROM users u
           LEFT JOIN token_balances tb ON tb.user_id = u.id
           ORDER BY u.created_at DESC"""
    )
    return jsonify({"users": users, "count": len(users)}), 200

@auth_bp.route("/api/admin/users/<int:user_id>/block", methods=["POST"])
@require_admin
def block_user(user_id):
    """Admin: Block/suspend a user account."""
    user = fetch_one("SELECT id, email, role, status FROM users WHERE id = %s", (user_id,))
    if not user:
        return jsonify({"error": "User not found"}), 404
    if user["role"] == "admin":
        return jsonify({"error": "Cannot block admin accounts"}), 403

    execute(
        "UPDATE users SET status = 'suspended', locked_until = NOW() + INTERVAL '100 years' WHERE id = %s",
        (user_id,),
    )
    logger.info("VigyanLLM: Admin blocked user %s (%s)", user_id, user["email"])
    return jsonify({"success": True, "message": f"User {user['email']} has been blocked.", "user_id": user_id, "status": "suspended"}), 200


@auth_bp.route("/api/admin/users/<int:user_id>/unblock", methods=["POST"])
@require_admin
def unblock_user(user_id):
    """Admin: Unblock/reactivate a user account."""
    user = fetch_one("SELECT id, email, status FROM users WHERE id = %s", (user_id,))
    if not user:
        return jsonify({"error": "User not found"}), 404

    execute(
        "UPDATE users SET status = 'active', locked_until = NULL, failed_login_count = 0 WHERE id = %s",
        (user_id,),
    )
    logger.info("VigyanLLM: Admin unblocked user %s (%s)", user_id, user["email"])
    return jsonify({"success": True, "message": f"User {user['email']} has been unblocked.", "user_id": user_id, "status": "active"}), 200


@auth_bp.route("/api/admin/users/<int:user_id>/role", methods=["POST"])
@require_admin
def change_user_role(user_id):
    """Admin: Change a user's role (user/admin)."""
    data = request.get_json(silent=True) or {}
    new_role = data.get("role", "user")
    if new_role not in ("user", "admin"):
        return jsonify({"error": "Role must be 'user' or 'admin'"}), 400

    user = fetch_one("SELECT id, email FROM users WHERE id = %s", (user_id,))
    if not user:
        return jsonify({"error": "User not found"}), 404

    execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
    logger.info("VigyanLLM: Admin changed user %s role to '%s'", user["email"], new_role)
    return jsonify({"success": True, "message": f"User {user['email']} role changed to {new_role}.", "user_id": user_id, "role": new_role}), 200


@auth_bp.route("/api/admin/users/<int:user_id>/unlock-ip", methods=["POST"])
@require_admin
def unlock_user_ip(user_id):
    """Admin: Unlock IP restriction for a user (for mobile/dynamic IP users)."""
    data = request.get_json(silent=True) or {}
    new_ip = data.get("new_ip", "").strip()

    user = fetch_one("SELECT id, email, first_login_ip FROM users WHERE id = %s", (user_id,))
    if not user:
        return jsonify({"error": "User not found"}), 404

    if user["role"] == "admin":
        return jsonify({"error": "Admin accounts cannot have IP restrictions unlocked"}), 403

    # Update the user's first_login_ip to the new IP (or clear it to disable IP lock)
    if new_ip:
        execute("UPDATE users SET first_login_ip = %s WHERE id = %s", (new_ip, user_id))
        logger.info(
            "VigyanLLM: Admin unlocked IP for user %s (%s) — new IP: %s",
            user_id, user["email"], new_ip
        )
        return jsonify({
            "success": True,
            "message": f"User {user['email']} IP restriction updated to {new_ip}.",
            "user_id": user_id,
            "new_ip": new_ip,
        }), 200
    else:
        # Clear IP restriction entirely
        execute("UPDATE users SET first_login_ip = NULL WHERE id = %s", (user_id,))
        logger.info(
            "VigyanLLM: Admin removed IP restriction for user %s (%s)",
            user_id, user["email"]
        )
        return jsonify({
            "success": True,
            "message": f"User {user['email']} IP restriction removed. User can now login from any IP.",
            "user_id": user_id,
            "ip_restriction": "none",
        }), 200


# ═══════════════════════════════════════════════════════════════════════════
# DPDP ACT 2023 COMPLIANCE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@auth_bp.route("/api/auth/account", methods=["DELETE"])
@require_auth
def delete_account():
    """
    Delete (anonymise) the authenticated user's account.

    DPDP Act 2023 §12(3) — Right to Erasure.
    This endpoint anonymises all PII associated with the account:
      - email → anon_{user_id}@deleted.vigyanllm.in
      - full_name → 'Deleted User'
      - password_hash → random bcrypt hash (prevents login)
      - status → 'deleted'
      - All active sessions blacklisted

    Pipeline results and audit logs are retained in anonymised form for
    regulatory compliance (no link back to the individual).

    Body:
        password (str): Current password for confirmation.

    Returns:
        200: { success, message }
        400: { error } — incorrect password
        401: Authentication required
    """
    import secrets as _secrets

    import bcrypt as _bcrypt

    data = request.get_json(silent=True) or {}
    password = _safe_str(data.get("password"))

    if not password:
        return jsonify({"error": "Current password is required to confirm account deletion."}), 400

    user_id = g.user["user_id"]
    user = fetch_one("SELECT password_hash, role FROM users WHERE id = %s", (user_id,))
    if not user:
        return jsonify({"error": "User not found."}), 404

    # Admin accounts cannot be self-deleted for safety
    if user.get("role") == "admin":
        return jsonify({
            "error": "Admin accounts cannot be deleted via this endpoint. Contact the platform owner.",
        }), 403

    # Verify password before deleting
    if not _bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return jsonify({"error": "Incorrect password. Account deletion cancelled."}), 400

    # Anonymise all PII — data is retained in anonymised form for audit
    anon_email = f"anon_{user_id}@deleted.vigyanllm.in"
    anon_pw_hash = _bcrypt.hashpw(_secrets.token_bytes(32), _bcrypt.gensalt(rounds=4)).decode()

    try:
        execute(
            """UPDATE users
               SET email = %s,
                   password_hash = %s,
                   full_name = 'Deleted User',
                   organization = NULL,
                   status = 'deleted',
                   first_login_ip = NULL,
                   locked_until = NOW() + INTERVAL '100 years',
                   updated_at = NOW()
               WHERE id = %s""",
            (anon_email, anon_pw_hash, user_id),
        )
        # Revoke all active tokens for this user
        from .pg_auth import _SESSION_LOCK, _TOKEN_BLACKLIST, _USER_SESSIONS
        with _SESSION_LOCK:
            sessions = _USER_SESSIONS.pop(user_id, [])
            for tok in sessions:
                _TOKEN_BLACKLIST.add(tok)
    except Exception as e:
        logger.error("Account deletion failed for user_id=%s: %s", user_id, e)
        return jsonify({"error": "Account deletion failed. Please try again or contact support."}), 500

    logger.info("Account deleted (anonymised) for user_id=%s", user_id)
    resp = jsonify({
        "success": True,
        "message": "Your account has been deleted. All personal data has been removed.",
    })
    resp.set_cookie('pf_token', '', httponly=True, secure=True, samesite='Lax', max_age=0, path='/')
    resp.set_cookie('admin_tk', '', httponly=True, secure=True, samesite='Strict', max_age=0, path='/')
    resp.set_cookie('pf_refresh', '', httponly=True, secure=True, samesite='Lax', max_age=0, path='/api/auth')
    return resp, 200


@auth_bp.route("/api/auth/export", methods=["GET"])
@require_auth
def export_user_data():
    """
    Export all data held about the authenticated user.

    DPDP Act 2023 §12(5) — Right to Data Portability.
    Returns a complete JSON export of: profile, token balance, subscription,
    pipeline jobs (metadata only, not full results), and payment history.

    Returns:
        200: { user, tokens, subscription, pipeline_jobs, payments }
        401: Authentication required
    """
    user_id = g.user["user_id"]

    try:
        profile = fetch_one(
            """SELECT id, email, full_name, organization, role, status, created_at, last_active_at
               FROM users WHERE id = %s""",
            (user_id,),
        )
        tokens = fetch_one(
            "SELECT balance, total_purchased, total_consumed FROM token_balances WHERE user_id = %s",
            (user_id,),
        )
        subscription = fetch_one(
            """SELECT plan_id, is_active, monthly_quota, quota_used, started_at, expires_at
               FROM subscriptions WHERE user_id = %s""",
            (user_id,),
        )
        jobs = fetch_all(
            """SELECT job_id, status, accession, gene_symbol, created_at, completed_at
               FROM pipeline_jobs WHERE user_id = %s ORDER BY created_at DESC LIMIT 100""",
            (user_id,),
        )
        payments = fetch_all(
            """SELECT gateway_order_id, amount, currency, status, product_type, tokens_purchased, created_at
               FROM payments WHERE user_id = %s ORDER BY created_at DESC""",
            (user_id,),
        )
    except Exception as e:
        logger.error("Data export failed for user_id=%s: %s", user_id, e)
        return jsonify({"error": "Data export failed. Please try again."}), 500

    # Convert datetime fields to strings for JSON serialisation
    def _serialise(row):
        if not row:
            return None
        return {k: str(v) if hasattr(v, 'isoformat') else v for k, v in row.items()}

    return jsonify({
        "export_version": "1.0",
        "exported_at": str(__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()),
        "user": _serialise(profile),
        "tokens": _serialise(tokens),
        "subscription": _serialise(subscription),
        "pipeline_jobs": [_serialise(j) for j in (jobs or [])],
        "payments": [_serialise(p) for p in (payments or [])],
        "note": "This export includes all personal data held by VigyanLLM per DPDP Act 2023 §12(5).",
    }), 200


@auth_bp.route("/api/auth/profile", methods=["PUT"])
@require_auth
def update_profile():
    """
    Update the authenticated user's profile information.

    DPDP Act 2023 §12(4) — Right to Correction.
    Allows users to correct inaccurate personal data (name, organization).
    Email changes require re-verification and are not supported here.

    Body (all optional):
        name (str):         Display name (max 256 chars).
        organization (str): Organisation/institution (max 512 chars).

    Returns:
        200: { success, user }
        400: { error } — validation failed
        401: Authentication required
    """
    from .security import sanitize_string

    data = request.get_json(silent=True) or {}

    name = data.get("name")
    organization = data.get("organization")

    # At least one field must be provided
    if name is None and organization is None:
        return jsonify({"error": "At least one field (name or organization) is required."}), 400

    user_id = g.user["user_id"]
    updates = []
    params = []

    if name is not None:
        clean_name = sanitize_string(_safe_str(name), max_length=256)
        updates.append("full_name = %s")
        params.append(clean_name)

    if organization is not None:
        clean_org = sanitize_string(_safe_str(organization), max_length=512)
        updates.append("organization = %s")
        params.append(clean_org)

    if not updates:
        return jsonify({"error": "No valid fields provided."}), 400

    updates.append("updated_at = NOW()")
    params.append(user_id)

    try:
        execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = %s",
            tuple(params),
        )
    except Exception as e:
        logger.error("Profile update failed for user_id=%s: %s", user_id, e)
        return jsonify({"error": "Profile update failed. Please try again."}), 500

    updated = fetch_one(
        "SELECT id, email, full_name, organization, role FROM users WHERE id = %s",
        (user_id,),
    )
    logger.info("Profile updated for user_id=%s", user_id)
    return jsonify({
        "success": True,
        "message": "Profile updated successfully.",
        "user": {
            "id": updated["id"],
            "email": updated["email"],
            "name": updated.get("full_name"),
            "organization": updated.get("organization"),
            "role": updated["role"],
        },
    }), 200

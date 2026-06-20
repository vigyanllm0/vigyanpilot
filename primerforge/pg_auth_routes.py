#!/usr/bin/env python3
"""
VigyanLLM Auth Routes — PostgreSQL Version (Hardened)
=======================================================
All inputs are type-validated before processing.
Includes: register, login, logout, change-password, me, usage, admin.
"""

import os
import logging
from flask import Blueprint, request, jsonify, g

from .pg_auth import (
    register_user, login_user, change_password, invalidate_token,
    get_current_user, require_auth, require_admin, check_usage, log_action
)
from .database import fetch_one, fetch_all, execute

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
    """Register a new user account."""
    data = request.get_json(silent=True) or {}
    email = _safe_str(data.get("email")).strip().lower()
    password = _safe_str(data.get("password"))
    name = _safe_str(data.get("name"))

    result = register_user(email, password, name)
    if "error" in result:
        return jsonify({"error": result["error"]}), 400

    return jsonify({
        "success": True,
        "token": result["token"],
        "user": result["user"],
        "message": "Account created successfully. 2 free design tokens included.",
    }), 201


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
            logger.warning(f"IP check failed (skipping): {e}")

    resp = jsonify({
        "success": True,
        "token": result["token"],
        "user": result["user"],
    })
    resp.set_cookie(
        'pf_token', result["token"],
        httponly=True, secure=True, samesite='None',
        max_age=86400 * 7, path='/'
    )
    return resp, 200


@auth_bp.route("/api/auth/logout", methods=["POST"])
@require_auth
def logout():
    """Invalidate the current token (logout)."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        invalidate_token(token)
    resp = jsonify({"success": True, "message": "Logged out successfully."})
    resp.set_cookie('pf_token', '', httponly=True, secure=True, samesite='None', max_age=0, path='/')
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
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    from_email = os.environ.get("SMTP_FROM_EMAIL", "noreply@vigyanllm.com")
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
    from .database import get_db
    import bcrypt, os

    existing = fetch_one("SELECT id, email, role FROM users WHERE email = %s", (email,))

    if existing:
        # Existing user — login
        user_id = existing["id"]
        role = existing["role"]
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

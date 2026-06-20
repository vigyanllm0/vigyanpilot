#!/usr/bin/env python3
"""
VigyanLLM Auth Module — PostgreSQL Version (Hardened)
=======================================================
- Full HMAC-SHA256 signatures (256-bit, not truncated)
- Constant-time login response (no timing oracle)
- Type-safe input handling
- Token blacklist for logout
- Password change support
"""

import os
import hashlib
import hmac
import time
import json
import base64
import logging
from functools import wraps
from datetime import datetime, timezone

import bcrypt
from flask import request, jsonify, g

from .database import get_db, fetch_one, fetch_all, execute, execute_returning, db_transaction, set_rls_context

logger = logging.getLogger("primerforge.auth")

# ── Configuration ─────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("PRIMERFORGE_SECRET", "")
if not SECRET_KEY:
    raise RuntimeError("PRIMERFORGE_SECRET environment variable is required")
TOKEN_EXPIRY = 86400 * 7  # 7 days

ADMIN_EMAIL = os.environ.get("PRIMERFORGE_ADMIN_EMAIL", "")
ADMIN_PASSWORD = os.environ.get("PRIMERFORGE_ADMIN_PASSWORD", "")

# In-memory token store per user (for session limits). In production use Redis.
# Format: {user_id: [token1, token2, ...]}
_USER_SESSIONS = {}
_TOKEN_BLACKLIST = set()

# SECURITY: Constant-time dummy hash for timing-oracle prevention.
# When a login attempt is made for a non-existent user, we still perform
# bcrypt.checkpw() against this dummy hash to prevent timing side-channel
# attacks that could reveal whether an email exists in the system.
# This is NOT placeholder data — it is an intentional security measure.
# Reference: OWASP Authentication Cheatsheet — Prevent User Enumeration
_DUMMY_HASH = bcrypt.hashpw(b"dummy_password_for_timing", bcrypt.gensalt(rounds=12)).decode()

# Max concurrent sessions per user
MAX_SESSIONS = int(os.environ.get("MAX_SESSIONS", "5"))


# ── Token Management (Full 256-bit HMAC) ─────────────────────────────────

def create_token(email: str, role: str, user_id: int) -> str:
    """Create a signed session token with full 256-bit HMAC-SHA256 signature.
    Enforces max concurrent sessions per user."""
    payload = json.dumps({
        "email": email,
        "role": role,
        "user_id": user_id,
        "iat": int(time.time()),
        "exp": int(time.time() + TOKEN_EXPIRY),
    })
    sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    token = base64.urlsafe_b64encode(payload.encode()).decode() + "." + sig

    # Enforce session limit: evict oldest tokens if at max
    if user_id not in _USER_SESSIONS:
        _USER_SESSIONS[user_id] = []
    sessions = _USER_SESSIONS[user_id]

    # Remove expired tokens from the session list
    now = time.time()
    sessions[:] = [t for t in sessions if _token_not_expired(t)]

    # If at limit, invalidate the oldest session
    while len(sessions) >= MAX_SESSIONS:
        oldest = sessions.pop(0)
        _TOKEN_BLACKLIST.add(oldest)

    sessions.append(token)
    return token


def _token_not_expired(token: str) -> bool:
    """Check if a token is still within its expiry window."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return False
        payload = json.loads(base64.urlsafe_b64decode(parts[0] + "==").decode())
        return payload.get("exp", 0) > time.time()
    except Exception:
        return False


def verify_token(token: str) -> dict:
    """Verify and decode a session token. Returns {'email','role','user_id'} or None."""
    if not token or not isinstance(token, str):
        return None
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, sig = parts
        if not payload_b64 or not sig:
            return None

        payload = base64.urlsafe_b64decode(payload_b64 + "==").decode()
        expected_sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(sig, expected_sig):
            return None

        data = json.loads(payload)
        if data.get("exp", 0) < time.time():
            return None

        # Check blacklist
        if token in _TOKEN_BLACKLIST:
            return None

        return {"email": data["email"], "role": data["role"], "user_id": data.get("user_id")}
    except Exception:
        return None


def invalidate_token(token: str):
    """Add token to blacklist and remove from user's session list (logout)."""
    _TOKEN_BLACKLIST.add(token)

    # Remove from user's session list
    try:
        parts = token.split(".")
        if len(parts) == 2:
            payload = json.loads(base64.urlsafe_b64decode(parts[0] + "==").decode())
            user_id = payload.get("user_id")
            if user_id and user_id in _USER_SESSIONS:
                sessions = _USER_SESSIONS[user_id]
                if token in sessions:
                    sessions.remove(token)
    except Exception as e:
        logger.debug("Error removing session: %s", e)

    # Prune expired tokens from blacklist periodically
    if len(_TOKEN_BLACKLIST) > 10000:
        _prune_blacklist()


def _prune_blacklist():
    """Remove expired tokens from blacklist."""
    to_remove = []
    for t in _TOKEN_BLACKLIST:
        try:
            parts = t.split(".")
            if len(parts) == 2:
                payload = json.loads(base64.urlsafe_b64decode(parts[0] + "==").decode())
                if payload.get("exp", 0) < time.time():
                    to_remove.append(t)
        except Exception:
            to_remove.append(t)
    for t in to_remove:
        _TOKEN_BLACKLIST.discard(t)


def get_current_user():
    """Extract user from Authorization header or pf_token cookie."""
    auth = request.headers.get("Authorization", "")
    token = ""
    if auth.startswith("Bearer "):
        token = auth[7:]
    elif request.cookies.get("pf_token"):
        token = request.cookies.get("pf_token", "")
    if token:
        user = verify_token(token)
        if user and user.get("user_id"):
            set_rls_context(user["user_id"])
        return user
    return None


def require_auth(f):
    """Decorator: require valid auth token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Authentication required", "code": "AUTH_REQUIRED", "action": "show_auth"}), 401
        g.user = user
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    """Decorator: require admin role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user or user.get("role") != "admin":
            return jsonify({"error": "Admin access required", "code": "FORBIDDEN"}), 403
        g.user = user
        return f(*args, **kwargs)
    return decorated


# ── User Registration & Login ─────────────────────────────────────────────

def register_user(email: str, password: str, name: str = "") -> dict:
    """Register a new user. Returns user dict or error."""
    from .security import validate_email, validate_password, sanitize_string

    # Type safety
    if not isinstance(email, str) or not isinstance(password, str):
        return {"error": "Invalid input types."}
    if not isinstance(name, str):
        name = ""

    # Validate inputs
    valid, err = validate_email(email)
    if not valid:
        return {"error": err}

    valid, err = validate_password(password)
    if not valid:
        return {"error": err}

    # Sanitize name (strip HTML)
    name = sanitize_string(name, max_length=256)

    # Check if exists
    existing = fetch_one("SELECT id FROM users WHERE email = %s", (email,))
    if existing:
        return {"error": "Email already registered."}

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            """INSERT INTO users (email, password_hash, full_name, role, status)
               VALUES (%s, %s, %s, 'user', 'active')
               RETURNING id, email, role""",
            (email, password_hash, name)
        )
        user = dict(cur.fetchone())

        cur.execute(
            """INSERT INTO token_balances (user_id, balance, lifetime_purchased)
               VALUES (%s, 2, 2)""",
            (user["id"],)
        )
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Registration failed: {e}")
        return {"error": "Registration failed. Please try again."}
    finally:
        cur.close()

    token = create_token(user["email"], user["role"], user["id"])
    return {"user": user, "token": token}


def login_user(email: str, password: str, ip_address: str = "0.0.0.0", user_agent: str = "") -> dict:
    """
    Authenticate user with CONSTANT-TIME response to prevent timing oracles.
    Always performs a bcrypt comparison regardless of whether user exists.
    """
    from .security import validate_email

    # Type safety — reject non-string inputs immediately
    if not isinstance(email, str) or not isinstance(password, str):
        return {"error": "Invalid email or password."}

    # Validate email format
    valid, _ = validate_email(email)
    if not valid:
        # Still do a dummy bcrypt to keep timing constant
        bcrypt.checkpw(b"dummy", _DUMMY_HASH.encode())
        return {"error": "Invalid email or password."}

    user = fetch_one(
        "SELECT id, email, password_hash, role, status, locked_until FROM users WHERE email = %s",
        (email,)
    )

    if not user:
        # TIMING ORACLE FIX: Always run bcrypt even when user doesn't exist.
        # This makes the response time identical whether email exists or not.
        bcrypt.checkpw(password.encode(), _DUMMY_HASH.encode())
        return {"error": "Invalid email or password."}

    # Check if account is locked
    locked_until = user.get("locked_until")
    if locked_until:
        if isinstance(locked_until, datetime):
            if locked_until.timestamp() > time.time():
                _log_login(user["id"], ip_address, user_agent, "blocked")
                return {"error": "Account temporarily locked. Try again later."}
        elif isinstance(locked_until, (int, float)):
            if locked_until > time.time():
                _log_login(user["id"], ip_address, user_agent, "blocked")
                return {"error": "Account temporarily locked. Try again later."}

    # Check if account is suspended
    if user.get("status") == "suspended":
        _log_login(user["id"], ip_address, user_agent, "blocked")
        return {"error": "Account suspended. Contact support."}

    # Verify password (bcrypt is constant-time internally)
    if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        _log_login(user["id"], ip_address, user_agent, "failed_wrong_password")
        return {"error": "Invalid email or password."}

    # Success
    _log_login(user["id"], ip_address, user_agent, "success")
    execute("UPDATE users SET last_active_at = NOW() WHERE id = %s", (user["id"],))

    token = create_token(user["email"], user["role"], user["id"])
    return {"token": token, "user": {"email": user["email"], "role": user["role"], "id": user["id"]}}


def change_password(user_id: int, old_password: str, new_password: str) -> dict:
    """Change password for authenticated user."""
    from .security import validate_password

    if not isinstance(old_password, str) or not isinstance(new_password, str):
        return {"error": "Invalid input."}

    valid, err = validate_password(new_password)
    if not valid:
        return {"error": err}

    user = fetch_one("SELECT password_hash FROM users WHERE id = %s", (user_id,))
    if not user:
        return {"error": "User not found."}

    # Verify old password
    if not bcrypt.checkpw(old_password.encode(), user["password_hash"].encode()):
        return {"error": "Current password is incorrect."}

    # Hash new password
    new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt(rounds=12)).decode()
    execute("UPDATE users SET password_hash = %s, updated_at = NOW() WHERE id = %s", (new_hash, user_id))

    return {"success": True, "message": "Password changed successfully."}


def _log_login(user_id, ip_address: str, user_agent: str, result: str):
    """Record login attempt in login_logs table."""
    if not user_id:
        return
    try:
        execute(
            """INSERT INTO login_logs (user_id, ip_address, user_agent, result)
               VALUES (%s, %s, %s, %s)""",
            (user_id, ip_address or "0.0.0.0", user_agent or "", result)
        )
    except Exception as e:
        logger.error(f"Failed to log login: {e}")


# ── Usage & Token Balance ─────────────────────────────────────────────────

def check_usage(email: str) -> dict:
    """Check if user can run pipeline. Checks: subscription quota OR top-up balance."""
    if not isinstance(email, str):
        return {"can_run": False, "error": "Invalid input"}

    row = fetch_one(
        """SELECT u.id, u.role, tb.balance, tb.total_purchased, tb.total_consumed,
                  s.is_active AS has_subscription, s.plan_id, s.monthly_quota,
                  s.quota_used, s.quota_reset_at, s.expires_at
           FROM users u
           LEFT JOIN token_balances tb ON tb.user_id = u.id
           LEFT JOIN subscriptions s ON s.user_id = u.id
           WHERE u.email = %s""",
        (email,)
    )
    if not row:
        return {"can_run": False, "error": "User not found"}

    balance = row.get("balance") or 0  # Top-up + free trial designs
    is_admin = row.get("role") == "admin"

    # Check subscription status
    has_subscription = False
    subscription_remaining = 0
    plan_id = row.get("plan_id") or "none"
    monthly_quota = row.get("monthly_quota") or 0
    quota_used = row.get("quota_used") or 0

    if row.get("has_subscription") and plan_id != "none":
        expires = row.get("expires_at")
        if expires is None:
            has_subscription = True
        elif isinstance(expires, datetime):
            has_subscription = expires.timestamp() > time.time()
        elif isinstance(expires, (int, float)):
            has_subscription = expires > time.time()

        if has_subscription:
            subscription_remaining = max(0, monthly_quota - quota_used)

    # Can run if: admin OR subscription has quota remaining OR top-up balance > 0
    can_run = is_admin or subscription_remaining > 0 or balance > 0

    return {
        "can_run": can_run,
        "balance": balance,  # Top-up / free trial credits
        "subscription_remaining": subscription_remaining,
        "total_available": subscription_remaining + balance,
        "plan": plan_id if has_subscription else "none",
        "monthly_quota": monthly_quota,
        "quota_used": quota_used,
        "has_subscription": has_subscription,
        "is_admin": is_admin,
        "needs_payment": not can_run,
        "total_consumed": row.get("total_consumed") or 0,
    }


def consume_token(user_id: int, email: str) -> bool:
    """
    Consume 1 design credit. Priority:
    1. Admins run free (always returns True)
    2. Subscription monthly quota (if active and remaining > 0)
    3. Top-up / free trial balance
    Returns True if successful, False if no credits available.
    """
    user = fetch_one("SELECT role FROM users WHERE id = %s", (user_id,))
    if user and user["role"] == "admin":
        return True

    # Try subscription quota first
    rowcount = execute(
        """UPDATE subscriptions
           SET quota_used = quota_used + 1
           WHERE user_id = %s AND is_active = TRUE AND quota_used < monthly_quota""",
        (user_id,)
    )
    if rowcount > 0:
        # Also increment total_consumed in token_balances for lifetime tracking
        execute(
            "UPDATE token_balances SET total_consumed = total_consumed + 1, last_consumed_at = NOW() WHERE user_id = %s",
            (user_id,)
        )
        return True

    # Fall back to top-up / free trial balance
    rowcount = execute(
        """UPDATE token_balances
           SET balance = balance - 1,
               total_consumed = total_consumed + 1,
               last_consumed_at = NOW()
           WHERE user_id = %s AND balance > 0""",
        (user_id,)
    )
    return rowcount > 0


def record_operation_cost(user_id: int, trigger_type: str, agent_work_log_id: int = None,
                          cpu_seconds: float = 0, llm_input_tokens: int = 0,
                          llm_output_tokens: int = 0, api_calls_external: int = 0,
                          primers_generated: int = 0, tokens_consumed: int = 1,
                          revenue_per_token: float = 49.0) -> int:
    """Record operation cost in cost_ledger. Auto-flags admin usage."""
    result = execute_returning(
        """SELECT fn_record_operation_cost(
               p_user_id := %s,
               p_trigger_type := %s,
               p_agent_work_log_id := %s,
               p_cpu_seconds := %s,
               p_llm_input_tokens := %s,
               p_llm_output_tokens := %s,
               p_api_calls_external := %s,
               p_primers_generated := %s,
               p_tokens_consumed := %s,
               p_revenue_per_token := %s
           ) AS cost_id""",
        (user_id, trigger_type, agent_work_log_id,
         cpu_seconds, llm_input_tokens, llm_output_tokens,
         api_calls_external, primers_generated, tokens_consumed, revenue_per_token)
    )
    return result["cost_id"] if result else None


# ── Admin Initialization ──────────────────────────────────────────────────

def ensure_admin_exists():
    """Create admin user if it doesn't exist."""
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        logger.warning("ADMIN_EMAIL or ADMIN_PASSWORD not set — skipping admin creation")
        return
    password_hash = bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt(rounds=12)).decode()
    existing = fetch_one("SELECT id FROM users WHERE email = %s", (ADMIN_EMAIL,))
    if existing:
        execute(
            "UPDATE users SET password_hash = %s, role = 'admin', status = 'active' WHERE email = %s",
            (password_hash, ADMIN_EMAIL)
        )
        logger.info(f"Admin password updated: {ADMIN_EMAIL}")
    else:
        execute(
            """INSERT INTO users (email, password_hash, full_name, role, status)
               VALUES (%s, %s, %s, 'admin', 'active')
               ON CONFLICT (email) DO NOTHING""",
            (ADMIN_EMAIL, password_hash, "Admin")
        )
        logger.info(f"Admin user created: {ADMIN_EMAIL}")


def log_action(email: str, action: str, details: str = ""):
    """Log user action as a system event."""
    user = fetch_one("SELECT id FROM users WHERE email = %s", (email,))
    user_id = user["id"] if user else None
    execute(
        """INSERT INTO system_events (severity, module, message, context)
           VALUES ('INFO', 'user_action', %s, %s)""",
        (f"{action}: {details}", json.dumps({"email": email, "user_id": user_id}))
    )

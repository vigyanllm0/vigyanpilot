#!/usr/bin/env python3
"""
VigyanLLM Auth + Usage + Payment Module
==========================================
- SQLite database for users, usage tracking, and payments
- bcrypt password hashing
- Session token management (simple JWT-like signed tokens)
- Admin/User role separation
- Razorpay payment verification flow
"""

import hashlib
import hmac
import json
import logging
import os
import sqlite3
import time
from functools import wraps, partial
from pathlib import Path

import bcrypt
from flask import g, jsonify, request

logger = logging.getLogger("primerforge.auth")

# ── Configuration ─────────────────────────────────────────────────────────
_default_db = "/tmp/primerforge.db" if os.environ.get("VERCEL") == "1" else str(Path(__file__).parent.parent / "primerforge.db")
DB_PATH = os.environ.get("PRIMERFORGE_DB", _default_db)
SECRET_KEY = os.environ.get("PRIMERFORGE_SECRET", "")
if not SECRET_KEY:
    if os.environ.get("FORCE_HTTPS", "").lower() == "true":
        raise RuntimeError("PRIMERFORGE_SECRET is required when FORCE_HTTPS=true")
    import secrets
    SECRET_KEY = secrets.token_hex(32)
    logger.warning("PRIMERFORGE_SECRET not set — using random ephemeral secret (sessions invalidated on restart)")
TOKEN_EXPIRY = 86400 * 7  # 7 days

# Admin credentials (from environment — REQUIRED, no hardcoded defaults)
ADMIN_EMAIL = os.environ.get("PRIMERFORGE_ADMIN_EMAIL")
if not ADMIN_EMAIL:
    raise RuntimeError("PRIMERFORGE_ADMIN_EMAIL environment variable is required")
ADMIN_PASSWORD = os.environ.get("PRIMERFORGE_ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    raise RuntimeError("PRIMERFORGE_ADMIN_PASSWORD environment variable is required")

# Pricing
PRICE_PER_DESIGN = 49  # ₹49 per primer design run
FREE_RUNS = 2          # 2 free runs per new user
PRICE_PER_DOCK = 99    # ₹99 per docking run
FREE_DOCK_RUNS = 2     # 2 free docking runs per new user
UPI_ID = os.environ.get("PRIMERFORGE_UPI_ID", "vigyanllm@upi")  # unused — kept for backwards compat


def _init_db_schema():
    """Initialize database and set WAL mode once at module load."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.close()
    logger.info("Database WAL mode initialized at %s", DB_PATH)

# Set WAL mode once on import (not per-request)
_init_db_schema()


def _retry_on_lock(max_attempts=3, delay=0.05):
    """Decorator: retry a function on sqlite3.OperationalError (database is locked)."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return fn(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e) and attempt < max_attempts - 1:
                        time.sleep(delay * (2 ** attempt))
                        continue
                    raise
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def get_db():
    """Get thread-local database connection."""
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH, timeout=5)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    """Close database connection."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Create tables if they don't exist."""
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT DEFAULT '',
            role TEXT DEFAULT 'user',
            run_count INTEGER DEFAULT 0,
            paid_runs INTEGER DEFAULT 0,
            dock_run_count INTEGER DEFAULT 0,
            dock_paid_runs INTEGER DEFAULT 0,
            plan TEXT DEFAULT 'free',
            billing_cycle TEXT DEFAULT 'monthly',
            plan_activated_at REAL DEFAULT 0,
            plan_expires_at REAL DEFAULT 0,
            is_academic INTEGER DEFAULT 0,
            academic_discount REAL DEFAULT 0,
            created_at REAL DEFAULT (strftime('%s','now')),
            last_login REAL DEFAULT 0,
            locked_until REAL DEFAULT 0,
            failed_attempts INTEGER DEFAULT 0,
            auth_provider TEXT DEFAULT 'email',
            google_id TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS token_blacklist (
            token_hash TEXT PRIMARY KEY,
            expires_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT DEFAULT '',
            created_at REAL DEFAULT (strftime('%s','now'))
        );

        CREATE TABLE IF NOT EXISTS daily_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            date TEXT NOT NULL,
            tool TEXT DEFAULT '',
            sequences_count INTEGER DEFAULT 0,
            created_at REAL DEFAULT (strftime('%s','now'))
        );

        CREATE TABLE IF NOT EXISTS monthly_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            year_month TEXT NOT NULL,
            api_calls INTEGER DEFAULT 0,
            created_at REAL DEFAULT (strftime('%s','now'))
        );

        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            amount INTEGER NOT NULL,
            upi_ref TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            runs_purchased INTEGER DEFAULT 1,
            product_type TEXT DEFAULT 'top_up',
            plan_id TEXT DEFAULT '',
            billing_cycle TEXT DEFAULT 'monthly',
            created_at REAL DEFAULT (strftime('%s','now')),
            verified_at REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS user_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            job_id TEXT NOT NULL,
            title TEXT DEFAULT '',
            forward_seq TEXT DEFAULT '',
            reverse_seq TEXT DEFAULT '',
            top_score REAL DEFAULT 0,
            sequence_length INTEGER DEFAULT 0,
            full_result TEXT DEFAULT '{}',
            created_at REAL DEFAULT (strftime('%s','now'))
        );

        CREATE TABLE IF NOT EXISTS academic_claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            institution TEXT NOT NULL,
            department TEXT DEFAULT '',
            use_case TEXT DEFAULT '',
            email_edu TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            tokens_granted INTEGER DEFAULT 0,
            created_at REAL DEFAULT (strftime('%s','now'))
        );

        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_email TEXT NOT NULL,
            referred_email TEXT DEFAULT '',
            referral_code TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'active',
            tokens_awarded INTEGER DEFAULT 0,
            created_at REAL DEFAULT (strftime('%s','now')),
            completed_at REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS feedback_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            context TEXT DEFAULT '',
            message TEXT NOT NULL,
            created_at REAL DEFAULT (strftime('%s','now'))
        );

        CREATE TABLE IF NOT EXISTS login_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            ip_address TEXT DEFAULT '',
            user_agent TEXT DEFAULT '',
            result TEXT DEFAULT 'success',
            created_at REAL DEFAULT (strftime('%s','now'))
        );

        CREATE TABLE IF NOT EXISTS saved_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            tool TEXT NOT NULL,
            title TEXT DEFAULT '',
            inputs TEXT DEFAULT '{}',
            outputs TEXT DEFAULT '{}',
            sequences_count INTEGER DEFAULT 0,
            job_id TEXT DEFAULT '',
            created_at REAL DEFAULT (strftime('%s','now'))
        );

        CREATE TABLE IF NOT EXISTS cookie_consents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT DEFAULT '',
            consent TEXT NOT NULL DEFAULT 'accepted',
            ip_address TEXT DEFAULT '',
            user_agent TEXT DEFAULT '',
            page_url TEXT DEFAULT '',
            accepted_at REAL NOT NULL DEFAULT (strftime('%s','now'))
        );
    """)

    # Backfill plan columns for existing users (if missing in older schema)
    try:
        db.execute("ALTER TABLE users ADD COLUMN plan TEXT DEFAULT 'free'")
    except sqlite3.OperationalError:
        pass  # column already exists
    try:
        db.execute("ALTER TABLE users ADD COLUMN billing_cycle TEXT DEFAULT 'monthly'")
    except sqlite3.OperationalError:
        pass
    try:
        db.execute("ALTER TABLE users ADD COLUMN plan_activated_at REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        db.execute("ALTER TABLE users ADD COLUMN plan_expires_at REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        db.execute("ALTER TABLE users ADD COLUMN is_academic INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        db.execute("ALTER TABLE users ADD COLUMN academic_discount REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        db.execute("ALTER TABLE users ADD COLUMN auth_provider TEXT DEFAULT 'email'")
    except sqlite3.OperationalError:
        pass
    try:
        db.execute("ALTER TABLE users ADD COLUMN google_id TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    # Backfill auth_provider for existing Google users (detected via audit log).
    # Safe to run on every init: only touches rows still marked 'email'.
    try:
        db.execute(
            """
            UPDATE users SET auth_provider = 'google'
            WHERE auth_provider = 'email' OR auth_provider IS NULL
              AND email IN (
                  SELECT DISTINCT user_email FROM usage_log WHERE action = 'google_login'
              )
            """
        )
    except sqlite3.OperationalError:
        pass
    db.commit()

    # Ensure admin exists (only if ADMIN_PASSWORD is configured)
    if ADMIN_PASSWORD:
        admin_hash = bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode()
        try:
            existing = db.execute("SELECT id FROM users WHERE email = ?", (ADMIN_EMAIL,)).fetchone()
            if existing:
                db.execute("UPDATE users SET password_hash = ?, name = ?, role = ? WHERE email = ?",
                           (admin_hash, "Admin", "admin", ADMIN_EMAIL))
            else:
                db.execute(
                    "INSERT INTO users (email, password_hash, name, role) VALUES (?, ?, ?, ?)",
                    (ADMIN_EMAIL, admin_hash, "Admin", "admin")
                )
            db.commit()
        except Exception as e:
            logger.error("Failed to create admin user: %s", e)
    else:
        logger.warning("ADMIN_PASSWORD not set — skipping admin user creation in SQLite DB")
    db.close()
    logger.info("Database initialized at %s", DB_PATH)


# ── Token Management ──────────────────────────────────────────────────────
def _sign(payload: str) -> str:
    return hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()


def create_token(email: str, role: str) -> str:
    """Create a signed session token."""
    payload = json.dumps({"email": email, "role": role, "exp": time.time() + TOKEN_EXPIRY})
    sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    import base64
    token = base64.urlsafe_b64encode(payload.encode()).decode() + "." + sig
    return token


def verify_token(token: str) -> dict:
    """Verify and decode a session token. Returns {'email','role'} or None."""
    if not token:
        return None
    try:
        import base64
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, sig = parts
        payload = base64.urlsafe_b64decode(payload_b64).decode()
        expected_sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        data = json.loads(payload)
        if data.get("exp", 0) < time.time():
            return None
        if _token_is_blacklisted(token):
            return None
        return {"email": data["email"], "role": data["role"]}
    except Exception:
        return None


def _token_is_blacklisted(token: str) -> bool:
    """Check if a token has been revoked."""
    import hashlib
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    db = get_db()
    row = db.execute("SELECT 1 FROM token_blacklist WHERE token_hash=? AND expires_at>?",
                     (token_hash, time.time())).fetchone()
    return row is not None


def revoke_token(token: str):
    """Add a token to the blacklist so it can no longer be used."""
    import hashlib
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    data = _decode_token_payload(token)
    expires_at = data.get("exp", time.time() + 3600) if data else time.time() + 3600
    db = get_db()
    db.execute("INSERT OR IGNORE INTO token_blacklist (token_hash, expires_at) VALUES (?, ?)",
               (token_hash, expires_at))
    db.commit()


def _decode_token_payload(token: str) -> dict:
    """Extract payload from a token without verifying signature."""
    try:
        import base64
        parts = token.split(".")
        if len(parts) == 2:
            payload = base64.urlsafe_b64decode(parts[0]).decode()
            return json.loads(payload)
    except Exception:
        return None


def cleanup_expired_blacklist():
    """Remove expired blacklist entries (call periodically)."""
    db = get_db()
    db.execute("DELETE FROM token_blacklist WHERE expires_at <= ?", (time.time(),))
    db.commit()


def get_current_user():
    """Extract user from Authorization header or pf_token cookie."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        user = verify_token(token)
        if user:
            return user
    cookie_token = request.cookies.get("pf_token", "")
    if cookie_token:
        return verify_token(cookie_token)
    return None


def require_auth(f):
    """Decorator: require valid auth token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Authentication required", "code": "AUTH_REQUIRED"}), 401
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


# ── Usage Checking ────────────────────────────────────────────────────────
def check_usage(email: str) -> dict:
    """Check if user can run pipeline. Returns {can_run, runs_used, free_remaining, needs_payment}."""
    db = get_db()
    row = db.execute("SELECT run_count, paid_runs FROM users WHERE email=?", (email,)).fetchone()
    if not row:
        return {"can_run": False, "error": "User not found"}
    run_count = row["run_count"]
    paid_runs = row["paid_runs"]
    total_allowed = FREE_RUNS + paid_runs
    can_run = run_count < total_allowed
    return {
        "can_run": can_run,
        "runs_used": run_count,
        "free_remaining": max(0, FREE_RUNS - run_count),
        "paid_remaining": max(0, total_allowed - run_count),
        "needs_payment": not can_run,
        "price_per_run": PRICE_PER_DESIGN,
    }


@_retry_on_lock(max_attempts=3)
def increment_usage(email: str):
    """Increment run count after successful pipeline execution."""
    db = get_db()
    db.execute("UPDATE users SET run_count = run_count + 1 WHERE email=?", (email,))
    db.execute("INSERT INTO usage_log (user_email, action, details) VALUES (?, ?, ?)",
               (email, "pipeline_run", f"Run #{db.execute('SELECT run_count FROM users WHERE email=?', (email,)).fetchone()['run_count']}"))
    db.commit()


# ── Docking Usage Checking ────────────────────────────────────────────────

def check_docking_usage(email: str) -> dict:
    """Check if user can run docking. Returns {can_run, runs_used, free_remaining, needs_payment}."""
    db = get_db()
    row = db.execute("SELECT dock_run_count, dock_paid_runs FROM users WHERE email=?", (email,)).fetchone()
    if not row:
        return {"can_run": False, "error": "User not found"}
    run_count = row["dock_run_count"]
    paid_runs = row["dock_paid_runs"]
    total_allowed = FREE_DOCK_RUNS + paid_runs
    can_run = run_count < total_allowed
    return {
        "can_run": can_run,
        "runs_used": run_count,
        "free_remaining": max(0, FREE_DOCK_RUNS - run_count),
        "paid_remaining": max(0, total_allowed - run_count),
        "needs_payment": not can_run,
        "price_per_run": PRICE_PER_DOCK,
    }


def increment_docking_usage(email: str):
    """Increment docking run count after successful job submission."""
    db = get_db()
    db.execute("UPDATE users SET dock_run_count = dock_run_count + 1 WHERE email=?", (email,))
    db.execute("INSERT INTO usage_log (user_email, action, details) VALUES (?, ?, ?)",
               (email, "docking_run", f"Dock Run #{db.execute('SELECT dock_run_count FROM users WHERE email=?', (email,)).fetchone()['dock_run_count']}"))
    db.commit()


def log_action(email: str, action: str, details: str = ""):
    """Log any user action."""
    db = get_db()
    db.execute("INSERT INTO usage_log (user_email, action, details) VALUES (?, ?, ?)",
               (email, action, details))
    db.commit()


# ── Plan-Aware Usage System ────────────────────────────────────────────────
# Used by the new subscription-based 4-tier model (Free/Pro/Lab/Enterprise)

def get_user_plan(email: str) -> str:
    """Get the user's current plan tier. Returns 'free' as default."""
    db = get_db()
    row = db.execute("SELECT plan, plan_expires_at FROM users WHERE email=?", (email,)).fetchone()
    if not row:
        return "free"
    plan = row["plan"] or "free"
    expires_at = row["plan_expires_at"] or 0
    # If plan has expired, fall back to free
    now = time.time()
    if plan != "free" and expires_at > 0 and expires_at < now:
        return "free"
    return plan


def _today_str() -> str:
    return time.strftime("%Y-%m-%d")


def _this_month_str() -> str:
    return time.strftime("%Y-%m")


def check_daily_usage(email: str, tool: str = "") -> dict:
    """Check how many analyses the user has done today."""
    db = get_db()
    today = _today_str()
    row = db.execute(
        "SELECT COALESCE(SUM(sequences_count), 0) as total FROM daily_usage WHERE user_email=? AND date=?",
        (email, today)
    ).fetchone()
    daily_used = row["total"] if row else 0

    plan = get_user_plan(email)
    from .price_registry import get_tier_limits
    limits = get_tier_limits(plan)
    daily_limit = limits["daily_analyses"]
    batch_limit = limits["batch_max_seq"]

    return {
        "plan": plan,
        "daily_limit": daily_limit,
        "daily_used": daily_used,
        "daily_remaining": max(0, daily_limit - daily_used),
        "batch_max_seq": batch_limit,
        "can_analyze": daily_used < daily_limit,
    }


def check_monthly_api_usage(email: str) -> dict:
    """Check API call usage for the current month."""
    db = get_db()
    year_month = _this_month_str()
    row = db.execute(
        "SELECT api_calls FROM monthly_usage WHERE user_email=? AND year_month=?",
        (email, year_month)
    ).fetchone()
    api_used = row["api_calls"] if row else 0

    plan = get_user_plan(email)
    from .price_registry import get_tier_limits
    limits = get_tier_limits(plan)
    api_limit = limits["api_calls_per_month"]

    return {
        "api_used": api_used,
        "api_limit": api_limit,
        "api_remaining": max(0, api_limit - api_used),
    }


@_retry_on_lock(max_attempts=3)
def record_daily_usage(email: str, tool: str = "", sequences_count: int = 1):
    """Record a usage event for daily/monthly tracking."""
    db = get_db()
    today = _today_str()
    now = time.time()
    db.execute(
        "INSERT INTO daily_usage (user_email, date, tool, sequences_count, created_at) VALUES (?, ?, ?, ?, ?)",
        (email, today, tool, sequences_count, now)
    )
    # Also increment the legacy run_count for backward compatibility
    db.execute("UPDATE users SET run_count = run_count + 1 WHERE email=?", (email,))
    db.commit()


@_retry_on_lock(max_attempts=3)
def record_api_usage(email: str, calls: int = 1):
    """Record API call usage for the current month."""
    db = get_db()
    year_month = _this_month_str()
    existing = db.execute(
        "SELECT id, api_calls FROM monthly_usage WHERE user_email=? AND year_month=?",
        (email, year_month)
    ).fetchone()
    if existing:
        db.execute(
            "UPDATE monthly_usage SET api_calls = api_calls + ? WHERE id=?",
            (calls, existing["id"])
        )
    else:
        db.execute(
            "INSERT INTO monthly_usage (user_email, year_month, api_calls) VALUES (?, ?, ?)",
            (email, year_month, calls)
        )
    db.commit()

#!/usr/bin/env python3
"""
VigyanLLM Auth + Usage + Payment Module
==========================================
- SQLite database for users, usage tracking, and payments
- bcrypt password hashing
- Session token management (simple JWT-like signed tokens)
- Admin/User role separation
- UPI payment verification flow
"""

import os
import sqlite3
import hashlib
import hmac
import time
import json
import logging
from pathlib import Path
from functools import wraps

import bcrypt
from flask import request, jsonify, g

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
UPI_ID = os.environ.get("PRIMERFORGE_UPI_ID", "vigyanllm@upi")


def get_db():
    """Get thread-local database connection."""
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
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
            created_at REAL DEFAULT (strftime('%s','now')),
            last_login REAL DEFAULT 0
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

        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            amount INTEGER NOT NULL,
            upi_ref TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            runs_purchased INTEGER DEFAULT 1,
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
    """)

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
    logger.info(f"Database initialized at {DB_PATH}")


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
    token = ""
    if auth.startswith("Bearer "):
        token = auth[7:]
    elif request.cookies.get("pf_token"):
        token = request.cookies.get("pf_token", "")
    if token:
        return verify_token(token)
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
        "upi_id": UPI_ID,
    }


def increment_usage(email: str):
    """Increment run count after successful pipeline execution."""
    db = get_db()
    db.execute("UPDATE users SET run_count = run_count + 1 WHERE email=?", (email,))
    db.execute("INSERT INTO usage_log (user_email, action, details) VALUES (?, ?, ?)",
               (email, "pipeline_run", f"Run #{db.execute('SELECT run_count FROM users WHERE email=?', (email,)).fetchone()['run_count']}"))
    db.commit()


def log_action(email: str, action: str, details: str = ""):
    """Log any user action."""
    db = get_db()
    db.execute("INSERT INTO usage_log (user_email, action, details) VALUES (?, ?, ?)",
               (email, action, details))
    db.commit()

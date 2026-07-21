#!/usr/bin/env python3
"""
VigyanLLM Auth API Routes
=============================
POST /api/auth/register  — Create new user account
POST /api/auth/login     — Login and get token
GET  /api/auth/me        — Get current user info + usage
GET  /api/admin/users    — Admin: list all users
GET  /api/admin/logs     — Admin: usage logs
GET  /api/admin/payments — Admin: payment history
GET  /api/admin/stats    — Admin: system stats
"""

import time

import bcrypt
from flask import Blueprint, g, jsonify, request

from .auth import (
    ADMIN_EMAIL,
    FREE_RUNS,
    PRICE_PER_DESIGN,
    check_usage,
    create_token,
    get_db,
    log_action,
    require_admin,
    require_auth,
)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    from .security import sanitize_string, validate_email, validate_password

    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password', '')
    name = sanitize_string(data.get('name', '').strip(), max_length=100)

    valid_email, email_err = validate_email(email)
    if not valid_email:
        return jsonify({"error": email_err}), 422
    valid_pw, pw_err = validate_password(password)
    if not valid_pw:
        return jsonify({"error": pw_err}), 422

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if existing:
        return jsonify({"error": "Email already registered. Please login."}), 409

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    db.execute(
        "INSERT INTO users (email, password_hash, name, role) VALUES (?, ?, ?, ?)",
        (email, pw_hash, name, "user")
    )
    db.commit()

    token = create_token(email, "user")
    log_action(email, "register", "New account created")

    return jsonify({
        "token": token,
        "user": {"email": email, "name": name, "role": "user"},
        "message": "Account created successfully."
    }), 201


LOCKOUT_THRESHOLDS = [
    {"attempts": 3, "lockout_seconds": 60},
    {"attempts": 5, "lockout_seconds": 300},
    {"attempts": 10, "lockout_seconds": 3600},
    {"attempts": 20, "lockout_seconds": 86400},
]


def _apply_login_lockout(db, email):
    """Check and apply progressive lockout on failed login."""
    row = db.execute(
        "SELECT locked_until, failed_attempts FROM users WHERE email=?",
        (email,)
    ).fetchone()
    if not row:
        return None

    locked_until = row["locked_until"] or 0
    now = time.time()

    if locked_until > now:
        remaining = int(locked_until - now)
        return {"error": f"Account temporarily locked. Try again in {remaining} seconds."}

    failed = (row["failed_attempts"] or 0) + 1
    lockout_seconds = 0
    for t in reversed(LOCKOUT_THRESHOLDS):
        if failed >= t["attempts"]:
            lockout_seconds = t["lockout_seconds"]
            break

    if lockout_seconds > 0:
        locked_until = now + lockout_seconds
        db.execute(
            "UPDATE users SET failed_attempts=?, locked_until=? WHERE email=?",
            (failed, locked_until, email)
        )
        db.commit()
        return {"error": f"Account temporarily locked. Try again in {lockout_seconds} seconds."}

    db.execute(
        "UPDATE users SET failed_attempts=? WHERE email=?",
        (failed, email)
    )
    db.commit()
    return None


def _clear_lockout(db, email):
    """Clear lockout state on successful login."""
    db.execute(
        "UPDATE users SET failed_attempts=0, locked_until=0 WHERE email=?",
        (email,)
    )
    db.commit()


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    db = get_db()
    row = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not row:
        return jsonify({"error": "Invalid email or password."}), 401

    lock_result = _apply_login_lockout(db, email)
    if lock_result:
        return jsonify(lock_result), 429

    if not bcrypt.checkpw(password.encode(), row['password_hash'].encode()):
        return jsonify({"error": "Invalid email or password."}), 401

    _clear_lockout(db, email)

    role = row['role']
    token = create_token(email, role)
    log_action(email, "login", f"Role: {role}")

    usage = check_usage(email)

    resp = jsonify({
        "token": token,
        "user": {"email": email, "name": row['name'], "role": role},
        "usage": usage,
        "is_admin": role == "admin",
    })
    resp.set_cookie(
        'pf_token', token,
        httponly=True, secure=True, samesite='Lax',
        max_age=86400 * 7, path='/'
    )
    return resp, 200


@auth_bp.route('/api/auth/me', methods=['GET'])
@require_auth
def me():
    user = g.user
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE email=?", (user['email'],)).fetchone()
    if not row:
        return jsonify({"error": "User not found."}), 404

    usage = check_usage(user['email'])
    return jsonify({
        "user": {
            "email": row['email'], "name": row['name'], "role": row['role'],
            "run_count": row['run_count'], "paid_runs": row['paid_runs'],
            "created_at": row['created_at'],
        },
        "usage": usage,
        "is_admin": row['role'] == "admin",
    }), 200


@auth_bp.route('/api/auth/check-usage', methods=['GET'])
@require_auth
def check_usage_route():
    usage = check_usage(g.user['email'])
    return jsonify(usage), 200


@auth_bp.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    """Revoke the current token."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        from primerforge.auth import revoke_token
        revoke_token(auth[7:])
    resp = jsonify({"message": "Logged out successfully."})
    resp.set_cookie('pf_token', '', httponly=True, secure=True, samesite='None', max_age=0, path='/')
    return resp, 200


@auth_bp.route('/api/auth/google', methods=['POST'])
def google_auth():
    """Verify Google OAuth2 credential or access token and create/login user."""
    import requests as http_requests
    data = request.get_json(silent=True) or {}
    credential = data.get('credential', '')
    access_token = data.get('access_token', '')

    if credential and isinstance(credential, str):
        try:
            r = http_requests.get(
                'https://oauth2.googleapis.com/tokeninfo',
                params={'id_token': credential},
                timeout=10
            )
            if r.status_code != 200:
                return jsonify({"error": "Invalid Google credential."}), 401
            ginfo = r.json()
            if not ginfo.get('email'):
                return jsonify({"error": "Could not retrieve email from Google credential."}), 400
        except Exception as e:
            return jsonify({"error": f"Google verification failed: {e!s}"}), 500
    elif access_token and isinstance(access_token, str):
        try:
            r = http_requests.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10
            )
            if r.status_code != 200:
                return jsonify({"error": "Invalid Google token."}), 401
            ginfo = r.json()
        except Exception as e:
            return jsonify({"error": f"Google verification failed: {e!s}"}), 500
    else:
        return jsonify({"error": "Google credential or access token is required."}), 400

    email = ginfo.get('email', '').strip().lower()
    name = ginfo.get('name', '')

    if not email:
        return jsonify({"error": "Could not retrieve email from Google."}), 400

    db = get_db()
    row = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()

    if row:
        # Existing user — login
        role = row['role']
        db.execute("UPDATE users SET last_login=? WHERE email=?", (time.time(), email))
        db.commit()
    else:
        # New user — register via Google
        # Generate a random password hash (user won't use password login)
        import os as _os
        random_pw = _os.urandom(24).hex()
        pw_hash = bcrypt.hashpw(random_pw.encode(), bcrypt.gensalt()).decode()
        role = "admin" if email == ADMIN_EMAIL else "user"
        db.execute(
            "INSERT INTO users (email, password_hash, name, role) VALUES (?, ?, ?, ?)",
            (email, pw_hash, name, role)
        )
        db.commit()

    token = create_token(email, role)
    log_action(email, "google_login", f"Name: {name}")
    usage = check_usage(email)

    return jsonify({
        "token": token,
        "user": {"email": email, "name": name, "role": role},
        "usage": usage,
        "is_admin": role == "admin",
    }), 200


# ═══════════════════════════════════════════════════════════════════════════
# ADMIN ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@auth_bp.route('/api/admin/users', methods=['GET'])
@require_admin
def admin_users():
    db = get_db()
    rows = db.execute("SELECT id, email, name, role, run_count, paid_runs, created_at, last_login FROM users ORDER BY created_at DESC").fetchall()
    users = [dict(r) for r in rows]
    return jsonify({"users": users, "total": len(users)}), 200


@auth_bp.route('/api/admin/logs', methods=['GET'])
@require_admin
def admin_logs():
    db = get_db()
    limit = request.args.get('limit', 100, type=int)
    rows = db.execute("SELECT * FROM usage_log ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    logs = [dict(r) for r in rows]
    return jsonify({"logs": logs, "total": len(logs)}), 200


@auth_bp.route('/api/admin/payments', methods=['GET'])
@require_admin
def admin_payments():
    db = get_db()
    rows = db.execute("SELECT * FROM payments ORDER BY created_at DESC").fetchall()
    payments = [dict(r) for r in rows]
    total_revenue = sum(p['amount'] for p in payments if p['status'] == 'verified')
    return jsonify({"payments": payments, "total": len(payments), "total_revenue": total_revenue}), 200


@auth_bp.route('/api/admin/stats', methods=['GET'])
@require_admin
def admin_stats():
    db = get_db()
    total_users = db.execute("SELECT COUNT(*) as c FROM users").fetchone()['c']
    total_runs = db.execute("SELECT SUM(run_count) as c FROM users").fetchone()['c'] or 0
    total_revenue = db.execute("SELECT SUM(amount) as c FROM payments WHERE status='verified'").fetchone()['c'] or 0
    total_payments = db.execute("SELECT COUNT(*) as c FROM payments WHERE status='verified'").fetchone()['c']
    active_today = db.execute("SELECT COUNT(*) as c FROM users WHERE last_login > ?", (time.time() - 86400,)).fetchone()['c']

    return jsonify({
        "total_users": total_users,
        "total_runs": total_runs,
        "total_revenue": total_revenue,
        "total_payments": total_payments,
        "active_today": active_today,
        "free_runs_per_user": FREE_RUNS,
        "price_per_design": PRICE_PER_DESIGN,
    }), 200

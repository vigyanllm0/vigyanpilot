#!/usr/bin/env python3
"""
VigyanLLM Auth API Routes
=============================
POST /api/auth/register  — Create new user account
POST /api/auth/login     — Login and get token
GET  /api/auth/me        — Get current user info + usage
POST /api/auth/verify-payment — Verify UPI payment & unlock runs
GET  /api/admin/users    — Admin: list all users
GET  /api/admin/logs     — Admin: usage logs
GET  /api/admin/payments — Admin: payment history
GET  /api/admin/stats    — Admin: system stats
"""

import bcrypt
import time
from flask import Blueprint, request, jsonify, g

from .auth import (
    get_db, get_current_user, require_auth, require_admin,
    create_token, check_usage, increment_usage, log_action,
    ADMIN_EMAIL, PRICE_PER_DESIGN, UPI_ID, FREE_RUNS
)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    from .security import validate_email, validate_password, sanitize_string

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

    if not bcrypt.checkpw(password.encode(), row['password_hash'].encode()):
        return jsonify({"error": "Invalid email or password."}), 401

    # Update last login
    db.execute("UPDATE users SET last_login=? WHERE email=?", (time.time(), email))
    db.commit()

    role = row['role']
    token = create_token(email, role)
    log_action(email, "login", f"Role: {role}")

    usage = check_usage(email)

    return jsonify({
        "token": token,
        "user": {"email": email, "name": row['name'], "role": role},
        "usage": usage,
        "is_admin": role == "admin",
    }), 200


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


@auth_bp.route('/api/auth/google', methods=['POST'])
def google_auth():
    """Verify Google OAuth2 access token and create/login user."""
    import requests as http_requests
    data = request.get_json(silent=True) or {}
    access_token = data.get('access_token', '')

    if not access_token:
        return jsonify({"error": "Google access token is required."}), 400

    # Verify token with Google's userinfo endpoint
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
        return jsonify({"error": f"Google verification failed: {str(e)}"}), 500

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


@auth_bp.route('/api/auth/verify-payment', methods=['POST'])
@require_auth
def verify_payment():
    """User submits UPI transaction reference to unlock runs."""
    data = request.get_json(silent=True) or {}
    upi_ref = (data.get('upi_ref') or '').strip()
    runs = int(data.get('runs', 1))

    if not upi_ref or len(upi_ref) < 6:
        return jsonify({"error": "Valid UPI transaction reference is required."}), 400
    if runs < 1 or runs > 100:
        return jsonify({"error": "Runs must be between 1 and 100."}), 400

    email = g.user['email']
    db = get_db()

    # Check for duplicate UPI ref
    existing = db.execute("SELECT id FROM payments WHERE upi_ref=?", (upi_ref,)).fetchone()
    if existing:
        return jsonify({"error": "This transaction reference has already been used."}), 409

    # Record payment
    amount = PRICE_PER_DESIGN * runs
    db.execute(
        "INSERT INTO payments (user_email, amount, upi_ref, status, runs_purchased, verified_at) VALUES (?, ?, ?, ?, ?, ?)",
        (email, amount, upi_ref, "verified", runs, time.time())
    )
    # Credit runs to user
    db.execute("UPDATE users SET paid_runs = paid_runs + ? WHERE email=?", (runs, email))
    db.commit()

    log_action(email, "payment_verified", f"₹{amount} for {runs} run(s), UTR: {upi_ref}")

    usage = check_usage(email)
    return jsonify({
        "message": f"Payment verified. {runs} run(s) unlocked.",
        "amount": amount,
        "runs_purchased": runs,
        "usage": usage,
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
        "upi_id": UPI_ID,
    }), 200

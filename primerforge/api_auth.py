"""API key authentication for VigyanLLM developer portal."""
import hashlib
import secrets
import time
import os
from functools import wraps

from flask import request, jsonify, g
import psycopg2


def generate_api_key():
    """Generate a new API key. Returns (full_key, key_hash, key_prefix)."""
    prefix = "vl_live_"
    raw = secrets.token_urlsafe(32)
    full_key = prefix + raw
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, key_hash, full_key[:16]


def get_db_connection():
    """Get database connection (PG)."""
    url = os.environ.get('DATABASE_URL', '')
    if not url:
        raise RuntimeError('DATABASE_URL not set')
    return psycopg2.connect(url)


def verify_api_key(conn, full_key):
    """Verify an API key and return the key record."""
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    cur = conn.cursor()
    cur.execute("""
        SELECT ak.*, u.email, u.plan
        FROM api_keys ak
        JOIN users u ON ak.user_id = u.id
        WHERE ak.key_hash = %s AND ak.is_active = TRUE
        AND (ak.expires_at IS NULL OR ak.expires_at > EXTRACT(EPOCH FROM NOW()))
    """, (key_hash,))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE api_keys SET last_used_at = EXTRACT(EPOCH FROM NOW()) WHERE id = %s", (row[0],))
        conn.commit()
    return row


def require_api_key(f):
    """Decorator: require valid API key in Authorization header."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer vl_live_'):
            return jsonify({'error': 'Missing or invalid API key. Use Authorization: Bearer vl_live_...'}), 401

        full_key = auth[7:]  # Remove "Bearer "
        conn = get_db_connection()
        try:
            key_record = verify_api_key(conn, full_key)
            if not key_record:
                return jsonify({'error': 'Invalid or expired API key'}), 401
            g.api_key_id = key_record[0]
            g.api_user_id = key_record[1]
            g.api_user_email = key_record[-2]  # email from JOIN
            g.api_user_plan = key_record[-1]   # plan from JOIN
            g.api_key_scopes = key_record[5]   # scopes JSONB
        finally:
            conn.close()
        return f(*args, **kwargs)
    return decorated


def check_rate_limit(conn, key_id, limit):
    """Check if API key has exceeded rate limit (per minute)."""
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM api_usage_logs
        WHERE api_key_id = %s AND created_at > EXTRACT(EPOCH FROM NOW()) - 60
    """, (key_id,))
    count = cur.fetchone()[0]
    return count < limit


def record_api_usage(conn, key_id, endpoint, method, status_code, latency_ms):
    """Record API usage."""
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO api_usage_logs (api_key_id, endpoint, method, status_code, latency_ms)
        VALUES (%s, %s, %s, %s, %s)
    """, (key_id, endpoint, method, status_code, latency_ms))
    conn.commit()

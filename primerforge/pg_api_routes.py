"""API Management routes for VigyanLLM developer portal."""
from flask import Blueprint, request, jsonify, g
import hashlib, secrets, json, time
from .api_auth import require_api_key, get_db_connection, generate_api_key

api_bp = Blueprint('api_management', __name__)

# ─── API Key Management ───

@api_bp.route('/api/developer/keys', methods=['GET'])
@require_api_key
def list_keys():
    """List all API keys for the authenticated user."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, key_prefix, name, scopes, rate_limit, is_active, created_at, last_used_at, expires_at
            FROM api_keys WHERE user_id = %s ORDER BY created_at DESC
        """, (g.api_user_id,))
        keys = []
        for row in cur.fetchall():
            keys.append({
                'id': row[0], 'key_prefix': row[1], 'name': row[2],
                'scopes': row[3], 'rate_limit': row[4], 'is_active': row[5],
                'created_at': row[6], 'last_used_at': row[7], 'expires_at': row[8]
            })
        return jsonify({'keys': keys})
    finally:
        conn.close()


@api_bp.route('/api/developer/keys', methods=['POST'])
@require_api_key
def create_key():
    """Generate a new API key."""
    data = request.get_json() or {}
    name = data.get('name', 'API Key')
    scopes = data.get('scopes', ['primer', 'blast', 'msa'])
    rate_limit = data.get('rate_limit', 60)

    full_key, key_hash, key_prefix = generate_api_key()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO api_keys (user_id, key_hash, key_prefix, name, scopes, rate_limit)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """, (g.api_user_id, key_hash, key_prefix, name, json.dumps(scopes), rate_limit))
        key_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({
            'id': key_id, 'key': full_key, 'key_prefix': key_prefix,
            'name': name, 'scopes': scopes, 'rate_limit': rate_limit,
            'message': 'Save this key — it will not be shown again'
        }), 201
    finally:
        conn.close()


@api_bp.route('/api/developer/keys/<int:key_id>', methods=['DELETE'])
@require_api_key
def revoke_key(key_id):
    """Revoke (deactivate) an API key."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE api_keys SET is_active = FALSE WHERE id = %s AND user_id = %s",
                    (key_id, g.api_user_id))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({'error': 'Key not found'}), 404
        return jsonify({'message': 'Key revoked'})
    finally:
        conn.close()


@api_bp.route('/api/developer/keys/<int:key_id>/rotate', methods=['POST'])
@require_api_key
def rotate_key(key_id):
    """Rotate an API key (generates new, revokes old)."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT name, scopes, rate_limit FROM api_keys WHERE id = %s AND user_id = %s",
                    (key_id, g.api_user_id))
        row = cur.fetchone()
        if not row:
            return jsonify({'error': 'Key not found'}), 404
        # Deactivate old
        cur.execute("UPDATE api_keys SET is_active = FALSE WHERE id = %s", (key_id,))
        # Generate new
        full_key, key_hash, key_prefix = generate_api_key()
        cur.execute("""
            INSERT INTO api_keys (user_id, key_hash, key_prefix, name, scopes, rate_limit)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """, (g.api_user_id, key_hash, key_prefix, row[0], json.dumps(row[1]), row[2]))
        new_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({
            'id': new_id, 'key': full_key, 'key_prefix': key_prefix,
            'name': row[0], 'message': 'Save this key — old key has been revoked'
        })
    finally:
        conn.close()

# ─── API Usage Analytics ───

@api_bp.route('/api/developer/usage', methods=['GET'])
@require_api_key
def usage_stats():
    """Get API usage statistics for the authenticated user."""
    days = request.args.get('days', 30, type=int)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Daily usage
        cur.execute("""
            SELECT DATE(to_timestamp(created_at)) as day, COUNT(*) as calls, AVG(latency_ms) as avg_latency
            FROM api_usage_logs a
            JOIN api_keys k ON a.api_key_id = k.id
            WHERE k.user_id = %s AND a.created_at > EXTRACT(EPOCH FROM NOW()) - %s * 86400
            GROUP BY day ORDER BY day
        """, (g.api_user_id, days))
        daily = [{'date': str(r[0]), 'calls': r[1], 'avg_latency_ms': round(r[2], 1)}
                 for r in cur.fetchall()]

        # Top endpoints
        cur.execute("""
            SELECT endpoint, COUNT(*) as calls, AVG(latency_ms) as avg_latency,
                   SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as errors
            FROM api_usage_logs a JOIN api_keys k ON a.api_key_id = k.id
            WHERE k.user_id = %s AND a.created_at > EXTRACT(EPOCH FROM NOW()) - %s * 86400
            GROUP BY endpoint ORDER BY calls DESC LIMIT 10
        """, (g.api_user_id, days))
        endpoints = [{'endpoint': r[0], 'calls': r[1], 'avg_latency_ms': round(r[2], 1), 'errors': r[3]}
                     for r in cur.fetchall()]

        # Total stats
        cur.execute("""
            SELECT COUNT(*) as total, AVG(latency_ms) as avg_latency,
                   SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as errors
            FROM api_usage_logs a JOIN api_keys k ON a.api_key_id = k.id
            WHERE k.user_id = %s AND a.created_at > EXTRACT(EPOCH FROM NOW()) - %s * 86400
        """, (g.api_user_id, days))
        totals = cur.fetchone()

        return jsonify({
            'total_calls': totals[0] or 0,
            'avg_latency_ms': round(totals[1] or 0, 1),
            'error_count': totals[2] or 0,
            'error_rate': round((totals[2] or 0) / max(totals[0] or 1, 1) * 100, 1),
            'daily': daily,
            'top_endpoints': endpoints
        })
    finally:
        conn.close()

# ─── Webhook Management ───

@api_bp.route('/api/developer/webhooks', methods=['GET'])
@require_api_key
def list_webhooks():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, url, events, is_active, created_at FROM webhooks WHERE user_id = %s ORDER BY created_at DESC",
                    (g.api_user_id,))
        hooks = [{'id': r[0], 'url': r[1], 'events': r[2], 'is_active': r[3], 'created_at': r[4]}
                 for r in cur.fetchall()]
        return jsonify({'webhooks': hooks})
    finally:
        conn.close()


@api_bp.route('/api/developer/webhooks', methods=['POST'])
@require_api_key
def create_webhook():
    data = request.get_json() or {}
    url = data.get('url', '')
    events = data.get('events', ['primer.complete'])
    secret = 'whsec_' + secrets.token_urlsafe(32)
    if not url:
        return jsonify({'error': 'URL required'}), 400
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO webhooks (user_id, url, events, secret) VALUES (%s, %s, %s, %s) RETURNING id",
                    (g.api_user_id, url, json.dumps(events), secret))
        hook_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({
            'id': hook_id, 'url': url, 'events': events, 'secret': secret,
            'message': 'Save this secret — it will not be shown again'
        }), 201
    finally:
        conn.close()


@api_bp.route('/api/developer/webhooks/<int:hook_id>', methods=['DELETE'])
@require_api_key
def delete_webhook(hook_id):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM webhooks WHERE id = %s AND user_id = %s", (hook_id, g.api_user_id))
        conn.commit()
        return jsonify({'message': 'Webhook deleted'})
    finally:
        conn.close()


@api_bp.route('/api/developer/webhooks/<int:hook_id>/test', methods=['POST'])
@require_api_key
def test_webhook(hook_id):
    """Send a test payload to a webhook."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT url, secret FROM webhooks WHERE id = %s AND user_id = %s",
                    (hook_id, g.api_user_id))
        row = cur.fetchone()
        if not row:
            return jsonify({'error': 'Webhook not found'}), 404
        import hmac, hashlib, requests
        payload = json.dumps({
            'event': 'test',
            'timestamp': int(time.time()),
            'data': {'message': 'Test webhook from VigyanLLM'}
        })
        sig = hmac.new(row[1].encode(), payload.encode(), hashlib.sha256).hexdigest()
        try:
            resp = requests.post(row[0], data=payload, headers={
                'Content-Type': 'application/json',
                'X-VigyanLLM-Signature': sig
            }, timeout=10)
            return jsonify({'status_code': resp.status_code, 'success': resp.ok, 'response': resp.text[:500]})
        except Exception as e:
            return jsonify({'error': str(e), 'success': False}), 502
    finally:
        conn.close()

# ─── External API (v1) ───

@api_bp.route('/api/v1/primer/design', methods=['POST'])
@require_api_key
def api_v1_primer_design():
    """External API: Design primers."""
    data = request.get_json() or {}
    sequence = data.get('sequence', '')
    if not sequence:
        return jsonify({'error': 'sequence required'}), 400
    # Rate limit check
    conn = get_db_connection()
    try:
        from .api_auth import check_rate_limit, record_api_usage
        if not check_rate_limit(conn, g.api_key_id, 60):
            return jsonify({'error': 'Rate limit exceeded (60/min)'}), 429
    finally:
        conn.close()
    # TODO: integrate with actual primer design pipeline
    return jsonify({'status': 'queued', 'message': 'Primer design accepted', 'api_version': 'v1'})


@api_bp.route('/api/v1/blast/search', methods=['POST'])
@require_api_key
def api_v1_blast_search():
    """External API: Run BLAST search."""
    return jsonify({'status': 'queued', 'message': 'BLAST search accepted', 'api_version': 'v1'})


@api_bp.route('/api/v1/msa/align', methods=['POST'])
@require_api_key
def api_v1_msa_align():
    """External API: Run MSA alignment."""
    return jsonify({'status': 'queued', 'message': 'MSA alignment accepted', 'api_version': 'v1'})


@api_bp.route('/api/v1/openapi.json', methods=['GET'])
def api_v1_openapi():
    """Serve OpenAPI spec."""
    import os
    spec_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'api', 'openapi.json')
    if os.path.exists(spec_path):
        with open(spec_path) as f:
            return jsonify(json.load(f))
    return jsonify({'error': 'OpenAPI spec not found'}), 404

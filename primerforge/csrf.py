"""CSRF protection middleware for VigyanLLM."""
import secrets
import hmac
from functools import wraps
from flask import request, jsonify, session


def generate_csrf_token():
    """Generate a CSRF token and store it in the session."""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']


def validate_csrf(f):
    """Decorator that validates CSRF token on state-changing requests."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            token = (
                request.headers.get('X-CSRF-Token')
                or (request.get_json(silent=True) or {}).get('_csrf_token')
            )
            if not token or not hmac.compare_digest(token, session.get('_csrf_token', '')):
                return jsonify({'error': 'CSRF token invalid or missing'}), 403
        return f(*args, **kwargs)
    return decorated


def init_csrf(app):
    """Initialize CSRF protection on the Flask app.

    Generates tokens, sets a readable cookie, and provides /api/csrf-token.
    Does NOT enforce validation globally — use @validate_csrf on specific routes.
    """
    app.secret_key = app.config.get('SECRET_KEY', secrets.token_hex(32))

    @app.before_request
    def set_csrf_token():
        if '_csrf_token' not in session:
            session['_csrf_token'] = secrets.token_hex(32)

    @app.after_request
    def inject_csrf_cookie(response):
        if '_csrf_token' in session:
            response.set_cookie(
                'csrf_token',
                session['_csrf_token'],
                httponly=False,
                secure=True,
                samesite='Lax',
                path='/',
            )
        return response

    @app.route('/api/csrf-token', methods=['GET'])
    def csrf_token():
        return jsonify({'token': session.get('_csrf_token', '')})

#!/usr/bin/env python3
"""
VigyanLLM Security Middleware (Production-Hardened)
=====================================================
This module initialises all security layers on the Flask application.

Layers applied (in order):
  1. Request body size limit (10 MB max)
  2. HTTP security headers via flask-talisman (CSP, HSTS, X-Frame-Options)
  3. Redis-backed rate limiting via flask-limiter (memory fallback for dev)
  4. Custom error handlers (429, 413, 500) — no stack traces to clients
  5. CORS header injection (after_request)
  6. Admin RBAC middleware (before_request, defense-in-depth)

Input validation utilities:
  validate_email()    — RFC-5321 format check + length guard
  validate_password() — complexity policy (uppercase, digit, special char)
  validate_quantity() — reject floats/NaN/Infinity
  sanitize_string()   — bleach HTML strip + length cap

Security contacts: security@vigyanllm.in
"""

import logging
import math
import os
import re

import bleach
from flask import jsonify, request

try:
    from flask_talisman import Talisman
except ImportError:  # pragma: no cover - exercised when optional dev deps are absent
    Talisman = None

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except ImportError:  # pragma: no cover - exercised when optional dev deps are absent
    Limiter = None

    def get_remote_address():
        return request.remote_addr or "127.0.0.1"

logger = logging.getLogger("primerforge.security")

# ── Environment Detection ─────────────────────────────────────────────────
# IS_PRODUCTION is True when FORCE_HTTPS=true OR VIGYANLLM_ENV=production.
# Both flags must be explicitly set — the app never auto-detects "production"
# from DATABASE_URL or other indirect signals to prevent accidental exposure.
IS_PRODUCTION = (
    os.environ.get("FORCE_HTTPS", "").lower() == "true"
    or os.environ.get("VIGYANLLM_ENV", "").lower() == "production"
)
FORCE_HTTPS = os.environ.get("FORCE_HTTPS", "").lower() == "true"
REDIS_URL = os.environ.get("REDIS_URL", "")  # e.g. redis://:password@host:6379/0
ALLOWED_ORIGINS = os.environ.get("CORS_ORIGINS", "").split(",") if os.environ.get("CORS_ORIGINS") else None
MAX_SESSIONS_PER_USER = int(os.environ.get("MAX_SESSIONS", "5"))

_PRODUCTION_REQUIRED_ENV = (
    "DATABASE_URL",
    "PRIMERFORGE_SECRET",
    "RAZORPAY_KEY_ID",
    "RAZORPAY_KEY_SECRET",
    "RAZORPAY_WEBHOOK_SECRET",
)


def validate_production_environment():
    """Fail fast when production mode is enabled without required secrets/services."""
    if not IS_PRODUCTION:
        return

    missing = [name for name in _PRODUCTION_REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        raise RuntimeError(
            "FORCE_HTTPS=true requires production environment variables: "
            + ", ".join(missing)
        )

    if not get_production_origins():
        raise RuntimeError("FORCE_HTTPS=true requires at least one CORS origin")


def get_production_origins():
    """Return CORS origins based on environment."""
    if ALLOWED_ORIGINS:
        return [o.strip() for o in ALLOWED_ORIGINS if o.strip()]
    # Production domains — always included regardless of mode
    origins = [
        "https://vigyanllm.in",
        "https://www.vigyanllm.in",
        "https://app.vigyanllm.in",
    ]
    if not IS_PRODUCTION:
        origins += [
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://localhost:11436",
            "http://127.0.0.1:11436",
            "http://localhost:3000",
            "http://localhost:5500",
            "http://127.0.0.1:5500",
            "https://vigyanpilot.vercel.app",
            "null",  # file:// protocol
        ]
    return origins


def _get_rate_limit_storage() -> str:
    """
    Return the rate-limiter storage URI.

    Uses Redis when REDIS_URL is configured (required for multi-worker production
    deployments so all Gunicorn workers share the same counter). Falls back to
    in-memory storage for single-worker development.

    BUG-16 FIX: Redis URL is logged with the password masked, regardless of
    whether the URL contains an '@' character.
    """
    if REDIS_URL:
        # Safely mask password from redis://[:password@]host:port/db
        try:
            from urllib.parse import urlparse
            parsed = urlparse(REDIS_URL)
            display = f"{parsed.hostname}:{parsed.port}/{parsed.path.lstrip('/')}"
        except Exception:
            display = "<redis-url-masked>"
        logger.info("Rate limiter: Redis (%s)", display)
        return REDIS_URL
    logger.info("Rate limiter: in-memory (single-worker only)")
    return "memory://"


def init_security(app):
    """Initialize all security layers on the Flask app."""
    validate_production_environment()

    # ── 1. Request Body Size Limit (10MB max) ─────────────────────────────
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB

    # ── 2. Security Headers via Talisman ──────────────────────────────────
    csp = {
        "default-src": "'self'",
        "script-src": [
            "'self'",
            "https://checkout.razorpay.com",
            "https://api.razorpay.com",
            "https://accounts.google.com",
            "'unsafe-inline'",
        ],
        "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
        "font-src": ["'self'", "https://fonts.gstatic.com"],
        "img-src": ["'self'", "data:", "https:"],
        "connect-src": [
            "'self'",
            "https://api.razorpay.com",
            "https://lumberjack.razorpay.com",
            "https://accounts.google.com",
            "https://www.googleapis.com",
        ],
        "frame-src": ["https://api.razorpay.com", "https://checkout.razorpay.com", "https://accounts.google.com"],
    }

    if Talisman is None:
        if IS_PRODUCTION:
            raise RuntimeError("flask-talisman is required when FORCE_HTTPS=true")
        logger.warning("flask-talisman not installed — using development security headers fallback.")
        _register_security_header_fallback(app, csp)
    else:
        Talisman(
            app,
            force_https=FORCE_HTTPS,
            force_https_permanent=False,
            strict_transport_security=True,
            strict_transport_security_max_age=31536000,
            strict_transport_security_include_subdomains=True,
            content_security_policy=csp,
            x_content_type_options=True,
            x_xss_protection=True,
            frame_options="DENY",
            referrer_policy="strict-origin-when-cross-origin",
            session_cookie_secure=FORCE_HTTPS,
            session_cookie_http_only=True,
        )

    # Always suppress Server header — Talisman does not do this.
    # Use a separate after_request so it runs even when Talisman
    # registers its own after_request chain.
    @app.after_request
    def _suppress_server(response):
        if "Server" in response.headers:
            del response.headers["Server"]
        if "Strict-Transport-Security" not in response.headers:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # ── 3. Rate Limiting (Redis-backed in production) ─────────────────────
    storage_uri = _get_rate_limit_storage()
    if Limiter is None:
        if IS_PRODUCTION:
            raise RuntimeError("flask-limiter is required when FORCE_HTTPS=true")
        logger.warning("flask-limiter not installed — rate limiting disabled for development.")
        limiter = _NoopLimiter()
    else:
        limiter = Limiter(
            key_func=get_remote_address,
            app=app,
            default_limits=["200 per minute", "5000 per hour"],
            storage_uri=storage_uri,
        )

    app.extensions["limiter"] = limiter

    # ── 4. Custom error handlers ──────────────────────────────────────────
    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return jsonify({
            "error": "Too many requests. Please slow down.",
            "code": "RATE_LIMITED",
        }), 429

    @app.errorhandler(413)
    def request_too_large(e):
        return jsonify({
            "error": "Request body too large. Maximum 10MB.",
            "code": "PAYLOAD_TOO_LARGE",
        }), 413

    @app.errorhandler(500)
    def internal_error(e):
        """Never expose stack traces or exception types to clients (SEC-10)."""
        logger.error("Internal server error: %s", e, exc_info=True)
        return jsonify({
            "error": "An internal error occurred. Please try again later.",
            "code": "INTERNAL_ERROR",
        }), 500

    logger.info("Security initialized (production=%s, https=%s)", IS_PRODUCTION, FORCE_HTTPS)
    return limiter


def apply_rate_limits(app):
    """Apply endpoint-specific rate limits AFTER blueprint registration."""
    limiter = app.extensions.get("limiter")
    if limiter and not isinstance(limiter, _NoopLimiter):
        endpoint_map = {
            "auth.login": "5 per minute",
            "auth.register": "3 per minute",
            "payments.verify_payment": "10 per minute",
            "payments.create_order": "10 per minute",
        }
        for endpoint, limit_str in endpoint_map.items():
            fn = app.view_functions.get(endpoint)
            if fn:
                app.view_functions[endpoint] = limiter.limit(limit_str)(fn)
                logger.debug("Rate limit %s applied to %s", limit_str, endpoint)

        logger.info("Rate limits applied to sensitive endpoints.")
    else:
        logger.warning("Rate limiting disabled — endpoint-specific limits skipped.")


class _NoopLimiter:
    """Development fallback used when flask-limiter is not installed."""

    def limit(self, *_args, **_kwargs):
        def decorator(func):
            return func

        return decorator


def _register_security_header_fallback(app, csp):
    """Apply security headers when Talisman is unavailable in development."""
    csp_value = _format_csp(csp)

    @app.after_request
    def _security_headers(response):
        response.headers.setdefault("Content-Security-Policy", csp_value)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if "Server" in response.headers:
            del response.headers["Server"]
        return response


def _format_csp(csp):
    directives = []
    for directive, values in csp.items():
        if isinstance(values, str):
            value = values
        else:
            value = " ".join(values)
        directives.append(f"{directive} {value}")
    return "; ".join(directives)


# ── CORS after_request (must be registered on the app separately) ─────────
def register_cors_headers(app):
    """Register CORS headers — called after all other middleware."""
    origins = get_production_origins()

    @app.after_request
    def _cors(response):
        origin = request.headers.get("Origin", "")
        if origin in origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Max-Age"] = "3600"
        return response


# ── Centralized Admin RBAC Middleware ──────────────────────────────────────
# All paths matching /api/admin/*, /api/admin/threats/*, /api/admin/scanner/*,
# /api/admin/debug/*, and financial/schema routes are gated here BEFORE any
# route handler executes. Returns 401/403 without revealing schema details.

ADMIN_PROTECTED_PREFIXES = (
    "/api/admin/",
    "/api/internal/",
    "/api/metadata/",
    "/api/schema/",
    "/api/telemetry/",
)


def _is_admin_protected_path(path: str) -> bool:
    """Return True if the path requires admin-level RBAC check."""
    for prefix in ADMIN_PROTECTED_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


def init_admin_rbac(app):
    """Register a before_request handler that enforces admin RBAC globally.

    This runs BEFORE route handlers and BEFORE the per-route @require_admin
    decorator, providing defense-in-depth. If the decorator is accidentally
    omitted on a new admin route, this middleware still blocks it.
    """
    from primerforge.pg_auth import verify_token

    @app.before_request
    def _admin_rbac_check():
        path = request.path

        if not _is_admin_protected_path(path):
            return

        if request.method == "OPTIONS":
            return

        auth = request.headers.get("Authorization", "")
        token = ""
        if auth.startswith("Bearer "):
            token = auth[7:]
        elif request.cookies.get("pf_token"):
            token = request.cookies.get("pf_token", "")

        if not token:
            return jsonify({"error": "Authentication required", "code": "AUTH_REQUIRED"}), 401

        user = verify_token(token)
        if not user or user.get("role") != "admin":
            return jsonify({"error": "Admin access required", "code": "FORBIDDEN"}), 403

    logger.info("Admin RBAC middleware initialized — protecting %d path prefixes",
                len(ADMIN_PROTECTED_PREFIXES))


# ── Input Sanitization Utilities ──────────────────────────────────────────

def sanitize_string(value, max_length: int = 256) -> str:
    """Strip HTML tags and limit length. Use for names, descriptions."""
    if not isinstance(value, str):
        return ""
    cleaned = bleach.clean(value, tags=[], strip=True)
    return cleaned[:max_length].strip()


def validate_email(email) -> tuple:
    """Validate email format and length. Returns (is_valid, error_message)."""
    if not isinstance(email, str):
        return False, "Invalid email format."
    if not email:
        return False, "Email is required."
    if len(email) > 320:
        return False, "Email address is too long (max 320 characters)."
    if len(email) < 5:
        return False, "Email address is too short."
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        return False, "Invalid email format."
    return True, ""


def validate_password(password) -> tuple:
    """
    Validate password strength against VigyanLLM password policy.

    Policy (BUG-19 FIX — added special character requirement):
      - Minimum 8 characters, maximum 128 characters
      - At least one uppercase letter (A-Z)
      - At least one lowercase letter (a-z)
      - At least one digit (0-9)
      - At least one special character (!@#$%^&*()-_=+[]{}|;:',.<>?/`~)

    Returns:
        (is_valid: bool, error_message: str) — error_message is "" on success.
    """
    if not isinstance(password, str):
        return False, "Invalid password format."
    if not password:
        return False, "Password is required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if len(password) > 128:
        return False, "Password is too long (max 128 characters)."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one digit (0-9)."
    if not re.search(r"[!@#$%^&*()\-_=+\[\]{}|;:',.<>?/`~]", password):
        return False, "Password must contain at least one special character (!@#$%^&* etc.)."
    return True, ""


def validate_quantity(raw_quantity) -> tuple:
    """
    Validate a quantity value. Returns (is_valid, quantity_int, error_message).
    Rejects floats, NaN, Infinity, non-numeric types.
    """
    if raw_quantity is None:
        return True, 1, ""  # Default to 1

    if isinstance(raw_quantity, bool):
        return False, 0, "Quantity must be an integer."

    if isinstance(raw_quantity, float):
        if math.isnan(raw_quantity) or math.isinf(raw_quantity):
            return False, 0, "Quantity must be a valid number."
        if raw_quantity != int(raw_quantity):
            return False, 0, "Quantity must be a whole number."
        return True, int(raw_quantity), ""

    if isinstance(raw_quantity, int):
        return True, raw_quantity, ""

    # String or other type
    try:
        val = int(raw_quantity)
        return True, val, ""
    except (TypeError, ValueError, OverflowError):
        return False, 0, "Quantity must be an integer."

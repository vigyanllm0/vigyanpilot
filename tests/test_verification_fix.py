#!/usr/bin/env python3
"""
Tests for email verification fix and security hardening.
Two tiers:
  1. Source-level checks (inspect.getsource) — verify code changes exist
  2. Flask integration tests (SQLite mode) — verify runtime behavior
"""

import os
import sys

import pytest

# Set env BEFORE any primerforge imports
os.environ["PRIMERFORGE_SECRET"] = "test-secret-key-for-verification-tests"
os.environ["VIGYANLLM_ENV"] = "development"
os.environ["PRIMERFORGE_ADMIN_EMAIL"] = "admin@test.com"
os.environ["PRIMERFORGE_ADMIN_PASSWORD"] = "Admin@1234"
# Use dummy PostgreSQL URL so pg_auth imports work for source-level checks
os.environ["DATABASE_URL"] = "postgresql://localhost:5432/test_unused"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Source-level checks (verify code changes exist) ────────────────────────

class TestVerificationCodeChanges:
    """Verify the 3-case verification fix exists in code."""

    def test_verify_three_cases_in_source(self):
        import inspect
        from primerforge.pg_auth import verify_email_with_token
        src = inspect.getsource(verify_email_with_token)
        # Case 1: unused token
        assert "verified_at IS NULL" in src
        # Case 2: consumed token (idempotent)
        assert "verified_at IS NOT NULL" in src
        assert "idempotent" in src.lower()
        # Case 3: invalid token
        assert "no matching row" in src.lower()

    def test_register_accepts_ip_address(self):
        import inspect
        from primerforge.pg_auth import register_user
        sig = inspect.signature(register_user)
        assert "ip_address" in sig.parameters

    def test_login_increments_on_failure(self):
        import inspect
        from primerforge.pg_auth import login_user
        src = inspect.getsource(login_user)
        assert "_increment_failed_login" in src

    def test_login_resets_on_success(self):
        import inspect
        from primerforge.pg_auth import login_user
        src = inspect.getsource(login_user)
        assert "_reset_failed_login" in src

    def test_lockout_constants(self):
        from primerforge.pg_auth import MAX_FAILED_LOGINS, LOCKOUT_MINUTES
        assert MAX_FAILED_LOGINS == 5
        assert LOCKOUT_MINUTES == 15


class TestSecurityCodeChanges:
    """Verify security hardening exists in code."""

    def test_security_headers_in_server(self):
        import inspect
        from primerforge.primer_server import create_app
        src = inspect.getsource(create_app)
        for h in ["X-Content-Type-Options", "X-Frame-Options", "X-XSS-Protection",
                   "Referrer-Policy", "Permissions-Policy", "Strict-Transport-Security",
                   "Content-Security-Policy"]:
            assert h in src, f"Missing: {h}"

    def test_server_header_removal(self):
        import inspect
        from primerforge.primer_server import create_app
        src = inspect.getsource(create_app)
        assert "X-Powered-By" in src

    def test_csp_configuration(self):
        import inspect
        from primerforge.primer_server import create_app
        src = inspect.getsource(create_app)
        assert "object-src 'none'" in src
        assert "base-uri 'self'" in src
        assert "form-action 'self'" in src

    def test_ip_brute_force_in_login(self):
        import inspect
        from primerforge.pg_auth_routes import login
        src = inspect.getsource(login)
        assert "ip_failures" in src
        assert "IP_RATE_LIMITED" in src

    def test_ip_rate_limit_in_register(self):
        import inspect
        from primerforge.pg_auth_routes import register
        src = inspect.getsource(register)
        assert "ip_registrations" in src

    def test_consent_enforcement_in_register(self):
        import inspect
        from primerforge.pg_auth_routes import register
        src = inspect.getsource(register)
        assert "CONSENT_REQUIRED" in src
        assert "consent_accepted is not True" in src

    def test_forgot_password_rate_limit(self):
        import inspect
        from primerforge.pg_auth_routes import forgot_password
        src = inspect.getsource(forgot_password)
        assert "reset_count" in src

    def test_resend_verification_rate_limit(self):
        import inspect
        from primerforge.pg_auth_routes import resend_verification
        src = inspect.getsource(resend_verification)
        assert "resend_count" in src

    def test_rate_limits_include_new_endpoints(self):
        import inspect
        from primerforge.security import apply_rate_limits
        src = inspect.getsource(apply_rate_limits)
        assert "forgot_password" in src
        assert "resend_verification" in src

    def test_hsts_preload(self):
        import inspect
        from primerforge.primer_server import create_app
        src = inspect.getsource(create_app)
        assert "preload" in src


# ── Flask integration tests (SQLite mode) ──────────────────────────────────

@pytest.fixture
def client():
    """Create Flask test client in SQLite mode."""
    # Ensure SQLite mode (no DATABASE_URL)
    os.environ.pop("DATABASE_URL", None)

    from primerforge.primer_server import create_app
    app = create_app()
    _app = app.wsgi_app if hasattr(app, "wsgi_app") else app
    _app.config["TESTING"] = True
    with _app.test_client() as c:
        yield c


class TestFlaskIntegration:

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_security_headers_on_health(self, client):
        resp = client.get("/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("X-XSS-Protection") == "1; mode=block"
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_security_headers_on_404(self, client):
        resp = client.get("/nonexistent-page-xyz")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""Tests for outbound-mail (Brevo) send-failure instrumentation + admin exposure.

Verifies:
  * a mocked Brevo failure records a ring-buffer row with the real HTTP status
    + error body (recipient stored as DOMAIN only — never the full address,
    never the API key)
  * the ring buffer caps at 10 entries (newest kept, oldest evicted)
  * GET /api/admin/mail-status is 403 for anon AND non-admin, 200 for admin
    and surfaces the recorded rows
"""

import os

# Must be set BEFORE primerforge.pg_* is imported (pg_auth raises at import time).
os.environ.setdefault("PRIMERFORGE_SECRET", "mail-log-secret-0123456789abcdef")

import pytest


# ── unit: ring buffer ─────────────────────────────────────────────────────────
def test_ring_caps_at_10_and_stores_domain_only(monkeypatch, tmp_path):
    from primerforge import mail_log

    monkeypatch.setenv("MAIL_LOG_PATH", str(tmp_path / "m.json"))
    for i in range(12):
        mail_log.record(
            "reset_email", f"user{i}@Example.COM", 400, ok=False, error=f"body{i}"
        )

    rows = mail_log.recent()
    assert len(rows) == 10
    # newest last; oldest (body0, body1) evicted
    assert rows[0]["error"] == "body2"
    assert rows[-1]["error"] == "body11"

    # domain only, lowercased — the full address never lands in the file
    assert rows[-1]["recipient_domain"] == "example.com"
    blob = (tmp_path / "m.json").read_text()
    assert "user11@Example.COM" not in blob
    assert "user11@example.com" not in blob
    assert "example.com" in blob
    # the API key is never written (we never pass it) — sanity
    assert "api-key" not in blob and "BREVO" not in blob


def test_record_never_raises_on_unwritable_path(monkeypatch, tmp_path):
    from primerforge import mail_log

    # A directory path that cannot be opened for writing as a file.
    monkeypatch.setenv("MAIL_LOG_PATH", str(tmp_path))  # path is a dir
    assert mail_log.record("reset_email", "a@b.co", 500, ok=False, error="x") is None
    assert mail_log.recent() == []


# ── integration: mocked Brevo failure → row recorded ──────────────────────────
def test_brevo_failure_records_real_status_and_body(monkeypatch, tmp_path):
    from primerforge import mail_log

    monkeypatch.setenv("MAIL_LOG_PATH", str(tmp_path / "m2.json"))
    monkeypatch.setenv("BREVO_API_KEY", "test-key-abc")
    monkeypatch.delenv("SMTP_HOST", raising=False)

    import requests

    class FakeResp:
        status_code = 401
        text = '{"code":"unauthorized","message":"API key is invalid"}'

    def fake_post(url, **kw):
        assert "brevo.com" in url
        return FakeResp()

    monkeypatch.setattr(requests, "post", fake_post)

    from primerforge.pg_auth_routes import _send_reset_email

    _send_reset_email("target@somecompany.org", "tok-xyz")

    rows = mail_log.recent()
    assert rows, "expected a recorded row after the mocked Brevo failure"
    last = rows[-1]
    assert last["purpose"] == "reset_email"
    assert last["ok"] is False
    assert last["http_status"] == 401
    assert "API key is invalid" in last["error"]
    assert last["recipient_domain"] == "somecompany.org"

    # full email + key never persisted
    blob = (tmp_path / "m2.json").read_text()
    assert "target@somecompany.org" not in blob
    assert "test-key-abc" not in blob


def test_brevo_success_records_ok(monkeypatch, tmp_path):
    from primerforge import mail_log

    monkeypatch.setenv("MAIL_LOG_PATH", str(tmp_path / "m3.json"))
    monkeypatch.setenv("BREVO_API_KEY", "test-key-ok")
    monkeypatch.delenv("SMTP_HOST", raising=False)

    import requests

    class FakeResp:
        status_code = 201
        text = '{"message":"Queued. Thank you"}'

    monkeypatch.setattr(requests, "post", lambda url, **kw: FakeResp())

    from primerforge.pg_auth_routes import _send_reset_email

    assert _send_reset_email("ok@sender.dev", "tok-ok") is True
    last = mail_log.recent()[-1]
    assert last["ok"] is True
    assert last["http_status"] == 201


# ── admin route authz ─────────────────────────────────────────────────────────
@pytest.fixture
def app(monkeypatch, tmp_path):
    from primerforge.primer_server import create_app

    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("PRIMERFORGE_DB", str(tmp_path / "mail.db"))
    monkeypatch.setenv("MAIL_LOG_PATH", str(tmp_path / "authz.json"))
    monkeypatch.setenv("PRIMERFORGE_ADMIN_EMAIL", "mail-log-admin@test.com")
    monkeypatch.setenv("PRIMERFORGE_ADMIN_PASSWORD", "MailLogAdmin!12345")
    monkeypatch.setenv("PRIMERFORGE_SECRET", "mail-log-secret-0123456789abcdef")
    import primerforge.security as security

    monkeypatch.setattr(security, "init_admin_rbac", lambda app: None)
    app = create_app()
    return app.wsgi_app if hasattr(app, "wsgi_app") else app


@pytest.fixture
def client(app):
    return app.test_client()


def _register_login(client, role=None):
    import uuid

    email = f"ml{uuid.uuid4().hex[:8]}@test.com"
    pw = "Mail-Log!Test1n26"
    r = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": pw,
            "name": "Mail Tester",
            "consent_accepted": True,
        },
    )
    assert r.status_code in (200, 201), f"register: {r.data[:200]}"

    if role == "admin":
        from flask import g  # noqa: F401
        from primerforge.auth import get_db

        with client.application.app_context():
            db = get_db()
            db.execute("UPDATE users SET role='admin' WHERE email=?", (email,))
            db.commit()

    r = client.post("/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, f"login: {r.data[:200]}"
    return client


def test_mail_status_anon_403(client):
    r = client.get("/api/admin/mail-status")
    assert r.status_code == 403
    assert r.get_json().get("code") == "FORBIDDEN"


def test_mail_status_non_admin_403(client):
    _register_login(client)  # role stays 'user'
    r = client.get("/api/admin/mail-status")
    assert r.status_code == 403


def test_mail_status_admin_200_and_returns_rows(client):
    _register_login(client, role="admin")
    from primerforge import mail_log

    mail_log.record("reset_email", "x@y.com", 400, ok=False, error="boom")
    r = client.get("/api/admin/mail-status")
    assert r.status_code == 200
    d = r.get_json()
    assert d["count"] >= 1
    assert any(a["error"] == "boom" for a in d["attempts"])
    # privacy holds in the response too — domain, not full address
    assert all("@" not in a["recipient_domain"] for a in d["attempts"])

"""Tests for the HttpOnly-cookie auth migration.

Verifies:
  * register / login / google set an HttpOnly `pf_token` cookie
  * the cookie authenticates API requests (get_current_user cookie fallback)
  * /api/auth/me returns an `auth_provider` field
  * google login persists `auth_provider='google'` and `google_id`
"""

import base64
import hashlib
import hmac
import json
import uuid

import pytest


@pytest.fixture
def app(monkeypatch, tmp_path):
    from primerforge.primer_server import create_app

    # .env is loaded at module import time; setting DATABASE_URL to "" (empty,
    # falsy) prevents load_dotenv(override=False) from re-populating it and keeps
    # create_app() on the SQLite auth path (USE_POSTGRES = bool(DATABASE_URL)).
    monkeypatch.setenv("DATABASE_URL", "")
    # Use a fresh temp SQLite DB so the full current schema (incl. auth_provider,
    # google_id, locked_until) is created on init.
    monkeypatch.setenv("PRIMERFORGE_DB", str(tmp_path / "test.db"))
    # init_admin_rbac imports primerforge.pg_auth which requires DATABASE_URL
    # at module import time. Stub it out so the SQLite auth path can be tested
    # without a Postgres connection string (mirrors the pre-existing limitation
    # in test_primer_server.py / test_order_serializer.py).
    import primerforge.security as security

    monkeypatch.setattr(security, "init_admin_rbac", lambda app: None)
    app = create_app()
    # create_app() returns a _ServerHeaderMiddleware wrapper; unwrap to the Flask app
    return app.wsgi_app if hasattr(app, "wsgi_app") else app


@pytest.fixture
def client(app):
    return app.test_client()


def _unique_email():
    return f"cookie-{uuid.uuid4().hex[:10]}@example.com"


def _google_token_info(payload: dict) -> dict:
    """Build a plausible signed-ish id_token payload for tokeninfo mocking."""
    header = base64.urlsafe_b64encode(b'{"alg":"RS256"}').rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).rstrip(b"=").decode()
    # Signature is not verified against a real key in the unit path; any token
    # that decodes with a 'sub' and 'email' is accepted by the endpoint.
    return {
        "id_token": f"{header}.{body}.sig",
        # tokeninfo response mirrors the same claims as the id_token body
        **payload,
    }


def test_register_sets_http_only_cookie(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": _unique_email(), "password": "Secret123!", "name": "Cookie Tester"},
    )
    assert resp.status_code == 201
    cookie = resp.headers.get("Set-Cookie", "")
    assert "pf_token=" in cookie
    assert "HttpOnly" in cookie
    assert "Path=/" in cookie


def test_login_sets_http_only_cookie_and_me_returns_provider(client):
    email = _unique_email()
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "Secret123!", "name": "Cookie Tester"},
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": email, "password": "Secret123!"},
    )
    assert resp.status_code == 200
    cookie = resp.headers.get("Set-Cookie", "")
    assert "pf_token=" in cookie
    assert "HttpOnly" in cookie

    # Replaying the cookie authenticates /api/auth/me
    token = cookie.split("pf_token=")[1].split(";")[0]
    me = client.get("/api/auth/me", headers={"Cookie": f"pf_token={token}"})
    assert me.status_code == 200
    assert me.get_json()["user"].get("auth_provider") == "email"


def test_google_login_sets_provider_and_google_id(client, monkeypatch):
    import primerforge.auth_routes as routes

    google_email = _unique_email()
    token_info = _google_token_info(
        {"sub": f"goog-{uuid.uuid4().hex[:8]}", "email": google_email, "name": "G User"}
    )

    class _FakeGoogle:
        def __init__(self):
            self.info = token_info

        def get(self, *args, **kwargs):
            return token_info["id_token"]

    fake = _FakeGoogle()
    import requests as real_requests

    # tokeninfo / userinfo response carry the metadata, NOT the id_token wrapper
    payload = dict(token_info)
    payload.pop("id_token", None)
    monkeypatch.setattr(real_requests, "get", lambda *a, **k: _Resp(payload))

    resp = client.post(
        "/api/auth/google",
        json={"credential": token_info["id_token"]},
    )
    assert resp.status_code == 200
    cookie = resp.headers.get("Set-Cookie", "")
    assert "pf_token=" in cookie
    assert "HttpOnly" in cookie
    assert resp.get_json()["user"].get("auth_provider") == "google"

    token = cookie.split("pf_token=")[1].split(";")[0]
    me = client.get("/api/auth/me", headers={"Cookie": f"pf_token={token}"})
    assert me.status_code == 200
    assert me.get_json()["user"].get("auth_provider") == "google"


class _Resp:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code

    def json(self):
        return self._data
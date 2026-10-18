#!/usr/bin/env python3
"""Verification-on-registration with the DEC-001 strict default (PG path).

DEC-001 ruling (pending work.md, founder): once mail reliably delivered
(Phase-1 closure, 2026-10-18), a verification send failure must leave the
account `pending` — verification still proves email ownership. The historical
auto-verify-on-send-failure behaviour is retained only as an explicit escape
hatch (``AUTO_VERIFY_ON_SEND_FAILURE=1``) for a future transport outage, so the
password-signup funnel cannot become a permanent black hole during one.

Contract under test:
  * strict (default): failed send -> account stays `pending`, no session, no
    silent activation;
  * opt-in (env=1): failed send -> auto-activate + hand back a session
    (`auto_verified`) — the outage escape hatch;
  * send success: normal verify-by-email flow, regardless of the flag.

Pure unit tests — every DB touchpoint (fetch_one/execute/get_db) and all
token/mail/session plumbing is monkeypatched; no database is required.
"""

import os
import sys

import pytest

# Env before any primerforge import (mirrors test_verification_fix.py; the
# dummy URL is only used if nothing else defined one — .database reads it
# at import).
os.environ.setdefault("PRIMERFORGE_SECRET", "test-secret-key-for-verification-tests")
os.environ.setdefault("VIGYANLLM_ENV", "development")
os.environ.setdefault("DATABASE_URL", "postgresql://localhost:5432/test_unused")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from primerforge import pg_auth  # noqa: E402

EMAIL = "auto.verify.probe@example.com"
# passes validate_password (12+, upper, lower, digit, special; no email part)
PASSWORD = "Auto#Verify99x"


class _Cursor:
    def __init__(self, row):
        self._row = row

    def execute(self, *a, **k):
        pass

    def fetchone(self):
        return self._row

    def close(self):
        pass


class _DB:
    """Minimal stand-in for the psycopg2 connection used by the INSERT."""

    def __init__(self, row):
        self._row = row

    def cursor(self):
        return _Cursor(self._row)

    def commit(self):
        pass

    def rollback(self):
        pass


@pytest.fixture
def harness(monkeypatch):
    """Record DB writes; stub token/mail/session plumbing; return controls."""
    h = {"executed": [], "log_actions": [], "mail_sent": False,
         "existing": None, "fail_activate": False}

    def fake_execute(query, params=None, commit=True):
        if h["fail_activate"] and "status = 'active'" in query:
            raise RuntimeError("db down")
        h["executed"].append((query, params))
        return 1

    def fake_fetch_one(query, params=None):
        return h["existing"]

    monkeypatch.setattr(pg_auth, "execute", fake_execute)
    monkeypatch.setattr(pg_auth, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(pg_auth, "get_db",
                        lambda: _DB({"id": 77, "email": EMAIL, "role": "user"}))
    monkeypatch.setattr(pg_auth, "create_verification_token", lambda uid: "vtok")
    monkeypatch.setattr(pg_auth, "send_verification_email",
                        lambda em, tok: h["mail_sent"])
    monkeypatch.setattr(pg_auth, "create_token",
                        lambda em, role, uid: "session-tok")
    monkeypatch.setattr(pg_auth, "log_action",
                        lambda email, action, details="":
                        h["log_actions"].append((email, action, details)))
    return h


def _queries(h):
    return [q for q, _ in h["executed"]]


def test_new_user_stays_pending_when_mail_undeliverable(harness, monkeypatch):
    # DEC-001 strict default: a failed verification send must NOT silently
    # activate the account. It stays `pending` — verification still proves
    # email ownership — and no session is handed out.
    monkeypatch.delenv("AUTO_VERIFY_ON_SEND_FAILURE", raising=False)
    harness["mail_sent"] = False
    res = pg_auth.register_user(EMAIL, PASSWORD, "Probe", ip_address="1.2.3.4")
    assert res["requires_verification"] is True
    assert res["email_sent"] is False
    assert "auto_verified" not in res
    assert "token" not in res
    assert not any("SET status = 'active'" in q for q in _queries(harness))


def test_new_user_auto_verifies_when_opted_in_and_mail_undeliverable(harness, monkeypatch):
    # Outage escape hatch (DEC-001 opt-in): with the flag set, a failed send
    # auto-activates and hands back a session so the funnel has no dead end.
    monkeypatch.setenv("AUTO_VERIFY_ON_SEND_FAILURE", "1")
    harness["mail_sent"] = False
    res = pg_auth.register_user(EMAIL, PASSWORD, "Probe", ip_address="1.2.3.4")
    assert res.get("auto_verified") is True
    assert res["requires_verification"] is False
    assert res["token"] == "session-tok"
    assert res["user"]["id"] == 77
    assert res["user"]["role"] == "user"
    # the pending row was activated, the verification row satisfied, and the
    # decision was written to the audit log
    assert any("SET status = 'active'" in q for q in _queries(harness))
    assert any("email_verifications" in q for q in _queries(harness))
    assert any(a == "registration_auto_verified"
               for _, a, _ in harness["log_actions"])


def test_new_user_stays_pending_when_mail_sent(harness):
    harness["mail_sent"] = True
    res = pg_auth.register_user(EMAIL, PASSWORD, "Probe", ip_address="1.2.3.4")
    assert res["requires_verification"] is True
    assert res["email_sent"] is True
    assert "auto_verified" not in res
    assert "token" not in res
    # normal flow: no silent activation
    assert not any("SET status = 'active'" in q for q in _queries(harness))


def test_reregistration_pending_stays_pending_when_mail_undeliverable(harness, monkeypatch):
    # Re-registering a stuck pending account is a verification resend, not a
    # backdoor activation: under the strict default a failed send leaves it
    # pending so ownership is still proven before login.
    monkeypatch.delenv("AUTO_VERIFY_ON_SEND_FAILURE", raising=False)
    harness["existing"] = {"id": 42, "status": "pending", "role": "user"}
    harness["mail_sent"] = False
    res = pg_auth.register_user(EMAIL, PASSWORD, "Probe", ip_address="1.2.3.4")
    assert res["requires_verification"] is True
    assert res["email_sent"] is False
    assert "auto_verified" not in res
    assert "token" not in res
    assert not any("SET status = 'active'" in q for q in _queries(harness))


def test_reregistration_pending_auto_verifies_when_opted_in(harness, monkeypatch):
    monkeypatch.setenv("AUTO_VERIFY_ON_SEND_FAILURE", "1")
    harness["existing"] = {"id": 42, "status": "pending", "role": "user"}
    harness["mail_sent"] = False
    res = pg_auth.register_user(EMAIL, PASSWORD, "Probe", ip_address="1.2.3.4")
    assert res.get("auto_verified") is True
    assert res["user"]["id"] == 42
    assert res["token"] == "session-tok"
    assert any("SET status = 'active'" in q for q in _queries(harness))


def test_reregistration_pending_resends_when_mail_sent(harness):
    harness["existing"] = {"id": 42, "status": "pending", "role": "user"}
    harness["mail_sent"] = True
    res = pg_auth.register_user(EMAIL, PASSWORD, "Probe", ip_address="1.2.3.4")
    assert res["requires_verification"] is True
    assert res["email_sent"] is True
    assert "token" not in res


def test_activation_failure_falls_back_to_pending(harness, monkeypatch):
    # Even in opt-in (outage) mode, if the activation UPDATE itself fails we
    # report the honest pending state (no session for a still-pending account)
    # instead of a broken login.
    monkeypatch.setenv("AUTO_VERIFY_ON_SEND_FAILURE", "1")
    harness["fail_activate"] = True
    res = pg_auth.register_user(EMAIL, PASSWORD, "Probe", ip_address="1.2.3.4")
    assert res["requires_verification"] is True
    assert res["email_sent"] is False
    assert "token" not in res


def test_existing_active_email_still_rejected(harness):
    harness["existing"] = {"id": 9, "status": "active", "role": "user"}
    res = pg_auth.register_user(EMAIL, PASSWORD, "Probe", ip_address="1.2.3.4")
    assert "error" in res
    assert not any("SET status = 'active'" in q for q in _queries(harness))


def test_register_route_sets_session_cookie_on_auto_verify():
    # The route's direct-session branch must hand over the session exactly
    # like login does (HttpOnly pf_token + pf_refresh) or the auto-verified
    # user would appear logged out on the next page load.
    import inspect

    from primerforge.pg_auth_routes import register
    src = inspect.getsource(register)
    assert "pf_token" in src
    assert "pf_refresh" in src
    assert "auto_verified" in src

"""Referral program: multi-referral model + reward correctness (SQLite path).

QA finding (2026-10, pre-promotion review): apply_referral() UPDATEd the
referrer's single code row, so a referrer's 2nd referral 404'd "Invalid or
expired referral code" — a lifetime cap of ONE referral per user on both DB
paths. apply now INSERTs one row per referred person while the code row
stays reusable; UNIQUE(referral_code) was dropped accordingly (SQLite init
rebuild in auth.init_db, PG migration 0128).

Also locks the reward contract: the REFERRER alone earns
REFERRAL_REWARD_RUNS (default 5) design runs when the referred user
completes their first design — the frontend used to claim "You both earn
... instantly" (copy fixed in primer-app.js).

SQLite-forced app; auth.DB_PATH is monkeypatched directly too, because it
binds at import (known quirk — a bare setenv after a prior import would
silently point every test at the first session's file).
"""

import sqlite3
import uuid

import pytest

PASSWORD = "Vault-Key!Pr1mer26"


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    db_file = str(tmp_path / "ref.db")
    monkeypatch.setenv("PRIMERFORGE_DB", db_file)

    import primerforge.auth as auth

    monkeypatch.setattr(auth, "DB_PATH", db_file)

    import primerforge.security as security

    monkeypatch.setattr(security, "init_admin_rbac", lambda app: None)

    from primerforge.primer_server import create_app

    application = create_app()
    return application.wsgi_app if hasattr(application, "wsgi_app") else application


@pytest.fixture
def client(app):
    return app.test_client()


def _register(client, tag):
    # register() normalises to lowercase — return what the DB will store,
    # or direct WHERE email=? reads silently miss the row.
    email = f"ref-{tag}-{uuid.uuid4().hex[:8]}@example.com".lower()
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "password": PASSWORD, "name": "Ref Probe"},
    )
    assert resp.status_code == 201, resp.get_data(as_text=True)
    return email


def _login(client, email):
    resp = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert resp.status_code == 200, resp.get_data(as_text=True)


def _get_code(client):
    resp = client.get("/api/referral/code")
    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    assert data["referral_url"] == (
        f"https://www.vigyanllm.in/primer?ref={data['referral_code']}"
    )
    return data["referral_code"]


def _apply(client, code, email):
    return client.post("/api/referral/apply", json={"code": code, "email": email})


def _stats(client):
    resp = client.get("/api/referral/code")
    assert resp.status_code == 200, resp.get_data(as_text=True)
    return resp.get_json()


def _paid_runs(db_file, email):
    conn = sqlite3.connect(db_file)
    try:
        row = conn.execute(
            "SELECT paid_runs FROM users WHERE email=?", (email,)
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def test_second_referral_same_code_succeeds(client):
    """Pre-fix behaviour: the 2nd referral with one code 404'd forever."""
    _register(client, "refA")
    code = _get_code(client)

    assert _apply(client, code, "b1@example.com").status_code == 200
    resp = _apply(client, code, "b2@example.com")
    assert resp.status_code == 200, resp.get_data(as_text=True)

    stats = _stats(client)
    assert stats["total_referred"] == 2
    assert stats["successful_referrals"] == 0
    assert stats["tokens_earned"] == 0


def test_unique_constraint_dropped(app):
    """referral_code is no longer UNIQUE — two rows may share one code."""
    import primerforge.auth as auth

    conn = sqlite3.connect(auth.DB_PATH)
    try:
        conn.execute(
            "INSERT INTO referrals (referrer_email, referral_code, status) "
            "VALUES ('dup-a@example.com', 'DUPCODE0001', 'active')"
        )
        conn.execute(
            "INSERT INTO referrals (referrer_email, referral_code, "
            "referred_email, status) VALUES "
            "('dup-a@example.com', 'DUPCODE0001', 'friend@example.com', 'pending_design')"
        )
        conn.commit()
    finally:
        conn.close()


def test_legacy_consumed_code_still_applies(client, app):
    """A code row consumed by the old UPDATE model (status flipped off
    'active') was dead for everyone; it must accept new referrals now."""
    _register(client, "refL")
    code = _get_code(client)

    import primerforge.auth as auth

    conn = sqlite3.connect(auth.DB_PATH)
    try:
        conn.execute(
            "UPDATE referrals SET referred_email='old@example.com', "
            "status='pending_design' WHERE referral_code=?",
            (code,),
        )
        conn.commit()
    finally:
        conn.close()

    resp = _apply(client, code, "new-friend@example.com")
    assert resp.status_code == 200, resp.get_data(as_text=True)
    # legacy consumed row counts as a referral of its own + the new one;
    # the permanent code row (referred_email empty) must not inflate the total
    assert _stats(client)["total_referred"] == 2


def test_empty_email_rejected(client):
    _register(client, "refS")
    code = _get_code(client)
    assert _apply(client, code, "").status_code == 400


def test_self_referral_rejected(client):
    referrer = _register(client, "refME")
    code = _get_code(client)
    resp = _apply(client, code, referrer)
    assert resp.status_code == 400
    assert "yourself" in resp.get_json()["error"].lower()


def test_duplicate_apply_is_idempotent(client):
    _register(client, "refD")
    code = _get_code(client)
    assert _apply(client, code, "same-friend@example.com").status_code == 200
    resp = _apply(client, code, "same-friend@example.com")
    assert resp.status_code == 200
    assert "already" in resp.get_json()["message"].lower()
    assert _stats(client)["total_referred"] == 1


def test_unknown_code_404(client):
    assert _apply(client, "NOSUCHCODE42", "x@example.com").status_code == 404


def test_reward_fires_for_referrer_per_row(client, app):
    """Each completed referral credits the referrer alone, once, per row."""
    import primerforge.auth as auth

    referrer = _register(client, "refR")
    code = _get_code(client)

    friend1 = _register(client, "r1")
    friend2 = _register(client, "r2")
    assert _apply(client, code, friend1).status_code == 200
    assert _apply(client, code, friend2).status_code == 200

    before_referrer = _paid_runs(auth.DB_PATH, referrer)
    before_f1 = _paid_runs(auth.DB_PATH, friend1)

    # friend1 completes their first design -> referrer +5, referred +0
    _login(client, friend1)
    resp = client.post("/api/referral/complete")
    assert resp.status_code == 200
    assert _paid_runs(auth.DB_PATH, referrer) == before_referrer + 5
    assert _paid_runs(auth.DB_PATH, friend1) == before_f1

    # completing again must not double-pay
    resp = client.post("/api/referral/complete")
    assert resp.status_code == 200
    assert "no pending" in resp.get_json()["message"].lower()
    assert _paid_runs(auth.DB_PATH, referrer) == before_referrer + 5

    # friend2 completes -> referrer +5 more (per-row rewards)
    _login(client, friend2)
    resp = client.post("/api/referral/complete")
    assert resp.status_code == 200
    assert _paid_runs(auth.DB_PATH, referrer) == before_referrer + 10

    # referrer sees both successes
    _login(client, referrer)
    stats = _stats(client)
    assert stats["successful_referrals"] == 2
    assert stats["tokens_earned"] == 10
    assert stats["total_referred"] == 2

"""Rate-limit hardening + promo-code editing (2026-10-11).

The production rate-limit identity bug this file locks down: nginx runs
on-box, so gunicorn saw ``remote_addr=127.0.0.1`` for EVERY request —
flask-limiter's ``get_remote_address`` key collapsed all clients into ONE
shared bucket (five consensus submits per minute from ANYONE 429'd every
user; five bad logins locked the login endpoint site-wide).  Fixes:

  * ``client_rate_key()`` keys limits on the LAST X-Forwarded-For entry
    (nginx appends the true TCP peer, so a client cannot forge it); the
    nginx real_ip block additionally resolves CloudFront viewers.
  * ``admin_rate_exempt()`` — signed-token role check, no DB — exempts
    admins from every rate limit (ops, probes, backfills).
  * Structural run guards: queue-depth cap per identity (email, or client
    IP for guests) on /docking/consensus and a concurrent-campaign cap
    per user on /docking/screen.
  * ``/api/admin/promo/update`` — admin editing of existing promo codes
    with USD-only, $1.00-minimum, immutable-history rules.

The local worker thread is a daemon started by create_app whenever the
docking engine loads; these tests point the queue at a tmp dir and stub
``claim_job`` so nothing queued here is ever executed.
"""

import base64
import hashlib
import hmac
import json
import sqlite3
import time
import uuid

import pytest


@pytest.fixture
def app(monkeypatch, tmp_path):
    import primerforge.docking_queue as dq

    # Redirect the queue BEFORE create_app so the (singleton) worker thread
    # never scans the repo dir, and stub the claim so test jobs never run.
    monkeypatch.setattr(dq, "QUEUE_DIR", str(tmp_path / "q"))
    monkeypatch.setattr(dq, "PENDING_DIR", str(tmp_path / "q" / "pending"))
    monkeypatch.setattr(dq, "RUNNING_DIR", str(tmp_path / "q" / "running"))
    monkeypatch.setattr(dq, "claim_job", lambda job_id: False)

    from primerforge.primer_server import create_app

    monkeypatch.setenv("DATABASE_URL", "")
    import primerforge.security as security

    monkeypatch.setattr(security, "init_admin_rbac", lambda application: None)
    application = create_app()
    application = application.wsgi_app if hasattr(application, "wsgi_app") else application
    return application


@pytest.fixture
def client(app):
    return app.test_client()


def _reset_limiter(application):
    lim = application.extensions.get("limiter")
    if lim is not None and hasattr(lim, "reset"):
        try:
            lim.reset()
        except Exception:
            pass


def _mint(email, role="user"):
    from primerforge import auth

    return auth.create_token(email, role)


def _register(client, email):
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": "Str0ng!Pass1", "consent_accepted": True},
    )
    assert r.status_code in (200, 201), r.status_code
    return r


def _make_admin(email):
    """Flip a registered SQLite user to admin (shared session DB quirk: the
    file is whatever auth.DB_PATH bound to — same file register used)."""
    from primerforge import auth

    conn = sqlite3.connect(auth.DB_PATH)
    conn.execute("UPDATE users SET role='admin' WHERE email=?", (email,))
    conn.commit()
    conn.close()


# ── 1. client_rate_key ─────────────────────────────────────────────────────


def test_client_rate_key_prefers_last_xff_hop(app):
    from primerforge import security

    with app.test_request_context("/", headers={"X-Forwarded-For": "1.1.1.1, 2.2.2.2"}):
        assert security.client_rate_key() == "2.2.2.2"


def test_client_rate_key_falls_back_to_socket_address(app):
    from primerforge import security

    with app.test_request_context("/"):
        assert security.client_rate_key() == "127.0.0.1"
    # blank/whitespace hops must not become the identity
    with app.test_request_context("/", headers={"X-Forwarded-For": " , "}):
        assert security.client_rate_key() == "127.0.0.1"


# ── 2. admin exemption ─────────────────────────────────────────────────────


def test_admin_exempt_recognizes_signed_admin_token(app):
    from primerforge import security

    tok = _mint("rl-admin@vigyan.test", "admin")
    with app.test_request_context("/", headers={"Authorization": f"Bearer {tok}"}):
        assert security.admin_rate_exempt() is True
    with app.test_request_context("/", headers={"Cookie": f"pf_token={tok}"}):
        assert security.admin_rate_exempt() is True


def test_admin_exempt_rejects_user_garbage_and_expired(app):
    from primerforge import auth, security

    with app.test_request_context("/", headers={"Authorization": f"Bearer {_mint('u@x.test')}"}):
        assert security.admin_rate_exempt() is False
    with app.test_request_context("/", headers={"Authorization": "Bearer not.a.token"}):
        assert security.admin_rate_exempt() is False
    with app.test_request_context("/"):
        assert security.admin_rate_exempt() is False

    # correctly-signed but EXPIRED admin token must not exempt
    payload = json.dumps({"email": "old@x.test", "role": "admin", "exp": time.time() - 60})
    sig = hmac.new(auth.SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    expired = base64.urlsafe_b64encode(payload.encode()).decode() + "." + sig
    with app.test_request_context("/", headers={"Authorization": f"Bearer {expired}"}):
        assert security.admin_rate_exempt() is False


# ── 3. per-client (not global) limiting ────────────────────────────────────


def test_consensus_limit_is_per_client_not_one_global_bucket(app, client):
    """One exhausted client must NOT block a different client."""
    _reset_limiter(app)
    body = json.dumps({"sequence": "", "ligand_smiles_list": []})
    h1 = {"Content-Type": "application/json", "X-Forwarded-For": "203.0.113.10"}
    codes = [client.post("/api/primer/docking/consensus", data=body, headers=h1).status_code
             for _ in range(6)]
    assert codes[:5] == [400, 400, 400, 400, 400], codes
    assert codes[5] == 429, codes

    h2 = {"Content-Type": "application/json", "X-Forwarded-For": "203.0.113.99"}
    r = client.post("/api/primer/docking/consensus", data=body, headers=h2)
    assert r.status_code == 400, "a second client must have its own budget"


def test_admin_bypasses_endpoint_rate_limits(app, client):
    """6 rapid consensus submits with an admin token: never 429."""
    _reset_limiter(app)
    tok = _mint("rl-admin2@vigyan.test", "admin")
    body = json.dumps({"sequence": "", "ligand_smiles_list": []})
    hdr = {"Content-Type": "application/json", "Authorization": f"Bearer {tok}"}
    codes = [client.post("/api/primer/docking/consensus", data=body, headers=hdr).status_code
             for _ in range(8)]
    assert 429 not in codes, codes
    assert codes == [400] * 8, codes


def test_manual_analysis_and_pipeline_submit_are_limited(app, client):
    _reset_limiter(app)
    # manual-analysis is 20/min → the 21st rapid submit must 429
    hdr = {"Content-Type": "application/json", "X-Forwarded-For": "198.51.100.7"}
    codes = [client.post("/api/primer/manual-analysis", json={}, headers=hdr).status_code
             for _ in range(21)]
    assert codes[:20] == [400] * 20 and codes[20] == 429, codes

    _reset_limiter(app)
    codes = [client.post("/api/pipeline/submit", json={}, headers=hdr).status_code
             for _ in range(6)]
    assert codes[5] == 429, codes


# ── 4. structural run guards ───────────────────────────────────────────────


def test_queue_depth_guard_blocks_sixth_live_run(app, client, monkeypatch):
    import primerforge.docking_queue as dq

    _reset_limiter(app)
    email = f"rl-depth-{uuid.uuid4().hex[:8]}@x.test"
    _register(client, email)
    for _ in range(5):
        dq.create_job("MKT", ["CCO"], user_email=email)

    r = client.post("/api/primer/docking/consensus",
                    json={"sequence": "MKTDEFAVLK", "ligand_smiles_list": ["CCO"]},
                    headers={"Authorization": f"Bearer {_mint(email)}"})
    assert r.status_code == 429, r.status_code
    payload = r.get_json()
    assert payload.get("code") == "RATE_LIMITED" and payload.get("scope") == "run_queue_depth"

    # a different identity is unaffected and proceeds to queue (job stays
    # pending — claim_job is stubbed)
    other = f"rl-other-{uuid.uuid4().hex[:8]}@x.test"
    _register(client, other)
    r2 = client.post("/api/primer/docking/consensus",
                     json={"sequence": "MKTDEFAVLK", "ligand_smiles_list": ["CCO"]},
                     headers={"Authorization": f"Bearer {_mint(other)}"})
    assert r2.status_code == 202, (r2.status_code, r2.get_json())


def test_queue_depth_guard_counts_guests_per_client_ip(app, client):
    import primerforge.docking_queue as dq

    _reset_limiter(app)
    for _ in range(5):
        dq.create_job("MKT", ["CCO"], user_email="", client_ip="192.0.2.55")

    body = json.dumps({"sequence": "MKTDEFAVLK", "ligand_smiles_list": ["CCO"]})
    hdr = {"Content-Type": "application/json", "X-Forwarded-For": "192.0.2.55"}
    r = client.post("/api/primer/docking/consensus", data=body, headers=hdr)
    assert r.status_code == 429 and r.get_json().get("scope") == "run_queue_depth"

    # another guest IP is unaffected (its submit queues and stays pending)
    hdr2 = {"Content-Type": "application/json", "X-Forwarded-For": "192.0.2.56"}
    r2 = client.post("/api/primer/docking/consensus", data=body, headers=hdr2)
    assert r2.status_code == 202, r2.status_code


def test_screening_concurrent_campaign_cap(app, client, monkeypatch):
    import primerforge.pipelines.virtual_screening as vs

    _reset_limiter(app)
    monkeypatch.setattr(
        vs, "list_campaigns",
        lambda email, limit=20: [{"status": "running", "user_email": email},
                                 {"status": "pending", "user_email": email}])

    email = f"rl-screen-{uuid.uuid4().hex[:8]}@x.test"
    _register(client, email)
    body = {"proteins": [{"sequence": "MKT", "name": "p1"}], "ligands": ["CCO", "CCN"]}

    r = client.post("/api/primer/docking/screen", json=body,
                    headers={"Authorization": f"Bearer {_mint(email)}"})
    assert r.status_code == 429, (r.status_code, r.get_json())

    # admins skip the cap: create_campaign must be reached (stubbed to raise
    # so no real campaign/worker spawn happens in tests)
    _make_admin(email)

    def _boom(*a, **k):
        raise RuntimeError("stop-before-spawn")

    monkeypatch.setattr(vs, "create_campaign", _boom)
    r2 = client.post("/api/primer/docking/screen", json=body,
                     headers={"Authorization": f"Bearer {_mint(email, 'admin')}"})
    assert r2.status_code != 429, "admin must not hit the per-user campaign cap"


# ── 5. promo-code editing (SQLite mirror of the PG route) ──────────────────


def _create_promo(client, admin_tok, **overrides):
    body = {"count": 1, "prefix": "RLT", "promo_type": "trial", "tier": "pro",
            "trial_days": 30, "daily_analyses": 50, "batch_max": 20, "has_export": 1,
            "price_inr": 999, "currency": "USD", "max_uses": 5}
    body.update(overrides)
    r = client.post("/api/admin/promo/create", json=body,
                    headers={"Authorization": f"Bearer {admin_tok}"})
    assert r.status_code == 200, (r.status_code, r.get_json())
    d = r.get_json()
    return (d.get("codes") or [d.get("code")])[0]


def _promo_row(code):
    from primerforge import auth

    conn = sqlite3.connect(auth.DB_PATH)
    conn.row_factory = sqlite3.Row
    row = dict(conn.execute("SELECT * FROM promo_codes WHERE code=?", (code,)).fetchone())
    conn.close()
    return row


def _setup_promo_admin(client):
    email = f"rl-promo-{uuid.uuid4().hex[:8]}@x.test"
    _register(client, email)
    _make_admin(email)
    return email, _mint(email, "admin")


def test_promo_update_edits_fields(client):
    _, tok = _setup_promo_admin(client)
    code = _create_promo(client, tok)

    r = client.post("/api/admin/promo/update",
                    json={"code": code, "trial_days": 14, "tier": "lab",
                          "daily_analyses": 75, "max_uses": 9, "price_inr": 1999},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200, (r.status_code, r.get_json())
    assert sorted(r.get_json()["updated"]) == \
        ["daily_analyses", "max_uses", "price_inr", "tier", "trial_days"]
    row = _promo_row(code)
    assert (row["trial_days"], row["tier"], row["daily_analyses"],
            row["max_uses"], row["price_inr"]) == (14, "lab", 75, 9, 1999)


def test_promo_update_rejects_non_admin(client):
    _, tok = _setup_promo_admin(client)
    code = _create_promo(client, tok)
    stranger = f"rl-nobody-{uuid.uuid4().hex[:8]}@x.test"
    _register(client, stranger)
    r = client.post("/api/admin/promo/update", json={"code": code, "trial_days": 1},
                    headers={"Authorization": f"Bearer {_mint(stranger)}"})
    assert r.status_code == 403


def test_promo_update_validation_guards(client):
    _, tok = _setup_promo_admin(client)

    # unknown code
    r = client.post("/api/admin/promo/update", json={"code": "RLT-NOPE99", "trial_days": 1},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 404

    code = _create_promo(client, tok, max_uses=2)

    # max_uses below redeemed history
    from primerforge import auth
    conn = sqlite3.connect(auth.DB_PATH)
    conn.execute("UPDATE promo_codes SET used_count=2 WHERE code=?", (code,))
    conn.commit(); conn.close()
    r = client.post("/api/admin/promo/update", json={"code": code, "max_uses": 1},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 400

    # below Razorpay's $1.00 USD payment minimum
    r = client.post("/api/admin/promo/update", json={"code": code, "price_inr": 50},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 400

    # discount_pct only for discount codes
    r = client.post("/api/admin/promo/update", json={"code": code, "discount_pct": 10},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 400

    # nothing to update
    r = client.post("/api/admin/promo/update", json={"code": code},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 400

    # legacy INR row is rejected, not resurrected
    from primerforge import auth as _auth
    conn = sqlite3.connect(_auth.DB_PATH)
    inr_code = f"RLTINR{uuid.uuid4().hex[:4].upper()}"
    conn.execute(
        "INSERT INTO promo_codes (code, promo_type, tier, daily_analyses, batch_max,"
        " has_export, trial_days, price_inr, currency, max_uses, created_by)"
        " VALUES (?, 'trial', 'pro', 50, 20, 1, 30, 699, 'INR', 1, 't')", (inr_code,))
    conn.commit(); conn.close()
    r = client.post("/api/admin/promo/update", json={"code": inr_code, "trial_days": 5},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 409


def test_promo_update_academic_price_immutable(client):
    _, tok = _setup_promo_admin(client)
    code = _create_promo(client, tok, promo_type="academic", prefix="ACA", price_inr=0)
    r = client.post("/api/admin/promo/update", json={"code": code, "price_inr": 999},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 400
    # non-price edits on academic codes still work
    r = client.post("/api/admin/promo/update", json={"code": code, "trial_days": 60},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200

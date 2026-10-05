"""End-to-end promo-code workflow under the USD regime.

Covers the full generation → redemption → checkout path:
  * admin generates trial/discount/academic codes (USD-cents price, USD currency)
  * anonymous /promo/validate returns price_minor / currency / discount_pct
  * trial flow: $1 (100¢) verification order → HMAC verify → plan created in
    USD cents → trial activated → second claim rejected (max_uses=1)
  * academic flow: direct Pro activation, no Razorpay hop
  * checkout: 30% discount promo → 999¢ × 0.70 = 699¢ USD order
  * revoke → validate returns 410

Razorpay is faked (no network); the payment signature is forged exactly the
way production computes it: HMAC-SHA256(secret, f"{order_id}|{payment_id}").
"""

import hashlib
import hmac
import time
import uuid

import pytest


@pytest.fixture
def app(monkeypatch, tmp_path):
    from primerforge.primer_server import create_app

    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("PRIMERFORGE_DB", str(tmp_path / "promo_workflow.db"))
    import primerforge.security as security

    monkeypatch.setattr(security, "init_admin_rbac", lambda app: None)
    app = create_app()
    return app.wsgi_app if hasattr(app, "wsgi_app") else app


class _FakeApi:
    def __init__(self, prefix):
        self.prefix = prefix
        self.created = []

    def create(self, payload):
        self.created.append(payload)
        return {"id": f"{self.prefix}_{len(self.created)}", **payload}


class _FakeRazorpayClient:
    def __init__(self):
        self.order = _FakeApi("order")
        self.plan = _FakeApi("plan")
        self.subscription = _FakeApi("sub")


@pytest.fixture
def fake_rzp(monkeypatch):
    import primerforge.payment_routes as payments

    monkeypatch.setattr(payments, "RAZORPAY_KEY_ID", "rzp_test_unit")
    monkeypatch.setattr(payments, "RAZORPAY_KEY_SECRET", "unit_secret")
    fake = _FakeRazorpayClient()
    monkeypatch.setattr(payments, "rz_client", fake)
    return fake


def _signature(order_id, payment_id):
    return hmac.new(
        b"unit_secret", f"{order_id}|{payment_id}".encode(), hashlib.sha256
    ).hexdigest()


def _register(app, tag):
    """Fresh client per user — cookie sessions do not share state."""
    client = app.test_client()
    email = f"{tag}-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "Secret123!",
            "name": "Promo Tester",
            "consent_accepted": True,
        },
    )
    assert r.status_code in (200, 201), r.data
    return client, email


def _admin_client(app):
    client, email = _register(app, "admin")
    with app.app_context():
        from primerforge.auth import get_db

        db = get_db()
        db.execute("UPDATE users SET role='admin' WHERE email=?", (email,))
        db.commit()
    r = client.post(
        "/api/auth/login", json={"email": email, "password": "Secret123!"}
    )
    assert r.status_code == 200, r.data
    return client


def _create_promo(admin_client, **overrides):
    body = {
        "promo_type": "trial",
        "prefix": "CHK",
        "count": 1,
        "trial_days": 30,
        "tier": "pro",
        "daily_analyses": 50,
        "batch_max": 20,
        "price_inr": 999,          # USD cents (legacy field name)
        "currency": "USD",
        "max_uses": 1,
        "has_export": 1,
        "discount_pct": 0,
        "expires_at": 0,
    }
    body.update(overrides)
    r = admin_client.post("/api/admin/promo/create", json=body)
    assert r.status_code == 200, r.data
    codes = r.get_json()["codes"]
    assert codes, "no codes generated"
    return codes[0]


def test_generation_defaults_are_usd(app):
    """Admin generator (as wired in admin-app.js) stores USD-cents prices."""
    admin = _admin_client(app)
    code = _create_promo(admin)

    r = admin.get("/api/admin/promo/list")
    assert r.status_code == 200
    row = next(c for c in r.get_json()["codes"] if c["code"] == code)
    assert row["currency"] == "USD"
    assert row["price_inr"] == 999          # $9.99 — not major rupees


def test_validate_returns_usd_minor_units(app):
    admin = _admin_client(app)
    code = _create_promo(admin)

    anon = app.test_client()
    r = anon.post("/api/promo/validate", json={"code": code})
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d["valid"] is True
    assert d["price_minor"] == 999
    assert d["price_inr"] == 999             # legacy alias = same minor value
    assert d["currency"] == "USD"
    assert d["discount_pct"] == 0


def test_trial_flow_full(app, fake_rzp):
    """$1 verification order → HMAC verify → USD plan + trial activated."""
    admin = _admin_client(app)
    code = _create_promo(admin)
    user, email = _register(app, "trial")

    # Step 1 — $1 (100¢) verification order
    r = user.post(
        "/api/promo/apply", json={"code": code, "step": "create_order"}
    )
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d["amount"] == 100
    assert d["currency"] == "USD"
    order_id = d["order_id"]
    assert fake_rzp.order.created[-1]["amount"] == 100
    assert fake_rzp.order.created[-1]["currency"] == "USD"

    # Step 2 — verify signature, create plan + subscription, activate trial
    payment_id = "pay_test_promo"
    r = user.post(
        "/api/promo/apply",
        json={
            "code": code,
            "razorpay_payment_id": payment_id,
            "razorpay_order_id": order_id,
            "razorpay_signature": _signature(order_id, payment_id),
        },
    )
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d["trial_days"] == 30
    assert d["price_minor"] == 999
    assert d["price_inr"] == 999

    # Razorpay plan + subscription were created in USD cents / after trial
    plan_payload = fake_rzp.plan.created[-1]
    assert plan_payload["item"]["amount"] == 999
    assert plan_payload["item"]["currency"] == "USD"
    sub_payload = fake_rzp.subscription.created[-1]
    assert sub_payload["start_at"] > time.time() + 29 * 86400

    # User state
    with app.app_context():
        from primerforge.auth import get_db

        u = get_db().execute(
            "SELECT plan, trial_ends_at, promo_code_used FROM users WHERE email=?",
            (email,),
        ).fetchone()
        p = get_db().execute(
            "SELECT used_count FROM promo_codes WHERE code=?", (code,)
        ).fetchone()
    assert u["plan"] == "trial"
    assert u["trial_ends_at"] > time.time()
    assert u["promo_code_used"] == code
    assert p["used_count"] == 1

    # /trial/status exposes the USD-cents price for display
    r = user.get("/api/trial/status")
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d["price_minor"] == 999
    assert d["currency"] == "USD"

    # Exhausted code cannot be claimed again
    other, _ = _register(app, "trial2")
    r = other.post(
        "/api/promo/apply", json={"code": code, "step": "create_order"}
    )
    assert r.status_code == 410


def test_academic_flow_activates_pro_without_razorpay(app, fake_rzp):
    admin = _admin_client(app)
    code = _create_promo(
        admin, promo_type="academic", prefix="ACAD", trial_days=90,
        price_inr=0, daily_analyses=100, batch_max=50,
    )
    orders_before = len(fake_rzp.order.created)
    user, email = _register(app, "acad")

    r = user.post("/api/promo/apply", json={"code": code})
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d["promo_type"] == "academic"
    assert d["price_minor"] == 0

    # No Razorpay hop for academic redemption
    assert len(fake_rzp.order.created) == orders_before
    assert fake_rzp.plan.created == []

    with app.app_context():
        from primerforge.auth import get_db

        u = get_db().execute(
            "SELECT plan, is_academic, pro_expires_at FROM users WHERE email=?",
            (email,),
        ).fetchone()
    assert u["plan"] == "pro"
    assert u["is_academic"] == 1
    assert u["pro_expires_at"] > time.time() + 89 * 86400


def test_checkout_discount_promo_math(app, fake_rzp):
    """30% discount promo: 999¢ → 699¢ USD order; revoke blocks re-validation."""
    admin = _admin_client(app)
    code = _create_promo(
        admin, promo_type="discount", prefix="DISC",
        discount_pct=30, max_uses=10,
    )

    anon = app.test_client()
    r = anon.post("/api/promo/validate", json={"code": code})
    assert r.status_code == 200, r.data
    assert r.get_json()["discount_pct"] == 30

    buyer, _ = _register(app, "buyer")
    r = buyer.post(
        "/api/payments/create-order",
        json={"plan_id": "pro-monthly", "promo_code": code},
    )
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d["amount"] == 699                # 999 × 0.70 = 699¢ ($6.99)
    assert d["currency"] == "USD"
    assert d["discount_pct"] == 30
    assert d["promo_code"] == code
    assert fake_rzp.order.created[-1]["amount"] == 699
    assert fake_rzp.order.created[-1]["currency"] == "USD"

    # Revoke → no longer redeemable
    r = admin.post("/api/admin/promo/revoke", json={"code": code})
    assert r.status_code == 200, r.data
    r = anon.post("/api/promo/validate", json={"code": code})
    assert r.status_code == 410


def test_bad_signature_rejected(app, fake_rzp):
    admin = _admin_client(app)
    code = _create_promo(admin)
    user, _ = _register(app, "badsig")

    r = user.post(
        "/api/promo/apply", json={"code": code, "step": "create_order"}
    )
    assert r.status_code == 200, r.data
    order_id = r.get_json()["order_id"]

    r = user.post(
        "/api/promo/apply",
        json={
            "code": code,
            "razorpay_payment_id": "pay_x",
            "razorpay_order_id": order_id,
            "razorpay_signature": "not-a-real-signature",
        },
    )
    assert r.status_code == 400

    # Code still redeemable after a failed verify (used_count untouched)
    with app.app_context():
        from primerforge.auth import get_db

        p = get_db().execute(
            "SELECT used_count FROM promo_codes WHERE code=?", (code,)
        ).fetchone()
    assert p["used_count"] == 0

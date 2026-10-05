import hmac
import hashlib
import uuid

import pytest


@pytest.fixture
def client(monkeypatch, tmp_path):
    from primerforge.primer_server import create_app

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("PRIMERFORGE_DB", str(tmp_path / "payment_routes.db"))
    app = create_app()
    return (app.wsgi_app if hasattr(app, "wsgi_app") else app).test_client()


class _FakeRazorpayOrderApi:
    def __init__(self):
        self.created = []

    def create(self, payload):
        self.created.append(payload)
        return {"id": f"order_test_{len(self.created)}", **payload}


class _FakeRazorpayClient:
    def __init__(self):
        self.order = _FakeRazorpayOrderApi()


def _register(client):
    email = f"pay-{uuid.uuid4().hex[:10]}@example.com"
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "Secret123!",
            "name": "Pay User",
            "consent_accepted": True,
        },
    )
    assert response.status_code in (200, 201), f"register failed: {response.data[:200]}"
    token = (response.get_json() or {}).get("token", "")
    if token:
        return email, {"Authorization": f"Bearer {token}"}
    # HttpOnly-cookie sessions carry no body token — test client keeps cookies.
    return email, {}


def _signature(secret, order_id, payment_id):
    return hmac.new(
        secret.encode(),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()


def test_sqlite_payments_pricing_alias(client):
    response = client.get("/api/payments/pricing")
    assert response.status_code == 200
    data = response.get_json()

    # USD regime: everything priced in minor units of USD (cents)
    assert data["currency"] == "USD"
    plans = {p["plan_id"]: p for p in data["plans"]}
    assert plans["pro-monthly"]["price_minor"] == 999        # $9.99
    assert plans["pro-yearly"]["price_minor"] == 8900        # $89.00
    assert plans["lab-monthly"]["price_minor"] == 4900       # $49.00
    assert plans["lab-yearly"]["price_minor"] == 39900       # $399.00
    # legacy alias returns the same minor value (never major rupees)
    for p in data["plans"]:
        assert p["price_inr"] == p["price_minor"]
    # academic −30% (truncated to cents)
    assert plans["pro-monthly"]["academic_price_minor"] == 699   # $6.99
    assert plans["lab-monthly"]["academic_price_minor"] == 3430  # $34.30

    # Top-up products are sellable and priced server-side
    topups = {t["product_id"]: t for t in data["topups"]}
    assert topups["top_up"]["unit_price_minor"] == 100       # $1.00 / run
    assert topups["dock_top_up"]["unit_price_minor"] == 100  # $1.00 / run
    assert all(t["currency"] == "USD" for t in data["topups"])


def test_sqlite_payments_create_order_alias_for_topup(client, monkeypatch):
    import primerforge.payment_routes as payments

    fake_client = _FakeRazorpayClient()
    monkeypatch.setattr(payments, "RAZORPAY_KEY_ID", "rzp_test_unit")
    monkeypatch.setattr(payments, "RAZORPAY_KEY_SECRET", "unit_secret")
    monkeypatch.setattr(payments, "rz_client", fake_client)

    _, headers = _register(client)
    response = client.post(
        "/api/payments/create-order",
        headers=headers,
        json={"product_id": "top_up", "quantity": 3},
    )

    assert response.status_code == 200, response.data
    data = response.get_json()
    assert data["order_id"] == "order_test_1"
    assert data["amount"] == 300              # 3 runs × 100¢ = 300¢ ($3.00)
    assert data["currency"] == "USD"
    assert data["runs"] == 3
    assert data["tokens"] == 3
    assert data["key_id"] == "rzp_test_unit"
    assert fake_client.order.created[0]["notes"]["product_id"] == "top_up"
    assert fake_client.order.created[0]["currency"] == "USD"


def test_sqlite_payments_verify_is_idempotent(client, monkeypatch):
    import primerforge.payment_routes as payments

    fake_client = _FakeRazorpayClient()
    secret = "unit_secret"
    monkeypatch.setattr(payments, "RAZORPAY_KEY_ID", "rzp_test_unit")
    monkeypatch.setattr(payments, "RAZORPAY_KEY_SECRET", secret)
    monkeypatch.setattr(payments, "rz_client", fake_client)

    email, headers = _register(client)
    order_response = client.post(
        "/api/payments/create-order",
        headers=headers,
        json={"product_id": "top_up", "quantity": 2},
    )
    order_id = order_response.get_json()["order_id"]
    payment_id = "pay_test_123"
    payload = {
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": _signature(secret, order_id, payment_id),
    }

    first = client.post("/api/payments/verify-payment", headers=headers, json=payload)
    second = client.post("/api/payments/verify-payment", headers=headers, json=payload)

    assert first.status_code == 200, first.data
    assert first.get_json()["runs_purchased"] == 2
    assert second.status_code == 200, second.data
    assert second.get_json()["runs_purchased"] == 0

    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.get_json()["user"]["paid_runs"] == 2
    # top-up must NOT activate a subscription plan
    st = client.get("/api/payments/status", headers=headers)
    assert st.status_code == 200
    assert st.get_json()["plan"] == "free"


def test_sqlite_payments_reject_bad_signature(client, monkeypatch):
    import primerforge.payment_routes as payments

    fake_client = _FakeRazorpayClient()
    monkeypatch.setattr(payments, "RAZORPAY_KEY_ID", "rzp_test_unit")
    monkeypatch.setattr(payments, "RAZORPAY_KEY_SECRET", "unit_secret")
    monkeypatch.setattr(payments, "rz_client", fake_client)

    _, headers = _register(client)
    order_response = client.post(
        "/api/payments/create-order",
        headers=headers,
        json={"product_id": "top_up", "quantity": 1},
    )
    assert order_response.status_code == 200, order_response.data
    order_id = order_response.get_json()["order_id"]
    response = client.post(
        "/api/payments/verify-payment",
        headers=headers,
        json={
            "razorpay_order_id": order_id,
            "razorpay_payment_id": "pay_test_bad",
            "razorpay_signature": "bad-signature",
        },
    )

    assert response.status_code == 400
    assert "verification failed" in response.get_json()["error"].lower()


def test_sqlite_payments_create_order_plan_usd(client, monkeypatch):
    """Checkout flow: plan orders price in USD cents, academic −30% applied."""
    import primerforge.payment_routes as payments

    fake_client = _FakeRazorpayClient()
    monkeypatch.setattr(payments, "RAZORPAY_KEY_ID", "rzp_test_unit")
    monkeypatch.setattr(payments, "RAZORPAY_KEY_SECRET", "unit_secret")
    monkeypatch.setattr(payments, "rz_client", fake_client)

    _, headers = _register(client)

    full = client.post(
        "/api/payments/create-order",
        headers=headers,
        json={"plan_id": "pro-monthly"},
    )
    assert full.status_code == 200, full.data
    body = full.get_json()
    assert body["amount"] == 999                # $9.99 in cents
    assert body["currency"] == "USD"
    assert body["tier"] == "pro"
    assert body["billing"] == "monthly"

    disc = client.post(
        "/api/payments/create-order",
        headers=headers,
        json={"plan_id": "lab-yearly", "discount": 30},
    )
    assert disc.status_code == 200, disc.data
    assert disc.get_json()["amount"] == 27930   # 39900 × 0.70 = 27930¢ ($279.30)

    # quote-only / free plans are not purchasable online
    ent = client.post(
        "/api/payments/create-order",
        headers=headers,
        json={"plan_id": "enterprise"},
    )
    assert ent.status_code == 400


def test_sqlite_payments_verify_activates_plan(client, monkeypatch):
    """Plan verify: signature OK → subscription activated with USD-era registry."""
    import primerforge.payment_routes as payments

    fake_client = _FakeRazorpayClient()
    secret = "unit_secret"
    monkeypatch.setattr(payments, "RAZORPAY_KEY_ID", "rzp_test_unit")
    monkeypatch.setattr(payments, "RAZORPAY_KEY_SECRET", secret)
    monkeypatch.setattr(payments, "rz_client", fake_client)

    _, headers = _register(client)
    order_response = client.post(
        "/api/payments/create-order",
        headers=headers,
        json={"plan_id": "pro-monthly"},
    )
    assert order_response.status_code == 200, order_response.data
    order_id = order_response.get_json()["order_id"]
    payment_id = "pay_plan_1"
    payload = {
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": _signature(secret, order_id, payment_id),
    }

    first = client.post("/api/payments/verify-payment", headers=headers, json=payload)
    assert first.status_code == 200, first.data
    assert first.get_json()["plan"] == "pro"

    st = client.get("/api/payments/status", headers=headers)
    assert st.status_code == 200
    assert st.get_json()["plan"] == "pro"
    # plan orders do not credit top-up runs
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.get_json()["user"]["paid_runs"] == 0

import hmac
import hashlib
import uuid

import pytest


@pytest.fixture
def client(monkeypatch):
    from primerforge.primer_server import create_app

    monkeypatch.delenv("DATABASE_URL", raising=False)
    return create_app().test_client()


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
        json={"email": email, "password": "secret123", "name": "Pay User"},
    )
    assert response.status_code == 201
    token = response.get_json()["token"]
    return email, {"Authorization": f"Bearer {token}"}


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
    assert data["top_up_price_inr"] == 49
    assert {p["product_id"] for p in data["products"]} >= {
        "individual",
        "institutional",
        "corporate",
    }
    quotas = {p["product_id"]: p["designs_included"] for p in data["products"]}
    assert quotas["individual"] == 250
    assert quotas["institutional"] == 2000
    assert quotas["corporate"] == 7500


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

    assert response.status_code == 200
    data = response.get_json()
    assert data["order_id"] == "order_test_1"
    assert data["amount"] == 14700
    assert data["runs"] == 3
    assert data["tokens"] == 3
    assert data["key_id"] == "rzp_test_unit"
    assert fake_client.order.created[0]["notes"]["product_id"] == "top_up"


def test_sqlite_payments_verify_is_idempotent(client, monkeypatch):
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

    assert first.status_code == 200
    assert first.get_json()["runs_purchased"] == 2
    assert second.status_code == 200
    assert second.get_json()["runs_purchased"] == 0

    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.get_json()["user"]["paid_runs"] == 2


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
        json={"runs": 1},
    )
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

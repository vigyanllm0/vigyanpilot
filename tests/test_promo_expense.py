"""Tests for promo code listing, expense logging, and admin endpoints.

Verifies:
  * admin can create and list promo codes
  * admin can record and list expenses
  * expense categories aggregate correctly
  * non-admin is blocked from promo/expense endpoints
"""

import uuid

import pytest


@pytest.fixture
def app(monkeypatch, tmp_path):
    from primerforge.primer_server import create_app

    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("PRIMERFORGE_DB", str(tmp_path / "promo_exp.db"))
    import primerforge.security as security

    monkeypatch.setattr(security, "init_admin_rbac", lambda app: None)
    app = create_app()
    return app.wsgi_app if hasattr(app, "wsgi_app") else app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_client(client):
    """Register an admin user and return authenticated client."""
    email = f"admin-{uuid.uuid4().hex[:8]}@test.com"
    r = client.post("/api/auth/register", json={
        "email": email, "password": "Admin123!", "name": "Test Admin",
        "consent_accepted": True,
    })
    assert r.status_code in (200, 201), f"Register failed: {r.data[:200]}"

    # Promote to admin
    from primerforge.auth import get_db
    from flask import g
    with client.application.app_context():
        db = get_db()
        db.execute("UPDATE users SET role='admin' WHERE email=?", (email,))
        db.commit()

    # Login
    r = client.post("/api/auth/login", json={"email": email, "password": "Admin123!"})
    assert r.status_code == 200, f"Login failed: {r.data[:200]}"
    return client


def test_admin_can_create_promo_codes(admin_client):
    r = admin_client.post("/api/admin/promo/create", json={
        "prefix": "TEST", "count": 3, "trial_days": 15, "tier": "pro",
        "daily_analyses": 25, "batch_max": 10, "price_inr": 699,
        "currency": "INR", "max_uses": 1, "has_export": 1,
    })
    assert r.status_code == 200
    d = r.get_json()
    assert d["success"] is True
    assert d["count"] == 3
    assert len(d["codes"]) == 3
    assert all(c.startswith("TEST-") for c in d["codes"])


def test_admin_can_list_promo_codes(admin_client):
    # Create some codes first
    admin_client.post("/api/admin/promo/create", json={
        "prefix": "LIST", "count": 2, "trial_days": 30,
        "price_inr": 699, "max_uses": 1,
    })

    r = admin_client.get("/api/admin/promo/list")
    assert r.status_code == 200
    d = r.get_json()
    assert "codes" in d
    assert "summary" in d
    assert d["summary"]["total_codes"] >= 2
    assert d["summary"]["total_used"] == 0
    assert d["summary"]["total_unused"] == d["summary"]["total_codes"]


def test_admin_can_record_expense(admin_client):
    r = admin_client.post("/api/admin/expenses/record", json={
        "category": "infrastructure",
        "description": "E2E Networks monthly server",
        "amount_inr": 2500.00,
    })
    assert r.status_code == 201
    d = r.get_json()
    assert d["success"] is True


def test_admin_can_list_expenses(admin_client):
    # Record a few expenses
    admin_client.post("/api/admin/expenses/record", json={
        "category": "infrastructure", "description": "Server cost", "amount_inr": 1000,
    })
    admin_client.post("/api/admin/expenses/record", json={
        "category": "verification_charge", "description": "Razorpay ₹1", "amount_inr": 1,
        "promo_code": "TEST-ABC123",
    })

    r = admin_client.get("/api/admin/expenses")
    assert r.status_code == 200
    d = r.get_json()
    assert len(d["expenses"]) >= 2
    assert d["summary"]["grand_total_inr"] >= 1001
    assert "infrastructure" in d["summary"]["by_category"]
    assert "verification_charge" in d["summary"]["by_category"]


def test_expense_category_filter(admin_client):
    admin_client.post("/api/admin/expenses/record", json={
        "category": "infrastructure", "description": "A", "amount_inr": 100,
    })
    admin_client.post("/api/admin/expenses/record", json={
        "category": "marketing", "description": "B", "amount_inr": 200,
    })

    r = admin_client.get("/api/admin/expenses?category=infrastructure")
    assert r.status_code == 200
    d = r.get_json()
    assert all(e["category"] == "infrastructure" for e in d["expenses"])


def test_non_admin_blocked_from_promo_list(client):
    r = client.get("/api/admin/promo/list")
    assert r.status_code in (401, 403)


def test_non_admin_blocked_from_expenses(client):
    r = client.get("/api/admin/expenses")
    assert r.status_code in (401, 403)


def test_non_admin_blocked_from_record_expense(client):
    r = client.post("/api/admin/expenses/record", json={
        "category": "other", "description": "Test", "amount_inr": 10,
    })
    assert r.status_code in (401, 403)


def test_admin_revenue_stats(admin_client):
    r = admin_client.get("/api/payments/revenue-stats")
    assert r.status_code == 200
    d = r.get_json()
    assert "revenue" in d
    assert "cost" in d
    assert "margin" in d
    assert "total_inr" in d["revenue"]
    assert "total_inr" in d["cost"]
    assert "margin_percent" in d["margin"]

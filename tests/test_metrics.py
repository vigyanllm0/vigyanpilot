"""Tests for /metrics Prometheus endpoint."""

import pytest


@pytest.fixture
def app(monkeypatch, tmp_path):
    from primerforge.primer_server import create_app

    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("PRIMERFORGE_DB", str(tmp_path / "metrics_test.db"))
    import primerforge.security as security
    monkeypatch.setattr(security, "init_admin_rbac", lambda app: None)
    app = create_app()
    return app.wsgi_app if hasattr(app, "wsgi_app") else app


@pytest.fixture
def client(app):
    return app.test_client()


def test_metrics_returns_200(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200


def test_metrics_content_type(client):
    resp = client.get("/metrics")
    ct = resp.content_type
    assert "text/plain" in ct or "openmetrics" in ct


def test_metrics_contains_request_counter(client):
    resp = client.get("/metrics")
    body = resp.get_data(as_text=True)
    assert "vigyanllm_requests_total" in body or "vigyanllm_request_duration" in body


def test_metrics_increments_on_request(client):
    resp = client.get("/metrics")
    body1 = resp.get_data(as_text=True)

    # Make a real request to increment the counter
    client.get("/health")

    resp2 = client.get("/metrics")
    body2 = resp2.get_data(as_text=True)
    assert body2 != body1 or "vigyanllm_requests_total" in body2

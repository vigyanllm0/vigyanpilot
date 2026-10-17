"""Saved-results routes: SQLite/dev mirror + the routing-reality regression.

Two implementations of /api/results/{save,list,delete} exist:

  * primer_server.py — SQLite/dev mirror (these tests' subject). It was
    dead in EVERY mode until 61cfe3c3 imported flask.g: `g` was never in
    scope, so every authenticated call NameError'd -> 500, and tests never
    caught it because require_auth 401s anonymous before the body runs.
  * pg_payment_routes.py (payment_bp) — the production implementation
    (user_reports-backed). payment_bp registers before the @app.route
    rules, so its handlers win the duplicate route in PG mode (confirmed
    live 2026-10-17). Its bugs — save returning rowcount as "id", a
    no-op tool filter, garbage id -> PG DataError 500 — were fixed the
    same day; the definitive coverage for that path is the live probe
    (no PG in the test suite).
"""

import uuid

import pytest


@pytest.fixture
def app(monkeypatch, tmp_path):
    from primerforge.primer_server import create_app

    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("PRIMERFORGE_DB", str(tmp_path / "sr.db"))
    import primerforge.security as security

    monkeypatch.setattr(security, "init_admin_rbac", lambda app: None)
    app = create_app()
    return app.wsgi_app if hasattr(app, "wsgi_app") else app


@pytest.fixture
def client(app):
    return app.test_client()


def _register(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": f"sr-{uuid.uuid4().hex[:10]}@example.com",
              "password": "Vault-Key!Pr1mer26", "name": "SR Probe"},
    )
    assert resp.status_code == 201, resp.get_json()


def test_results_routes_sqlite_roundtrip(client):
    """save -> list (both filters) -> delete -> gone, as a logged-in user.

    The id the save returns MUST be the id the list shows (the prod
    implementation used to return rowcount=1 for every save).
    """
    _register(client)

    r = client.post("/api/results/save", json={
        "tool": "primer", "title": "my design",
        "inputs": {"seq": "ACGT"}, "outputs": {"pairs": 3},
        "sequences_count": 1, "job_id": "job-1",
    })
    assert r.status_code == 200
    rid = r.get_json()["id"]
    assert r.get_json()["success"] is True

    r = client.get("/api/results/list")
    assert r.status_code == 200
    body = r.get_json()
    assert body["total"] == 1
    assert body["results"][0]["id"] == rid        # save-returned id == real id
    assert body["results"][0]["tool"] == "primer"
    assert body["results"][0]["inputs"] == '{"seq": "ACGT"}'

    r = client.get("/api/results/list?tool=docking")   # filter excludes it
    assert r.status_code == 200
    assert r.get_json()["total"] == 0

    r = client.get("/api/results/list?tool=primer")    # filter includes it
    assert r.get_json()["total"] == 1

    r = client.post("/api/results/delete", json={"id": rid})
    assert r.status_code == 200
    assert client.get("/api/results/list").get_json()["total"] == 0

    r = client.post("/api/results/delete", json={"id": rid})   # repeat -> 404
    assert r.status_code == 404


def test_delete_garbage_id_is_404_not_500(client):
    """A non-numeric id must 404 — it used to reach the DB layer and 500."""
    _register(client)
    r = client.post("/api/results/delete", json={"id": "zz-not-int"})
    assert r.status_code == 404


def test_results_routes_still_require_auth(client):
    assert client.get("/api/results/list").status_code == 401
    assert client.post("/api/results/save", json={"tool": "t"}).status_code == 401
    assert client.post("/api/results/delete", json={"id": 1}).status_code == 401

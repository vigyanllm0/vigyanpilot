"""Saved-results: PG mirror for /api/results/{save,list,delete} + SQLite regression.

The Phase-3 routes were written SQLite-only: in PG mode create_app never
binds `get_db` (only the SQLite else-branch imports it), so every logged-in
call NameError'd -> 500 — the dashboard's Saved Results table never worked
on production. These tests pin the PG mirror helpers (dialect, INSERT ...
RETURNING id, ownership checks, jsonb->TEXT response parity) against faked
database.* helpers, and keep the SQLite route path honest end-to-end.
"""

import uuid

import pytest

import primerforge.primer_server as ps


# ── PG helper unit tests (database.* faked — no PG needed) ────────────────

def test_sr_json_text_contract():
    assert ps._sr_json_text("already") == "already"
    assert ps._sr_json_text({"a": 1}) == '{"a": 1}'
    assert ps._sr_json_text(None) == "{}"


def test_sr_pg_save_uses_returning_id_and_jsonb_casts(monkeypatch):
    seen = {}

    def fake_execute_returning(query, params=None, commit=True):
        seen["q"], seen["p"] = query, params
        return {"id": 42}

    monkeypatch.setattr("primerforge.database.execute_returning", fake_execute_returning)
    rid = ps._sr_pg_save("a@b.c", "primer", "T", {"x": 1}, {"y": 2}, 3, "j1")

    assert rid == 42
    assert "RETURNING id" in seen["q"]           # psycopg2 has no last_insert_rowid()
    assert "%s::jsonb" in seen["q"]              # JSONB columns, explicit cast
    assert "last_insert_rowid" not in seen["q"]
    assert seen["p"] == ("a@b.c", "primer", "T", '{"x": 1}', '{"y": 2}', 3, "j1")


def test_sr_pg_list_wires_total_and_stringifies_jsonb(monkeypatch):
    seen = {}

    def fake_fetch_all(query, params=None):
        seen["all"] = (query, params)
        # psycopg2 typecasts jsonb columns to dicts — must be re-stringified
        return [{"id": 1, "inputs": {"seq": "ACGT"}, "outputs": {}, "title": "t"}]

    def fake_fetch_one(query, params=None):
        seen["one"] = (query, params)
        return {"total": 7}

    monkeypatch.setattr("primerforge.database.fetch_all", fake_fetch_all)
    monkeypatch.setattr("primerforge.database.fetch_one", fake_fetch_one)
    out = ps._sr_pg_list("a@b.c", 20, 0, "")

    assert out["total"] == 7
    row = out["results"][0]
    assert row["inputs"] == '{"seq": "ACGT"}'    # TEXT-string parity w/ SQLite branch
    assert "user_email=%s" in seen["all"][0]
    assert seen["all"][1] == ("a@b.c", 20, 0)
    assert seen["one"][1] == ("a@b.c",)


def test_sr_pg_list_tool_filter(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        "primerforge.database.fetch_all",
        lambda q, p=None: seen.update(allp=p) or [])
    monkeypatch.setattr(
        "primerforge.database.fetch_one",
        lambda q, p=None: seen.update(onep=p) or {"total": 0})

    ps._sr_pg_list("a@b.c", 10, 5, "docking")

    assert seen["allp"] == ("a@b.c", "docking", 10, 5)
    assert seen["onep"] == ("a@b.c", "docking")


def test_sr_pg_delete_rejects_garbage_id_without_db_touch(monkeypatch):
    touched = []
    monkeypatch.setattr("primerforge.database.fetch_one",
                        lambda q, p=None: touched.append(p))
    monkeypatch.setattr("primerforge.database.execute",
                        lambda q, p=None, commit=True: touched.append(("del", p)))

    assert ps._sr_pg_delete("not-an-int", "a@b.c") == "not_found"
    assert touched == []                          # no SELECT, no DELETE


def test_sr_pg_delete_outcomes(monkeypatch):
    deleted = []
    monkeypatch.setattr("primerforge.database.execute",
                        lambda q, p=None, commit=True: deleted.append(p))

    # unknown row -> not_found
    monkeypatch.setattr("primerforge.database.fetch_one",
                        lambda q, p=None: None)
    assert ps._sr_pg_delete(99, "a@b.c") == "not_found"

    # someone else's row -> forbidden, DELETE never issued
    monkeypatch.setattr("primerforge.database.fetch_one",
                        lambda q, p=None: {"user_email": "other@x.y"})
    assert ps._sr_pg_delete(5, "a@b.c") == "forbidden"
    assert deleted == []

    # owner match -> deleted
    monkeypatch.setattr("primerforge.database.fetch_one",
                        lambda q, p=None: {"user_email": "a@b.c"})
    assert ps._sr_pg_delete(5, "a@b.c") == "deleted"
    assert deleted == [(5,)]


# ── SQLite-mode route regression (the original path stays honest) ────────

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
    """save -> list (both filters) -> delete -> gone, as a logged-in user."""
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
    assert body["results"][0]["id"] == rid
    assert body["results"][0]["tool"] == "primer"
    assert body["results"][0]["inputs"] == '{"seq": "ACGT"}'

    r = client.get("/api/results/list?tool=docking")   # filter excludes it
    assert r.status_code == 200
    assert r.get_json()["total"] == 0

    r = client.post("/api/results/delete", json={"id": rid})
    assert r.status_code == 200
    assert client.get("/api/results/list").get_json()["total"] == 0

    r = client.post("/api/results/delete", json={"id": rid})   # repeat -> 404
    assert r.status_code == 404


def test_results_list_and_delete_still_require_auth(client):
    assert client.get("/api/results/list").status_code == 401
    assert client.post("/api/results/delete", json={"id": 1}).status_code == 401

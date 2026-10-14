"""Queue HTTP API must be locked behind the worker shared secret.

The /api/primer/docking/queue/* routes (enqueue/claim/complete/fail/stats/
recover/cleanup) are worker-only plumbing over persistent_queue. They had no
caller anywhere in the repo (production workers use the local file queue) and
no authentication — anyone could enqueue junk jobs or trigger a mass re-queue
via recover. The gate is deny-by-default:

  * QUEUE_WORKER_TOKEN unset  -> every route 403s (the deployed default)
  * token set                 -> X-Queue-Token must match, else 403
  * token set + correct header-> routes behave normally

SQLite-forced app (mirrors test_guest_mode.py).
"""

import pytest


@pytest.fixture
def app(monkeypatch, tmp_path):
    from primerforge.primer_server import create_app

    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("PRIMERFORGE_DB", str(tmp_path / "queue.db"))
    import primerforge.security as security

    monkeypatch.setattr(security, "init_admin_rbac", lambda app: None)
    app = create_app()
    return app.wsgi_app if hasattr(app, "wsgi_app") else app


@pytest.fixture
def client(app):
    return app.test_client()


QUEUE_GET = "/api/primer/docking/queue/stats"
QUEUE_POSTS = [
    ("/api/primer/docking/queue/enqueue", {"data": {"x": 1}}),
    ("/api/primer/docking/queue/claim", {}),
    ("/api/primer/docking/queue/complete", {"job_id": "j1"}),
    ("/api/primer/docking/queue/fail", {"job_id": "j1"}),
    ("/api/primer/docking/queue/recover", {}),
    ("/api/primer/docking/queue/cleanup", {"days": 7}),
]


def test_all_queue_routes_403_when_token_unset(client, monkeypatch):
    """Deployed default (no QUEUE_WORKER_TOKEN): every route denies."""
    monkeypatch.delenv("QUEUE_WORKER_TOKEN", raising=False)
    assert client.get(QUEUE_GET).status_code == 403
    for path, body in QUEUE_POSTS:
        resp = client.post(path, json=body)
        assert resp.status_code == 403, path
        assert resp.get_json().get("code") == "FORBIDDEN", path


def test_wrong_token_403(client, monkeypatch):
    monkeypatch.setenv("QUEUE_WORKER_TOKEN", "correct-horse-battery")
    assert client.get(QUEUE_GET, headers={"X-Queue-Token": "wrong"}).status_code == 403
    assert client.get(QUEUE_GET).status_code == 403
    resp = client.post(
        "/api/primer/docking/queue/enqueue",
        json={"data": {"x": 1}},
        headers={"X-Queue-Token": "nope"},
    )
    assert resp.status_code == 403


def test_correct_token_passes(client, monkeypatch):
    monkeypatch.setenv("QUEUE_WORKER_TOKEN", "correct-horse-battery")
    hdr = {"X-Queue-Token": "correct-horse-battery"}
    # stats: real 200 with queue counters (not 403)
    resp = client.get(QUEUE_GET, headers=hdr)
    assert resp.status_code == 200
    assert "pending_count" in resp.get_json()
    # enqueue: creates a job
    resp = client.post(
        "/api/primer/docking/queue/enqueue",
        json={"data": {"smiles": "CCO"}},
        headers=hdr,
    )
    assert resp.status_code == 201
    job_id = resp.get_json()["job_id"]
    assert job_id
    # claim: picks it up
    resp = client.post("/api/primer/docking/queue/claim", json={}, headers=hdr)
    assert resp.status_code == 200
    assert resp.get_json()["job_id"] == job_id
    # complete: finishes it
    resp = client.post(
        "/api/primer/docking/queue/complete",
        json={"job_id": job_id, "result": {"ok": True}},
        headers=hdr,
    )
    assert resp.status_code == 200


def test_empty_token_env_denies_even_with_header(client, monkeypatch):
    """Empty-string env is treated as unset — never a bypass."""
    monkeypatch.setenv("QUEUE_WORKER_TOKEN", "")
    resp = client.get(QUEUE_GET, headers={"X-Queue-Token": ""})
    assert resp.status_code == 403

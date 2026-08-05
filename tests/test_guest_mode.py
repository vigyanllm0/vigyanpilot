"""Tests for guest-mode (Option A: "computation is free, persistence is paid").

Verifies:
  * anonymous users can run the primer pipeline, manual oligo analysis, and
    single-ligand docking consensus without any 401 auth wall
  * anonymous guest pipeline jobs are readable back via status/result
  * persistence actions (saved results / reports) still require auth
  * logged-in Free users are still capped by the daily-limit system (not the
    legacy FREE_RUNS/run_count gate)
"""

import json
import uuid

import pytest


@pytest.fixture
def app(monkeypatch, tmp_path):
    from primerforge.primer_server import create_app

    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("PRIMERFORGE_DB", str(tmp_path / "guest.db"))
    import primerforge.security as security

    monkeypatch.setattr(security, "init_admin_rbac", lambda app: None)
    app = create_app()
    return app.wsgi_app if hasattr(app, "wsgi_app") else app


@pytest.fixture
def client(app):
    return app.test_client()


def _unique_email():
    return f"guest-{uuid.uuid4().hex[:10]}@example.com"


def _valid_oligo():
    return "ACGTACGTACGTACGTTAGG"


def _valid_template():
    # 200 bp ACGT repeat — passes ≥100 bp validation
    return "ACGT" * 200


def test_guest_can_run_manual_analysis(client):
    """Anonymous /api/primer/manual-analysis must not return 401."""
    resp = client.post(
        "/api/primer/manual-analysis",
        json={"forward": _valid_oligo()},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("forward", {}).get("sequence", "").upper() == _valid_oligo()


def test_guest_can_submit_pipeline(client):
    """Anonymous /api/pipeline/submit must be accepted (not 401)."""
    resp = client.post(
        "/api/pipeline/submit",
        json={"sequence": _valid_template(), "product_min": 100, "product_max": 400},
    )
    assert resp.status_code == 202
    data = resp.get_json()
    assert data.get("job_id")


def test_guest_can_read_own_pipeline_job(client):
    """Guest jobs are readable back via status/result without auth."""
    submit = client.post(
        "/api/pipeline/submit",
        json={"sequence": _valid_template(), "product_min": 100, "product_max": 400},
    )
    assert submit.status_code == 202
    job_id = submit.get_json()["job_id"]
    status = client.get(f"/api/pipeline/status/{job_id}")
    assert status.status_code == 200
    result = client.get(f"/api/pipeline/result/{job_id}")
    assert result.status_code == 200


def test_guest_single_ligand_docking(client):
    """Anonymous single-ligand docking consensus must be accepted (not 401)."""
    resp = client.post(
        "/api/primer/docking/consensus",
        json={
            "sequence": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPDHERGLVDRFYKVELAPTHKGGFGLRGDGFNICKDG",
            "ligand_smiles_list": ["CC(=O)Oc1ccccc1C(=O)O"],
            "top_n": 5,
        },
    )
    assert resp.status_code == 202
    assert resp.get_json().get("job_id")


def test_save_results_still_requires_auth(client):
    """Persistence (saved results) must still 401 for anonymous."""
    resp = client.post(
        "/api/results/save",
        json={"tool": "primer", "title": "t", "inputs": {}, "outputs": {}, "sequences_count": 1},
    )
    assert resp.status_code == 401


def test_logged_in_free_user_is_daily_limited(client):
    """The daily-limit system (not legacy FREE_RUNS) gates logged-in Free users."""
    email = _unique_email()
    reg = client.post(
        "/api/auth/register",
        json={"email": email, "password": "Secret123!", "name": "Free User"},
    )
    assert reg.status_code == 201
    token = reg.headers.get("Set-Cookie", "").split("pf_token=")[1].split(";")[0]

    headers = {"Cookie": f"pf_token={token}"}
    check = client.get("/api/usage/check?tool=primer", headers=headers)
    assert check.status_code == 200
    usage = check.get_json()
    assert usage["can_analyze"] is True
    assert usage["daily_limit"] >= 1

"""
Docking capacity & response-speed work (2026-10-07).

Covers:
  1. Dynamic job timeout  (scales with ligands + sequence; clamps 300–900s)
  2. Route validation caps (≤100 ligands, ≤400 aa sequence mode, PDB-mode
     exemptions, SMILES normalization/dedup, top_n clamping, PDB sanity)
  3. Structure cache        (repeat runs skip the 30–90s web-API fold;
                             fallback helices are never cached)
  4. Pipeline throughput    (2 concurrent Vina lanes sized to the cores;
                             every ligand screened — no silent [:5]);
     GNINA refinement capped to top-K with binary-error fail-fast
  5. Queue robustness       (timeout → actionable error; worker heartbeat
                             keeps long jobs from stale-release re-runs)

The ESMFold web-API sequence cap (MAX_SEQUENCE_LENGTH = 400) was measured
empirically 2026-10-07: L=400 → HTTP 200, L=403+ → HTTP 413.
"""

import asyncio
import json
import os
import subprocess
import time

import pytest

FAKE_PDB = (
    "ATOM      1  N   MET A   1       0.000   0.000   0.000  1.00 50.00           N\n"
    "ATOM      2  CA  MET A   1       1.458   0.000   0.000  1.00 50.00           C\n"
    "ATOM      3  C   MET A   1       2.009   1.420   0.000  1.00 50.00           C\n"
    "ATOM      4  O   MET A   1       1.251   2.390   0.000  1.00 50.00           O\n"
    "TER\nEND\n"
)


def _seq(n: int) -> str:
    """Deterministic standard-amino-acid sequence of length n."""
    aa = "ACDEFGHIKLMNPQRSTVWY"
    return "".join(aa[i % 20] for i in range(n))


def _score(smiles: str) -> float:
    """Deterministic per-ligand Vina score (negative, varies by SMILES)."""
    return -5.0 - (sum(ord(c) for c in smiles) % 50) / 10.0


# ══════════════════════════════════════════════════════════════════════════
# 1. Dynamic job timeout
# ══════════════════════════════════════════════════════════════════════════

def test_job_timeout_scales_and_clamps():
    from primerforge.docking_queue import _job_timeout_seconds

    # base 300 + 8/ligand + 0.25/residue (sequence mode)
    assert _job_timeout_seconds(_seq(100), 1, has_pdb=False) == 300 + 8 + 25
    # PDB-upload mode skips folding → no per-residue cost
    assert _job_timeout_seconds(_seq(400), 1, has_pdb=True) == 308
    # grows with ligand count
    assert _job_timeout_seconds("", 50, True) > _job_timeout_seconds("", 10, True)
    # clamps: floor 300, ceiling 900 (frontend polls ~1000s)
    assert _job_timeout_seconds("", 0, True) == 300
    assert _job_timeout_seconds(_seq(400), 500, False) == 900


# ══════════════════════════════════════════════════════════════════════════
# 2. Route validation caps
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def env(monkeypatch, tmp_path):
    """Fresh app whose create_job is a capture stub (no queue/DB writes)."""
    from primerforge.primer_server import create_app

    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("PRIMERFORGE_DB", str(tmp_path / "scaling.db"))
    monkeypatch.delenv("REDIS_URL", raising=False)
    import primerforge.security as security

    monkeypatch.setattr(security, "init_admin_rbac", lambda application: None)

    import primerforge.docking_queue as dq

    captured: dict = {}

    def fake_create(sequence, ligand_smiles_list, top_n=50, pdb_content=""):
        captured.update(sequence=sequence, ligands=list(ligand_smiles_list),
                        top_n=top_n, pdb_content=pdb_content)
        return "fakejobid1234"

    monkeypatch.setattr(dq, "create_job", fake_create)

    application = create_app()
    app = application.wsgi_app if hasattr(application, "wsgi_app") else application
    return app.test_client(), captured


def _post(client, body):
    return client.post("/api/primer/docking/consensus",
                       data=json.dumps(body), headers={"Content-Type": "application/json"})


def test_route_rejects_101_ligands(env):
    client, captured = env
    r = _post(client, {"sequence": _seq(60), "ligand_smiles_list": ["CCO"] * 101})
    assert r.status_code == 400, r.get_json()
    assert "100 ligands" in r.get_json()["error"]
    assert "captured" not in captured


def test_route_accepts_100_ligands_untruncated(env):
    """The full list must reach create_job — the old queue silently [:5]'d it."""
    client, captured = env
    ligands = [f"CCCN{i}" for i in range(100)]
    r = _post(client, {"sequence": _seq(60), "ligand_smiles_list": ligands})
    assert r.status_code == 202, r.get_json()
    assert len(captured["ligands"]) == 100
    assert captured["ligands"] == ligands


def test_route_dedupes_smiles(env):
    client, captured = env
    r = _post(client, {"sequence": _seq(60),
                       "ligand_smiles_list": ["CCO", "CCO", " CCO ", "c1ccccc1", "c1ccccc1"]})
    assert r.status_code == 202, r.get_json()
    assert captured["ligands"] == ["CCO", "c1ccccc1"]


def test_route_rejects_non_string_ligands(env):
    client, _ = env
    r = _post(client, {"sequence": _seq(60), "ligand_smiles_list": ["CCO", 42]})
    assert r.status_code == 400
    assert "SMILES strings" in r.get_json()["error"]


def test_route_sequence_length_cap_and_pdb_guidance(env):
    client, captured = env
    from primerforge.pipelines.esmfold_engine import MAX_SEQUENCE_LENGTH

    assert MAX_SEQUENCE_LENGTH == 400, "web-API cap re-probe: 400 OK / 403 → 413"
    # 401 aa → refused with PDB-upload guidance
    r = _post(client, {"sequence": _seq(401), "ligand_smiles_list": ["CCO"]})
    assert r.status_code == 400
    err = r.get_json()["error"]
    assert "400 amino acids" in err and "PDB" in err
    # exactly 400 aa → accepted
    r = _post(client, {"sequence": _seq(400), "ligand_smiles_list": ["CCO"]})
    assert r.status_code == 202, r.get_json()
    assert captured["sequence"] == _seq(400)


def test_route_rejects_invalid_amino_acids(env):
    client, _ = env
    r = _post(client, {"sequence": "A" * 12 + "XBZ", "ligand_smiles_list": ["CCO"]})
    assert r.status_code == 400
    assert "Invalid amino acids" in r.get_json()["error"]


def test_route_clamps_top_n(env):
    client, captured = env
    r = _post(client, {"sequence": _seq(60), "ligand_smiles_list": ["CCO"], "top_n": 999})
    assert r.status_code == 202
    assert captured["top_n"] == 100  # frontend slider max (5–100)


def test_pdb_mode_exemptions_and_limits(env):
    client, captured = env
    # PDB mode: long extracted sequence is fine (structure is given)
    long_seq = _seq(1500)
    pdb = FAKE_PDB * 40  # multi-residue-ish ATOM payload
    r = _post(client, {"sequence": long_seq, "ligand_smiles_list": ["CCO"], "pdb_content": pdb})
    assert r.status_code == 202, r.get_json()
    assert captured["sequence"] == long_seq
    # PDB mode: sequence no longer required at all
    r = _post(client, {"sequence": "", "ligand_smiles_list": ["CCO"], "pdb_content": pdb})
    assert r.status_code == 202, r.get_json()
    # PDB without ATOM records → 400
    r = _post(client, {"sequence": "", "ligand_smiles_list": ["CCO"], "pdb_content": "REMARK nothing here\n"})
    assert r.status_code == 400
    assert "ATOM" in r.get_json()["error"]
    # oversized PDB (> 5MB) → 400 (below Flask's 10MB request cap)
    big = "ATOM" + "A" * (5 * 1024 * 1024 + 10)
    r = _post(client, {"sequence": "", "ligand_smiles_list": ["CCO"], "pdb_content": big})
    assert r.status_code == 400
    assert "too large" in r.get_json()["error"].lower()


# ══════════════════════════════════════════════════════════════════════════
# 3. Structure cache
# ══════════════════════════════════════════════════════════════════════════

def _stub_api_success(sequence, report=None, calls=None):
    if calls is not None:
        calls["n"] += 1
    return {"status": "success", "tool": "ESMFold (web API, free)",
            "pdb_string": FAKE_PDB, "plddt_score": 77.0,
            "sequence_length": len(sequence), "message": "api fold", "license": "MIT"}


def test_structure_cache_serves_repeat_runs(monkeypatch, tmp_path):
    import primerforge.pipelines.esmfold_engine as ee

    calls = {"n": 0}

    def fake_fetch(sequence, report=None):
        return _stub_api_success(sequence, calls=calls)

    monkeypatch.setattr(ee, "_fetch_esmfold_api_pdb", fake_fetch)
    monkeypatch.setattr(ee, "_local_gpu_available", lambda: False)
    monkeypatch.setenv("DOCKING_QUEUE_DIR", str(tmp_path / "queue"))

    seq = _seq(120)
    r1 = asyncio.run(ee.predict_structure(seq))
    r2 = asyncio.run(ee.predict_structure(seq))

    assert calls["n"] == 1, "second run must be served from the structure cache"
    assert r1["pdb_string"] == FAKE_PDB
    assert r2["pdb_string"] == FAKE_PDB
    assert "structure cache" in r2["message"]
    # cache file exists under the queue dir
    cache_dir = os.path.join(str(tmp_path / "queue"), "structure_cache")
    assert len([f for f in os.listdir(cache_dir) if f.endswith(".json")]) == 1


def test_fallback_helix_is_never_cached(monkeypatch, tmp_path):
    """A web-API outage must not poison the cache for 7 days."""
    import primerforge.pipelines.esmfold_engine as ee

    state = {"ok": False, "n": 0}

    def fake_fetch(sequence, report=None):
        state["n"] += 1
        return _stub_api_success(sequence) if state["ok"] else None

    monkeypatch.setattr(ee, "_fetch_esmfold_api_pdb", fake_fetch)
    monkeypatch.setattr(ee, "_local_gpu_available", lambda: False)
    monkeypatch.setenv("DOCKING_QUEUE_DIR", str(tmp_path / "queue"))

    seq = _seq(80)
    r1 = asyncio.run(ee.predict_structure(seq))
    assert r1["tool"] == "Fallback helical bundle"
    assert r1["plddt_score"] == 0

    state["ok"] = True
    r2 = asyncio.run(ee.predict_structure(seq))
    assert state["n"] == 2, "fallback must not be cached — recovery must hit the API"
    assert "web API" in r2["tool"]
    assert r2["plddt_score"] == 77.0


# ══════════════════════════════════════════════════════════════════════════
# 4. Pipeline: parallel Vina, full ligand coverage, GNINA top-K + fail-fast
# ══════════════════════════════════════════════════════════════════════════

def _run_pipeline(monkeypatch, ligands, top_n=None, gnina_stub=...):
    import primerforge.pipelines.consensus_pipeline as cp
    import primerforge.pipelines.docking_engine as de

    async def fake_esmfold(sequence, progress_callback=None):
        return {"status": "success", "tool": "test", "pdb_string": FAKE_PDB,
                "plddt_score": 88.0, "sequence_length": len(sequence)}

    conc = {"cur": 0, "max": 0}

    async def fake_vina(receptor_pdb, ligand_smiles, exhaustiveness=8,
                        receptor_pdbqt_path=None, cpu=None):
        conc["cur"] += 1
        conc["max"] = max(conc["max"], conc["cur"])
        await asyncio.sleep(0.03)
        conc["cur"] -= 1
        return {"binding_affinity": _score(ligand_smiles),
                "structure": {"ligand": FAKE_PDB}}

    async def noop_progress(stage, msg, metadata=None):
        return None

    def fake_pdbqt(receptor_pdb, output_path):
        with open(output_path, "w") as f:
            f.write("ATOM      1  C   UNL A   1       0.000   0.000   0.000  0.00  0.00     0.000 C\n")
        return True

    monkeypatch.setattr(cp, "esmfold_predict", fake_esmfold)
    monkeypatch.setattr(cp, "run_vina_docking", fake_vina)
    monkeypatch.setattr(de, "pdb_to_pdbqt", fake_pdbqt)
    if gnina_stub is not ...:
        monkeypatch.setattr(cp, "run_gnina_docking", gnina_stub)

    result = asyncio.run(cp.run_consensus_pipeline(
        _seq(40), ligands, top_n=top_n if top_n is not None else len(ligands),
        progress_callback=noop_progress))
    return result, conc


def test_vina_runs_in_parallel_lanes(monkeypatch):
    expected_lanes = min(2, os.cpu_count() or 1)
    ligands = [f"CCO{'C' * i}" for i in range(6)]
    result, conc = _run_pipeline(monkeypatch, ligands)
    assert result["status"] == "success", result.get("message")
    assert conc["max"] == expected_lanes, (
        f"expected {expected_lanes} concurrent Vina lanes, saw {conc['max']}")


def test_every_ligand_is_screened_no_truncation(monkeypatch):
    ligands = [f"CCCN{i}" for i in range(12)]
    result, _ = _run_pipeline(monkeypatch, ligands)
    assert result["status"] == "success", result.get("message")
    assert result["stage2"]["screened"] == 12
    assert result["stage2"]["successful"] == 12
    assert len(result["ranked_results"]) == 12


def test_gnina_refines_only_top_k(monkeypatch):
    calls = {"n": 0}

    async def ok_gnina(receptor_pdb, ligand_smiles, exhaustiveness=4,
                       receptor_pdbqt_path=None):
        calls["n"] += 1
        return {"binding_affinity": -8.0, "cnn_affinity": 0.9,
                "structure": {"ligand": FAKE_PDB}}

    ligands = [f"CCCN{i}" for i in range(15)]
    result, _ = _run_pipeline(monkeypatch, ligands, gnina_stub=ok_gnina)
    assert result["status"] == "success", result.get("message")
    from primerforge.pipelines.consensus_pipeline import GNINA_REFINE_TOP_K
    assert calls["n"] == GNINA_REFINE_TOP_K == 10
    assert result["stage3"]["refined"] == 10
    assert result["stage3"]["vina_only"] == 5
    assert result["stage3"]["best_gnina_score"] == -8.0
    # ranked list still covers every candidate (Vina-only fallback ranking)
    ranked = result["ranked_results"]
    assert len(ranked) == 15
    assert all(c.get("consensus_rank") for c in ranked)


def test_gnina_binary_error_fails_fast(monkeypatch):
    """Missing/broken gnina binary → ONE attempt, not K (was 50 on prod)."""
    calls = {"n": 0}

    async def broken_gnina(receptor_pdb, ligand_smiles, exhaustiveness=4,
                           receptor_pdbqt_path=None):
        calls["n"] += 1
        raise FileNotFoundError("gnina: No such file or directory")

    ligands = [f"CCCN{i}" for i in range(15)]
    result, _ = _run_pipeline(monkeypatch, ligands, gnina_stub=broken_gnina)
    assert result["status"] == "success", result.get("message")
    assert calls["n"] == 1, f"fail-fast broken: {calls['n']} attempts"
    s3 = result["stage3"]
    assert s3["status"] == "gnina_failed"
    assert any("No such file" in r for r in s3["failure_reasons"])
    ranked = result["ranked_results"]
    assert len(ranked) == 15
    # every candidate still carries a usable consensus score (Vina fallback)
    assert all(c.get("consensus_score") is not None for c in ranked)


def test_gnina_per_ligand_error_does_not_fail_fast(monkeypatch):
    """A ligand-specific failure must not abort refinement of the rest."""
    calls = {"n": 0}

    async def flaky_gnina(receptor_pdb, ligand_smiles, exhaustiveness=4,
                          receptor_pdbqt_path=None):
        calls["n"] += 1
        raise RuntimeError("CNN scoring failed for this molecule")

    ligands = [f"CCCN{i}" for i in range(15)]
    result, _ = _run_pipeline(monkeypatch, ligands, gnina_stub=flaky_gnina)
    from primerforge.pipelines.consensus_pipeline import GNINA_REFINE_TOP_K
    assert calls["n"] == GNINA_REFINE_TOP_K  # all top-K attempted
    s3 = result["stage3"]
    assert s3["status"] == "gnina_failed"
    assert len(s3["failure_reasons"]) <= 5  # bounded payload


# ══════════════════════════════════════════════════════════════════════════
# 5. Queue robustness
# ══════════════════════════════════════════════════════════════════════════

def test_process_job_timeout_yields_actionable_error(monkeypatch, tmp_path):
    import primerforge.docking_queue as dq

    for attr in ("PENDING_DIR", "RUNNING_DIR", "COMPLETE_DIR", "FAILED_DIR"):
        monkeypatch.setattr(dq, attr, str(tmp_path / attr.lower()))
    os.makedirs(dq.RUNNING_DIR, exist_ok=True)
    job = {"job_id": "tjob1", "sequence": _seq(60),
           "ligand_smiles_list": ["CCO"], "top_n": 5, "pdb_content": ""}
    with open(os.path.join(dq.RUNNING_DIR, "tjob1.json"), "w") as f:
        json.dump(job, f)

    seen: dict = {}

    def fake_run(cmd, **kwargs):
        seen["timeout"] = kwargs.get("timeout")
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs.get("timeout", 0))

    monkeypatch.setattr(subprocess, "run", fake_run)
    dq._process_job(job)

    assert seen["timeout"] == dq._job_timeout_seconds(_seq(60), 1, False)
    with open(os.path.join(dq.FAILED_DIR, "tjob1.json")) as f:
        failed = json.load(f)
    assert failed["status"] == "failed"
    assert "timed out" in failed["error"].lower()
    assert "fewer ligands" in failed["error"]


def test_worker_heartbeat_keeps_long_jobs_out_of_stale_release(monkeypatch, tmp_path):
    from primerforge import docking_worker as dw

    monkeypatch.setenv("DOCKING_QUEUE_DIR", str(tmp_path))
    os.makedirs(os.path.join(str(tmp_path), "running"), exist_ok=True)
    path = os.path.join(str(tmp_path), "running", "tjob2.json")
    with open(path, "w") as f:
        json.dump({"job_id": "tjob2", "status": "running"}, f)
    old = time.time() - 600  # 10 min old → would be stale-released
    os.utime(path, (old, old))

    stop = dw._start_heartbeat("tjob2", interval=0.05)
    time.sleep(0.25)
    stop.set()
    assert os.path.getmtime(path) > old + 60, "heartbeat did not touch the RUNNING file"


def test_no_silent_ligand_truncation_in_queue_or_worker():
    """Regression tripwire: the [:5] truncation silently dropped 95% of a
    submitted library (queue AND worker both carried it)."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pattern = '(job.get("ligand_smiles_list") or [])[:5]'
    for rel in ("primerforge/docking_queue.py", "primerforge/docking_worker.py"):
        with open(os.path.join(root, rel)) as f:
            src = f.read()
        assert pattern not in src, f"{rel} reintroduced silent ligand truncation"

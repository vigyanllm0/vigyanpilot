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


def multi_res_pdb(n: int = 12) -> str:
    """n-residue poly-ALA backbone with valid fixed-width ATOM records.

    The consensus route pre-validates uploaded structures at ≥10 CA
    residues (Phase 4) — single-residue payloads are rejected with 400.
    """
    lines = []
    serial = 1
    for i in range(n):
        for name, el in (("N", "N"), ("CA", "C"), ("C", "C"), ("O", "O")):
            x = 3.8 * (i + 1)
            y = 1.2 if name == "N" else 0.0
            lines.append(
                f"ATOM  {serial:>5d} {name:^4s} ALA A{i + 1:>4d}    "
                f"{x:>8.3f}{y:>8.3f}{0.0:>8.3f}  1.00 50.00          {el:>2s}"
            )
            serial += 1
    lines.append("TER")
    lines.append("END")
    return "\n".join(lines) + "\n"


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

    # base 300 + 8/ligand + 0.25/residue (sequence mode) + 45/GNINA refine
    # (top-K=10; n=1 → 1 refine) — mirrors consensus_pipeline's stage-3 cost
    assert _job_timeout_seconds(_seq(100), 1, has_pdb=False) == 300 + 8 + 25 + 45
    # PDB-upload mode skips folding → no per-residue cost (GNINA term remains)
    assert _job_timeout_seconds(_seq(400), 1, has_pdb=True) == 300 + 8 + 45
    # GNINA term saturates at top-K=10 — ligand 11 costs only the Vina term
    # (838 vs 830, both under the 900 clamp; +53 if GNINA were uncapped)
    assert _job_timeout_seconds("", 11, True) == _job_timeout_seconds("", 10, True) + 8
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

    def fake_create(sequence, ligand_smiles_list, top_n=50, pdb_content="", box=None):
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
    pdb = multi_res_pdb(12)  # ≥10 CA residues (route pre-validation, Phase 4)
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
    # <10 CA residues (here: 1) → 400 BEFORE anything is queued (Phase 4)
    r = _post(client, {"sequence": "", "ligand_smiles_list": ["CCO"], "pdb_content": FAKE_PDB})
    assert r.status_code == 400, r.get_json()
    assert "CA" in r.get_json()["error"]
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
                        receptor_pdbqt_path=None, cpu=None, box=None):
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
    # Stub the availability probe as OK — these tests exercise the run path
    # with fake binaries; the real probe would legitimately skip stage 3.
    monkeypatch.setattr(cp, "gnina_available", lambda **kw: {
        "ok": True, "path": "gnina", "version": "test", "reason": None})

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
                       receptor_pdbqt_path=None, box=None):
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
                           receptor_pdbqt_path=None, box=None):
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
                          receptor_pdbqt_path=None, box=None):
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

    # Fake clock: each time.time() call jumps +1000s, so the wait loop's
    # first budget check (start already consumed call #1) trips immediately.
    calls = {"n": 0}

    def fake_clock():
        calls["n"] += 1
        return calls["n"] * 1000.0

    monkeypatch.setattr(dq, "time", type("T", (), {"time": staticmethod(fake_clock)}))

    procs: list = []

    class FakeProc:
        pid = 0xDEAD
        returncode = None
        killed = False

        def communicate(self, timeout=None):
            if timeout is None:
                return ("", "")
            raise subprocess.TimeoutExpired(cmd=["fake"], timeout=timeout)

        def kill(self):
            self.killed = True
            self.returncode = -9

    def fake_popen(cmd, **kwargs):
        procs.append(FakeProc())
        return procs[-1]

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    dq._process_job(job)

    # spawned in its own session so killpg can't hit the queue's group
    assert procs and procs[0].killed
    with open(os.path.join(dq.FAILED_DIR, "tjob1.json")) as f:
        failed = json.load(f)
    assert failed["status"] == "failed"
    assert "timed out" in failed["error"].lower()
    assert "fewer ligands" in failed["error"]
    # temp job-input file cleaned up
    assert not os.path.exists(os.path.join(dq.RUNNING_DIR, "tjob1.input"))


def test_worker_heartbeat_keeps_long_jobs_out_of_stale_release(monkeypatch, tmp_path):
    # docking_worker applies RLIMIT_AS=600MB at import — correct for its
    # standalone subprocess role, but Linux ENFORCES it (macOS ignores it),
    # which would cap pytest's own address space and wedge Thread.start()
    # inside this test. Neutralize before the module's first import.
    import resource as _res

    monkeypatch.setattr(_res, "setrlimit", lambda *args, **kwargs: None)
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


# ══════════════════════════════════════════════════════════════════════════
# 6. Stop run  (cancel route + queue marker + process-tree kill)
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def qdirs(monkeypatch, tmp_path):
    """Isolated queue directories — never the repo's docking_queue/."""
    import primerforge.docking_queue as dq

    for attr in ("PENDING_DIR", "RUNNING_DIR", "COMPLETE_DIR", "FAILED_DIR"):
        monkeypatch.setattr(dq, attr, str(tmp_path / attr.lower()))
    for d in (dq.PENDING_DIR, dq.RUNNING_DIR, dq.COMPLETE_DIR, dq.FAILED_DIR):
        os.makedirs(d, exist_ok=True)
    return dq


def _write_job(dq, directory, job_id, status):
    job = {"job_id": job_id, "status": status, "type": "docking",
           "sequence": _seq(60), "ligand_smiles_list": ["CCO"], "top_n": 5,
           "pdb_content": "", "created_at": time.time(),
           "updated_at": time.time(), "result": None, "error": None}
    with open(os.path.join(directory, f"{job_id}.json"), "w") as f:
        json.dump(job, f)
    return job


def test_cancel_pending_job_fails_immediately(qdirs):
    dq = qdirs
    _write_job(dq, dq.PENDING_DIR, "c1", "pending")
    assert dq.cancel_job("c1") == "cancelled"
    assert not os.path.exists(os.path.join(dq.PENDING_DIR, "c1.json"))
    job = dq.get_job("c1")
    assert job["status"] == "failed"
    assert job["error"] == "Stopped by user."
    assert not os.path.exists(dq._cancel_marker_path("c1"))


def test_cancel_running_job_writes_marker_only(qdirs):
    """Running → the route must NOT fail the job itself; it flags the queue's
    wait loop, which kills the process tree within ~1s."""
    dq = qdirs
    _write_job(dq, dq.RUNNING_DIR, "c2", "running")
    assert dq.cancel_job("c2") == "stopping"
    job = dq.get_job("c2")
    assert job["status"] == "running"
    assert os.path.exists(dq._cancel_marker_path("c2"))


def test_cancel_unknown_and_finished_jobs(qdirs):
    dq = qdirs
    assert dq.cancel_job("nope") == "not_found"
    _write_job(dq, dq.COMPLETE_DIR, "c3", "completed")
    assert dq.cancel_job("c3") == "finished"
    assert dq.get_job("c3")["status"] == "completed"  # untouched


def test_process_job_pre_spawn_marker_stops_without_spawn(qdirs, monkeypatch):
    """A stop that lands while the job is re-queued must not burn CPU."""
    dq = qdirs
    _write_job(dq, dq.RUNNING_DIR, "c4", "running")
    with open(dq._cancel_marker_path("c4"), "w"):
        pass

    def forbid_spawn(*args, **kwargs):
        raise AssertionError("worker must not spawn for a stopped job")

    monkeypatch.setattr(subprocess, "Popen", forbid_spawn)
    dq._process_job(dq.get_job("c4"))
    job = dq.get_job("c4")
    assert job["status"] == "failed"
    assert job["error"] == "Stopped by user."
    assert not os.path.exists(dq._cancel_marker_path("c4"))


def test_process_job_kills_running_worker_on_marker(qdirs, monkeypatch):
    """Marker written mid-run → wait loop kills the tree, fails the job,
    and cleans marker + input file."""
    dq = qdirs
    _write_job(dq, dq.RUNNING_DIR, "c5", "running")
    marker = dq._cancel_marker_path("c5")
    procs: list = []

    class FakeProc:
        pid = 0xBEEF
        returncode = None

        def __init__(self):
            self.killed = False
            self._calls = 0

        def communicate(self, timeout=None):
            if timeout is None:
                return ("", "")
            self._calls += 1
            if self._calls == 1:
                with open(marker, "w"):
                    pass  # user presses Stop while the job runs
            raise subprocess.TimeoutExpired(cmd=["fake"], timeout=timeout)

        def kill(self):
            self.killed = True
            self.returncode = -9

    def fake_popen(cmd, **kwargs):
        assert kwargs.get("start_new_session") is True, \
            "worker must own its process group so killpg can't hit the queue"
        p = FakeProc()
        procs.append(p)
        return p

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    dq._process_job(dq.get_job("c5"))

    assert procs and procs[0].killed
    job = dq.get_job("c5")
    assert job["status"] == "failed"
    assert job["error"] == "Stopped by user."
    assert not os.path.exists(marker)
    assert not os.path.exists(os.path.join(dq.RUNNING_DIR, "c5.input"))


def test_cancel_route_status_codes(env, qdirs):
    """POST /api/primer/docking/cancel/<id>: 200 pending, 202 running,
    409 finished, 404 unknown — and the status route reflects the stop."""
    client, _ = env
    dq = qdirs  # same monkeypatched dirs the route module reads
    _write_job(dq, dq.PENDING_DIR, "r1", "pending")
    assert client.post("/api/primer/docking/cancel/r1").status_code == 200
    assert client.post("/api/primer/docking/cancel/r1").status_code == 409  # already stopped

    _write_job(dq, dq.RUNNING_DIR, "r2", "running")
    assert client.post("/api/primer/docking/cancel/r2").status_code == 202

    _write_job(dq, dq.COMPLETE_DIR, "r3", "completed")
    assert client.post("/api/primer/docking/cancel/r3").status_code == 409

    assert client.post("/api/primer/docking/cancel/nope").status_code == 404

    # status endpoint reports the stopped job as failed with the stop error
    st = client.get("/api/primer/docking/status/r1").get_json()
    assert st["status"] == "failed"
    assert st["error"] == "Stopped by user."


# ════════════════════════════════════════════════════════════════════════════
# 7. Deep-audit hardening (2026-10-08)
#    - job-id path safety: client ids never reach os.path.join unvalidated
#    - corrupt job records → 404 (UI clears) instead of a ~17-minute poll loop
#    - credit settlement never strands an invisible orphan run
#    - submit-path UI always re-enables the run button (verified headless;
#      covered here server-side via the accounting contract)
# ════════════════════════════════════════════════════════════════════════════

def test_job_id_guard_blocks_traversal_reads_and_moves(qdirs):
    """A '../x' id must never resolve outside the queue directories.

    Planted record sits at exactly where pending/../x.json would land —
    without valid_job_id() get_job would read it and cancel_job would MOVE it
    into the failed dir."""
    dq = qdirs
    outside = os.path.join(os.path.dirname(dq.PENDING_DIR), "x.json")
    with open(outside, "w") as f:
        json.dump({"job_id": "../x", "status": "completed",
                   "result": {"planted": True}}, f)
    try:
        assert dq.get_job("../x") is None
        assert dq.cancel_job("../x") == "not_found"
        assert os.path.exists(outside)  # untouched — no move, no delete
        # other hostile shapes: sub-dir traversal, bare dots, NUL, oversize
        assert dq.get_job("a/b") is None
        assert dq.cancel_job("a/b") == "not_found"
        for bad in ("..", "a\\b", "ab\x00cd", "x" * 65, "", None):
            assert dq.get_job(bad) is None
            assert dq.cancel_job(bad) == "not_found"
            assert dq.claim_job(bad) is False
            assert dq.complete_job(bad, {}) is False
        # valid ids (uuid-hex in prod, short tokens in tests) keep working
        _write_job(dq, dq.PENDING_DIR, "ok-1_Ab9", "pending")
        assert dq.get_job("ok-1_Ab9")["status"] == "pending"
        assert dq.cancel_job("ok-1_Ab9") == "cancelled"
    finally:
        if os.path.exists(outside):
            os.remove(outside)


def test_status_route_rejects_unsafe_ids(env, qdirs):
    """Route level: '%2F' separators die in routing (werkzeug AND gunicorn —
    probed empirically), ids that survive routing die in the id guard."""
    client, _ = env
    assert client.get(
        "/api/primer/docking/status/..%2F..%2Fetc%2Fpasswd").status_code == 404
    # Routing-level rejection keeps its real code (404/405) — never a fake 500
    resp = client.post("/api/primer/docking/cancel/..%2F..%2Fx")
    assert resp.status_code in (404, 405)
    assert resp.get_json()["code"] != "500"
    assert client.get("/api/primer/docking/status/..").status_code == 404
    # a dot survives routing but fails the id policy → guard (not routing)
    assert client.get("/api/primer/docking/status/bad.id").status_code == 404
    assert client.post("/api/primer/docking/structure/upload/bad.id/1").status_code == 404


def test_corrupt_job_record_is_404_not_polling_forever(env, qdirs):
    """Truncated job file (writer crash) must read as missing so the frontend
    404s, clears its stored run and stops — never raises on every poll."""
    client, _ = env
    with open(os.path.join(qdirs.COMPLETE_DIR, "deadbeef0001.json"), "w") as f:
        f.write('{"job_id": "deadbeef0001", "status": "comp')  # crash mid-dump
    assert qdirs.get_job("deadbeef0001") is None
    resp = client.get("/api/primer/docking/status/deadbeef0001")
    assert resp.status_code == 404
    assert resp.get_json()["code"] == "NOT_FOUND"


def test_corrupt_pending_record_is_dropped_not_retried_forever(qdirs):
    """claim_job must drop an unreadable pending file instead of re-claiming
    (and failing) it every poll cycle forever."""
    dq = qdirs
    p = os.path.join(dq.PENDING_DIR, "bad00bad0001.json")
    with open(p, "w") as f:
        f.write('{"job_id": "bad00bad0001", "status": "pend')
    assert dq.claim_job("bad00bad0001") is False
    assert not os.path.exists(p)


def test_settle_no_tokens_cancels_orphan_job(qdirs):
    """PG consume → False (402) must also stop the just-queued job — before
    this fix the job ran to completion invisibly while the user only saw a
    payment prompt."""
    from primerforge.primer_server import _settle_docking_job
    dq = qdirs
    _write_job(dq, dq.PENDING_DIR, "orphan402a", "pending")
    user = {"email": "u@example.com", "role": "user", "user_id": 7}
    out = _settle_docking_job("orphan402a", user, True, lambda uid, email: False, None)
    assert out is not None
    body, status = out
    assert status == 402
    assert body["code"] == "PAYMENT_REQUIRED"
    job = dq.get_job("orphan402a")
    assert job["status"] == "failed"
    assert job["error"] == "Stopped by user."


def test_settle_credit_exception_cancels_orphan_job(qdirs):
    """Money path: if consume_docking_token throws, the run must not execute
    unsettled — cancel + 500, never a silent free run."""
    from primerforge.primer_server import _settle_docking_job
    dq = qdirs
    _write_job(dq, dq.PENDING_DIR, "orphan500x", "pending")

    def boom(uid, email):
        raise RuntimeError("pg down")

    out = _settle_docking_job("orphan500x", {"email": "u@e.c", "role": "user", "user_id": 7},
                              True, boom, None)
    assert out is not None and out[1] == 500
    assert dq.get_job("orphan500x")["status"] == "failed"


def test_settle_bookkeeping_failure_lets_run_proceed(qdirs):
    """SQLite counter drift is non-authoritative: the client already holds
    its 202, so the run must survive a usage-log failure."""
    from primerforge.primer_server import _settle_docking_job
    dq = qdirs
    _write_job(dq, dq.PENDING_DIR, "keepme12345", "pending")

    def boom(email):
        raise RuntimeError("db locked")

    out = _settle_docking_job("keepme12345", {"email": "u@e.c", "role": "user"},
                              False, None, boom)
    assert out is None
    assert dq.get_job("keepme12345")["status"] == "pending"


def test_settle_admin_and_guest_skip_accounting(qdirs):
    from primerforge.primer_server import _settle_docking_job
    called = []
    assert _settle_docking_job("x1", {"email": "a@b.c", "role": "admin"},
                               True, lambda *a: called.append(a), None) is None
    assert _settle_docking_job("x2", None, True,
                               lambda *a: called.append(a), None) is None
    assert called == []


@pytest.fixture
def raise_increment(monkeypatch):
    """Replace auth.increment_docking_usage BEFORE env's create_app binds it
    (fixture is listed first on purpose — the test asserts it was called, so
    a reordering fails loudly instead of silently passing)."""
    import primerforge.auth as auth_mod

    called = {"n": 0}

    def boom(email):
        called["n"] += 1
        raise RuntimeError("usage db locked")

    monkeypatch.setattr(auth_mod, "increment_docking_usage", boom)
    return called


def test_consensus_bookkeeping_failure_still_returns_202(raise_increment, env, qdirs):
    """Logged-in submit where usage bookkeeping throws: client gets the 202
    it was promised (job proceeds), error is logged — not an orphaned run
    behind a 500."""
    client, _ = env
    assert raise_increment is not None  # fixture ordering sanity
    reg = client.post(
        "/api/auth/register",
        json={"email": "settle-user@example.com", "password": "Vault-Key!Pr1mer26",
              "name": "Settle User"},
    )
    assert reg.status_code == 201
    token = reg.headers.get("Set-Cookie", "").split("pf_token=")[1].split(";")[0]

    resp = client.post(
        "/api/primer/docking/consensus",
        data=json.dumps({
            "sequence": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPDHERGLVDRFYKVELAPTHKGGFGLRGDGFNICKDG",
            "ligand_smiles_list": ["CCO"],
            "top_n": 5,
        }),
        headers={"Content-Type": "application/json", "Cookie": f"pf_token={token}"},
    )
    assert resp.status_code == 202
    assert resp.get_json().get("job_id")
    assert raise_increment["n"] == 1  # the patched path really ran


def test_http_exceptions_keep_their_status_codes(env):
    """Routing-level HTTPExceptions must keep their real status codes: a POST
    to a GET-only rule used to surface as a fake 500 (the catch-all
    Exception handler swallowed MethodNotAllowed)."""
    client, _ = env
    resp = client.post("/health")
    assert resp.status_code == 405
    assert resp.get_json()["code"] == "405"


def test_worker_write_result_is_atomic(tmp_path, monkeypatch):
    """The worker subprocess's result write must be atomic (tmp + os.replace):
    a truncated empty file in complete/ would surface as a status 404
    mid-completion and make the UI abandon a run that is actually finishing
    (live flake, 2026-10-08 — the last non-atomic writer in the queue path)."""
    import resource as _res
    monkeypatch.setattr(_res, "setrlimit", lambda *a, **k: None)  # see test_worker heartbeat note
    from primerforge import docking_worker as dw

    base = str(tmp_path / "q")
    monkeypatch.setenv("DOCKING_QUEUE_DIR", base)
    for d in ("pending", "running", "complete", "failed"):
        os.makedirs(os.path.join(base, d), exist_ok=True)
    running = os.path.join(base, "running", "wtest01.json")
    with open(running, "w") as f:
        json.dump({"job_id": "wtest01", "status": "running", "sequence": "MK",
                   "ligand_smiles_list": ["CCO"], "top_n": 5}, f)

    dw.write_result("wtest01", result={"vina_score": -7.2})

    final = os.path.join(base, "complete", "wtest01.json")
    assert os.path.exists(final)
    with open(final) as f:
        job = json.load(f)
    assert job["status"] == "completed"
    assert job["result"]["vina_score"] == -7.2
    assert not os.path.exists(running)
    leftovers = os.listdir(os.path.join(base, "complete"))
    assert not any(".tmp" in n for n in leftovers), leftovers

    # error path: same guarantees, lands in failed/
    running2 = os.path.join(base, "running", "wtest02.json")
    with open(running2, "w") as f:
        json.dump({"job_id": "wtest02", "status": "running"}, f)
    dw.write_result("wtest02", error="Docking failed")
    with open(os.path.join(base, "failed", "wtest02.json")) as f:
        assert json.load(f)["error"] == "Docking failed"
    assert not any(".tmp" in n for n in os.listdir(os.path.join(base, "failed")))

"""Regression tests for the docking 3D-data pipeline fixes (2026-10-07).

Covers the three root causes found by the end-to-end docking run:

  1. ``_extract_plddt_from_pdb`` used to read the *occupancy* column
     (cols 55-60, always 1.00) instead of the B-factor column (61-66),
     so every ESMFold-web-API structure reported pLDDT = 1.0 and the
     frontend's fraction→percent guard displayed a false "100%".
  2. ``pdb_to_pdbqt``'s RDKit fallback died on predicted structures with
     side-chain clashes: RDKit's proximity bonding created an impossible
     inter-residue bond (e.g. Asp OD1 … Ser OG at 1.5 A) and sanitization
     raised, aborting the whole docking job ("Failed to convert receptor
     PDB to PDBQT."). The tolerant parser now drops only such clash bonds
     without moving any coordinate.
  3. GNINA failures were swallowed at DEBUG level, making production
     breakage undiagnosable — they now surface as
     ``stage3.failure_reasons`` in the job result.
  4. No-GPU hosts (the production cloud box has none) must never load the
     local ESMFold model — 8.4GB download, >10GB RAM OOM, 300s job-timeout
     blowout on CPU. They go straight to the free ESMFold web API (remote
     GPU) with one fast retry on 429/5xx, then an honest helical fallback.
  5. Rate limits: POST /docking/consensus is 5/min per IP (6th rapid
     submit → 429 RATE_LIMITED) while status/structure polling — which the
     3D viewer depends on — must never throttle.
"""

import pytest

from primerforge.pipelines.docking_engine import _mol_from_pdb
from primerforge.pipelines.esmfold_engine import _extract_plddt_from_pdb


@pytest.fixture(autouse=True)
def _isolated_structure_cache(tmp_path, monkeypatch):
    """predict_structure caches real predictions under DOCKING_QUEUE_DIR —
    point it at a per-test tmp dir so tests never read/write the repo cache
    (cross-test contamination would defeat path-selection assertions)."""
    monkeypatch.setenv("DOCKING_QUEUE_DIR", str(tmp_path / "docking_queue"))


# ── 1. pLDDT extraction ─────────────────────────────────────────────────────

_PDB_TEMPLATE = (
    "ATOM      1  N   MET A   1       2.808   9.807 -15.108{occ}{b}           N  \n"
    "ATOM      2  CA  MET A   1       3.100  10.500 -14.000{occ}{b}           C  \n"
)


def test_plddt_reads_bfactor_not_occupancy():
    """B-factor 0.32 with occupancy 1.00 must yield ~32%, not 1.0."""
    pdb = _PDB_TEMPLATE.format(occ="  1.00", b="  0.32")
    assert _extract_plddt_from_pdb(pdb) == pytest.approx(32.0, abs=0.5)


def test_plddt_fraction_scale_is_normalized_to_percent():
    """ESMFold web API writes pLDDT on a 0-1 scale → must return percent."""
    pdb = _PDB_TEMPLATE.format(occ="  1.00", b="  0.87")
    assert _extract_plddt_from_pdb(pdb) == pytest.approx(87.0, abs=0.5)


def test_plddt_standard_0_100_scale_unchanged():
    """Standard ESMFold PDBs (0-100 in B-factor) must not be scaled again."""
    pdb = _PDB_TEMPLATE.format(occ="  1.00", b=" 87.50")
    assert _extract_plddt_from_pdb(pdb) == pytest.approx(87.5, abs=0.5)


def test_plddt_empty_pdb_returns_zero():
    assert _extract_plddt_from_pdb("HEADER    TEST\nEND\n") == 0.0


# ── 2. clash-tolerant PDB parsing ───────────────────────────────────────────

# Ser8 OG sits 0.7-1.5 A from Asp10 OD1/CG (the clash geometry that killed
# docking): RDKit proximity-bonds them → O with valence 3 → sanitization
# raised. The template below uses standard PDB column alignment.
_CLASH_PDB = """\
ATOM      1  N   MET A   1       0.000   0.000   0.000  1.00 50.00           N
ATOM      2  CA  MET A   1       1.458   0.000   0.000  1.00 50.00           C
ATOM      3  C   MET A   1       2.009   1.420   0.000  1.00 50.00           C
ATOM      4  O   MET A   1       1.251   2.390   0.000  1.00 50.00           O
ATOM      5  CB  MET A   1       2.009  -0.770   1.200  1.00 50.00           C
ATOM      6  N   SER A   8       3.300   1.500   0.000  1.00 50.00           N
ATOM      7  CA  SER A   8       4.000   2.700   0.000  1.00 50.00           C
ATOM      8  C   SER A   8       5.500   2.500   0.000  1.00 50.00           C
ATOM      9  O   SER A   8       6.100   1.450   0.000  1.00 50.00           O
ATOM     10  CB  SER A   8       3.500   3.900   0.800  1.00 50.00           C
ATOM     11  OG  SER A   8       0.000   3.600   0.700  1.00 50.00           O
ATOM     12  N   ASP A  10       6.000   3.600   0.000  1.00 50.00           N
ATOM     13  CA  ASP A  10       7.400   3.600   0.000  1.00 50.00           C
ATOM     14  C   ASP A  10       7.900   5.050   0.000  1.00 50.00           C
ATOM     15  O   ASP A  10       7.150   6.020   0.000  1.00 50.00           O
ATOM     16  CG  ASP A  10       0.000   2.400   0.700  1.00 50.00           C
ATOM     17  OD1 ASP A  10       0.000   3.600   1.400  1.00 50.00           O
ATOM     18  OD2 ASP A  10       1.100   2.000   0.200  1.00 50.00           O
TER
END
"""


def test_mol_from_pdb_survives_sidechain_clash():
    """The clash geometry must not abort parsing; all 18 atoms kept."""
    mol = _mol_from_pdb(_CLASH_PDB)
    assert mol is not None, "clash-tolerant parse returned None"
    assert mol.GetNumAtoms() == 18


def test_mol_from_pdb_clash_bond_removed():
    mol = _mol_from_pdb(_CLASH_PDB)
    assert mol is not None
    from rdkit import Chem

    Chem.SanitizeMol(mol)  # must not raise — chemistry is valid now
    og = next(a for a in mol.GetAtoms()
              if a.GetPDBResidueInfo().GetName().strip() == "OG")
    foreign = [
        b.GetOtherAtom(og).GetPDBResidueInfo().GetResidueNumber()
        for b in og.GetBonds()
        if b.GetOtherAtom(og).GetPDBResidueInfo().GetResidueNumber() != 8
    ]
    assert foreign == [], f"inter-residue clash bond(s) still present: {foreign}"


def test_mol_from_pdb_peptide_bonds_kept():
    """Cleanup must only drop non-backbone inter-residue bonds."""
    mol = _mol_from_pdb(_CLASH_PDB)
    assert mol is not None
    inter_res_cn = 0
    for b in mol.GetBonds():
        i1 = b.GetBeginAtom().GetPDBResidueInfo()
        i2 = b.GetEndAtom().GetPDBResidueInfo()
        if i1 is None or i2 is None or i1.GetResidueNumber() == i2.GetResidueNumber():
            continue
        if {i1.GetName().strip(), i2.GetName().strip()} == {"C", "N"}:
            inter_res_cn += 1
    # fixture has peptide pairs 1→8 and 8→10
    assert inter_res_cn == 2, f"peptide bonds lost: {inter_res_cn}"


def test_mol_from_pdb_clean_structure_untouched():
    """A well-behaved PDB parses on the fast path with no bond removal."""
    clean = """\
ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00 50.00           N
ATOM      2  CA  ALA A   1       1.458   0.000   0.000  1.00 50.00           C
ATOM      3  C   ALA A   1       2.009   1.420   0.000  1.00 50.00           C
ATOM      4  O   ALA A   1       1.251   2.390   0.000  1.00 50.00           O
ATOM      5  CB  ALA A   1       2.009  -0.770   1.200  1.00 50.00           C
TER
END
"""
    mol = _mol_from_pdb(clean)
    assert mol is not None
    assert mol.GetNumAtoms() == 5


def test_mol_from_pdb_garbage_returns_none():
    assert _mol_from_pdb("NOT A PDB FILE AT ALL\n") is None


# ── 3. GNINA failure reasons surface in stage3 ──────────────────────────────

def test_gnina_failure_reasons_surfaced(monkeypatch):
    """stage3.failure_reasons must record why GNINA re-scoring degraded."""
    import asyncio

    import primerforge.pipelines.consensus_pipeline as cp

    fake_pdb = (
        "ATOM      1  N   MET A   1       0.000   0.000   0.000  1.00 50.00           N\n"
        "ATOM      2  CA  MET A   1       1.458   0.000   0.000  1.00 50.00           C\n"
        "ATOM      3  C   MET A   1       2.009   1.420   0.000  1.00 50.00           C\n"
        "ATOM      4  O   MET A   1       1.251   2.390   0.000  1.00 50.00           O\n"
        "TER\nEND\n"
    )

    async def fake_esmfold(sequence, progress_callback=None):
        return {"status": "success", "tool": "test", "pdb_string": fake_pdb,
                "plddt_score": 88.0, "sequence_length": len(sequence)}

    async def fake_vina(receptor_pdb, ligand_smiles, exhaustiveness=8,
                        receptor_pdbqt_path=None, cpu=None):
        return {"binding_affinity": -7.5, "structure": {"ligand": fake_pdb}}

    async def fake_gnina(receptor_pdb, ligand_smiles, exhaustiveness=4,
                         receptor_pdbqt_path=None):
        raise RuntimeError("Gnina failed: [Errno 8] Exec format error: 'gnina'")

    async def noop_progress(stage, msg, metadata=None):
        return None

    monkeypatch.setattr(cp, "esmfold_predict", fake_esmfold)
    monkeypatch.setattr(cp, "run_vina_docking", fake_vina)
    monkeypatch.setattr(cp, "run_gnina_docking", fake_gnina)
    # receptor PDB→PDBQT conversion: stub the file write
    import primerforge.pipelines.docking_engine as de

    def fake_pdbqt(receptor_pdb, output_path):
        with open(output_path, "w") as f:
            f.write("ATOM      1  C   UNL A   1       0.000   0.000   0.000  0.00  0.00     0.000 C\n")
        return True

    monkeypatch.setattr(de, "pdb_to_pdbqt", fake_pdbqt)

    result = asyncio.run(cp.run_consensus_pipeline(
        "MTYKLIISDDDESLHQLVAGPGNALLPSRFTVTGQ",
        ["CC(=O)Oc1ccccc1C(=O)O"],
        top_n=5,
        progress_callback=noop_progress,
    ))

    assert result["status"] == "success", result.get("message")
    s3 = result["stage3"]
    assert s3["status"] == "gnina_failed", s3
    assert s3["failure_reasons"], "failure_reasons missing"
    assert "Exec format error" in s3["failure_reasons"][0]
    ranked = result["ranked_results"]
    assert ranked[0]["gnina_score"] is None
    assert ranked[0]["status"] == "gnina_failed"
    # consensus falls back to Vina when GNINA is unavailable
    assert ranked[0]["consensus_score"] == pytest.approx(-7.5, abs=0.01)
    assert result["stage1"]["plddt_score"] == 88.0


# ── 4. no-GPU structure prediction guard ─────────────────────────────────
# Production cloud box has NO GPU: the local ESMFold model must never load
# there (8.4GB download + >10GB RAM OOM + 300s job-timeout blowout).
# The web API (remote GPU) is the designed path for GPU-less hosts.

def test_no_gpu_host_uses_web_api_never_local_model(monkeypatch):
    import asyncio

    import primerforge.pipelines.esmfold_engine as ee

    called = {"local": 0, "api": 0}
    monkeypatch.setattr(ee, "_local_gpu_available", lambda: False)

    def _no_local(*_a, **_k):
        called["local"] += 1
        raise AssertionError("local model path must not run without a GPU")

    def _api(seq, report=None):
        called["api"] += 1
        return {"status": "success", "tool": "ESMFold (web API, free)",
                "pdb_string": _PDB_TEMPLATE.format(occ="  1.00", b="  0.41"),
                "plddt_score": 41.0, "sequence_length": len(seq),
                "message": "via web API", "license": "MIT"}

    monkeypatch.setattr(ee, "_run_esmfold_sync", _no_local)
    monkeypatch.setattr(ee, "_fetch_esmfold_api_pdb", _api)

    res = asyncio.run(ee.predict_structure("MTYKLIISDDDESLHQLVAGPGNALLPSRFTVTGQ"))
    assert res["tool"] == "ESMFold (web API, free)"
    assert called == {"local": 0, "api": 1}


def test_no_gpu_api_failure_degrades_to_honest_fallback(monkeypatch):
    import asyncio

    import primerforge.pipelines.esmfold_engine as ee

    monkeypatch.setattr(ee, "_local_gpu_available", lambda: False)
    monkeypatch.setattr(ee, "_fetch_esmfold_api_pdb", lambda seq, report=None: None)

    res = asyncio.run(ee.predict_structure("MTYKLIISDDDESLHQLVAGPGNALLPSRFTVTGQ"))
    assert res["tool"] == "Fallback helical bundle"
    assert res["plddt_score"] == 0          # UI must show the low-confidence warning
    assert "web API" in res["message"] and "no GPU" in res["message"]
    assert "ATOM" in res["pdb_string"]      # dockable coordinates still produced


def test_gpu_host_keeps_local_model_path(monkeypatch):
    import asyncio

    import primerforge.pipelines.esmfold_engine as ee

    monkeypatch.setattr(ee, "_local_gpu_available", lambda: True)

    def _local(sequence, loop, report=None):
        return {"status": "success", "tool": "ESMFold (local, MIT)",
                "pdb_string": "ATOM\n", "plddt_score": 90.0,
                "sequence_length": len(sequence), "message": "local", "license": "MIT"}

    monkeypatch.setattr(ee, "_run_esmfold_sync", _local)
    monkeypatch.setattr(ee, "_fetch_esmfold_api_pdb",
                        lambda seq, report=None: (_ for _ in ()).throw(
                            AssertionError("web API must not be used when a GPU exists")))

    res = asyncio.run(ee.predict_structure("MTYKLIISDDDESLHQLVAGPGNALLPSRFTVTGQ"))
    assert res["tool"] == "ESMFold (local, MIT)"


def test_local_gpu_available_is_false_without_torch():
    import importlib.util

    from primerforge.pipelines.esmfold_engine import _local_gpu_available

    if importlib.util.find_spec("torch") is None:
        assert _local_gpu_available() is False
    else:
        assert isinstance(_local_gpu_available(), bool)


# ── 5. ESMFold web API rate-limit retry ──────────────────────────────────

def _api_response(body):
    class _Resp:
        def read(self):
            return body.encode()

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    return _Resp()


def test_esmfold_api_retries_once_on_429(monkeypatch):
    import urllib.error

    import primerforge.pipelines.esmfold_engine as ee

    assert ee._ESMFOLD_RETRY_DELAY_S == 15  # documented backoff
    monkeypatch.setattr(ee, "_ESMFOLD_RETRY_DELAY_S", 0)  # no real sleep in tests
    calls = {"n": 0}
    good_body = _PDB_TEMPLATE.format(occ="  1.00", b="  0.45") * 60

    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {}, None)
        return _api_response(good_body)

    monkeypatch.setattr(ee.urllib.request, "urlopen", fake_urlopen)
    res = ee._fetch_esmfold_api_pdb("MTYKLIISDDDESLHQLVAGPGNALLPSRFTVTGQ")
    assert calls["n"] == 2, "429 must be retried exactly once"
    assert res is not None and res["tool"] == "ESMFold (web API, free)"
    assert res["plddt_score"] == pytest.approx(45.0, abs=0.5)


def test_esmfold_api_gives_up_after_persistent_429(monkeypatch):
    import urllib.error

    import primerforge.pipelines.esmfold_engine as ee

    monkeypatch.setattr(ee, "_ESMFOLD_RETRY_DELAY_S", 0)
    calls = {"n": 0}

    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {}, None)

    monkeypatch.setattr(ee.urllib.request, "urlopen", fake_urlopen)
    res = ee._fetch_esmfold_api_pdb("MTYKLIISDDDESLHQLVAGPGNALLPSRFTVTGQ")
    assert calls["n"] == 2, "must stop after the single retry"
    assert res is None


def test_esmfold_api_does_not_retry_hard_timeouts(monkeypatch):
    """A slow fold (URLError/timeout, 180s) must NOT retry — 2x180 > 300s budget."""
    import primerforge.pipelines.esmfold_engine as ee

    monkeypatch.setattr(ee, "_ESMFOLD_RETRY_DELAY_S", 0)
    calls = {"n": 0}

    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        raise TimeoutError("socket timed out")

    monkeypatch.setattr(ee.urllib.request, "urlopen", fake_urlopen)
    res = ee._fetch_esmfold_api_pdb("MTYKLIISDDDESLHQLVAGPGNALLPSRFTVTGQ")
    assert calls["n"] == 1
    assert res is None


# ── 6. rate limiting (submit5/min, polling must never throttle) ──────────

@pytest.fixture
def app(monkeypatch, tmp_path):
    from primerforge.primer_server import create_app

    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("PRIMERFORGE_DB", str(tmp_path / "ratelimit.db"))
    import primerforge.security as security

    monkeypatch.setattr(security, "init_admin_rbac", lambda application: None)
    application = create_app()
    return application.wsgi_app if hasattr(application, "wsgi_app") else application


@pytest.fixture
def client(app):
    return app.test_client()


def _reset_limiter(application):
    lim = application.extensions.get("limiter")
    if lim is not None and hasattr(lim, "reset"):
        try:
            lim.reset()
        except Exception:
            pass


def test_consensus_submit_rate_limited(app, client):
    """5/min per IP on POST /docking/consensus: 6th rapid submit → 429.

    Bodies are validation-invalid so no jobs are ever queued; the limiter
    counts requests before the view runs, which is exactly what we assert.
    """
    import json

    _reset_limiter(app)
    hdr = {"Content-Type": "application/json"}
    body = json.dumps({"sequence": "", "ligand_smiles_list": []})
    resp = [client.post("/api/primer/docking/consensus", data=body, headers=hdr)
            for _ in range(6)]
    codes = [r.status_code for r in resp]
    assert codes[:5] == [400, 400, 400, 400, 400], codes
    assert codes[5] == 429, codes
    payload = resp[5].get_json()
    assert payload.get("code") == "RATE_LIMITED", payload


def test_status_polling_is_never_rate_limited(app, client):
    """Frontend polls /status every ~2s for up to 9 min — a 429 here would
    kill in-flight jobs, so the status route must stay outside the tight
    submit limit (only the 200/min global default applies)."""
    _reset_limiter(app)
    codes = [client.get("/api/primer/docking/status/doesnotexist123").status_code
             for _ in range(12)]
    assert 429 not in codes, codes


def test_structure_fetch_is_never_rate_limited(app, client):
    """3D viewer fetches structure/batch right after completion — must not429."""
    _reset_limiter(app)
    codes = [client.get("/api/primer/docking/structure/batch/doesnotexist123").status_code
             for _ in range(12)]
    assert 429 not in codes, codes

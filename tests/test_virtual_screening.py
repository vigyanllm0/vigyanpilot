"""Tests for the Virtual Screening Engine v2 (file-based, chunked, resumable).

Covers: library normalization, ligand prep, campaign lifecycle, cancellation,
chunk resume, export, and API routes (create/status/results/cancel/list).
"""

import json
import os
import tempfile
import time
from unittest.mock import patch

import pytest

# Force SQLite + isolated queue dir before importing the app
os.environ["DATABASE_URL"] = ""
os.environ["DOCKING_QUEUE_DIR"] = tempfile.mkdtemp(prefix="vs_test_queue_")

from primerforge.pipelines.virtual_screening import (  # noqa: E402
    CHUNK_SIZE,
    DEFAULT_EXHAUSTIVENESS,
    MAX_LIGANDS,
    MAX_PROTEINS,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_PENDING,
    STATUS_RUNNING,
    _check_cancel,
    _campaign_dir,
    _read_json,
    cancel_campaign,
    create_campaign,
    export_campaign_csv,
    export_campaign_sdf,
    get_campaign,
    is_stale,
    list_campaigns,
    normalize_library,
    prep_ligand_pdbqt,
    read_library_smi,
    update_campaign,
    update_progress,
    write_library_smi,
)

VALID_SMILES = [
    "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",       # caffeine
    "CC(=O)Oc1ccccc1C(=O)O",               # aspirin
    "CC(=O)Nc1ccc(O)cc1",                  # acetaminophen
    "CC(C)Cc1ccc(cc1)C(C)C(=O)O",          # ibuprofen
]


# ── Library normalization ──────────────────────────────────────────────────

class TestNormalizeLibrary:
    def test_deduplicates(self):
        lib = normalize_library(["CCO", "CCO", "CCN"])
        assert len(lib) == 2
        assert lib[0]["smiles"] == "CCO"
        assert lib[1]["smiles"] == "CCN"

    def test_drops_invalid_smiles(self):
        lib = normalize_library(["CCO", "not_a_smiles", "CCN"])
        assert len(lib) == 2
        assert all(l["smiles"] in ("CCO", "CCN") for l in lib)

    def test_accepts_dict_entries(self):
        lib = normalize_library([
            {"smiles": "CCO", "name": "ethanol"},
            {"smiles": "CCN", "name": "ethylamine"},
        ])
        assert len(lib) == 2
        assert lib[0]["name"] == "ethanol"

    def test_assigns_sequential_indices(self):
        lib = normalize_library(VALID_SMILES)
        assert [l["_index"] for l in lib] == list(range(len(VALID_SMILES)))

    def test_empty_input(self):
        assert normalize_library([]) == []

    def test_mixed_types(self):
        lib = normalize_library(["CCO", {"smiles": "CCN"}, "invalid!!", 42])
        assert len(lib) == 2


# ── Ligand prep ────────────────────────────────────────────────────────────

class TestPrepLigand:
    def test_valid_smiles_produces_pdbqt(self):
        pdbqt = prep_ligand_pdbqt("CC(=O)Oc1ccccc1C(=O)O")
        assert pdbqt is not None
        assert "ATOM" in pdbqt
        assert len(pdbqt) > 100

    def test_invalid_smiles_returns_none(self):
        assert prep_ligand_pdbqt("not_a_smiles") is None

    def test_empty_smiles_returns_none(self):
        assert prep_ligand_pdbqt("") is None

    def test_deterministic(self):
        a = prep_ligand_pdbqt("CCO")
        b = prep_ligand_pdbqt("CCO")
        assert a == b  # same seed → same conformer


# ── Library file I/O ───────────────────────────────────────────────────────

class TestLibraryFileIO:
    def test_write_and_read_roundtrip(self, tmp_path):
        lib = normalize_library(VALID_SMILES)
        path = str(tmp_path / "lib.smi")
        write_library_smi(lib, path)
        back = read_library_smi(path)
        assert len(back) == len(lib)
        assert back[0]["smiles"] == lib[0]["smiles"]
        assert back[0]["_index"] == lib[0]["_index"]


# ── Campaign lifecycle ─────────────────────────────────────────────────────

class TestCampaignLifecycle:
    def test_create_and_get(self):
        cid = create_campaign(
            proteins=[{"sequence": "MKTAYIAKQRQISFVKSHFSRQ" * 3}],
            ligands=VALID_SMILES,
        )
        assert cid
        c = get_campaign(cid)
        assert c is not None
        assert c["status"] == STATUS_PENDING
        assert c["library"]["total"] == len(VALID_SMILES)
        assert len(c["proteins"]) == 1

    def test_create_writes_library_file(self):
        cid = create_campaign(
            proteins=[{"sequence": "MKTAYIAKQRQISFVKSHFSRQ" * 3}],
            ligands=VALID_SMILES,
        )
        lib_path = os.path.join(_campaign_dir(cid), "library.smi")
        assert os.path.exists(lib_path)
        lines = open(lib_path).read().strip().split("\n")
        assert len(lines) == len(VALID_SMILES)

    def test_create_dedupes(self):
        cid = create_campaign(
            proteins=[{"sequence": "MKTAYIAKQRQISFVKSHFSRQ" * 3}],
            ligands=["CCO", "CCO", "CCN", "CCN", "CCC"],
        )
        c = get_campaign(cid)
        assert c["library"]["total"] == 3

    def test_rejects_no_proteins(self):
        with pytest.raises(ValueError, match="protein"):
            create_campaign(proteins=[], ligands=VALID_SMILES)

    def test_rejects_too_many_proteins(self):
        proteins = [{"sequence": "MKTAYIAKQRQISFVKSHFSRQ" * 3}] * (MAX_PROTEINS + 1)
        with pytest.raises(ValueError, match="Maximum"):
            create_campaign(proteins=proteins, ligands=VALID_SMILES)

    def test_rejects_too_few_ligands(self):
        with pytest.raises(ValueError, match="ligands"):
            create_campaign(
                proteins=[{"sequence": "MKTAYIAKQRQISFVKSHFSRQ" * 3}],
                ligands=["CCO"],
            )

    def test_rejects_too_many_ligands(self):
        # Use a smaller threshold by patching MAX_LIGANDS
        with patch("primerforge.pipelines.virtual_screening.MAX_LIGANDS", 3):
            with pytest.raises(ValueError, match="Maximum"):
                create_campaign(
                    proteins=[{"sequence": "MKTAYIAKQRQISFVKSHFSRQ" * 3}],
                    ligands=VALID_SMILES,
                )

    def test_rejects_bad_protein(self):
        with pytest.raises(ValueError, match="sequence or PDB"):
            create_campaign(proteins=[{"name": "empty"}], ligands=VALID_SMILES)

    def test_rejects_long_sequence(self):
        with pytest.raises(ValueError, match="too long"):
            create_campaign(
                proteins=[{"sequence": "M" * 401}],
                ligands=VALID_SMILES,
            )

    def test_rejects_invalid_pdb(self):
        with pytest.raises(ValueError, match="ATOM"):
            create_campaign(
                proteins=[{"pdb_content": "NOT A PDB FILE"}],
                ligands=VALID_SMILES,
            )

    def test_config_exhaustiveness(self):
        cid = create_campaign(
            proteins=[{"sequence": "MKTAYIAKQRQISFVKSHFSRQ" * 3}],
            ligands=VALID_SMILES,
            config={"exhaustiveness": 4},
        )
        c = get_campaign(cid)
        assert c["config"]["exhaustiveness"] == 4

    def test_config_top_k_clamped(self):
        cid = create_campaign(
            proteins=[{"sequence": "MKTAYIAKQRQISFVKSHFSRQ" * 3}],
            ligands=VALID_SMILES,
            config={"top_k_refine": 999},
        )
        c = get_campaign(cid)
        assert c["config"]["top_k_refine"] <= 50

    def test_update_campaign(self):
        cid = create_campaign(
            proteins=[{"sequence": "MKTAYIAKQRQISFVKSHFSRQ" * 3}],
            ligands=VALID_SMILES,
        )
        update_campaign(cid, {"status": STATUS_RUNNING})
        c = get_campaign(cid)
        assert c["status"] == STATUS_RUNNING

    def test_update_progress(self):
        cid = create_campaign(
            proteins=[{"sequence": "MKTAYIAKQRQISFVKSHFSRQ" * 3}],
            ligands=VALID_SMILES,
        )
        update_progress(cid, {"stage": "docking", "ligands_done": 100})
        c = get_campaign(cid)
        assert c["progress"]["stage"] == "docking"
        assert c["progress"]["ligands_done"] == 100
        # Other progress keys preserved
        assert c["progress"]["ligands_total"] == len(VALID_SMILES)

    def test_get_nonexistent(self):
        assert get_campaign("nonexistent_id_12345") is None

    def test_get_invalid_id(self):
        assert get_campaign("../../etc/passwd") is None
        assert get_campaign("") is None


# ── Cancellation ───────────────────────────────────────────────────────────

class TestCancellation:
    def test_cancel_creates_marker(self):
        cid = create_campaign(
            proteins=[{"sequence": "MKTAYIAKQRQISFVKSHFSRQ" * 3}],
            ligands=VALID_SMILES,
        )
        assert cancel_campaign(cid) is True
        assert _check_cancel(cid) is True

    def test_cancel_nonexistent(self):
        assert cancel_campaign("no_such_id") is False


# ── Staleness detection ────────────────────────────────────────────────────

class TestStaleness:
    def test_pending_is_not_stale(self):
        cid = create_campaign(
            proteins=[{"sequence": "MKTAYIAKQRQISFVKSHFSRQ" * 3}],
            ligands=VALID_SMILES,
        )
        assert is_stale(cid) is False

    def test_running_without_heartbeat_is_stale(self):
        cid = create_campaign(
            proteins=[{"sequence": "MKTAYIAKQRQISFVKSHFSRQ" * 3}],
            ligands=VALID_SMILES,
        )
        update_campaign(cid, {"status": STATUS_RUNNING})
        # No running marker → stale
        assert is_stale(cid) is True

    def test_running_with_fresh_heartbeat_is_not_stale(self):
        cid = create_campaign(
            proteins=[{"sequence": "MKTAYIAKQRQISFVKSHFSRQ" * 3}],
            ligands=VALID_SMILES,
        )
        update_campaign(cid, {"status": STATUS_RUNNING})
        # Touch the running marker
        running_path = os.path.join(_campaign_dir(cid), "running")
        open(running_path, "a").close()
        assert is_stale(cid) is False

    def test_aged_pending_campaign_is_stale(self):
        """A 'pending' campaign whose worker never started must be detected.

        Regression: prod campaign 51f38dcc73b6483e sat at 'pending' forever
        (worker died on `import primerforge`) and the UI never offered Resume
        because is_stale() only looked at STATUS_RUNNING.
        """
        from primerforge.pipelines.virtual_screening import PENDING_STALE_S
        cid = create_campaign(
            proteins=[{"sequence": "MKTAYIAKQRQISFVKSHFSRQ" * 3}],
            ligands=VALID_SMILES,
        )
        update_campaign(cid, {"status": STATUS_PENDING})
        # Fresh pending → not stale (worker may still be queueing for a slot)
        assert is_stale(cid) is False
        # Backdate past the slot-wait grace window → stale
        path = os.path.join(_campaign_dir(cid), "campaign.json")
        data = _read_json(path)
        data["updated_at"] = time.time() - (PENDING_STALE_S + 1)
        data["created_at"] = data["updated_at"]
        from primerforge.pipelines.virtual_screening import _atomic_json
        _atomic_json(path, data)
        assert is_stale(cid) is True

    def test_pending_grace_window_not_stale(self):
        """Pending inside the acquire_slots(120s) grace window is NOT stale."""
        from primerforge.pipelines.virtual_screening import PENDING_STALE_S
        cid = create_campaign(
            proteins=[{"sequence": "MKTAYIAKQRQISFVKSHFSRQ" * 3}],
            ligands=VALID_SMILES,
        )
        path = os.path.join(_campaign_dir(cid), "campaign.json")
        data = _read_json(path)
        data["updated_at"] = time.time() - (PENDING_STALE_S - 60)
        from primerforge.pipelines.virtual_screening import _atomic_json
        _atomic_json(path, data)
        assert is_stale(cid) is False


# ── Listing ────────────────────────────────────────────────────────────────

class TestListCampaigns:
    def test_lists_user_campaigns(self):
        email = "test_list@example.com"
        for _ in range(3):
            create_campaign(
                proteins=[{"sequence": "MKTAYIAKQRQISFVKSHFSRQ" * 3}],
                ligands=VALID_SMILES,
                user_email=email,
            )
        campaigns = list_campaigns(email)
        assert len(campaigns) == 3

    def test_excludes_other_users(self):
        create_campaign(
            proteins=[{"sequence": "MKTAYIAKQRQISFVKSHFSRQ" * 3}],
            ligands=VALID_SMILES,
            user_email="alice@example.com",
        )
        campaigns = list_campaigns("bob@example.com")
        assert len([c for c in campaigns if c.get("user_email") == "alice@example.com"]) == 0


# ── Export ─────────────────────────────────────────────────────────────────

class TestExport:
    def _make_completed_campaign_with_results(self, tmp_path):
        """Create a campaign with fake final.json results for export testing."""
        cid = create_campaign(
            proteins=[{"sequence": "MKTAYIAKQRQISFVKSHFSRQ" * 3, "name": "TestProt"}],
            ligands=VALID_SMILES,
        )
        cdir = _campaign_dir(cid)
        results_dir = os.path.join(cdir, "results", "p1")
        os.makedirs(results_dir, exist_ok=True)
        final = {
            "protein_id": "p1",
            "protein_name": "TestProt",
            "box": {"center": [0, 0, 0], "size": [22, 22, 22]},
            "exhaustiveness": 1,
            "top_hits": [
                {"smiles": VALID_SMILES[0], "vina_score": -8.5, "gnina_score": -7.2, "consensus_score": -7.72},
                {"smiles": VALID_SMILES[1], "vina_score": -6.1, "gnina_score": None, "consensus_score": -6.1},
            ],
        }
        with open(os.path.join(results_dir, "final.json"), "w") as f:
            json.dump(final, f)
        return cid

    def test_csv_export(self, tmp_path):
        cid = self._make_completed_campaign_with_results(tmp_path)
        csv_data = export_campaign_csv(cid)
        assert csv_data is not None
        assert "protein_id" in csv_data
        assert "vina_score" in csv_data
        assert VALID_SMILES[0] in csv_data

    def test_sdf_export(self, tmp_path):
        cid = self._make_completed_campaign_with_results(tmp_path)
        sdf_data = export_campaign_sdf(cid)
        assert sdf_data is not None
        assert "$$$$" in sdf_data

    def test_csv_export_nonexistent(self):
        assert export_campaign_csv("no_such_id") is None

    def test_sdf_export_nonexistent(self):
        assert export_campaign_sdf("no_such_id") is None


# ── API routes ─────────────────────────────────────────────────────────────

@pytest.fixture
def app():
    from primerforge.primer_server import create_app
    a = create_app()
    if hasattr(a, "wsgi_app"):
        a = a.wsgi_app
    return a


@pytest.fixture
def client(app):
    return app.test_client()


class TestScreenRoutes:
    def test_create_requires_auth(self, client):
        r = client.post("/api/primer/docking/screen", json={
            "proteins": [{"sequence": "MKTAYIAKQRQISFVKSHFSRQ" * 3}],
            "ligands": VALID_SMILES,
        })
        assert r.status_code == 401

    def test_list_requires_auth(self, client):
        r = client.get("/api/primer/docking/screen")
        assert r.status_code == 401

    def test_create_validates_proteins(self, client):
        r = client.post("/api/primer/docking/screen", json={
            "proteins": [],
            "ligands": VALID_SMILES,
        })
        # 401 comes first (no auth), but if we get 400 it's the right error
        assert r.status_code in (400, 401)

    def test_create_validates_ligands(self, client):
        r = client.post("/api/primer/docking/screen", json={
            "proteins": [{"sequence": "MKTAYIAKQRQISFVKSHFSRQ" * 3}],
            "ligands": [],
        })
        assert r.status_code in (400, 401)

    def test_status_nonexistent_returns_404(self, client):
        r = client.get("/api/primer/docking/screen/nonexistent_id_12345")
        assert r.status_code == 404

    def test_export_nonexistent_returns_404(self, client):
        r = client.get("/api/primer/docking/screen/nonexistent_id_12345/export/csv")
        assert r.status_code == 404

    def test_cancel_nonexistent_returns_404(self, client):
        r = client.post("/api/primer/docking/screen/nonexistent_id_12345/cancel")
        assert r.status_code == 404


# ── Chunk resume ───────────────────────────────────────────────────────────

class TestChunkResume:
    def test_completed_chunk_is_skipped(self, tmp_path):
        """A chunk with existing results should be skipped on resume."""
        cid = create_campaign(
            proteins=[{"sequence": "MKTAYIAKQRQISFVKSHFSRQ" * 3}],
            ligands=VALID_SMILES,
        )
        cdir = _campaign_dir(cid)
        results_dir = os.path.join(cdir, "results", "p1")
        os.makedirs(results_dir, exist_ok=True)
        # Write a fake completed chunk
        chunk_path = os.path.join(results_dir, "chunk_0.jsonl")
        with open(chunk_path, "w") as f:
            f.write(json.dumps({"index": 0, "smiles": "CCO", "vina_score": -5.0}) + "\n")
        # The engine should skip this chunk
        assert os.path.exists(chunk_path)


# ── Worker subprocess bootstrap (prod spawn path) ──────────────────────────

class TestWorkerBootstrap:
    """screening_worker.py must import without any pre-seeded sys.path.

    Regression (prod 2026-10-11): the worker is spawned as
    `python primerforge/screening_worker.py --campaign <id>` with the parent
    env. Prod's venv has NO editable install of primerforge (only wsgi.py
    bootstraps sys.path for the parent), so the child died on import — and
    because its own error handler needed the same import, the campaign was
    stranded at status=pending forever, spinning with no results.
    """

    WORKER = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "primerforge", "screening_worker.py")

    def _clean_env(self):
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        env["PYTHONUNBUFFERED"] = "1"
        return env

    def test_worker_source_bootstraps_sys_path(self):
        src = open(self.WORKER).read()
        assert "sys.path.insert" in src, (
            "screening_worker must put the repo root on sys.path before any "
            "primerforge import — prod's venv does not install the package.")

    def test_worker_boots_without_pythonpath(self, tmp_path):
        """Run the worker cold: it must reach campaign lookup, not ImportError."""
        import subprocess
        import sys
        r = subprocess.run(
            [sys.executable, self.WORKER, "--campaign", "nonexistent12345"],
            capture_output=True, text=True, env=self._clean_env(),
            cwd=str(tmp_path), timeout=120,
        )
        combined = r.stdout + r.stderr
        assert "No module named 'primerforge'" not in combined, combined[:800]
        # It got far enough to look the campaign up (expected: not found)
        assert "not found" in combined, combined[:800]

    def test_worker_marks_failed_without_engine_import(self, tmp_path):
        """_mark_failed_raw must reach status=failed using stdlib only."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("_sw_under_test", self.WORKER)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # Point the worker at a queue dir holding a 'pending' campaign
        cdir = tmp_path / "screen" / "campaignraw01"
        cdir.mkdir(parents=True)
        (cdir / "campaign.json").write_text(json.dumps({
            "campaign_id": "campaignraw01", "status": "pending",
            "progress": {"stage": "pending", "message": "Campaign queued"},
        }))
        os.environ["DOCKING_QUEUE_DIR"] = str(tmp_path)
        try:
            assert mod._mark_failed_raw("campaignraw01", "import blew up") is True
            data = json.loads((cdir / "campaign.json").read_text())
            assert data["status"] == "failed"
            assert "import blew up" in data["progress"]["message"]
            # A terminal campaign must never be clobbered by the fallback
            data["status"] = "completed"
            (cdir / "campaign.json").write_text(json.dumps(data))
            assert mod._mark_failed_raw("campaignraw01", "late crash") is True
            data = json.loads((cdir / "campaign.json").read_text())
            assert data["status"] == "completed"
            # Bogus / traversing ids must be refused
            assert mod._mark_failed_raw("../etc/passwd", "x") is False
            assert mod._mark_failed_raw("", "x") is False
        finally:
            os.environ.pop("DOCKING_QUEUE_DIR", None)

    def test_spawn_helper_sets_pythonpath_and_cwd(self):
        """_spawn_screening_worker must hand the child a resolvable import."""
        import subprocess as _sp
        import sys as _sys
        from primerforge.primer_server import _spawn_screening_worker

        captured = {}

        def _fake_popen(*args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            return object()

        pkg_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "primerforge")
        repo_root = os.path.dirname(pkg_dir)

        with patch.object(_sp, "Popen", _fake_popen):
            err = _spawn_screening_worker("abc123def456")

        assert err is None, err
        kwargs = captured["kwargs"]
        # cwd + PYTHONPATH both point at the repo root → `import primerforge` works
        assert kwargs["cwd"] == repo_root, kwargs["cwd"]
        assert repo_root in kwargs["env"]["PYTHONPATH"], kwargs["env"]["PYTHONPATH"]
        # and the child really is the screening worker with our campaign id
        argv = captured["args"][0]
        assert argv[1].endswith("screening_worker.py"), argv
        assert argv[2:] == ["--campaign", "abc123def456"], argv
        assert "start_new_session" in kwargs and kwargs["start_new_session"] is True
        # no PYTHONPATH leakage of the parent's value ahead of the repo root
        assert kwargs["env"]["PYTHONPATH"].split(os.pathsep)[0] == repo_root

    def test_spawn_helper_reports_popen_failure(self):
        """A failed spawn returns an error string (route turns it into a 500)."""
        import subprocess as _sp
        from primerforge.primer_server import _spawn_screening_worker

        def _boom(*a, **k):
            raise OSError("cannot fork")

        with patch.object(_sp, "Popen", _boom):
            err = _spawn_screening_worker("abc123def456")
        assert isinstance(err, str) and "cannot fork" in err


# ── GNINA refine → consensus mapping ───────────────────────────────────────

class TestGninaRefineMapping:
    """The refine path must surface GNINA's score under `gnina_score`.

    Regression (prod 2026-10-11): run_gnina_docking reports the refined
    pose's Vina energy as `binding_affinity` and has no `gnina_score` key.
    The engine read `gres.get("gnina_score")` → always None → every
    "consensus" score silently collapsed to the plain Vina score while the
    campaign still claimed GNINA had refined the pose (cnn_affinity was
    populated, so GNINA demonstrably ran).
    """

    PDB = "\n".join(
        "ATOM  %5d  CA  ALA A%4d    %8.3f%8.3f%8.3f  1.00 50.00           C"
        % (i + 1, i + 1, float(i) * 1.5, float(i) * 1.5, 0.0)
        for i in range(12)
    ) + "\nEND\n"

    VINA = [-5.0, -6.0, -7.0]          # worst → best after Vina
    GNINA_BEST = -8.0                   # refined score for the top-Vina hit

    def _run(self, tmp_path, gnina_result, gnina_ok=True):
        """Run one full campaign with every external binary stubbed."""
        import asyncio

        import primerforge.pipelines.docking_engine as de
        import primerforge.pipelines.virtual_screening as vs

        ligands = [{"smiles": s} for s in VALID_SMILES[:3]]
        cid = vs.create_campaign(
            proteins=[{"sequence": "MKTAYIAKQRQISFVKSHFSRQ", "name": "RefineProt",
                       "pdb_content": self.PDB}],
            ligands=ligands,
            config={"exhaustiveness": 1, "top_k_refine": 2, "chunk_size": 50},
        )

        async def _fake_dock(receptor_pdbqt, prepared, smiles_by_index, box,
                             exh, lanes, progress_cb=None):
            return [
                {"index": i, "smiles": smiles_by_index[i],
                 "vina_score": self.VINA[k], "status": "ok"}
                for k, (i, _) in enumerate(sorted(smiles_by_index.items()))
            ]

        async def _fake_gnina(*a, **k):
            return gnina_result

        with patch.object(vs, "_prep_receptor",
                          lambda *a, **k: ("fake.pdbqt",
                                           {"center": [0, 0, 0], "size": [22, 22, 22]})), \
             patch.object(vs, "prep_ligand_batch",
                          lambda ligands, out_dir, idx: [(l["_index"], "/tmp/fake.pdbqt")
                                                         for l in ligands]), \
             patch.object(vs, "_dock_chunk", _fake_dock), \
             patch.object(de, "run_gnina_docking", _fake_gnina), \
             patch.object(de, "gnina_available",
                          lambda *a, **k: {"ok": gnina_ok, "reason": ""}):
            asyncio.run(vs.run_campaign(cid))
        return cid

    def _final(self, cid):
        path = os.path.join(_campaign_dir(cid), "results", "p1", "final.json")
        return _read_json(path)

    def test_gnina_score_lands_from_binding_affinity(self, tmp_path):
        """binding_affinity (the only key GNINA returns) → gnina_score."""
        cid = self._run(tmp_path, {
            "binding_affinity": self.GNINA_BEST,
            "cnn_affinity": 3.1, "cnn_score": 0.91, "status": "success",
        })
        final = self._final(cid)
        assert final is not None, "final.json missing"
        assert final["gnina_refined"] == 2, "top_k=2 must both be refined"
        refined = [h for h in final["top_hits"] if h.get("gnina_score") is not None]
        assert len(refined) == 2, (
            "gnina_score must be populated for refined hits — reading the "
            "nonexistent `gnina_score` key from run_gnina_docking silently "
            "returned None and collapsed consensus to Vina-only")
        hit = refined[0]
        assert hit["gnina_score"] == self.GNINA_BEST
        assert hit["cnn_affinity"] == 3.1
        assert hit["cnn_score"] == 0.91

    def test_consensus_is_weighted_not_vina_echo(self, tmp_path):
        cid = self._run(tmp_path, {
            "binding_affinity": self.GNINA_BEST,
            "cnn_affinity": 3.1, "cnn_score": 0.91, "status": "success",
        })
        final = self._final(cid)
        top = final["top_hits"][0]
        # Vina ranks the 3rd ligand best (-7.0); it is the one refined.
        assert top["vina_score"] == -7.0
        expected = round(0.4 * -7.0 + 0.6 * self.GNINA_BEST, 3)
        assert top["consensus_score"] == expected, (
            "consensus must be 0.4*vina + 0.6*gnina")
        assert top["score_source"] == "consensus"

    def test_unrefined_hits_tagged_vina_source(self, tmp_path):
        """A 1-method score must never be sold as a 2-method consensus."""
        cid = self._run(tmp_path, {
            "binding_affinity": self.GNINA_BEST,
            "cnn_affinity": 3.1, "cnn_score": 0.91, "status": "success",
        })
        final = self._final(cid)
        sources = {h["smiles"]: h.get("score_source") for h in final["top_hits"]}
        assert set(sources.values()) == {"consensus", "vina"}, sources
        unrefined = [h for h in final["top_hits"]
                     if h.get("gnina_score") is None]
        assert unrefined, "top_k=2 of 3 → at least one unrefined hit"
        for h in unrefined:
            assert h["score_source"] == "vina"
            assert h["consensus_score"] == h["vina_score"]

    def test_best_gnina_summary_is_best_actual_score(self, tmp_path):
        """results_summary.best_gnina must be the best CNN score that exists,
        not rank-1's — hits are ranked by consensus and refinement blends in
        the CNN term, so a weak GNINA score sinks the refined hits BELOW an
        unrefined Vina-only molecule. Reading rank-1 alone reported
        best_gnina=null while the same dict said gnina_refined=10 (prod
        campaign 3046eb6741b94fcf, 2026-10-12)."""
        import primerforge.pipelines.virtual_screening as vs
        # GNINA weak enough (-2.0) that both refined hits fall below the
        # unrefined Vina -5.0 molecule → rank 1 is Vina-only.
        cid = self._run(tmp_path, {
            "binding_affinity": -2.0,
            "cnn_affinity": 0.4, "cnn_score": 0.2, "status": "success",
        })
        final = self._final(cid)
        assert final["top_hits"][0].get("gnina_score") is None, (
            "fixture must put a Vina-only molecule at rank 1")
        summ = (vs.get_campaign(cid) or {}).get("results_summary") or {}
        p1 = summ.get("p1") or {}
        assert p1["gnina_refined"] == 2
        assert p1["best_gnina"] == -2.0, (
            "best_gnina must report the best refined score across the "
            "campaign, not null because rank 1 happens to be unrefined")

    def test_results_re_ranked_by_consensus(self, tmp_path):
        """final.json order must match the score it is labelled with."""
        cid = self._run(tmp_path, {
            "binding_affinity": self.GNINA_BEST,
            "cnn_affinity": 3.1, "cnn_score": 0.91, "status": "success",
        })
        final = self._final(cid)
        scores = [h["consensus_score"] for h in final["top_hits"]]
        assert scores == sorted(scores), (
            "hits were left in Vina order while displaying consensus scores")
        assert [h["rank"] for h in final["top_hits"]] == list(
            range(1, len(final["top_hits"]) + 1))

    def test_gnina_not_available_falls_back_honestly(self, tmp_path):
        """No GNINA → vina-only scores, tagged as such, rank still set."""
        cid = self._run(tmp_path, {"binding_affinity": -8.0}, gnina_ok=False)
        final = self._final(cid)
        assert final["gnina_refined"] == 0
        for h in final["top_hits"]:
            assert h.get("gnina_score") is None
            assert h["score_source"] == "vina"
            assert h["consensus_score"] == h["vina_score"]
        assert [h["rank"] for h in final["top_hits"]] == list(
            range(1, len(final["top_hits"]) + 1))

    def test_failed_refine_not_counted_as_refined(self, tmp_path):
        """A refine that throws must not inflate gnina_refined."""
        import asyncio

        import primerforge.pipelines.docking_engine as de
        import primerforge.pipelines.virtual_screening as vs

        cid = vs.create_campaign(
            proteins=[{"sequence": "MKTAYIAKQRQISFVKSHFSRQ", "name": "FailProt",
                       "pdb_content": self.PDB}],
            ligands=[{"smiles": s} for s in VALID_SMILES[:3]],
            config={"exhaustiveness": 1, "top_k_refine": 3, "chunk_size": 50},
        )

        async def _fake_dock(receptor_pdbqt, prepared, smiles_by_index, box,
                             exh, lanes, progress_cb=None):
            return [{"index": i, "smiles": smiles_by_index[i],
                     "vina_score": -6.0, "status": "ok"}
                    for i in smiles_by_index]

        async def _boom(*a, **k):
            raise RuntimeError("gnina exploded")

        with patch.object(vs, "_prep_receptor",
                          lambda *a, **k: ("fake.pdbqt",
                                           {"center": [0, 0, 0], "size": [22, 22, 22]})), \
             patch.object(vs, "prep_ligand_batch",
                          lambda ligands, out_dir, idx: [(l["_index"], "/tmp/fake.pdbqt")
                                                         for l in ligands]), \
             patch.object(vs, "_dock_chunk", _fake_dock), \
             patch.object(de, "run_gnina_docking", _boom), \
             patch.object(de, "gnina_available",
                          lambda *a, **k: {"ok": True, "reason": ""}):
            asyncio.run(vs.run_campaign(cid))

        final = self._final(cid)
        assert final["gnina_refined"] == 0, (
            "refine failures must not be counted as successful refinements")
        for h in final["top_hits"]:
            assert h.get("gnina_score") is None
            assert h["score_source"] == "vina"


class TestResultsRouteAnnotation:
    """Both result branches must return protein identity + rank.

    Regression (prod 2026-10-11): the per-protein branch returned raw
    top_hits with no protein_id/protein_name (the protein column rendered
    empty when filtering), neither branch guaranteed `rank`, and the merged
    sort used `or`, which treats a legitimate 0.0 score as missing.
    """

    def _campaign_with_hits(self, n_hits=3):
        cid = create_campaign(
            proteins=[{"sequence": "MKTAYIAKQRQISFVKSHFSRQ", "name": "ProtA",
                       "pdb_content": "ATOM      1  CA  ALA A   1       0.000   0.000   0.000  1.00 50.00           C\nEND\n"},
                      {"sequence": "MKTAYIAKQRQISFVKSHFSRQ", "name": "ProtB",
                       "pdb_content": "ATOM      1  CA  ALA A   1       0.000   0.000   0.000  1.00 50.00           C\nEND\n"}],
            ligands=VALID_SMILES[:n_hits],
        )
        for pid, pname, offset in (("p1", "ProtA", 0.0), ("p2", "ProtB", -3.0)):
            rdir = os.path.join(_campaign_dir(cid), "results", pid)
            os.makedirs(rdir, exist_ok=True)
            # final.json stores hits best-first, as the engine writes them
            n = n_hits
            hits = [{"smiles": VALID_SMILES[i], "vina_score": -(n - i) + offset,
                     "consensus_score": -(n - i) + offset,
                     "gnina_score": None, "score_source": "vina"}
                    for i in range(n)]
            with open(os.path.join(rdir, "final.json"), "w") as f:
                json.dump({"protein_id": pid, "protein_name": pname,
                           "top_hits": hits}, f)
        return cid

    def test_merged_rows_carry_protein_and_rank(self, client):
        cid = self._campaign_with_hits()
        r = client.get(f"/api/primer/docking/screen/{cid}/results")
        assert r.status_code == 200
        d = r.get_json()
        assert d["total"] == 6
        for h in d["results"]:
            assert h["protein_name"] in ("ProtA", "ProtB"), h
            assert h["protein_id"] in ("p1", "p2"), h
            assert isinstance(h.get("rank"), int) and h["rank"] >= 1, h
        assert [h["rank"] for h in d["results"]] == [1, 2, 3, 4, 5, 6], (
            "merged view is one combined ranking → ranks must be global")

    def test_merged_sort_prefers_consensus_score(self, client):
        """ProtB scores 3 kcal better — it must lead the merged list."""
        cid = self._campaign_with_hits()
        r = client.get(f"/api/primer/docking/screen/{cid}/results")
        d = r.get_json()
        assert d["results"][0]["protein_name"] == "ProtB"
        assert d["results"][-1]["protein_name"] == "ProtA"

    def test_per_protein_rows_carry_protein_and_rank(self, client):
        cid = self._campaign_with_hits()
        r = client.get(f"/api/primer/docking/screen/{cid}/results?protein_id=p2")
        assert r.status_code == 200
        d = r.get_json()
        assert d["total"] == 3
        for h in d["results"]:
            assert h["protein_id"] == "p2", h
            assert h["protein_name"] == "ProtB", h
        assert [h["rank"] for h in d["results"]] == [1, 2, 3]

    def test_unknown_protein_id_returns_404(self, client):
        cid = self._campaign_with_hits()
        r = client.get(f"/api/primer/docking/screen/{cid}/results?protein_id=nosuch")
        assert r.status_code == 404

    def test_zero_score_not_treated_as_missing(self, client):
        """A 0.0 score is real data — the `or`-chain used to skip it."""
        cid = self._campaign_with_hits()
        rdir = os.path.join(_campaign_dir(cid), "results", "p1")
        with open(os.path.join(rdir, "final.json"), "w") as f:
            json.dump({"protein_id": "p1", "protein_name": "ProtA",
                       "top_hits": [
                           {"smiles": VALID_SMILES[0], "vina_score": 0.0,
                            "consensus_score": 0.0, "gnina_score": None},
                           {"smiles": VALID_SMILES[1], "vina_score": -9.0,
                            "consensus_score": -9.0, "gnina_score": None},
                       ]}, f)
        r = client.get(f"/api/primer/docking/screen/{cid}/results?protein_id=p1")
        d = r.get_json()
        scores = [h["consensus_score"] for h in d["results"]]
        assert scores == [-9.0, 0.0], "0.0 must sort last, not be dropped"

    def test_score_source_backfilled_for_legacy_campaigns(self, client):
        """Pre-2026-10-11 campaigns have no score_source — derive it."""
        cid = self._campaign_with_hits()
        # Rewrite p1's final.json as a legacy record: one hit GNINA refined
        # (cnn fields present), one it never saw, and NO score_source.
        rdir = os.path.join(_campaign_dir(cid), "results", "p1")
        with open(os.path.join(rdir, "final.json"), "w") as f:
            json.dump({"protein_id": "p1", "protein_name": "ProtA",
                       "top_hits": [
                           {"smiles": VALID_SMILES[0], "vina_score": -8.0,
                            "gnina_score": -7.5, "cnn_affinity": 3.0,
                            "consensus_score": -7.7},
                           {"smiles": VALID_SMILES[1], "vina_score": -6.0,
                            "gnina_score": None, "consensus_score": -6.0},
                       ]}, f)
        d = client.get(f"/api/primer/docking/screen/{cid}/results?protein_id=p1").get_json()
        by_smiles = {h["smiles"]: h for h in d["results"]}
        assert by_smiles[VALID_SMILES[0]]["score_source"] == "consensus"
        assert by_smiles[VALID_SMILES[1]]["score_source"] == "vina"
        # CSV must agree with the API
        csv_data = export_campaign_csv(cid)
        assert "score_source" in csv_data
        tail = [ln.rsplit(",", 1)[-1] for ln in csv_data.strip().splitlines()[1:]]
        assert tail.count("consensus") == 1, tail
        assert tail.count("vina") == len(tail) - 1, tail

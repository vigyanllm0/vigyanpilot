"""Tests for redocking-RMSD site validation (primerforge.pipelines.redock_validate).

Covers the pure helpers (bound-ligand extraction, pose parsing, in-frame
RMSD semantics), the never-raise contract of validate_redocking_sync, and
the /api/primer/docking/redock-validate route (400s + mocked success /
unavailable paths).  The real Vina redock is verified separately as an E2E
(1HSG: RMSD 4.23 A, score -10.038) — not run in the unit suite.
"""

import json
from pathlib import Path

import pytest

from primerforge.pipelines import redock_validate as rv

# 1HSG: HIV-1 protease with co-crystal ligand MK1 (chain B, resnum 902).
FIX = Path(__file__).parent / "fixtures" / "docking"
PDB_1HSG = str(FIX / "1hsg_complex.pdb")


def _load_1hsg() -> str:
    with open(PDB_1HSG, encoding="utf-8") as fh:
        return fh.read()


# ── find_bound_ligand ──────────────────────────────────────────────────────

class TestFindBoundLigand:
    def test_finds_mk1_as_largest_group(self):
        lig = rv.find_bound_ligand(_load_1hsg())
        assert lig is not None
        assert lig["resname"] == "MK1"
        assert lig["chain"] == "B"
        assert lig["resnum"] == 902
        assert lig["heavy_atoms"] == 45

    def test_block_is_hetatm_plus_self_contained_conect_only(self):
        lig = rv.find_bound_ligand(_load_1hsg())
        lines = lig["block"].strip().split("\n")
        assert all(l.startswith(("HETATM", "CONECT")) for l in lines)
        serials = {int(l[6:11]) for l in lines if l.startswith("HETATM")}
        for line in (l for l in lines if l.startswith("CONECT")):
            fields = [line[s:s + 5].strip() for s in (6, 11, 16, 21, 26)]
            referenced = {int(f) for f in fields if f}
            assert referenced <= serials, "CONECT must stay inside the ligand"

    def test_water_never_selected(self):
        assert rv.find_bound_ligand(_load_1hsg(), resname="HOH") is None

    def test_unknown_resname_returns_none(self):
        assert rv.find_bound_ligand(_load_1hsg(), resname="XYZ") is None

    def test_chain_filter(self):
        assert rv.find_bound_ligand(_load_1hsg(), chain="A") is None
        lig = rv.find_bound_ligand(_load_1hsg(), chain="B")
        assert lig and lig["resname"] == "MK1"

    def test_no_ligand_structure_returns_none(self):
        pdb = ("ATOM      1  N   ALA A   1       0.000   0.000   0.000"
               "  1.00  0.00           N\nEND\n")
        assert rv.find_bound_ligand(pdb) is None


# ── molecule helpers ───────────────────────────────────────────────────────

@pytest.mark.skipif(rv.pybel is None, reason="openbabel/pybel unavailable")
class TestMoleculeHelpers:
    @pytest.fixture()
    def lig_block(self) -> str:
        return rv.find_bound_ligand(_load_1hsg())["block"]

    def test_perceive_smiles(self, lig_block):
        smi = rv.perceive_smiles(lig_block)
        assert smi and len(smi) > 20

    def test_experimental_pose_mol(self, lig_block):
        mol = rv.experimental_pose_mol(lig_block)
        assert mol is not None
        assert mol.GetNumAtoms() == 45  # heavy atoms (removeHs=True)

    def test_parse_pose_mol_sdf(self, lig_block):
        from openbabel import pybel
        sdf = pybel.readstring("pdb", lig_block).write("sdf")
        mol = rv.parse_pose_mol(sdf)
        assert mol is not None and mol.GetNumAtoms() == 45

    def test_parse_pose_mol_pdb_text(self, lig_block):
        mol = rv.parse_pose_mol(lig_block)
        assert mol is not None and mol.GetNumAtoms() == 45

    def test_parse_pose_mol_garbage(self):
        assert rv.parse_pose_mol("") is None
        assert rv.parse_pose_mol("not a molecule") is None


@pytest.mark.skipif(rv.Chem is None, reason="rdkit unavailable")
class TestPoseRmsd:
    @pytest.fixture()
    def poses(self):
        lig = rv.find_bound_ligand(_load_1hsg())
        exp = rv.experimental_pose_mol(lig["block"])
        return exp

    def test_self_is_zero(self, poses):
        from rdkit import Chem
        assert rv.pose_rmsd(Chem.Mol(poses), poses) == {"rmsd": 0.0}

    def test_in_place_not_aligned(self, poses):
        """A pose translated 5 A must report ~5 A (no superposition).

        CalcRMS is the in-place variant — GetBestRMS (ligand-aligned) would
        return ~0 for any pose and prove nothing.  Verified empirically:
        5.0 vs 0.0 on the translated control.
        """
        from rdkit import Chem
        conf0 = poses.GetConformer()
        conf2 = Chem.Conformer(poses.GetNumAtoms())
        moved = Chem.Mol(poses)
        for i in range(poses.GetNumAtoms()):
            p = conf0.GetAtomPosition(i)
            conf2.SetAtomPosition(i, (p.x + 5.0, p.y, p.z))
        moved.RemoveAllConformers()
        moved.AddConformer(conf2)
        res = rv.pose_rmsd(moved, poses)
        assert "rmsd" in res
        assert res["rmsd"] == pytest.approx(5.0, abs=0.05)

    def test_atom_order_shuffled_returns_identical_value(self, poses):
        import random
        from rdkit import Chem
        rng = random.Random(1)
        order = list(range(poses.GetNumAtoms()))
        rng.shuffle(order)
        shuffled = Chem.RenumberAtoms(poses, order)
        assert rv.pose_rmsd(shuffled, poses) == rv.pose_rmsd(
            Chem.Mol(poses), poses)

    def test_atom_count_mismatch_is_honest_reason(self, poses):
        from rdkit import Chem
        small = Chem.MolFromSmiles("CCO")
        res = rv.pose_rmsd(small, poses)
        assert "rmsd" not in res
        assert "heavy atoms" in res["reason"]

    def test_unparseable_molecule_reason(self, poses):
        res = rv.pose_rmsd(None, poses)
        assert "rmsd" not in res
        assert "could not be parsed" in res["reason"]


# ── validate_redocking_sync — never-raise contract ─────────────────────────

class TestValidateRedockingSync:
    def test_no_bound_ligand_unavailable(self):
        pdb = ("ATOM      1  N   ALA A   1       0.000   0.000   0.000"
               "  1.00  0.00           N\nEND\n")
        res = rv.validate_redocking_sync(pdb)
        assert res["available"] is False
        assert "bound ligand" in res["reason"]

    def test_water_selection_unavailable(self):
        res = rv.validate_redocking_sync(_load_1hsg(), resname="HOH")
        assert res["available"] is False
        assert "co-crystal ligand" in res["reason"]

    def test_short_garbage_never_raises(self):
        res = rv.validate_redocking_sync("ATOM  broken")
        assert res["available"] is False

    @pytest.mark.skipif(rv.pybel is None or rv.Chem is None,
                        reason="openbabel/rdkit unavailable")
    @pytest.mark.slow
    def test_exhaustiveness_clamped(self, monkeypatch):
        """exhaustiveness is clamped into [1, 32]; no Vina actually runs."""
        captured = {}

        async def fake_vina(receptor, smiles, exhaustiveness=8, box=None):
            captured["exh"] = exhaustiveness
            raise RuntimeError("vina not run in tests")

        monkeypatch.setattr(rv, "run_vina_docking", fake_vina, raising=False)
        res = rv.validate_redocking_sync(_load_1hsg(), resname="MK1",
                                         exhaustiveness=999)
        assert captured["exh"] == rv.MAX_EXHAUSTIVENESS
        assert res["available"] is False  # fake vina raised -> unavailable

    @pytest.mark.skipif(rv.pybel is None or rv.Chem is None,
                        reason="openbabel/rdkit unavailable")
    def test_vina_failure_is_unavailable_not_raise(self, monkeypatch):
        async def boom(*a, **kw):
            raise Exception("Vina failed with code 1: bad receptor")
        monkeypatch.setattr(rv, "run_vina_docking", boom, raising=False)
        res = rv.validate_redocking_sync(_load_1hsg(), resname="MK1")
        assert res["available"] is False
        assert "Vina failed" in res["reason"]


# ── route /api/primer/docking/redock-validate ──────────────────────────────

class TestRedockRoute:
    URL = "/api/primer/docking/redock-validate"

    @pytest.fixture()
    def client(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "")
        from primerforge.primer_server import create_app
        application = create_app()
        app = application.wsgi_app if hasattr(application, "wsgi_app") else application
        app.config["TESTING"] = True
        return app.test_client()

    def test_missing_content_400(self, client):
        r = client.post(self.URL, json={})
        assert r.status_code == 400
        assert "No PDB content" in r.get_json()["error"]

    def test_short_content_400(self, client):
        r = client.post(self.URL, json={"pdb_content": "ATOM  short"})
        assert r.status_code == 400

    def test_no_bound_ligand_400(self, client):
        pdb = ("ATOM      1  N   ALA A   1       0.000   0.000   0.000"
               "  1.00  0.00           N\nEND\n")
        r = client.post(self.URL, json={"pdb_content": pdb})
        assert r.status_code == 400
        assert "bound ligand" in r.get_json()["error"]

    def test_bad_box_shape_400(self, client):
        r = client.post(self.URL, json={
            "pdb_content": _load_1hsg(),
            "box": {"center": [1, 2], "size": [10, 10]},
        })
        assert r.status_code == 400
        assert "box" in r.get_json()["error"]

    def test_mocked_success_200(self, client, monkeypatch, tmp_path):
        def fake_sync(pdb_text, resname=None, chain=None, box=None,
                      exhaustiveness=8):
            return {"available": True, "rmsd": 4.23, "verdict": "poor",
                    "verdict_label": "Does not reproduce the crystal pose",
                    "vina_score": -10.038, "exhaustiveness": exhaustiveness,
                    "ligand": {"resname": "MK1", "chain": "B",
                               "resnum": 902, "heavy_atoms": 45},
                    "receptor_prepared": True, "note": "n"}
        import primerforge.pipelines.redock_validate as rmod
        monkeypatch.setattr(rmod, "validate_redocking_sync", fake_sync)
        r = client.post(self.URL, json={
            "pdb_content": _load_1hsg(), "resname": "MK1", "exhaustiveness": 8})
        assert r.status_code == 200
        data = r.get_json()
        assert data["available"] is True
        assert data["rmsd"] == 4.23
        assert data["verdict"] == "poor"
        assert json.dumps(data)  # JSON-serializable

    def test_unavailable_still_200(self, client, monkeypatch, tmp_path):
        def fake_unavail(pdb_text, resname=None, chain=None, box=None,
                         exhaustiveness=8):
            return {"available": False, "reason": "Vina is not installed."}
        import primerforge.pipelines.redock_validate as rmod
        monkeypatch.setattr(rmod, "validate_redocking_sync", fake_unavail)
        r = client.post(self.URL, json={
            "pdb_content": _load_1hsg(), "resname": "MK1"})
        assert r.status_code == 200
        data = r.get_json()
        assert data["available"] is False
        assert data["reason"] == "Vina is not installed."

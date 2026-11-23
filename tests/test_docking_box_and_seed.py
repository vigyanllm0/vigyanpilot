"""Bound-ligand search box, box validation, and reproducible Vina seed."""

import os

os.environ.setdefault("PRIMERFORGE_SECRET", "unit-test-secret-for-route-import")
os.environ.setdefault("PRIMERFORGE_ADMIN_EMAIL", "box-tests@test.com")
os.environ.setdefault("PRIMERFORGE_ADMIN_PASSWORD", "BoxTests-Test-1!")

import pytest  # noqa: E402

from primerforge.pipelines import docking_engine as de  # noqa: E402


def _atom(serial, x, y, z, name="CA", res="ALA"):
    return (f"ATOM  {serial:5d}  {name:<3s} {res:>3s} A{serial:4d}    "
            f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00           C")


def _het(serial, name, res, chain, num, x, y, z, element):
    return (f"HETATM{serial:5d} {name:<4s} {res:>3s} {chain}{num:4d}    "
            f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00          {element:>2s}")


@pytest.fixture
def complex_pdb():
    protein = "\n".join(_atom(i + 1, -10 + i * 2.0, 5.0, 3.0) for i in range(12))
    ligand = "\n".join(
        _het(100 + i, nm, "SAM", "A", 900, x, y, z, nm[0])
        for i, (nm, x, y, z) in enumerate([
            ("C1", 10.0, 5.0, 3.0), ("C2", 14.0, 7.0, 4.0),
            ("O3", 12.0, 9.0, 2.0), ("N4", 16.0, 6.0, 5.0)])
    )
    water = _het(500, "O", "HOH", "A", 1000, 0.0, 0.0, 0.0, "O")
    return protein + "\n" + ligand + "\n" + water


class TestBoundLigandBox:

    def test_centres_on_bound_ligand_not_water(self, complex_pdb):
        box = de.box_from_bound_ligand(complex_pdb)
        assert box is not None
        assert box["source"] == "bound_ligand"
        assert box["ligand"]["resname"] == "SAM"
        assert box["ligand"]["heavy_atoms"] == 4, "water must not be counted"
        assert box["center"] == pytest.approx([13.0, 6.75, 3.5], abs=0.01)

    def test_side_is_extent_plus_margin_clamped(self, complex_pdb):
        box = de.box_from_bound_ligand(complex_pdb)
        assert all(de.BOX_MIN_SIDE <= s <= de.BOX_MAX_SIDE for s in box["size"])
        assert box["size"][0] == pytest.approx(22.0, abs=0.1)  # 6 A extent + 2 x 8

    def test_resname_and_chain_filters(self, complex_pdb):
        assert de.box_from_bound_ligand(complex_pdb, resname="XXX") is None
        assert de.box_from_bound_ligand(complex_pdb, resname="sam", chain="A") is not None
        assert de.box_from_bound_ligand(complex_pdb, chain="B") is None

    def test_water_or_ion_only_returns_none(self):
        water = _het(1, "O", "HOH", "A", 1, 0.0, 0.0, 0.0, "O")
        assert de.box_from_bound_ligand(water) is None

    def test_oversized_ligand_reports_truncated_axes(self):
        pts = [_het(i, "C" + str(i), "BIG", "A", 7, i * 4.0, 0.0, 0.0, "C") for i in range(10)]
        box = de.box_from_bound_ligand("\n".join(pts))
        assert "x" in box["truncated_axes"]
        assert box["size"][0] == de.BOX_MAX_SIDE


class TestValidateBox:

    def test_clean_box_has_no_warnings(self):
        assert de.validate_box({"center": [0, 0, 0], "size": [22, 22, 22]}) == {"ok": True, "warnings": []}

    def test_small_box_warns(self):
        result = de.validate_box({"center": [0, 0, 0], "size": [12, 22, 22]})
        assert not result["ok"]
        assert any("smaller" in w for w in result["warnings"])

    def test_oversized_side_warns(self):
        result = de.validate_box({"center": [0, 0, 0], "size": [40, 20, 20]})
        assert any("above 30" in w for w in result["warnings"])

    def test_volume_limit_warns(self):
        result = de.validate_box({"center": [0, 0, 0], "size": [30, 30, 31]})
        assert any("volume" in w.lower() for w in result["warnings"])

    def test_centre_outside_protein_warns(self, complex_pdb):
        result = de.validate_box({"center": [500, 0, 0], "size": [22, 22, 22]}, complex_pdb)
        assert any("outside the protein" in w for w in result["warnings"])

    def test_malformed_box_is_not_ok(self):
        assert de.validate_box({"size": "huge"})["ok"] is False


class TestConsensusBoxSelection:

    def test_bound_ligand_source_is_used_and_validated(self, complex_pdb):
        from primerforge.pipelines import consensus_pipeline as cp

        box, note = cp._select_box(complex_pdb, {"bound_ligand": {"resname": "SAM", "chain": "A"}})
        assert note is None
        assert box["source"] == "bound_ligand"
        assert "validation" in box and box["validation"]["ok"] is True

    def test_missing_bound_ligand_falls_back_with_note(self, complex_pdb):
        from primerforge.pipelines import consensus_pipeline as cp

        box, note = cp._select_box(complex_pdb, {"bound_ligand": {"resname": "ZZZ"}})
        assert box["source"] != "bound_ligand"
        assert note and "No bound ligand" in note

    def test_bound_ligand_resolves_against_original_when_prep_strips_ligand(
            self, complex_pdb):
        """Regression: receptor preparation removes HETATM — including the
        co-crystal ligand.  The pipeline must resolve a bound-ligand box
        against the raw upload, or every uploaded-complex run silently
        falls back to the whole-protein centroid box (frontend E2E on
        1HSG: MK1 stripped by prep -> run used protein_centroid)."""
        from primerforge.pipelines import consensus_pipeline as cp

        prepared = "\n".join(l for l in complex_pdb.split("\n")
                             if not l.startswith("HETATM"))
        assert "SAM" not in prepared, "test needs a ligand-stripped receptor"

        spec = {"bound_ligand": {"resname": None, "chain": None}}
        # prepared receptor alone: honest fallback (the pre-fix behaviour)
        box, note = cp._select_box(prepared, spec)
        assert box["source"] != "bound_ligand"
        assert note and "No bound ligand" in note

        # original upload supplied: the box resolves as the user asked
        box, note = cp._select_box(prepared, spec, original_pdb=complex_pdb)
        assert note is None
        assert box["source"] == "bound_ligand"
        assert box["ligand"]["resname"] == "SAM"
        assert "validation" in box



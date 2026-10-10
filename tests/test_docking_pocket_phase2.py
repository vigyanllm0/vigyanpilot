"""
Phase 2 — real docking (pocket-centered box + receptor preparation).

Covers:
 1. Box utilities: compute_box_center_from_pdb (centroid, clamps, no-coords
    fallback) and box_from_residues (selection center/size, chain filter,
    None when nothing matches).
 2. _select_box priority: manual > residue range > blind > pocket > centroid,
    size clamping to Vina's volume limit, warn-allow fallbacks (malformed
    manual override and a raising detector both degrade to centroid).
 3. Pipeline wiring: the selected box reaches Vina AND GNINA (captured) and
    stage2.box; manual box passthrough end-to-end; pocket box carries
    pocket_id/druggability/nested pocket; upload preparation strips waters/
    ions/HETATM with a report (no structure blob in the job JSON) while
    quality still classifies the ORIGINAL file (CRYST1 preserved); a
    exploding preparer never kills the run.
 4. Exhaustiveness rule: ≤10 ligands → 8, >10 → 2 (recorded = what ran).
 5. Route: box validation (manual/residue/blind accepted & normalized,
    malformed → 400 before queueing) and /gridbox residue-range + radius
    clamp modes.
 6. Queue: create_job persists the box override for the worker.
"""

import asyncio
import json

import pytest

from primerforge.pipelines.docking_engine import (
    box_from_residues,
    compute_box_center_from_pdb,
)


# ══════════════════════════════════════════════════════════════════════════
# Fixture builders (ideal poly-ALA geometry, same layout as
# tests/test_protein_validation.py so expected coordinates are computable).
# ══════════════════════════════════════════════════════════════════════════

_RES_ATOMS = (
    ("N", "N", -0.833, 1.211, 0.0),
    ("CA", "C", 0.0, 0.0, 0.0),
    ("C", "C", -0.861, -1.253, 0.0),
    ("O", "O", -0.861, -1.253, 1.24),
)


def _atom(serial, name, res, chain, num, x, y, z, b, el):
    return (
        f"ATOM  {serial:>5d} {name:^4s} {res:>3s} {chain}{num:>4d}    "
        f"{x:>8.3f}{y:>8.3f}{z:>8.3f}  1.00{b:>6.2f}          {el:>2s}"
    )


def build_pdb(n=12, b=95.0, chain="A", header=""):
    lines = [header] if header else []
    serial = 1
    for i in range(1, n + 1):
        cx = 3.8 * (i - 1)
        for name, el, dx, dy, dz in _RES_ATOMS:
            lines.append(_atom(serial, name, "ALA", chain, i,
                               cx + dx, dy, dz, b, el))
            serial += 1
    lines += ["TER", "END"]
    return "\n".join(lines) + "\n"


def _het(serial, name, res, chain, num, x, y, z, el):
    """HETATM line with the same column layout as _atom (1.00 occupancy)."""
    return (
        f"HETATM{serial:>5d} {name:^4s} {res:>3s} {chain}{num:>4d}    "
        f"{x:>8.3f}{y:>8.3f}{z:>8.3f}  1.00{0.0:>6.2f}          {el:>2s}"
    )


def pdb_with_solvent():
    """12-residue structure + 2 waters + 1 sodium ion + 1 free ligand."""
    pdb = build_pdb(12, b=95.0)
    extras = [
        _het(901, "O", "HOH", "A", 901, 50.0, 50.0, 50.0, "O"),
        _het(902, "O", "HOH", "A", 902, 51.0, 50.0, 50.0, "O"),
        _het(903, "NA", "NA", "A", 903, 52.0, 50.0, 50.0, "NA"),
        _het(904, "C1", "LIG", "A", 904, 53.0, 50.0, 50.0, "C"),
    ]
    return pdb.replace("TER\n", "TER\n" + "\n".join(extras) + "\n", 1)


def _seq(n):
    aa = "ACDEFGHIKLMNPQRSTVWY"
    return "".join(aa[i % 20] for i in range(n))


# ══════════════════════════════════════════════════════════════════════════
# 1. Box utilities
# ══════════════════════════════════════════════════════════════════════════

def test_compute_box_center_from_pdb_centroid_and_clamps():
    cx, cy, cz, sx, sy, sz = compute_box_center_from_pdb(build_pdb(12))
    # x extent 41.8 Å + 10 → clamped to the 30 Å Vina volume limit
    assert sx == 30.0
    # y/z extents are tiny → floor of default_size 25
    assert sy == 25.0 and sz == 25.0
    # centroid sits mid-protein (poly-ALA runs x=0..41.8 + atom offsets)
    assert 19.0 < cx < 22.0
    assert -1.0 < cy < 0.5 and 0.0 < cz < 1.0


def test_compute_box_center_from_pdb_no_coords_falls_back():
    assert compute_box_center_from_pdb("HEADER something\nEND\n") == (
        0.0, 0.0, 0.0, 30.0, 30.0, 30.0)


def test_box_from_residues_centers_on_selection():
    box = box_from_residues(build_pdb(12), "A", 3, 5)
    assert box is not None
    assert box["source"] == "residue_range"
    assert box["residues"] == {"chain": "A", "start": 3, "end": 5}
    # residues 3-5 → base x 7.6/11.4/15.2, mean atom x ≈ 10.76
    assert box["center"][0] == pytest.approx(10.76, abs=0.05)
    # extent x 8.46 + 10 = 18.46 → rounded 18.5; y/z fall near the 12 floor
    assert box["size"][0] == 18.5
    assert 12.0 <= box["size"][1] <= 30.0


def test_box_from_residues_no_match_returns_none():
    assert box_from_residues(build_pdb(12), "Z", 3, 5) is None   # wrong chain
    assert box_from_residues(build_pdb(12), "A", 50, 60) is None  # wrong range
    assert box_from_residues("", "A", 1, 5) is None


# ══════════════════════════════════════════════════════════════════════════
# 2. _select_box priority + warn-allow fallbacks
# ══════════════════════════════════════════════════════════════════════════

def _detect_stub(detect):
    """Build a detect_pockets stub: None→[], RuntimeError→raises,
    callable→used directly, list→returns it."""
    if detect is None:
        return lambda _pdb: []
    if detect is RuntimeError:
        def raise_stub(_pdb):
            raise RuntimeError("voxel grid exploded")
        return raise_stub
    if callable(detect):
        return detect
    return lambda _pdb: detect


def _select_box(manual, pdb=None, detect=None):
    import unittest.mock as mock
    import primerforge.pipelines.consensus_pipeline as cp
    detect_fn = _detect_stub(detect)
    with mock.patch.object(cp, "detect_pockets", detect_fn):
        return cp._select_box(pdb if pdb is not None else build_pdb(12), manual)


def test_select_box_manual_wins_and_clamps_size():
    box, note = _select_box({"center": [1.0, 2.0, 3.0],
                             "size": [50.0, 10.0, 20.0]})
    assert note is None
    assert box["source"] == "manual"
    assert box["center"] == [1.0, 2.0, 3.0]
    # clamped to Vina's [12, 30] window per side
    assert box["size"] == [30.0, 12.0, 20.0]


def test_select_box_malformed_manual_degrades_to_centroid():
    box, note = _select_box({"center": ["a", "b", "c"], "size": [25, 25, 25]})
    assert box["source"] == "protein_centroid"
    assert note is None


def test_select_box_residue_range_and_missing_fallback():
    box, note = _select_box({"residues": {"chain": "A", "start": 3, "end": 5}})
    assert box["source"] == "residue_range"
    assert note is None

    box, note = _select_box({"residues": {"chain": "A", "start": 50, "end": 60}})
    assert box["source"] == "protein_centroid"      # not found → fallback
    assert note and "not found" in note


def test_select_box_blind_skips_detection():
    calls = []

    def spy(_pdb):
        calls.append(True)
        return []

    box, note = _select_box({"blind": True}, detect=spy)
    assert box["source"] == "protein_centroid"
    assert note is None
    assert not calls          # detector never consulted (skip = skip)


def test_select_box_top_pocket_centers_the_box():
    from primerforge.pipelines.pocket_detector import Pocket
    pocket = Pocket(pocket_id=2, center=(11.0, 20.0, 30.0), radius=8.0,
                    residues=[("A", 42, "LEU")], residue_count=14,
                    volume=486.0, hydrophobicity=0.57, druggability="high",
                    score=72.5, enclosure=0.81)
    box, note = _select_box(None, detect=[pocket])
    assert note is None
    assert box["source"] == "pocket"
    assert box["pocket_id"] == 2
    assert box["druggability"] == "high"
    assert box["pocket_score"] == 72.5
    assert box["pockets_found"] == 1
    assert box["center"] == [11.0, 20.0, 30.0]
    # 2×radius + 4 = 20 Å
    assert box["size"] == [20.0, 20.0, 20.0]
    # nested copy for the 3D viewer sphere
    assert box["pocket"]["radius"] == 8.0
    assert box["pocket"]["center"] == [11.0, 20.0, 30.0]


def test_select_box_no_pockets_and_raising_detector_are_centroid():
    box, note = _select_box(None, detect=[])
    assert box["source"] == "protein_centroid"
    assert note is None

    box, note = _select_box(None, detect=RuntimeError)   # warn-allow
    assert box["source"] == "protein_centroid"
    assert note is None


# ══════════════════════════════════════════════════════════════════════════
# 3. Pipeline wiring (both engines see the same box; preparation; quality)
# ══════════════════════════════════════════════════════════════════════════

def _run(monkeypatch, *, pdb_content="", box=None, detect=None,
         receptor_capture=None, vina_calls=None, gnina_calls=None):
    """Run the pipeline with stubbed engines; capture box/receptor flow."""
    import unittest.mock as mock
    import primerforge.pipelines.consensus_pipeline as cp
    import primerforge.pipelines.docking_engine as de

    detect_fn = _detect_stub(detect)

    async def fake_esmfold(sequence, progress_callback=None):
        return {"status": "success", "tool": "test",
                "pdb_string": build_pdb(12, b=95.0),
                "plddt_score": 88.0, "sequence_length": len(sequence)}

    async def fake_vina(receptor_pdb, ligand_smiles, exhaustiveness=8,
                        receptor_pdbqt_path=None, cpu=None, box=None):
        if vina_calls is not None:
            vina_calls.append({"box": box, "exh": exhaustiveness})
        return {"binding_affinity": -6.0, "computation_time": "1.0s",
                "structure": {"ligand": build_pdb(1, b=50.0)},
                "box": box}

    async def fake_gnina(receptor_pdb, ligand_smiles, exhaustiveness=4,
                         receptor_pdbqt_path=None, box=None):
        if gnina_calls is not None:
            gnina_calls.append({"box": box})
        return {"binding_affinity": -8.0, "cnn_score": 0.8, "cnn_affinity": 3.0,
                "intramol_energy": -0.5, "poses": 9, "pose_table": [],
                "computation_time": "1.0s", "box": box}

    async def noop_progress(stage, msg, metadata=None):
        return None

    def fake_pdbqt(receptor, output_path):
        if receptor_capture is not None:
            receptor_capture.append(receptor)
        with open(output_path, "w") as fh:
            fh.write("ATOM      1  C   UNL A   1       0.000   0.000   0.000"
                     "  0.00  0.00     0.000 C\n")
        return True

    monkeypatch.setattr(cp, "esmfold_predict", fake_esmfold)
    monkeypatch.setattr(cp, "run_vina_docking", fake_vina)
    monkeypatch.setattr(cp, "run_gnina_docking", fake_gnina)
    # Availability probe stubbed OK — this helper exercises the run path with
    # a fake GNINA; the real probe (test host may lack GNINA) would skip
    # stage 3 instead of calling the fake.
    monkeypatch.setattr(cp, "gnina_available", lambda **kw: {
        "ok": True, "path": "gnina", "version": "test", "reason": None})
    monkeypatch.setattr(de, "pdb_to_pdbqt", fake_pdbqt)
    with mock.patch.object(cp, "detect_pockets", detect_fn):
        return asyncio.run(cp.run_consensus_pipeline(
            _seq(40) if not pdb_content else "", ["CCO"], top_n=1,
            progress_callback=noop_progress,
            pdb_content=pdb_content, box=box))


def test_pipeline_pocket_box_reaches_both_engines(monkeypatch):
    from primerforge.pipelines.pocket_detector import Pocket
    pocket = Pocket(pocket_id=1, center=(5.0, 6.0, 7.0), radius=7.0,
                    residues=[], residue_count=10, volume=300.0,
                    hydrophobicity=0.4, druggability="moderate", score=60.0,
                    enclosure=0.7)
    vina_calls, gnina_calls = [], []
    result = _run(monkeypatch, detect=[pocket],
                  vina_calls=vina_calls, gnina_calls=gnina_calls)
    assert result["status"] == "success", result.get("message")
    s2 = result["stage2"]
    assert s2["box"]["source"] == "pocket"
    # sequence mode produces a clean ESMFold structure — no preparation pass
    assert "preparation" not in result["stage1"]
    assert s2["box"]["pocket_id"] == 1
    assert s2["box"]["druggability"] == "moderate"
    # identical box object handed to Vina AND GNINA (stage-3 refines the
    # same volume stage 2 screened)
    assert vina_calls and vina_calls[0]["box"]["source"] == "pocket"
    assert gnina_calls and gnina_calls[0]["box"]["center"] == [5.0, 6.0, 7.0]
    # small run → deeper search recorded
    assert s2["exhaustiveness"] == 8
    assert vina_calls[0]["exh"] == 8


def test_pipeline_manual_box_passthrough(monkeypatch):
    vina_calls, gnina_calls = [], []
    result = _run(monkeypatch,
                  box={"center": [9.5, 8.5, 7.5], "size": [22.0, 18.0, 16.0]},
                  vina_calls=vina_calls, gnina_calls=gnina_calls)
    assert result["status"] == "success", result.get("message")
    s2 = result["stage2"]
    assert s2["box"] == {"center": [9.5, 8.5, 7.5],
                         "size": [22.0, 18.0, 16.0], "source": "manual"}
    assert vina_calls[0]["box"]["source"] == "manual"
    assert gnina_calls[0]["box"]["source"] == "manual"
    # detector never consulted when an explicit override exists
    assert "box_note" not in s2


def test_pipeline_residue_box_and_missing_note(monkeypatch):
    result = _run(monkeypatch,
                  box={"residues": {"chain": "A", "start": 3, "end": 5}})
    assert result["status"] == "success", result.get("message")
    assert result["stage2"]["box"]["source"] == "residue_range"

    result = _run(monkeypatch,
                  box={"residues": {"chain": "A", "start": 900, "end": 999}})
    assert result["status"] == "success"
    s2 = result["stage2"]
    assert s2["box"]["source"] == "protein_centroid"
    assert "not found" in s2["box_note"]


def test_pipeline_upload_preparation_strips_solvent(monkeypatch):
    receptor = []
    result = _run(monkeypatch, pdb_content=pdb_with_solvent(),
                  receptor_capture=receptor)
    assert result["status"] == "success", result.get("message")
    prep = result["stage1"]["preparation"]
    assert prep["performed"] is True
    assert prep["waters_removed"] == 2
    assert prep["ions_removed"] == 1
    assert "LIG" in prep["hetatm_removed"]
    assert prep["changed_structure"] is True
    # the structure itself is NOT duplicated into the job JSON
    assert "prepared_pdb" not in prep
    # the receptor that reached PDBQT conversion is solvent-free
    assert receptor and "HOH" not in receptor[0]
    assert " LIG" not in receptor[0]
    # protein atoms kept
    assert receptor[0].count("ATOM  ") == 12 * 4


def test_prepare_upload_caps_protonation_list(monkeypatch):
    """Per-residue protonation list is bounded in the job JSON (polish item)
    while protonation_count keeps the true total for display."""
    import primerforge.pipelines.consensus_pipeline as cp

    prepared_pdb = ("ATOM      N  ALA A   1       0.000   0.000   0.000"
                    "  1.00 95.00           N\n")

    class _Report:
        pass

    report = _Report()
    report.prepared_pdb = prepared_pdb
    monkeypatch.setattr(cp, "prepare_protein", lambda _s: report)

    long_list = [f"ASP{i} HID" for i in range(1, 81)]  # 80 residues
    monkeypatch.setattr(cp, "_prep_report_dict", lambda _r: {
        "waters_removed": 0, "ions_removed": 0, "hetatm_removed": [],
        "hydrogens_added": 0, "protonation_changes": list(long_list),
        "prepared_pdb": prepared_pdb})

    prepared, prep = cp._prepare_upload("ATOM ...original...")
    assert prepared == prepared_pdb
    assert prep["protonation_count"] == 80          # true total kept
    assert len(prep["protonation_changes"]) == 20   # list capped
    assert prep["protonation_truncated"] is True
    assert "prepared_pdb" not in prep

    # short list → counted but never flagged/truncated
    monkeypatch.setattr(cp, "_prep_report_dict", lambda _r: {
        "waters_removed": 0, "ions_removed": 0, "hetatm_removed": [],
        "hydrogens_added": 0, "protonation_changes": ["ASP10 HID"],
        "prepared_pdb": prepared_pdb})
    _, short = cp._prepare_upload("ATOM ...original...")
    assert short["protonation_count"] == 1
    assert "protonation_truncated" not in short
    assert short["protonation_changes"] == ["ASP10 HID"]


def test_pipeline_quality_runs_on_original_before_preparation(monkeypatch):
    # Two header lines: preparation keeps only other_lines[:1] (HEADER), so
    # if quality ran on the PREPARED receptor the CRYST1 record would be
    # gone and confidence would be misread as prediction. Quality must run
    # on the ORIGINAL file first.
    pdb = build_pdb(12, b=30.0, header=(
        "HEADER    SYNTHETIC TEST STRUCTURE\n"
        "CRYST1   42.000   42.000   42.000  90.00  90.00  90.00 P 1           1"))
    pdb = pdb.replace("TER\n", "TER\n" + _het(901, "O", "HOH", "A", 901,
                                               50.0, 50.0, 50.0, "O") + "\n", 1)
    result = _run(monkeypatch, pdb_content=pdb)
    assert result["status"] == "success", result.get("message")
    q = result["stage1"]["quality"]
    assert q["plddt_source"] == "b_factor_estimate"
    # ...and the water was still removed from the docking receptor
    assert result["stage1"]["preparation"]["waters_removed"] == 1


def test_pipeline_preparation_failure_is_warn_allow(monkeypatch):
    import primerforge.pipelines.consensus_pipeline as cp

    def boom(_pdb, **_kw):
        raise RuntimeError("preparer exploded")

    monkeypatch.setattr(cp, "prepare_protein", boom)
    receptor = []
    result = _run(monkeypatch, pdb_content=pdb_with_solvent(),
                  receptor_capture=receptor)
    assert result["status"] == "success", result.get("message")
    prep = result["stage1"]["preparation"]
    assert prep["performed"] is False
    assert "exploded" in prep["error"]
    # original structure used as the receptor
    assert receptor and "HOH" in receptor[0]


# ══════════════════════════════════════════════════════════════════════════
# 4. Exhaustiveness rule (queue-side mirror asserted in test_gnina_phase1)
# ══════════════════════════════════════════════════════════════════════════

def test_stage2_exhaustiveness_rule():
    from primerforge.pipelines.consensus_pipeline import _stage2_exhaustiveness
    assert _stage2_exhaustiveness(1) == 8
    assert _stage2_exhaustiveness(10) == 8
    assert _stage2_exhaustiveness(11) == 2
    assert _stage2_exhaustiveness(100) == 2


# ══════════════════════════════════════════════════════════════════════════
# 5. Route: box validation before queueing + /gridbox modes
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def env(monkeypatch, tmp_path):
    """Fresh app whose create_job captures the box override."""
    from primerforge.primer_server import create_app

    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("PRIMERFORGE_DB", str(tmp_path / "pk.db"))
    monkeypatch.delenv("REDIS_URL", raising=False)
    import primerforge.security as security
    monkeypatch.setattr(security, "init_admin_rbac", lambda application: None)

    import primerforge.docking_queue as dq

    captured: dict = {}

    def fake_create(sequence, ligand_smiles_list, top_n=50, pdb_content="",
                    box=None):
        captured.update(sequence=sequence, ligands=list(ligand_smiles_list),
                        top_n=top_n, pdb_content=pdb_content, box=box)
        return "pkfakejobid"

    monkeypatch.setattr(dq, "create_job", fake_create)

    application = create_app()
    app = application.wsgi_app if hasattr(application, "wsgi_app") else application
    return app.test_client(), captured


def _post(client, body):
    return client.post("/api/primer/docking/consensus",
                       data=json.dumps(body),
                       headers={"Content-Type": "application/json"})


def _seq_body(**extra):
    body = {"sequence": _seq(30), "ligand_smiles_list": ["CCO"]}
    body.update(extra)
    return body


def test_route_accepts_manual_box(env):
    client, captured = env
    r = _post(client, _seq_body(box={"center": [1.5, 2.5, 3.5],
                                     "size": [24, 20, 18]}))
    assert r.status_code == 202, r.get_json()
    assert captured["box"] == {"center": [1.5, 2.5, 3.5],
                               "size": [24.0, 20.0, 18.0]}


def test_route_accepts_residue_and_blind_box(env):
    client, captured = env
    r = _post(client, _seq_body(
        box={"residues": {"chain": "B", "start": 10, "end": 25}}))
    assert r.status_code == 202, r.get_json()
    assert captured["box"] == {"residues": {"chain": "B", "start": 10, "end": 25}}

    r = _post(client, _seq_body(box={"blind": True}))
    assert r.status_code == 202, r.get_json()
    assert captured["box"] == {"blind": True}


@pytest.mark.parametrize("bad_box, fragment", [
    (["not", "an", "object"], "must be an object"),
    ({"center": [1, 2], "size": [25, 25, 25]}, "3 numbers"),
    ({"center": [1, 2, 3], "size": [25, 25]}, "3 numbers"),
    ({"center": [1, 2, 3], "size": ["x", "y", "z"]}, "numbers"),
    ({"center": [float("nan"), 2, 3], "size": [25, 25, 25]}, "finite"),
    ({"center": [1, 2, 3], "size": [100, 25, 25]}, "6–40"),
    ({"center": [1, 2, 3], "size": [25, 25, 0]}, "6–40"),
    ({"residues": {"chain": "A", "start": "x", "end": 5}}, "integers"),
    ({"residues": {"chain": "A", "start": 10, "end": 5}}, "start ≤ end"),
    ({}, "center+size"),
    ({"junk": 1}, "center+size"),
])
def test_route_rejects_malformed_box(env, bad_box, fragment):
    client, captured = env
    r = _post(client, _seq_body(box=bad_box))
    assert r.status_code == 400, (bad_box, r.get_json())
    assert fragment in r.get_json()["error"]
    assert not captured  # never queued, no credit consumed


def test_gridbox_residue_range_mode(env):
    client, _ = env
    r = client.post("/api/primer/docking/gridbox",
                    data=json.dumps({"pdb_content": build_pdb(12),
                                     "residues": "A:3-5"}),
                    headers={"Content-Type": "application/json"})
    assert r.status_code == 200, r.get_json()
    body = r.get_json()
    assert body["source"] == "residue_range"
    assert body["center"]["x"] == pytest.approx(10.76, abs=0.05)
    assert body["size"]["x"] == 18.5
    assert body["residues"] == {"chain": "A", "start": 3, "end": 5}


def test_gridbox_radius_mode_validates_and_clamps(env):
    client, _ = env
    r = client.post("/api/primer/docking/gridbox",
                    data=json.dumps({"center": [1, 2, 3], "radius": 8}),
                    headers={"Content-Type": "application/json"})
    assert r.status_code == 200
    assert r.get_json()["size"]["x"] == 20.0   # 2*8 + 4

    # radius above Vina's per-side limit is rejected outright
    r = client.post("/api/primer/docking/gridbox",
                    data=json.dumps({"center": [1, 2, 3], "radius": 40}),
                    headers={"Content-Type": "application/json"})
    assert r.status_code == 400

    # residue range with no matching atoms → 400 (nothing computed)
    r = client.post("/api/primer/docking/gridbox",
                    data=json.dumps({"pdb_content": build_pdb(12),
                                     "residues": {"chain": "A", "start": 700,
                                                  "end": 800}}),
                    headers={"Content-Type": "application/json"})
    assert r.status_code == 400
    assert "No atoms found" in r.get_json()["error"]


# ══════════════════════════════════════════════════════════════════════════
# 6. Queue: the override survives create_job → get_job
# ══════════════════════════════════════════════════════════════════════════

def test_create_job_persists_box_override(monkeypatch, tmp_path):
    import primerforge.docking_queue as dq

    for attr in ("PENDING_DIR", "RUNNING_DIR", "COMPLETE_DIR", "FAILED_DIR"):
        d = tmp_path / attr.lower()
        d.mkdir()
        monkeypatch.setattr(dq, attr, str(d))
    monkeypatch.setattr(
        "primerforge.docking_db.save_job", lambda *a, **k: None, raising=False)

    job_id = dq.create_job(_seq(30), ["CCO"], top_n=1, pdb_content="",
                           box={"blind": True})
    job = dq.get_job(job_id)
    assert job is not None
    assert job["box"] == {"blind": True}

    # default: box key present and None (auto selection)
    job_id2 = dq.create_job(_seq(30), ["CCO"], top_n=1, pdb_content="")
    assert dq.get_job(job_id2)["box"] is None

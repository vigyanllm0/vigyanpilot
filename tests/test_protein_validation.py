"""
Phase 4 — protein validation ("broken or perfect").

Covers:
 1. Analyzer foundations: b_factor parsing (incl. malformed + first-model-only),
    all-zero-B neutral guard, per-residue pLDDT extraction & scale detection,
    confidence-region segmentation, count_ca_residues.
 2. Fallback-helix residue-numbering regression (every residue used to be #1).
 3. Verdict mapping (A/B good, C usable, D/F poor + pLDDT<50 floor) and
    confidence-source detection (esmfold / prediction / b_factor_estimate /
    unavailable).
 4. _stage1_quality: warn-allow error containment, repair suggestion flags,
    indicative_only, truncation caps with authoritative totals, JSON safety.
 5. Pipeline wiring: stage1.quality + mode on both branches; an analyzer
    explosion never kills the run.
 6. Route pre-validation: uploaded structure needs ≥10 CA residues (400
    before queuing/token burn).
"""

import asyncio
import json

import pytest

from primerforge.pipelines.broken_protein_analyzer import (
    _parse_pdb,
    analyze_plddt,
    count_ca_residues,
    extract_per_residue_plddt,
)


# ══════════════════════════════════════════════════════════════════════════
# Fixture builders — ideal poly-ALA geometry:
#   N-CA 1.47 A, CA-C 1.52 A, N-CA-C 111° (passes check_ramachandran),
#   nearest inter-residue contact 3.20 A vs VdW sum 3.25 (no clash at the
#   0.5 A overlap threshold), contiguous numbering (no gaps).
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


def build_pdb(n=12, b=95.0, chain="A", header="", renumber=None, duplicates=0):
    """Ideal-geometry poly-ALA structure.

    renumber: {original_resnum: new_resnum} (creates numbering gaps).
    duplicates: extra residues placed AT residue 2's coordinates with fresh
    residue numbers → guaranteed cross-residue steric clashes.
    """
    lines = [header] if header else []
    serial = 1

    def emit(num, base_i, bb):
        nonlocal serial
        cx = 3.8 * base_i
        for name, el, dx, dy, dz in _RES_ATOMS:
            lines.append(_atom(serial, name, "ALA", chain, num,
                               cx + dx, dy, dz, bb, el))
            serial += 1

    renumber = renumber or {}
    for i in range(1, n + 1):
        emit(renumber.get(i, i), i, b)
    for d in range(duplicates):
        emit(100 + d, 2, b)
    lines += ["TER", "END"]
    return "\n".join(lines) + "\n"


def _strip_model_end(pdb):
    return "\n".join(
        line for line in pdb.splitlines()
        if line != "TER" and not line.startswith("END")
    )


def _seq(n):
    aa = "ACDEFGHIKLMNPQRSTVWY"
    return "".join(aa[i % 20] for i in range(n))


# ══════════════════════════════════════════════════════════════════════════
# 1. Analyzer foundations
# ══════════════════════════════════════════════════════════════════════════

def test_parse_pdb_reads_b_factor():
    _, atoms = _parse_pdb(build_pdb(3, b=95.0))
    assert len(atoms) == 12
    assert all(a["b_factor"] == 95.0 for a in atoms)


def test_parse_pdb_malformed_b_factor_keeps_atom():
    # A garbage temperature column must never drop the atom (0.0 = no data).
    pdb = build_pdb(3, b=95.0).replace("95.00", " ABC ")
    residues, atoms = _parse_pdb(pdb)
    assert len(atoms) == 12
    assert len(residues) == 3
    assert all(a["b_factor"] == 0.0 for a in atoms)


def test_parse_pdb_reads_first_model_only():
    # NMR ensembles: atoms of model 2 must NOT merge into model 1's residues
    # (they used to — every inter-model contact reported as a fake clash).
    model = _strip_model_end(build_pdb(4))
    pdb = f"MODEL        1\n{model}\nENDMDL\nMODEL        2\n{model}\nENDMDL\nEND\n"
    residues, atoms = _parse_pdb(pdb)
    assert len(residues) == 4
    assert len(atoms) == 16  # model 2 excluded


def test_analyze_plddt_all_zero_b_is_neutral_not_perfect():
    # Regression: with b_factor now parsed, an all-zero column would have
    # estimated a perfect 100 per residue. Guard: neutral documented default.
    pdb = build_pdb(6, b=0.0)
    result = analyze_plddt(pdb)
    assert result["mean_plddt"] == 70.0
    assert extract_per_residue_plddt(pdb) is None  # caller sees "no data"


def test_extract_per_residue_plddt_scales():
    # percent scale (local models / AlphaFold B column)
    assert extract_per_residue_plddt(build_pdb(4, b=95.0)) == [95.0] * 4
    # 0-1 fraction scale (ESMFold web API) → detected and scaled to percent
    frac = build_pdb(4, b=95.0).replace("95.00", "0.950")
    assert extract_per_residue_plddt(frac) == [95.0] * 4
    # no data at all
    assert extract_per_residue_plddt(build_pdb(4, b=0.0)) is None
    assert extract_per_residue_plddt("") is None


def test_count_ca_residues():
    assert count_ca_residues(build_pdb(7)) == 7
    ligand_only = ("ATOM      1  C   LIG A   1       0.000   0.000   0.000"
                   "  1.00  0.00           C\n")
    assert count_ca_residues(ligand_only) == 0


def test_regions_segmentation_merges_short_runs():
    # tier runs: high×4, very_low×2 (short → merged into previous run and
    # re-tiered from the merged mean), high×6.
    pdb = build_pdb(12, b=95.0)
    scores = [95, 95, 95, 95, 40, 40, 95, 95, 95, 95, 95, 95]
    result = analyze_plddt(pdb, scores)
    regions = result["regions"]
    assert len(regions) == 2
    first, second = regions
    assert (first["start"], first["end"], first["count"]) == (1, 6, 6)
    assert first["mean"] == 76.7
    assert first["tier"] == "medium"  # (95*4 + 40*2) / 6 → 70–89 tier
    assert (second["start"], second["end"], second["count"]) == (7, 12, 6)
    assert second["tier"] == "high"
    # contiguous uniform structure → a single region
    uniform = analyze_plddt(build_pdb(12, b=95.0), [95.0] * 12)["regions"]
    assert len(uniform) == 1
    assert uniform[0]["tier"] == "high"


# ══════════════════════════════════════════════════════════════════════════
# 2. Fallback-helix residue numbering (regression)
# ══════════════════════════════════════════════════════════════════════════

def test_fallback_pdb_numbers_residues_distinctly():
    from primerforge.pipelines.broken_protein_analyzer import (
        detect_missing_residues,
    )
    from primerforge.pipelines.esmfold_engine import _generate_fallback_pdb

    seq = "MKVLAAGIVGLSTAAAGLVAAG"
    pdb = _generate_fallback_pdb(seq)
    residues, _ = _parse_pdb(pdb)
    # regression: every residue used to be numbered 1 (one merged residue)
    assert len(residues) == len(seq)
    assert count_ca_residues(pdb) == len(seq)
    assert detect_missing_residues(pdb) == []


# ══════════════════════════════════════════════════════════════════════════
# 3. Verdict mapping + confidence sources
# ══════════════════════════════════════════════════════════════════════════

def test_quality_verdict_mapping():
    import primerforge.pipelines.consensus_pipeline as cp

    assert cp._quality_verdict("A", 95, "esmfold") == "good"
    assert cp._quality_verdict("B", 76, "prediction") == "good"
    assert cp._quality_verdict("C", 65, "esmfold") == "usable"
    assert cp._quality_verdict("D", 45, "esmfold") == "poor"
    assert cp._quality_verdict("F", 20, "esmfold") == "poor"
    # confidence floor: a confident-looking grade can't rescue pLDDT < 50
    assert cp._quality_verdict("A", 40, "esmfold") == "poor"
    # no confidence data → grade governs (there is no number to floor)
    assert cp._quality_verdict("B", 40, "unavailable") == "good"
    # unknown grade → conservative middle
    assert cp._quality_verdict("X", None, "esmfold") == "usable"


def test_confidence_source_esmfold():
    import primerforge.pipelines.consensus_pipeline as cp

    scores, src = cp._confidence_source(build_pdb(12, b=95.0), "esmfold", 88)
    assert (src, scores[0], len(scores)) == ("esmfold", 95.0, 12)
    # no B data (helical fallback writes 0.00): honest stage-1 mean is fed
    # as a uniform list so the analyzer reports it verbatim (0 → very low)
    zero = build_pdb(12, b=0.0)
    scores, src = cp._confidence_source(zero, "esmfold", 0)
    assert (src, scores) == ("esmfold", [0.0] * 12)
    scores, src = cp._confidence_source(zero, "esmfold", None)
    assert (src, scores) == ("esmfold", [70.0] * 12)


def test_confidence_source_upload_prediction_vs_experimental():
    import primerforge.pipelines.consensus_pipeline as cp

    # no experimental records + B data → prediction (B = pLDDT)
    scores, src = cp._confidence_source(build_pdb(12, b=95.0), "upload", None)
    assert src == "prediction" and scores[0] == 95.0
    # experimental header + B data → B is a displacement factor: analyzer's
    # documented 100-B/2 heuristic applies, labelled b_factor_estimate
    cryst = "CRYST1    1.000    1.000    1.000  90.00  90.00  90.00 P 1           1\n"
    scores, src = cp._confidence_source(
        build_pdb(12, b=40.0, header=cryst), "upload", None)
    assert (scores, src) == (None, "b_factor_estimate")
    # experimental + all-zero B → nothing to estimate from
    scores, src = cp._confidence_source(
        build_pdb(12, b=0.0, header=cryst), "upload", None)
    assert (scores, src) == (None, "unavailable")
    # prediction header wins even when CRYST1 is present
    _, src = cp._confidence_source(
        build_pdb(12, b=95.0, header=cryst + "REMARK 999 ALPHAFOLD V4\n"),
        "upload", None)
    assert src == "prediction"
    # no header, no B data → unavailable (never fabricated numbers)
    scores, src = cp._confidence_source(build_pdb(12, b=0.0), "upload", None)
    assert (scores, src) == (None, "unavailable")


# ══════════════════════════════════════════════════════════════════════════
# 4. _stage1_quality — warn-allow, repair flags, truncation
# ══════════════════════════════════════════════════════════════════════════

def test_stage1_quality_good_structure():
    import primerforge.pipelines.consensus_pipeline as cp

    q = cp._stage1_quality(build_pdb(12, b=95.0), "esmfold", 95)
    assert q["verdict"] == "good"
    assert q["quality_score"] >= 75
    assert q["plddt_source"] == "esmfold"
    assert q["plddt"]["mean"] == 95.0
    assert q["indicative_only"] is False
    assert q["repair_suggested"] is False
    assert q["totals"]["gaps"] == 0 and q["totals"]["clashes"] == 0
    assert q["plddt"]["regions"]  # strip/table data present
    json.dumps(q)  # status route must jsonify this


def test_stage1_quality_gap_suggests_repair():
    import primerforge.pipelines.consensus_pipeline as cp

    # residue 5 renumbered to 20 → numbering gaps (4→6 and 12→20)
    q = cp._stage1_quality(build_pdb(12, renumber={5: 20}), "esmfold", 95)
    assert q["repair_suggested"] is True
    assert q["totals"]["gaps"] >= 2
    assert q["missing_residues"]
    assert q["quality_score"] > 50  # gaps alone don't condemn the structure


def test_stage1_quality_clashes_suggest_repair():
    import primerforge.pipelines.consensus_pipeline as cp

    q = cp._stage1_quality(build_pdb(12, duplicates=3), "esmfold", 95)
    assert q["repair_suggested"] is True
    assert q["totals"]["clashes"] >= 4
    assert any(c["severity"] == "critical" for c in q["clashes"])


def test_stage1_quality_truncation_caps_with_totals():
    import primerforge.pipelines.consensus_pipeline as cp

    q = cp._stage1_quality(build_pdb(12, duplicates=3), "esmfold", 95)
    # pathological overlap count: lists capped for the job JSON…
    assert len(q["clashes"]) == 20
    assert len(q["defects"]) <= 40
    assert q["truncated"] is True
    # …while the counts stay authoritative (pre-truncation)
    assert q["totals"]["clashes"] > 20


def test_stage1_quality_low_plddt_forces_poor_and_indicative():
    import primerforge.pipelines.consensus_pipeline as cp

    q = cp._stage1_quality(build_pdb(12, b=30.0), "esmfold", 30)
    assert q["plddt"]["mean"] == 30.0
    assert q["verdict"] == "poor"          # floor overrides the C-grade composite
    assert q["indicative_only"] is True


def test_stage1_quality_fallback_helix_is_poor():
    import primerforge.pipelines.consensus_pipeline as cp
    from primerforge.pipelines.esmfold_engine import _generate_fallback_pdb

    seq = "MKVLAAGIVGLSTAAAGVLAAG"
    pdb = _generate_fallback_pdb(seq)
    q = cp._stage1_quality(pdb, "esmfold", 0)
    assert q["plddt"]["total_residues"] == len(seq)
    assert q["plddt"]["mean"] == 0.0       # honest fallback pLDDT, verbatim
    assert q["verdict"] == "poor"
    assert q["indicative_only"] is True


def test_stage1_quality_analyzer_failure_is_contained(monkeypatch):
    import primerforge.pipelines.consensus_pipeline as cp

    def boom(*_args, **_kwargs):
        raise RuntimeError("analyzer exploded")

    monkeypatch.setattr(cp, "analyze_protein", boom)
    q = cp._stage1_quality(build_pdb(12), "esmfold", 95)  # must not raise
    assert q["verdict"] == "unknown"
    assert "analyzer exploded" in q["error"]


# ══════════════════════════════════════════════════════════════════════════
# 4b. Clash detection — covalent geometry is NOT a steric clash
#     (production bug 2026-10-10: every peptide bond was reported as a
#     "critical clash"; a 159-aa pLDDT-91 model showed 50 fake criticals
#     and was downgraded to grade C "treat with caution")
# ══════════════════════════════════════════════════════════════════════════

def _ca(serial, name, res_num, x, y, z, element, res_name="ALA", chain="A"):
    return {"serial": serial, "name": name, "res_name": res_name,
            "chain": chain, "res_num": res_num, "x": x, "y": y, "z": z,
            "element": element}


def test_peptide_bonds_and_1_3_neighbours_are_not_clashes():
    from primerforge.pipelines.broken_protein_analyzer import detect_clashes

    atoms = [
        # residue 1 backbone: C=0,0,0 — peptide C(i)-N(i+1) = 1.33 A (real
        # geometry 1.20-1.39 in predicted models) would have tripped the
        # old overlap test (vdW sum 3.25 - 1.33 = 1.92 A "overlap")
        _ca(1, "C", 1, 0.0, 0.0, 0.0, "C"),
        _ca(2, "O", 1, 0.0, -1.23, 0.0, "O"),
        _ca(3, "N", 2, 1.33, 0.0, 0.0, "N"),
        _ca(4, "CA", 2, 2.5, 0.9, 0.0, "C"),   # C(i)...CA(i+1) 1-3 ~2.6 A
        _ca(5, "C", 2, 3.9, 0.2, 0.0, "C"),
        # PRO CD(i+1): 1-3 partner of C(i) across the link (~2.4 A)
        _ca(6, "CD", 2, 1.1, 1.4, 0.6, "C", res_name="PRO"),
    ]
    assert detect_clashes(atoms) == []


def test_sidechain_sidechain_clash_between_consecutive_residues_still_flagged():
    from primerforge.pipelines.broken_protein_analyzer import detect_clashes

    atoms = [
        _ca(1, "CB", 1, 0.0, 0.0, 0.0, "C"),
        _ca(2, "CB", 2, 1.2, 0.0, 0.0, "C"),   # 1.2 A apart, both sidechain
    ]
    clashes = detect_clashes(atoms)
    assert len(clashes) == 1
    assert clashes[0]["severity"] == "critical"


def test_real_nonbonded_clash_far_from_peptide_link_still_flagged():
    from primerforge.pipelines.broken_protein_analyzer import detect_clashes

    # The production case: ARG44 NH2 sits 1.01 A from GLN65 O (a genuine
    # ESMFold defect) — residues 21 apart, must survive every skip rule.
    atoms = [
        _ca(1, "NH2", 44, -12.252, 7.682, -11.374, "N", res_name="ARG"),
        _ca(2, "O", 65, -12.638, 6.998, -12.009, "O", res_name="GLN"),
    ]
    clashes = detect_clashes(atoms)
    assert len(clashes) == 1
    assert clashes[0]["distance"] == pytest.approx(1.01, abs=0.01)
    assert clashes[0]["severity"] == "critical"


def test_disulfide_bond_is_not_a_clash():
    from primerforge.pipelines.broken_protein_analyzer import detect_clashes

    atoms = [
        _ca(1, "SG", 10, 0.0, 0.0, 0.0, "S", res_name="CYS"),
        _ca(2, "SG", 50, 2.05, 0.0, 0.0, "S", res_name="CYS"),
    ]
    assert detect_clashes(atoms) == []


def test_quality_score_clash_component_gradates_instead_of_cliff():
    # Old formula (5n + 20*sum overlaps) saturated to a full 20-point loss
    # at ~4 mild contacts; the MolProbity-style rate keeps a small penalty
    # for a handful of warnings and still zeroes out for a broken model.
    from primerforge.pipelines.broken_protein_analyzer import compute_quality_score

    plddt = {"mean_plddt": 90, "total_residues": 100}
    hbond = {"satisfaction_rate": 70}
    mild = [{"overlap": 0.6}] * 4          # 4 warnings in an 800-atom model
    q_mild = compute_quality_score(plddt, [], mild, [], hbond, n_atoms=800)
    assert q_mild[0] >= 90, "4 mild short contacts must not zero the clash component"

    garbage = [{"overlap": 2.0}] * 40      # 120 weighted / 800 atoms = 150/1000
    q_bad = compute_quality_score(plddt, [], garbage, [], hbond, n_atoms=800)
    assert q_bad[0] < 80, "a grossly clashing model must still be penalised"
    assert q_mild[0] > q_bad[0] + 5


def test_docking_recommendation_is_severity_aware():
    # "Minor issues" must not sit beside a "N critical" defect count: the
    # suitable-but-critical case names the defects and the repair path.
    from primerforge.pipelines.broken_protein_analyzer import _docking_recommendation

    clean = _docking_recommendation(88.0, 0)
    assert "suitable for docking" in clean and "Minor issues" in clean

    sev2 = _docking_recommendation(88.0, 2)
    assert "suitable for docking overall" in sev2
    assert "2 severe defects" in sev2 and "Minor issues" not in sev2
    assert "Repair structure" in sev2

    sev1 = _docking_recommendation(88.0, 1)
    assert "1 severe defect flagged" in sev1 and "1 severe defects" not in sev1

    # mid / low tiers unchanged
    assert "moderate quality issues" in _docking_recommendation(60.0, 5)
    assert "significant quality issues" in _docking_recommendation(30.0, 9)


def test_docking_recommendation_wired_through_analyze_protein():
    # End-to-end: a real analyze_protein report carries the helper's verdict.
    from primerforge.pipelines.broken_protein_analyzer import (
        _docking_recommendation,
        analyze_protein,
    )

    report = analyze_protein(build_pdb(n=12))
    assert report.recommendation == _docking_recommendation(
        report.quality_score,
        sum(1 for d in report.defects if d.severity == "critical"),
    )


def test_stage1_quality_no_fake_criticals_on_clean_peptide_geometry():
    # Ideal poly-ALA has peptide-length contacts only in real builds; run
    # the full stage-1 path on a genuine 159-aa ESMFold-style backbone and
    # require that critical defects come from real anomalies alone.
    import primerforge.pipelines.consensus_pipeline as cp
    from primerforge.pipelines.broken_protein_analyzer import analyze_protein

    # 40-residue contiguous segment with authentic peptide C-N spacing
    lines, serial, x = [], 1, 0.0
    for i in range(1, 41):
        for name, el, dx, dy, dz in (("N", "N", 0.0, 1.21, 0.0),
                                     ("CA", "C", 0.0, 0.0, 0.0),
                                     ("C", "C", 1.28, -1.0, 0.0),
                                     ("O", "O", 1.28, -1.0, 1.24)):
            lines.append(_atom(serial, name, "ALA", "A", i,
                               x + dx, dy, dz, 95.0, el))
            serial += 1
        x += 3.8
    pdb = "\n".join(lines) + "\nEND\n"
    report = analyze_protein(pdb)
    # covalent backbone pairs excluded → nothing critical on clean geometry
    crit = [c for c in report.clashes if c["severity"] == "critical"]
    assert crit == [], f"peptide geometry leaked as critical: {crit[:3]}"
    q = cp._stage1_quality(pdb, "esmfold", 95)
    assert q["defect_count"]["critical"] == 0
    assert q["repair_suggested"] is False


# ══════════════════════════════════════════════════════════════════════════
# 5. Pipeline wiring (both branches) + warn-allow end-to-end
# ══════════════════════════════════════════════════════════════════════════

def _run(monkeypatch, *, pdb=None, plddt=88.0, pdb_content="",
         esmfold_calls=None):
    import primerforge.pipelines.consensus_pipeline as cp
    import primerforge.pipelines.docking_engine as de

    async def fake_esmfold(sequence, progress_callback=None):
        if esmfold_calls is not None:
            esmfold_calls.append(sequence)
        return {"status": "success", "tool": "test",
                "pdb_string": pdb or build_pdb(12, b=95.0),
                "plddt_score": plddt, "sequence_length": len(sequence)}

    async def fake_vina(receptor_pdb, ligand_smiles, exhaustiveness=8,
                        receptor_pdbqt_path=None, cpu=None, box=None):
        return {"binding_affinity": -5.5,
                "structure": {"ligand": build_pdb(1, b=50.0)}}

    async def noop_progress(stage, msg, metadata=None):
        return None

    def fake_pdbqt(receptor, output_path):
        with open(output_path, "w") as fh:
            fh.write("ATOM      1  C   UNL A   1       0.000   0.000   0.000"
                     "  0.00  0.00     0.000 C\n")
        return True

    monkeypatch.setattr(cp, "esmfold_predict", fake_esmfold)
    monkeypatch.setattr(cp, "run_vina_docking", fake_vina)
    monkeypatch.setattr(de, "pdb_to_pdbqt", fake_pdbqt)
    return asyncio.run(cp.run_consensus_pipeline(
        _seq(40), ["CCO"], top_n=1, progress_callback=noop_progress,
        pdb_content=pdb_content))


def test_pipeline_wires_quality_esmfold_mode(monkeypatch):
    result = _run(monkeypatch, plddt=88.0)
    assert result["status"] == "success", result.get("message")
    s1 = result["stage1"]
    assert s1["mode"] == "esmfold"
    q = s1["quality"]
    assert q["verdict"] == "good"
    assert q["plddt_source"] == "esmfold"
    assert q["plddt"]["mean"] == 95.0
    assert q["plddt"]["regions"]
    json.dumps(q)


def test_pipeline_upload_mode_skips_esmfold(monkeypatch):
    calls = []
    result = _run(monkeypatch, pdb_content=build_pdb(12, b=95.0),
                  esmfold_calls=calls)
    assert result["status"] == "success", result.get("message")
    assert calls == []  # uploaded structure → no prediction
    s1 = result["stage1"]
    assert s1["mode"] == "upload"
    assert s1["sequence_length"] == 12
    q = s1["quality"]
    assert q["plddt_source"] == "prediction"
    assert q["verdict"] == "good"
    json.dumps(q)


def test_pipeline_quality_failure_never_kills_run(monkeypatch):
    import primerforge.pipelines.consensus_pipeline as cp

    result = _run(monkeypatch)  # stubs in place
    assert result["status"] == "success"

    def boom(*_args, **_kwargs):
        raise RuntimeError("analyzer exploded")

    monkeypatch.setattr(cp, "analyze_protein", boom)
    result = _run(monkeypatch)
    assert result["status"] == "success", result.get("message")
    assert result["stage1"]["quality"]["verdict"] == "unknown"
    assert "analyzer exploded" in result["stage1"]["quality"]["error"]
    # warn-allow: stages 2/3 ran anyway
    assert result["stage2"]["successful"] == 1
    assert result["ranked_results"]


# ══════════════════════════════════════════════════════════════════════════
# 6. Route pre-validation (≥10 CA residues before anything is queued)
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def env(monkeypatch, tmp_path):
    """Fresh app whose create_job is a capture stub (no queue/DB writes)."""
    from primerforge.primer_server import create_app

    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("PRIMERFORGE_DB", str(tmp_path / "pv.db"))
    monkeypatch.delenv("REDIS_URL", raising=False)
    import primerforge.security as security

    monkeypatch.setattr(security, "init_admin_rbac", lambda application: None)

    import primerforge.docking_queue as dq

    captured: dict = {}

    def fake_create(sequence, ligand_smiles_list, top_n=50, pdb_content="", box=None):
        captured.update(sequence=sequence, ligands=list(ligand_smiles_list),
                        top_n=top_n, pdb_content=pdb_content)
        return "pvfakejobid"

    monkeypatch.setattr(dq, "create_job", fake_create)

    application = create_app()
    app = application.wsgi_app if hasattr(application, "wsgi_app") else application
    return app.test_client(), captured


def _post(client, body):
    return client.post("/api/primer/docking/consensus",
                       data=json.dumps(body),
                       headers={"Content-Type": "application/json"})


def test_route_rejects_structure_with_too_few_ca(env):
    client, captured = env
    # 1 residue with a CA → 400, nothing queued, no credit consumed
    r = _post(client, {"sequence": "", "ligand_smiles_list": ["CCO"],
                       "pdb_content": build_pdb(1)})
    assert r.status_code == 400, r.get_json()
    assert "CA" in r.get_json()["error"]
    # 0 CA (ligand-only ATOM records) → 400
    ligand = ("ATOM      1  C   LIG A   1       0.000   0.000   0.000"
              "  1.00  0.00           C\n")
    r = _post(client, {"sequence": "", "ligand_smiles_list": ["CCO"],
                       "pdb_content": ligand})
    assert r.status_code == 400, r.get_json()
    assert "CA" in r.get_json()["error"]
    assert not captured  # create_job never invoked


def test_route_accepts_structure_with_ten_ca(env):
    client, captured = env
    r = _post(client, {"sequence": "", "ligand_smiles_list": ["CCO"],
                       "pdb_content": build_pdb(12)})
    assert r.status_code == 202, r.get_json()
    assert captured["pdb_content"]
    assert len(captured["ligands"]) == 1

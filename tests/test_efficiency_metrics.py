"""
Release 4 — Phase 3+5 (tasks 5.1 + 5.2 + data source for 3.3):
post-run efficiency metrics + interaction analysis (`_attach_metrics`).

Covers:
 1. Per-ligand efficiency uses EACH ligand's own SMILES (heavy atoms / MW /
    BEI per ligand; smaller ligand → higher LE at equal energy) — the screen
    call's placeholder-SMILES fields are overwritten.
 2. Screen report: score clusters, rmsd_to_best score-proxy, pLDDT-weighted
    confidence (factor 1.0 at pLDDT ≥ 70, penalised below 50).
 3. Honest regenerated summary (corrected top-ligand LE, never the
    placeholder-25-heavy-atom number) + recommendations + plddt_used.
 4. Interactions: counts on EVERY ranked ligand, residue list capped, full
    (capped) detail only for the top _INTERACTION_DETAIL_TOP ranks;
    oversized analyzer output is sliced to the JSON caps.
 5. Warn-allow contract: empty ranked / short receptor / raising analyzer
    never raises — and one metrics section failing never blocks the other.
 6. End-to-end through run_consensus_pipeline (stubbed engines): efficiency
    + interactions actually attached on the real success path.
"""

import pytest

from tests.test_docking_pocket_phase2 import _run, build_pdb

from primerforge.pipelines.consensus_pipeline import (
    _INTERACTION_DETAIL_TOP,
    _INTERACTION_LIST_CAPS,
    _INTERACTION_RESIDUE_CAP,
    _attach_metrics,
)

# Real ethanol SDF (3 atoms; C1 sits exactly on the receptor ALA1 CA → a
# deterministic hydrophobic contact under HYDROPHOBIC_DIST = 4.5 Å).
LIG_SDF = (
    "ethanol\n"
    "  Vigyan\n"
    "\n"
    "  3  2  0  0  0  0  0  0  0  0999 V2000\n"
    "    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n"
    "    1.5000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n"
    "    2.1000    1.3000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0\n"
    "  1  2  1  0  0  0  0\n"
    "  2  3  1  0  0  0  0\n"
    "M  END\n"
    "$$$$"
)

RECEPTOR = build_pdb(12, b=95.0)   # poly-ALA; CA of res-1 at the origin


def _res(*ligands, plddt=88.0):
    """A success-path result shaped like run_consensus_pipeline's return."""
    ranked = []
    for i, (smiles, score) in enumerate(ligands):
        ranked.append({
            "smiles": smiles,
            "vina_score": score,
            "gnina_score": (score - 1.0) if i == 0 else None,
            "consensus_score": score,
            "consensus_rank": i + 1,
            "structure": {"ligand": LIG_SDF},
        })
    return {
        "status": "success",
        "stage1": {"plddt_score": plddt, "mode": "esmfold",
                   "pdb_string": RECEPTOR},
        "ranked_results": ranked,
    }


# ══════════════════════════════════════════════════════════════════════════
# 5.1 — per-ligand efficiency (own SMILES) + screen report
# ══════════════════════════════════════════════════════════════════════════

def test_per_ligand_efficiency_uses_own_smiles():
    # 6 heavy atoms vs 12 at identical energy (the module floors the count
    # at max(count, 5) — 6+ keeps the per-ligand signal clearly above it,
    # and both differ from the screen call's 25-HA placeholder)
    result = _res(("CCCCCO", -6.0), ("CCCCCCCCCCCC", -6.0))
    _attach_metrics(result, RECEPTOR)
    e1 = result["ranked_results"][0]["efficiency"]
    e2 = result["ranked_results"][1]["efficiency"]

    assert e1["heavy_atoms"] == 6          # own SMILES — NOT the 25-HA
    assert e2["heavy_atoms"] == 12         # placeholder of the screen call
    assert e1["le"] > e2["le"] > 0         # |E|/N — smaller ligand wins
    assert e1["bei"] > e2["bei"] > 0       # |E|*1000/MW
    assert e1["mw"] < e2["mw"]
    for key in ("lle", "confidence_weighted", "cluster", "cluster_rep",
                "rmsd_to_best"):
        assert key in e1 and key in e2


def test_screen_clusters_rmsd_and_confidence():
    result = _res(("CCCCCO", -6.4), ("CCCCCCCCCCCC", -6.0))   # 0.4 kcal/mol apart
    _attach_metrics(result, RECEPTOR)
    eff = result["efficiency"]

    # report_to_dict's own key name is heavy_atom_count
    assert [p["heavy_atom_count"] for p in eff["poses"]] == [6, 12]
    # near-identical scores → one score-proxy cluster of both members
    assert len(eff["clusters"]) == 1
    assert eff["clusters"][0]["member_count"] == 2
    e1 = result["ranked_results"][0]["efficiency"]
    e2 = result["ranked_results"][1]["efficiency"]
    assert e1["cluster"] == e2["cluster"]
    assert e1["cluster_rep"] is True and e2["cluster_rep"] is False
    # rmsd_to_best score-proxy: rank 1 = 0, rank 2 = |Δscore| * 0.5
    assert e1["rmsd_to_best"] == 0.0
    assert e2["rmsd_to_best"] == pytest.approx(0.2)
    # pLDDT 88 (≥70) → confidence factor 1.0 → weighted == raw score
    assert eff["poses"][0]["confidence_weighted_score"] == pytest.approx(-6.4)


def test_low_plddt_penalises_confidence_weighted(monkeypatch):
    import primerforge.pipelines.consensus_pipeline as cp

    result = _res(("CCO", -6.0), plddt=40)
    _attach_metrics(result, RECEPTOR)
    eff = result["efficiency"]
    # factor = 0.3 + 0.4*40/50 = 0.62 → -6.0 * 0.62 = -3.72 (penalised)
    assert eff["poses"][0]["confidence_weighted_score"] == pytest.approx(-3.72)
    assert eff["plddt_used"] == 40.0
    # honest warning surfaced in recommendations
    assert any("pLDDT" in r for r in eff["recommendations"])
    # high pLDDT → no penalty, no pLDDT warning
    ok = _res(("CCO", -6.0), plddt=88)
    _attach_metrics(ok, RECEPTOR)
    assert ok["efficiency"]["poses"][0]["confidence_weighted_score"] == \
        pytest.approx(-6.0)
    assert not any("pLDDT is low" in r for r in
                   ok["efficiency"]["recommendations"])


def test_honest_summary_never_uses_placeholder_le():
    result = _res(("CCCCCO", -6.4), ("CCCCCCCCCCCC", -6.0), plddt=40)
    _attach_metrics(result, RECEPTOR)
    summary = result["efficiency"]["summary"]

    # top ligand LE = 6.4/6 = 1.067 — the screen call's placeholder (25 HA)
    # would have said 0.256
    assert "top LE 1.067/heavy atom" in summary
    assert "0.256" not in summary
    assert "2 ranked ligands" in summary and "kcal/mol" in summary
    assert any("ligand efficiency" in r for r in
               result["efficiency"]["recommendations"])


# ══════════════════════════════════════════════════════════════════════════
# 5.2 / 3.3 data — interaction counts, detail gating, JSON caps
# ══════════════════════════════════════════════════════════════════════════

def test_interactions_counts_for_all_detail_top_only():
    n = _INTERACTION_DETAIL_TOP + 2
    result = _res(*[("CCO", -5.0 - 0.1 * i) for i in range(n)])
    _attach_metrics(result, RECEPTOR)

    for i, cand in enumerate(result["ranked_results"]):
        inter = cand["interactions"]
        # counts on EVERY rank (results-table summary, task 5.2)
        assert inter["counts"]["total_interactions"] >= 1   # real CA–C contact
        assert {"hydrogen_bonds", "hydrophobic_contacts", "salt_bridges",
                "pi_stacking"} <= set(inter["counts"])
        assert len(inter["residues"]) <= _INTERACTION_RESIDUE_CAP
        if i < _INTERACTION_DETAIL_TOP:
            assert set(inter["detail"]) == set(_INTERACTION_LIST_CAPS)
            for key, cap in _INTERACTION_LIST_CAPS.items():
                assert len(inter["detail"][key]) <= cap
            assert inter["recommendation"]
        else:
            # bounded job JSON: no detail / recommendation past the top
            assert "detail" not in inter
            assert "recommendation" not in inter
    # the real contact is in the top ligand's detail list
    assert result["ranked_results"][0]["interactions"]["detail"][
        "hydrophobic_contacts"]


def test_pdb_format_ligand_analysed_not_dummy():
    """vina-only runs persist the docked pose as PDB (no $$$$ block).

    The analyzer must parse those coordinates — before the fallback it
    returned nothing for PDB input and the analysis silently ran on a
    DUMMY atom at the origin, reporting ZERO contacts for every
    non-GNINA pose (both `_attach_metrics` and the client's on-demand
    POST go through this function).
    """
    from primerforge.pipelines.interaction_analyzer import (
        analyze_interactions,
        report_to_dict,
    )
    from tests.test_docking_pocket_phase2 import _het

    # ligand carbon exactly on ALA1 CA (origin) → deterministic contact
    lig_pdb = "\n".join([
        _het(1, "C1", "LIG", "A", 1, 0.0, 0.0, 0.0, "C"),
        _het(2, "C2", "LIG", "A", 1, 1.5, 0.0, 0.0, "C"),
        _het(3, "O1", "LIG", "A", 1, 2.1, 1.3, 0.0, "O"),
        "END",
    ])
    assert lig_pdb.lstrip().startswith("HETATM")   # PDB, no $$$$ marker

    d = report_to_dict(analyze_interactions(RECEPTOR, ligand_sdf=lig_pdb))
    # real coords detected (old path: DUMMY name fails the ligand-carbon
    # filter → total_interactions == 0)
    assert d["summary"]["total_interactions"] >= 1
    assert d["hydrophobic_contacts"], "real ligand carbons must be detected"
    assert d["hydrophobic_contacts"][0]["ligand_atom"].startswith("C")


def test_interaction_output_capped_on_overflow(monkeypatch):
    """Oversized analyzer output is sliced to the JSON caps."""
    import primerforge.pipelines.consensus_pipeline as cp
    from primerforge.pipelines.interaction_analyzer import (
        BindingSiteResidue,
        Interaction,
        InteractionReport,
    )

    big = InteractionReport(
        hydrogen_bonds=[Interaction("hbond", f"A:{i} ASP", "OD1", "N1",
                                    2.9, "strong") for i in range(50)],
        hydrophobic_contacts=[Interaction("hydrophobic", f"A:{i} LEU",
                                          "CD1", "C1", 3.8, "moderate")
                              for i in range(50)],
        salt_bridges=[Interaction("salt_bridge", f"A:{i} ARG", "NH1", "O1",
                                  3.2, "strong") for i in range(50)],
        pi_stacking=[Interaction("pi_stack", f"A:{i} PHE", "CZ", "C1",
                                 4.8, "weak") for i in range(50)],
        binding_site_residues=[BindingSiteResidue("A", i + 1, "ASP",
                                                  5, [], "hbond_partner")
                               for i in range(30)],
        interaction_summary={"total_interactions": 200,
                             "hydrogen_bonds": 50,
                             "hydrophobic_contacts": 50,
                             "salt_bridges": 50,
                             "pi_stacking": 50,
                             "binding_site_residues": 30,
                             "strong_interactions": 100,
                             "unique_receptor_residues": 30},
        recommendation="x")
    monkeypatch.setattr(cp, "analyze_interactions",
                        lambda *a, **k: big)

    result = _res(("CCO", -6.0))
    _attach_metrics(result, RECEPTOR)
    inter = result["ranked_results"][0]["interactions"]
    assert len(inter["detail"]["hydrogen_bonds"]) == 12
    assert len(inter["detail"]["hydrophobic_contacts"]) == 12
    assert len(inter["detail"]["salt_bridges"]) == 8
    assert len(inter["detail"]["pi_stacking"]) == 8
    assert len(inter["residues"]) == _INTERACTION_RESIDUE_CAP
    # counts pass through unsliced (numbers, not lists)
    assert inter["counts"]["total_interactions"] == 200


# ══════════════════════════════════════════════════════════════════════════
# Warn-allow contract
# ══════════════════════════════════════════════════════════════════════════

def test_warn_allow_never_raises(monkeypatch):
    import primerforge.pipelines.consensus_pipeline as cp

    orig_interactions = cp.analyze_interactions

    # empty ranked → strict no-op
    empty = {"status": "success", "ranked_results": []}
    _attach_metrics(empty, RECEPTOR)
    assert "efficiency" not in empty

    # too-short receptor → efficiency still attached, interactions skipped
    short = _res(("CCO", -6.0))
    _attach_metrics(short, "x")
    assert "efficiency" in short
    assert "interactions" not in short["ranked_results"][0]

    # raising interaction analyzer → efficiency survives, no raise
    def boom(*_a, **_k):
        raise RuntimeError("analyzer exploded")
    monkeypatch.setattr(cp, "analyze_interactions", boom)
    result = _res(("CCO", -6.0))
    _attach_metrics(result, RECEPTOR)
    assert "efficiency" in result
    assert "interactions" not in result["ranked_results"][0]

    # raising scoring analyzer → interactions still attached, no raise
    # (interactions analyzer restored: only scoring fails here)
    monkeypatch.setattr(cp, "analyze_interactions", orig_interactions)
    monkeypatch.setattr(cp, "analyze_poses", boom)
    result = _res(("CCO", -6.0))
    _attach_metrics(result, RECEPTOR)
    assert "efficiency" not in result
    assert "interactions" in result["ranked_results"][0]

    # absent (None) analyzers → no-op
    monkeypatch.setattr(cp, "analyze_poses", None)
    _attach_metrics(_res(("CCO", -6.0)), RECEPTOR)   # must not raise


def test_missing_structure_skips_only_interactions():
    result = _res(("CCO", -6.0))
    del result["ranked_results"][0]["structure"]
    _attach_metrics(result, RECEPTOR)
    assert "efficiency" in result
    assert "interactions" not in result["ranked_results"][0]


# ══════════════════════════════════════════════════════════════════════════
# End-to-end: the pipeline's real success path attaches both
# ══════════════════════════════════════════════════════════════════════════

def test_pipeline_end_to_end_attaches_metrics(monkeypatch):
    result = _run(monkeypatch)                       # stubbed engines, CCO
    assert result["status"] == "success", result.get("message")

    # 5.1 screen report on the result
    assert "efficiency" in result
    assert result["efficiency"]["summary"]

    top = result["ranked_results"][0]
    # CCO = 3 heavy atoms, floored to 5 by the module's max(count, 5) —
    # still proves OWN-SMILES wiring (the screen placeholder would say 25)
    assert top["efficiency"]["heavy_atoms"] == 5
    assert top["efficiency"]["le"] > 0

    # 5.2 interaction summary on the ranked entry (fake ligand is a PDB
    # string → the analyzer's honest dummy path; counts still attached)
    inter = top["interactions"]
    assert inter["counts"]["total_interactions"] >= 0
    assert "detail" in inter                          # rank 1 ≤ detail top

"""
VigyanLLM — Consensus Pipeline Orchestrator
Professional 3-stage drug discovery workflow:
  Stage 1: ESMFold    — Predict 3D protein structure (local, MIT)
  Stage 2: AutoDock Vina — Fast physics screening of all ligands (local, Apache 2.0)
  Stage 3: GNINA     — CNN deep-learning re-scoring of top hits (local, Apache/GPL-subprocess)
"""

import asyncio
import logging
import os
import tempfile
import time
from typing import Any

logger = logging.getLogger(__name__)

# ── Import engines ────────────────────────────────────────────────────────────
try:
    from primerforge.pipelines.esmfold_engine import predict_structure as esmfold_predict
except ImportError:
    esmfold_predict = None
    logger.warning("ESMFold engine not available.")

try:
    from primerforge.pipelines.docking_engine import (
        binary_spawn_error,
        box_from_residues,
        compute_box_center_from_pdb,
        gnina_available,
        human_binary_error,
        run_gnina_docking,
        run_vina_docking,
    )
except ImportError:
    run_vina_docking = None
    run_gnina_docking = None
    box_from_residues = None
    compute_box_center_from_pdb = None
    gnina_available = None
    binary_spawn_error = None
    human_binary_error = None
    logger.warning("Docking engine not available.")

# GNINA's CNN re-scoring is the slowest step on CPU — only the top-K Vina
# hits get refined; the rest are ranked on Vina-only consensus (see stage 3).
GNINA_REFINE_TOP_K = 10
# Stage-2 Vina screening search depth for LARGE library screens (the queue
# mirrors these in its job-budget formula — see docking_queue). Small runs
# (≤10 ligands) use STAGE2_EXHAUSTIVENESS_SMALL instead — see
# _stage2_exhaustiveness().
STAGE2_EXHAUSTIVENESS = 2
STAGE2_EXHAUSTIVENESS_SMALL = 8
# Stage-3 GNINA redock search depth (was a magic 4 at the old call site).
STAGE3_GNINA_EXHAUSTIVENESS = 4

# ── Stage-1 structure quality (Phase 4 — "broken or perfect") ────────────────
# stdlib-only module; its import failure must never take the pipeline down.
try:
    from primerforge.pipelines.broken_protein_analyzer import (
        analyze_protein,
        count_ca_residues as _count_ca_residues,
        extract_per_residue_plddt as _extract_plddt,
        report_to_dict as _quality_report_dict,
    )
    _QUALITY_IMPORT_ERROR: str | None = None
except Exception as _qimp:  # pragma: no cover - analyzer is stdlib-only
    analyze_protein = None
    _count_ca_residues = None
    _extract_plddt = None
    _quality_report_dict = None
    _QUALITY_IMPORT_ERROR = str(_qimp)


def _confidence_source(pdb_string: str, mode: str, esmfold_mean: Any) -> tuple[Any, str]:
    """Decide what per-residue confidence to feed the quality analyzer.

    Returns (scores, source):
      "esmfold"          — we produced this structure; the B-factor column IS
                           pLDDT (scale-aware). If the column has no data
                           (helical fallback writes 0.00) the honest stage-1
                           plddt_score is fed as a uniform list instead of
                           the analyzer's neutral default.
      "prediction"       — uploaded file with prediction headers (or no
                           experimental records): B-factor column read as pLDDT.
      "b_factor_estimate"- uploaded experimental structure (CRYST1/EXPDTA):
                           B is a displacement factor — scores=None and the
                           analyzer's documented 100-B/2 estimate applies.
      "unavailable"      — no confidence data anywhere: neutral default,
                           never fabricated numbers.
    """
    if analyze_protein is None:
        return None, "unavailable"
    if mode == "esmfold":
        scores = _extract_plddt(pdb_string)
        if scores is not None:
            return scores, "esmfold"
        mean = esmfold_mean if isinstance(esmfold_mean, (int, float)) else 70
        n_res = _count_ca_residues(pdb_string)
        return [float(mean)] * max(1, n_res), "esmfold"
    # Uploaded structure
    head = pdb_string[:65536].upper()
    predicted = "ALPHAFOLD" in head or "ESMFOLD" in head
    experimental = "CRYST1" in head or "EXPDTA" in head
    scores = _extract_plddt(pdb_string)
    if not predicted and experimental:
        if scores is None:
            return None, "unavailable"
        return None, "b_factor_estimate"
    if scores is None:
        return None, "unavailable"
    return scores, "prediction"


def _quality_verdict(grade: str, mean_plddt: Any, source: str) -> str:
    """Good/usable/poor verdict from the composite grade + confidence floor.

    A/B → good, C → usable, D/F → poor; mean pLDDT < 50 forces poor
    (confidently wrong coordinates are still wrong coordinates).
    """
    verdict = {"A": "good", "B": "good", "C": "usable",
               "D": "poor", "F": "poor"}.get(grade, "usable")
    if (source != "unavailable" and isinstance(mean_plddt, (int, float))
            and mean_plddt < 50):
        return "poor"
    return verdict


def _stage1_quality(pdb_string: str, mode: str, esmfold_mean: Any) -> dict:
    """Run the broken-protein analyzer on the stage-1 receptor.

    Warn-allow by design: analyzer problems are recorded in the returned
    dict and the docking run ALWAYS proceeds (never raises).
    """
    if analyze_protein is None:
        return {"error": f"quality analyzer unavailable: {_QUALITY_IMPORT_ERROR}",
                "verdict": "unknown"}
    try:
        scores, source = _confidence_source(pdb_string, mode, esmfold_mean)
        report = analyze_protein(pdb_string, scores)
        quality = _quality_report_dict(report)
        # Authoritative counts captured BEFORE list truncation below.
        quality["totals"] = {
            "gaps": len(quality.get("missing_residues") or []),
            "clashes": len(quality.get("clashes") or []),
            "ramachandran_outliers": len(quality.get("ramachandran_outliers") or []),
            "defects": len(quality.get("defects") or []),
        }
        # Oversized lists capped so a pathological structure can't bloat the
        # job JSON — the counts in defect_count/summary stay authoritative.
        truncated = False
        for key, cap in (("defects", 40), ("clashes", 20),
                         ("ramachandran_outliers", 20), ("missing_residues", 20)):
            items = quality.get(key) or []
            if len(items) > cap:
                quality[key] = items[:cap]
                truncated = True
        if truncated:
            quality["truncated"] = True
        mean_plddt = (quality.get("plddt") or {}).get("mean")
        quality["plddt_source"] = source
        quality["verdict"] = _quality_verdict(
            quality.get("quality_grade"), mean_plddt, source)
        quality["indicative_only"] = (
            quality["verdict"] == "poor"
            or (source != "unavailable" and isinstance(mean_plddt, (int, float))
                and mean_plddt < 50)
        )
        # Repair only what regenerative folding can actually fix
        # (missing loops + steric clashes).
        quality["repair_suggested"] = bool(quality.get("missing_residues")) or bool(
            quality.get("clashes"))
        return quality
    except Exception as exc:
        logger.warning("Stage-1 quality analysis failed (run proceeds): %s",
                       exc, exc_info=True)
        return {"error": str(exc), "verdict": "unknown"}


# ── Phase 2: real docking — pocket-centered box + receptor preparation ───────
# Neither dependency may ever take the pipeline down (warn-allow, like quality).

try:
    from primerforge.pipelines.pocket_detector import detect_pockets
    _POCKET_IMPORT_ERROR: str | None = None
except Exception as _pimp:  # pragma: no cover - numpy always present in practice
    detect_pockets = None
    _POCKET_IMPORT_ERROR = str(_pimp)

try:
    from primerforge.pipelines.protein_preparer import (
        prepare_protein,
        report_to_dict as _prep_report_dict,
    )
    _PREP_IMPORT_ERROR: str | None = None
except Exception as _prepimp:  # pragma: no cover
    prepare_protein = None
    _prep_report_dict = None
    _PREP_IMPORT_ERROR = str(_prepimp)

# ── Release 4 (Phase 3+5): efficiency metrics + interaction analysis ────────
# Pure-Python modules; guarded like the rest — their absence must never fail
# a run (metrics are post-success decoration, warn-allow by contract).
try:
    from primerforge.pipelines.advanced_scoring import (
        analyze_poses,
        report_to_dict as _advanced_report_dict,
    )
    _SCORING_IMPORT_ERROR: str | None = None
except Exception as _simp:  # pragma: no cover
    analyze_poses = None
    _advanced_report_dict = None
    _SCORING_IMPORT_ERROR = str(_simp)

try:
    from primerforge.pipelines.interaction_analyzer import (
        analyze_interactions,
        report_to_dict as _interaction_report_dict,
    )
    _INTERACTION_IMPORT_ERROR: str | None = None
except Exception as _iimp:  # pragma: no cover
    analyze_interactions = None
    _interaction_report_dict = None
    _INTERACTION_IMPORT_ERROR = str(_iimp)

# Interaction detail is bounded in the job JSON (task 5.3 lesson): the top
# ranked poses carry capped lists for the 3D interaction overlay; every
# ranked ligand still gets counts + pocket residues for the results table,
# and POST /api/primer/docking/interactions gives on-demand detail per rank.
_INTERACTION_DETAIL_TOP = 10
_INTERACTION_LIST_CAPS = {"hydrogen_bonds": 12, "hydrophobic_contacts": 12,
                          "salt_bridges": 8, "pi_stacking": 8}
_INTERACTION_RESIDUE_CAP = 12

# Search-box side limits (Vina volume limit ~27,000 Å³ → 30 Å max per side).
_BOX_MAX_SIDE = 30.0
_BOX_MIN_SIDE = 12.0


def _stage2_exhaustiveness(n_ligands: int) -> int:
    """Honest per-run stage-2 depth: 8 for ≤10-ligand focused runs (a deeper
    search is affordable on tiny libraries), 2 for larger screens. The value
    recorded in stage2.exhaustiveness is whatever actually ran."""
    return STAGE2_EXHAUSTIVENESS_SMALL if n_ligands <= 10 else STAGE2_EXHAUSTIVENESS


def _centroid_box(receptor_pdb: str) -> dict:
    """Whole-protein blind-docking box (fallback when nothing else applies)."""
    if compute_box_center_from_pdb is None:  # docking engine failed to import
        return {"center": [0.0, 0.0, 0.0], "size": [30.0, 30.0, 30.0],
                "source": "protein_centroid"}
    cx, cy, cz, sx, sy, sz = compute_box_center_from_pdb(receptor_pdb)
    return {"center": [round(cx, 3), round(cy, 3), round(cz, 3)],
            "size": [round(sx, 1), round(sy, 1), round(sz, 1)],
            "source": "protein_centroid"}


def _select_box(receptor_pdb: str, manual_box: dict | None) -> tuple[dict, str | None]:
    """Choose the docking search box for stages 2 and 3. Returns (box, note).

    Priority:
      1. manual_box {"center","size"}      → source "manual" (advanced panel)
      2. manual_box {"residues"}           → source "residue_range" (falls
         back to centroid with a note when the range isn't in the structure)
      3. manual_box {"blind": true}        → skip detection, centroid box
      4. auto: top detected pocket         → source "pocket" (pocket-centered,
         size = 2×radius + 4 Å clamped [12, 30])
      5. fallback: whole-protein centroid  → source "protein_centroid"

    Never raises: pocket-detection problems fall back to the centroid.
    """
    if isinstance(manual_box, dict):
        if manual_box.get("center") and manual_box.get("size"):
            try:
                center = [round(float(v), 3) for v in list(manual_box["center"])[:3]]
                size = [max(_BOX_MIN_SIDE, min(round(float(v), 1), _BOX_MAX_SIDE))
                        for v in list(manual_box["size"])[:3]]
                return {"center": center, "size": size, "source": "manual"}, None
            except (TypeError, ValueError, IndexError):
                logger.warning("Malformed manual box override — using auto selection.")
        elif manual_box.get("residues"):
            res = manual_box.get("residues") or {}
            box = None
            try:
                if box_from_residues is not None:
                    box = box_from_residues(
                        receptor_pdb, str(res.get("chain", "")),
                        int(res.get("start")), int(res.get("end")))
            except Exception as exc:
                logger.warning("Residue-range box failed: %s", exc)
            if box:
                return box, None
            return _centroid_box(receptor_pdb), (
                f"Residues {res.get('chain', '?')}:{res.get('start', '?')}-"
                f"{res.get('end', '?')} not found in the structure — fell back "
                "to the whole-protein centroid box.")
        elif manual_box.get("blind"):
            return _centroid_box(receptor_pdb), None

    # Auto: pocket-centered box (task 2.1) — top ranked pocket wins.
    if detect_pockets is not None:
        try:
            pockets = detect_pockets(receptor_pdb)
        except Exception as exc:
            logger.warning("Pocket detection failed (centroid fallback): %s", exc)
            pockets = []
        if pockets:
            p = pockets[0]
            radius = float(p.radius)
            side = max(_BOX_MIN_SIDE, min(2.0 * radius + 4.0, _BOX_MAX_SIDE))
            center = [round(float(v), 3) for v in p.center]
            return {
                "center": center,
                "size": [round(side, 1)] * 3,
                "source": "pocket",
                "pocket_id": int(p.pocket_id),
                "druggability": p.druggability,
                "pocket_score": round(float(p.score), 1),
                "pockets_found": len(pockets),
                # Nested copy the 3D viewer draws as a translucent sphere.
                "pocket": {"id": int(p.pocket_id), "center": center,
                           "radius": round(radius, 2),
                           "score": round(float(p.score), 1),
                           "druggability": p.druggability},
            }, None
        logger.info("No pocket detected — blind docking (whole-protein centroid).")
    else:
        logger.warning("Pocket detector unavailable (%s) — centroid box.",
                       _POCKET_IMPORT_ERROR)
    return _centroid_box(receptor_pdb), None


# protonation_changes is per-residue and can run to hundreds of entries on a
# large protein — bound the job JSON (the UI shows the true count instead).
_PROTONATION_CAP = 20


def _prepare_upload(pdb_content: str) -> tuple[str, dict]:
    """Receptor preparation for uploaded PDBs (task 2.3).

    Removes waters/ions/non-cofactor HETATM and reports exactly what was
    changed. Warn-allow: any failure returns the ORIGINAL structure with the
    error recorded (preparation must never block a run).
    """
    if prepare_protein is None:
        return pdb_content, {"performed": False,
                             "error": f"preparer unavailable: {_PREP_IMPORT_ERROR}"}
    try:
        report = prepare_protein(pdb_content)
        prep = _prep_report_dict(report)
        prep.pop("prepared_pdb", "")  # structure itself is the return value
        prepared = report.prepared_pdb or pdb_content
        # Text always differs (atoms are re-sorted) — "changed" means atoms
        # were actually removed/added, judged from the report counts.
        prep["changed_structure"] = bool(
            prep.get("waters_removed") or prep.get("ions_removed")
            or prep.get("hetatm_removed") or prep.get("hydrogens_added"))
        prep["performed"] = True
        # Cap the per-residue protonation list (job JSON is stored whole);
        # protonation_count always carries the true total for display.
        _pc = prep.get("protonation_changes")
        if isinstance(_pc, list):
            prep["protonation_count"] = len(_pc)
            if len(_pc) > _PROTONATION_CAP:
                prep["protonation_changes"] = _pc[:_PROTONATION_CAP]
                prep["protonation_truncated"] = True
        return prepared, prep
    except Exception as exc:
        logger.warning("Receptor preparation failed (original used): %s",
                       exc, exc_info=True)
        return pdb_content, {"performed": False, "error": str(exc)}


def _attach_metrics(result: dict, receptor_pdb: str) -> None:
    """Release 4 — post-run efficiency (task 5.1) + interactions (5.2/3.3).

    Called only on success paths AFTER ``status = "success"``. Warn-allow by
    contract: any failure here logs a warning and leaves the run successful
    (metrics must never break an otherwise-good result).

    Produces, on every ranked ligand:
      ``efficiency``   {le, lle, bei, heavy_atoms, mw, cluster, cluster_rep,
                        rmsd_to_best (score-proxy), confidence_weighted}
      ``interactions`` {counts, residues[≤12], detail[≤caps, top-10 only],
                        recommendation (top-10 only)}
    plus a screen-level ``result["efficiency"]`` report (clusters,
    binding-mode consistency, honest summary/recommendations).
    """
    ranked = result.get("ranked_results") or []
    if not ranked or analyze_poses is None or _advanced_report_dict is None:
        return

    plddt = (result.get("stage1") or {}).get("plddt_score")
    try:
        plddt = float(plddt) if plddt not in (None, "") else None
    except (TypeError, ValueError):
        plddt = None

    # ── 5.1a — one screen-level analyze_poses() over the ranked set ────────
    # Gives cross-ligand score clustering, rmsd_to_best (the module's
    # documented score-proxy) and pLDDT-weighted confidence. Its LE/LLE/BEI
    # fields assume ONE smiles for all poses, so 5.1b recomputes them per
    # ligand (correct heavy-atom count) and overwrites.
    screen_dict: dict | None = None
    try:
        screen_dict = _advanced_report_dict(analyze_poses(
            [{"score": (c["consensus_score"]
                        if c.get("consensus_score") is not None
                        else (c.get("vina_score") or 0.0)),
              "vina_score": float(c.get("vina_score") or 0.0),
              "gnina_score": float(c.get("gnina_score") or 0.0),
              "consensus_score": float(
                  c["consensus_score"] if c.get("consensus_score") is not None
                  else (c.get("vina_score") or 0.0)),
              "rank": c.get("consensus_rank") or i + 1}
             for i, c in enumerate(ranked)],
            receptor_plddt=plddt, smiles=""))
    except Exception as exc:
        logger.warning("Screen-level efficiency analysis failed: %s", exc)

    # ── 5.1b — per-ligand LE/LLE/BEI (THIS ligand's heavy-atom count) ──────
    top_recommendations: list[str] = []
    if screen_dict:
        screen_poses = screen_dict.get("poses") or []
        for i, cand in enumerate(ranked):
            if i >= len(screen_poses):
                break
            pa = screen_poses[i]          # input order invariant (append)
            try:
                own = analyze_poses(
                    [{"score": pa["score"], "vina_score": pa["vina_score"],
                      "gnina_score": pa["gnina_score"],
                      "consensus_score": pa["consensus_score"], "rank": 1}],
                    receptor_plddt=plddt, smiles=cand.get("smiles") or "")
                op = own.poses[0]
                # Size-dependent fields only — clusters/rmsd/confidence come
                # from the screen call (cross-ligand), not this single pose.
                pa["ligand_efficiency"] = op.ligand_efficiency
                pa["ligand_efficiency_lipe"] = op.ligand_efficiency_lipe
                pa["binding_energy_index"] = op.binding_energy_index
                pa["heavy_atom_count"] = op.heavy_atom_count
                pa["molecular_weight"] = op.molecular_weight
                if i == 0:
                    # Top ligand's own recommendations are honest (correct
                    # LE, pLDDT warning; single-pose so no bogus binding recs)
                    top_recommendations = list(own.recommendations)
            except Exception as exc:
                logger.warning("Efficiency metrics failed for rank %d: %s",
                               i + 1, exc)
            cand["efficiency"] = {
                "le": pa["ligand_efficiency"],
                "lle": pa["ligand_efficiency_lipe"],
                "bei": pa["binding_energy_index"],
                "heavy_atoms": pa["heavy_atom_count"],
                "mw": pa["molecular_weight"],
                "cluster": pa["cluster_id"],
                "cluster_rep": pa["is_cluster_representative"],
                "rmsd_to_best": pa["rmsd_to_best"],
                "confidence_weighted": pa["confidence_weighted_score"],
            }

        # ── 5.1c — honest screen summary/recommendations ──────────────────
        # The screen call's own strings were formatted with placeholder
        # SMILES (25 heavy atoms) — regenerate from corrected metrics.
        try:
            clusters = screen_dict.get("clusters") or []
            top_eff = ranked[0].get("efficiency") or {}
            top_score = (ranked[0].get("consensus_score")
                         if ranked[0].get("consensus_score") is not None
                         else ranked[0].get("vina_score") or 0.0)
            n_lig, n_cl = len(ranked), len(clusters)
            # Machine tokens never render raw in the card subtitle.
            _mode = (screen_dict.get("binding_modes") or {}).get("consistency", "unknown")
            if _mode == "insufficient_poses":
                _mode = "n/a (single pose — no spread to assess)"
            screen_dict["summary"] = (
                f"{n_lig} ranked ligand{'' if n_lig == 1 else 's'} — "
                f"best {float(top_score):.2f} "
                f"kcal/mol, top LE {float(top_eff.get('le') or 0):.3f}/heavy "
                f"atom, {n_cl} score cluster{'' if n_cl == 1 else 's'}, "
                f"binding mode: {_mode}.")
            recs = list(top_recommendations)
            if len(clusters) > 1:
                recs.append(f"Found {len(clusters)} distinct score clusters "
                            "across the ranked set — structurally diverse top hits.")
            if plddt is not None and plddt < 50 and not any(
                    "pLDDT" in r for r in recs):
                recs.append(f"⚠ Receptor pLDDT is low ({plddt:.0f}%) — "
                            "confidence-weighted scores should drive decisions.")
            screen_dict["recommendations"] = recs[:6]
            if plddt is not None:
                screen_dict["plddt_used"] = round(plddt, 1)
            result["efficiency"] = screen_dict
        except Exception as exc:
            logger.warning("Efficiency summary failed: %s", exc)

    # ── 3.3/5.2 — interaction analysis per ranked ligand (bounded JSON) ────
    if not receptor_pdb or len(receptor_pdb) < 50 or analyze_interactions is None:
        return
    for i, cand in enumerate(ranked):
        try:
            sdf = (cand.get("structure") or {}).get("ligand") or ""
            if not sdf:
                continue
            idict = _interaction_report_dict(analyze_interactions(
                receptor_pdb, ligand_sdf=sdf,
                ligand_smiles=cand.get("smiles") or ""))
            site = (idict.get("binding_site_residues")
                    or [])[:_INTERACTION_RESIDUE_CAP]
            entry: dict[str, Any] = {
                "counts": idict.get("summary") or {},
                "residues": [{"residue": r.get("name", "?"),
                              "chain": r.get("chain", "?"),
                              "number": r.get("number"),
                              "contacts": r.get("contact_count", 0),
                              "role": r.get("role")} for r in site],
            }
            if i < _INTERACTION_DETAIL_TOP:
                entry["detail"] = {k: (idict.get(k) or [])[:cap]
                                   for k, cap in _INTERACTION_LIST_CAPS.items()}
                entry["recommendation"] = idict.get("recommendation") or ""
            cand["interactions"] = entry
        except Exception as exc:
            logger.warning("Interaction analysis failed for rank %d: %s",
                           i + 1, exc)


async def run_consensus_pipeline(
    sequence: str,
    ligand_smiles_list: list[str],
    top_n: int = 50,
    progress_callback=None,
    pdb_content: str = "",
    box: dict | None = None,
) -> dict[str, Any]:
    """
    Full 3-stage consensus pipeline.

    Args:
        sequence:           Protein amino acid sequence
        ligand_smiles_list: List of ligand SMILES strings to screen
        top_n:              Number of top Vina hits to pass to GNINA (default 50)
        progress_callback:  Optional async function(stage, message) for live status
        box:                Optional search-box override from the advanced panel:
                            {"center":[x,y,z], "size":[sx,sy,sz]} (manual),
                            {"residues":{"chain","start","end"}} (residue range),
                            or {"blind": true} (force whole-protein centroid).
                            None = auto (pocket detection → centroid fallback).

    Returns:
        {
            best_molecule: {smiles, vina_score, gnina_score, consensus_rank},
            ranked_results: [...],
            stage1: {plddt_score, pdb_string, ...},
            stage2: {screened, top_n_selected, box, exhaustiveness, ...},
            stage3: {refined, ...},
            status: "success"
        }
    """

    # Input validation
    if pdb_content:
        # PDB-upload mode skips structure prediction entirely, so sequence
        # length/charset limits do not apply — the file IS the structure.
        if "ATOM" not in pdb_content:
            return {"status": "error", "message": "Uploaded PDB contains no ATOM records."}
    else:
        if not sequence or len(sequence) < 10:
            return {"status": "error", "message": "Protein sequence must be at least 10 amino acids."}
        valid_aa = set("ACDEFGHIKLMNPQRSTVWY")
        clean_seq = "".join(c for c in sequence.upper() if c.isalpha())
        invalid = set(clean_seq) - valid_aa
        if invalid:
            return {"status": "error", "message": f"Invalid amino acids: {', '.join(sorted(invalid))}. Only standard 20 amino acids accepted."}
        try:
            from .esmfold_engine import MAX_SEQUENCE_LENGTH
        except ImportError:
            MAX_SEQUENCE_LENGTH = 400
        if len(clean_seq) > MAX_SEQUENCE_LENGTH:
            return {"status": "error", "message": (
                f"Sequence too long ({len(clean_seq)} residues) — web structure prediction "
                f"supports up to {MAX_SEQUENCE_LENGTH} amino acids. For longer proteins, "
                "upload the protein PDB file instead (Protein → PDB tab).")}
    if not ligand_smiles_list:
        return {"status": "error", "message": "At least one ligand SMILES required."}
    if len(ligand_smiles_list) > 100:
        return {"status": "error", "message": (
            "Maximum 100 ligands per consensus run. For larger libraries, use "
            "virtual screening (POST /api/primer/docking/screen — up to 500 ligands).")}

    async def _progress(stage: str, msg: str, metadata: dict = None):
        logger.info("[%s] %s", stage, msg)
        if progress_callback:
            await progress_callback(stage, msg, metadata)

    result = {
        "status": "running",
        "stage1": None,
        "stage2": None,
        "stage3": None,
        "ranked_results": [],
        "best_molecule": None,
    }

    # Shared temp dir for receptor PDBQT (reused across all Vina/GNINA calls)
    import shutil
    _receptor_pdbqt_dir = tempfile.mkdtemp(prefix="receptor_pdbqt_")
    try:
        return await _run_pipeline_inner(sequence, ligand_smiles_list, top_n, _receptor_pdbqt_dir, _progress, result, pdb_content=pdb_content, box=box)
    finally:
        shutil.rmtree(_receptor_pdbqt_dir, ignore_errors=True)


async def _run_pipeline_inner(
    sequence: str,
    ligand_smiles_list: list[str],
    top_n: int,
    _receptor_pdbqt_dir: str,
    _progress,
    result: dict,
    pdb_content: str = "",
    box: dict | None = None,
) -> dict[str, Any]:

    _receptor_pdbqt_path = os.path.join(_receptor_pdbqt_dir, "receptor.pdbqt")

    # ══════════════════════════════════════════════════════════════════════════
    # STAGE 1: ESMFold — Predict Protein 3D Structure (or use uploaded PDB)
    # ══════════════════════════════════════════════════════════════════════════
    if pdb_content:
        # User uploaded a PDB file — skip ESMFold, use provided structure
        await _progress("STAGE 1 / PDB", "Using uploaded PDB structure (ESMFold skipped)...")
        receptor_pdb = pdb_content
        # Count residues from ATOM records
        residue_count = 0
        last_res = ""
        for line in pdb_content.split("\n"):
            if line.startswith("ATOM") and line[12:16].strip() == "CA":
                res_num = line[22:26].strip()
                if res_num != last_res:
                    last_res = res_num
                    residue_count += 1
        result["stage1"] = {
            "pdb_string": pdb_content,
            "sequence_length": residue_count or len(sequence),
            "plddt_score": None,
            "mode": "upload",
            "tool": "User-uploaded PDB",
            "message": f"Using uploaded PDB structure ({residue_count} residues). ESMFold prediction skipped.",
            "computation_time": "0.0s"
        }
        await _progress("STAGE 1 / PDB", f"✅ Loaded uploaded structure — {residue_count} residues")
    else:
        # No PDB uploaded — run ESMFold
        if not esmfold_predict:
            return {**result, "status": "error", "message": "ESMFold engine not loaded. Install: pip install transformers einops"}

        try:
            from primerforge.pipelines.esmfold_engine import _local_gpu_available
            if _local_gpu_available():
                device = "GPU (local ESMFold)"
                mode_str = "Mode: Local ESMFold on GPU"
            else:
                device = "ESMFold web API"
                mode_str = "Mode: ESMFold web API (host has no GPU — remote inference)"
        except Exception:
            device = "ESMFold web API"
            mode_str = "Mode: ESMFold web API (remote inference)"

        await _progress("PIPELINE", f"Initializing Consensus Discovery Suite on {device}...")
        await _progress("STAGE 1 / ESMFold", f"Commencing structural folding for sequence (Length: {len(sequence)}aa, {mode_str})...")

        try:
            stage1_result = await esmfold_predict(sequence, progress_callback=_progress)
            result["stage1"] = stage1_result
            result["stage1"]["mode"] = "esmfold"
            receptor_pdb = stage1_result["pdb_string"]
            score = stage1_result.get('plddt_score', 0)
            await _progress("STAGE 1 / ESMFold", f"✅ Structure predicted — pLDDT: {score}%")
        except Exception as e:
            return {**result, "status": "error", "message": f"Stage 1 (ESMFold) failed: {e!s}"}

    # ── Stage-1 quality validation (Phase 4 — broken or perfect) ────────────
    # Every structure (predicted or uploaded) is analyzed. NEVER fatal:
    # analyzer failures are recorded and the run proceeds (warn, allow).
    result["stage1"]["quality"] = _stage1_quality(
        receptor_pdb,
        result["stage1"].get("mode", "esmfold"),
        result["stage1"].get("plddt_score"),
    )
    _q = result["stage1"]["quality"]
    if _q.get("error"):
        await _progress("STAGE 1 / QUALITY",
                        f"⚠ Structure quality check unavailable: {_q['error']}")
    else:
        await _progress(
            "STAGE 1 / QUALITY",
            f"Structure quality: {str(_q.get('verdict', 'unknown')).upper()} "
            f"({_q.get('quality_score')}/100, grade {_q.get('quality_grade')})")

    # ── Receptor preparation (Phase 2, task 2.3): PDB uploads only ─────────
    # Quality ran on the ORIGINAL file first — preparation rebuilds the
    # record list (and would drop CRYST1/EXPDTA headers, breaking confidence
    # source classification). Preparation feeds docking + pocket detection.
    if pdb_content:
        receptor_pdb, result["stage1"]["preparation"] = _prepare_upload(pdb_content)
        _prep = result["stage1"]["preparation"]
        if _prep.get("error"):
            await _progress("STAGE 1 / PREP",
                            f"⚠ Structure preparation unavailable: {_prep['error']}")
        elif _prep.get("changed_structure"):
            await _progress(
                "STAGE 1 / PREP",
                f"Structure prepared — removed {_prep.get('waters_removed', 0)} waters, "
                f"{_prep.get('ions_removed', 0)} ions, "
                f"{len(_prep.get('hetatm_removed') or [])} heteroatoms "
                f"({_prep.get('protonation_count', len(_prep.get('protonation_changes') or []))} protonation states noted).")
        else:
            await _progress("STAGE 1 / PREP",
                            "Structure already clean — nothing removed.")

    # ── Search-box selection (Phase 2, task 2.1) ───────────────────────────
    # Pocket-centered by default; manual/residue/blind overrides from the
    # advanced panel win over detection. One box serves stages 2 AND 3.
    dock_box, box_note = _select_box(receptor_pdb, box)
    if dock_box.get("source") == "pocket":
        await _progress(
            "STAGE 2 / BOX",
            f"Binding pocket #{dock_box['pocket_id']} detected "
            f"(score {dock_box['pocket_score']}, {dock_box['druggability']} druggability) — "
            f"box {dock_box['size'][0]:.0f}×{dock_box['size'][1]:.0f}×{dock_box['size'][2]:.0f} Å "
            "centered on the pocket.")
    else:
        _box_labels = {"manual": "Manual override box",
                       "residue_range": "Residue-range box",
                       "protein_centroid": "Blind docking (whole-protein centroid)"}
        await _progress(
            "STAGE 2 / BOX",
            f"{_box_labels.get(dock_box.get('source'), 'Search box')} "
            f"{dock_box['size'][0]:.0f}×{dock_box['size'][1]:.0f}×{dock_box['size'][2]:.0f} Å.")
    if box_note:
        await _progress("STAGE 2 / BOX", f"⚠ {box_note}")

    await _progress("PIPELINE", "─── STAGE 2 INITIATED: BROAD SCREENING ───")
    # ══════════════════════════════════════════════════════════════════════════
    # STAGE 2: AutoDock Vina — Fast Broad Screening
    # ══════════════════════════════════════════════════════════════════════════
    await _progress("STAGE 2 / Vina", f"Screening {len(ligand_smiles_list)} ligands with AutoDock Vina...")

    if not run_vina_docking:
        return {**result, "status": "error", "message": "AutoDock Vina engine not loaded."}

    # Honest per-run depth: deeper search for ≤10-ligand focused runs
    # (recorded in stage2.exhaustiveness — what actually ran).
    exh2 = _stage2_exhaustiveness(len(ligand_smiles_list))

    # Pre-convert receptor PDB→PDBQT ONCE for all ligands
    from .docking_engine import pdb_to_pdbqt
    if not pdb_to_pdbqt(receptor_pdb, _receptor_pdbqt_path):
        return {**result, "status": "error", "message": "Failed to convert receptor PDB to PDBQT."}

    vina_results = []
    failed = 0
    total_ligands = len(ligand_smiles_list)

    # Parallelism sized for the production box (2 vCPU): two concurrent Vina
    # processes × (--cpu = cores/2 threads each) saturates the CPUs without
    # oversubscription. Each Vina/obabel child is its own OS process (own
    # RLIMIT_AS), so memory stays bounded; on a 1-core host this degrades to
    # the old serial behavior automatically.
    _cores = os.cpu_count() or 1
    vina_parallelism = min(2, _cores)
    cpu_per_vina = max(1, _cores // vina_parallelism)
    semaphore = asyncio.Semaphore(vina_parallelism)

    async def screen_ligand(smiles: str, idx: int):
        nonlocal failed
        async with semaphore:
            try:
                if idx % 5 == 0 or idx == total_ligands - 1:
                    await _progress("STAGE 2 / Vina", f"Screening ligand {idx+1}/{total_ligands}...", {"current": idx+1, "total": total_ligands})

                docking_result = await run_vina_docking(
                    receptor_pdb, smiles, exhaustiveness=exh2,
                    receptor_pdbqt_path=_receptor_pdbqt_path, cpu=cpu_per_vina,
                    box=dock_box)
                return {
                    "smiles": smiles,
                    "vina_score": docking_result.get("binding_affinity"),
                    "vina_time": docking_result.get("computation_time"),
                    "gnina_score": None,
                    "consensus_rank": None,
                    "status": "screened",
                    "structure": docking_result.get("structure"),
                    "box": docking_result.get("box"),
                }
            except Exception as e:
                logger.debug("Vina failed for ligand #%s: %s", idx, e)
                failed += 1
                return None

    t_stage2 = time.time()
    tasks = [screen_ligand(smiles, i) for i, smiles in enumerate(ligand_smiles_list)]
    raw_results = await asyncio.gather(*tasks)
    vina_results = [r for r in raw_results if r is not None]

    # Sort by Vina score ascending (more negative = stronger binding)
    vina_results.sort(key=lambda x: x["vina_score"] if x["vina_score"] is not None else 0)

    # Select top_n for GNINA refinement
    top_candidates = vina_results[:top_n]

    result["stage2"] = {
        "screened": len(ligand_smiles_list),
        "successful": len(vina_results),
        "failed": failed,
        "top_n_selected": len(top_candidates),
        "best_vina_score": top_candidates[0]["vina_score"] if top_candidates else None,
        # Honest run parameters (surfaced in the results UI): what actually ran.
        "exhaustiveness": exh2,
        "computation_time": f"{time.time() - t_stage2:.1f}s",
        # Box actually used (pocket/manual/residue/blind) — selected once for
        # the whole run and shared with stage 3.
        "box": dock_box,
        **({"box_note": box_note} if box_note else {}),
    }
    await _progress("STAGE 2 / Vina", f"✅ Screening complete — {len(top_candidates)} top candidates selected for GNINA.", {"current": total_ligands, "total": total_ligands})

    await _progress("PIPELINE", "─── STAGE 3 INITIATED: CNN REFINEMENT ───")
    # ══════════════════════════════════════════════════════════════════════════
    # STAGE 3: GNINA — CNN Deep-Learning Re-Scoring
    # ══════════════════════════════════════════════════════════════════════════
    # CNN re-scoring is the slowest step on CPU — refine only the best K by
    # Vina score (GNINA_REFINE_TOP_K). Remaining candidates keep Vina-only
    # consensus via the g=v fallback below and still get ranked, so output
    # size/top_n semantics are unchanged.
    refine_list = top_candidates[:GNINA_REFINE_TOP_K]
    total_refined = len(refine_list)
    vina_only = len(top_candidates) - total_refined
    await _progress("STAGE 3 / GNINA", f"Re-scoring top {total_refined} of {len(top_candidates)} candidates with GNINA CNN...", {"current": 0, "total": total_refined})

    # Pre-flight probe — the SAME `gnina --version` contract as the prod
    # deploy gate. A binary that exists but can't execute on this host
    # (Linux build on macOS, missing +x, broken install) reads as NOT
    # available: attempt-per-ligand would only burn the job budget
    # re-discovering the same errno, and a red "failed" card would be
    # dishonest — nothing was computed, so nothing failed.
    _gnina_probe = gnina_available() if gnina_available else None
    if not run_gnina_docking or not _gnina_probe or not _gnina_probe["ok"]:
        _skip_reason = (_gnina_probe or {}).get("reason") or (
            "GNINA module not importable on this host.")
        logger.warning("GNINA not available (%s) — returning Vina-only results.",
                       _skip_reason)
        # Honest labelling: no CNN ran, so the "consensus" score IS the plain
        # Vina score (0.4v + 0.6v = v) and every candidate is tagged as such.
        # The UI must not present this as a 2-method consensus.
        for i, candidate in enumerate(top_candidates):
            candidate["consensus_rank"] = i + 1
            candidate["consensus_score"] = round(candidate.get("vina_score") or 0, 3)
            candidate["score_source"] = "vina"
        result["stage3"] = {
            "status": "skipped",
            "reason": _skip_reason,
            "consensus_mode": "vina_only",
            "refined": 0,
            "vina_only": len(top_candidates),
            "best_gnina_score": None,
        }
        result["ranked_results"] = top_candidates
        result["best_molecule"] = top_candidates[0] if top_candidates else None
        result["status"] = "success"
        _attach_metrics(result, receptor_pdb)
        return result

    gnina_semaphore = asyncio.Semaphore(1)  # GNINA is heavier — 1 at a time
    gnina_failures: list[str] = []
    gnina_broken_reason: list[str] = []  # sentinel: first BINARY-level failure

    def _binary_error(e: Exception) -> bool:
        # Shared with docking_engine — the availability probe classifies the
        # same errors BEFORE any ligand is attempted (single source of truth).
        return binary_spawn_error(e)

    def _human_binary_error(e: Exception) -> str:
        return human_binary_error(e)

    async def refine_candidate(candidate: dict, idx: int):
        async with gnina_semaphore:
            if gnina_broken_reason:
                # Fail fast (inside the lock — ordering guarantees the flag is
                # already set by the first failed candidate): the binary itself
                # is unusable, so don't re-attempt for every remaining
                # candidate (prod previously burned tens of subprocess
                # attempts on an executable that could never run).
                candidate["gnina_score"] = None
                candidate["status"] = "gnina_failed"
                return candidate
            try:
                if idx % 2 == 0 or idx == total_refined - 1:
                    await _progress("STAGE 3 / GNINA", f"Refining candidate {idx+1}/{total_refined}...", {"current": idx+1, "total": total_refined})

                gnina_result = await run_gnina_docking(receptor_pdb, candidate["smiles"], exhaustiveness=STAGE3_GNINA_EXHAUSTIVENESS, receptor_pdbqt_path=_receptor_pdbqt_path, box=dock_box)
                candidate["gnina_score"] = gnina_result.get("binding_affinity")
                # Honest CNN fields (2026-10-08): cnn_score = pose confidence
                # 0-1; cnn_affinity = predicted affinity (log mol/L). The
                # legacy `cnn_affinity` key used to carry the pose score.
                candidate["cnn_score"] = gnina_result.get("cnn_score")
                candidate["cnn_affinity"] = gnina_result.get("cnn_affinity")
                candidate["gnina_time"] = gnina_result.get("computation_time")
                candidate["pose_table"] = gnina_result.get("pose_table")
                # Keep the stage-2 (Vina) pose if GNINA didn't return one —
                # structure carries the viewer/interactions ligand (test fakes
                # and partial results must never blank it out).
                candidate["structure"] = (
                    gnina_result.get("structure") or candidate.get("structure"))
                candidate["status"] = "refined"
                return candidate
            except Exception as e:
                # Keep the reason visible in the job result (surfaced via the
                # status API) — previously GNINA failures were logged at DEBUG
                # only and vanished, making prod breakage undiagnosable.
                logger.warning("GNINA failed for candidate: %s", e)
                reason = _human_binary_error(e) if _binary_error(e) else str(e)[:300]
                gnina_failures.append(reason)
                if _binary_error(e) and not gnina_broken_reason:
                    gnina_broken_reason.append(reason)
                    logger.warning("GNINA binary unusable — skipping remaining refinements: %s", e)
                candidate["gnina_score"] = None
                candidate["status"] = "gnina_failed"
                return candidate

    t_stage3 = time.time()
    refined_top = await asyncio.gather(*[refine_candidate(c, i) for i, c in enumerate(refine_list)])
    # Merge refined top-K with Vina-only remainder — one ranked list of size top_n
    refined = list(refined_top) + list(top_candidates[total_refined:])

    # Final consensus ranking:
    # Weighted score = 0.4 * vina_score + 0.6 * gnina_score (both negative, lower = better).
    # Candidates GNINA never saw fall back to g = v, which makes their
    # consensus score EXACTLY the Vina score — ranked honestly below/above
    # genuine 2-method scores, and tagged score_source="vina" so the UI can
    # say which number is which (never present a 1-method score as consensus).
    def consensus_score(c):
        v = c.get("vina_score") or 0
        g = c.get("gnina_score")
        if g is None:
            g = v
        return 0.4 * v + 0.6 * g

    refined.sort(key=consensus_score)

    n_cnn = sum(1 for c in refined_top if c.get("gnina_score") is not None)
    if n_cnn == 0:
        consensus_mode = "vina_only"      # no candidate got a CNN score
    elif n_cnn == len(refined_top) and vina_only == 0:
        consensus_mode = "full"           # every ranked candidate: Vina + CNN
    else:
        consensus_mode = "partial"        # mixed coverage (K-limit or failures)

    for i, candidate in enumerate(refined):
        candidate["consensus_rank"] = i + 1
        candidate["consensus_score"] = round(consensus_score(candidate), 3)
        candidate["score_source"] = (
            "consensus" if candidate.get("gnina_score") is not None else "vina")

    result["stage3"] = {
        "refined": len(refined_top),
        "vina_only": vina_only,
        "best_gnina_score": next(
            (c.get("gnina_score") for c in refined if c.get("gnina_score") is not None), None),
        # Honest run description (surfaced by the results UI):
        "consensus_mode": consensus_mode,
        "cnn_refined": n_cnn,
        "consensus_weights": {"vina": 0.4, "gnina": 0.6},
        "refine_top_k": GNINA_REFINE_TOP_K,
        "gnina_exhaustiveness": STAGE3_GNINA_EXHAUSTIVENESS,
        "cnn_model": "crossdock_default2018",  # single-model (CPU); see docking_engine
        "computation_time": f"{time.time() - t_stage3:.1f}s",
    }
    if gnina_failures:
        # Surface why GNINA re-scoring degraded to Vina-only (visible via the
        # status API so production breakage is diagnosable without SSH).
        result["stage3"]["status"] = "gnina_failed" if all(
            c.get("gnina_score") is None for c in refined) else "partial"
        result["stage3"]["failure_reasons"] = gnina_failures[:5]
    result["ranked_results"] = refined
    result["best_molecule"] = refined[0] if refined else None
    result["status"] = "success"
    _attach_metrics(result, receptor_pdb)

    await _progress("STAGE 3 / GNINA", f"✅ Refinement complete — Best molecule at consensus rank #1: {result['best_molecule']['smiles'][:30]}...")

    return result

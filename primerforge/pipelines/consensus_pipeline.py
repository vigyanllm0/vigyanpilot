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
from typing import Any

logger = logging.getLogger(__name__)

# ── Import engines ────────────────────────────────────────────────────────────
try:
    from primerforge.pipelines.esmfold_engine import predict_structure as esmfold_predict
except ImportError:
    esmfold_predict = None
    logger.warning("ESMFold engine not available.")

try:
    from primerforge.pipelines.docking_engine import run_gnina_docking, run_vina_docking
except ImportError:
    run_vina_docking = None
    run_gnina_docking = None
    logger.warning("Docking engine not available.")


async def run_consensus_pipeline(
    sequence: str,
    ligand_smiles_list: list[str],
    top_n: int = 50,
    progress_callback=None,
    pdb_content: str = ""
) -> dict[str, Any]:
    """
    Full 3-stage consensus pipeline.

    Args:
        sequence:           Protein amino acid sequence
        ligand_smiles_list: List of ligand SMILES strings to screen
        top_n:              Number of top Vina hits to pass to GNINA (default 50)
        progress_callback:  Optional async function(stage, message) for live status

    Returns:
        {
            best_molecule: {smiles, vina_score, gnina_score, consensus_rank},
            ranked_results: [...],
            stage1: {plddt_score, pdb_string, ...},
            stage2: {screened, top_n_selected, ...},
            stage3: {refined, ...},
            status: "success"
        }
    """

    # Input validation
    if not sequence or len(sequence) < 10:
        return {"status": "error", "message": "Protein sequence must be at least 10 amino acids."}
    valid_aa = set("ACDEFGHIKLMNPQRSTVWY")
    clean_seq = "".join(c for c in sequence.upper() if c.isalpha())
    invalid = set(clean_seq) - valid_aa
    if invalid:
        return {"status": "error", "message": f"Invalid amino acids: {', '.join(sorted(invalid))}. Only standard 20 amino acids accepted."}
    if len(clean_seq) > 2000:
        return {"status": "error", "message": "Sequence too long (max 2000 residues for web docking)."}
    if not ligand_smiles_list:
        return {"status": "error", "message": "At least one ligand SMILES required."}
    if len(ligand_smiles_list) > 50:
        return {"status": "error", "message": "Maximum 50 ligands per run."}

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
        return await _run_pipeline_inner(sequence, ligand_smiles_list, top_n, _receptor_pdbqt_dir, _progress, result, pdb_content=pdb_content)
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
            import torch
            device = "MPS (Apple Silicon)" if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() else "CPU (Standard)"
            mode_str = f"Mode: Local GPU Inference on {device}"
        except ImportError:
            device = "CPU (ESMFold fallback)"
            mode_str = "Mode: Extended-chain fallback (no torch)"
            torch = None

        await _progress("PIPELINE", f"Initializing Consensus Discovery Suite on {device}...")
        await _progress("STAGE 1 / ESMFold", f"Commencing structural folding for sequence (Length: {len(sequence)}aa, {mode_str})...")

        try:
            stage1_result = await esmfold_predict(sequence, progress_callback=_progress)
            result["stage1"] = stage1_result
            receptor_pdb = stage1_result["pdb_string"]
            score = stage1_result.get('plddt_score', 0)
            await _progress("STAGE 1 / ESMFold", f"✅ Structure predicted — pLDDT: {score}%")
        except Exception as e:
            return {**result, "status": "error", "message": f"Stage 1 (ESMFold) failed: {e!s}"}

    await _progress("PIPELINE", "─── STAGE 2 INITIATED: BROAD SCREENING ───")
    # ══════════════════════════════════════════════════════════════════════════
    # STAGE 2: AutoDock Vina — Fast Broad Screening
    # ══════════════════════════════════════════════════════════════════════════
    await _progress("STAGE 2 / Vina", f"Screening {len(ligand_smiles_list)} ligands with AutoDock Vina...")

    if not run_vina_docking:
        return {**result, "status": "error", "message": "AutoDock Vina engine not loaded."}

    # Pre-convert receptor PDB→PDBQT ONCE for all ligands
    from .docking_engine import pdb_to_pdbqt
    if not pdb_to_pdbqt(receptor_pdb, _receptor_pdbqt_path):
        return {**result, "status": "error", "message": "Failed to convert receptor PDB to PDBQT."}

    vina_results = []
    failed = 0
    total_ligands = len(ligand_smiles_list)

    # Run Vina for all ligands — one at a time to stay within 908MB RAM / 2-core limits
    semaphore = asyncio.Semaphore(1)

    async def screen_ligand(smiles: str, idx: int):
        nonlocal failed
        async with semaphore:
            try:
                if idx % 5 == 0 or idx == total_ligands - 1:
                    await _progress("STAGE 2 / Vina", f"Screening ligand {idx+1}/{total_ligands}...", {"current": idx+1, "total": total_ligands})

                docking_result = await run_vina_docking(receptor_pdb, smiles, exhaustiveness=2, receptor_pdbqt_path=_receptor_pdbqt_path)
                return {
                    "smiles": smiles,
                    "vina_score": docking_result.get("binding_affinity"),
                    "gnina_score": None,
                    "consensus_rank": None,
                    "status": "screened",
                    "structure": docking_result.get("structure"),
                }
            except Exception as e:
                logger.debug("Vina failed for ligand #%s: %s", idx, e)
                failed += 1
                return None

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
    }
    await _progress("STAGE 2 / Vina", f"✅ Screening complete — {len(top_candidates)} top candidates selected for GNINA.", {"current": total_ligands, "total": total_ligands})

    await _progress("PIPELINE", "─── STAGE 3 INITIATED: CNN REFINEMENT ───")
    # ══════════════════════════════════════════════════════════════════════════
    # STAGE 3: GNINA — CNN Deep-Learning Re-Scoring
    # ══════════════════════════════════════════════════════════════════════════
    total_refined = len(top_candidates)
    await _progress("STAGE 3 / GNINA", f"Re-scoring {total_refined} candidates with GNINA CNN...", {"current": 0, "total": total_refined})

    if not run_gnina_docking:
        logger.warning("GNINA not available — returning Vina-only results.")
        for i, candidate in enumerate(top_candidates):
            candidate["consensus_rank"] = i + 1
        result["stage3"] = {"status": "skipped", "reason": "GNINA binary not available"}
        result["ranked_results"] = top_candidates
        result["best_molecule"] = top_candidates[0] if top_candidates else None
        result["status"] = "success"
        return result

    gnina_semaphore = asyncio.Semaphore(1)  # GNINA is heavier — 1 at a time

    async def refine_candidate(candidate: dict, idx: int):
        async with gnina_semaphore:
            try:
                if idx % 2 == 0 or idx == total_refined - 1:
                    await _progress("STAGE 3 / GNINA", f"Refining candidate {idx+1}/{total_refined}...", {"current": idx+1, "total": total_refined})

                gnina_result = await run_gnina_docking(receptor_pdb, candidate["smiles"], exhaustiveness=4, receptor_pdbqt_path=_receptor_pdbqt_path)
                candidate["gnina_score"] = gnina_result.get("binding_affinity")
                candidate["cnn_affinity"] = gnina_result.get("cnn_affinity")
                candidate["structure"] = gnina_result.get("structure")
                candidate["status"] = "refined"
                return candidate
            except Exception as e:
                logger.debug("GNINA failed for candidate: %s", e)
                candidate["gnina_score"] = None
                candidate["status"] = "gnina_failed"
                return candidate

    refined = await asyncio.gather(*[refine_candidate(c, i) for i, c in enumerate(top_candidates)])

    # Final consensus ranking:
    # Weighted score = 0.4 * vina_score + 0.6 * gnina_score (both negative, lower = better)
    def consensus_score(c):
        v = c.get("vina_score") or 0
        g = c.get("gnina_score") or v
        return 0.4 * v + 0.6 * g

    refined.sort(key=consensus_score)

    for i, candidate in enumerate(refined):
        candidate["consensus_rank"] = i + 1
        candidate["consensus_score"] = round(consensus_score(candidate), 3)

    result["stage3"] = {
        "refined": len(refined),
        "best_gnina_score": refined[0].get("gnina_score") if refined else None,
    }
    result["ranked_results"] = refined
    result["best_molecule"] = refined[0] if refined else None
    result["status"] = "success"

    await _progress("STAGE 3 / GNINA", f"✅ Refinement complete — Best molecule at consensus rank #1: {result['best_molecule']['smiles'][:30]}...")

    return result

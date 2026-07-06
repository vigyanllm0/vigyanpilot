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
import subprocess
import tempfile
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# ── Import engines ────────────────────────────────────────────────────────────
try:
    from primerforge.pipelines.esmfold_engine import predict_structure as esmfold_predict
except ImportError:
    esmfold_predict = None
    logger.warning("ESMFold engine not available.")

try:
    from primerforge.pipelines.docking_engine import run_vina_docking, run_gnina_docking
except ImportError:
    run_vina_docking = None
    run_gnina_docking = None
    logger.warning("Docking engine not available.")


async def run_consensus_pipeline(
    sequence: str,
    ligand_smiles_list: List[str],
    top_n: int = 50,
    progress_callback=None
) -> Dict[str, Any]:
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

    async def _progress(stage: str, msg: str, metadata: dict = None):
        logger.info(f"[{stage}] {msg}")
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

    # ══════════════════════════════════════════════════════════════════════════
    # STAGE 1: ESMFold — Predict Protein 3D Structure
    # ══════════════════════════════════════════════════════════════════════════
    import torch
    device = "MPS (Apple Silicon)" if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() else "CPU (Standard)"
    await _progress("PIPELINE", f"Initializing Consensus Discovery Suite on {device}...")
    await _progress("STAGE 1 / ESMFold", f"Commencing structural folding for sequence (Length: {len(sequence)}aa, Mode: Local GPU Inference)...")

    if not esmfold_predict:
        return {**result, "status": "error", "message": "ESMFold engine not loaded. Install: pip install transformers einops"}

    try:
        stage1_result = await esmfold_predict(sequence, progress_callback=_progress)
        result["stage1"] = stage1_result
        receptor_pdb = stage1_result["pdb_string"]
        await _progress("STAGE 1 / ESMFold", f"✅ Structure predicted — pLDDT: {stage1_result['plddt_score']}%")
    except Exception as e:
        return {**result, "status": "error", "message": f"Stage 1 (ESMFold) failed: {str(e)}"}

    await _progress("PIPELINE", "─── STAGE 2 INITIATED: BROAD SCREENING ───")
    # ══════════════════════════════════════════════════════════════════════════
    # STAGE 2: AutoDock Vina — Fast Broad Screening
    # ══════════════════════════════════════════════════════════════════════════
    await _progress("STAGE 2 / Vina", f"Screening {len(ligand_smiles_list)} ligands with AutoDock Vina...")

    if not run_vina_docking:
        return {**result, "status": "error", "message": "AutoDock Vina engine not loaded."}

    vina_results = []
    failed = 0
    total_ligands = len(ligand_smiles_list)

    # Run Vina for all ligands — batch with concurrency limit (4 parallel max)
    semaphore = asyncio.Semaphore(4)

    async def screen_ligand(smiles: str, idx: int):
        nonlocal failed
        async with semaphore:
            try:
                if idx % 5 == 0 or idx == total_ligands - 1:
                    await _progress("STAGE 2 / Vina", f"Screening ligand {idx+1}/{total_ligands}...", {"current": idx+1, "total": total_ligands})

                docking_result = await run_vina_docking(receptor_pdb, smiles, exhaustiveness=4)
                return {
                    "smiles": smiles,
                    "vina_score": docking_result.get("binding_affinity"),
                    "gnina_score": None,
                    "consensus_rank": None,
                    "status": "screened"
                }
            except Exception as e:
                logger.debug(f"Vina failed for ligand #{idx}: {e}")
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

    gnina_semaphore = asyncio.Semaphore(2)  # GNINA is heavier — fewer parallel

    async def refine_candidate(candidate: dict, idx: int):
        async with gnina_semaphore:
            try:
                if idx % 2 == 0 or idx == total_refined - 1:
                    await _progress("STAGE 3 / GNINA", f"Refining candidate {idx+1}/{total_refined}...", {"current": idx+1, "total": total_refined})

                gnina_result = await run_gnina_docking(receptor_pdb, candidate["smiles"], exhaustiveness=8)
                candidate["gnina_score"] = gnina_result.get("binding_affinity")
                candidate["cnn_affinity"] = gnina_result.get("cnn_affinity")
                candidate["structure"] = gnina_result.get("structure")
                candidate["status"] = "refined"
                return candidate
            except Exception as e:
                logger.debug(f"GNINA failed for candidate: {e}")
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

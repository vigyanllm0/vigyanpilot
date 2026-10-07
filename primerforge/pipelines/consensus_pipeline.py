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

# GNINA's CNN re-scoring is the slowest step on CPU — only the top-K Vina
# hits get refined; the rest are ranked on Vina-only consensus (see stage 3).
GNINA_REFINE_TOP_K = 10


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
                    receptor_pdb, smiles, exhaustiveness=2,
                    receptor_pdbqt_path=_receptor_pdbqt_path, cpu=cpu_per_vina)
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
    # CNN re-scoring is the slowest step on CPU — refine only the best K by
    # Vina score (GNINA_REFINE_TOP_K). Remaining candidates keep Vina-only
    # consensus via the g=v fallback below and still get ranked, so output
    # size/top_n semantics are unchanged.
    refine_list = top_candidates[:GNINA_REFINE_TOP_K]
    total_refined = len(refine_list)
    vina_only = len(top_candidates) - total_refined
    await _progress("STAGE 3 / GNINA", f"Re-scoring top {total_refined} of {len(top_candidates)} candidates with GNINA CNN...", {"current": 0, "total": total_refined})

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
    gnina_failures: list[str] = []
    gnina_broken_reason: list[str] = []  # sentinel: first BINARY-level failure

    def _binary_error(e: Exception) -> bool:
        """True when GNINA itself can't run (missing/exec-format/permission),
        as opposed to a per-ligand docking failure."""
        if isinstance(e, (FileNotFoundError, PermissionError)):
            return True
        if isinstance(e, OSError) and getattr(e, "errno", None) in (8, 13, 2):
            return True
        msg = str(e).lower()
        return ("exec format error" in msg or "permission denied" in msg
                or "no such file or directory" in msg or "not found" in msg)

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

                gnina_result = await run_gnina_docking(receptor_pdb, candidate["smiles"], exhaustiveness=4, receptor_pdbqt_path=_receptor_pdbqt_path)
                candidate["gnina_score"] = gnina_result.get("binding_affinity")
                candidate["cnn_affinity"] = gnina_result.get("cnn_affinity")
                candidate["structure"] = gnina_result.get("structure")
                candidate["status"] = "refined"
                return candidate
            except Exception as e:
                # Keep the reason visible in the job result (surfaced via the
                # status API) — previously GNINA failures were logged at DEBUG
                # only and vanished, making prod breakage undiagnosable.
                logger.warning("GNINA failed for candidate: %s", e)
                gnina_failures.append(str(e)[:300])
                if _binary_error(e) and not gnina_broken_reason:
                    gnina_broken_reason.append(str(e)[:300])
                    logger.warning("GNINA binary unusable — skipping remaining refinements: %s", e)
                candidate["gnina_score"] = None
                candidate["status"] = "gnina_failed"
                return candidate

    refined_top = await asyncio.gather(*[refine_candidate(c, i) for i, c in enumerate(refine_list)])
    # Merge refined top-K with Vina-only remainder — one ranked list of size top_n
    refined = list(refined_top) + list(top_candidates[total_refined:])

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
        "refined": len(refined_top),
        "vina_only": vina_only,
        "best_gnina_score": next(
            (c.get("gnina_score") for c in refined if c.get("gnina_score") is not None), None),
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

    await _progress("STAGE 3 / GNINA", f"✅ Refinement complete — Best molecule at consensus rank #1: {result['best_molecule']['smiles'][:30]}...")

    return result

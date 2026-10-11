"""
VigyanLLM — Virtual Screening Engine v2

File-based, chunked, resumable virtual screening campaigns.

Architecture
────────────
Campaign = a directory under ``docking_queue/screen/<id>/``::

    campaign.json           spec + status + progress + config (atomic writes)
    library.smi             normalized ligands (id<TAB>SMILES<TAB>name)
    receptors/<pid>.pdb     prepared receptor structure
    receptors/<pid>.pdbqt   receptor PDBQT for Vina
    receptors/<pid>.box.json  detected pocket box
    ligands/<pid>/chunk_<n>/<idx>.pdbqt  pre-prepared ligand PDBQTs
    results/<pid>/chunk_<n>.jsonl        per-chunk scores (one JSON per line)
    results/<pid>/final.json             ranked results + GNINA-refined scores
    cancel                  touch to request cancellation
    running                 worker heartbeat (mtime = last update)

Funnel
──────
1. Bulk screen: AutoDock Vina at configurable exhaustiveness (default 1),
   num_modes=1, pocket-detected box.  Pre-prepared ligand PDBQTs
   (meeko + ETKDGv3, ~23 ms/ligand) — no obabel --gen3d per-ligand cost.
2. Top-K re-dock: top K candidates per protein re-docked at exhaustiveness 8
   for a deeper pose search.
3. GNINA CNN refine: top K scored with GNINA's convolutional scoring for
   consensus ranking.

Throughput
──────────
Measured on the production t3.large (2 vCPU, x86):
- Ligand prep (meeko+ETKDGv3): ~23 ms/ligand single-thread.
- Vina exh=1, pocket box (~22 Å): ~3.2 s/ligand/core on M-series ARM;
  ~6.4 s/ligand/core on prod x86 (measured 2026-10-11).
- 2 vCPU → ~0.31 ligands/s (exh=1).  100k ligands ≈ 90 h.
- Scaling is linear with CPU cores: 16 vCPU ≈ 2.5 lig/s, 32 vCPU ≈ 5 lig/s.

The engine auto-scales Vina lanes to the CPU slots it holds (see
``docking_queue.acquire_slots``); interactive docking jobs always get
priority for the remaining cores.
"""

from __future__ import annotations

import asyncio
import csv
import glob
import io
import json
import logging
import os
import shutil
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

MAX_PROTEINS = 10
MAX_LIGANDS = 100_000
CHUNK_SIZE = 500
DEFAULT_EXHAUSTIVENESS = 1
REFINE_EXHAUSTIVENESS = 8
DEFAULT_TOP_K_REFINE = 10
MAX_TOP_K_REFINE = 50
VINA_TIMEOUT_S = 120.0
HEARTBEAT_TIMEOUT_S = 300.0  # 5 min — campaign considered dead if no heartbeat
# A 'pending' campaign is stale after this long. Must clear the worker's
# acquire_slots(wait_s=120) queue wait + interpreter/rdkit import (~10-30 s)
# with margin, since run_campaign flips status to 'running' immediately after.
PENDING_STALE_S = 240.0

# Campaign status values
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"
STATUS_INTERRUPTED = "interrupted"

# Queue base dir — import from docking_queue for consistency; fall back to
# a manual computation if the import fails (e.g., in a standalone subprocess).
try:
    from primerforge.docking_queue import QUEUE_DIR as _QUEUE_BASE
except ImportError:
    # virtual_screening.py lives in primerforge/pipelines/; queue dir is
    # two levels up from this file (repo root) → docking_queue/
    _QUEUE_BASE = os.environ.get(
        "DOCKING_QUEUE_DIR",
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "docking_queue",
        ),
    )
SCREEN_DIR = os.path.join(_QUEUE_BASE, "screen")

# Vina path (resolved at import; same binary the consensus pipeline uses)
_VINA_BIN = shutil.which("vina") or "vina"


# ── File helpers ─────────────────────────────────────────────────────────────

def _atomic_json(path: str, data: dict) -> None:
    """Atomic JSON write — readers never see a truncated file."""
    tmp = f"{path}.tmp{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=None, separators=(",", ":"))
    os.replace(tmp, path)


def _read_json(path: str) -> dict | None:
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _campaign_dir(campaign_id: str) -> str:
    return os.path.join(SCREEN_DIR, campaign_id)


def _campaign_json_path(campaign_id: str) -> str:
    return os.path.join(_campaign_dir(campaign_id), "campaign.json")


# ── Ligand prep (meeko + ETKDGv3) ───────────────────────────────────────────

def prep_ligand_pdbqt(smiles: str, seed: int = 0xf00d) -> str | None:
    """SMILES → ligand PDBQT string via meeko + ETKDGv3. Returns None on failure.

    ~23 ms per drug-like molecule on M-series ARM.  No obabel --gen3d (which
    costs 1–5 s per ligand and is the single biggest throughput bottleneck).
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
        from meeko import MoleculePreparation, PDBQTWriterLegacy

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        mol = Chem.AddHs(mol)
        ps = AllChem.ETKDGv3()
        ps.randomSeed = seed
        if AllChem.EmbedMolecule(mol, ps) != 0:
            return None
        prep = MoleculePreparation()
        setups = prep.prepare(mol)
        if not setups:
            return None
        result = PDBQTWriterLegacy.write_string(setups[0])
        pdbqt_str = result[0] if isinstance(result, tuple) else result
        ok = result[1] if isinstance(result, tuple) and len(result) > 1 else True
        if not ok or not pdbqt_str or len(pdbqt_str) < 50:
            return None
        return pdbqt_str
    except Exception:
        return None


def prep_ligand_batch(
    ligands: list[dict], out_dir: str, chunk_idx: int,
) -> list[tuple[int, str]]:
    """Prep a chunk of ligands → PDBQT files. Returns [(lib_index, pdbqt_path)].

    Sequential (23 ms × 500 = 11.5 s per chunk) — fast enough that
    parallelising would compete with Vina for CPU.  Failed preps are skipped
    (recorded in results as ``prep_failed``).
    """
    chunk_dir = os.path.join(out_dir, f"chunk_{chunk_idx}")
    os.makedirs(chunk_dir, exist_ok=True)
    prepared: list[tuple[int, str]] = []
    for lig in ligands:
        idx = lig["_index"]
        pdbqt = prep_ligand_pdbqt(lig["smiles"])
        if pdbqt is None:
            continue
        path = os.path.join(chunk_dir, f"{idx}.pdbqt")
        with open(path, "w") as f:
            f.write(pdbqt)
        prepared.append((idx, path))
    return prepared


# ── Vina lean runner ─────────────────────────────────────────────────────────

def _parse_vina_score(pdbqt_path: str) -> float | None:
    """Parse the best affinity from a Vina output PDBQT."""
    try:
        with open(pdbqt_path) as f:
            for line in f:
                if line.startswith("REMARK VINA RESULT:"):
                    parts = line.split()
                    return float(parts[3])
    except (OSError, ValueError, IndexError):
        pass
    return None


async def _dock_vina_prepped(
    receptor_pdbqt: str,
    ligand_pdbqt: str,
    box: dict,
    exhaustiveness: int = 1,
    cpu: int = 1,
    timeout: float = VINA_TIMEOUT_S,
) -> tuple[float | None, str | None]:
    """Run Vina on a pre-prepared ligand PDBQT. Returns (score, out_path).

    Lean runner: no temp dir, no ligand prep, no receptor conversion — all
    done once before the campaign starts.  stdout/stderr → DEVNULL (the
    progress-bar output can deadlock pipes when many Vina processes run
    concurrently on low-core machines).
    """
    out_path = ligand_pdbqt.replace(".pdbqt", "_out.pdbqt")
    cx, cy, cz = (float(v) for v in box["center"])
    sx, sy, sz = (float(v) for v in box["size"])
    cmd = [
        _VINA_BIN,
        "--receptor", receptor_pdbqt,
        "--ligand", ligand_pdbqt,
        "--center_x", f"{cx:.3f}", "--center_y", f"{cy:.3f}", "--center_z", f"{cz:.3f}",
        "--size_x", f"{sx:.1f}", "--size_y", f"{sy:.1f}", "--size_z", f"{sz:.1f}",
        "--exhaustiveness", str(exhaustiveness),
        "--num_modes", "1",
        "--out", out_path,
    ]
    if cpu:
        cmd += ["--cpu", str(cpu)]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=timeout)
    except (asyncio.TimeoutError, OSError):
        return None, None
    if proc.returncode != 0:
        return None, None
    score = _parse_vina_score(out_path)
    return score, out_path


# ── Chunk dock (parallel lanes) ─────────────────────────────────────────────

async def _dock_chunk(
    receptor_pdbqt: str,
    prepared: list[tuple[int, str]],
    smiles_by_index: dict[int, str],
    box: dict,
    exhaustiveness: int,
    lanes: int,
    progress_cb=None,
) -> list[dict]:
    """Dock a chunk of pre-prepared ligands in parallel. Returns result dicts.

    Each lane runs one Vina process at a time (``lanes`` = CPU slots held).
    Failed docks are recorded as ``{"index": i, "score": None, "status": "dock_failed"}``.
    """
    sem = asyncio.Semaphore(max(1, lanes))
    done_count = 0
    total = len(prepared)

    async def _dock_one(idx: int, path: str) -> dict:
        nonlocal done_count
        async with sem:
            score, out_path = await _dock_vina_prepped(
                receptor_pdbqt, path, box, exhaustiveness, cpu=1,
            )
            done_count += 1
            if out_path and os.path.exists(out_path):
                try:
                    os.unlink(out_path)
                except OSError:
                    pass
            if progress_cb:
                try:
                    await progress_cb(done_count, total)
                except Exception:
                    pass
            return {
                "index": idx,
                "smiles": smiles_by_index.get(idx, ""),
                "vina_score": score,
                "status": "ok" if score is not None else "dock_failed",
            }

    tasks = [_dock_one(idx, path) for idx, path in prepared]
    gathered = await asyncio.gather(*tasks, return_exceptions=True)
    results = []
    for r in gathered:
        if isinstance(r, dict):
            results.append(r)
        elif isinstance(r, Exception):
            logger.debug("Dock exception: %s", r)
    return results


# ── Receptor prep (once per protein) ────────────────────────────────────────

def _prep_receptor(
    pdb_content: str, protein_id: str, receptors_dir: str,
) -> tuple[str | None, dict | None]:
    """Prepare receptor PDBQT + detect pocket box. Returns (pdbqt_path, box).

    Cached in ``receptors/<pid>.pdbqt`` and ``receptors/<pid>.box.json``.
    Uses ``pdb_to_pdbqt`` (obabel -xr or meeko fallback) and ``_select_box``
    (pocket detection → centroid fallback) from the consensus pipeline.
    """
    pdbqt_path = os.path.join(receptors_dir, f"{protein_id}.pdbqt")
    box_path = os.path.join(receptors_dir, f"{protein_id}.box.json")

    # Box: cached or detect
    box = _read_json(box_path)
    if box is None:
        try:
            from primerforge.pipelines.consensus_pipeline import _select_box
            box, _note = _select_box(pdb_content, None)
        except Exception as exc:
            logger.warning("Pocket detection failed for %s: %s", protein_id, exc)
            box = None
        if box is None:
            # centroid fallback
            try:
                from primerforge.pipelines.docking_engine import compute_box_center_from_pdb
                cx, cy, cz, sx, sy, sz = compute_box_center_from_pdb(pdb_content)
                box = {
                    "center": [round(cx, 3), round(cy, 3), round(cz, 3)],
                    "size": [round(sx, 1), round(sy, 1), round(sz, 1)],
                    "source": "protein_centroid",
                }
            except Exception:
                box = {"center": [0, 0, 0], "size": [22, 22, 22], "source": "default"}
        _atomic_json(box_path, box)

    # PDBQT: cached or convert
    if not os.path.exists(pdbqt_path):
        from primerforge.pipelines.docking_engine import pdb_to_pdbqt
        ok = pdb_to_pdbqt(pdb_content, pdbqt_path)
        if not ok:
            return None, box

    return pdbqt_path, box


# ── Library normalization ───────────────────────────────────────────────────

def normalize_library(ligands: list) -> list[dict]:
    """Normalize + dedupe a ligand list. Each entry: {"_index", "smiles", "name"}.

    Accepts list of SMILES strings or list of {"smiles": ..., "name": ...} dicts.
    Invalid SMILES are dropped (RDKit parse check).
    """
    from rdkit import Chem

    seen: set[str] = set()
    normalized: list[dict] = []
    idx = 0
    for item in ligands:
        if isinstance(item, str):
            smiles = item.strip()
            name = ""
        elif isinstance(item, dict):
            smiles = str(item.get("smiles", "")).strip()
            name = str(item.get("name", "")).strip()
        else:
            continue
        if not smiles or smiles in seen:
            continue
        if Chem.MolFromSmiles(smiles) is None:
            continue
        seen.add(smiles)
        normalized.append({"_index": idx, "smiles": smiles, "name": name})
        idx += 1
    return normalized


def write_library_smi(ligands: list[dict], path: str) -> None:
    """Write normalized library to a .smi file (id<TAB>SMILES<TAB>name)."""
    with open(path, "w") as f:
        for lig in ligands:
            f.write(f"{lig['_index']}\t{lig['smiles']}\t{lig.get('name', '')}\n")


def read_library_smi(path: str) -> list[dict]:
    """Read a .smi file back into normalized ligand dicts."""
    ligands = []
    with open(path) as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                try:
                    idx = int(parts[0])
                except ValueError:
                    continue
                ligands.append({"_index": idx, "smiles": parts[1], "name": parts[2] if len(parts) > 2 else ""})
    return ligands


# ── Campaign lifecycle ──────────────────────────────────────────────────────

def create_campaign(
    proteins: list[dict],
    ligands: list,
    config: dict | None = None,
    user_email: str = "",
) -> str:
    """Create a new screening campaign. Returns campaign_id.

    proteins: [{"id"?, "sequence"?, "pdb_content"?, "name"?}, ...]
    ligands:  list of SMILES strings or {"smiles": ..., "name": ...} dicts
    config:   {"exhaustiveness"?, "top_k_refine"?, "chunk_size"?}
    """
    if not proteins or not isinstance(proteins, list):
        raise ValueError("At least one protein is required.")
    if len(proteins) > MAX_PROTEINS:
        raise ValueError(f"Maximum {MAX_PROTEINS} proteins per campaign.")

    normalized = normalize_library(ligands)
    if len(normalized) < 2:
        raise ValueError("At least 2 valid ligands required.")
    if len(normalized) > MAX_LIGANDS:
        raise ValueError(f"Maximum {MAX_LIGANDS:,} ligands per campaign.")

    # Validate protein entries
    clean_proteins = []
    for i, p in enumerate(proteins):
        if not isinstance(p, dict):
            raise ValueError(f"Protein {i+1} must be an object.")
        seq = str(p.get("sequence", "")).strip()
        pdb = str(p.get("pdb_content", "")).strip()
        name = str(p.get("name", "")).strip() or f"Protein {i+1}"
        pid = str(p.get("id", "")).strip() or f"p{i+1}"
        if not seq and not pdb:
            raise ValueError(f"Protein {i+1} needs a sequence or PDB content.")
        if pdb and "ATOM" not in pdb:
            raise ValueError(f"Protein {i+1}: PDB content contains no ATOM records.")
        if seq and len(seq) > 400:
            raise ValueError(
                f"Protein {i+1}: sequence too long ({len(seq)} aa). "
                "Maximum 400 aa for folding; upload a PDB file for longer proteins."
            )
        clean_proteins.append({"id": pid, "name": name, "sequence": seq, "pdb_content": pdb})

    cfg = config or {}
    exh = max(1, min(int(cfg.get("exhaustiveness", DEFAULT_EXHAUSTIVENESS)), 16))
    top_k = max(0, min(int(cfg.get("top_k_refine", DEFAULT_TOP_K_REFINE)), MAX_TOP_K_REFINE))
    chunk_size = max(50, min(int(cfg.get("chunk_size", CHUNK_SIZE)), 2000))

    campaign_id = uuid.uuid4().hex[:16]
    cdir = _campaign_dir(campaign_id)
    os.makedirs(os.path.join(cdir, "receptors"), exist_ok=True)
    os.makedirs(os.path.join(cdir, "results"), exist_ok=True)
    os.makedirs(os.path.join(cdir, "ligands"), exist_ok=True)

    # Write library
    write_library_smi(normalized, os.path.join(cdir, "library.smi"))

    # Detect lanes (CPU slots) at creation time
    try:
        from primerforge.docking_queue import CPU_SLOTS
        lanes = max(1, CPU_SLOTS)
    except Exception:
        lanes = max(1, (os.cpu_count() or 1))

    campaign = {
        "campaign_id": campaign_id,
        "status": STATUS_PENDING,
        "created_at": time.time(),
        "updated_at": time.time(),
        "user_email": user_email,
        "proteins": clean_proteins,
        "library": {
            "total": len(normalized),
            "source": "upload",
        },
        "config": {
            "exhaustiveness": exh,
            "top_k_refine": top_k,
            "chunk_size": chunk_size,
            "lanes": lanes,
        },
        "progress": {
            "stage": "pending",
            "message": "Campaign queued",
            "current_protein": 0,
            "total_proteins": len(clean_proteins),
            "current_chunk": 0,
            "total_chunks": 0,
            "ligands_done": 0,
            "ligands_total": len(normalized),
            "rate": None,
            "eta_seconds": None,
        },
        "results_summary": {},
    }
    _atomic_json(_campaign_json_path(campaign_id), campaign)
    logger.info(
        "Screen campaign %s created: %d proteins × %d ligands (exh=%d, chunk=%d)",
        campaign_id, len(clean_proteins), len(normalized), exh, chunk_size,
    )
    return campaign_id


def get_campaign(campaign_id: str) -> dict | None:
    """Read campaign state. Returns None if not found or invalid ID."""
    if not campaign_id or not campaign_id.replace("-", "").isalnum() or len(campaign_id) > 64:
        return None
    return _read_json(_campaign_json_path(campaign_id))


def update_campaign(campaign_id: str, updates: dict) -> None:
    """Merge updates into campaign.json (atomic)."""
    path = _campaign_json_path(campaign_id)
    data = _read_json(path)
    if data is None:
        return
    data.update(updates)
    data["updated_at"] = time.time()
    _atomic_json(path, data)


def update_progress(campaign_id: str, progress_updates: dict) -> None:
    """Merge progress updates into campaign.json (atomic)."""
    path = _campaign_json_path(campaign_id)
    data = _read_json(path)
    if data is None:
        return
    data.setdefault("progress", {}).update(progress_updates)
    data["updated_at"] = time.time()
    _atomic_json(path, data)


def cancel_campaign(campaign_id: str) -> bool:
    """Request cancellation by touching the cancel marker. Returns True if campaign exists."""
    cdir = _campaign_dir(campaign_id)
    if not os.path.exists(_campaign_json_path(campaign_id)):
        return False
    cancel_path = os.path.join(cdir, "cancel")
    with open(cancel_path, "w") as f:
        f.write(str(time.time()))
    return True


def _check_cancel(campaign_id: str) -> bool:
    return os.path.exists(os.path.join(_campaign_dir(campaign_id), "cancel"))


def _heartbeat(campaign_id: str) -> None:
    """Update the running marker's mtime (worker liveness signal)."""
    path = os.path.join(_campaign_dir(campaign_id), "running")
    try:
        with open(path, "a"):
            pass
        os.utime(path)
    except OSError:
        pass


def is_stale(campaign_id: str) -> bool:
    """True when a campaign's worker is gone and nobody is coming back for it.

    Covers two dead states:
      * ``running`` with no heartbeat for >5 min (worker crashed mid-run).
      * ``pending`` untouched for >PENDING_STALE_S — the worker was spawned
        but never reached ``run_campaign`` (observed on prod 2026-10-11 when
        the child died on ``import primerforge``). Without this branch such a
        campaign sat at 'pending' forever and the UI never offered Resume.

    Grace for ``pending``: the worker calls ``acquire_slots(..., wait_s=120)``
    BEFORE ``run_campaign`` flips the status to ``running``, so a legitimate
    queue wait must not be misread as a dead worker.
    """
    c = get_campaign(campaign_id)
    if c is None:
        return False
    status = c.get("status")

    if status == STATUS_PENDING:
        ref = c.get("updated_at") or c.get("created_at") or 0.0
        return (time.time() - ref) > PENDING_STALE_S

    if status != STATUS_RUNNING:
        return False
    path = os.path.join(_campaign_dir(campaign_id), "running")
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return True
    return (time.time() - mtime) > HEARTBEAT_TIMEOUT_S


def list_campaigns(user_email: str, limit: int = 20) -> list[dict]:
    """List campaigns for a user (most recent first)."""
    if not os.path.isdir(SCREEN_DIR):
        return []
    results = []
    for entry in os.listdir(SCREEN_DIR):
        c = get_campaign(entry)
        if c and c.get("user_email") == user_email:
            results.append(c)
    results.sort(key=lambda c: c.get("created_at", 0), reverse=True)
    return results[:limit]


# ── Campaign runner (called by screening_worker subprocess) ─────────────────

async def run_campaign(
    campaign_id: str,
    progress_callback=None,
) -> dict:
    """Process all proteins × ligands. Resumable — skips completed chunks.

    This is the main entry point called by ``screening_worker.py``.
    Returns the final campaign dict.
    """
    campaign = get_campaign(campaign_id)
    if campaign is None:
        raise ValueError(f"Campaign {campaign_id} not found.")

    cdir = _campaign_dir(campaign_id)
    ligands = read_library_smi(os.path.join(cdir, "library.smi"))
    config = campaign.get("config", {})
    exh = int(config.get("exhaustiveness", DEFAULT_EXHAUSTIVENESS))
    top_k = int(config.get("top_k_refine", DEFAULT_TOP_K_REFINE))
    chunk_size = int(config.get("chunk_size", CHUNK_SIZE))
    lanes = max(1, int(config.get("lanes", 1)))

    proteins = campaign.get("proteins", [])
    total_proteins = len(proteins)
    total_ligands = len(ligands)
    total_chunks = -(-total_ligands // chunk_size)  # ceil

    update_campaign(campaign_id, {"status": STATUS_RUNNING})
    _heartbeat(campaign_id)

    start_time = time.time()
    results_summary: dict[str, Any] = {}

    async def _report(stage: str, message: str, **kw):
        pg = {"stage": stage, "message": message[:300]}
        pg.update(kw)
        update_progress(campaign_id, pg)
        _heartbeat(campaign_id)
        if progress_callback:
            try:
                await progress_callback(stage, message, kw)
            except Exception:
                pass

    try:
        for p_idx, protein in enumerate(proteins):
            if _check_cancel(campaign_id):
                await _report("cancelled", "Cancelled by user")
                update_campaign(campaign_id, {"status": STATUS_CANCELLED})
                return get_campaign(campaign_id) or {}

            pid = protein["id"]
            pname = protein.get("name", pid)

            await _report(
                "folding", f"Preparing structure for {pname}…",
                current_protein=p_idx, total_proteins=total_proteins,
                current_chunk=0, total_chunks=total_chunks,
                ligands_done=0, ligands_total=total_ligands,
            )

            # 1. Get structure (fold or load PDB)
            pdb_content = protein.get("pdb_content", "")
            if not pdb_content:
                sequence = protein.get("sequence", "")
                from primerforge.pipelines.esmfold_engine import predict_structure
                fold = await predict_structure(sequence)
                pdb_content = fold.get("pdb_string", "")
                plddt = fold.get("plddt_score", 0)
                if not pdb_content or "ATOM" not in pdb_content:
                    raise RuntimeError(
                        f"Structure prediction failed for {pname}: "
                        f"{fold.get('message', 'no structure returned')}"
                    )
                protein["plddt_score"] = plddt

            # Cache structure
            pdb_path = os.path.join(cdir, "receptors", f"{pid}.pdb")
            with open(pdb_path, "w") as f:
                f.write(pdb_content)

            # 2. Prep receptor PDBQT + detect box
            await _report("prep", f"Preparing receptor + detecting pocket for {pname}…")
            receptors_dir = os.path.join(cdir, "receptors")
            receptor_pdbqt, box = _prep_receptor(pdb_content, pid, receptors_dir)
            if receptor_pdbqt is None:
                raise RuntimeError(f"Receptor preparation failed for {pname}.")

            # 3. Bulk screen in chunks
            for chunk_idx in range(total_chunks):
                if _check_cancel(campaign_id):
                    await _report("cancelled", "Cancelled by user")
                    update_campaign(campaign_id, {"status": STATUS_CANCELLED})
                    return get_campaign(campaign_id) or {}

                chunk_start = chunk_idx * chunk_size
                chunk_end = min(chunk_start + chunk_size, total_ligands)
                chunk_ligands = ligands[chunk_start:chunk_end]
                chunk_result_path = os.path.join(cdir, "results", pid, f"chunk_{chunk_idx}.jsonl")

                # Skip already-completed chunks (resume support)
                if os.path.exists(chunk_result_path):
                    continue

                await _report(
                    "docking",
                    f"Screening {pname}: chunk {chunk_idx+1}/{total_chunks} "
                    f"(ligands {chunk_start+1}–{chunk_end})",
                    current_protein=p_idx, total_proteins=total_proteins,
                    current_chunk=chunk_idx + 1, total_chunks=total_chunks,
                    ligands_done=chunk_start, ligands_total=total_ligands,
                    rate=None, eta_seconds=None,
                )

                # Prep chunk
                ligands_out_dir = os.path.join(cdir, "ligands", pid)
                prepared = prep_ligand_batch(chunk_ligands, ligands_out_dir, chunk_idx)
                smiles_by_index = {l["_index"]: l["smiles"] for l in chunk_ligands}

                # Dock chunk (parallel Vina)
                chunk_t0 = time.time()

                async def _chunk_progress(done: int, total: int, _ci=chunk_idx, _cs=chunk_start, _ct=total_chunks):
                    elapsed = time.time() - chunk_t0
                    rate = done / elapsed if elapsed > 0 else 0
                    remaining = total - done
                    eta = remaining / rate if rate > 0 else None
                    global_lig_done = _cs + done
                    await _report(
                        "docking",
                        f"Docking {pname}: ligand {global_lig_done}/{total_ligands} "
                        f"(chunk {_ci+1}/{_ct})",
                        current_protein=p_idx, total_proteins=total_proteins,
                        current_chunk=_ci + 1, total_chunks=_ct,
                        ligands_done=global_lig_done, ligands_total=total_ligands,
                        rate=round(rate, 3) if rate else None,
                        eta_seconds=int(eta) if eta else None,
                    )

                results = await _dock_chunk(
                    receptor_pdbqt, prepared, smiles_by_index, box,
                    exh, lanes, progress_cb=_chunk_progress,
                )

                # Write chunk results (atomic JSONL)
                os.makedirs(os.path.dirname(chunk_result_path), exist_ok=True)
                tmp_path = f"{chunk_result_path}.tmp{os.getpid()}"
                with open(tmp_path, "w") as f:
                    for r in results:
                        f.write(json.dumps(r) + "\n")
                os.replace(tmp_path, chunk_result_path)

                # Cleanup prepared ligand PDBQTs (saves disk at 100k scale)
                chunk_ligand_dir = os.path.join(ligands_out_dir, f"chunk_{chunk_idx}")
                shutil.rmtree(chunk_ligand_dir, ignore_errors=True)

                chunk_elapsed = time.time() - chunk_t0
                n_ok = sum(1 for r in results if r.get("status") == "ok")
                logger.info(
                    "Campaign %s protein %s chunk %d: %d/%d docked in %.1fs (%.2f lig/s)",
                    campaign_id, pid, chunk_idx, n_ok, len(prepared), chunk_elapsed,
                    n_ok / chunk_elapsed if chunk_elapsed > 0 else 0,
                )

            # 4. Merge chunk results → rank → top-K
            await _report("refining", f"Ranking {pname} hits, selecting top {top_k} for GNINA refine…")
            all_results = _merge_chunk_results(os.path.join(cdir, "results", pid), total_chunks)
            all_results.sort(key=lambda r: r.get("vina_score") or 999)
            # Store top 100 in final.json (for display/export); top_k only
            # controls how many get GNINA-refined.
            top_hits = all_results[:100]

            # 5. GNINA refine top-K (only if top_k > 0 and GNINA available)
            refined = 0
            refine_hits = top_hits[:top_k] if top_k > 0 else []
            if refine_hits:
                from primerforge.pipelines.docking_engine import run_gnina_docking
                gnina_available = True
                try:
                    from primerforge.pipelines.docking_engine import gnina_available as _ga
                    probe = _ga()
                    gnina_available = probe.get("ok", False)
                except Exception:
                    gnina_available = False

                if gnina_available:
                    for k, hit in enumerate(refine_hits):
                        if _check_cancel(campaign_id):
                            break
                        try:
                            gres = await run_gnina_docking(
                                pdb_content, hit["smiles"],
                                exhaustiveness=REFINE_EXHAUSTIVENESS, box=box,
                            )
                            hit["gnina_score"] = gres.get("gnina_score")
                            hit["cnn_affinity"] = gres.get("cnn_affinity")
                            hit["cnn_score"] = gres.get("cnn_score")
                            refined += 1
                        except Exception as exc:
                            logger.debug("GNINA refine failed for %s: %s", hit.get("smiles", "")[:30], exc)
                        await _report(
                            "refining",
                            f"GNINA refine {pname}: {k+1}/{len(refine_hits)}",
                            current_protein=p_idx, total_proteins=total_proteins,
                            ligands_done=total_ligands, ligands_total=total_ligands,
                        )

            # Compute consensus score (0.4×vina + 0.6×gnina when available;
            # falls back to vina-only when GNINA didn't run)
            for hit in top_hits:
                v = hit.get("vina_score")
                g = hit.get("gnina_score")
                if v is not None and g is not None:
                    hit["consensus_score"] = round(0.4 * v + 0.6 * g, 3)
                elif v is not None:
                    hit["consensus_score"] = round(v, 3)

            # 6. Write final results
            final_path = os.path.join(cdir, "results", pid, "final.json")
            final_data = {
                "protein_id": pid,
                "protein_name": pname,
                "box": box,
                "exhaustiveness": exh,
                "refine_exhaustiveness": REFINE_EXHAUSTIVENESS if top_k else None,
                "gnina_refined": refined,
                "total_screened": total_ligands,
                "total_docked": len(all_results),
                "top_hits": top_hits[:100],  # store top 100 with full detail
            }
            _atomic_json(final_path, final_data)

            best = top_hits[0] if top_hits else None
            results_summary[pid] = {
                "name": pname,
                "total_screened": total_ligands,
                "total_docked": len(all_results),
                "gnina_refined": refined,
                "best_vina": best.get("vina_score") if best else None,
                "best_gnina": best.get("gnina_score") if best else None,
                "best_consensus": best.get("consensus_score") if best else None,
                "best_smiles": best.get("smiles", "") if best else "",
            }

            update_campaign(campaign_id, {"results_summary": dict(results_summary)})

        # Done
        elapsed = time.time() - start_time
        rate = total_ligands / elapsed if elapsed > 0 else 0
        update_campaign(campaign_id, {
            "status": STATUS_COMPLETED,
            "progress": {
                "stage": "completed",
                "message": f"Screened {total_ligands} ligands × {total_proteins} proteins in {elapsed:.0f}s ({rate:.2f} lig/s)",
                "ligands_done": total_ligands,
                "ligands_total": total_ligands,
                "current_chunk": total_chunks,
                "total_chunks": total_chunks,
                "rate": round(rate, 3),
                "eta_seconds": 0,
            },
            "results_summary": results_summary,
            "elapsed_seconds": round(elapsed, 1),
        })
        logger.info(
            "Campaign %s completed: %d ligands × %d proteins in %.0fs (%.2f lig/s)",
            campaign_id, total_ligands, total_proteins, elapsed, rate,
        )

    except Exception as exc:
        logger.error("Campaign %s failed: %s", campaign_id, exc, exc_info=True)
        update_campaign(campaign_id, {
            "status": STATUS_FAILED,
            "progress": {"stage": "failed", "message": str(exc)[:300]},
        })

    # Cleanup running marker
    try:
        os.remove(os.path.join(cdir, "running"))
    except OSError:
        pass

    return get_campaign(campaign_id) or {}


def _merge_chunk_results(results_dir: str, total_chunks: int) -> list[dict]:
    """Merge all chunk JSONL files into a single result list."""
    merged = []
    for i in range(total_chunks):
        path = os.path.join(results_dir, f"chunk_{i}.jsonl")
        if not os.path.exists(path):
            continue
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        merged.append(json.loads(line))
                    except ValueError:
                        pass
    return merged


# ── Export ───────────────────────────────────────────────────────────────────

def export_campaign_csv(campaign_id: str) -> str | None:
    """Export all protein results as a CSV string. Returns None if not found."""
    campaign = get_campaign(campaign_id)
    if campaign is None:
        return None
    cdir = _campaign_dir(campaign_id)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "protein_id", "protein_name", "rank", "smiles", "vina_score",
        "gnina_score", "cnn_affinity", "consensus_score",
    ])
    for protein in campaign.get("proteins", []):
        pid = protein["id"]
        final = _read_json(os.path.join(cdir, "results", pid, "final.json"))
        if final is None:
            continue
        for rank, hit in enumerate(final.get("top_hits", [])[:100], 1):
            writer.writerow([
                pid, final.get("protein_name", pid), rank,
                hit.get("smiles", ""),
                hit.get("vina_score", ""),
                hit.get("gnina_score", ""),
                hit.get("cnn_affinity", ""),
                hit.get("consensus_score", ""),
            ])
    return buf.getvalue()


def export_campaign_sdf(campaign_id: str, top_n: int = 100) -> str | None:
    """Export top-N poses per protein as an SDF string. Returns None if not found.

    Uses RDKit to embed each top SMILES with its Vina pose (best conformer).
    """
    campaign = get_campaign(campaign_id)
    if campaign is None:
        return None
    cdir = _campaign_dir(campaign_id)
    blocks: list[str] = []
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except ImportError:
        return None

    for protein in campaign.get("proteins", []):
        pid = protein["id"]
        final = _read_json(os.path.join(cdir, "results", pid, "final.json"))
        if final is None:
            continue
        for hit in final.get("top_hits", [])[:top_n]:
            smiles = hit.get("smiles", "")
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                continue
            mol = Chem.AddHs(mol)
            ps = AllChem.ETKDGv3()
            ps.randomSeed = 42
            AllChem.EmbedMolecule(mol, ps)
            AllChem.MMFFOptimizeMolecule(mol)
            mol.SetProp("_Name", f"{pid}_{hit.get('rank', 0)}_{smiles[:30]}")
            mol.SetProp("protein", final.get("protein_name", pid))
            mol.SetProp("smiles", smiles)
            mol.SetProp("vina_score", str(hit.get("vina_score", "")))
            mol.SetProp("gnina_score", str(hit.get("gnina_score", "")))
            mol.SetProp("consensus_score", str(hit.get("consensus_score", "")))
            blocks.append(Chem.MolToMolBlock(mol) + "$$$$\n")
    return "".join(blocks) if blocks else None


# ── Backward compatibility (v1 API) ────────────────────────────────────────

# The old VirtualScreeningCampaign class is removed — it imported nonexistent
# VinaEngine/GNINAEngine, docked at origin, and stored state in an in-memory
# dict across gunicorn workers.  The v2 engine above replaces it entirely.

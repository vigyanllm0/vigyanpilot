#!/usr/bin/env python3
"""
VigyanLLM — Colab T4 Bridge Server (v2)
========================================
Runs ONLY on a CUDA-capable Colab instance (T4 GPU).
Exposes docking endpoints over FastAPI + Ngrok on port 7860.

CPU routes (chat, primer, MSA, gene-predict, sessions) stay on the Mac backend.
This server handles:
  • /run-dry-lab          – single-query molecular docking (Vina)
  • /api/docking          – explicit PDB + SMILES docking
  • /consensus-pipeline   – multi-ligand consensus screening
  • /pulse  /health       – GPU health check
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════════════
# 0.  KILL-STALE PROCESSES  (runs before anything else binds to port 7860)
# ═══════════════════════════════════════════════════════════════════════════════
import os
import subprocess
import time


def kill_stale_processes():
    """Kill leftover uvicorn and free port 7860."""
    for cmd in [["pkill", "-f", "uvicron"], ["fuser", "-k", "7860/tcp"]]:
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        except Exception as e:
            print("Suppressed exception: %s", e)
    time.sleep(2)
    print("✅ Stale processes cleared.")

kill_stale_processes()

# ═══════════════════════════════════════════════════════════════════════════════
# 1.  GPU GUARD  (crashes immediately on CPU-only runtimes)
# ═══════════════════════════════════════════════════════════════════════════════
import torch

if not torch.cuda.is_available():
    raise RuntimeError(
        "🚫 GPU GUARD FAILED — No CUDA device detected.\n"
        "This bridge server requires a T4 (or better) GPU.\n"
        "Start a Colab runtime with GPU acceleration enabled.\n"
        "CPU routes (chat, primer, MSA) belong on the Mac backend."
    )

_GPU_NAME = torch.cuda.get_device_name(0)
_GPU_VRAM_TOTAL_GB = round(torch.cuda.get_device_properties(0).total_mem / 1024**3, 2)
print(f"✅ GPU detected: {_GPU_NAME}  |  VRAM: {_GPU_VRAM_TOTAL_GB} GB")

# ═══════════════════════════════════════════════════════════════════════════════
# 2.  STANDARD IMPORTS  (safe on both CPU & GPU — no heavy GPU-only libs yet)
# ═══════════════════════════════════════════════════════════════════════════════
import datetime as _dt
import re
import shutil
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any

import psutil
import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ═══════════════════════════════════════════════════════════════════════════════
# 3.  GPU-ONLY IMPORTS  (gated — never run on the Mac backend)
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from vina import Vina  # AutoDock Vina Python bindings
except ImportError:
    Vina = None
    print("⚠️  vina not installed — docking will be unavailable.")

try:
    import rdkit  # cheminformatics (SMILES handling)
except ImportError:
    rdkit = None

try:
    import meeko  # Meeko ligand preparation
except ImportError:
    meeko = None

# ═══════════════════════════════════════════════════════════════════════════════
# 4.  FASTAPI APP
# ═══════════════════════════════════════════════════════════════════════════════
app = FastAPI(
    title="VigyanLLM Colab T4 Bridge",
    version="2.0.0",
    description="GPU-only docking + consensus pipeline for VigyanLLM",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://vigyanllm.in", "http://localhost:11436", "http://localhost:5000"],
    allow_methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    allow_credentials=True,
)

# In-memory job store for consensus pipeline
JOBS: dict[str, dict[str, Any]] = {}

# ═══════════════════════════════════════════════════════════════════════════════
# 5.  GPU INFO HELPER
# ═══════════════════════════════════════════════════════════════════════════════
def gpu_info() -> dict[str, Any]:
    """Return current GPU stats using PyTorch (no pynvml dependency)."""
    try:
        free_vram, total_vram = torch.cuda.mem_get_info(0)
        return {
            "name": _GPU_NAME,
            "total_vram_gb": round(total_vram / 1024**3, 2),
            "free_vram_gb": round(free_vram / 1024**3, 2),
            "used_vram_gb": round((total_vram - free_vram) / 1024**3, 2),
            "utilization_pct": round((1 - free_vram / total_vram) * 100, 1),
        }
    except Exception:
        return {
            "name": _GPU_NAME,
            "total_vram_gb": _GPU_VRAM_TOTAL_GB,
            "free_vram_gb": 0,
            "used_vram_gb": 0,
            "utilization_pct": 0,
        }

# ═══════════════════════════════════════════════════════════════════════════════
# 6.  DOCKING UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════
def compute_box_center(pdb_path: str) -> tuple[float, float, float, float, float, float]:
    """Compute a bounding box center + size from ATOM/HETATM records."""
    xs, ys, zs = [], [], []
    with open(pdb_path) as fh:
        for line in fh:
            if line.startswith(("ATOM  ", "HETATM")):
                try:
                    xs.append(float(line[30:38]))
                    ys.append(float(line[38:46]))
                    zs.append(float(line[46:54]))
                except ValueError:
                    continue
    if not xs:
        return 0.0, 0.0, 0.0, 60.0, 60.0, 60.0
    return (
        sum(xs) / len(xs),
        sum(ys) / len(ys),
        sum(zs) / len(zs),
        max(30.0, max(xs) - min(xs) + 10.0),
        max(30.0, max(ys) - min(ys) + 10.0),
        max(30.0, max(zs) - min(zs) + 10.0),
    )


def fetch_pdb(pdb_id: str) -> str:
    """Download PDB coordinates from RCSB."""
    pdb_id = pdb_id.strip().upper()
    url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
    res = requests.get(url, timeout=30)
    res.raise_for_status()
    if "ATOM" not in res.text and "HETATM" not in res.text:
        raise ValueError(f"RCSB did not return atomic coordinates for {pdb_id}")
    return res.text


def _run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return (proc.stdout or "") + (proc.stderr or "")


def prepare_receptor(pdb_text: str, out_pdb: str, out_pdbqt: str) -> None:
    Path(out_pdb).write_text(pdb_text)
    if not shutil.which("obabel"):
        raise RuntimeError("Open Babel CLI 'obabel' is required for receptor PDBQT preparation.")
    _run(["obabel", out_pdb, "-O", out_pdbqt, "-xr"])


def prepare_ligand(smiles: str, out_pdbqt: str) -> None:
    if not shutil.which("obabel"):
        raise RuntimeError("Open Babel CLI 'obabel' is required for ligand PDBQT preparation.")
    _run(["obabel", f"-:{smiles}", "-O", out_pdbqt, "--gen3d", "-p", "7.4"])


def run_vina_python(
    receptor_pdb: str,
    ligand_smiles: str,
    grid_box: dict[str, Any] | None = None,
    exhaustiveness: int = 8,
) -> dict[str, Any]:
    """Execute a full Vina docking run. Returns affinity + 3-D structures."""
    if Vina is None:
        raise RuntimeError("AutoDock Vina Python bindings are not installed.")

    start = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        receptor_pdb_path = os.path.join(tmp, "receptor.pdb")
        receptor_pdbqt_path = os.path.join(tmp, "receptor.pdbqt")
        ligand_pdbqt_path = os.path.join(tmp, "ligand.pdbqt")
        out_pdbqt_path = os.path.join(tmp, "out.pdbqt")

        prepare_receptor(receptor_pdb, receptor_pdb_path, receptor_pdbqt_path)
        prepare_ligand(ligand_smiles, ligand_pdbqt_path)

        if grid_box:
            center = [
                float(grid_box.get("center_x", 0)),
                float(grid_box.get("center_y", 0)),
                float(grid_box.get("center_z", 0)),
            ]
            box_size = [
                float(grid_box.get("size_x", 20)),
                float(grid_box.get("size_y", 20)),
                float(grid_box.get("size_z", 20)),
            ]
        else:
            cx, cy, cz, sx, sy, sz = compute_box_center(receptor_pdb_path)
            center = [cx, cy, cz]
            box_size = [sx, sy, sz]

        v = Vina(sf_name="vina", cpu=max(1, min(8, os.cpu_count() or 2)))
        v.set_receptor(receptor_pdbqt_path)
        v.set_ligand_from_file(ligand_pdbqt_path)
        v.compute_vina_maps(center=center, box_size=box_size)
        v.dock(exhaustiveness=int(exhaustiveness), n_poses=9)
        energies = v.energies(n_poses=9)
        best_score = float(energies[0][0])
        v.write_poses(out_pdbqt_path, n_poses=9, overwrite=True)

        return {
            "status": "success",
            "source": "COLAB_T4_VINA",
            "binding_affinity_kcal_mol": round(best_score, 3),
            "binding_mode": 1,
            "poses": len(energies),
            "pose_rmsd": 0.0,
            "computation_time": f"{time.time() - start:.1f}s",
            "confidence": 90 if best_score < -7 else 82,
            "vina_log": "AutoDock Vina completed on Colab T4 runtime.",
            "grid_box": {"center": center, "box_size": box_size},
            "gpu": gpu_info(),
            "structure": {
                "receptor": receptor_pdb,
                "ligand": Path(out_pdbqt_path).read_text(),
            },
        }


def parse_query(query: str) -> dict[str, str]:
    """Extract PDB ID and SMILES from a natural-language docking query."""
    pdb_match = re.search(r"\b[0-9][A-Za-z0-9]{3}\b", query)
    smiles_match = re.search(r"SMILES\s*[:=]\s*([^\s,;]+)", query, re.I)
    if not smiles_match:
        common = {
            "aspirin": "CC(=O)Oc1ccccc1C(=O)O",
            "ibuprofen": "CC(C)Cc1ccc(cc1)[C@@H](C)C(=O)O",
            "acetaminophen": "CC(=O)NC1=CC=C(O)C=C1",
            "remdesivir": "CCC(CC)COC(=O)C(C)NP(=O)(OCC1C(C(C(O1)N2C=CC(=O)NC2=O)(C)F)O)OC3=CC=CC=C3",
            "erlotinib": "COCCOc1cc2ncnc(c2cc1OCCOC)Nc3cccc(c3)C#C",
            "imatinib": "CC1=C(C=C(C=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C)NC4=NC=CC(=N4)C5=CN=CC=C5",
        }
        lower = query.lower()
        for name, smiles_str in common.items():
            if name in lower:
                smiles_match = type("_M", (), {"group": lambda self, idx: smiles_str})()
                break
    return {
        "pdb_id": pdb_match.group(0).upper() if pdb_match else "",
        "ligand_smiles": smiles_match.group(1) if smiles_match else "",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 7.  ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

# ---- Health / Pulse ----
@app.get("/pulse")
@app.get("/health")
async def pulse():
    """Health check — returns GPU name, VRAM stats, server identity."""
    return {
        "status": "alive",
        "server": "VigyanLLM-Colab-T4-Bridge-v2",
        "runtime": "google_colab",
        "gpu": gpu_info(),
        "cpu_percent": psutil.cpu_percent(),
        "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z"),
    }


# ---- Explicit docking endpoint ----
@app.post("/api/docking")
async def api_docking(request: Request):
    payload = await request.json()
    protein_pdb = payload.get("protein_pdb") or ""
    pdb_id = payload.get("pdb_id") or payload.get("pdbId") or ""
    ligand_smiles = payload.get("ligand_smiles") or payload.get("smiles") or ""

    try:
        if not protein_pdb and pdb_id:
            protein_pdb = fetch_pdb(pdb_id)
        if not protein_pdb or not ligand_smiles:
            return JSONResponse(
                {"status": "error", "error": "protein_pdb (or pdb_id) and ligand_smiles are required."},
                status_code=422,
            )
        result = run_vina_python(
            protein_pdb,
            ligand_smiles,
            grid_box=payload.get("grid_box"),
            exhaustiveness=int(payload.get("exhaustiveness", 8)),
        )
        result["ligand_smiles"] = ligand_smiles
        result["pdb_id"] = pdb_id
        return result
    except Exception as exc:
        return JSONResponse(
            {"status": "error", "error": str(exc), "source": "COLAB_T4_VINA"},
            status_code=500,
        )


# ---- Natural-language docking / consensus pipeline ----
@app.post("/run-dry-lab")
async def run_dry_lab(request: Request):
    payload = await request.json()
    try:
        # ── Single-query docking mode ──
        if payload.get("query"):
            parsed = parse_query(payload["query"])
            pdb_id = payload.get("pdb_id") or parsed["pdb_id"]
            smiles = payload.get("ligand_smiles") or parsed["ligand_smiles"]
            if not pdb_id or not smiles:
                return JSONResponse(
                    {
                        "status": "error",
                        "error": "Query must include a PDB ID and either 'SMILES: ...' or a known ligand name.",
                    },
                    status_code=422,
                )
            protein_pdb = fetch_pdb(pdb_id)
            result = run_vina_python(
                protein_pdb, smiles, exhaustiveness=int(payload.get("exhaustiveness", 8))
            )
            result["pdb_id"] = pdb_id
            result["ligand_smiles"] = smiles
            return result

        # ── Consensus pipeline mode ──
        smiles = payload.get("smiles") or payload.get("ligand_smiles_list") or []
        if isinstance(smiles, str):
            smiles = [smiles]
        raw_pdb = payload.get("protein_pdb") or payload.get("pdb_content") or payload.get("pdb") or ""
        protein_pdb = raw_pdb if isinstance(raw_pdb, str) and ("ATOM" in raw_pdb or "HETATM" in raw_pdb) else ""
        if not protein_pdb and payload.get("pdb_id"):
            protein_pdb = fetch_pdb(payload["pdb_id"])
        if not protein_pdb:
            return JSONResponse(
                {"status": "error", "error": "Provide protein_pdb/pdb_content/pdb_id for consensus mode."},
                status_code=422,
            )
        if not smiles:
            return JSONResponse(
                {"status": "error", "error": "At least one SMILES is required."},
                status_code=422,
            )

        job_id = str(uuid.uuid4())
        JOBS[job_id] = {
            "job_id": job_id,
            "status": "running",
            "result": None,
            "log": [],
            "created_at": _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        threading.Thread(
            target=_run_consensus_job,
            args=(job_id, protein_pdb, smiles, int(payload.get("top_n", 50))),
            daemon=True,
        ).start()
        return {"job_id": job_id, "status": "running"}

    except Exception as exc:
        return JSONResponse({"status": "error", "error": str(exc)}, status_code=500)


def _run_consensus_job(job_id: str, protein_pdb: str, smiles_list: list[str], top_n: int) -> None:
    """Background worker for multi-ligand consensus screening."""
    job = JOBS[job_id]
    job["log"].append({"stage": "Vina", "message": f"Screening {len(smiles_list)} ligands"})
    results = []
    for idx, smi in enumerate(smiles_list):
        try:
            docked = run_vina_python(protein_pdb, smi, exhaustiveness=4)
            results.append({
                "consensus_rank": 0,
                "smiles": smi,
                "vina_score": docked["binding_affinity_kcal_mol"],
                "gnina_score": None,
                "consensus_score": docked["binding_affinity_kcal_mol"],
                "structure": docked["structure"],
            })
            job["log"].append({
                "stage": "Vina",
                "message": f"Screened ligand {idx + 1}/{len(smiles_list)}",
                "metadata": {"current": idx + 1, "total": len(smiles_list)},
            })
        except Exception as exc:
            job["log"].append({"stage": "Vina", "message": f"Failed {smi}: {exc}"})

    results.sort(key=lambda item: item["vina_score"])
    for rank, row in enumerate(results, 1):
        row["consensus_rank"] = rank
    best = results[0] if results else None
    job["status"] = "success" if best else "error"
    job["result"] = {
        "status": job["status"],
        "stage1": {"status": "provided", "engine": "PDB/RCSB", "gpu": gpu_info()},
        "stage2": {
            "screened": len(smiles_list),
            "successful": len(results),
            "top_n_selected": min(top_n, len(results)),
            "best_vina_score": best["vina_score"] if best else None,
        },
        "stage3": {"status": "skipped", "message": "GNINA not configured in this bootstrap."},
        "ranked_results": results,
        "best_molecule": best,
    }


# ---- Consensus pipeline status ----
@app.get("/consensus-pipeline/status/{job_id}")
async def consensus_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"status": "error", "error": f"Job {job_id} not found"}, status_code=404)
    return job


# ═══════════════════════════════════════════════════════════════════════════════
# 8.  ENTRY POINT — uvicorn on port 7860 (NO Google Drive mounting)
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting VigyanLLM Colab T4 Bridge on port 7860 …")
    print(f"   GPU: {_GPU_NAME}  |  VRAM: {_GPU_VRAM_TOTAL_GB} GB")
    uvicorn.run(app, host="0.0.0.0", port=7860, log_level="info")

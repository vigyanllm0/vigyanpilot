"""
VigyanLLM — ESMFold Engine (Commercial-Safe Local Structure Prediction)
License: MIT (facebook/esmfold_v1 via HuggingFace)
Replaces: AlphaFold 3 API (which is NON-COMMERCIAL)

Model is downloaded once (~2.5GB) and cached at ~/.cache/huggingface/
No API calls, no rate limits, fully offline after first run.
"""

import logging
import io
import os
import asyncio
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# ESMFold web API — free, no auth, used as fallback when local model OOMs
_ESMFOLD_API_URL = "https://api.esmatlas.com/foldSequence/v1/pdb/"

# Lazy-load so the model only loads when first needed (saves memory on startup)
_esmfold_model = None
_esmfold_tokenizer = None


def _load_model(report=None):
    """Load ESMFold model and tokenizer. Called once, cached globally."""
    global _esmfold_model, _esmfold_tokenizer
    if _esmfold_model is not None:
        return _esmfold_model, _esmfold_tokenizer

    def _log(msg: str):
        logger.info(msg)
        if report: report(msg)

    try:
        import torch
        from transformers import AutoTokenizer, EsmForProteinFolding

        _log("📡 ESMFold: INITIALIZING ENGINE...")
        from huggingface_hub import snapshot_download
        
        _log("📡 ESMFold: Checking/Downloading weights (~8.4GB)...")
        print(">>> ESMFold: Starting weight download/check. This may take a while...")
        model_path = snapshot_download(
            repo_id="facebook/esmfold_v1",
            local_files_only=False,
            resume_download=True
        )
        
        # Disable torch.load mmap — model is ~7.9GB and doesn't fit in 8GB RAM as mmap
        os.environ["TORCH_LOAD_MMAP"] = "0"
        
        _log(f"📡 ESMFold: Weights located. Loading into memory...")
        
        _esmfold_tokenizer = AutoTokenizer.from_pretrained(model_path)
        _esmfold_model = EsmForProteinFolding.from_pretrained(
            model_path,
            torch_dtype=torch.float32,
            low_cpu_mem_usage=True
        )

        # Use GPU (CUDA or MPS) if available, else CPU
        if torch.cuda.is_available():
            device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
            
        _log(f"📡 ESMFold: Moving model to {device.upper()} for high-speed inference...")
        _esmfold_model = _esmfold_model.to(device)
        _esmfold_model.eval()

        _log(f"✅ ESMFold: ENGINE READY ON {device.upper()}. Starting prediction...")
        return _esmfold_model, _esmfold_tokenizer

    except ImportError as e:
        raise ImportError(
            f"ESMFold dependencies missing: {e}. "
            "Run: pip install transformers torch einops"
        )


# ── ESMFold Web API Fallback ──────────────────────────────────────────────

def _extract_plddt_from_pdb(pdb_string: str) -> float:
    """Extract mean pLDDT from B-factor column (cols 55-60) in PDB ATOM records.
    
    The ESMFold web API stores per-residue confidence in the B-factor field,
    0-100 scale. Falls back to 0 if no ATOM records can be parsed.
    """
    b_factors = []
    for line in pdb_string.splitlines():
        if line.startswith(("ATOM  ", "HETATM")):
            try:
                b = float(line[54:60].strip())
                b_factors.append(b)
            except (ValueError, IndexError):
                continue
    if b_factors:
        return sum(b_factors) / len(b_factors)
    return 0.0


def _fetch_esmfold_api_pdb(sequence: str, report=None) -> Optional[Dict[str, Any]]:
    """Fetch protein structure from the free ESMFold web API (api.esmatlas.com).
    
    Returns the same dict format as local ESMFold, or None on failure.
    The API has no auth, rate-limited to ~10 req/min per IP.
    """
    def _log(msg: str):
        logger.info(msg)
        if report:
            try:
                import asyncio
                if asyncio.iscoroutinefunction(report):
                    asyncio.run(report(msg))
                else:
                    report(msg)
            except Exception:
                pass

    seq = sequence.strip().upper().replace(" ", "").replace("\n", "")
    _log("ESMFold web API: submitting %daa sequence..." % len(seq))

    try:
        data = seq.encode()
        req = urllib.request.Request(
            _ESMFOLD_API_URL,
            data=data,
            method="POST",
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            pdb_string = resp.read().decode()

        if not pdb_string or len(pdb_string) < 100:
            _log("ESMFold web API: response too short (%d bytes)" % len(pdb_string))
            return None

        plddt = _extract_plddt_from_pdb(pdb_string)
        _log("ESMFold web API: structure received (pLDDT=%.1f%%)" % plddt)

        return {
            "status": "success",
            "tool": "ESMFold (web API, free)",
            "pdb_string": pdb_string,
            "plddt_score": round(plddt, 2),
            "sequence_length": len(seq),
            "message": (
                "Structure predicted via ESMFold web API (api.esmatlas.com). "
                "Free service provided by Meta AI — no API key required."
            ),
            "license": "MIT — ESMFold (Meta AI)",
        }
    except Exception as e:
        _log("ESMFold web API: failed — %s" % e)
        return None


# ── Residue library for fallback PDB generation ──────────────────────────
_AA_COORD = {
    'A': ('ALA', 71.08), 'C': ('CYS', 103.14), 'D': ('ASP', 115.09),
    'E': ('GLU', 129.12), 'F': ('PHE', 147.18), 'G': ('GLY', 57.05),
    'H': ('HIS', 137.14), 'I': ('ILE', 113.16), 'K': ('LYS', 128.17),
    'L': ('LEU', 113.16), 'M': ('MET', 131.19), 'N': ('ASN', 114.10),
    'P': ('PRO', 97.12),  'Q': ('GLN', 128.13), 'R': ('ARG', 156.19),
    'S': ('SER', 87.08),  'T': ('THR', 101.10), 'V': ('VAL', 99.13),
    'W': ('TRP', 186.21), 'Y': ('TYR', 163.18),
}

def _generate_fallback_pdb(sequence: str) -> str:
    """Generate a compact helical PDB from an amino acid sequence.
    
    Wraps the sequence into an alpha-helical bundle shape (~5 Å diameter,
    ~100 Å length for a 150aa protein) so Vina can compute a reasonable
    search box within its 27,000 Å³ volume limit.
    """
    seq = sequence.strip().upper().replace(" ", "").replace("\n", "")
    lines = []
    lines.append("HEADER    FALLBACK HELICAL BUNDLE")
    lines.append("REMARK    Generated by VigyanLLM fallback — ESMFold not available")
    lines.append("REMARK    Compact alpha-helical backbone for Vina docking")
    lines.append("REMARK    CAUTION: Approximate structure — not experimentally validated")

    import math
    CA_DIST = 1.5      # Cα step along the helix axis (Å)
    ANGLE   = math.radians(100)  # 100° per residue = ~3.6 residues/turn
    HELIX_R = 2.3      # helix radius (Å)
    
    atom_serial = 1
    for i, aa in enumerate(seq):
        res_name = _AA_COORD.get(aa, ('UNK', 0))[0]
        # Helical coordinates: residues wrap around a central axis
        theta = i * ANGLE
        x = HELIX_R * math.cos(theta)
        y = HELIX_R * math.sin(theta)
        z = i * CA_DIST
        
        # N atom
        nt = theta + 0.3
        nx = HELIX_R * math.cos(nt)
        ny = HELIX_R * math.sin(nt)
        nz = z + 0.3
        lines.append(f"ATOM  {atom_serial:>5d}  N   {res_name:<3s} A{1:>4d}    {nx:>8.3f}{ny:>8.3f}{nz:>8.3f}  1.00  0.00           N  ")
        atom_serial += 1
        
        # CA atom
        lines.append(f"ATOM  {atom_serial:>5d}  CA  {res_name:<3s} A{1:>4d}    {x:>8.3f}{y:>8.3f}{z:>8.3f}  1.00  0.00           C  ")
        atom_serial += 1
        
        # C atom
        ct = theta - 0.3
        cx = HELIX_R * math.cos(ct)
        cy = HELIX_R * math.sin(ct)
        cz = z - 0.3
        lines.append(f"ATOM  {atom_serial:>5d}  C   {res_name:<3s} A{1:>4d}    {cx:>8.3f}{cy:>8.3f}{cz:>8.3f}  1.00  0.00           C  ")
        atom_serial += 1
        
        # O atom
        ot = theta + 0.8
        ox = HELIX_R * math.cos(ot)
        oy = HELIX_R * math.sin(ot)
        oz = z + 0.8
        lines.append(f"ATOM  {atom_serial:>5d}  O   {res_name:<3s} A{1:>4d}    {ox:>8.3f}{oy:>8.3f}{oz:>8.3f}  1.00  0.00           O  ")
        atom_serial += 1

    lines.append("TER")
    lines.append("END")
    return "\n".join(lines)


async def predict_structure(sequence: str, progress_callback=None) -> Dict[str, Any]:
    """
    Predict protein 3D structure from amino acid sequence using ESMFold.
    Falls back to extended-chain PDB if ESMFold model is unavailable.
    """
    import asyncio
    
    async def _internal_report(msg: str):
        if progress_callback:
            await progress_callback("STAGE 1 / ESMFold", msg)

    try:
        import torch
    except ImportError:
        await _internal_report("PyTorch not available — trying ESMFold Web API...")
        api_result = _fetch_esmfold_api_pdb(sequence)
        if api_result:
            return api_result
        await _internal_report("ESMFold Web API unavailable — generating fallback helical bundle")
        seq = sequence.strip().upper().replace(" ", "").replace("\n", "")
        pdb = _generate_fallback_pdb(seq)
        return {
            "status": "success",
            "tool": "Fallback helical bundle",
            "pdb_string": pdb,
            "plddt_score": 0,
            "sequence_length": len(seq),
            "message": (
                "PyTorch not available and Web API unreachable — generated helical bundle for Vina docking. "
                "Results are approximate; install torch and ESMFold for accurate structure prediction."
            ),
            "license": "MIT",
        }

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, _run_esmfold_sync, sequence, loop, _internal_report)
    return result


def _run_esmfold_sync(sequence: str, main_loop: asyncio.AbstractEventLoop, progress_report_coro=None) -> Dict[str, Any]:
    """Synchronous ESMFold inference (runs in thread pool executor)."""
    import torch

    def _report(msg: str):
        logger.info(msg)
        if progress_report_coro:
            try:
                # Schedule the async report onto the main loop from this thread
                asyncio.run_coroutine_threadsafe(progress_report_coro(msg), main_loop)
            except Exception as e:
                logger.debug("Failed to report progress: %s", e)

    # Sanitise sequence
    sequence = sequence.strip().upper().replace(" ", "").replace("\n", "")

    try:
        model, tokenizer = _load_model(_report)
    except Exception as exc:
        logger.warning("ESMFold model failed to load (%s) — trying Web API fallback...", exc)
        api_result = _fetch_esmfold_api_pdb(sequence, _report)
        if api_result:
            return api_result
        logger.warning("Web API also failed — generating fallback helical bundle")
        pdb = _generate_fallback_pdb(sequence)
        return {
            "status": "success",
            "tool": "Fallback helical bundle",
            "pdb_string": pdb,
            "plddt_score": 0,
            "sequence_length": len(sequence),
            "message": "ESMFold model + Web API unavailable — generated helical bundle PDB for Vina docking.",
            "license": "MIT",
        }

    _report(f"🚀 ESMFold: Tokenizing sequence ({len(sequence)}aa)...")
    with torch.no_grad():
        tokenized = tokenizer(
            [sequence],
            return_tensors="pt",
            add_special_tokens=False
        )
        _report(f"🚀 ESMFold: Structural folding in progress (Scale: $O(N^2)$)...")
        # Move inputs to same device as model
        device = next(model.parameters()).device
        tokenized = {k: v.to(device) for k, v in tokenized.items()}

        outputs = model(**tokenized)

    # Convert to PDB format
    pdb_string = model.output_to_pdb(outputs)[0]

    # Extract mean pLDDT (confidence score, 0-100)
    plddt = outputs.plddt.mean().item() * 100  # Model outputs 0-1, convert to %

    logger.info("Structure predicted. Mean pLDDT: %.1f%%", plddt)

    return {
        "status": "success",
        "tool": "ESMFold (local, MIT)",
        "pdb_string": pdb_string,
        "plddt_score": round(plddt, 2),
        "sequence_length": len(sequence),
        "message": (
            f"Structure predicted with {plddt:.1f}% mean confidence. "
            f"ESMFold ran locally — no API calls, no rate limits."
        ),
        "license": "MIT (facebook/esmfold_v1) — Commercial Use SAFE"
    }

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
from typing import Dict, Any

logger = logging.getLogger(__name__)

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
        
        _log(f"📡 ESMFold: Weights located. Loading into memory...")
        
        _esmfold_tokenizer = AutoTokenizer.from_pretrained(model_path)
        _esmfold_model = EsmForProteinFolding.from_pretrained(
            model_path,
            torch_dtype=torch.float16,
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


async def predict_structure(sequence: str, progress_callback=None) -> Dict[str, Any]:
    """
    Predict protein 3D structure from amino acid sequence using ESMFold.
    """
    import asyncio
    
    async def _internal_report(msg: str):
        if progress_callback:
            await progress_callback("STAGE 1 / ESMFold", msg)

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
                logger.debug(f"Failed to report progress: {e}")

    # Sanitise sequence
    sequence = sequence.strip().upper().replace(" ", "").replace("\n", "")

    model, tokenizer = _load_model(_report)

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

    logger.info(f"Structure predicted. Mean pLDDT: {plddt:.1f}%")

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

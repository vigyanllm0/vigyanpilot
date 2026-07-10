"""
Pipeline warm-up — pre-loads all heavy modules and models at startup
to prevent cold-start delays on the first job.
"""

import logging
import time

logger = logging.getLogger(__name__)


def warmup_all():
    """Import and pre-warm all heavy dependencies used by the pipeline."""
    t0 = time.time()
    logger.info("Warm-up: starting (importing heavy modules)...")

    _warmup_torch()
    _warmup_esmfold()
    _warmup_rdkit()
    _warmup_docking_binaries()

    elapsed = time.time() - t0
    logger.info("Warm-up: complete in %.1fs", elapsed)


def _warmup_torch():
    """Pre-import PyTorch (heavy ~2GB)."""
    try:
        import torch
        logger.info("Warm-up: torch %s loaded (device: %s)", torch.__version__, torch.device('cuda' if torch.cuda.is_available() else 'cpu'))
    except Exception as e:
        logger.warning("Warm-up: torch import failed: %s", e)


def _warmup_esmfold():
    """Pre-load ESMFold model into memory (~8.4GB)."""
    try:
        from primerforge.pipelines.esmfold_engine import _load_model
        _load_model()
        logger.info("Warm-up: ESMFold model loaded into memory")
    except Exception as e:
        logger.warning("Warm-up: ESMFold model load failed: %s", e)


def _warmup_rdkit():
    """Pre-import RDKit and Meeko."""
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
        from meeko import MoleculePreparation
        logger.info("Warm-up: RDKit and Meeko imported")
    except Exception as e:
        logger.warning("Warm-up: RDKit/Meeko import failed: %s", e)


def _warmup_docking_binaries():
    """Verify Vina and GNINA binaries are available."""
    import shutil
    vina = shutil.which("vina")
    gnina = shutil.which("gnina")
    obabel = shutil.which("obabel")
    logger.info("Warm-up: binaries — vina=%s, gnina=%s, obabel=%s", vina, gnina, obabel)

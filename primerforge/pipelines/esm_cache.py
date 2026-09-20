"""
VigyanLLM — ESMFold Result Cache

Caches ESMFold predictions to avoid re-folding identical sequences.
Uses file-based cache with SHA-256 hash keys.

Usage:
    from esm_cache import get_cached_structure, cache_structure
    result = get_cached_structure(sequence)
    if not result:
        result = fold_protein(sequence)
        cache_structure(sequence, result)
"""

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Cache directory
CACHE_DIR = Path(os.environ.get('ESM_CACHE_DIR', '/tmp/vigyanllm_esm_cache'))
CACHE_MAX_AGE_DAYS = 30  # Cache entries expire after 30 days
CACHE_MAX_ENTRIES = 10000  # Maximum cache entries


def _sequence_hash(sequence: str) -> str:
    """Generate SHA-256 hash of amino acid sequence."""
    # Normalize: uppercase, strip whitespace, remove common prefixes
    seq = sequence.upper().replace(' ', '').replace('\n', '').replace('\r', '')
    # Remove common FASTA headers
    if '>' in seq:
        seq = seq.split('>')[-1]
        if '\n' in seq:
            seq = seq.split('\n', 1)[1]
    return hashlib.sha256(seq.encode()).hexdigest()[:16]


def _cache_path(seq_hash: str) -> Path:
    """Get cache file path for a sequence hash."""
    return CACHE_DIR / f"{seq_hash}.json"


def get_cached_structure(sequence: str) -> Optional[dict]:
    """
    Look up cached ESMFold result for a sequence.

    Returns:
        Cached result dict or None if not found/expired.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    seq_hash = _sequence_hash(sequence)
    path = _cache_path(seq_hash)

    if not path.exists():
        return None

    try:
        with open(path) as f:
            data = json.load(f)

        # Check expiry
        cached_at = data.get('cached_at', 0)
        age_days = (time.time() - cached_at) / 86400
        if age_days > CACHE_MAX_AGE_DAYS:
            logger.info("Cache expired for %s (%.1f days old)", seq_hash, age_days)
            path.unlink()
            return None

        logger.info("Cache hit for %s (%.1f days old)", seq_hash, age_days)
        data['cache_hit'] = True
        return data

    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Corrupt cache entry %s: %s", seq_hash, e)
        path.unlink()
        return None


def cache_structure(sequence: str, result: dict) -> bool:
    """
    Store ESMFold result in cache.

    Args:
        sequence: Amino acid sequence
        result: ESMFold result dict (pdb_string, plddt_scores, etc.)

    Returns:
        True if cached successfully.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Evict old entries if at capacity
    _evict_if_needed()

    seq_hash = _sequence_hash(sequence)
    path = _cache_path(seq_hash)

    data = dict(result)
    data['cached_at'] = time.time()
    data['sequence_hash'] = seq_hash
    data['sequence_length'] = len(sequence.replace(' ', '').replace('\n', ''))
    data['cache_hit'] = False

    try:
        with open(path, 'w') as f:
            json.dump(data, f)
        logger.info("Cached ESMFold result for %s (%d aa)", seq_hash, data['sequence_length'])
        return True
    except Exception as e:
        logger.error("Failed to cache: %s", e)
        return False


def _evict_if_needed():
    """Evict oldest entries if cache is full."""
    if not CACHE_DIR.exists():
        return

    entries = list(CACHE_DIR.glob('*.json'))
    if len(entries) < CACHE_MAX_ENTRIES:
        return

    # Sort by modification time (oldest first)
    entries.sort(key=lambda p: p.stat().st_mtime)

    # Remove oldest 10%
    to_remove = entries[:len(entries) // 10]
    for path in to_remove:
        try:
            path.unlink()
        except OSError:
            pass

    logger.info("Evicted %d cache entries", len(to_remove))


def cache_stats() -> dict:
    """Get cache statistics."""
    if not CACHE_DIR.exists():
        return {'entries': 0, 'total_size_mb': 0}

    entries = list(CACHE_DIR.glob('*.json'))
    total_size = sum(e.stat().st_size for e in entries)

    return {
        'entries': len(entries),
        'total_size_mb': round(total_size / 1048576, 2),
        'cache_dir': str(CACHE_DIR),
        'max_entries': CACHE_MAX_ENTRIES,
        'max_age_days': CACHE_MAX_AGE_DAYS,
    }


def clear_cache():
    """Clear all cached entries."""
    if not CACHE_DIR.exists():
        return 0

    count = 0
    for path in CACHE_DIR.glob('*.json'):
        try:
            path.unlink()
            count += 1
        except OSError:
            pass

    logger.info("Cleared %d cache entries", count)
    return count

"""
Sequence Caching Layer
========================
PostgreSQL-backed cache with 7-day TTL for external sequence fetches.
Reduces API calls to NCBI/Ensembl/NCBI Virus/ENA/DDBJ.
"""

import json
import logging
from typing import Optional

from .sequence_retrieval import SequenceRecord

logger = logging.getLogger(__name__)


def get_cached(source: str, query_key: str) -> Optional[SequenceRecord]:
    """
    Check cache for a sequence. Returns SequenceRecord if found and not expired.
    """
    try:
        from primerforge.database import fetch_one
        row = fetch_one(
            """SELECT sequence, metadata FROM sequence_cache
               WHERE source = %s AND query_key = %s AND expires_at > NOW()""",
            (source, query_key)
        )
        if row and row.get("sequence"):
            metadata = row["metadata"] if isinstance(row["metadata"], dict) else {}
            return SequenceRecord(
                id=query_key,
                source=source,
                accession=query_key,
                sequence=row["sequence"],
                description=metadata.get("description", ""),
                length=len(row["sequence"]),
                metadata=metadata,
                exon_map=metadata.get("exon_map", []),
                transcripts=metadata.get("transcripts", []),
            )
    except Exception as e:
        logger.debug("Cache lookup failed: %s", e)
    return None


def store_cached(record: SequenceRecord) -> None:
    """Store a SequenceRecord in the cache with 7-day TTL."""
    try:
        from primerforge.database import execute
        metadata = dict(record.metadata)
        metadata["description"] = record.description
        metadata["exon_map"] = record.exon_map
        metadata["transcripts"] = record.transcripts

        execute(
            """INSERT INTO sequence_cache (source, query_key, sequence, metadata)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (source, query_key) DO UPDATE SET
                 sequence = EXCLUDED.sequence,
                 metadata = EXCLUDED.metadata,
                 fetched_at = NOW(),
                 expires_at = NOW() + INTERVAL '7 days'""",
            (record.source, record.accession, record.sequence, json.dumps(metadata))
        )
    except Exception as e:
        logger.debug("Cache store failed: %s", e)


def fetch_with_cache(query: str, source: str = "auto", **kwargs) -> SequenceRecord:
    """
    Fetch a sequence, checking cache first. If cache miss, fetch from API and store.
    """
    from .sequence_retrieval import fetch_sequence, detect_source

    if source == "auto":
        source = detect_source(query) or "ncbi"

    # Check cache
    cached = get_cached(source, query)
    if cached and cached.sequence:
        logger.info("Cache HIT: %s/%s", source, query)
        return cached

    # Cache miss — fetch from API
    logger.info("Cache MISS: %s/%s — fetching from API", source, query)
    record = fetch_sequence(query, source, **kwargs)

    # Store in cache
    if record.sequence:
        store_cached(record)

    return record

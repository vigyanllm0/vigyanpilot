"""
Step 1: Transcript Isoform Filter
====================================
Retrieve all transcript isoforms for the target locus from Ensembl/GENCODE.
Supports two modes:
  - common_exon: identifies exons shared across ALL isoforms (targets conserved regions)
  - isoform_specific: identifies regions unique to a single isoform (targets distinguishing regions)

Output: target regions with transcript IDs and exon boundaries for downstream primer design.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def execute(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Step 1: Fetch sequence and filter isoforms.

    Input keys:
        - sequence (str): Raw DNA sequence (if provided directly)
        - accession (str): Gene ID / accession to fetch (if no raw sequence)
        - gene_symbol (str): Gene symbol (alternative to accession)
        - targeting_mode (str): 'common_exon' or 'isoform_specific'
        - target_transcript (str, optional): Specific transcript ID for isoform_specific mode
        - organism (str): Species identifier (default 'human')

    Output keys:
        - target_sequence (str): Final target sequence for design
        - exon_map (list): Exon coordinates [{start, end, exon_id, transcript_id}]
        - transcripts (list): All available transcript records
        - selected_regions (list): Regions selected for primer design
        - targeting_mode (str): Mode used
        - sequence_length (int): Length of the target sequence
        - isoform_count (int): Number of isoforms found
    """
    sequence = input_data.get("sequence", "")
    accession = input_data.get("accession", "")
    gene_symbol = input_data.get("gene_symbol", "")
    targeting_mode = input_data.get("targeting_mode", "common_exon")
    target_transcript = input_data.get("target_transcript", "")
    organism = input_data.get("organism", "human")

    transcripts: list[dict[str, Any]] = []
    exon_map: list[dict[str, Any]] = []

    # ── Fetch sequence and transcript data ─────────────────────────────────
    if not sequence and (accession or gene_symbol):
        query = accession or gene_symbol
        try:
            from ..sequence_cache import fetch_with_cache
            record = fetch_with_cache(query)
            sequence = record.sequence
            exon_map = getattr(record, "exon_map", []) or []
            transcripts = getattr(record, "transcripts", []) or []
        except Exception as e:
            logger.warning("Sequence fetch failed for '%s': %s", query, e)
            # Try Ensembl REST API as fallback
            transcripts, exon_map, fetched_seq = _fetch_ensembl_transcripts(
                query, organism
            )
            if fetched_seq:
                sequence = fetched_seq
    else:
        # User-provided sequence: extract any embedded transcript info
        exon_map = input_data.get("exon_map", [])
        transcripts = input_data.get("transcripts", [])

    if not sequence:
        raise ValueError(
            "No sequence available after fetching. "
            "Check accession/gene_symbol or provide raw sequence."
        )

    # ── Apply isoform filtering ────────────────────────────────────────────
    if targeting_mode == "isoform_specific":
        selected_regions = _isoform_specific_regions(
            transcripts, exon_map, target_transcript, len(sequence)
        )
    else:
        # Default: common_exon mode
        selected_regions = _common_exon_regions(
            transcripts, exon_map, len(sequence)
        )

    # Ensure at least one region exists (fallback to full sequence)
    if not selected_regions:
        logger.info("No specific regions identified — using full sequence as target.")
        selected_regions = [{"start": 0, "end": len(sequence), "type": "full_sequence"}]

    return {
        "target_sequence": sequence,
        "exon_map": exon_map,
        "transcripts": transcripts,
        "selected_regions": selected_regions,
        "targeting_mode": targeting_mode,
        "sequence_length": len(sequence),
        "isoform_count": len(transcripts) if transcripts else 1,
    }


# ---------------------------------------------------------------------------
# Common Exon Mode — identify exon regions shared by ALL isoforms
# ---------------------------------------------------------------------------

def _common_exon_regions(
    transcripts: list[dict[str, Any]],
    exon_map: list[dict[str, Any]],
    seq_length: int,
) -> list[dict[str, Any]]:
    """
    Identify exonic regions that are present in ALL transcript isoforms.
    These are the most conserved and reliable regions for primer design.
    """
    if not transcripts or len(transcripts) < 2:
        # Only one transcript (or no transcript data) — all exons are "common"
        if exon_map:
            return [
                {
                    "start": ex.get("start", 0),
                    "end": ex.get("end", 0),
                    "type": "common_exon",
                    "exon_id": ex.get("exon_id", f"exon_{i+1}"),
                    "shared_by": 1,
                }
                for i, ex in enumerate(exon_map)
            ]
        return [{"start": 0, "end": seq_length, "type": "full_sequence"}]

    # Group exons by transcript
    transcript_exon_sets: dict[str, list[tuple[int, int]]] = {}
    for exon in exon_map:
        tid = exon.get("transcript_id", "unknown")
        start = exon.get("start", 0)
        end = exon.get("end", 0)
        if tid not in transcript_exon_sets:
            transcript_exon_sets[tid] = []
        transcript_exon_sets[tid].append((start, end))

    if not transcript_exon_sets:
        return [{"start": 0, "end": seq_length, "type": "full_sequence"}]

    # Find overlapping regions present in ALL transcripts using interval intersection
    # Build a position-level coverage map
    all_tids = list(transcript_exon_sets.keys())
    n_transcripts = len(all_tids)

    # Use a sweep-line approach: count how many transcripts cover each position
    events: list[tuple[int, int]] = []  # (position, +1 or -1)
    for tid, exons in transcript_exon_sets.items():
        merged = _merge_intervals(exons)
        for start, end in merged:
            events.append((start, +1))
            events.append((end, -1))

    events.sort(key=lambda x: (x[0], -x[1]))  # sort by position, ends before starts at same pos

    # Alternative: use per-transcript interval sets to find common regions
    # Convert each transcript's exons into a set of covered positions (efficient interval)
    common_intervals = _intersect_all_transcripts(transcript_exon_sets, seq_length)

    regions = []
    for start, end in common_intervals:
        if end - start >= 20:  # Minimum 20nt for a useful target region
            regions.append({
                "start": start,
                "end": end,
                "type": "common_exon",
                "shared_by": n_transcripts,
            })

    return regions


def _intersect_all_transcripts(
    transcript_exon_sets: dict[str, list[tuple[int, int]]],
    seq_length: int,
) -> list[tuple[int, int]]:
    """Find intervals covered by ALL transcripts using successive intersection."""
    all_tids = list(transcript_exon_sets.keys())
    if not all_tids:
        return []

    # Start with the first transcript's merged intervals
    current = _merge_intervals(transcript_exon_sets[all_tids[0]])

    # Intersect with each subsequent transcript
    for tid in all_tids[1:]:
        other = _merge_intervals(transcript_exon_sets[tid])
        current = _intersect_intervals(current, other)
        if not current:
            break

    return current


def _intersect_intervals(
    a: list[tuple[int, int]], b: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    """Compute intersection of two sorted interval lists."""
    result = []
    i, j = 0, 0
    while i < len(a) and j < len(b):
        start = max(a[i][0], b[j][0])
        end = min(a[i][1], b[j][1])
        if start < end:
            result.append((start, end))
        # Advance the interval that ends first
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return result


def _merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping intervals into non-overlapping sorted list."""
    if not intervals:
        return []
    sorted_ivs = sorted(intervals, key=lambda x: x[0])
    merged = [sorted_ivs[0]]
    for start, end in sorted_ivs[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


# ---------------------------------------------------------------------------
# Isoform-Specific Mode — identify regions unique to a single isoform
# ---------------------------------------------------------------------------

def _isoform_specific_regions(
    transcripts: list[dict[str, Any]],
    exon_map: list[dict[str, Any]],
    target_transcript: str,
    seq_length: int,
) -> list[dict[str, Any]]:
    """
    Identify regions unique to a specific isoform (not present in other isoforms).
    Useful for designing primers that specifically detect one splice variant.
    """
    if not transcripts or not exon_map:
        return [{"start": 0, "end": seq_length, "type": "isoform_specific"}]

    # Group exons by transcript
    transcript_exon_sets: dict[str, list[tuple[int, int]]] = {}
    for exon in exon_map:
        tid = exon.get("transcript_id", "unknown")
        start = exon.get("start", 0)
        end = exon.get("end", 0)
        if tid not in transcript_exon_sets:
            transcript_exon_sets[tid] = []
        transcript_exon_sets[tid].append((start, end))

    # If no target specified, use the first transcript
    if not target_transcript:
        if transcripts:
            target_transcript = transcripts[0].get("transcript_id", "")
        if not target_transcript and transcript_exon_sets:
            target_transcript = list(transcript_exon_sets.keys())[0]

    target_exons = transcript_exon_sets.get(target_transcript, [])
    if not target_exons:
        logger.warning(
            f"Target transcript '{target_transcript}' not found in exon map. "
            "Using full sequence."
        )
        return [{"start": 0, "end": seq_length, "type": "isoform_specific"}]

    target_merged = _merge_intervals(target_exons)

    # Collect all OTHER transcripts' exons
    other_intervals: list[tuple[int, int]] = []
    for tid, exons in transcript_exon_sets.items():
        if tid != target_transcript:
            other_intervals.extend(exons)

    if not other_intervals:
        # No other transcripts — everything is "unique"
        return [
            {
                "start": s,
                "end": e,
                "type": "isoform_specific",
                "transcript_id": target_transcript,
            }
            for s, e in target_merged
        ]

    other_merged = _merge_intervals(other_intervals)

    # Subtract other intervals from target intervals to find unique regions
    unique_regions = _subtract_intervals(target_merged, other_merged)

    regions = []
    for start, end in unique_regions:
        if end - start >= 20:  # Minimum 20nt for a useful target region
            regions.append({
                "start": start,
                "end": end,
                "type": "isoform_specific",
                "transcript_id": target_transcript,
                "unique_length": end - start,
            })

    # If no unique regions found, fall back to target exons with a warning
    if not regions:
        logger.info(
            f"No unique regions ≥20nt found for transcript {target_transcript}. "
            "Falling back to all exons of this isoform."
        )
        regions = [
            {
                "start": s,
                "end": e,
                "type": "isoform_fallback",
                "transcript_id": target_transcript,
            }
            for s, e in target_merged
        ]

    return regions


def _subtract_intervals(
    a: list[tuple[int, int]], b: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    """Subtract intervals b from intervals a. Returns remaining portions of a."""
    result = []
    b_idx = 0
    for a_start, a_end in a:
        current_start = a_start
        while b_idx < len(b) and b[b_idx][1] <= current_start:
            b_idx += 1
        temp_idx = b_idx
        while temp_idx < len(b) and b[temp_idx][0] < a_end:
            b_start, b_end = b[temp_idx]
            if b_start > current_start:
                result.append((current_start, min(b_start, a_end)))
            current_start = max(current_start, b_end)
            temp_idx += 1
        if current_start < a_end:
            result.append((current_start, a_end))
    return result


# ---------------------------------------------------------------------------
# Ensembl REST API fallback
# ---------------------------------------------------------------------------

def _fetch_ensembl_transcripts(
    query: str, organism: str
) -> tuple[list[dict], list[dict], str]:
    """
    Fetch transcript isoforms from Ensembl REST API.
    Returns: (transcripts_list, exon_map, sequence)
    """
    import json
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen

    transcripts = []
    exon_map = []
    sequence = ""

    # Map common organism names to Ensembl species identifiers
    species_map = {
        "human": "homo_sapiens",
        "mouse": "mus_musculus",
        "rat": "rattus_norvegicus",
        "zebrafish": "danio_rerio",
    }
    species = species_map.get(organism.lower(), organism.lower())
    base_url = "https://rest.ensembl.org"

    # Validate query — no path separators, allow alphanumeric, dots, hyphens, underscores
    if not query or not isinstance(query, str) or "/" in query or "\\" in query:
        return [], [], ""
    sanitized_query = re.sub(r"[^a-zA-Z0-9_.\-]", "", query)
    if not sanitized_query:
        return [], [], ""

    try:
        # 1. Lookup gene → get all transcripts
        # Try as gene symbol first via xrefs
        lookup_url = f"{base_url}/lookup/symbol/{species}/{sanitized_query}?expand=1"
        headers = {"Content-Type": "application/json"}

        req = Request(lookup_url, headers=headers)
        try:
            with urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
        except (HTTPError, URLError):
            # Try as Ensembl ID (already sanitized above)
            lookup_url = f"{base_url}/lookup/id/{sanitized_query}?expand=1"
            req = Request(lookup_url, headers=headers)
            with urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

        # Extract transcript information
        if "Transcript" in data:
            for tx in data["Transcript"]:
                tid = tx.get("id", "")
                transcripts.append({
                    "transcript_id": tid,
                    "display_name": tx.get("display_name", tid),
                    "biotype": tx.get("biotype", ""),
                    "is_canonical": tx.get("is_canonical", 0) == 1,
                    "start": tx.get("start", 0),
                    "end": tx.get("end", 0),
                    "strand": tx.get("strand", 1),
                })

                # Extract exons for this transcript
                if "Exon" in tx:
                    for i, exon in enumerate(tx["Exon"]):
                        exon_map.append({
                            "transcript_id": tid,
                            "exon_id": exon.get("id", f"{tid}_exon_{i+1}"),
                            "start": exon.get("start", 0),
                            "end": exon.get("end", 0),
                            "rank": i + 1,
                        })

        # 2. Fetch genomic sequence for the gene region
        gene_start = data.get("start")
        gene_end = data.get("end")
        region = data.get("seq_region_name", "")
        strand = data.get("strand", 1)

        if region and gene_start and gene_end:
            seq_url = (
                f"{base_url}/sequence/region/{species}/"
                f"{region}:{gene_start}..{gene_end}:{strand}?content-type=application/json"
            )
            req = Request(seq_url, headers=headers)
            with urlopen(req, timeout=15) as resp:
                seq_data = json.loads(resp.read().decode())
                sequence = seq_data.get("seq", "")

    except Exception as e:
        logger.warning("Ensembl API fetch failed for '%s': %s", query, e)

    return transcripts, exon_map, sequence

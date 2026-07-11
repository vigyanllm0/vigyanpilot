"""
Step 5: Repeat Masking
========================
Avoid placing primers in repetitive elements (Alu, LINE, SINE, LTR, etc.)
Uses local Dfam-style repeat annotations (when genomic coordinates are available)
or a sequence-complexity scan as fallback.  Repositioned earlier in the pipeline
(was Step 12) to filter before Primer3 design.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6
"""

import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPEAT_OVERLAP_PENALTY = "repeat_overlap"
REPEAT_OVERLAP_WEIGHT = 12.0

DEFAULT_DFAM_REPEAT_PATH = os.environ.get(
    "DFAM_REPEAT_PATH",
    "/opt/postgres_data/dfam/dfam_repeats.tsv",
)

# Low-complexity detection thresholds
HOMOPOLYMER_MIN_LENGTH = 6       # ≥ 6 consecutive identical bases
DINUCLEOTIDE_MIN_UNITS = 5       # ≥ 5 repeats of a 2-mer (e.g., ATATAT... = 5 units)
TRINUCLEOTIDE_MIN_UNITS = 4      # ≥ 4 repeats of a 3-mer (e.g., CAGCAGCAGCAG)

# Pre-compiled low-complexity patterns
_HOMOPOLYMER_RE = re.compile(r'(.)\1{' + str(HOMOPOLYMER_MIN_LENGTH - 1) + r',}')
_DINUCLEOTIDE_RE = re.compile(r'(.{2})\1{' + str(DINUCLEOTIDE_MIN_UNITS - 1) + r',}')
_TRINUCLEOTIDE_RE = re.compile(r'(.{3})\1{' + str(TRINUCLEOTIDE_MIN_UNITS - 1) + r',}')


# ---------------------------------------------------------------------------
# Local Dfam annotation query
# ---------------------------------------------------------------------------

def _query_dfam_annotations(coordinates: str, annotation_path: str | None = None) -> list[dict[str, Any]]:
    """
    Query a local Dfam-style repeat annotation TSV.

    Args:
        coordinates: Genomic coordinates string (e.g., "chr1:1000-2000")
        annotation_path: Optional TSV with chrom/start/end/class/family/name columns.

    Returns:
        List of RepeatRegion dicts with keys:
            start (int): 0-based start position relative to target
            end (int): 0-based end position (exclusive)
            element_type (str): One of Alu, LINE, SINE, LTR, Simple
            length (int): Length of the repeat region

    Raises:
        RuntimeError: If the annotation file is not configured or cannot be read.
    """
    clean_coords = coordinates.replace(",", "").strip()

    try:
        chrom, positions = clean_coords.split(":")
        start_str, end_str = positions.split("-")
        region_start = int(start_str)
        region_end = int(end_str)
    except (ValueError, AttributeError) as e:
        raise RuntimeError(
            f"Invalid genomic coordinates format: '{coordinates}'. "
            f"Expected format: chr1:1000-2000. Error: {e}"
        )

    repeat_path = annotation_path or DEFAULT_DFAM_REPEAT_PATH
    if not repeat_path or not os.path.exists(repeat_path):
        raise RuntimeError(
            f"Dfam repeat annotations are not available at {repeat_path!r}"
        )

    repeat_regions: list[dict[str, Any]] = []
    try:
        with open(repeat_path, encoding="utf-8") as handle:
            header: list[str] | None = None
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if header is None and any(token.lower() in {"chrom", "chromosome"} for token in parts):
                    header = [p.strip().lower() for p in parts]
                    continue

                if header:
                    row = {header[i]: parts[i] for i in range(min(len(header), len(parts)))}
                    rep_chrom = row.get("chrom") or row.get("chromosome") or ""
                    rep_start = int(row.get("start") or row.get("chromstart") or 0)
                    rep_end = int(row.get("end") or row.get("chromend") or 0)
                    rep_class = row.get("class") or row.get("repclass") or row.get("type") or "Unknown"
                    rep_family = row.get("family") or row.get("repfamily") or row.get("name") or ""
                else:
                    if len(parts) < 3:
                        continue
                    rep_chrom = parts[0]
                    rep_start = int(parts[1])
                    rep_end = int(parts[2])
                    rep_class = parts[3] if len(parts) > 3 else "Unknown"
                    rep_family = parts[4] if len(parts) > 4 else ""

                if rep_chrom.lower().replace("chr", "") != chrom.lower().replace("chr", ""):
                    continue
                if rep_end <= region_start or rep_start >= region_end:
                    continue

                rel_start = max(0, rep_start - region_start)
                rel_end = min(region_end - region_start, rep_end - region_start)
                if rel_end > rel_start:
                    repeat_regions.append({
                        "start": rel_start,
                        "end": rel_end,
                        "element_type": _classify_repeat_element(rep_class, rep_family),
                        "length": rel_end - rel_start,
                        "source": "Dfam",
                    })
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Dfam annotation query failed for {coordinates}: {e}")

    return repeat_regions


def _classify_repeat_element(rep_class: str, rep_family: str) -> str:
    """Map repeat class/family to simplified element type."""
    rep_class_lower = rep_class.lower()
    rep_family_lower = rep_family.lower()

    if "alu" in rep_family_lower:
        return "Alu"
    elif "line" in rep_class_lower or "l1" in rep_family_lower or "l2" in rep_family_lower:
        return "LINE"
    elif "sine" in rep_class_lower:
        return "SINE"
    elif "ltr" in rep_class_lower or "erv" in rep_family_lower:
        return "LTR"
    elif "simple" in rep_class_lower or "low_complexity" in rep_class_lower:
        return "Simple"
    else:
        return rep_class if rep_class else "Unknown"


# ---------------------------------------------------------------------------
# Complexity scan (fallback when no genomic coordinates or local annotations fail)
# ---------------------------------------------------------------------------

def _complexity_scan(seq: str) -> list[dict[str, Any]]:
    """
    Detect low-complexity regions in a DNA sequence using pattern matching.

    Detects:
        - Homopolymer runs ≥ 6 bases (e.g., AAAAAA)
        - Dinucleotide repeats ≥ 5 units (e.g., ATATATATAT)
        - Trinucleotide repeats ≥ 4 units (e.g., CAGCAGCAGCAG)

    Args:
        seq: DNA sequence string (case-insensitive).

    Returns:
        List of region dicts with keys:
            start (int): 0-based start position
            end (int): 0-based end position (exclusive)
            element_type (str): "Simple" or "low_complexity"
            length (int): Length of the region
            pattern (str): The repeated unit detected
            repeat_type (str): "homopolymer", "dinucleotide", or "trinucleotide"
    """
    upper_seq = seq.upper()
    regions: list[dict[str, Any]] = []
    seen_ranges: list[tuple] = []

    # Scan for homopolymer runs ≥ 6
    for match in _HOMOPOLYMER_RE.finditer(upper_seq):
        start, end = match.start(), match.end()
        regions.append({
            "start": start,
            "end": end,
            "element_type": "Simple",
            "length": end - start,
            "pattern": match.group(1),
            "repeat_type": "homopolymer",
        })
        seen_ranges.append((start, end))

    # Scan for dinucleotide repeats ≥ 5 units
    for match in _DINUCLEOTIDE_RE.finditer(upper_seq):
        start, end = match.start(), match.end()
        # Skip if entirely contained within an already-detected region
        if not _is_subsumed(start, end, seen_ranges):
            regions.append({
                "start": start,
                "end": end,
                "element_type": "Simple",
                "length": end - start,
                "pattern": match.group(1),
                "repeat_type": "dinucleotide",
            })
            seen_ranges.append((start, end))

    # Scan for trinucleotide repeats ≥ 4 units
    for match in _TRINUCLEOTIDE_RE.finditer(upper_seq):
        start, end = match.start(), match.end()
        if not _is_subsumed(start, end, seen_ranges):
            regions.append({
                "start": start,
                "end": end,
                "element_type": "Simple",
                "length": end - start,
                "pattern": match.group(1),
                "repeat_type": "trinucleotide",
            })
            seen_ranges.append((start, end))

    # Sort by start position
    regions.sort(key=lambda r: r["start"])
    return regions


def _is_subsumed(start: int, end: int, existing: list[tuple]) -> bool:
    """Check if a range [start, end) is entirely within any existing range."""
    for ex_start, ex_end in existing:
        if start >= ex_start and end <= ex_end:
            return True
    return False


# ---------------------------------------------------------------------------
# Soft masking
# ---------------------------------------------------------------------------

def _soft_mask(seq: str, regions: list[dict[str, Any]]) -> str:
    """
    Lowercase all identified repeat/low-complexity positions in the sequence.

    Positions covered by any region in the list are lowercased; all other
    positions retain their original case.

    Args:
        seq: Original DNA sequence.
        regions: List of region dicts (must have 'start' and 'end' keys).

    Returns:
        Soft-masked sequence with repeat positions in lowercase.
    """
    if not regions:
        return seq

    # Build a set of all masked positions
    masked_positions = set()
    for region in regions:
        for pos in range(region["start"], min(region["end"], len(seq))):
            masked_positions.add(pos)

    # Apply masking
    result = []
    for i, char in enumerate(seq):
        if i in masked_positions:
            result.append(char.lower())
        else:
            result.append(char.upper())

    return "".join(result)


# ---------------------------------------------------------------------------
# Primer overlap rejection logic
# ---------------------------------------------------------------------------

def _calculate_overlap_fraction(
    primer_start: int, primer_length: int, masked_positions: set
) -> float:
    """
    Calculate the fraction of a primer's binding region that overlaps
    masked (lowercase) positions.

    Args:
        primer_start: 0-based start position of the primer in the sequence.
        primer_length: Length of the primer.
        masked_positions: Set of 0-based positions that are masked.

    Returns:
        Fraction of the primer overlapping masked positions (0.0 to 1.0).
    """
    if primer_length == 0:
        return 0.0

    primer_positions = set(range(primer_start, primer_start + primer_length))
    overlap_count = len(primer_positions & masked_positions)
    return overlap_count / primer_length


def _get_masked_positions(masked_seq: str) -> set:
    """Extract the set of 0-based positions that are lowercase (masked)."""
    return {i for i, c in enumerate(masked_seq) if c.islower()}


def _check_primer_repeat_overlap(
    primer_seq: str,
    primer_start: int,
    masked_seq: str,
    regions: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """
    Check if a primer overlaps masked repeat regions by ≥ 50%.

    Args:
        primer_seq: The primer sequence.
        primer_start: 0-based start position of the primer in the target.
        masked_seq: The soft-masked target sequence.
        regions: List of repeat region dicts.

    Returns:
        None if the primer passes, or a dict with overlap details if rejected:
            penalty (str), overlap_percent (float), overlapping_element_type (str)
    """
    primer_length = len(primer_seq)
    masked_positions = _get_masked_positions(masked_seq)

    overlap_fraction = _calculate_overlap_fraction(
        primer_start, primer_length, masked_positions
    )

    if overlap_fraction >= 0.5:
        # Determine the primary overlapping element type
        primer_positions = set(range(primer_start, primer_start + primer_length))
        element_type = _identify_overlapping_element(primer_positions, regions)

        return {
            "penalty": REPEAT_OVERLAP_PENALTY,
            "penalty_weight": REPEAT_OVERLAP_WEIGHT,
            "overlap_percent": round(overlap_fraction * 100, 1),
            "overlapping_element_type": element_type,
        }

    return None


def _identify_overlapping_element(
    primer_positions: set, regions: list[dict[str, Any]]
) -> str:
    """Identify the repeat element type with the most overlap to the primer."""
    best_overlap = 0
    best_type = "Unknown"

    for region in regions:
        region_positions = set(range(region["start"], region["end"]))
        overlap = len(primer_positions & region_positions)
        if overlap > best_overlap:
            best_overlap = overlap
            best_type = region.get("element_type", "Unknown")

    return best_type


# ---------------------------------------------------------------------------
# Module-level execute function
# ---------------------------------------------------------------------------

def execute(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Step 5: Repeat Masking — mask repetitive elements before primer design.

    Queries local Dfam annotations when genomic coordinates are provided; otherwise
    falls back to a sequence-complexity scan.  Soft-masks the target sequence
    (lowercase) at repeat positions.  If primer candidates are already present,
    applies the 50% overlap rejection rule.

    Input keys:
        target_sequence (str): The DNA target sequence (required).
        genomic_coordinates (str, optional): e.g. "chr1:1000-2000".
        primer_candidates (list, optional): Existing primer candidates to filter.

    Output keys:
        masked_sequence (str): Soft-masked target sequence.
        repeat_regions (list): List of dicts with start/end/type/length.
        low_complexity_regions (list): Alias for regions from complexity scan.
        masking_source (str): "dfam" or "complexity_scan".
        flagged_primers (list): Primers rejected for repeat overlap (if any).
    """
    target_sequence = input_data.get("target_sequence", "")
    genomic_coordinates = input_data.get("genomic_coordinates")
    dfam_repeat_path = input_data.get("dfam_repeat_path")
    primer_candidates = input_data.get("primer_candidates", [])

    if not target_sequence:
        raise ValueError("No target_sequence provided for repeat masking")

    # --------------- Identify repeat regions ---------------
    repeat_regions: list[dict[str, Any]] = []
    masking_source = "complexity_scan"

    if genomic_coordinates:
        # Try local Dfam annotations first
        try:
            repeat_regions = _query_dfam_annotations(genomic_coordinates, dfam_repeat_path)
            masking_source = "dfam"
            logger.info(
                "Dfam annotations returned %d regions for %s",
                len(repeat_regions),
                genomic_coordinates,
            )
        except RuntimeError as e:
            # Fallback to complexity scan (Requirement 5.6)
            logger.warning(
                "Dfam annotation source unavailable (%s). "
                "Falling back to sequence-complexity scan.",
                str(e),
            )
            repeat_regions = _complexity_scan(target_sequence)
            masking_source = "complexity_scan"
    else:
        # No genomic coordinates — use complexity scan (Requirement 5.2)
        repeat_regions = _complexity_scan(target_sequence)
        masking_source = "complexity_scan"
        logger.info(
            "No genomic coordinates provided; using complexity scan. "
            "Found %d low-complexity regions.",
            len(repeat_regions),
        )

    # --------------- Soft-mask the sequence (Requirement 5.3) ---------------
    masked_sequence = _soft_mask(target_sequence, repeat_regions)

    # --------------- Primer overlap rejection (Requirements 5.4, 5.5) -------
    flagged_primers: list[dict[str, Any]] = []

    if primer_candidates:
        for candidate in primer_candidates:
            primer_seq = candidate.get("sequence", "")
            primer_start = candidate.get("start", 0)

            overlap_result = _check_primer_repeat_overlap(
                primer_seq, primer_start, masked_sequence, repeat_regions
            )
            if overlap_result:
                flagged_primers.append({
                    "primer_id": candidate.get("id", "unknown"),
                    "sequence": primer_seq,
                    "start": primer_start,
                    **overlap_result,
                })

    # --------------- Build output ---------------
    # Separate low_complexity_regions for clarity
    low_complexity_regions = [
        r for r in repeat_regions
        if r.get("element_type") in ("Simple", "low_complexity")
    ]

    return {
        "masked_sequence": masked_sequence,
        "repeat_regions": repeat_regions,
        "low_complexity_regions": low_complexity_regions,
        "masking_source": masking_source,
        "flagged_primers": flagged_primers,
        "repeat_count": len(repeat_regions),
        "masked_fraction": round(
            sum(1 for c in masked_sequence if c.islower()) / max(len(masked_sequence), 1),
            4,
        ),
    }

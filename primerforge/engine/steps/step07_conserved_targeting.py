"""
Step 7: Conserved Region Targeting
====================================
Configure Primer3 design constraints to force primer binding within
>95% conserved regions identified by Step 6 MSA.

Fallback logic:
  - If conserved_regions list is empty or no region >= 18nt (primer min length),
    remove the targeting constraint and flag the output:
    "MSA warning: no highly conserved region present across analyzed strains.
     Primers designed from standard regions."
  - Otherwise, set SEQUENCE_INCLUDED_REGION to the longest conserved interval.

Output keys:
  - design_region (list): [start, end] 0-indexed region passed to Primer3
  - conserved_targeting_active (bool): Whether targeting was applied
  - conserved_targeting_note (str): Frontend-displayed message
  - force_included_region (list|None): [start, length] for Primer3
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

MIN_PRIMER_LENGTH = 18


def execute(input_data: dict[str, Any]) -> dict[str, Any]:
    conserved_regions = input_data.get("conserved_regions", [])
    scores = input_data.get("conservation_scores", [])
    msa_status = input_data.get("msa_status", "")
    msa_note = input_data.get("msa_note", "")

    sequence = (
        input_data.get("consensus_sequence")
        or input_data.get("target_sequence")
        or input_data.get("sequence", "")
    )

    if not sequence:
        return _no_targeting("No sequence available.", input_data)

    usable_regions = _filter_usable_regions(conserved_regions, min_length=MIN_PRIMER_LENGTH)

    if not usable_regions or msa_status in ("fallback_no_strains", "fallback_error"):
        fallback_note = (
            "No highly conserved region present across analyzed strains. "
            "Primers designed from standard regions."
        )
        if msa_status == "fallback_no_strains":
            fallback_note = (
                "Insufficient strain data for conservation analysis. "
                "Primers designed from standard regions."
            )
        return _no_targeting(fallback_note, input_data)

    # Pick the longest conserved region
    best_region = max(usable_regions, key=lambda r: r["length"])
    start = best_region["start"]
    end = best_region["end"]
    length = best_region["length"]
    avg_cons = best_region["avg_conservation"]

    # Clamp to sequence bounds
    start = max(0, start)
    end = min(len(sequence) - 1, end)
    length = max(0, end - start + 1)

    if length < MIN_PRIMER_LENGTH:
        return _no_targeting(
            f"Longest conserved region only {length}nt (< {MIN_PRIMER_LENGTH}nt min primer length). "
            "Primers designed from standard regions.",
            input_data,
        )

    note = (
        f"Conserved region targeting active: {length}bp region "
        f"({avg_cons*100:.1f}% avg conservation) at positions {start+1}-{end+1}. "
        f"Primer3 constrained to this interval."
    )

    return {
        "design_region": [start, end],
        "conserved_targeting_active": True,
        "conserved_targeting_note": note,
        "force_included_region": [start, length],
    }


def _filter_usable_regions(
    regions: list[dict[str, Any]], min_length: int = MIN_PRIMER_LENGTH
) -> list[dict[str, Any]]:
    return [r for r in regions if r.get("length", 0) >= min_length]


def _no_targeting(reason: str, input_data: dict[str, Any]) -> dict[str, Any]:
    logger.info("Conserved targeting skipped: %s", reason)

    sequence = input_data.get("consensus_sequence") or input_data.get("target_sequence") or input_data.get("sequence", "")
    total_len = len(sequence) if sequence else 0

    return {
        "design_region": [0, total_len - 1] if total_len > 0 else [0, 0],
        "conserved_targeting_active": False,
        "conserved_targeting_note": reason,
        "force_included_region": None,
    }

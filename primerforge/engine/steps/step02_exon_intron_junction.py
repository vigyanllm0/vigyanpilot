"""
Step 2: Exon-Intron Junction Mapping
======================================
Identify exon-exon junctions and designate preferred primer placement sites.
Strategy:
  - Flag ±50nt around each exon-exon junction as preferred placement zones
  - Rank junction-spanning primers (must have ≥5nt on each side of junction)
  - Fallback to intron-flanking design (≥1000bp intron) if no junction primers pass
  - Handle single-exon transcripts gracefully (entire exon is valid)

This prevents gDNA co-amplification in RT-PCR workflows by ensuring primers
require a spliced mRNA template.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Minimum overhang on each side of a junction for a spanning primer
MIN_JUNCTION_OVERHANG = 5  # nt

# Zone around each junction that is marked as preferred placement
JUNCTION_ZONE_NT = 50  # ±50nt

# Minimum intron size for intron-flanking strategy to discriminate from gDNA
MIN_INTRON_FOR_FLANKING = 1000  # bp


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def execute(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Step 2: Map exon-intron junctions for RT-PCR safety.

    Input keys:
        - target_sequence (str): The target sequence
        - exon_map (list): Exon coordinates [{start, end, transcript_id, exon_id, rank}]
        - selected_regions (list): Regions from Step 1
        - sequence_length (int): Length of the target sequence

    Output keys:
        - valid_regions (list): Regions suitable for primer placement
        - junction_positions (list): All identified exon-exon junctions
        - preferred_zones (list): ±50nt zones around junctions (highest priority)
        - junction_spanning_sites (list): Exact positions for junction-spanning primers
        - intron_flanking_pairs (list): Intron-flanking primer region pairs
        - junction_strategy (str): Strategy used (junction_spanning | intron_flanking | single_exon)
    """
    exon_map = input_data.get("exon_map", [])
    sequence_length = input_data.get("sequence_length", 0)
    target_sequence = input_data.get("target_sequence", "")
    selected_regions = input_data.get("selected_regions", [])

    if not sequence_length and target_sequence:
        sequence_length = len(target_sequence)

    # ── Handle single-exon or no-exon transcripts ──────────────────────────
    if not exon_map or len(exon_map) < 2:
        logger.info("Single-exon or no exon structure — treating as cDNA/synthetic template.")
        valid_regions = selected_regions or [{"start": 0, "end": sequence_length}]
        for r in valid_regions:
            r["type"] = r.get("type", "single_exon")
        return {
            "valid_regions": valid_regions,
            "junction_positions": [],
            "preferred_zones": [],
            "junction_spanning_sites": [],
            "intron_flanking_pairs": [],
            "junction_strategy": "single_exon",
            "junction_note": "No exon-intron structure detected — entire sequence valid for design.",
        }

    # ── Sort exons by genomic position ─────────────────────────────────────
    sorted_exons = sorted(exon_map, key=lambda e: (e.get("start", 0), e.get("end", 0)))

    # ── Identify all exon-exon junctions ───────────────────────────────────
    junction_positions = []
    preferred_zones = []
    junction_spanning_sites = []
    intron_flanking_pairs = []

    for i in range(len(sorted_exons) - 1):
        exon_a = sorted_exons[i]
        exon_b = sorted_exons[i + 1]

        exon_a_end = exon_a.get("end", 0)
        exon_b_start = exon_b.get("start", 0)
        intron_size = exon_b_start - exon_a_end

        junction = {
            "junction_id": f"J{i+1}",
            "exon_upstream": exon_a.get("exon_id", f"exon_{i+1}"),
            "exon_downstream": exon_b.get("exon_id", f"exon_{i+2}"),
            "exon_a_end": exon_a_end,
            "exon_b_start": exon_b_start,
            "intron_size": intron_size,
            "transcript_id": exon_a.get("transcript_id", ""),
        }
        junction_positions.append(junction)

        # ── Preferred zone: ±50nt around the junction ──────────────────────
        zone_start = max(0, exon_a_end - JUNCTION_ZONE_NT)
        zone_end = min(sequence_length, exon_b_start + JUNCTION_ZONE_NT)
        preferred_zones.append({
            "start": zone_start,
            "end": zone_end,
            "junction_id": junction["junction_id"],
            "type": "preferred_junction_zone",
            "priority": 1,  # Highest priority
        })

        # ── Junction-spanning primer sites ─────────────────────────────────
        # Primer must have ≥MIN_JUNCTION_OVERHANG nt on each side
        # In spliced mRNA, the junction is at exon_a_end (genomic coords)
        # On mRNA: last MIN_JUNCTION_OVERHANG of exon A + first MIN_JUNCTION_OVERHANG of exon B
        span_start = exon_a_end - MIN_JUNCTION_OVERHANG
        span_end = exon_b_start + MIN_JUNCTION_OVERHANG

        if span_start >= 0 and span_end <= sequence_length:
            junction_spanning_sites.append({
                "start": span_start,
                "end": span_end,
                "junction_id": junction["junction_id"],
                "min_overhang": MIN_JUNCTION_OVERHANG,
                "type": "junction_spanning",
                "priority": 1,
            })

        # ── Intron-flanking strategy (fallback) ────────────────────────────
        if intron_size >= MIN_INTRON_FOR_FLANKING:
            # Forward primer in exon A (last 100nt), reverse in exon B (first 100nt)
            fwd_region_start = max(exon_a.get("start", 0), exon_a_end - 100)
            fwd_region_end = exon_a_end
            rev_region_start = exon_b_start
            rev_region_end = min(exon_b.get("end", sequence_length), exon_b_start + 100)

            intron_flanking_pairs.append({
                "junction_id": junction["junction_id"],
                "fwd_region": {"start": fwd_region_start, "end": fwd_region_end},
                "rev_region": {"start": rev_region_start, "end": rev_region_end},
                "intron_size": intron_size,
                "type": "intron_flanking",
                "priority": 2,  # Lower priority than junction-spanning
            })

    # ── Determine strategy and build valid_regions ─────────────────────────
    valid_regions = []

    if junction_spanning_sites:
        strategy = "junction_spanning"
        # Primary: use junction-spanning sites
        for site in junction_spanning_sites:
            valid_regions.append({
                "start": max(0, site["start"] - 20),  # Extra context for primer design
                "end": min(sequence_length, site["end"] + 20),
                "type": "junction_spanning",
                "junction_id": site["junction_id"],
                "priority": 1,
            })
        # Also include preferred zones for flexibility
        for zone in preferred_zones:
            valid_regions.append(zone)
    elif intron_flanking_pairs:
        strategy = "intron_flanking"
        logger.info(
            "No junction-spanning primers feasible — using intron-flanking strategy "
            f"({len(intron_flanking_pairs)} flanking pairs with intron ≥{MIN_INTRON_FOR_FLANKING}bp)."
        )
        for pair in intron_flanking_pairs:
            valid_regions.append({
                "start": pair["fwd_region"]["start"],
                "end": pair["fwd_region"]["end"],
                "type": "intron_flanking_fwd",
                "junction_id": pair["junction_id"],
                "priority": 2,
            })
            valid_regions.append({
                "start": pair["rev_region"]["start"],
                "end": pair["rev_region"]["end"],
                "type": "intron_flanking_rev",
                "junction_id": pair["junction_id"],
                "priority": 2,
            })
    else:
        strategy = "exon_coverage"
        logger.info(
            "No junction-spanning or intron-flanking possible — "
            "using full exon coverage (all introns <1000bp)."
        )
        for exon in sorted_exons:
            valid_regions.append({
                "start": exon.get("start", 0),
                "end": exon.get("end", 0),
                "type": "exon",
                "exon_id": exon.get("exon_id", ""),
                "priority": 3,
            })

    # Rank junction-spanning primers by quality
    _rank_junction_sites(junction_spanning_sites, sorted_exons)

    # ── Summary note ───────────────────────────────────────────────────────
    introns_over_1k = sum(1 for j in junction_positions if j["intron_size"] >= MIN_INTRON_FOR_FLANKING)
    note_parts = [
        f"{len(junction_positions)} junctions found",
        f"Strategy: {strategy}",
    ]
    if intron_flanking_pairs:
        note_parts.append(f"{introns_over_1k} introns ≥1000bp (gDNA discriminating)")
    if junction_spanning_sites:
        note_parts.append(f"{len(junction_spanning_sites)} spanning sites identified")

    return {
        "valid_regions": valid_regions,
        "junction_positions": junction_positions,
        "preferred_zones": preferred_zones,
        "junction_spanning_sites": junction_spanning_sites,
        "intron_flanking_pairs": intron_flanking_pairs,
        "junction_strategy": strategy,
        "junction_note": ". ".join(note_parts) + ".",
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rank_junction_sites(
    sites: list[dict[str, Any]],
    sorted_exons: list[dict[str, Any]],
) -> None:
    """
    Rank junction-spanning sites by quality:
      - Prefer junctions with larger exons on both sides (more design flexibility)
      - Prefer junctions near the middle of the transcript (avoid 5'/3' bias)
    """
    if not sites or not sorted_exons:
        return

    total_span = sorted_exons[-1].get("end", 0) - sorted_exons[0].get("start", 0)
    mid_point = sorted_exons[0].get("start", 0) + total_span / 2

    for site in sites:
        site_mid = (site["start"] + site["end"]) / 2
        distance_from_center = abs(site_mid - mid_point)
        # Lower rank_score = better (closer to center, more balanced overhang)
        site["rank_score"] = distance_from_center / max(total_span, 1)

    sites.sort(key=lambda s: s.get("rank_score", 999))
    for i, site in enumerate(sites):
        site["rank"] = i + 1

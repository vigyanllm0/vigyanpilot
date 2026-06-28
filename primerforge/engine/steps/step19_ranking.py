"""
Step 19: Automated Penalty & Ranking Matrix
=============================================
Aggregate penalties from all evaluation steps into a unified scoring function.
Rank primer pairs by total penalty (ascending — lowest = best).
Assign status: PASS (<10), REVIEW (10-30), FAIL (>30).
Output the top 10 pairs with full annotations.

Penalty weights (from design spec):
  - off_target (BLAST):       20
  - pseudogene/organelle:     20
  - snp_3prime_critical:      15
  - repeat_overlap:           12
  - delta_tm (excess):        10
  - clinical_hotspot:         10
  - amplicon_stall:           10
  - dimer_risk:                8
  - multiplex_incompatible:    8
  - hairpin_risk:              5
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Penalty Weights ────────────────────────────────────────────────────────
PENALTY_WEIGHTS = {
    "off_target": 20.0,
    "pseudogene": 20.0,
    "snp_3prime": 15.0,
    "repeat_overlap": 12.0,
    "delta_tm": 10.0,
    "clinical_hotspot": 10.0,
    "amplicon_stall": 10.0,
    "dimer": 8.0,
    "multiplex_incompatible": 8.0,
    "hairpin": 5.0,
}

# ── Status Thresholds ──────────────────────────────────────────────────────
STATUS_THRESHOLDS = {
    "PASS": (0, 10),       # total_penalty < 10
    "REVIEW": (10, 30),    # 10 <= total_penalty <= 30
    "FAIL": (30, float("inf")),  # total_penalty > 30
}

# Maximum number of top pairs to return
TOP_N_PAIRS = 10


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def execute(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Step 19: Final penalty aggregation and ranking.

    Input keys:
        - multiplex_scored (list): Pairs from Step 18
        - clinical_checked / variant_filtered / amplicon_checked /
          structure_checked / aligned_pairs / filtered_pairs / refined_pairs /
          candidate_pairs (list): Pair-shaped upstream fallbacks when optional
          downstream checks are skipped or soft-fail.

    Output keys:
        - ranked_pairs (list): All pairs sorted by total_penalty (ascending)
        - top_pairs (list): Top 10 pairs with full annotations
        - ranking_summary (dict): Counts per status category
        - ranking_note (str): Summary
    """
    pairs, source_key = _select_pairs_to_rank(input_data)
    if not pairs:
        return {
            "ranked_pairs": [],
            "top_pairs": [],
            "ranking_summary": {"PASS": 0, "REVIEW": 0, "FAIL": 0},
            "ranking_note": "No pairs to rank",
            "ranking_source": source_key,
        }

    target_seq = (
        input_data.get("target_sequence")
        or input_data.get("consensus_sequence", "")
        or input_data.get("sequence", "")
    )

    # Copy pair dicts before sorting/annotating so Step 19 does not reorder an
    # upstream step's result list in place.
    pairs = [dict(pair) for pair in pairs]

    # ── Aggregate penalties for each pair ──────────────────────────────────
    conserved_targeting_active = input_data.get("conserved_targeting_active", False)
    msa_status = input_data.get("msa_status", "")

    # Extract conservation percentage from step7 note
    import re as _re
    _conserved_note = input_data.get("conserved_targeting_note", "")
    _conservation_percent = None
    if _conserved_note:
        _m = _re.search(r'([\d.]+)%', _conserved_note)
        if _m:
            _conservation_percent = float(_m.group(1))

    for pair in pairs:
        _normalize_frontend_aliases(pair, target_seq)
        total_penalty = _aggregate_penalties(pair)
        pair["total_penalty"] = round(total_penalty, 2)
        status = _assign_status(total_penalty)
        pair["overall_status"] = status
        pair["status"] = status
        pair["overall_pass"] = status == "PASS"
        pair["penalty_breakdown"] = _build_penalty_breakdown(pair)
        pair["penalty_score"] = pair["total_penalty"]
        # Compute score = 100 − penalty, clamped to [0, 100]
        pair["score"] = round(max(0.0, min(100.0, 100.0 - total_penalty)), 2)
        # Set conserved region flag — only when MSA was successfully completed
        if conserved_targeting_active is True and msa_status == "complete":
            pair["conserved_region_pass"] = True
        elif conserved_targeting_active is False and msa_status == "complete":
            # MSA completed but no conserved region large enough was found
            pair["conserved_region_pass"] = False
        # else: MSA was skipped or failed — leave undefined so frontend shows N/A

        # Store conservation percentage from step7 note
        if _conservation_percent is not None:
            pair["conservation_percent"] = _conservation_percent
        elif pair.get("conserved_region_pass") is True:
            pair["conservation_percent"] = 100.0
        elif pair.get("conserved_region_pass") is False:
            pair["conservation_percent"] = 0.0

    # ── Sort by total penalty (ascending — lowest = best) ──────────────────
    pairs.sort(key=lambda p: p["total_penalty"])

    # ── Assign ranks and pair_id ────────────────────────────────────────────
    for i, pair in enumerate(pairs):
        pair["rank"] = i + 1
        # pair_id is used by the frontend for display — keep existing or set from rank
        if not pair.get("pair_id"):
            pair["pair_id"] = i + 1

    # ── Top N pairs with annotations ───────────────────────────────────────
    top_pairs = pairs[:TOP_N_PAIRS]

    # ── Summary statistics ─────────────────────────────────────────────────
    ranking_summary = {"PASS": 0, "REVIEW": 0, "FAIL": 0}
    for pair in pairs:
        status = pair.get("overall_status", "FAIL")
        ranking_summary[status] = ranking_summary.get(status, 0) + 1

    # ── Build ranking note ─────────────────────────────────────────────────
    note_parts = [
        f"{len(pairs)} pairs ranked",
        f"source: {source_key}",
        f"PASS: {ranking_summary['PASS']}",
        f"REVIEW: {ranking_summary['REVIEW']}",
        f"FAIL: {ranking_summary['FAIL']}",
    ]
    if pairs:
        note_parts.append(f"Best penalty: {pairs[0]['total_penalty']}")
        if len(pairs) > 1:
            note_parts.append(f"Worst penalty: {pairs[-1]['total_penalty']}")

    return {
        "ranked_pairs": pairs,
        "top_pairs": top_pairs,
        "ranking_summary": ranking_summary,
        "ranking_note": " | ".join(note_parts),
        "ranking_source": source_key,
    }


# ---------------------------------------------------------------------------
# Candidate Selection
# ---------------------------------------------------------------------------

def _select_pairs_to_rank(input_data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
    """Return the richest available pair-shaped list for final ranking."""
    for key in (
        "multiplex_scored",
        "clinical_checked",
        "variant_filtered",
        "amplicon_checked",
        "structure_checked",
        "aligned_pairs",
        "filtered_pairs",
        "refined_pairs",
        "candidate_pairs",
    ):
        pairs = input_data.get(key)
        if pairs:
            return pairs, key
    return [], "none"


# ---------------------------------------------------------------------------
# Output Normalization
# ---------------------------------------------------------------------------

def _normalize_frontend_aliases(pair: Dict[str, Any], target_seq: str = "") -> None:
    """Populate canonical UI/export aliases without changing ranking inputs."""
    fwd = _primer_dict(pair.get("forward"), pair.get("forward_tm"))
    rev = _primer_dict(pair.get("reverse"), pair.get("reverse_tm"))

    _infer_positions(pair, fwd, rev, target_seq)

    pair["forward"] = fwd
    pair["reverse"] = rev
    pair.setdefault("forward_primer", dict(fwd))
    pair.setdefault("reverse_primer", dict(rev))

    product_size = (
        pair.get("amplicon_size")
        or pair.get("product_size")
        or pair.get("amplicon_length")
        or pair.get("amplicon_len")
    )
    if not product_size:
        start = pair.get("product_start")
        end = pair.get("product_end")
        if isinstance(start, int) and isinstance(end, int) and end >= start:
            product_size = end - start + 1
    if product_size:
        pair["amplicon_size"] = int(product_size)
        start = pair.get("product_start")
        end = pair.get("product_end")
        if isinstance(start, int) and (not isinstance(end, int) or end < start):
            pair["product_end"] = start + int(product_size) - 1

    amplicon_seq = pair.get("amplicon_sequence") or _extract_amplicon_sequence(pair, target_seq)
    if amplicon_seq:
        pair["amplicon_sequence"] = amplicon_seq
        pair.setdefault("amplicon_size", len(amplicon_seq))
        pair.setdefault("product_size", len(amplicon_seq))
        amplicon_gc = _gc_percent(amplicon_seq)
        if not pair.get("amplicon_gc"):
            pair["amplicon_gc"] = amplicon_gc
        if not pair.get("product_gc"):
            pair["product_gc"] = pair["amplicon_gc"]
    else:
        pair.setdefault("amplicon_gc", pair.get("product_gc"))
        pair.setdefault("product_gc", pair.get("amplicon_gc"))

    f_tm = _numeric_or_none(fwd.get("tm") or fwd.get("tm_nn"))
    r_tm = _numeric_or_none(rev.get("tm") or rev.get("tm_nn"))
    if f_tm is not None:
        fwd.setdefault("tm", f_tm)
        pair["forward_primer"].setdefault("tm", f_tm)
    if r_tm is not None:
        rev.setdefault("tm", r_tm)
        pair["reverse_primer"].setdefault("tm", r_tm)

    delta_tm = pair.get("tm_delta")
    if delta_tm is None:
        delta_tm = pair.get("delta_tm_nn", pair.get("delta_tm"))
    if delta_tm is None and f_tm is not None and r_tm is not None:
        delta_tm = abs(f_tm - r_tm)
    delta_tm_value = _numeric_or_none(delta_tm)
    pair["tm_delta"] = round(delta_tm_value, 2) if delta_tm_value is not None else None

    if "annealing_ta" not in pair and f_tm is not None and r_tm is not None:
        pair["annealing_ta"] = round((f_tm + r_tm) / 2 - 5, 1)

    pair.setdefault("cross_dimer_dg", None)
    pair.setdefault("product_start", fwd.get("start_pos"))
    pair.setdefault("product_end", rev.get("start_pos") or rev.get("stop_pos"))

    specificity_pass = pair.get("specificity_pass")
    if specificity_pass is not None:
        off_target_count = 0 if specificity_pass else 1
        f_hits = fwd.get("blast_significant_hits", 0) or 0
        r_hits = rev.get("blast_significant_hits", 0) or 0
        if not specificity_pass:
            off_target_count = max(1, f_hits + r_hits)
        pair.setdefault("specificity", {"off_target_count": off_target_count})

    pair["forward_primer"].update({
        "sequence": fwd.get("sequence", ""),
        "length": fwd.get("length", len(fwd.get("sequence", ""))),
        "tm": fwd.get("tm", fwd.get("tm_nn")),
        "gc": fwd.get("gc"),
        "hairpin_dg": fwd.get("hairpin_dg"),
        "self_dimer_dg": fwd.get("self_dimer_dg", fwd.get("dimer_dg")),
        "start_pos": fwd.get("start_pos", fwd.get("start") + 1 if fwd.get("start") is not None else None),
        "stop_pos": fwd.get("stop_pos"),
        "gc_clamp_ok": fwd.get("gc_clamp_ok", _gc_clamp(fwd.get("sequence", ""))),
    })
    pair["reverse_primer"].update({
        "sequence": rev.get("sequence", ""),
        "length": rev.get("length", len(rev.get("sequence", ""))),
        "tm": rev.get("tm", rev.get("tm_nn")),
        "gc": rev.get("gc"),
        "hairpin_dg": rev.get("hairpin_dg"),
        "self_dimer_dg": rev.get("self_dimer_dg", rev.get("dimer_dg")),
        "start_pos": rev.get("start_pos", rev.get("start") + 1 if rev.get("start") is not None else None),
        "stop_pos": rev.get("stop_pos"),
        "gc_clamp_ok": rev.get("gc_clamp_ok", _gc_clamp(rev.get("sequence", ""))),
    })
    if pair["forward_primer"].get("quality_score") is None:
        pair["forward_primer"]["quality_score"] = _measured_primer_quality(pair["forward_primer"])
    if pair["reverse_primer"].get("quality_score") is None:
        pair["reverse_primer"]["quality_score"] = _measured_primer_quality(pair["reverse_primer"])
    fwd.setdefault("quality_score", pair["forward_primer"].get("quality_score"))
    rev.setdefault("quality_score", pair["reverse_primer"].get("quality_score"))


def _primer_dict(value: Any, fallback_tm: Any = None) -> Dict[str, Any]:
    if isinstance(value, dict):
        primer = dict(value)
    else:
        sequence = value if isinstance(value, str) else ""
        primer = {"sequence": sequence}

    sequence = primer.get("sequence", "")
    primer.setdefault("length", len(sequence))
    primer.setdefault("tm", fallback_tm if fallback_tm is not None else primer.get("tm_nn"))
    primer.setdefault("gc", _gc_percent(sequence))
    primer.setdefault("hairpin_dg", None)
    primer.setdefault("self_dimer_dg", primer.get("dimer_dg"))
    primer.setdefault("gc_clamp_ok", _gc_clamp(sequence))
    return primer


def _infer_positions(pair: Dict[str, Any], fwd: Dict[str, Any], rev: Dict[str, Any], target_seq: str) -> None:
    fwd_seq = fwd.get("sequence", "")
    rev_seq = rev.get("sequence", "")
    target_upper = target_seq.upper()

    if target_upper and fwd_seq and fwd.get("start") is None:
        fwd_idx = target_upper.find(fwd_seq.upper())
        if fwd_idx >= 0:
            fwd["start"] = fwd_idx

    if target_upper and rev_seq and rev.get("start") is None:
        rev_comp = _reverse_complement(rev_seq)
        rev_idx = target_upper.find(rev_comp.upper())
        if rev_idx >= 0:
            rev["start"] = rev_idx

    for primer in (fwd, rev):
        start = primer.get("start")
        length = primer.get("length", len(primer.get("sequence", "")))
        if isinstance(start, int) and length:
            primer.setdefault("start_pos", start + 1)
            primer.setdefault("stop_pos", start + length)

    if "product_start" not in pair and fwd.get("start_pos"):
        pair["product_start"] = fwd["start_pos"]
    if "product_end" not in pair and rev.get("stop_pos"):
        pair["product_end"] = rev["stop_pos"]


def _extract_amplicon_sequence(pair: Dict[str, Any], target_seq: str) -> str:
    if not target_seq:
        return ""
    start = pair.get("product_start")
    end = pair.get("product_end")
    if isinstance(start, int) and isinstance(end, int) and 1 <= start <= end <= len(target_seq):
        return target_seq[start - 1:end]
    size = pair.get("amplicon_size") or pair.get("product_size")
    if isinstance(start, int) and isinstance(size, int):
        inferred_end = start + size - 1
        if 1 <= start <= inferred_end <= len(target_seq):
            pair["product_end"] = inferred_end
            return target_seq[start - 1:inferred_end]
    return ""


def _gc_percent(sequence: str) -> float:
    if not sequence:
        return 0.0
    seq = sequence.upper()
    return round(((seq.count("G") + seq.count("C")) / len(seq)) * 100.0, 2)


def _gc_clamp(sequence: str) -> bool:
    return bool(sequence) and sequence[-1].upper() in {"G", "C"}


def _numeric(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _numeric_or_none(value: Any):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _measured_primer_quality(primer: Dict[str, Any]):
    tm = _numeric_or_none(primer.get("tm"))
    gc = _numeric_or_none(primer.get("gc"))
    hairpin_dg = _numeric_or_none(primer.get("hairpin_dg"))
    self_dimer_dg = _numeric_or_none(primer.get("self_dimer_dg"))
    gc_clamp_ok = primer.get("gc_clamp_ok")
    if None in (tm, gc, hairpin_dg, self_dimer_dg) or gc_clamp_ok is None:
        return None

    score = 100.0
    score -= max(0.0, abs(gc - 50.0) - 10.0) * 2.0
    score -= max(0.0, abs(tm - 62.0) - 7.0) * 3.0
    score -= max(0.0, -hairpin_dg - 1.5) * 5.0
    score -= max(0.0, -self_dimer_dg - 4.0) * 5.0
    if not gc_clamp_ok:
        score -= 8.0
    return max(0.0, min(100.0, round(score, 1)))


def _reverse_complement(sequence: str) -> str:
    return sequence.upper().translate(str.maketrans("ACGTN", "TGCAN"))[::-1]


# ---------------------------------------------------------------------------
# Penalty Aggregation
# ---------------------------------------------------------------------------

def _aggregate_penalties(pair: Dict[str, Any]) -> float:
    """
    Aggregate all penalties from steps 5, 7, 10, 11, 12, 13, 14, 15, 16, 18.
    Uses the design-spec weights.
    """
    total = 0.0

    # ── Get accumulated penalties dict (from individual steps) ─────────────
    penalties = pair.get("penalties", {})

    # Step 10: BLAST specificity (off_target)
    if pair.get("specificity_pass") is False:
        total += PENALTY_WEIGHTS["off_target"]
    # Also add any explicitly recorded off-target penalties
    total += penalties.get("off_target_fwd", 0)
    total += penalties.get("off_target_rev", 0)
    total += penalties.get("off_target_amplicon", 0)

    # Step 11: Bowtie2 / Pseudogene
    if pair.get("pseudogene_hit"):
        total += PENALTY_WEIGHTS["pseudogene"]
    elif pair.get("bowtie2_pass") is False:
        total += PENALTY_WEIGHTS["pseudogene"]
    total += penalties.get("pseudogene", 0)
    total += penalties.get("multi_map_fwd", 0)
    total += penalties.get("multi_map_rev", 0)

    # Step 15: dbSNP 3' critical
    if pair.get("snp_pass") is False:
        # Use accumulated penalty from step 15 or default
        snp_penalty = penalties.get("snp_3prime_fwd", 0) + penalties.get("snp_3prime_rev", 0)
        if snp_penalty == 0:
            total += PENALTY_WEIGHTS["snp_3prime"]
        else:
            total += snp_penalty

    # Step 5: Repeat masking
    if pair.get("repeat_pass") is False:
        total += PENALTY_WEIGHTS["repeat_overlap"]
    total += penalties.get("repeat_overlap", 0)

    # Step 7: ΔTm excess
    delta_tm = _numeric_or_none(pair.get("delta_tm_nn") or pair.get("delta_tm"))
    if delta_tm is not None and delta_tm > 1.5:
        # Penalty proportional to excess over 1.5°C
        tm_penalty = (delta_tm - 1.5) * PENALTY_WEIGHTS["delta_tm"]
        total += tm_penalty
    total += penalties.get("delta_tm_penalty", 0)

    # Step 16: Clinical hotspot
    if pair.get("clinical_hotspot_overlap") or pair.get("clinical_pass") is False:
        total += PENALTY_WEIGHTS["clinical_hotspot"]
    total += penalties.get("clinical_hotspot", 0)

    # Step 14: Amplicon stall
    if pair.get("amplicon_stall_risk") or pair.get("amplicon_pass") is False:
        total += PENALTY_WEIGHTS["amplicon_stall"]
    total += penalties.get("amplicon_stall", 0)

    # Step 13: Dimer risk (self-dimer + cross-dimer)
    fwd_dimer = _numeric_or_none(pair.get("forward", {}).get("self_dimer_dg"))
    rev_dimer = _numeric_or_none(pair.get("reverse", {}).get("self_dimer_dg"))
    cross_dimer = _numeric_or_none(pair.get("cross_dimer_dg"))
    if (
        (fwd_dimer is not None and fwd_dimer < -5.0)
        or (rev_dimer is not None and rev_dimer < -5.0)
        or (cross_dimer is not None and cross_dimer < -5.0)
    ):
        total += PENALTY_WEIGHTS["dimer"]
    total += penalties.get("self_dimer_fwd", 0)
    total += penalties.get("self_dimer_rev", 0)
    total += penalties.get("cross_dimer", 0)

    # Step 18: Multiplex incompatibility
    if pair.get("multiplex_compatible") is False:
        total += PENALTY_WEIGHTS["multiplex_incompatible"]
    total += penalties.get("multiplex_incompatible", 0)

    # Step 13: Hairpin risk
    fwd_hp = _numeric_or_none(pair.get("forward", {}).get("hairpin_dg"))
    rev_hp = _numeric_or_none(pair.get("reverse", {}).get("hairpin_dg"))
    if (
        (fwd_hp is not None and fwd_hp < -2.0)
        or (rev_hp is not None and rev_hp < -2.0)
    ):
        total += PENALTY_WEIGHTS["hairpin"]
    total += penalties.get("hairpin_fwd", 0)
    total += penalties.get("hairpin_rev", 0)

    # Step 12: Organelle screening
    total += penalties.get("organelle", 0)

    # Primer3 original penalty (if available)
    p3_penalty = pair.get("penalty", 0)
    if p3_penalty > 0:
        total += p3_penalty * 1.0  # 1:1 pass-through of Primer3 penalty

    return total


# ---------------------------------------------------------------------------
# Status Assignment
# ---------------------------------------------------------------------------

def _assign_status(total_penalty: float) -> str:
    """Assign PASS/REVIEW/FAIL based on total penalty thresholds."""
    if total_penalty < STATUS_THRESHOLDS["PASS"][1]:
        return "PASS"
    elif total_penalty <= STATUS_THRESHOLDS["REVIEW"][1]:
        return "REVIEW"
    else:
        return "FAIL"


# ---------------------------------------------------------------------------
# Penalty Breakdown
# ---------------------------------------------------------------------------

def _build_penalty_breakdown(pair: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build a detailed breakdown of penalties for reporting."""
    breakdown = []

    # BLAST specificity
    if pair.get("specificity_pass") is False:
        breakdown.append({
            "source": "step10_blast",
            "reason": "Off-target BLAST hits",
            "penalty": PENALTY_WEIGHTS["off_target"],
        })

    # Bowtie2 / Pseudogene
    if pair.get("pseudogene_hit"):
        breakdown.append({
            "source": "step11_bowtie2",
            "reason": "Pseudogene/organelle hit",
            "penalty": PENALTY_WEIGHTS["pseudogene"],
        })
    elif pair.get("bowtie2_pass") is False:
        breakdown.append({
            "source": "step11_bowtie2",
            "reason": "Multi-mapper detected",
            "penalty": PENALTY_WEIGHTS["pseudogene"],
        })

    # dbSNP 3' critical
    if pair.get("snp_pass") is False:
        fwd_count = pair.get("forward", {}).get("snp_3prime_count", 0)
        rev_count = pair.get("reverse", {}).get("snp_3prime_count", 0)
        breakdown.append({
            "source": "step15_dbsnp",
            "reason": f"3' critical SNP (fwd:{fwd_count}, rev:{rev_count})",
            "penalty": PENALTY_WEIGHTS["snp_3prime"],
        })

    # Repeat overlap
    if pair.get("repeat_pass") is False:
        breakdown.append({
            "source": "step05_repeat",
            "reason": "Primer overlaps repetitive element",
            "penalty": PENALTY_WEIGHTS["repeat_overlap"],
        })

    # ΔTm
    delta_tm = _numeric_or_none(pair.get("delta_tm_nn") or pair.get("delta_tm"))
    if delta_tm is not None and delta_tm > 1.5:
        breakdown.append({
            "source": "step07_tm",
            "reason": f"ΔTm={delta_tm:.1f}°C exceeds 1.5°C threshold",
            "penalty": round((delta_tm - 1.5) * PENALTY_WEIGHTS["delta_tm"], 1),
        })

    # Clinical hotspot
    if pair.get("clinical_hotspot_overlap"):
        breakdown.append({
            "source": "step16_clinical",
            "reason": "Overlaps ClinVar hotspot",
            "penalty": PENALTY_WEIGHTS["clinical_hotspot"],
        })

    # Amplicon stall
    if pair.get("amplicon_stall_risk"):
        dg = _numeric_or_none(pair.get("amplicon_dg_72C"))
        dg_text = f"{dg:.1f}" if dg is not None else "N/A"
        breakdown.append({
            "source": "step14_amplicon",
            "reason": f"Amplicon ΔG={dg_text} kcal/mol — Taq stall risk",
            "penalty": PENALTY_WEIGHTS["amplicon_stall"],
        })

    # Dimer
    cross_dg = _numeric_or_none(pair.get("cross_dimer_dg"))
    if cross_dg is not None and cross_dg < -5.0:
        breakdown.append({
            "source": "step13_structure",
            "reason": f"Cross-dimer ΔG={cross_dg:.1f} kcal/mol",
            "penalty": PENALTY_WEIGHTS["dimer"],
        })

    # Multiplex
    if pair.get("multiplex_compatible") is False:
        worst_dg = _numeric_or_none(pair.get("cross_pool_worst_dg"))
        worst_dg_text = f"{worst_dg:.1f}" if worst_dg is not None else "N/A"
        breakdown.append({
            "source": "step18_multiplex",
            "reason": f"Pool cross-dimer ΔG={worst_dg_text} kcal/mol",
            "penalty": PENALTY_WEIGHTS["multiplex_incompatible"],
        })

    # Hairpin
    fwd_hp = _numeric_or_none(pair.get("forward", {}).get("hairpin_dg"))
    rev_hp = _numeric_or_none(pair.get("reverse", {}).get("hairpin_dg"))
    if (
        (fwd_hp is not None and fwd_hp < -2.0)
        or (rev_hp is not None and rev_hp < -2.0)
    ):
        fwd_hp_text = f"{fwd_hp:.1f}" if fwd_hp is not None else "N/A"
        rev_hp_text = f"{rev_hp:.1f}" if rev_hp is not None else "N/A"
        breakdown.append({
            "source": "step13_structure",
            "reason": f"Hairpin (fwd ΔG={fwd_hp_text}, rev ΔG={rev_hp_text} kcal/mol)",
            "penalty": PENALTY_WEIGHTS["hairpin"],
        })

    return breakdown

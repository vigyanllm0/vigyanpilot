"""
Step 6: Core Primer3 Baseline Design
======================================
Generate candidate primer pairs using Primer3 with industry constraints,
then post-filter for strict enforcement of:

- Primer length: [18, 25] nucleotides (Requirement 6.1)
- GC content: [40%, 60%] (Requirement 6.2)
- Tm window: user-specified or default 58-62°C, bounded [50, 72]°C (Requirement 6.3)
- 3' homopolymer: reject if >3 consecutive identical in last 5nt (Requirement 6.4)
- Request 20 candidate pairs from Primer3 (Requirement 6.5)
- Flag low_candidate_yield if <5 pairs after filtering (Requirement 6.6)
- Max ΔTm ≤ 1.5°C between forward and reverse (Requirement 6.7)
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Constraint constants
PRIMER_LENGTH_MIN = 18
PRIMER_LENGTH_MAX = 25
GC_MIN = 40.0
GC_MAX = 60.0
TM_DEFAULT_MIN = 58.0
TM_DEFAULT_MAX = 62.0
TM_ABSOLUTE_MIN = 50.0
TM_ABSOLUTE_MAX = 72.0
MAX_DELTA_TM = 1.5
NUM_CANDIDATES_REQUESTED = 20
LOW_YIELD_THRESHOLD = 5
HOMOPOLYMER_MAX_RUN = 3  # reject if > 3 consecutive identical in last 5nt


def _compute_gc_content(sequence: str) -> float:
    """Compute GC content as a percentage for a DNA sequence."""
    seq_upper = sequence.upper()
    if len(seq_upper) == 0:
        return 0.0
    gc_count = seq_upper.count("G") + seq_upper.count("C")
    return round((gc_count / len(seq_upper)) * 100.0, 2)


def _has_3prime_homopolymer(sequence: str) -> bool:
    """
    Check if a primer has >3 consecutive identical nucleotides
    within the last 5 nucleotides of its 3' terminus.

    Returns True if the primer should be REJECTED.
    """
    if len(sequence) < 5:
        tail = sequence.upper()
    else:
        tail = sequence[-5:].upper()

    # Check for runs of >3 consecutive identical bases in the tail
    max_run = 1
    current_run = 1
    for i in range(1, len(tail)):
        if tail[i] == tail[i - 1]:
            current_run += 1
            if current_run > max_run:
                max_run = current_run
        else:
            current_run = 1

    return max_run > HOMOPOLYMER_MAX_RUN


def _validate_tm_window(tm_min: float, tm_max: float) -> tuple[float, float]:
    """
    Validate and clamp the Tm window to absolute bounds [50, 72]°C.

    Returns the validated (tm_min, tm_max) tuple.
    """
    tm_min = max(TM_ABSOLUTE_MIN, min(tm_min, TM_ABSOLUTE_MAX))
    tm_max = max(TM_ABSOLUTE_MIN, min(tm_max, TM_ABSOLUTE_MAX))
    if tm_min > tm_max:
        tm_min, tm_max = tm_max, tm_min
    return tm_min, tm_max


def _passes_length_constraint(length: int) -> bool:
    """Check if primer length is within [18, 25]."""
    return PRIMER_LENGTH_MIN <= length <= PRIMER_LENGTH_MAX


def _passes_gc_constraint(gc_percent: float) -> bool:
    """Check if GC content is within [40%, 60%]."""
    return GC_MIN <= gc_percent <= GC_MAX


def _passes_tm_constraint(tm: float, tm_min: float, tm_max: float) -> bool:
    """Check if Tm falls within the user-specified window."""
    return tm_min <= tm <= tm_max


def _filter_candidate(
    primer_info: dict[str, Any],
    tm_min: float,
    tm_max: float,
) -> tuple[bool, str]:
    """
    Post-filter a single primer against constraints.

    Returns (passes, rejection_reason).
    """
    seq = primer_info["sequence"]
    length = len(seq)
    gc = primer_info["gc"]
    tm = primer_info["tm"]

    if not _passes_length_constraint(length):
        return False, f"length_violation ({length}nt not in [18,25])"

    if not _passes_gc_constraint(gc):
        return False, f"gc_violation ({gc}% not in [40,60])"

    if not _passes_tm_constraint(tm, tm_min, tm_max):
        return False, f"tm_violation ({tm}°C not in [{tm_min},{tm_max}])"

    if _has_3prime_homopolymer(seq):
        return False, "3prime_homopolymer"

    return True, ""


def execute(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Step 6: Run Primer3 to generate baseline candidate pairs, then post-filter.

    Input keys:
        - consensus_sequence (or target_sequence): DNA sequence template
        - design_params (optional): dict with tm_min, tm_max, product_size_min, product_size_max

    Output keys:
        - candidate_pairs: list of dicts with forward, reverse, product_size, penalty,
          forward_tm, reverse_tm, delta_tm
        - low_candidate_yield: bool (True if < 5 pairs after filtering)
        - pair_count: int (number of pairs after filtering)
    """
    try:
        import primer3 as p3
    except ImportError:
        raise RuntimeError("primer3 Python package is required for Primer3 design. Install: pip install primer3")

    # Extract sequence
    sequence = input_data.get("consensus_sequence") or input_data.get("target_sequence", "")
    if not sequence:
        raise ValueError("No sequence available for Primer3 design")

    # Clean sequence (replace non-ACGT with N for primer3)
    clean_seq = re.sub(r'[^ACGTacgt]', 'N', sequence.upper())

    # Extract design parameters
    design_params = input_data.get("design_params", {}) or {}

    # Tm window: user-specified or defaults, bounded to [50, 72]
    tm_min = design_params.get("tm_min", TM_DEFAULT_MIN)
    tm_max = design_params.get("tm_max", TM_DEFAULT_MAX)
    tm_min, tm_max = _validate_tm_window(tm_min, tm_max)
    opt_tm = (tm_min + tm_max) / 2.0

    # Product size range
    product_min = design_params.get("product_size_min", input_data.get("product_min", 80))
    product_max = design_params.get("product_size_max", input_data.get("product_max", 500))

    # Get buffer conditions (passed from upstream steps or defaults)
    buffer = input_data.get("buffer", {}) or {}
    na_mm = buffer.get("monovalent_mm", 50.0)
    mg_mm = buffer.get("divalent_mm", 1.5)
    dntp_mm = buffer.get("dntp_mm", 0.2)
    oligo_nm = buffer.get("oligo_conc_nm", 250.0)

    # Run Primer3 — request 20 candidates (Requirement 6.5)
    try:
        p3_result = p3.design_primers(
            seq_args={
                'SEQUENCE_TEMPLATE': clean_seq,
                'SEQUENCE_INCLUDED_REGION': [0, len(clean_seq)],
            },
            global_args={
                'PRIMER_NUM_RETURN': NUM_CANDIDATES_REQUESTED,
                'PRIMER_OPT_SIZE': 20,
                'PRIMER_MIN_SIZE': PRIMER_LENGTH_MIN,
                'PRIMER_MAX_SIZE': PRIMER_LENGTH_MAX,
                'PRIMER_OPT_TM': opt_tm,
                'PRIMER_MIN_TM': tm_min,
                'PRIMER_MAX_TM': tm_max,
                'PRIMER_MIN_GC': GC_MIN,
                'PRIMER_MAX_GC': GC_MAX,
                'PRIMER_PRODUCT_SIZE_RANGE': [[product_min, product_max]],
                'PRIMER_DNA_CONC': oligo_nm,
                'PRIMER_SALT_MONOVALENT': na_mm,
                'PRIMER_SALT_DIVALENT': mg_mm,
                'PRIMER_DNTP_CONC': dntp_mm,
                'PRIMER_MAX_SELF_ANY_TH': 45.0,
                'PRIMER_MAX_SELF_END_TH': 35.0,
                'PRIMER_MAX_HAIRPIN_TH': 47.0,
                'PRIMER_PAIR_MAX_COMPL_ANY_TH': 45.0,
                'PRIMER_PAIR_MAX_COMPL_END_TH': 35.0,
                'PRIMER_MAX_POLY_X': 4,
                'PRIMER_PAIR_MAX_DIFF_TM': MAX_DELTA_TM,
                'PRIMER_GC_CLAMP': 1,
            }
        )
    except Exception as e:
        raise RuntimeError(f"Primer3 design failed: {e}")

    num_returned = p3_result.get('PRIMER_PAIR_NUM_RETURNED', 0)

    if num_returned == 0:
        return {
            "candidate_pairs": [],
            "low_candidate_yield": True,
            "pair_count": 0,
        }

    # Extract raw candidate pairs from Primer3 output
    raw_pairs = []
    for i in range(num_returned):
        left_pos = p3_result.get(f'PRIMER_LEFT_{i}')
        right_pos = p3_result.get(f'PRIMER_RIGHT_{i}')
        fwd_seq = p3_result.get(f'PRIMER_LEFT_{i}_SEQUENCE', "")
        rev_seq = p3_result.get(f'PRIMER_RIGHT_{i}_SEQUENCE', "")
        fwd_tm = round(p3_result.get(f'PRIMER_LEFT_{i}_TM', 0.0), 2)
        rev_tm = round(p3_result.get(f'PRIMER_RIGHT_{i}_TM', 0.0), 2)
        fwd_gc = round(p3_result.get(f'PRIMER_LEFT_{i}_GC_PERCENT', 0.0), 2)
        rev_gc = round(p3_result.get(f'PRIMER_RIGHT_{i}_GC_PERCENT', 0.0), 2)
        product_size = p3_result.get(f'PRIMER_PAIR_{i}_PRODUCT_SIZE', 0)
        penalty = p3_result.get(f'PRIMER_PAIR_{i}_PENALTY', 0.0)

        if left_pos is None or right_pos is None:
            continue

        raw_pairs.append({
            "pair_index": i,
            "forward": {
                "sequence": fwd_seq,
                "start": left_pos[0],
                "length": left_pos[1],
                "tm": fwd_tm,
                "gc": fwd_gc,
            },
            "reverse": {
                "sequence": rev_seq,
                "start": right_pos[0],
                "length": right_pos[1],
                "tm": rev_tm,
                "gc": rev_gc,
            },
            "product_size": product_size,
            "penalty": round(penalty, 3),
        })

    # Post-filter: enforce constraints AFTER Primer3 returns candidates
    filtered_pairs = []
    for pair in raw_pairs:
        fwd = pair["forward"]
        rev = pair["reverse"]

        # Check forward primer constraints
        fwd_passes, fwd_reason = _filter_candidate(fwd, tm_min, tm_max)
        if not fwd_passes:
            logger.debug(
                f"Pair {pair['pair_index']} rejected: forward primer {fwd_reason}"
            )
            continue

        # Check reverse primer constraints
        rev_passes, rev_reason = _filter_candidate(rev, tm_min, tm_max)
        if not rev_passes:
            logger.debug(
                f"Pair {pair['pair_index']} rejected: reverse primer {rev_reason}"
            )
            continue

        # Check ΔTm constraint (Requirement 6.7)
        delta_tm = round(abs(fwd["tm"] - rev["tm"]), 2)
        if delta_tm > MAX_DELTA_TM:
            logger.debug(
                f"Pair {pair['pair_index']} rejected: delta_tm={delta_tm}°C > {MAX_DELTA_TM}°C"
            )
            continue

        # Pair passes all post-filters
        fwd_start = fwd["start"]
        fwd_length = fwd["length"]
        rev_start = rev["start"] - rev["length"] + 1
        rev_length = rev["length"]
        amplicon_start = fwd_start
        amplicon_end = rev["start"]
        filtered_pairs.append({
            "forward": fwd["sequence"],
            "reverse": rev["sequence"],
            "forward_start": fwd_start,
            "forward_start_pos": fwd_start + 1,
            "forward_stop_pos": fwd_start + fwd_length,
            "forward_length": fwd_length,
            "reverse_start": rev_start,
            "reverse_start_pos": rev_start + 1,
            "reverse_stop_pos": rev_start + rev_length,
            "reverse_length": rev_length,
            "product_start": amplicon_start + 1,
            "product_end": amplicon_end + 1,
            "amplicon_sequence": clean_seq[amplicon_start:amplicon_end + 1],
            "product_size": pair["product_size"],
            "penalty": pair["penalty"],
            "forward_tm": fwd["tm"],
            "reverse_tm": rev["tm"],
            "delta_tm": delta_tm,
        })

    pair_count = len(filtered_pairs)
    low_candidate_yield = pair_count < LOW_YIELD_THRESHOLD

    if low_candidate_yield:
        logger.warning(
            f"Low candidate yield: only {pair_count} pairs passed post-filtering "
            f"(threshold: {LOW_YIELD_THRESHOLD})"
        )

    # Assign pair_id to each candidate pair for tracking through pipeline
    for i, pair in enumerate(filtered_pairs):
        pair["pair_id"] = i + 1

    return {
        "candidate_pairs": filtered_pairs,
        "low_candidate_yield": low_candidate_yield,
        "pair_count": pair_count,
    }

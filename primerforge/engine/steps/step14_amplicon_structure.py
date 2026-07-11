"""
Step 14: Amplicon Secondary Structure Verification
====================================================
Predict internal hairpin/palindromic structures within the amplicon at the
extension temperature (72°C). Taq polymerase can stall on highly stable
internal structures, causing incomplete extension and dropout.

Strategy:
  - Compute folding ΔG of the amplicon at 72°C
  - Flag "amplicon_stall_risk" if ΔG < -8.0 kcal/mol
  - Report position, length, and ΔG of the most stable structure
  - Skip analysis for amplicons < 20nt (too short for stable folding)
"""

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────
AMPLICON_DG_THRESHOLD = -8.0  # kcal/mol at 72°C
MIN_AMPLICON_LENGTH = 20  # Skip for amplicons shorter than this
EXTENSION_TEMPERATURE = 72.0  # °C (standard Taq extension)
AMPLICON_STALL_PENALTY = 10.0

# Minimum hairpin loop size and stem length for internal structure prediction
MIN_LOOP_SIZE = 3
MIN_STEM_LENGTH = 4


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def execute(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Step 14: Check amplicon folding stability at extension temperature.

    Input keys:
        - structure_checked (list): Pairs from Step 13
        - target_sequence (str): Full target sequence for amplicon extraction

    Output keys:
        - amplicon_checked (list): Pairs with folding annotations
        - amplicon_note (str): Summary
    """
    pairs = input_data.get("structure_checked", [])
    if not pairs:
        return {"amplicon_checked": [], "amplicon_note": "No pairs to check"}

    target_seq = (
        input_data.get("target_sequence")
        or input_data.get("consensus_sequence", "")
    )

    # ── Try to use the thermodynamics engine for folding prediction ─────────
    use_engine = _check_engine_available()

    amplicon_checked = []
    stall_risk_count = 0

    for pair in pairs:
        pair.setdefault("penalties", {})

        # ── Extract amplicon sequence ──────────────────────────────────────
        amplicon_seq = _extract_amplicon(pair, target_seq)
        pair["amplicon_sequence"] = amplicon_seq

        if not amplicon_seq or len(amplicon_seq) < MIN_AMPLICON_LENGTH:
            # Skip — amplicon too short for meaningful structure prediction
            pair["amplicon_dg_72C"] = 0.0
            pair["amplicon_stall_risk"] = False
            pair["amplicon_pass"] = True
            pair["amplicon_length"] = len(amplicon_seq) if amplicon_seq else 0
            pair["amplicon_detail"] = (
                f"Amplicon too short ({len(amplicon_seq) if amplicon_seq else 0}nt < {MIN_AMPLICON_LENGTH}nt) "
                "— skipping structure prediction."
            )
            amplicon_checked.append(pair)
            continue

        # ── Predict folding at extension temperature ───────────────────────
        if use_engine:
            fold_result = _predict_folding_engine(amplicon_seq)
        else:
            fold_result = _predict_folding_heuristic(amplicon_seq)

        pair["amplicon_dg_72C"] = fold_result["delta_g"]
        pair["amplicon_stall_risk"] = fold_result["delta_g"] < AMPLICON_DG_THRESHOLD
        pair["amplicon_pass"] = fold_result["delta_g"] >= AMPLICON_DG_THRESHOLD
        pair["amplicon_length"] = len(amplicon_seq)
        pair["amplicon_structure_position"] = fold_result.get("position")
        pair["amplicon_structure_length"] = fold_result.get("structure_length")
        pair["amplicon_detail"] = fold_result["detail"]

        if pair["amplicon_stall_risk"]:
            stall_risk_count += 1
            pair["penalties"]["amplicon_stall"] = AMPLICON_STALL_PENALTY
            pair.setdefault("forward", {}).setdefault("flags", []).append("amplicon_stall_risk")

        amplicon_checked.append(pair)

    passed = len(amplicon_checked) - stall_risk_count

    # Ensure pair_id is preserved for all pairs
    for i, pair in enumerate(amplicon_checked):
        if not pair.get("pair_id"):
            pair["pair_id"] = i + 1

    return {
        "amplicon_checked": amplicon_checked,
        "amplicon_note": (
            f"{passed}/{len(amplicon_checked)} pairs have safe amplicon structure at {EXTENSION_TEMPERATURE}°C. "
            f"{stall_risk_count} flagged with stall risk (ΔG < {AMPLICON_DG_THRESHOLD} kcal/mol)."
        ),
    }


# ---------------------------------------------------------------------------
# Amplicon Extraction
# ---------------------------------------------------------------------------

def _extract_amplicon(pair: dict[str, Any], target_seq: str) -> str:
    """Extract amplicon sequence from target using primer positions."""
    fwd = pair.get("forward", {})
    rev = pair.get("reverse", {})

    # Try explicit amplicon_sequence first
    if pair.get("amplicon_sequence"):
        return pair["amplicon_sequence"]

    # Try to extract from target using positions
    fwd_start = fwd.get("start", fwd.get("position", 0))
    rev_end = rev.get("end", rev.get("position", 0))

    # Some pipelines store rev as the start of the reverse primer on the template
    if rev_end == 0:
        rev_start = rev.get("start", 0)
        rev_len = rev.get("length", len(rev.get("sequence", "")))
        rev_end = rev_start + rev_len if rev_start else 0

    if target_seq and fwd_start < rev_end and rev_end <= len(target_seq):
        return target_seq[fwd_start:rev_end]

    # Fallback: try to infer from sequences + target
    fwd_seq = fwd.get("sequence", "")
    if target_seq and fwd_seq:
        idx = target_seq.upper().find(fwd_seq.upper())
        if idx >= 0:
            # Find reverse primer complement in target
            rev_seq = rev.get("sequence", "")
            rev_comp = _reverse_complement(rev_seq)
            rev_idx = target_seq.upper().find(rev_comp.upper(), idx)
            if rev_idx >= 0:
                return target_seq[idx : rev_idx + len(rev_seq)]

    return ""


# ---------------------------------------------------------------------------
# Structure Prediction
# ---------------------------------------------------------------------------

def _predict_folding_engine(amplicon_seq: str) -> dict[str, Any]:
    """Use the internal thermodynamics engine for folding prediction."""
    try:
        from ..thermodynamics import predict_amplicon_folding

        result = predict_amplicon_folding(amplicon_seq, temperature_c=EXTENSION_TEMPERATURE)
        return {
            "delta_g": round(result.delta_g, 2),
            "is_stable": result.is_stable,
            "detail": result.details,
            "position": None,
            "structure_length": None,
        }
    except Exception as e:
        logger.debug("Engine folding prediction failed: %s", e)
        return _predict_folding_heuristic(amplicon_seq)


def _predict_folding_heuristic(amplicon_seq: str) -> dict[str, Any]:
    """
    Heuristic amplicon folding prediction based on palindrome/inverted repeat detection.
    Estimates ΔG at extension temperature using nearest-neighbor model.
    """
    seq = amplicon_seq.upper()
    n = len(seq)

    best_dg = 0.0
    best_position = None
    best_length = None

    # Scan for inverted repeats (potential hairpins) using a sliding window approach
    for loop_center in range(MIN_STEM_LENGTH + MIN_LOOP_SIZE, n - MIN_STEM_LENGTH):
        for stem_len in range(MIN_STEM_LENGTH, min(15, loop_center, n - loop_center)):
            for loop_size in range(MIN_LOOP_SIZE, min(12, n - loop_center)):
                left_start = loop_center - stem_len - loop_size // 2
                right_end = loop_center + stem_len + loop_size // 2

                if left_start < 0 or right_end > n:
                    continue

                left_arm = seq[left_start : left_start + stem_len]
                right_arm = seq[right_end - stem_len : right_end]

                # Check complementarity
                matches = _count_complement_matches(left_arm, right_arm)
                if matches >= stem_len * 0.75:  # ≥75% complementarity
                    # Estimate ΔG for this stem-loop at 72°C
                    dg = _estimate_stem_loop_dg(
                        left_arm, right_arm, loop_size, EXTENSION_TEMPERATURE
                    )
                    if dg < best_dg:
                        best_dg = dg
                        best_position = left_start
                        best_length = right_end - left_start

            # Early break if we found a very stable structure
            if best_dg < AMPLICON_DG_THRESHOLD * 1.5:
                break

    is_stable = best_dg < AMPLICON_DG_THRESHOLD
    detail = (
        f"ΔG={best_dg:.1f} kcal/mol at {EXTENSION_TEMPERATURE}°C"
        + (f" (position {best_position}, length {best_length}nt)" if best_position is not None else "")
        + (" — STALL RISK" if is_stable else " — OK")
    )

    return {
        "delta_g": round(best_dg, 2),
        "is_stable": is_stable,
        "detail": detail,
        "position": best_position,
        "structure_length": best_length,
    }


# ---------------------------------------------------------------------------
# Thermodynamic Estimation Helpers
# ---------------------------------------------------------------------------

# Simplified nearest-neighbor ΔH/ΔS for stem estimation
_NN_DH = {
    "AT": -7.2, "TA": -7.2, "GC": -9.8, "CG": -10.6,
    "AA": -7.9, "TT": -7.9, "GA": -8.2, "TC": -8.2,
    "CA": -8.5, "TG": -8.5, "GT": -8.4, "AC": -8.4,
    "CT": -7.8, "AG": -7.8, "GG": -8.0, "CC": -8.0,
}

_NN_DS = {
    "AT": -20.4, "TA": -21.3, "GC": -24.4, "CG": -27.2,
    "AA": -22.2, "TT": -22.2, "GA": -22.2, "TC": -22.2,
    "CA": -22.7, "TG": -22.7, "GT": -22.4, "AC": -22.4,
    "CT": -21.0, "AG": -21.0, "GG": -19.9, "CC": -19.9,
}

COMPLEMENT = {"A": "T", "T": "A", "G": "C", "C": "G"}


def _estimate_stem_loop_dg(
    left_arm: str, right_arm: str, loop_size: int, temperature_c: float
) -> float:
    """
    Estimate ΔG for a stem-loop structure at the given temperature.
    ΔG(T) = ΔH - T × ΔS
    """
    temperature_k = temperature_c + 273.15

    # Sum ΔH and ΔS for stem base pairs
    dh_total = 0.0
    ds_total = 0.0

    rev_right = right_arm[::-1]
    for i in range(len(left_arm) - 1):
        doublet = left_arm[i : i + 2]
        if doublet in _NN_DH:
            dh_total += _NN_DH[doublet]
            ds_total += _NN_DS[doublet]

    # Loop penalty (Jacobson-Stockmayer): ΔG_loop ≈ 1.75 × R × T × ln(loop_size)
    R_kcal = 1.987 / 1000.0  # kcal/(mol·K)
    if loop_size > 0:
        loop_penalty = 1.75 * R_kcal * temperature_k * math.log(loop_size)
    else:
        loop_penalty = 0.0

    # ΔG at temperature
    dg = dh_total - (temperature_k * ds_total / 1000.0) + loop_penalty

    return dg


def _count_complement_matches(left: str, right: str) -> int:
    """Count Watson-Crick complement matches between left arm and reversed right arm."""
    rev_right = right[::-1]
    matches = 0
    for i in range(min(len(left), len(rev_right))):
        if COMPLEMENT.get(left[i]) == rev_right[i]:
            matches += 1
    return matches


def _reverse_complement(seq: str) -> str:
    """Return the reverse complement of a DNA sequence."""
    return "".join(COMPLEMENT.get(base, "N") for base in reversed(seq.upper()))


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _check_engine_available() -> bool:
    """Check if the internal thermodynamics engine is available."""
    try:
        from ..thermodynamics import predict_amplicon_folding  # noqa: F401
        return True
    except ImportError:
        return False

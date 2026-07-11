"""
Step 13: Primer Secondary Structure Validation
================================================
Compute ΔG for hairpins, self-dimers, and cross-dimers using thermodynamic
calculations (primer3-py or internal engine).

Thresholds:
  - Hairpin ΔG:      flag if < -2.0 kcal/mol
  - Self-dimer ΔG:   flag if < -5.0 kcal/mol
  - Cross-dimer ΔG:  flag if < -5.0 kcal/mol

All values are recorded. ALL pairs pass forward regardless of flags — penalties
are applied in Step 19 (ranking). This ensures no candidate is silently dropped
before final scoring.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Thresholds (kcal/mol) — more negative = more stable = worse ────────────
HAIRPIN_THRESHOLD = -2.0
SELF_DIMER_THRESHOLD = -5.0
CROSS_DIMER_THRESHOLD = -5.0

# Penalty weights (applied in annotations, used by Step 19)
HAIRPIN_PENALTY = 5.0
DIMER_PENALTY = 8.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def execute(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Step 13: Secondary structure validation for all primer candidates.

    Input keys:
        - aligned_pairs (list): Pairs from Step 11 (or filtered_pairs / refined_pairs fallback)
        - buffer (dict, optional): Buffer conditions for thermodynamic calcs

    Output keys:
        - structure_checked (list): ALL pairs with ΔG annotations (none dropped)
        - structure_note (str): Summary
    """
    pairs = _select_pair_shaped_candidates(input_data)
    if not pairs:
        return {"structure_checked": [], "structure_note": "No pairs to check"}

    # ── Determine thermodynamic calculation method ─────────────────────────
    use_primer3 = _check_primer3_available()

    # Buffer conditions
    buffer = input_data.get("buffer", {})
    na_mm = buffer.get("monovalent_mm", 50.0)
    mg_mm = buffer.get("divalent_mm", 1.5)
    dntp_mm = buffer.get("dntp_mm", 0.2)
    oligo_nm = buffer.get("oligo_conc_nm", 250.0)

    # ── Process each pair ──────────────────────────────────────────────────
    structure_checked = []
    flagged_count = 0

    for pair in pairs:
        pair = _normalise_pair_schema(pair)
        fwd_seq = pair.get("forward", {}).get("sequence", "")
        rev_seq = pair.get("reverse", {}).get("sequence", "")
        pair.setdefault("penalties", {})
        pair["forward"].setdefault("flags", [])
        pair["reverse"].setdefault("flags", [])

        if not fwd_seq or not rev_seq:
            pair["structure_pass"] = True
            pair["structure_flags"] = []
            structure_checked.append(pair)
            continue

        # ── Compute all ΔG values ─────────────────────────────────────────
        if use_primer3:
            thermo = _compute_with_primer3(fwd_seq, rev_seq, na_mm, mg_mm, dntp_mm, oligo_nm)
        else:
            thermo = _compute_with_engine(fwd_seq, rev_seq)

        # ── Record values on pair ─────────────────────────────────────────
        pair["forward"]["hairpin_dg"] = thermo["fwd_hairpin_dg"]
        pair["forward"]["self_dimer_dg"] = thermo["fwd_self_dimer_dg"]
        pair["reverse"]["hairpin_dg"] = thermo["rev_hairpin_dg"]
        pair["reverse"]["self_dimer_dg"] = thermo["rev_self_dimer_dg"]
        pair.setdefault("forward_primer", {}).update({
            "hairpin_dg": thermo["fwd_hairpin_dg"],
            "self_dimer_dg": thermo["fwd_self_dimer_dg"],
        })
        pair.setdefault("reverse_primer", {}).update({
            "hairpin_dg": thermo["rev_hairpin_dg"],
            "self_dimer_dg": thermo["rev_self_dimer_dg"],
        })
        pair["cross_dimer_dg"] = thermo["cross_dimer_dg"]

        # ── Flag assessment ───────────────────────────────────────────────
        structure_flags = []

        # Forward hairpin
        if thermo["fwd_hairpin_dg"] < HAIRPIN_THRESHOLD:
            structure_flags.append({
                "type": "hairpin",
                "primer": "forward",
                "dg": thermo["fwd_hairpin_dg"],
                "threshold": HAIRPIN_THRESHOLD,
            })
            pair["forward"]["flags"].append("hairpin_stable")
            pair["penalties"]["hairpin_fwd"] = HAIRPIN_PENALTY

        # Reverse hairpin
        if thermo["rev_hairpin_dg"] < HAIRPIN_THRESHOLD:
            structure_flags.append({
                "type": "hairpin",
                "primer": "reverse",
                "dg": thermo["rev_hairpin_dg"],
                "threshold": HAIRPIN_THRESHOLD,
            })
            pair["reverse"]["flags"].append("hairpin_stable")
            pair["penalties"]["hairpin_rev"] = HAIRPIN_PENALTY

        # Forward self-dimer
        if thermo["fwd_self_dimer_dg"] < SELF_DIMER_THRESHOLD:
            structure_flags.append({
                "type": "self_dimer",
                "primer": "forward",
                "dg": thermo["fwd_self_dimer_dg"],
                "threshold": SELF_DIMER_THRESHOLD,
            })
            pair["forward"]["flags"].append("self_dimer_stable")
            pair["penalties"]["self_dimer_fwd"] = DIMER_PENALTY

        # Reverse self-dimer
        if thermo["rev_self_dimer_dg"] < SELF_DIMER_THRESHOLD:
            structure_flags.append({
                "type": "self_dimer",
                "primer": "reverse",
                "dg": thermo["rev_self_dimer_dg"],
                "threshold": SELF_DIMER_THRESHOLD,
            })
            pair["reverse"]["flags"].append("self_dimer_stable")
            pair["penalties"]["self_dimer_rev"] = DIMER_PENALTY

        # Cross-dimer (forward vs reverse)
        if thermo["cross_dimer_dg"] < CROSS_DIMER_THRESHOLD:
            structure_flags.append({
                "type": "cross_dimer",
                "primer": "pair",
                "dg": thermo["cross_dimer_dg"],
                "threshold": CROSS_DIMER_THRESHOLD,
            })
            pair["penalties"]["cross_dimer"] = DIMER_PENALTY

        # ── Pass/flag assessment (informational — pairs still pass forward) ─
        structure_pass = len(structure_flags) == 0
        pair["structure_pass"] = structure_pass
        pair["structure_flags"] = structure_flags

        if not structure_pass:
            flagged_count += 1

        # ALL pairs pass forward regardless of flags
        structure_checked.append(pair)

    passed = len(structure_checked) - flagged_count

    # Ensure pair_id is preserved for all pairs
    for i, pair in enumerate(structure_checked):
        if not pair.get("pair_id"):
            pair["pair_id"] = i + 1

    return {
        "structure_checked": structure_checked,
        "structure_note": (
            f"{passed}/{len(structure_checked)} pairs passed structure validation. "
            f"{flagged_count} flagged (penalties applied, still forwarded)."
        ),
    }


# ---------------------------------------------------------------------------
# Thermodynamic Computation Methods
# ---------------------------------------------------------------------------

def _normalise_pair_schema(pair: dict[str, Any]) -> dict[str, Any]:
    """Accept nested, alias, and flat Primer3 pair schemas without inventing measurements."""
    pair = dict(pair)
    fwd = _normalise_primer(
        pair.get("forward_primer", pair.get("forward")),
        sequence=pair.get("forward_sequence") or pair.get("forward"),
        tm=pair.get("forward_tm"),
        gc=pair.get("forward_gc"),
        length=pair.get("forward_length"),
        start=pair.get("forward_start"),
        start_pos=pair.get("forward_start_pos"),
        stop_pos=pair.get("forward_stop_pos"),
    )
    rev = _normalise_primer(
        pair.get("reverse_primer", pair.get("reverse")),
        sequence=pair.get("reverse_sequence") or pair.get("reverse"),
        tm=pair.get("reverse_tm"),
        gc=pair.get("reverse_gc"),
        length=pair.get("reverse_length"),
        start=pair.get("reverse_start"),
        start_pos=pair.get("reverse_start_pos"),
        stop_pos=pair.get("reverse_stop_pos"),
    )
    pair["forward"] = fwd
    pair["reverse"] = rev
    pair.setdefault("forward_primer", dict(fwd))
    pair.setdefault("reverse_primer", dict(rev))
    return pair


def _normalise_primer(value: Any, **aliases: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        primer = dict(value)
    elif isinstance(value, str):
        primer = {"sequence": value}
    else:
        primer = {}

    sequence = aliases.get("sequence")
    if isinstance(sequence, dict):
        sequence = sequence.get("sequence")
    if sequence and not isinstance(sequence, dict):
        primer.setdefault("sequence", sequence)

    for key in ("tm", "gc", "length", "start", "start_pos", "stop_pos"):
        value = aliases.get(key)
        if value is not None:
            primer.setdefault(key, value)

    primer.setdefault("sequence", "")
    primer.setdefault("length", len(primer.get("sequence", "")))
    return primer


def _select_pair_shaped_candidates(input_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Pick primer-pair records, not flat single-primer lists with similar names."""
    for key in ("aligned_pairs", "refined_pairs", "candidate_pairs", "filtered_pairs"):
        candidates = input_data.get(key) or []
        pair_records = [p for p in candidates if _looks_like_pair(p)]
        if pair_records:
            return pair_records
    return []


def _looks_like_pair(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if value.get("forward_primer") and value.get("reverse_primer"):
        return True
    fwd = value.get("forward")
    rev = value.get("reverse")
    return bool(fwd and rev)

def _compute_with_primer3(
    fwd_seq: str,
    rev_seq: str,
    na_mm: float,
    mg_mm: float,
    dntp_mm: float,
    oligo_nm: float,
) -> dict[str, float]:
    """Compute all ΔG values using primer3-py library."""
    import primer3 as p3

    # Forward hairpin
    fwd_hp = p3.calc_hairpin(
        fwd_seq, mv_conc=na_mm, dv_conc=mg_mm, dntp_conc=dntp_mm, dna_conc=oligo_nm
    )
    # Reverse hairpin
    rev_hp = p3.calc_hairpin(
        rev_seq, mv_conc=na_mm, dv_conc=mg_mm, dntp_conc=dntp_mm, dna_conc=oligo_nm
    )
    # Forward self-dimer (homodimer)
    fwd_sd = p3.calc_homodimer(
        fwd_seq, mv_conc=na_mm, dv_conc=mg_mm, dntp_conc=dntp_mm, dna_conc=oligo_nm
    )
    # Reverse self-dimer (homodimer)
    rev_sd = p3.calc_homodimer(
        rev_seq, mv_conc=na_mm, dv_conc=mg_mm, dntp_conc=dntp_mm, dna_conc=oligo_nm
    )
    # Cross-dimer (heterodimer)
    cross = p3.calc_heterodimer(
        fwd_seq, rev_seq, mv_conc=na_mm, dv_conc=mg_mm, dntp_conc=dntp_mm, dna_conc=oligo_nm
    )

    return {
        "fwd_hairpin_dg": round(fwd_hp.dg / 1000.0, 2),  # cal → kcal
        "rev_hairpin_dg": round(rev_hp.dg / 1000.0, 2),
        "fwd_self_dimer_dg": round(fwd_sd.dg / 1000.0, 2),
        "rev_self_dimer_dg": round(rev_sd.dg / 1000.0, 2),
        "cross_dimer_dg": round(cross.dg / 1000.0, 2),
    }


def _compute_with_engine(fwd_seq: str, rev_seq: str) -> dict[str, float]:
    """Fallback: compute ΔG using internal thermodynamics engine."""
    from ..thermodynamics import predict_cross_dimer, predict_hairpin, predict_self_dimer

    fwd_hp = predict_hairpin(fwd_seq)
    rev_hp = predict_hairpin(rev_seq)
    fwd_sd = predict_self_dimer(fwd_seq)
    rev_sd = predict_self_dimer(rev_seq)
    cross = predict_cross_dimer(fwd_seq, rev_seq)

    return {
        "fwd_hairpin_dg": round(fwd_hp.delta_g, 2),
        "rev_hairpin_dg": round(rev_hp.delta_g, 2),
        "fwd_self_dimer_dg": round(fwd_sd.delta_g, 2),
        "rev_self_dimer_dg": round(rev_sd.delta_g, 2),
        "cross_dimer_dg": round(cross.delta_g, 2),
    }


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _check_primer3_available() -> bool:
    """Check if primer3-py is importable."""
    try:
        import primer3  # noqa: F401
        return True
    except ImportError:
        logger.info("primer3-py not available — using internal thermodynamics engine.")
        return False

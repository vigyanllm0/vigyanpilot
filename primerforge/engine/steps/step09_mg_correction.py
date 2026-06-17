"""
Step 9: Divalent Cation Mg²+ Scaling (von Ahsen 2001)
=======================================================
Applies the von Ahsen 2001 magnesium correction to salt-adjusted Tm values.

The correction accounts for Mg²+-induced duplex stabilization:
    Tm(Mg²+) = Tm(salt) + 7.21·ln([Mg²+_free_in_mM])

Free Mg²+ is computed as total Mg²+ minus dNTP (which chelates Mg²+ at 1:1
stoichiometry). If free Mg²+ ≤ 0, the correction is skipped and a warning
is logged.

Reference:
    von Ahsen N, Wittwer CT, Schütz E (2001). Oligonucleotide melting
    temperatures under PCR conditions: nearest-neighbor corrections for
    Mg²+, deoxynucleotide triphosphate, and dimethyl sulfoxide
    concentrations with comparison to alternative empirical formulas.
    Clin Chem 47(11):1956-61.
"""

import logging
import math
from typing import Any, Dict, List

from .base import PipelineStep

logger = logging.getLogger(__name__)

# Valid range for total Mg²+ concentration (mM)
MG_MIN_MM = 0.1
MG_MAX_MM = 100.0

# von Ahsen 2001 coefficient
VON_AHSEN_COEFFICIENT = 7.21


class MgCorrectionStep(PipelineStep):
    """Applies von Ahsen 2001 Mg²+ Tm correction to primer candidates."""

    def __init__(self):
        super().__init__(name="Divalent Cation Mg²+ Scaling", step_number=9)

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply Mg²+ correction to all primer candidates.

        Input keys:
            primer_candidates: List[Dict] — primers with tm_salt_adjusted values
            free_mg_mm: float — free Mg²+ in mM (from step 8), OR
            mg_total_mm: float — total Mg²+ in mM (if free_mg_mm not provided)
            dntp_mm: float — dNTP concentration in mM (used if computing free Mg²+ here)

        Output keys:
            primer_candidates: List[Dict] — updated with tm_mg_adjusted and delta_tm_penalty
            mg_correction_applied: bool
            free_mg_mm: float — the free Mg²+ value used
            mg_correction_note: str
        """
        primer_candidates = input_data.get("primer_candidates", [])
        if not primer_candidates:
            primer_candidates = _primer_candidates_from_pairs(input_data)
        if not primer_candidates:
            return {
                "primer_candidates": [],
                "mg_correction_applied": False,
                "mg_correction_note": "No primer candidates to process",
            }

        # Determine free Mg²+ concentration
        free_mg_mm = self._resolve_free_mg(input_data)

        # Validate Mg²+ total is within acceptable range if provided
        mg_total_mm = input_data.get("mg_total_mm")
        if mg_total_mm is not None:
            validation_error = self._validate_mg_range(mg_total_mm)
            if validation_error:
                raise ValueError(validation_error)

        # If free Mg²+ ≤ 0, skip correction
        if free_mg_mm is None or free_mg_mm <= 0:
            logger.warning(
                "VigyanLLM: Free Mg²+ is zero or negative (%.4f mM). "
                "Skipping Mg²+ correction — retaining salt-adjusted Tm values.",
                free_mg_mm if free_mg_mm is not None else 0.0,
            )
            # Retain salt-adjusted Tm as the final Tm, no mg correction
            for candidate in primer_candidates:
                tm_salt = _candidate_tm(candidate)
                candidate["tm_mg_adjusted"] = round(tm_salt, 2)
                candidate["delta_tm_penalty"] = 0.0
            return {
                "primer_candidates": primer_candidates,
                "mg_correction_applied": False,
                "free_mg_mm": free_mg_mm if free_mg_mm is not None else 0.0,
                "mg_correction_note": "Insufficient free Mg²+ — correction skipped",
            }

        # Apply von Ahsen 2001 correction to each candidate
        corrected_candidates = self._apply_correction(primer_candidates, free_mg_mm)

        return {
            "primer_candidates": corrected_candidates,
            "mg_correction_applied": True,
            "free_mg_mm": round(free_mg_mm, 4),
            "mg_correction_note": (
                f"Mg²+ correction applied: free [Mg²+] = {free_mg_mm:.4f} mM "
                f"ΔTm offset = {VON_AHSEN_COEFFICIENT * math.log(free_mg_mm):.2f}°C"
            ),
        }

    def _resolve_free_mg(self, input_data: Dict[str, Any]) -> float:
        """
        Resolve free Mg²+ concentration from input data.

        Priority:
        1. Use pre-computed free_mg_mm from step 8
        2. Compute from mg_total_mm - dntp_mm

        Returns:
            Free Mg²+ in mM, or 0.0 if not determinable.
        """
        # Check if step 8 already computed free Mg²+
        free_mg_mm = input_data.get("free_mg_mm")
        if free_mg_mm is not None:
            return float(free_mg_mm)

        # Compute from total and dNTP
        mg_total_mm = input_data.get("mg_total_mm")
        dntp_mm = input_data.get("dntp_mm")

        if mg_total_mm is None:
            # Use default buffer conditions
            mg_total_mm = 1.5  # Default [Mg²+] = 1.5 mM
            dntp_mm = dntp_mm if dntp_mm is not None else 0.2  # Default dNTP = 0.2 mM
            logger.info(
                "Using default Mg²+ conditions: total=%.2f mM, dNTP=%.2f mM",
                mg_total_mm, dntp_mm,
            )
        elif dntp_mm is None:
            dntp_mm = 0.2  # Default dNTP

        # Free Mg²+ = total - dNTP (1:1 chelation stoichiometry)
        return mg_total_mm - dntp_mm

    def _validate_mg_range(self, mg_total_mm: float) -> str:
        """
        Validate that total Mg²+ is within the model's reliable range.

        Args:
            mg_total_mm: Total Mg²+ concentration in mM.

        Returns:
            Error message string if invalid, empty string if valid.
        """
        if mg_total_mm < MG_MIN_MM:
            return (
                f"Total [Mg²+] = {mg_total_mm} mM is below the minimum "
                f"reliable range ({MG_MIN_MM} mM). "
                "The von Ahsen 2001 model is not validated for this concentration."
            )
        if mg_total_mm > MG_MAX_MM:
            return (
                f"Total [Mg²+] = {mg_total_mm} mM exceeds the maximum "
                f"reliable range ({MG_MAX_MM} mM). "
                "The von Ahsen 2001 model is not validated for this concentration."
            )
        return ""

    def _apply_correction(
        self, candidates: List[Dict[str, Any]], free_mg_mm: float
    ) -> List[Dict[str, Any]]:
        """
        Apply the von Ahsen 2001 Mg²+ Tm correction to all candidates.

        Formula: Tm(Mg²+) = Tm(salt) + 7.21·ln([Mg²+_free_in_molar])

        Args:
            candidates: List of primer candidate dictionaries.
            free_mg_mm: Free Mg²+ concentration in mM.

        Returns:
            Updated list of candidates with tm_mg_adjusted and delta_tm_penalty.
        """
        # Pre-compute the correction offset (same for all primers)
        mg_offset = VON_AHSEN_COEFFICIENT * math.log(free_mg_mm)

        for candidate in candidates:
            tm_salt = _candidate_tm(candidate)

            # Apply von Ahsen correction
            tm_mg = tm_salt + mg_offset

            # Round to 2 decimal places
            candidate["tm_salt_adjusted"] = round(float(tm_salt), 2)
            candidate["tm_mg_adjusted"] = round(tm_mg, 2)

            # Compute delta_tm_penalty: penalty for Tm shift > 1.5°C
            # (useful for pair-level penalty aggregation in later steps)
            candidate["delta_tm_penalty"] = round(abs(mg_offset), 2)

        return candidates


def execute(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Module-level execute function that instantiates MgCorrectionStep
    and runs the step.

    This is the entry point used by the pipeline orchestrator.
    """
    step = MgCorrectionStep()
    return step.execute(input_data)


def _candidate_tm(candidate: Dict[str, Any]) -> float:
    value = (
        candidate.get("tm_salt_adjusted")
        or candidate.get("tm_nn")
        or candidate.get("tm")
        or candidate.get("tm_basic")
    )
    if value is None:
        raise ValueError(f"Primer candidate {candidate.get('id', 'unknown')} has no Tm for Mg correction")
    return float(value)


def _primer_candidates_from_pairs(input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten upstream primer pairs so Mg correction runs on real primers."""
    for key in ("refined_pairs", "candidate_pairs", "filtered_pairs", "aligned_pairs"):
        pairs = input_data.get(key)
        if not pairs:
            continue
        candidates: List[Dict[str, Any]] = []
        for idx, pair in enumerate(pairs, start=1):
            pair_id = pair.get("pair_id") or pair.get("rank") or pair.get("pair_index") or idx
            for direction in ("forward", "reverse"):
                primer = pair.get(direction, {})
                if isinstance(primer, str):
                    primer = {"sequence": primer, "tm": pair.get(f"{direction}_tm")}
                sequence = primer.get("sequence", "")
                if not sequence:
                    continue
                candidates.append({
                    **primer,
                    "id": f"{pair_id}_{direction}",
                    "pair_id": pair_id,
                    "direction": direction,
                    "sequence": sequence,
                })
        return candidates
    return []

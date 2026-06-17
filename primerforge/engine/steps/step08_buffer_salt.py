"""
Step 8: Dynamic Buffer & Salt Adjustments
==========================================
Recalculates Tm using custom buffer conditions (monovalent, divalent,
dNTP, oligo concentrations). Computes free [Mg²+] after dNTP chelation
and applies the corrected Tm to all primer candidates.

References:
- Owczarzy R et al. (2004) Biochemistry 43:3537-3554 (salt correction)
- von Ahsen N et al. (2001) Clin Chem 47:1956-1961 (Mg²+ correction)
"""

import logging
from typing import Any, Dict, List, Tuple

from .base import PipelineStep

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# DEFAULT BUFFER CONDITIONS
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_BUFFER = {
    "monovalent_mm": 50.0,   # [Na+] in mM
    "divalent_mm": 1.5,      # [Mg²+] total in mM
    "dntp_mm": 0.2,          # [dNTP] in mM
    "oligo_conc_nm": 250.0,  # Oligonucleotide concentration in nM
}

# ═══════════════════════════════════════════════════════════════════════════
# VALIDATION RANGES
# ═══════════════════════════════════════════════════════════════════════════

VALID_RANGES = {
    "monovalent_mm": (10.0, 1000.0),
    "dntp_mm": (0.05, 1.0),
    "oligo_conc_nm": (50.0, 1000.0),
}


# ═══════════════════════════════════════════════════════════════════════════
# BUFFER SALT STEP CLASS
# ═══════════════════════════════════════════════════════════════════════════

class BufferSaltStep(PipelineStep):
    """
    Recalculates Tm using custom buffer conditions.

    Adjusts thermodynamic calculations based on user-provided or default
    buffer composition (monovalent cations, Mg²+, dNTP, oligo concentration).
    Computes free Mg²+ after accounting for dNTP chelation.
    """

    def __init__(self):
        super().__init__(name="buffer_salt_adjustment", step_number=8)

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recalculate Tm with custom or default buffer conditions.

        Input keys:
            primer_candidates (list): List of primer candidate dicts with 'sequence' key.
            buffer_conditions (optional dict): Custom buffer with keys:
                monovalent_mm, divalent_mm, dntp_mm, oligo_conc_nm

        Output keys:
            primer_candidates (list): Updated with tm_salt_adjusted field.
            buffer_conditions_used (dict): The buffer conditions applied.
            free_mg_mm (float): Free [Mg²+] after dNTP chelation (mM).
        """
        from ..thermodynamics import calculate_tm, BufferConditions

        primer_candidates = input_data.get("primer_candidates", [])
        if not primer_candidates:
            primer_candidates = _primer_candidates_from_pairs(input_data)
        buffer_input = input_data.get("buffer_conditions", None)

        # Resolve buffer conditions: use provided or fall back to defaults
        if buffer_input:
            conditions = {
                "monovalent_mm": buffer_input.get("monovalent_mm", DEFAULT_BUFFER["monovalent_mm"]),
                "divalent_mm": buffer_input.get("divalent_mm", DEFAULT_BUFFER["divalent_mm"]),
                "dntp_mm": buffer_input.get("dntp_mm", DEFAULT_BUFFER["dntp_mm"]),
                "oligo_conc_nm": buffer_input.get("oligo_conc_nm", DEFAULT_BUFFER["oligo_conc_nm"]),
            }
        else:
            conditions = dict(DEFAULT_BUFFER)

        # Validate buffer conditions
        is_valid, error_msg = self._validate_buffer(conditions)
        if not is_valid:
            raise ValueError(f"Buffer validation failed: {error_msg}")

        # Compute free [Mg²+]
        free_mg_mm = self._compute_free_mg(conditions["divalent_mm"], conditions["dntp_mm"])

        # Build BufferConditions for the thermodynamics engine
        buffer = BufferConditions(
            monovalent_mm=conditions["monovalent_mm"],
            divalent_mm=conditions["divalent_mm"],
            dntp_mm=conditions["dntp_mm"],
            oligo_conc_nm=conditions["oligo_conc_nm"],
        )

        # Recalculate Tm for each primer candidate
        updated_candidates = []
        for candidate in primer_candidates:
            updated = dict(candidate)
            seq = candidate.get("sequence", "")

            if not seq or len(seq) < 8:
                logger.warning(
                    f"Skipping primer '{candidate.get('id', 'unknown')}': "
                    f"sequence too short ({len(seq)} nt)"
                )
                updated["tm_salt_adjusted"] = None
                updated["buffer_salt_error"] = "Sequence too short for Tm calculation"
                updated_candidates.append(updated)
                continue

            try:
                thermo = calculate_tm(seq, buffer)
                updated["tm_salt_adjusted"] = thermo.tm_salt_adjusted
                updated["delta_h"] = thermo.delta_h
                updated["delta_s"] = thermo.delta_s
                updated["delta_g_37"] = thermo.delta_g_37
            except Exception as e:
                logger.warning(
                    f"Tm recalculation failed for primer "
                    f"'{candidate.get('id', 'unknown')}': {e}"
                )
                updated["tm_salt_adjusted"] = None
                updated["buffer_salt_error"] = str(e)

            updated_candidates.append(updated)

        logger.info(
            f"Step 8 complete: {len(updated_candidates)} primers recalculated "
            f"with buffer [Na+]={conditions['monovalent_mm']}mM, "
            f"[Mg²+]={conditions['divalent_mm']}mM, "
            f"[dNTP]={conditions['dntp_mm']}mM, "
            f"[oligo]={conditions['oligo_conc_nm']}nM, "
            f"free [Mg²+]={free_mg_mm:.3f}mM"
        )

        return {
            "primer_candidates": updated_candidates,
            "buffer_conditions_used": conditions,
            "free_mg_mm": round(free_mg_mm, 4),
        }

    def _validate_buffer(self, conditions: Dict[str, float]) -> Tuple[bool, str]:
        """
        Validate buffer conditions are within acceptable ranges.

        Ranges:
            monovalent_mm: [10, 1000] mM
            dntp_mm: [0.05, 1.0] mM
            oligo_conc_nm: [50, 1000] nM

        Args:
            conditions: Dict with buffer condition values.

        Returns:
            (is_valid, error_message) — error_message is empty if valid.
        """
        for key, (low, high) in VALID_RANGES.items():
            value = conditions.get(key)
            if value is None:
                return False, f"Missing required buffer parameter: {key}"
            if value < low or value > high:
                return False, (
                    f"{key} = {value} is outside the acceptable range "
                    f"[{low}, {high}]"
                )
        return True, ""

    def _compute_free_mg(self, mg_total_mm: float, dntp_mm: float) -> float:
        """
        Compute free [Mg²+] after dNTP chelation.

        dNTPs chelate Mg²+ at 1:1 stoichiometry, so:
            free_mg = max(0, total_mg - dNTP)

        Args:
            mg_total_mm: Total [Mg²+] in mM.
            dntp_mm: [dNTP] in mM.

        Returns:
            Free [Mg²+] in mM.
        """
        return max(0.0, mg_total_mm - dntp_mm)


# ═══════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL EXECUTE FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

_step_instance = BufferSaltStep()


def _primer_candidates_from_pairs(input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten upstream primer pairs so buffer correction runs on real primers."""
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
                    primer = {"sequence": primer}
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


def execute(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Module-level entry point for Step 8: Dynamic Buffer & Salt Adjustments.

    Recalculates Tm for all primer candidates using custom or default
    buffer conditions. Computes free [Mg²+] after dNTP chelation.

    Args:
        input_data: Pipeline data dict with keys:
            - primer_candidates (list): Primer candidate dicts.
            - buffer_conditions (optional dict): Custom buffer composition.

    Returns:
        Dict with keys:
            - primer_candidates: Updated with tm_salt_adjusted.
            - buffer_conditions_used: Buffer conditions applied.
            - free_mg_mm: Free [Mg²+] in mM.
    """
    return _step_instance.execute(input_data)

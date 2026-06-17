"""
Step 22: Probe Design (qPCR/TaqMan)
=====================================
Designs dual-labeled TaqMan hydrolysis probes between primer pairs.

Validates: Requirements 22.1, 22.2, 22.3, 22.4, 22.5, 22.6, 22.7
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from primerforge.engine.steps.base import PipelineStep
from primerforge.engine.thermodynamics import (
    BufferConditions,
    calculate_tm,
    predict_hairpin,
)

logger = logging.getLogger(__name__)


class ProbeDesignStep(PipelineStep):
    """
    Designs dual-labeled TaqMan probes positioned between primer pairs.

    For each ranked primer pair, finds candidate probes in the inter-primer
    region, validates thermodynamic and structural constraints, assigns
    reporter/quencher labels, and returns the top 3 candidates.
    """

    def __init__(self):
        super().__init__(name="probe_design", step_number=22)

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Design TaqMan probes for each ranked primer pair.

        Input keys:
            ranked_pairs: list of primer pair dicts
            amplicon_sequences: list of amplicon sequences (parallel to ranked_pairs)
            primer_tms: dict mapping pair_id -> {"fwd_tm": float, "rev_tm": float}
            buffer_conditions: dict with monovalent_mm, divalent_mm, dntp_mm, oligo_conc_nm
            probe_mode: bool indicating whether probe design is requested

        Output keys:
            probe_results: list of dicts per pair with:
                - pair_index: int
                - status: "probe_designed" | "probe_incompatible"
                - probes: list of top 3 probe candidate dicts (empty if incompatible)
                - reason: str (only if incompatible)
        """
        probe_mode = input_data.get("probe_mode", False)
        if not probe_mode:
            return {"probe_results": [], "probe_note": "Probe design skipped (probe_mode=False)"}

        ranked_pairs = input_data.get("ranked_pairs", [])
        amplicon_sequences = input_data.get("amplicon_sequences", [])
        primer_tms = input_data.get("primer_tms", {})
        buffer_cond = input_data.get("buffer_conditions", {})

        buffer = BufferConditions(
            monovalent_mm=buffer_cond.get("monovalent_mm", 50.0),
            divalent_mm=buffer_cond.get("divalent_mm", 1.5),
            dntp_mm=buffer_cond.get("dntp_mm", 0.2),
            oligo_conc_nm=buffer_cond.get("oligo_conc_nm", 250.0),
        )

        probe_results: List[Dict[str, Any]] = []

        for i, pair in enumerate(ranked_pairs):
            # Get amplicon sequence for this pair
            if i < len(amplicon_sequences):
                amplicon = amplicon_sequences[i]
            else:
                amplicon = pair.get("amplicon_sequence", "")

            if not amplicon:
                probe_results.append({
                    "pair_index": i,
                    "status": "probe_incompatible",
                    "probes": [],
                    "reason": "No amplicon sequence available",
                })
                continue

            # Get primer Tm values
            pair_id = pair.get("pair_id", str(i))
            tm_info = primer_tms.get(pair_id, {})
            fwd_tm = tm_info.get("fwd_tm") or _primer_tm(pair.get("forward"), pair.get("forward_tm"))
            rev_tm = tm_info.get("rev_tm") or _primer_tm(pair.get("reverse"), pair.get("reverse_tm"))

            if fwd_tm == 0 or rev_tm == 0:
                # Try to get Tm from nested fields
                fwd_tm = fwd_tm or pair.get("fwd_tm", 60.0)
                rev_tm = rev_tm or pair.get("rev_tm", 60.0)

            mean_primer_tm = (fwd_tm + rev_tm) / 2.0

            # Determine probe region boundaries
            fwd_end = self._get_fwd_end(pair, amplicon)
            rev_start = self._get_rev_start(pair, amplicon)

            # Find probe region (between primers with ≥1nt gap)
            probe_region = self._find_probe_region(fwd_end, rev_start, amplicon)

            if not probe_region:
                probe_results.append({
                    "pair_index": i,
                    "status": "probe_incompatible",
                    "probes": [],
                    "reason": "Insufficient space between primers for probe placement",
                })
                continue

            # Generate and validate candidate probes
            candidates = self._generate_candidates(
                probe_region, fwd_end, mean_primer_tm, buffer
            )

            if not candidates:
                probe_results.append({
                    "pair_index": i,
                    "status": "probe_incompatible",
                    "probes": [],
                    "reason": "No valid probe found meeting all constraints (Tm, GC, length, 5'G, hairpin)",
                })
                continue

            # Return top 3
            top_probes = candidates[:3]
            probe_results.append({
                "pair_index": i,
                "status": "probe_designed",
                "probes": top_probes,
                "reason": None,
            })

        return {
            "probe_results": probe_results,
            "probe_note": f"Probe design completed for {len(ranked_pairs)} pairs",
        }

    def _get_fwd_end(self, pair: Dict[str, Any], amplicon: str) -> int:
        """Get the end position of the forward primer in the amplicon."""
        fwd = _primer_dict(pair.get("forward"))
        fwd_seq = fwd.get("sequence", "")
        if fwd_seq:
            # Forward primer binds at the start of the amplicon
            return len(fwd_seq) - 1
        # Fallback: use primer length or default
        fwd_len = fwd.get("length", pair.get("fwd_length", 20))
        return fwd_len - 1

    def _get_rev_start(self, pair: Dict[str, Any], amplicon: str) -> int:
        """Get the start position of the reverse primer in the amplicon."""
        rev = _primer_dict(pair.get("reverse"))
        rev_seq = rev.get("sequence", "")
        if rev_seq:
            # Reverse primer binds at the end of the amplicon (its complement)
            return len(amplicon) - len(rev_seq)
        # Fallback: use primer length or default
        rev_len = rev.get("length", pair.get("rev_length", 20))
        return len(amplicon) - rev_len

    def _find_probe_region(self, fwd_end: int, rev_start: int, amplicon: str) -> str:
        """
        Extract the probe region between forward and reverse primers.

        The probe must be placed with at least 1 nucleotide gap from each primer:
        - Start at fwd_end + 1 (≥1nt gap from forward primer 3' end)
        - End at rev_start - 1 (≥1nt gap from reverse primer 5' end)

        Returns:
            The probe region sequence, or empty string if region too short.
        """
        # Probe region starts after a 1nt gap from fwd primer end
        probe_start = fwd_end + 1 + 1  # +1 for 0-index end, +1 for gap
        # Probe region ends before a 1nt gap from rev primer start
        probe_end = rev_start - 1  # -1 for gap

        if probe_start >= probe_end:
            return ""

        region = amplicon[probe_start:probe_end]

        # Minimum length check: need at least 18nt for a valid probe
        if len(region) < 18:
            return ""

        return region

    def _validate_probe(
        self, probe_seq: str, primer_mean_tm: float, buffer: BufferConditions
    ) -> Tuple[bool, str]:
        """
        Validate a candidate probe against all constraints.

        Constraints:
            - No G at 5' position (quenches reporter fluorescence)
            - Length: [18, 30] nucleotides
            - GC content: [30%, 80%]
            - Tm: mean_primer_Tm + [8, 10]°C
            - Hairpin ΔG ≥ -2.0 kcal/mol

        Returns:
            (is_valid, rejection_reason)
        """
        seq = probe_seq.upper()

        # Check 5' G
        if seq[0] == "G":
            return False, "5' position is G (quenches reporter fluorescence)"

        # Check length
        length = len(seq)
        if length < 18 or length > 30:
            return False, f"Length {length} outside range [18, 30]"

        # Check GC content
        gc_count = seq.count("G") + seq.count("C")
        gc_percent = (gc_count / length) * 100.0
        if gc_percent < 30.0 or gc_percent > 80.0:
            return False, f"GC content {gc_percent:.1f}% outside range [30%, 80%]"

        # Check Tm
        try:
            thermo = calculate_tm(seq, buffer)
            probe_tm = thermo.tm_salt_adjusted
        except ValueError:
            return False, "Unable to calculate probe Tm"

        target_tm_low = primer_mean_tm + 8.0
        target_tm_high = primer_mean_tm + 10.0
        if probe_tm < target_tm_low or probe_tm > target_tm_high:
            return False, (
                f"Probe Tm {probe_tm:.1f}°C outside target range "
                f"[{target_tm_low:.1f}, {target_tm_high:.1f}]°C "
                f"(mean primer Tm + [8,10]°C)"
            )

        # Check hairpin ΔG
        hairpin = predict_hairpin(seq, buffer)
        if hairpin.delta_g < -2.0:
            return False, (
                f"Hairpin ΔG {hairpin.delta_g:.2f} kcal/mol < -2.0 kcal/mol "
                f"(stable secondary structure)"
            )

        return True, ""

    def _assign_labels(self, probe_len: int) -> Dict[str, str]:
        """
        Assign reporter and quencher labels based on probe length.

        - 5' reporter: FAM (default)
        - 3' quencher: BHQ-1 for probes ≤25nt, TAMRA for probes >25nt

        Returns:
            Dict with "reporter_5prime" and "quencher_3prime" keys.
        """
        reporter = "FAM"
        quencher = "BHQ-1" if probe_len <= 25 else "TAMRA"
        return {
            "reporter_5prime": reporter,
            "quencher_3prime": quencher,
        }

    def _generate_candidates(
        self,
        probe_region: str,
        fwd_end: int,
        mean_primer_tm: float,
        buffer: BufferConditions,
    ) -> List[Dict[str, Any]]:
        """
        Generate and score all valid probe candidates from the probe region.

        Scans all subsequences of length [18, 30] within the probe region,
        validates each, and returns sorted candidates (best first).
        """
        region = probe_region.upper()
        region_len = len(region)
        candidates: List[Dict[str, Any]] = []

        # The probe region starts at fwd_end + 2 in the amplicon
        # (fwd_end + 1 for 0-index adjustment, +1 for gap)
        region_start_in_amplicon = fwd_end + 2

        for length in range(18, min(31, region_len + 1)):
            for start in range(0, region_len - length + 1):
                probe_seq = region[start : start + length]

                is_valid, reason = self._validate_probe(probe_seq, mean_primer_tm, buffer)
                if not is_valid:
                    continue

                # Compute probe properties
                thermo = calculate_tm(probe_seq, buffer)
                gc_count = probe_seq.count("G") + probe_seq.count("C")
                gc_percent = (gc_count / length) * 100.0
                labels = self._assign_labels(length)
                hairpin = predict_hairpin(probe_seq, buffer)

                # Compute score (lower = better)
                # Prefer Tm closer to mean_primer_tm + 9 (middle of [8, 10] range)
                target_tm = mean_primer_tm + 9.0
                tm_deviation = abs(thermo.tm_salt_adjusted - target_tm)
                # Prefer GC near 50%
                gc_deviation = abs(gc_percent - 50.0)
                # Prefer shorter probes (better quenching efficiency)
                length_score = (length - 18) * 0.5
                # Penalize hairpin stability
                hairpin_score = max(0, -(hairpin.delta_g + 2.0)) * 2.0

                score = tm_deviation + gc_deviation * 0.1 + length_score + hairpin_score

                candidate = {
                    "sequence": probe_seq,
                    "length": length,
                    "tm": round(thermo.tm_salt_adjusted, 2),
                    "gc_percent": round(gc_percent, 1),
                    "hairpin_dg": round(hairpin.delta_g, 2),
                    "reporter_5prime": labels["reporter_5prime"],
                    "quencher_3prime": labels["quencher_3prime"],
                    "position_start": region_start_in_amplicon + start,
                    "position_end": region_start_in_amplicon + start + length - 1,
                    "score": round(score, 3),
                }
                candidates.append(candidate)

        # Sort by score (best first)
        candidates.sort(key=lambda c: c["score"])
        return candidates


# ═══════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL EXECUTE FUNCTION
# ═══════════════════════════════════════════════════════════════════════════


def execute(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Module-level entry point for the probe design step.

    This function is called by the pipeline orchestrator.

    Args:
        input_data: Pipeline context dictionary.

    Returns:
        Dict with probe_results and probe_note.
    """
    step = ProbeDesignStep()
    return step.execute(input_data)


def _primer_tm(primer: Any, fallback: Any = 0) -> float:
    """Return primer Tm from dict or legacy string-shaped pair data."""
    if isinstance(primer, dict):
        value = primer.get("tm") or primer.get("tm_nn") or primer.get("tm_salt_adjusted") or fallback
    else:
        value = fallback
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _primer_dict(primer: Any) -> Dict[str, Any]:
    if isinstance(primer, dict):
        return primer
    if isinstance(primer, str):
        return {"sequence": primer, "length": len(primer)}
    return {}

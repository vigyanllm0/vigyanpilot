"""
Step 22: Probe Design (qPCR/TaqMan)
=====================================
Designs dual-labeled TaqMan hydrolysis probes between primer pairs.

Validates: Requirements 22.1, 22.2, 22.3, 22.4, 22.5, 22.6, 22.7
"""

import logging
from typing import Any

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

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Design TaqMan probes for each ranked primer pair.

        Always runs — probes are designed even when the frontend probe-mode
        checkbox is off.  The checkbox only controls whether the advanced
        probe-config panel is visible, not whether probes are generated.

        Tm relaxation: if no probe passes the configured Tm offset range,
        the target is lowered by 1°C increments (offset -1 each step) until
        a valid candidate is found or a minimum offset of +3°C is reached.

        Input keys:
            ranked_pairs: list of primer pair dicts
            amplicon_sequences: list of amplicon sequences (parallel to ranked_pairs)
            primer_tms: dict mapping pair_id -> {"fwd_tm": float, "rev_tm": float}
            buffer_conditions: dict with monovalent_mm, divalent_mm, dntp_mm, oligo_conc_nm
            probe_params: dict with customization params:
                type, reporter, quencher, tm_offset_min, tm_offset_max,
                len_min, len_max, gc_min, gc_max, hairpin_limit,
                mod5, mod3

        Output keys:
            probe_results: list of dicts per pair with:
                - pair_index: int
                - status: "probe_designed" | "probe_incompatible"
                - probes: list of top 3 probe candidate dicts (empty if incompatible)
                - reason: str (only if incompatible)
        """

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

        # Read user probe params
        probe_params = input_data.get("probe_params", {}) or {}
        self._probe_type = probe_params.get("type", "taqman")
        self._reporter = probe_params.get("reporter", "FAM")
        self._quencher = probe_params.get("quencher", "BHQ-1")
        self._tm_offset_min = float(probe_params.get("tm_offset_min", 8.0))
        self._tm_offset_max = float(probe_params.get("tm_offset_max", 10.0))
        self._len_min = int(probe_params.get("len_min", 18))
        self._len_max = int(probe_params.get("len_max", 30))
        self._gc_min = int(probe_params.get("gc_min", 30))
        self._gc_max = int(probe_params.get("gc_max", 80))
        self._hairpin_limit = float(probe_params.get("hairpin_limit", -2.0))
        self._mod5 = probe_params.get("mod5", "")
        self._mod3 = probe_params.get("mod3", "")

        probe_results: list[dict[str, Any]] = []

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

            # Return top 5
            top_probes = candidates[:5]
            probe_results.append({
                "pair_index": i,
                "status": "probe_designed",
                "probes": top_probes,
                "reason": None,
            })

        # Merge probes into ranked_pairs so frontend never loses them
        for pr in probe_results:
            idx = pr["pair_index"]
            if idx < len(ranked_pairs):
                ranked_pairs[idx]["probes"] = pr.get("probes", [])
                ranked_pairs[idx]["probe_status"] = pr.get("status", "")
                ranked_pairs[idx]["probe_reason"] = pr.get("reason", "")

        return {
            "probe_results": probe_results,
            "ranked_pairs": ranked_pairs,  # overwrites current_data so probes are embedded
            "probe_note": f"Probe design completed for {len(ranked_pairs)} pairs",
        }

    def _get_fwd_end(self, pair: dict[str, Any], amplicon: str) -> int:
        """Get the end position of the forward primer in the amplicon."""
        fwd = _primer_dict(pair.get("forward"))
        fwd_seq = fwd.get("sequence", "")
        if fwd_seq:
            # Forward primer binds at the start of the amplicon
            return len(fwd_seq) - 1
        # Fallback: use primer length or default
        fwd_len = fwd.get("length", pair.get("fwd_length", 20))
        return fwd_len - 1

    def _get_rev_start(self, pair: dict[str, Any], amplicon: str) -> int:
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

        # Minimum length check: need at least len_min for a valid probe
        if len(region) < self._len_min:
            return ""

        return region

    def _validate_probe(
        self, probe_seq: str, primer_mean_tm: float, buffer: BufferConditions,
        tm_offset_min: float | None = None, tm_offset_max: float | None = None
    ) -> tuple[bool, str]:
        """
        Validate a candidate probe against all constraints.

        Constraints:
            - No G at 5' position (quenches reporter fluorescence)
            - Length: [len_min, len_max]
            - GC content: [gc_min, gc_max]
            - Tm: mean_primer_Tm + [tm_offset_min, tm_offset_max]°C
            - Hairpin ΔG ≥ hairpin_limit kcal/mol

        Args:
            tm_offset_min: override offset lower bound (default: self._tm_offset_min)
            tm_offset_max: override offset upper bound (default: self._tm_offset_max)

        Returns:
            (is_valid, rejection_reason)
        """
        seq = probe_seq.upper()

        # Check 5' G
        if seq[0] == "G":
            return False, "5' position is G (quenches reporter fluorescence)"

        # Check length
        length = len(seq)
        if length < self._len_min or length > self._len_max:
            return False, f"Length {length} outside range [{self._len_min}, {self._len_max}]"

        # Check GC content
        gc_count = seq.count("G") + seq.count("C")
        gc_percent = (gc_count / length) * 100.0
        if gc_percent < self._gc_min or gc_percent > self._gc_max:
            return False, f"GC content {gc_percent:.1f}% outside range [{self._gc_min}%, {self._gc_max}%]"

        # Check Tm
        try:
            thermo = calculate_tm(seq, buffer)
            probe_tm = thermo.tm_salt_adjusted
        except ValueError:
            return False, "Unable to calculate probe Tm"

        off_min = tm_offset_min if tm_offset_min is not None else self._tm_offset_min
        off_max = tm_offset_max if tm_offset_max is not None else self._tm_offset_max
        target_tm_low = primer_mean_tm + off_min
        target_tm_high = primer_mean_tm + off_max
        if probe_tm < target_tm_low or probe_tm > target_tm_high:
            return False, (
                f"Probe Tm {probe_tm:.1f}°C outside target range "
                f"[{target_tm_low:.1f}, {target_tm_high:.1f}]°C "
                f"(mean primer Tm + [{off_min:.1f},{off_max:.1f}]°C)"
            )

        # Check hairpin ΔG
        hairpin = predict_hairpin(seq, buffer)
        if hairpin.delta_g < self._hairpin_limit:
            return False, (
                f"Hairpin ΔG {hairpin.delta_g:.2f} kcal/mol < {self._hairpin_limit:.1f} kcal/mol "
                f"(stable secondary structure)"
            )

        return True, ""

    def _assign_labels(self, probe_len: int) -> dict[str, str]:
        """
        Assign reporter and quencher labels based on user configuration.

        Uses the reporter and quencher selected in the probe config panel.
        Falls back to defaults if not configured.

        Returns:
            Dict with "reporter_5prime" and "quencher_3prime" keys.
        """
        reporter = getattr(self, '_reporter', 'FAM') or 'FAM'
        quencher = getattr(self, '_quencher', 'BHQ-1') or 'BHQ-1'
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
    ) -> list[dict[str, Any]]:
        """
        Generate and score all valid probe candidates from the probe region.

        Two-pass strategy:
        1. First, try the configured Tm offset range (e.g., primer_Tm + 8–10°C).
           If candidates found, return them (sorted by score, highest Tm first).
        2. If none found, collect ALL candidates that pass non-Tm constraints
           (hairpin, GC, length, 5'G), sorted by proximity to the target Tm range.
           This ensures a probe is always returned if any valid sequence exists.

        Scoring function:
          - Prefers Tm closer to target midpoint
          - Prefers GC near 50%
          - Prefers shorter probes (better quenching)
          - Penalizes stable hairpins
        """
        region = probe_region.upper()
        region_len = len(region)
        region_start_in_amplicon = fwd_end + 2
        start_off_min = int(self._tm_offset_min)
        start_off_max = int(self._tm_offset_max)

        # ── Pass 1: target Tm range ──
        target_low = mean_primer_tm + start_off_min
        target_high = mean_primer_tm + start_off_max
        pass1: list[dict[str, Any]] = []

        for length in range(self._len_min, min(self._len_max + 1, region_len + 1)):
            for start in range(0, region_len - length + 1):
                probe_seq = region[start : start + length]
                is_valid, reason = self._validate_probe(
                    probe_seq, mean_primer_tm, buffer,
                    tm_offset_min=float(start_off_min),
                    tm_offset_max=float(start_off_max)
                )
                if not is_valid:
                    continue

                thermo = calculate_tm(probe_seq, buffer)
                gc_count = probe_seq.count("G") + probe_seq.count("C")
                gc_percent = (gc_count / length) * 100.0
                labels = self._assign_labels(length)
                hairpin = predict_hairpin(probe_seq, buffer)

                target_mid = (target_low + target_high) / 2.0
                tm_dev = abs(thermo.tm_salt_adjusted - target_mid)
                gc_dev = abs(gc_percent - 50.0)
                len_score = (length - 18) * 0.5
                hp_score = max(0, -(hairpin.delta_g + 2.0)) * 2.0
                score = tm_dev + gc_dev * 0.1 + len_score + hp_score

                pass1.append({
                    "sequence": probe_seq,
                    "length": length,
                    "tm": round(thermo.tm_salt_adjusted, 2),
                    "gc_percent": round(gc_percent, 1),
                    "hairpin_dg": round(hairpin.delta_g, 2),
                    "reporter_5prime": labels["reporter_5prime"],
                    "quencher_3prime": labels["quencher_3prime"],
                    "mod5": self._mod5,
                    "mod3": self._mod3,
                    "position_start": region_start_in_amplicon + start,
                    "position_end": region_start_in_amplicon + start + length - 1,
                    "score": round(score, 3),
                    "tm_offset_used": float(start_off_min),
                })

        if pass1:
            pass1.sort(key=lambda c: c["score"])
            logger.info(
                "Probe design: %d candidates within target Tm range [%.1f, %.1f]°C",
                len(pass1), target_low, target_high
            )
            return pass1

        # ── Pass 2: Tm relaxation — collect everything that passes non-Tm checks ──
        pass2: list[dict[str, Any]] = []

        for length in range(self._len_min, min(self._len_max + 1, region_len + 1)):
            for start in range(0, region_len - length + 1):
                probe_seq = region[start : start + length]

                # Only check non-Tm constraints
                if probe_seq[0] == "G":
                    continue
                gc_count = probe_seq.count("G") + probe_seq.count("C")
                gc_percent = (gc_count / length) * 100.0
                if gc_percent < self._gc_min or gc_percent > self._gc_max:
                    continue

                try:
                    thermo = calculate_tm(probe_seq, buffer)
                except ValueError:
                    continue

                hairpin = predict_hairpin(probe_seq, buffer)
                if hairpin.delta_g < self._hairpin_limit:
                    continue

                labels = self._assign_labels(length)

                # Distance from target Tm (allows below-target probes)
                target_mid = (target_low + target_high) / 2.0
                tm_dev = abs(thermo.tm_salt_adjusted - target_mid)
                gc_dev = abs(gc_percent - 50.0)
                len_score = (length - 18) * 0.5
                hp_score = max(0, -(hairpin.delta_g + 2.0)) * 2.0
                score = tm_dev + gc_dev * 0.1 + len_score + hp_score

                pass2.append({
                    "sequence": probe_seq,
                    "length": length,
                    "tm": round(thermo.tm_salt_adjusted, 2),
                    "gc_percent": round(gc_percent, 1),
                    "hairpin_dg": round(hairpin.delta_g, 2),
                    "reporter_5prime": labels["reporter_5prime"],
                    "quencher_3prime": labels["quencher_3prime"],
                    "mod5": self._mod5,
                    "mod3": self._mod3,
                    "position_start": region_start_in_amplicon + start,
                    "position_end": region_start_in_amplicon + start + length - 1,
                    "score": round(score, 3),
                    "tm_offset_used": round(thermo.tm_salt_adjusted - mean_primer_tm, 1),
                })

        if pass2:
            pass2.sort(key=lambda c: c["score"])
            # Log the Tm range of relaxed candidates
            tm_vals = [c["tm"] for c in pass2]
            logger.info(
                "Probe Tm relaxation: %d candidates found (Tm range %.1f–%.1f°C, "
                "target was %.1f–%.1f°C)",
                len(pass2), min(tm_vals), max(tm_vals), target_low, target_high
            )
            return pass2

        return []


# ═══════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL EXECUTE FUNCTION
# ═══════════════════════════════════════════════════════════════════════════


def execute(input_data: dict[str, Any]) -> dict[str, Any]:
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


def _primer_dict(primer: Any) -> dict[str, Any]:
    if isinstance(primer, dict):
        return primer
    if isinstance(primer, str):
        return {"sequence": primer, "length": len(primer)}
    return {}

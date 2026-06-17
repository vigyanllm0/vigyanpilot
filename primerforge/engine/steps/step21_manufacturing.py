"""
Step 21: Manufacturing Feasibility Screening
==============================================
Screens primers for synthesis difficulty including homopolymer runs,
extreme GC windows, and G-quadruplex risk. Assigns a feasibility score
and recommends purification methods for flagged primers.
"""

import logging
import re
from typing import Any, Dict, List

from primerforge.engine.steps.base import PipelineStep

logger = logging.getLogger(__name__)

# Deduction values per flag type
FLAG_DEDUCTIONS = {
    "synthesis_difficult": 25,
    "synthesis_challenging": 20,
    "G-quadruplex_risk": 30,
}

# Ranking penalty applied when feasibility score < 50
SYNTHESIS_HIGH_RISK_PENALTY = 5.0


class ManufacturingFeasibilityStep(PipelineStep):
    """
    Step 21: Screens primers for synthesis feasibility issues.

    Checks for homopolymer runs, extreme GC content windows, and
    G-quadruplex forming sequences. Assigns a manufacturing feasibility
    score and recommends HPLC purification for flagged primers.
    """

    def __init__(self):
        super().__init__(name="Manufacturing Feasibility Screening", step_number=21)

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 21: Manufacturing feasibility screening.

        Input keys:
            ranked_pairs (list): Primer pairs from step 19 ranking.

        Output keys:
            manufacturing_results (list): Per-pair feasibility results.
            feasibility_scores (dict): Mapping of primer ID to feasibility score.
        """
        ranked_pairs = input_data.get("ranked_pairs", [])
        if not ranked_pairs:
            return {
                "manufacturing_results": [],
                "feasibility_scores": {},
            }

        manufacturing_results = []
        feasibility_scores = {}

        for pair in ranked_pairs:
            pair_result = {"pair_id": pair.get("pair_id", pair.get("rank", "unknown"))}

            for direction in ("forward", "reverse"):
                primer = pair.get(direction, {})
                seq = primer.get("sequence", "")
                if not seq:
                    continue

                primer_id = primer.get("id", f"{pair_result['pair_id']}_{direction}")
                flags = self._screen_primer(seq)

                # Compute feasibility score
                score = self._compute_feasibility_score(flags)
                feasibility_scores[primer_id] = score

                # Determine purification recommendation
                purification = "HPLC" if flags else "standard_desalt"

                # Apply ranking penalty if score < 50
                if score < 50:
                    flags.append("synthesis_high_risk")
                    # Apply penalty to the pair's total penalty
                    current_penalty = pair.get("total_penalty", 0.0)
                    pair["total_penalty"] = round(
                        current_penalty + SYNTHESIS_HIGH_RISK_PENALTY, 2
                    )

                pair_result[direction] = {
                    "primer_id": primer_id,
                    "sequence": seq,
                    "flags": flags,
                    "feasibility_score": score,
                    "purification_recommendation": purification,
                }

            manufacturing_results.append(pair_result)

        logger.info(
            "VigyanLLM: Manufacturing feasibility screening complete for %d pairs",
            len(ranked_pairs),
        )

        return {
            "manufacturing_results": manufacturing_results,
            "feasibility_scores": feasibility_scores,
        }

    def _screen_primer(self, seq: str) -> List[str]:
        """Run all synthesis feasibility checks on a primer sequence."""
        flags: List[str] = []

        if self._check_homopolymer(seq):
            flags.append("synthesis_difficult")
        if self._check_gc_window(seq):
            flags.append("synthesis_challenging")
        if self._check_g_quadruplex(seq):
            flags.append("G-quadruplex_risk")

        return flags

    def _check_homopolymer(self, seq: str) -> bool:
        """
        Flag if the sequence contains 5 or more consecutive identical bases.

        Requirement 21.1: Flag primers containing homopolymer runs of 5 or more
        identical consecutive nucleotides as "synthesis_difficult".
        """
        seq_upper = seq.upper()
        for base in "ACGT":
            if base * 5 in seq_upper:
                return True
        return False

    def _check_gc_window(self, seq: str, window: int = 10) -> bool:
        """
        Flag if GC content exceeds 80% or falls below 20% in any 10bp sliding window.

        Requirement 21.2: Flag primers with GC content >80% or <20% in any
        10bp sliding window as "synthesis_challenging".
        """
        seq_upper = seq.upper()
        if len(seq_upper) < window:
            # For sequences shorter than the window, check the entire sequence
            gc_count = sum(1 for b in seq_upper if b in "GC")
            gc_pct = gc_count / len(seq_upper) if seq_upper else 0
            return gc_pct > 0.80 or gc_pct < 0.20

        for i in range(len(seq_upper) - window + 1):
            window_seq = seq_upper[i : i + window]
            gc_count = sum(1 for b in window_seq if b in "GC")
            gc_pct = gc_count / window
            if gc_pct > 0.80 or gc_pct < 0.20:
                return True
        return False

    def _check_g_quadruplex(self, seq: str) -> bool:
        """
        Flag if the sequence contains more than 4 consecutive G nucleotides.

        Requirement 21.3: Flag primers containing more than 4 consecutive G
        nucleotides as "G-quadruplex_risk".
        """
        return "GGGGG" in seq.upper()

    def _compute_feasibility_score(self, flags: List[str]) -> int:
        """
        Compute manufacturing feasibility score (0-100).

        Requirement 21.5: Base score of 100, with fixed deductions per active flag:
        - synthesis_difficult: -25
        - synthesis_challenging: -20
        - G-quadruplex_risk: -30

        Score is clamped to minimum of 0.
        """
        score = 100
        for flag in flags:
            score -= FLAG_DEDUCTIONS.get(flag, 0)
        return max(0, score)


def execute(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Module-level execute function for Step 21: Manufacturing Feasibility Screening.

    This function is used by the pipeline orchestrator for step registration.
    """
    step = ManufacturingFeasibilityStep()
    return step.execute(input_data)

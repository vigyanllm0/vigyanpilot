"""
Step 17: 5' Overhang Adapter Tailing for NGS
==============================================
Prepends platform-appropriate 5' adapter overhang sequences to candidate primers
for direct compatibility with Illumina/Ion Torrent library preparation workflows.

Supports:
- Illumina Nextera (R1/R2)
- Illumina TruSeq (R1/R2)
- Ion Torrent (A/P1)
- Custom adapters (15-35nt, ACGT only)

Validates adapter-gene cross-dimer ΔG and recommends PAGE purification for
oligos exceeding 60nt total length.
"""

import logging
import math
import re
from typing import Any, Dict, List, Optional, Tuple

from .base import PipelineStep

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# ADAPTER TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════

ADAPTER_TEMPLATES: Dict[str, str] = {
    "illumina_nextera_r1": "TCGTCGGCAGCGTCAGATGTGTATAAGAGACAG",
    "illumina_nextera_r2": "GTCTCGTGGGCTCGGAGATGTGTATAAGAGACAG",
    "illumina_truseq_r1": "AGATCGGAAGAGCACACGTCTGAACTCCAGTCA",
    "illumina_truseq_r2": "AGATCGGAAGAGCGTCGTGTAGGGAAAGAGTGT",
    "ion_torrent_a": "CCATCTCATCCCTGCGTGTCTCCGACTCAG",
    "ion_torrent_p1": "CCTCTCTATGGGCAGTCGGTGAT",
}

# Mapping from platform name to (R1 adapter key, R2 adapter key)
PLATFORM_ADAPTER_MAP: Dict[str, Tuple[str, str]] = {
    "illumina_nextera": ("illumina_nextera_r1", "illumina_nextera_r2"),
    "illumina_truseq": ("illumina_truseq_r1", "illumina_truseq_r2"),
    "ion_torrent": ("ion_torrent_a", "ion_torrent_p1"),
}

# Thresholds
FOLDBACK_DG_THRESHOLD = -5.0  # kcal/mol — flag if cross-dimer ΔG below this
MAX_UNTAILED_LENGTH = 60  # nt — recommend PAGE purification above this
CUSTOM_ADAPTER_MIN_LEN = 15
CUSTOM_ADAPTER_MAX_LEN = 35
VALID_DNA_PATTERN = re.compile(r"^[ACGTacgt]+$")


# ═══════════════════════════════════════════════════════════════════════════
# ADAPTER TAILING PIPELINE STEP
# ═══════════════════════════════════════════════════════════════════════════


class AdapterTailingStep(PipelineStep):
    """Prepends 5' adapter overhangs for NGS library prep compatibility."""

    def __init__(self):
        super().__init__(name="adapter_tailing", step_number=17)

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Append 5' adapter overhangs to primer candidates.

        Input keys:
            primer_candidates (list): List of primer candidate dicts with
                'sequence', 'direction' ('forward'/'reverse'), and optionally 'tm_salt_adjusted'.
            adapter_platform (str): One of 'illumina_nextera', 'illumina_truseq', 'ion_torrent'.
            custom_adapter (str, optional): User-supplied adapter (15-35nt, ACGT only).

        Output keys:
            tailed_primers (list): Primers with adapter prepended and annotations.
            adapter_foldback_flags (list): List of primer IDs flagged for foldback risk.
            purification_recommendations (list): Primers requiring PAGE purification.
        """
        candidates = input_data.get("primer_candidates", [])
        if not candidates:
            candidates = _primer_candidates_from_pairs(input_data)
        platform = input_data.get("adapter_platform", "")
        custom_adapter = input_data.get("custom_adapter", None)

        if not candidates:
            return {
                "tailed_primers": [],
                "adapter_foldback_flags": [],
                "purification_recommendations": [],
                "adapter_note": "No primer candidates to tail",
            }

        # Resolve adapter sequences
        r1_adapter, r2_adapter = self._resolve_adapters(platform, custom_adapter)

        if r1_adapter is None:
            return {
                "tailed_primers": candidates,
                "adapter_foldback_flags": [],
                "purification_recommendations": [],
                "adapter_note": f"Unknown platform '{platform}' and no valid custom adapter — skipping tailing",
            }

        # Get annealing temperature from upstream step (default 60°C)
        annealing_temp = input_data.get("annealing_temp", 60.0)

        tailed_primers: List[Dict[str, Any]] = []
        foldback_flags: List[str] = []
        purification_recs: List[Dict[str, Any]] = []
        all_failed_foldback = True

        for primer in candidates:
            direction = primer.get("direction", "forward")
            gene_specific_seq = primer.get("sequence", "")

            # Select adapter based on direction
            adapter = r1_adapter if direction == "forward" else r2_adapter

            # Prepend adapter to 5' end
            tailed_seq = adapter + gene_specific_seq

            # Compute cross-dimer ΔG between adapter and gene-specific region
            cross_dimer_dg = self._compute_adapter_dimer_dg(
                adapter, gene_specific_seq, annealing_temp
            )

            # Recalculate effective Tm on gene-specific portion only
            effective_tm = self._compute_effective_tm(gene_specific_seq)

            # Check total length for PAGE purification
            total_length = len(tailed_seq)
            needs_page = total_length > MAX_UNTAILED_LENGTH

            # Build annotated tailed primer
            tailed_primer = dict(primer)  # Copy original data
            tailed_primer["tailed_sequence"] = tailed_seq
            tailed_primer["adapter_platform"] = platform or "custom"
            tailed_primer["adapter_sequence"] = adapter
            tailed_primer["gene_specific_sequence"] = gene_specific_seq
            tailed_primer["total_length"] = total_length
            tailed_primer["effective_tm"] = effective_tm
            tailed_primer["adapter_dimer_dg"] = round(cross_dimer_dg, 2)

            # Foldback risk check
            has_foldback_risk = cross_dimer_dg < FOLDBACK_DG_THRESHOLD
            tailed_primer["adapter_foldback_risk"] = has_foldback_risk

            if has_foldback_risk:
                primer_id = primer.get("id", primer.get("pair_id", f"primer_{len(tailed_primers)}"))
                foldback_flags.append(primer_id)
                tailed_primer.setdefault("flags", [])
                if isinstance(tailed_primer["flags"], list):
                    tailed_primer["flags"].append("adapter_foldback_risk")
                tailed_primer.setdefault("penalties", {})
                if isinstance(tailed_primer["penalties"], dict):
                    tailed_primer["penalties"]["adapter_foldback"] = 8.0
            else:
                all_failed_foldback = False

            # PAGE purification recommendation
            if needs_page:
                purification_recs.append({
                    "primer_id": primer.get("id", primer.get("pair_id", f"primer_{len(tailed_primers)}")),
                    "total_length": total_length,
                    "purification": "PAGE",
                    "reason": f"Total length {total_length}nt exceeds 60nt threshold",
                })
                tailed_primer["purification_recommendation"] = "PAGE"
            else:
                tailed_primer["purification_recommendation"] = "standard"

            tailed_primers.append(tailed_primer)

        # Soft-failure: if ALL candidates have foldback risk
        if all_failed_foldback and len(tailed_primers) > 0:
            logger.warning(
                "All %d candidates failed adapter foldback filter — "
                "passing unfiltered set with penalty annotations",
                len(tailed_primers),
            )
            return {
                "tailed_primers": tailed_primers,
                "adapter_foldback_flags": foldback_flags,
                "purification_recommendations": purification_recs,
                "adapter_note": (
                    "SOFT-FAILURE: All candidates failed adapter cross-dimer check "
                    f"(ΔG < {FOLDBACK_DG_THRESHOLD} kcal/mol). "
                    "Passing unfiltered set with penalty annotations."
                ),
                "adapter_soft_failure": True,
            }

        return {
            "tailed_primers": tailed_primers,
            "adapter_foldback_flags": foldback_flags,
            "purification_recommendations": purification_recs,
            "adapter_note": (
                f"Tailed {len(tailed_primers)} primers with {platform or 'custom'} adapters. "
                f"{len(foldback_flags)} flagged for foldback risk, "
                f"{len(purification_recs)} recommended PAGE purification."
            ),
        }

    def _resolve_adapters(
        self, platform: str, custom_adapter: Optional[str]
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Resolve adapter sequences from platform or custom input.

        Returns (r1_adapter, r2_adapter) tuple, or (None, None) if invalid.
        """
        # Try custom adapter first if provided
        if custom_adapter:
            valid, msg = self._validate_custom_adapter(custom_adapter)
            if valid:
                # Custom adapter used for both directions
                return custom_adapter.upper(), custom_adapter.upper()
            else:
                logger.warning("Invalid custom adapter: %s — falling back to platform", msg)

        # Try platform templates
        platform_key = platform.lower().strip() if platform else ""
        if platform_key in PLATFORM_ADAPTER_MAP:
            r1_key, r2_key = PLATFORM_ADAPTER_MAP[platform_key]
            return ADAPTER_TEMPLATES[r1_key], ADAPTER_TEMPLATES[r2_key]

        return None, None

    def _validate_custom_adapter(self, adapter: str) -> Tuple[bool, str]:
        """
        Validate custom adapter: 15-35nt, ACGT only.

        Returns (is_valid, error_message).
        """
        if not adapter:
            return False, "Adapter sequence is empty"

        adapter = adapter.strip()
        length = len(adapter)

        if length < CUSTOM_ADAPTER_MIN_LEN:
            return False, f"Adapter too short ({length}nt < {CUSTOM_ADAPTER_MIN_LEN}nt minimum)"

        if length > CUSTOM_ADAPTER_MAX_LEN:
            return False, f"Adapter too long ({length}nt > {CUSTOM_ADAPTER_MAX_LEN}nt maximum)"

        if not VALID_DNA_PATTERN.match(adapter):
            invalid_chars = set(adapter.upper()) - set("ACGT")
            return False, f"Invalid characters in adapter: {invalid_chars}"

        return True, ""

    def _compute_adapter_dimer_dg(
        self, adapter: str, gene_specific: str, annealing_temp: float
    ) -> float:
        """
        Compute cross-dimer ΔG between adapter overhang and gene-specific region.

        Uses nearest-neighbor thermodynamics to estimate the stability of
        potential adapter-gene interactions at the specified annealing temperature.

        Args:
            adapter: 5' adapter sequence
            gene_specific: Gene-specific primer sequence
            annealing_temp: Annealing temperature in °C

        Returns:
            ΔG in kcal/mol (more negative = more stable = worse)
        """
        try:
            # Try primer3 library first for accurate heterodimer calculation
            import primer3 as p3
            result = p3.calc_heterodimer(
                adapter, gene_specific,
                mv_conc=50.0,
                dv_conc=1.5,
                temp_c=annealing_temp,
            )
            return result.dg / 1000.0  # Convert cal/mol to kcal/mol
        except Exception as e: logger.debug("Suppressed exception: %s", e)

        # Fallback: use internal thermodynamics engine
        try:
            from ..thermodynamics import predict_cross_dimer
            result = predict_cross_dimer(adapter, gene_specific)
            return result.delta_g
        except Exception as e: logger.debug("Suppressed exception: %s", e)

        # Last resort: simplified sliding-window calculation
        return self._simplified_cross_dimer_dg(adapter, gene_specific, annealing_temp)

    def _simplified_cross_dimer_dg(
        self, seq1: str, seq2: str, temp_c: float
    ) -> float:
        """
        Simplified cross-dimer ΔG estimation using a sliding window approach.

        Scans all alignments of seq1 against the reverse complement of seq2,
        counting Watson-Crick base pairs and estimating stability.
        """
        from ..thermodynamics import NN_PARAMS

        s1 = seq1.upper()
        s2 = seq2.upper()
        # Reverse complement of seq2
        comp_map = {"A": "T", "T": "A", "G": "C", "C": "G"}
        rc2 = "".join(comp_map.get(b, "N") for b in reversed(s2))

        n1, n2 = len(s1), len(rc2)
        min_dg = 0.0

        for offset in range(-(n2 - 3), n1 - 2):
            dg = 0.0
            pairs = 0

            for i in range(n1):
                j = i - offset
                if 0 <= j < n2:
                    if s1[i] == rc2[j]:
                        pairs += 1
                        if i + 1 < n1:
                            dinuc = s1[i] + s1[i + 1]
                            if dinuc in NN_PARAMS:
                                dh, ds = NN_PARAMS[dinuc]
                                dg += (dh - 310.15 * ds / 1000.0) * 0.5
                    else:
                        if pairs >= 3:
                            break

            if pairs >= 4 and dg < min_dg:
                min_dg = dg

        return round(min_dg, 2)

    def _compute_effective_tm(self, gene_specific_seq: str) -> float:
        """
        Recalculate Tm on the gene-specific portion only (excluding adapter).

        This ensures annealing temperature is determined by the gene-binding
        region, not the full tailed oligo.
        """
        seq = gene_specific_seq.upper().strip()
        if len(seq) < 8:
            # Too short for NN calculation, use basic formula
            gc = seq.count("G") + seq.count("C")
            at = seq.count("A") + seq.count("T")
            if len(seq) < 14:
                return 2.0 * at + 4.0 * gc
            else:
                return 64.9 + 41.0 * (gc - 16.4) / len(seq)

        try:
            from ..thermodynamics import calculate_tm, BufferConditions
            result = calculate_tm(seq, BufferConditions())
            return result.tm_salt_adjusted
        except (ImportError, Exception):
            # Fallback: basic Tm formula
            gc = seq.count("G") + seq.count("C")
            n = len(seq)
            return 81.5 + 16.6 * math.log10(0.05) + 41.0 * (gc / n) - 600.0 / n


# ═══════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL EXECUTE FUNCTION
# ═══════════════════════════════════════════════════════════════════════════


def execute(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Module-level entry point for the Adapter Tailing step.

    Instantiates AdapterTailingStep and delegates execution.

    Input keys:
        primer_candidates (list): Primer candidate dicts.
        adapter_platform (str): Platform identifier.
        custom_adapter (str, optional): User-supplied adapter sequence.

    Output keys:
        tailed_primers (list): Annotated tailed primers.
        adapter_foldback_flags (list): Primer IDs with foldback risk.
        purification_recommendations (list): Primers needing PAGE purification.
    """
    step = AdapterTailingStep()
    return step.execute(input_data)


def _primer_candidates_from_pairs(input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build flat adapter-tailing candidates from the richest available pair list."""
    for key in (
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
            candidates: List[Dict[str, Any]] = []
            for idx, pair in enumerate(pairs, start=1):
                pair_id = pair.get("pair_id") or pair.get("rank") or idx
                for direction, primer_key in (("forward", "forward"), ("reverse", "reverse")):
                    primer = pair.get(primer_key, {})
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

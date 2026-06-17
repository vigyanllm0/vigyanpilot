"""
Step 3: Bisulfite Conversion Simulation
=========================================
Simulates bisulfite conversion of unmethylated cytosines for
methylation-specific PCR (MSP) primer design.

Bisulfite treatment converts unmethylated cytosines to uracil (read as T),
while methylated cytosines (typically in CpG contexts) remain unconverted.
This step generates both fully-converted and CpG-preserved reference
sequences for sense and antisense strands.
"""

import logging
from typing import Any, Dict, List, Tuple

from .base import PipelineStep

logger = logging.getLogger(__name__)

# Standard IUPAC ambiguity codes (non-ACGT characters that are valid)
IUPAC_AMBIGUITY_CODES = set("RYSWKMBDHVN")


class BisulfiteConversionStep(PipelineStep):
    """Simulates bisulfite conversion of unmethylated cytosines."""

    def __init__(self):
        super().__init__(name="Bisulfite Conversion Simulation", step_number=3)

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate bisulfite conversion on sense and antisense strands.

        Input keys:
            target_sequence: str — the DNA sequence to convert
            design_mode: str — must be "bisulfite" to activate conversion

        Output keys:
            bisulfite_applied: bool
            cpg_count: int
            cpg_positions: List[int]
            unsuitable_for_msp: bool
            converted_sense_cpg_preserved: str
            converted_antisense_cpg_preserved: str
            converted_sense_fully: str
            converted_antisense_fully: str
            ambiguous_positions: List[Dict]
        """
        design_mode = input_data.get("design_mode", "")

        # If not bisulfite mode, skip this step entirely
        if design_mode != "bisulfite":
            logger.info("Design mode is '%s', skipping bisulfite conversion.", design_mode)
            return {"bisulfite_applied": False}

        target_sequence = input_data.get("target_sequence", "")
        if not target_sequence:
            raise ValueError("No target_sequence provided for bisulfite conversion")

        seq_upper = target_sequence.upper()

        # Count CpG sites in the sense strand
        cpg_count, cpg_positions = self._count_cpg_sites(seq_upper)

        # Determine if target is unsuitable for MSP (CpG < 2)
        unsuitable_for_msp = cpg_count < 2
        if unsuitable_for_msp:
            logger.warning(
                "Target has only %d CpG site(s) — unsuitable for methylation-specific PCR.",
                cpg_count,
            )

        # Find ambiguous (IUPAC non-ACGT) positions
        ambiguous_positions = self._find_ambiguous_positions(seq_upper)

        # Generate antisense strand (reverse complement)
        antisense = self._reverse_complement(seq_upper)

        # Generate converted sequences for sense strand
        converted_sense_cpg_preserved = self._convert_strand(seq_upper, preserve_cpg=True)
        converted_sense_fully = self._convert_strand(seq_upper, preserve_cpg=False)

        # Generate converted sequences for antisense strand
        converted_antisense_cpg_preserved = self._convert_strand(antisense, preserve_cpg=True)
        converted_antisense_fully = self._convert_strand(antisense, preserve_cpg=False)

        return {
            "bisulfite_applied": True,
            "cpg_count": cpg_count,
            "cpg_positions": cpg_positions,
            "unsuitable_for_msp": unsuitable_for_msp,
            "converted_sense_cpg_preserved": converted_sense_cpg_preserved,
            "converted_antisense_cpg_preserved": converted_antisense_cpg_preserved,
            "converted_sense_fully": converted_sense_fully,
            "converted_antisense_fully": converted_antisense_fully,
            "ambiguous_positions": ambiguous_positions,
        }

    def _convert_strand(self, seq: str, preserve_cpg: bool) -> str:
        """
        Convert C→T in a strand, optionally preserving CpG cytosines.

        Args:
            seq: Uppercase DNA sequence string.
            preserve_cpg: If True, cytosines followed by G are preserved.
                          If False, all cytosines are converted (fully converted).

        Returns:
            Converted sequence string.
        """
        result = []
        seq_len = len(seq)

        for i, base in enumerate(seq):
            if base == "C":
                if preserve_cpg and i + 1 < seq_len and seq[i + 1] == "G":
                    # CpG context — preserve the C
                    result.append("C")
                elif base in IUPAC_AMBIGUITY_CODES:
                    # Should not reach here since we check for 'C' first,
                    # but included for safety
                    result.append(base)
                else:
                    # Non-CpG cytosine (or fully-converted mode) → convert to T
                    result.append("T")
            elif base in IUPAC_AMBIGUITY_CODES:
                # Leave IUPAC ambiguity codes unconverted
                result.append(base)
            else:
                # A, G, T — leave unchanged
                result.append(base)

        return "".join(result)

    def _count_cpg_sites(self, seq: str) -> Tuple[int, List[int]]:
        """
        Count CpG dinucleotides and return their 0-indexed positions.

        A CpG site is defined as a C immediately followed by G on the same
        strand. The position recorded is the index of the C.

        Args:
            seq: Uppercase DNA sequence string.

        Returns:
            Tuple of (count, list of 0-indexed positions of C in CpG).
        """
        positions: List[int] = []
        for i in range(len(seq) - 1):
            if seq[i] == "C" and seq[i + 1] == "G":
                positions.append(i)
        return len(positions), positions

    def _find_ambiguous_positions(self, seq: str) -> List[Dict]:
        """
        Identify positions with IUPAC ambiguity codes (non-ACGT characters).

        These positions cannot be reliably converted during bisulfite treatment
        and are annotated as ambiguous in the output.

        Args:
            seq: Uppercase DNA sequence string.

        Returns:
            List of dicts with 'position', 'code', and 'note' for each
            ambiguous position.
        """
        ambiguous: List[Dict] = []
        for i, base in enumerate(seq):
            if base in IUPAC_AMBIGUITY_CODES:
                ambiguous.append({
                    "position": i,
                    "code": base,
                    "note": "Left unconverted — ambiguous base cannot be reliably converted",
                })
        return ambiguous

    def _reverse_complement(self, seq: str) -> str:
        """
        Compute the reverse complement of a DNA sequence.

        Standard bases are complemented (A↔T, C↔G). IUPAC ambiguity codes
        are complemented according to standard rules.

        Args:
            seq: Uppercase DNA sequence string.

        Returns:
            Reverse complement string.
        """
        complement_map = {
            "A": "T", "T": "A", "C": "G", "G": "C",
            # IUPAC ambiguity complements
            "R": "Y", "Y": "R",  # R=A/G ↔ Y=C/T
            "S": "S",            # S=G/C ↔ S=G/C
            "W": "W",            # W=A/T ↔ W=A/T
            "K": "M", "M": "K",  # K=G/T ↔ M=A/C
            "B": "V", "V": "B",  # B=C/G/T ↔ V=A/C/G
            "D": "H", "H": "D",  # D=A/G/T ↔ H=A/C/T
            "N": "N",            # N=A/C/G/T ↔ N=A/C/G/T
        }
        return "".join(complement_map.get(base, "N") for base in reversed(seq))


def execute(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Module-level execute function that instantiates BisulfiteConversionStep
    and runs the step.

    This is the entry point used by the pipeline orchestrator.
    """
    step = BisulfiteConversionStep()
    return step.execute(input_data)

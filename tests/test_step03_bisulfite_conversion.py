"""
Unit tests for Step 3: Bisulfite Conversion Simulation.

Tests cover:
- Non-bisulfite mode early return
- CpG-preserved conversion (non-CpG C→T, CpG C stays)
- Fully-converted mode (all C→T)
- CpG counting and position reporting
- Unsuitable target flagging (CpG < 2)
- IUPAC ambiguity code handling
- Antisense strand generation and conversion
- Edge cases (empty CpG, all-CpG, no cytosines)
"""

import pytest

from primerforge.engine.steps.step03_bisulfite_conversion import (
    BisulfiteConversionStep,
    execute,
)


class TestNonBisulfiteMode:
    """When design_mode is not 'bisulfite', the step should skip."""

    def test_standard_mode_returns_false(self):
        result = execute({"design_mode": "standard", "target_sequence": "ACGTCG"})
        assert result == {"bisulfite_applied": False}

    def test_empty_mode_returns_false(self):
        result = execute({"design_mode": "", "target_sequence": "ACGTCG"})
        assert result == {"bisulfite_applied": False}

    def test_missing_mode_returns_false(self):
        result = execute({"target_sequence": "ACGTCG"})
        assert result == {"bisulfite_applied": False}


class TestCpGPreservedConversion:
    """CpG-preserved conversion: non-CpG C→T, CpG cytosines kept."""

    def test_simple_cpg_preserved(self):
        # ACGTCG: CpG at pos 1 (CG) and pos 4 (CG)
        result = execute({"design_mode": "bisulfite", "target_sequence": "ACGTCG"})
        # C at pos 1 is CpG → stays C; C at pos 4 is CpG → stays C
        assert result["converted_sense_cpg_preserved"] == "ACGTCG"

    def test_non_cpg_c_converted(self):
        # ACCAGT: C at pos 1 (followed by C, not G) → T; C at pos 2 (followed by A) → T
        result = execute({"design_mode": "bisulfite", "target_sequence": "ACCAGT"})
        assert result["converted_sense_cpg_preserved"] == "ATTAGT"

    def test_mixed_cpg_and_non_cpg(self):
        # ACGTCGATCCA
        # pos 1: C followed by G → CpG, keep C
        # pos 4: C followed by G → CpG, keep C
        # pos 8: C followed by C → not CpG, convert to T
        # pos 9: C followed by A → not CpG, convert to T
        result = execute({"design_mode": "bisulfite", "target_sequence": "ACGTCGATCCA"})
        assert result["converted_sense_cpg_preserved"] == "ACGTCGATTTA"


class TestFullyConvertedMode:
    """Fully converted: all C→T regardless of CpG context."""

    def test_all_c_converted(self):
        result = execute({"design_mode": "bisulfite", "target_sequence": "ACGTCG"})
        # All C → T: A T G T T G
        assert result["converted_sense_fully"] == "ATGTTG"

    def test_fully_converted_has_no_c(self):
        result = execute({"design_mode": "bisulfite", "target_sequence": "CCCCGCCCGATACC"})
        assert "C" not in result["converted_sense_fully"]
        assert "C" not in result["converted_antisense_fully"]

    def test_no_c_in_sequence(self):
        result = execute({"design_mode": "bisulfite", "target_sequence": "AATTGG"})
        assert result["converted_sense_fully"] == "AATTGG"
        assert result["converted_sense_cpg_preserved"] == "AATTGG"


class TestCpGCounting:
    """CpG site counting and position reporting."""

    def test_two_cpg_sites(self):
        result = execute({"design_mode": "bisulfite", "target_sequence": "ACGTCG"})
        assert result["cpg_count"] == 2
        assert result["cpg_positions"] == [1, 4]

    def test_no_cpg_sites(self):
        result = execute({"design_mode": "bisulfite", "target_sequence": "AATTGGCC"})
        assert result["cpg_count"] == 0
        assert result["cpg_positions"] == []

    def test_adjacent_cpg(self):
        # CGCG: CpG at pos 0 and pos 2
        result = execute({"design_mode": "bisulfite", "target_sequence": "CGCG"})
        assert result["cpg_count"] == 2
        assert result["cpg_positions"] == [0, 2]

    def test_single_cpg(self):
        result = execute({"design_mode": "bisulfite", "target_sequence": "AACGTT"})
        assert result["cpg_count"] == 1
        assert result["cpg_positions"] == [2]


class TestUnsuitableForMSP:
    """Flag target as unsuitable when CpG count < 2."""

    def test_zero_cpg_is_unsuitable(self):
        result = execute({"design_mode": "bisulfite", "target_sequence": "AATTGGCC"})
        assert result["unsuitable_for_msp"] is True

    def test_one_cpg_is_unsuitable(self):
        result = execute({"design_mode": "bisulfite", "target_sequence": "AACGTT"})
        assert result["unsuitable_for_msp"] is True

    def test_two_cpg_is_suitable(self):
        result = execute({"design_mode": "bisulfite", "target_sequence": "ACGTCG"})
        assert result["unsuitable_for_msp"] is False

    def test_many_cpg_is_suitable(self):
        result = execute({"design_mode": "bisulfite", "target_sequence": "CGCGCGCG"})
        assert result["unsuitable_for_msp"] is False


class TestIUPACAmbiguity:
    """IUPAC ambiguity codes are left unconverted and annotated."""

    def test_ambiguous_positions_detected(self):
        # R at pos 2, N at pos 5
        result = execute({"design_mode": "bisulfite", "target_sequence": "ACRGCN"})
        assert len(result["ambiguous_positions"]) == 2
        assert result["ambiguous_positions"][0]["position"] == 2
        assert result["ambiguous_positions"][0]["code"] == "R"
        assert result["ambiguous_positions"][1]["position"] == 5
        assert result["ambiguous_positions"][1]["code"] == "N"

    def test_ambiguous_base_left_unconverted_in_cpg_preserved(self):
        # Y is an IUPAC code (C/T) — should NOT be converted even though
        # it might represent a C
        result = execute({"design_mode": "bisulfite", "target_sequence": "AYGTT"})
        assert "Y" in result["converted_sense_cpg_preserved"]

    def test_no_ambiguity_in_acgt_only(self):
        result = execute({"design_mode": "bisulfite", "target_sequence": "ACGTACGT"})
        assert result["ambiguous_positions"] == []


class TestAntisenseStrand:
    """Antisense (reverse complement) strand conversion."""

    def test_antisense_is_reverse_complement(self):
        step = BisulfiteConversionStep()
        assert step._reverse_complement("ACGT") == "ACGT"  # palindrome
        assert step._reverse_complement("AAAA") == "TTTT"
        assert step._reverse_complement("CCCC") == "GGGG"
        assert step._reverse_complement("AACG") == "CGTT"

    def test_antisense_conversion_generated(self):
        result = execute({"design_mode": "bisulfite", "target_sequence": "ACGT"})
        # Antisense of ACGT is ACGT (palindrome)
        assert result["converted_antisense_cpg_preserved"] is not None
        assert result["converted_antisense_fully"] is not None

    def test_antisense_fully_converted_has_no_c(self):
        result = execute({"design_mode": "bisulfite", "target_sequence": "GGGCCCAAATTT"})
        assert "C" not in result["converted_antisense_fully"]


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_missing_sequence_raises_error(self):
        with pytest.raises(ValueError, match="No target_sequence"):
            execute({"design_mode": "bisulfite", "target_sequence": ""})

    def test_single_base_c(self):
        result = execute({"design_mode": "bisulfite", "target_sequence": "C"})
        assert result["converted_sense_fully"] == "T"
        assert result["converted_sense_cpg_preserved"] == "T"  # no G after
        assert result["cpg_count"] == 0

    def test_cg_at_end_of_sequence(self):
        # CG at end: pos len-2 is C followed by G
        result = execute({"design_mode": "bisulfite", "target_sequence": "AACG"})
        assert result["cpg_count"] == 1
        assert result["cpg_positions"] == [2]
        assert result["converted_sense_cpg_preserved"] == "AACG"

    def test_output_keys_present(self):
        result = execute({"design_mode": "bisulfite", "target_sequence": "ACGTCG"})
        expected_keys = {
            "bisulfite_applied", "cpg_count", "cpg_positions",
            "unsuitable_for_msp", "converted_sense_cpg_preserved",
            "converted_antisense_cpg_preserved", "converted_sense_fully",
            "converted_antisense_fully", "ambiguous_positions",
        }
        assert expected_keys.issubset(result.keys())

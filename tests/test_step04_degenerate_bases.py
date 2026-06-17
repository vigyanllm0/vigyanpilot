"""
Unit tests for Step 4: Degenerate Base Parsing.

Tests cover:
- IUPAC ambiguity code parsing (Requirement 4.1)
- MSA consensus sequence generation (Requirement 4.2)
- Degeneracy fold calculation and recording (Requirement 4.3)
- 256-fold degeneracy threshold rejection (Requirement 4.4)
- Invalid character detection (Requirement 4.5)
"""

import pytest

from primerforge.engine.steps.step04_degenerate_bases import (
    DEGENERATE_EXPAND,
    DEGENERACY_FOLD,
    IUPAC_MAP,
    MAX_DEGENERACY,
    VALID_CHARS,
    execute,
)


class TestIUPACParsing:
    """Requirement 4.1: Parse IUPAC ambiguity codes into constituent nucleotide sets."""

    def test_standard_bases_no_degenerate(self):
        result = execute({"target_sequence": "ACGTACGT"})
        assert result["consensus_sequence"] == "ACGTACGT"
        assert result["degenerate_positions"] == []
        assert result["total_degenerate_count"] == 0

    def test_r_code_detected(self):
        result = execute({"target_sequence": "ARCGT"})
        dp = result["degenerate_positions"][0]
        assert dp["position"] == 1
        assert dp["code"] == "R"
        assert dp["nucleotides"] == ["A", "G"]
        assert dp["fold"] == 2

    def test_y_code_detected(self):
        result = execute({"target_sequence": "AYCGT"})
        dp = result["degenerate_positions"][0]
        assert dp["code"] == "Y"
        assert dp["nucleotides"] == ["C", "T"]
        assert dp["fold"] == 2

    def test_m_code_detected(self):
        result = execute({"target_sequence": "AMCGT"})
        dp = result["degenerate_positions"][0]
        assert dp["code"] == "M"
        assert dp["nucleotides"] == ["A", "C"]
        assert dp["fold"] == 2

    def test_k_code_detected(self):
        result = execute({"target_sequence": "AKCGT"})
        dp = result["degenerate_positions"][0]
        assert dp["code"] == "K"
        assert dp["nucleotides"] == ["G", "T"]
        assert dp["fold"] == 2

    def test_s_code_detected(self):
        result = execute({"target_sequence": "ASCGT"})
        dp = result["degenerate_positions"][0]
        assert dp["code"] == "S"
        assert dp["nucleotides"] == ["C", "G"]
        assert dp["fold"] == 2

    def test_w_code_detected(self):
        result = execute({"target_sequence": "AWCGT"})
        dp = result["degenerate_positions"][0]
        assert dp["code"] == "W"
        assert dp["nucleotides"] == ["A", "T"]
        assert dp["fold"] == 2

    def test_b_code_detected(self):
        result = execute({"target_sequence": "ABCGT"})
        dp = result["degenerate_positions"][0]
        assert dp["code"] == "B"
        assert dp["nucleotides"] == ["C", "G", "T"]
        assert dp["fold"] == 3

    def test_d_code_detected(self):
        result = execute({"target_sequence": "ADCGT"})
        dp = result["degenerate_positions"][0]
        assert dp["code"] == "D"
        assert dp["nucleotides"] == ["A", "G", "T"]
        assert dp["fold"] == 3

    def test_h_code_detected(self):
        result = execute({"target_sequence": "AHCGT"})
        dp = result["degenerate_positions"][0]
        assert dp["code"] == "H"
        assert dp["nucleotides"] == ["A", "C", "T"]
        assert dp["fold"] == 3

    def test_v_code_detected(self):
        result = execute({"target_sequence": "AVCGT"})
        dp = result["degenerate_positions"][0]
        assert dp["code"] == "V"
        assert dp["nucleotides"] == ["A", "C", "G"]
        assert dp["fold"] == 3

    def test_n_code_detected(self):
        result = execute({"target_sequence": "ANCGT"})
        dp = result["degenerate_positions"][0]
        assert dp["code"] == "N"
        assert dp["nucleotides"] == ["A", "C", "G", "T"]
        assert dp["fold"] == 4

    def test_multiple_degenerate_codes(self):
        result = execute({"target_sequence": "ARYNA"})
        assert result["total_degenerate_count"] == 3
        codes = [dp["code"] for dp in result["degenerate_positions"]]
        assert codes == ["R", "Y", "N"]

    def test_case_insensitive(self):
        result = execute({"target_sequence": "arcgt"})
        dp = result["degenerate_positions"][0]
        assert dp["code"] == "R"


class TestMSAConsensus:
    """Requirement 4.2: Generate consensus from MSA using IUPAC codes."""

    def test_identical_sequences_no_degeneracy(self):
        result = execute({
            "target_sequence": "ACGT",
            "msa_sequences": ["ACGT", "ACGT"],
        })
        assert result["consensus_sequence"] == "ACGT"
        assert result["total_degenerate_count"] == 0

    def test_single_position_difference(self):
        result = execute({
            "target_sequence": "ACGT",
            "msa_sequences": ["AGGT"],
        })
        # Position 1: {C, G} → S
        assert result["consensus_sequence"][1] == "S"

    def test_two_base_ambiguity(self):
        result = execute({
            "target_sequence": "AAAA",
            "msa_sequences": ["AGAA"],
        })
        # Position 1: {A, G} → R
        assert result["consensus_sequence"][1] == "R"

    def test_three_base_ambiguity(self):
        result = execute({
            "target_sequence": "AAAA",
            "msa_sequences": ["ACAA", "AGAA"],
        })
        # Position 1: {A, C, G} → V
        assert result["consensus_sequence"][1] == "V"

    def test_four_base_ambiguity(self):
        result = execute({
            "target_sequence": "AAAA",
            "msa_sequences": ["ACAA", "AGAA", "ATAA"],
        })
        # Position 1: {A, C, G, T} → N
        assert result["consensus_sequence"][1] == "N"

    def test_multiple_varied_positions(self):
        result = execute({
            "target_sequence": "AAAA",
            "msa_sequences": ["ACGA", "AGTA"],
        })
        # pos 0: A → A
        # pos 1: {A, C, G} → V
        # pos 2: {A, G, T} → D
        # pos 3: A → A
        assert result["consensus_sequence"] == "AVDA"

    def test_msa_with_gaps_ignored(self):
        result = execute({
            "target_sequence": "ACGT",
            "msa_sequences": ["A-GT"],
        })
        # Position 1: only C from target (gap ignored) → C
        assert result["consensus_sequence"][1] == "C"

    def test_consensus_length_is_minimum(self):
        result = execute({
            "target_sequence": "ACGT",
            "msa_sequences": ["AC"],
        })
        # Uses min length = 2
        assert len(result["consensus_sequence"]) == 2


class TestDegeneracyFold:
    """Requirement 4.3: Record position, code, nucleotides, and fold."""

    def test_fold_2_for_two_base_codes(self):
        two_base_codes = "RYMKSW"
        for code in two_base_codes:
            result = execute({"target_sequence": f"A{code}A"})
            dp = result["degenerate_positions"][0]
            assert dp["fold"] == 2, f"Expected fold 2 for {code}"

    def test_fold_3_for_three_base_codes(self):
        three_base_codes = "BDHV"
        for code in three_base_codes:
            result = execute({"target_sequence": f"A{code}A"})
            dp = result["degenerate_positions"][0]
            assert dp["fold"] == 3, f"Expected fold 3 for {code}"

    def test_fold_4_for_n(self):
        result = execute({"target_sequence": "ANA"})
        dp = result["degenerate_positions"][0]
        assert dp["fold"] == 4

    def test_position_is_zero_indexed(self):
        result = execute({"target_sequence": "ACGRT"})
        dp = result["degenerate_positions"][0]
        assert dp["position"] == 3


class TestDegeneracyThreshold:
    """Requirement 4.4: Reject if effective degeneracy > 256."""

    def test_at_threshold_accepted(self):
        # 8 R codes: 2^8 = 256
        result = execute({"target_sequence": "RRRRRRRR"})
        assert result["max_degeneracy_per_window"] == 256

    def test_above_threshold_rejected(self):
        # 9 R codes: 2^9 = 512 > 256
        with pytest.raises(ValueError, match="256"):
            execute({"target_sequence": "RRRRRRRRR"})

    def test_n_codes_exceed_quickly(self):
        # 5 N codes: 4^5 = 1024 > 256
        with pytest.raises(ValueError, match="256"):
            execute({"target_sequence": "NNNNN"})

    def test_mixed_folds_product(self):
        # B(3) * D(3) * H(3) * V(3) * N(4) = 3*3*3*3*4 = 324 > 256
        with pytest.raises(ValueError, match="256"):
            execute({"target_sequence": "BDHVN"})

    def test_scattered_within_threshold(self):
        # R at positions far apart - only 3 in any 25-nt window: 2^3 = 8
        seq = "R" + "A" * 12 + "R" + "A" * 12 + "R" + "A" * 12
        result = execute({"target_sequence": seq})
        assert result["max_degeneracy_per_window"] <= 256

    def test_window_based_calculation(self):
        # 30-char seq with 8 R's clustered at start: 2^8 = 256 in first window
        seq = "RRRRRRRR" + "A" * 22
        result = execute({"target_sequence": seq})
        assert result["max_degeneracy_per_window"] == 256


class TestInvalidCharacterDetection:
    """Requirement 4.5: Reject invalid characters with position."""

    def test_invalid_char_rejected(self):
        with pytest.raises(ValueError, match="X"):
            execute({"target_sequence": "ACXGT"})

    def test_invalid_char_position_reported(self):
        with pytest.raises(ValueError, match="2"):
            execute({"target_sequence": "ACXGT"})

    def test_number_rejected(self):
        with pytest.raises(ValueError, match="1"):
            execute({"target_sequence": "A1CGT"})

    def test_lowercase_valid(self):
        # Lowercase should be accepted (case-insensitive)
        result = execute({"target_sequence": "acgt"})
        assert result["consensus_sequence"] == "ACGT"

    def test_space_rejected(self):
        with pytest.raises(ValueError, match=" "):
            execute({"target_sequence": "AC GT"})

    def test_invalid_in_msa_rejected(self):
        with pytest.raises(ValueError, match="X"):
            execute({
                "target_sequence": "ACGT",
                "msa_sequences": ["AXGT"],
            })


class TestOutputKeys:
    """Verify all required output keys are present."""

    def test_output_keys_present(self):
        result = execute({"target_sequence": "ARCGT"})
        assert "consensus_sequence" in result
        assert "degenerate_positions" in result
        assert "total_degenerate_count" in result
        assert "max_degeneracy_per_window" in result

    def test_no_target_sequence_raises(self):
        with pytest.raises(ValueError, match="No target_sequence"):
            execute({"target_sequence": ""})

    def test_missing_target_sequence_raises(self):
        with pytest.raises(ValueError, match="No target_sequence"):
            execute({})


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_single_base(self):
        result = execute({"target_sequence": "A"})
        assert result["consensus_sequence"] == "A"
        assert result["total_degenerate_count"] == 0

    def test_single_degenerate_base(self):
        result = execute({"target_sequence": "R"})
        assert result["total_degenerate_count"] == 1
        assert result["max_degeneracy_per_window"] == 2

    def test_all_standard_bases(self):
        result = execute({"target_sequence": "ACGT" * 10})
        assert result["total_degenerate_count"] == 0
        assert result["max_degeneracy_per_window"] == 1

    def test_msa_empty_list(self):
        result = execute({"target_sequence": "ACGT", "msa_sequences": []})
        assert result["consensus_sequence"] == "ACGT"

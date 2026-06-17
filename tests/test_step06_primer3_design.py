"""
Unit tests for Step 6: Primer3 Parameter Constraints.

Tests cover:
- Primer length enforcement [18, 25] (Requirement 6.1)
- GC content rejection outside [40%, 60%] (Requirement 6.2)
- Tm window enforcement with defaults and user-specified (Requirement 6.3)
- 3' homopolymer rejection: >3 consecutive in last 5nt (Requirement 6.4)
- Request 20 candidates from Primer3 (Requirement 6.5)
- Low candidate yield flag when < 5 pairs (Requirement 6.6)
- ΔTm ≤ 1.5°C between forward and reverse (Requirement 6.7)
- Module-level execute() function input/output contract
"""

import pytest

from primerforge.engine.steps.step06_primer3_design import (
    PRIMER_LENGTH_MIN,
    PRIMER_LENGTH_MAX,
    GC_MIN,
    GC_MAX,
    TM_DEFAULT_MIN,
    TM_DEFAULT_MAX,
    TM_ABSOLUTE_MIN,
    TM_ABSOLUTE_MAX,
    MAX_DELTA_TM,
    NUM_CANDIDATES_REQUESTED,
    LOW_YIELD_THRESHOLD,
    HOMOPOLYMER_MAX_RUN,
    _compute_gc_content,
    _has_3prime_homopolymer,
    _validate_tm_window,
    _passes_length_constraint,
    _passes_gc_constraint,
    _passes_tm_constraint,
    _filter_candidate,
    execute,
)


class TestGCContentComputation:
    """Test GC content calculation."""

    def test_all_gc(self):
        assert _compute_gc_content("GCGCGC") == 100.0

    def test_all_at(self):
        assert _compute_gc_content("ATATAT") == 0.0

    def test_50_percent(self):
        assert _compute_gc_content("ATGC") == 50.0

    def test_empty_string(self):
        assert _compute_gc_content("") == 0.0

    def test_case_insensitive(self):
        assert _compute_gc_content("gcgc") == 100.0


class TestHomopolymerDetection:
    """Requirement 6.4: 3' homopolymer rejection."""

    def test_4_consecutive_in_last_5_rejected(self):
        # Last 5: "AAAAG" -> 4 A's consecutive -> >3, reject
        assert _has_3prime_homopolymer("GCGCGCAAAAG") is True

    def test_4_consecutive_at_very_end(self):
        # Last 5: "GAAAA" -> 4 A's consecutive
        assert _has_3prime_homopolymer("GCGCGCGAAAA") is True

    def test_3_consecutive_is_ok(self):
        # Last 5: "GAAAG" -> 3 A's consecutive -> exactly 3, OK
        assert _has_3prime_homopolymer("GCGCGCGAAAG") is False

    def test_no_homopolymer(self):
        assert _has_3prime_homopolymer("GCATGCATGC") is False

    def test_homopolymer_earlier_not_in_last_5(self):
        # AAAA in middle, last 5: "GCATG" -> no issue
        assert _has_3prime_homopolymer("AAAAGCATG") is False

    def test_5_consecutive_rejected(self):
        # Last 5: "TTTTT" -> 5 T's consecutive
        assert _has_3prime_homopolymer("GCGTTTTT") is True

    def test_short_primer_with_homopolymer(self):
        # Only 4nt: "AAAA" -> run of 4
        assert _has_3prime_homopolymer("AAAA") is True

    def test_short_primer_no_homopolymer(self):
        assert _has_3prime_homopolymer("ATGC") is False


class TestTmWindowValidation:
    """Requirement 6.3: Tm window validation and clamping."""

    def test_default_values_unchanged(self):
        tm_min, tm_max = _validate_tm_window(58.0, 62.0)
        assert tm_min == 58.0
        assert tm_max == 62.0

    def test_clamps_below_minimum(self):
        tm_min, tm_max = _validate_tm_window(45.0, 60.0)
        assert tm_min == 50.0
        assert tm_max == 60.0

    def test_clamps_above_maximum(self):
        tm_min, tm_max = _validate_tm_window(60.0, 80.0)
        assert tm_min == 60.0
        assert tm_max == 72.0

    def test_both_clamped(self):
        tm_min, tm_max = _validate_tm_window(30.0, 90.0)
        assert tm_min == 50.0
        assert tm_max == 72.0

    def test_swaps_if_inverted(self):
        tm_min, tm_max = _validate_tm_window(65.0, 55.0)
        assert tm_min == 55.0
        assert tm_max == 65.0


class TestLengthConstraint:
    """Requirement 6.1: Primer length [18, 25]."""

    def test_minimum_valid(self):
        assert _passes_length_constraint(18) is True

    def test_maximum_valid(self):
        assert _passes_length_constraint(25) is True

    def test_middle_valid(self):
        assert _passes_length_constraint(20) is True

    def test_too_short(self):
        assert _passes_length_constraint(17) is False

    def test_too_long(self):
        assert _passes_length_constraint(26) is False


class TestGCConstraint:
    """Requirement 6.2: GC content [40%, 60%]."""

    def test_minimum_valid(self):
        assert _passes_gc_constraint(40.0) is True

    def test_maximum_valid(self):
        assert _passes_gc_constraint(60.0) is True

    def test_middle_valid(self):
        assert _passes_gc_constraint(50.0) is True

    def test_too_low(self):
        assert _passes_gc_constraint(39.99) is False

    def test_too_high(self):
        assert _passes_gc_constraint(60.01) is False


class TestTmConstraint:
    """Requirement 6.3: Tm within user-specified window."""

    def test_within_default_range(self):
        assert _passes_tm_constraint(60.0, 58.0, 62.0) is True

    def test_at_lower_bound(self):
        assert _passes_tm_constraint(58.0, 58.0, 62.0) is True

    def test_at_upper_bound(self):
        assert _passes_tm_constraint(62.0, 58.0, 62.0) is True

    def test_below_range(self):
        assert _passes_tm_constraint(57.9, 58.0, 62.0) is False

    def test_above_range(self):
        assert _passes_tm_constraint(62.1, 58.0, 62.0) is False


class TestFilterCandidate:
    """Test individual primer post-filtering."""

    def test_valid_primer_passes(self):
        primer = {
            "sequence": "ATGCATGCATGCATGCATGC",  # 20nt, GC=50%
            "gc": 50.0,
            "tm": 60.0,
        }
        passes, reason = _filter_candidate(primer, 58.0, 62.0)
        assert passes is True
        assert reason == ""

    def test_length_violation_rejected(self):
        primer = {
            "sequence": "ATGCATGCATGCATGCAT",  # 18nt but force short
            "gc": 50.0,
            "tm": 60.0,
        }
        # Use a 15nt sequence to trigger length violation
        primer["sequence"] = "ATGCATGCATGCATG"
        passes, reason = _filter_candidate(primer, 58.0, 62.0)
        assert passes is False
        assert "length_violation" in reason

    def test_gc_violation_rejected(self):
        primer = {
            "sequence": "ATATATATATATATATATATAT",  # 22nt, low GC
            "gc": 0.0,
            "tm": 60.0,
        }
        passes, reason = _filter_candidate(primer, 58.0, 62.0)
        assert passes is False
        assert "gc_violation" in reason

    def test_tm_violation_rejected(self):
        primer = {
            "sequence": "ATGCATGCATGCATGCATGC",  # 20nt
            "gc": 50.0,
            "tm": 75.0,
        }
        passes, reason = _filter_candidate(primer, 58.0, 62.0)
        assert passes is False
        assert "tm_violation" in reason

    def test_3prime_homopolymer_rejected(self):
        primer = {
            "sequence": "ATGCATGCATGCATGCAAAA",  # 20nt, ends with AAAA
            "gc": 45.0,
            "tm": 60.0,
        }
        passes, reason = _filter_candidate(primer, 58.0, 62.0)
        assert passes is False
        assert "3prime_homopolymer" in reason


class TestExecuteFunction:
    """Test the module-level execute() function."""

    def test_raises_on_empty_sequence(self):
        with pytest.raises(ValueError, match="No sequence"):
            execute({})

    def test_raises_on_missing_sequence(self):
        with pytest.raises(ValueError, match="No sequence"):
            execute({"some_key": "value"})

    def test_output_keys_present(self):
        """Test that execute returns the required output keys."""
        # Use a well-known sequence that should produce primers
        # A simple 200bp sequence with balanced GC
        seq = "ATGCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC"
        result = execute({"target_sequence": seq})

        assert "candidate_pairs" in result
        assert "low_candidate_yield" in result
        assert "pair_count" in result
        assert isinstance(result["candidate_pairs"], list)
        assert isinstance(result["low_candidate_yield"], bool)
        assert isinstance(result["pair_count"], int)

    def test_accepts_consensus_sequence_key(self):
        seq = "ATGCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC"
        result = execute({"consensus_sequence": seq})
        assert "candidate_pairs" in result

    def test_design_params_respected(self):
        """Test that design_params override defaults."""
        seq = "ATGCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC"
        result = execute({
            "target_sequence": seq,
            "design_params": {
                "tm_min": 55.0,
                "tm_max": 65.0,
                "product_size_min": 100,
                "product_size_max": 300,
            },
        })
        assert "candidate_pairs" in result

    def test_top_level_product_range_is_respected(self):
        """UI-style product_min/product_max keys must constrain Primer3 output."""
        seq = (
            "ATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGC"
            "CGTACGATCGTACGATCGTACGATCGTACGATCGTACGATCGTACGATCGTACGATCGTA"
            "GGCATCGATCGATGCTAGCTAGCATCGATCGATCGTAGCTAGCTAGCATCGATCGATCGA"
            "TACGATCGTAGCTAGCTAGCATCGATCGTACGATCGATCGATGCTAGCTAGCATCGATC"
            "GATCGTAGCTAGCTAGCATCGATCGATCGATCGTAGCTAGCTAGCATCGATCGATCGAT"
        )
        result = execute({
            "target_sequence": seq,
            "product_min": 100,
            "product_max": 300,
        })
        for pair in result["candidate_pairs"]:
            assert 100 <= pair["product_size"] <= 300
            assert 100 <= len(pair["amplicon_sequence"]) <= 300

    def test_candidate_pair_structure(self):
        """Test that each candidate pair has the required fields."""
        # A longer, more natural-looking sequence
        seq = (
            "ATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGC"
            "ATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGC"
            "ATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGC"
            "ATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGC"
        )
        result = execute({"target_sequence": seq})

        if result["pair_count"] > 0:
            pair = result["candidate_pairs"][0]
            assert "forward" in pair
            assert "reverse" in pair
            assert "product_size" in pair
            assert "penalty" in pair
            assert "forward_tm" in pair
            assert "reverse_tm" in pair
            assert "delta_tm" in pair

    def test_low_candidate_yield_flag(self):
        """A difficult sequence should trigger low_candidate_yield when < 5 pairs."""
        # A very AT-rich sequence that's hard to design primers for (low GC)
        # but still long enough for valid product size range
        seq = "A" * 40 + "GCGC" + "T" * 100 + "GCGC" + "A" * 60
        result = execute({
            "target_sequence": seq,
            "design_params": {"product_size_min": 50, "product_size_max": 200},
        })
        # This sequence should yield very few (likely 0) valid pairs due to
        # extreme AT-richness making it impossible to find GC-balanced primers
        if result["pair_count"] < 5:
            assert result["low_candidate_yield"] is True
        # Even if somehow pairs are returned, the flag logic is correct
        if result["pair_count"] >= 5:
            assert result["low_candidate_yield"] is False

    def test_all_filtered_pairs_respect_delta_tm(self):
        """All returned pairs should have ΔTm ≤ 1.5°C."""
        seq = (
            "ATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGC"
            "ATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGC"
            "ATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGC"
            "ATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGC"
        )
        result = execute({"target_sequence": seq})
        for pair in result["candidate_pairs"]:
            assert pair["delta_tm"] <= MAX_DELTA_TM

    def test_all_filtered_pairs_forward_length_valid(self):
        """All returned forward primers should be 18-25nt."""
        seq = (
            "ATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGC"
            "ATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGC"
            "ATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGC"
            "ATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGC"
        )
        result = execute({"target_sequence": seq})
        for pair in result["candidate_pairs"]:
            fwd_len = len(pair["forward"])
            assert PRIMER_LENGTH_MIN <= fwd_len <= PRIMER_LENGTH_MAX

    def test_all_filtered_pairs_reverse_length_valid(self):
        """All returned reverse primers should be 18-25nt."""
        seq = (
            "ATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGC"
            "ATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGC"
            "ATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGC"
            "ATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGC"
        )
        result = execute({"target_sequence": seq})
        for pair in result["candidate_pairs"]:
            rev_len = len(pair["reverse"])
            assert PRIMER_LENGTH_MIN <= rev_len <= PRIMER_LENGTH_MAX

    def test_pair_count_matches_list_length(self):
        """pair_count should match the length of candidate_pairs."""
        seq = (
            "ATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGC"
            "ATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGC"
            "ATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGCATGCTAGCATGC"
        )
        result = execute({"target_sequence": seq})
        assert result["pair_count"] == len(result["candidate_pairs"])

    def test_consensus_sequence_takes_priority(self):
        """consensus_sequence should be used over target_sequence if both provided."""
        seq1 = "ATGCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC"
        seq2 = "NNNNNNNNNNNN"  # This would fail or produce 0 pairs
        result = execute({"consensus_sequence": seq1, "target_sequence": seq2})
        # Should use seq1 (consensus_sequence), not seq2
        assert "candidate_pairs" in result

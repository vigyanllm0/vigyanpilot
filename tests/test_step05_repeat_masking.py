"""
Unit tests for Step 5: Repeat Masking.

Tests cover:
- Complexity scan detecting homopolymer runs ≥6 (Requirement 5.2)
- Complexity scan detecting dinucleotide repeats ≥5 units (Requirement 5.2)
- Complexity scan detecting trinucleotide repeats ≥4 units (Requirement 5.2)
- Soft-masking lowercases exactly detected positions (Requirement 5.3)
- 50% overlap primer rejection with "repeat_overlap" penalty (Requirement 5.4)
- Repeat element type and overlap percentage reporting (Requirement 5.5)
- Fallback to complexity scan when local Dfam annotations are unavailable (Requirement 5.6)
- Module-level execute function input/output contract
"""

import pytest

from primerforge.engine.steps.step05_repeat_masking import (
    REPEAT_OVERLAP_PENALTY,
    REPEAT_OVERLAP_WEIGHT,
    _calculate_overlap_fraction,
    _check_primer_repeat_overlap,
    _complexity_scan,
    _get_masked_positions,
    _soft_mask,
    execute,
)


class TestComplexityScanHomopolymer:
    """Requirement 5.2: Detect homopolymer runs of 6 or more bases."""

    def test_detects_6_base_homopolymer(self):
        seq = "GCGCAAAAAAGCGC"  # 6 A's at positions 4-9
        regions = _complexity_scan(seq)
        homo = [r for r in regions if r["repeat_type"] == "homopolymer"]
        assert len(homo) == 1
        assert homo[0]["start"] == 4
        assert homo[0]["end"] == 10
        assert homo[0]["pattern"] == "A"

    def test_detects_long_homopolymer(self):
        seq = "TTTTTTTTTTTT"  # 12 T's
        regions = _complexity_scan(seq)
        homo = [r for r in regions if r["repeat_type"] == "homopolymer"]
        assert len(homo) >= 1
        assert homo[0]["length"] == 12

    def test_ignores_5_base_run(self):
        seq = "GCGCAAAAAGCGC"  # Only 5 A's — below threshold
        regions = _complexity_scan(seq)
        homo = [r for r in regions if r["repeat_type"] == "homopolymer"]
        assert len(homo) == 0

    def test_multiple_homopolymers(self):
        seq = "AAAAAACCCCCCC"  # 6 A's + 7 C's
        regions = _complexity_scan(seq)
        homo = [r for r in regions if r["repeat_type"] == "homopolymer"]
        assert len(homo) == 2

    def test_case_insensitive(self):
        seq = "gcgcaaaaaagcgc"
        regions = _complexity_scan(seq)
        homo = [r for r in regions if r["repeat_type"] == "homopolymer"]
        assert len(homo) == 1


class TestComplexityScanDinucleotide:
    """Requirement 5.2: Detect dinucleotide repeats of 5 or more units."""

    def test_detects_5_unit_dinucleotide(self):
        seq = "GCGCATATATATATATGCGC"  # AT repeated ≥5 times
        regions = _complexity_scan(seq)
        di = [r for r in regions if r["repeat_type"] == "dinucleotide"]
        assert len(di) >= 1
        assert di[0]["pattern"] == "AT"

    def test_ignores_4_unit_dinucleotide(self):
        seq = "GCGCATATATATGCGC"  # AT repeated 3 times only (ATATAT = 6 chars)
        regions = _complexity_scan(seq)
        di = [r for r in regions if r["repeat_type"] == "dinucleotide"]
        assert len(di) == 0

    def test_gc_dinucleotide_repeat(self):
        seq = "AAAGCGCGCGCGCGAAA"  # GC repeated ≥5 times
        regions = _complexity_scan(seq)
        di = [r for r in regions if r["repeat_type"] == "dinucleotide"]
        assert len(di) >= 1


class TestComplexityScanTrinucleotide:
    """Requirement 5.2: Detect trinucleotide repeats of 4 or more units."""

    def test_detects_4_unit_trinucleotide(self):
        seq = "GCGCCAGCAGCAGCAGGCGC"  # CAG repeated 4 times
        regions = _complexity_scan(seq)
        tri = [r for r in regions if r["repeat_type"] == "trinucleotide"]
        assert len(tri) >= 1
        assert tri[0]["pattern"] == "CAG"

    def test_ignores_3_unit_trinucleotide(self):
        seq = "GCGCCAGCAGCAGGCGC"  # CAG repeated 3 times only
        regions = _complexity_scan(seq)
        tri = [r for r in regions if r["repeat_type"] == "trinucleotide"]
        assert len(tri) == 0

    def test_ctg_trinucleotide_repeat(self):
        seq = "AAACTGCTGCTGCTGAAA"  # CTG repeated 4 times
        regions = _complexity_scan(seq)
        tri = [r for r in regions if r["repeat_type"] == "trinucleotide"]
        assert len(tri) >= 1


class TestSoftMask:
    """Requirement 5.3: Soft-mask lowercases exactly identified repeat positions."""

    def test_lowercases_homopolymer_positions(self):
        seq = "ATCGATCGAAAAAAAAATCGATCG"
        regions = _complexity_scan(seq)
        masked = _soft_mask(seq, regions)
        # Every lowercase position should correspond to detected region
        masked_pos = _get_masked_positions(masked)
        for region in regions:
            for p in range(region["start"], region["end"]):
                assert p in masked_pos

    def test_non_repeat_positions_uppercase(self):
        seq = "ATCGATCGAAAAAAAAATCGATCG"
        regions = _complexity_scan(seq)
        masked = _soft_mask(seq, regions)
        # Positions 0-7 are not in any detected region
        for i in range(8):
            assert masked[i].isupper()

    def test_empty_regions_no_masking(self):
        seq = "ATCGATCG"
        masked = _soft_mask(seq, [])
        assert masked == seq

    def test_all_positions_masked(self):
        seq = "AAAAAAAAAA"  # 10 A's, all masked
        regions = _complexity_scan(seq)
        masked = _soft_mask(seq, regions)
        assert all(c.islower() for c in masked)

    def test_preserves_sequence_content(self):
        seq = "ATCGAAAAAAGCTA"
        regions = _complexity_scan(seq)
        masked = _soft_mask(seq, regions)
        assert masked.upper() == seq.upper()


class TestOverlapRejection:
    """Requirement 5.4: Reject primers with ≥50% overlap in masked regions."""

    def test_rejects_at_50_percent(self):
        # 10-base primer, 5 positions masked = 50% -> reject
        masked_positions = {0, 1, 2, 3, 4}
        fraction = _calculate_overlap_fraction(0, 10, masked_positions)
        assert fraction >= 0.5

    def test_passes_below_50_percent(self):
        # 10-base primer, 4 positions masked = 40% -> pass
        masked_positions = {0, 1, 2, 3}
        fraction = _calculate_overlap_fraction(0, 10, masked_positions)
        assert fraction < 0.5

    def test_rejects_fully_overlapping(self):
        # 10-base primer, all 10 positions masked = 100% -> reject
        masked_positions = set(range(10))
        fraction = _calculate_overlap_fraction(0, 10, masked_positions)
        assert fraction == 1.0

    def test_no_overlap(self):
        # 10-base primer, no masked positions
        masked_positions = set()
        fraction = _calculate_overlap_fraction(0, 10, masked_positions)
        assert fraction == 0.0

    def test_primer_overlap_check_returns_penalty_info(self):
        seq = "AAAAAAAAAA"  # All masked
        regions = _complexity_scan(seq)
        masked = _soft_mask(seq, regions)

        result = _check_primer_repeat_overlap("AAAAAAAAAA", 0, masked, regions)
        assert result is not None
        assert result["penalty"] == REPEAT_OVERLAP_PENALTY
        assert result["penalty_weight"] == REPEAT_OVERLAP_WEIGHT
        assert result["overlap_percent"] == 100.0

    def test_primer_overlap_check_returns_none_if_passing(self):
        # Sequence with masking only at end
        seq = "ATCGATCGAAAAAAAAAA"
        regions = _complexity_scan(seq)
        masked = _soft_mask(seq, regions)

        # Primer at start, no overlap with masked region
        result = _check_primer_repeat_overlap("ATCGATCG", 0, masked, regions)
        assert result is None


class TestOverlapReporting:
    """Requirement 5.5: Report element type and percentage overlap."""

    def test_reports_overlap_percentage(self):
        result = execute({
            "target_sequence": "GCGCAAAAAAAAAAAAGCGC",  # homopolymer A
            "primer_candidates": [
                {"id": "p1", "sequence": "AAAAAAAAAA", "start": 4},
            ],
        })
        assert len(result["flagged_primers"]) == 1
        flagged = result["flagged_primers"][0]
        assert "overlap_percent" in flagged
        assert flagged["overlap_percent"] > 0

    def test_reports_element_type(self):
        result = execute({
            "target_sequence": "GCGCAAAAAAAAAAAAGCGC",
            "primer_candidates": [
                {"id": "p1", "sequence": "AAAAAAAAAA", "start": 4},
            ],
        })
        flagged = result["flagged_primers"][0]
        assert "overlapping_element_type" in flagged
        assert flagged["overlapping_element_type"] == "Simple"


class TestFallbackBehavior:
    """Requirement 5.6: Fallback to complexity scan if local Dfam annotations fail."""

    def test_no_coordinates_uses_complexity_scan(self):
        result = execute({"target_sequence": "ATCGATCGAAAAAAAAATCG"})
        assert result["masking_source"] == "complexity_scan"

    def test_invalid_coordinates_falls_back(self):
        result = execute({
            "target_sequence": "ATCGATCGAAAAAAAAATCG",
            "genomic_coordinates": "invalid_format",
        })
        assert result["masking_source"] == "complexity_scan"
        assert len(result["repeat_regions"]) >= 1


class TestExecuteFunction:
    """Test module-level execute function input/output contract."""

    def test_required_output_keys(self):
        result = execute({"target_sequence": "ATCGATCGATCG"})
        assert "masked_sequence" in result
        assert "repeat_regions" in result
        assert "low_complexity_regions" in result
        assert "masking_source" in result

    def test_raises_on_missing_sequence(self):
        with pytest.raises(ValueError, match="No target_sequence"):
            execute({})

    def test_raises_on_empty_sequence(self):
        with pytest.raises(ValueError, match="No target_sequence"):
            execute({"target_sequence": ""})

    def test_clean_sequence_no_masking(self):
        result = execute({"target_sequence": "ATCGATCGATCG"})
        assert result["masked_sequence"] == "ATCGATCGATCG"
        assert result["repeat_regions"] == []

    def test_output_masked_sequence_same_length(self):
        seq = "ATCGATCGAAAAAAAAATCGATCG"
        result = execute({"target_sequence": seq})
        assert len(result["masked_sequence"]) == len(seq)

    def test_primer_candidates_filtering(self):
        # Sequence: 20 chars clean + 12 A's + 20 chars clean
        seq = "ATCGATCGATCGATCGATCG" + "AAAAAAAAAAAA" + "ATCGATCGATCGATCGATCG"
        result = execute({
            "target_sequence": seq,
            "primer_candidates": [
                {"id": "good", "sequence": "ATCGATCGAT", "start": 0},  # fully in clean region
                {"id": "bad", "sequence": "AAAAAAAAAA", "start": 20},  # fully in masked region
            ],
        })
        flagged_ids = [p["primer_id"] for p in result["flagged_primers"]]
        assert "bad" in flagged_ids
        assert "good" not in flagged_ids

    def test_masked_fraction_reported(self):
        result = execute({"target_sequence": "AAAAAAAAAA"})
        assert "masked_fraction" in result
        assert result["masked_fraction"] == 1.0

    def test_masked_fraction_zero_for_clean(self):
        result = execute({"target_sequence": "ATCGATCGATCG"})
        assert result["masked_fraction"] == 0.0

"""Unit tests for sequence retrieval input parsing and validation.

Tests cover:
- Pattern precedence: NCBI → Ensembl → coordinate → HGNC gene symbol
- NCBI accession patterns (NM_, NR_, XM_, XR_, NC_, NG_, NT_, NW_)
- Ensembl stable ID patterns (ENS + optional species prefix + G/T/E/P + 11 digits)
- Genomic coordinate patterns (chr[N]:[start]-[end])
- HGNC gene symbol recognition (1-40 alphanumeric + hyphens)
- Validation errors for unrecognized formats
- Max 50 queries per request
- Input string max 256 chars, whitespace trimming
"""

import pytest

from primerforge.engine.sequence_retrieval import (
    MAX_INPUT_LENGTH,
    MAX_QUERIES_PER_REQUEST,
    InputParseResult,
    ValidationError,
    classify_input,
    detect_source,
    parse_queries,
    validate_batch,
    validate_input,
)


# ═══════════════════════════════════════════════════════════════════════════
# NCBI ACCESSION PATTERN TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestNCBIPatterns:
    """NCBI accession patterns: NM_, NR_, XM_, XR_, NC_, NG_, NT_, NW_ + digits + optional .version."""

    @pytest.mark.parametrize("accession", [
        "NM_001301717",
        "NM_001301717.2",
        "NR_046018.2",
        "XM_017001507.2",
        "XR_001755205.1",
        "NC_000017.11",
        "NG_005905.2",
        "NT_167187.1",
        "NW_003315952.2",
    ])
    def test_valid_ncbi_accessions(self, accession):
        result = classify_input(accession)
        assert result.input_type == "ncbi_accession"
        assert result.source == "ncbi"
        assert result.error is None

    @pytest.mark.parametrize("accession", [
        "nm_001301717.2",  # lowercase
        "Nm_001301717",    # mixed case
    ])
    def test_ncbi_case_insensitive(self, accession):
        result = classify_input(accession)
        assert result.input_type == "ncbi_accession"
        assert result.source == "ncbi"

    def test_ncbi_without_version(self):
        result = classify_input("NM_007294")
        assert result.input_type == "ncbi_accession"
        assert result.source == "ncbi"

    def test_ncbi_with_version(self):
        result = classify_input("NM_007294.4")
        assert result.input_type == "ncbi_accession"
        assert result.source == "ncbi"

    def test_ncbi_takes_precedence_over_gene_symbol(self):
        """NCBI accession should be recognized before gene symbol fallback."""
        result = classify_input("NM_001301717")
        assert result.input_type == "ncbi_accession"
        assert result.source == "ncbi"


# ═══════════════════════════════════════════════════════════════════════════
# ENSEMBL PATTERN TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestEnsemblPatterns:
    """Ensembl stable IDs: ENS + optional species prefix + G/T/E/P + 11 digits."""

    @pytest.mark.parametrize("ensembl_id", [
        "ENSG00000141510",     # human gene
        "ENST00000269305",     # human transcript
        "ENSE00000936617",     # human exon
        "ENSP00000269305",     # human protein
        "ENSMUSG00000059552",  # mouse gene (species prefix MUS)
        "ENSDARG00000024894",  # zebrafish (species prefix DAR)
    ])
    def test_valid_ensembl_ids(self, ensembl_id):
        result = classify_input(ensembl_id)
        assert result.input_type == "ensembl_id"
        assert result.source == "ensembl"
        assert result.error is None

    def test_ensembl_with_version(self):
        result = classify_input("ENSG00000141510.17")
        assert result.input_type == "ensembl_id"
        assert result.source == "ensembl"

    def test_ensembl_case_insensitive(self):
        result = classify_input("ensg00000141510")
        assert result.input_type == "ensembl_id"
        assert result.source == "ensembl"

    def test_ensembl_wrong_digit_count(self):
        """Ensembl IDs need exactly 11 digits."""
        result = classify_input("ENSG0000014151")  # 10 digits
        # Should not match as ensembl_id (falls through to gene symbol or invalid)
        assert result.input_type != "ensembl_id"


# ═══════════════════════════════════════════════════════════════════════════
# GENOMIC COORDINATE PATTERN TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestCoordinatePatterns:
    """Genomic coordinates: chr[N]:[start]-[end]."""

    @pytest.mark.parametrize("coord", [
        "chr1:100-200",
        "chr17:43044295-43125364",
        "chr22:1000000-2000000",
        "chrX:15560138-15602945",
        "chrY:2654896-2655740",
        "chrM:1-16569",
        "chrMT:100-500",
    ])
    def test_valid_coordinates(self, coord):
        result = classify_input(coord)
        assert result.input_type == "genomic_coordinate"
        assert result.source == "ensembl_region"
        assert result.error is None

    def test_coordinate_case_insensitive(self):
        result = classify_input("CHR17:100-200")
        assert result.input_type == "genomic_coordinate"
        assert result.source == "ensembl_region"

    def test_coordinate_start_greater_than_end(self):
        """start must be < end."""
        result = classify_input("chr1:500-100")
        assert result.input_type == "invalid"
        assert "start" in result.error and "end" in result.error

    def test_coordinate_start_equals_end(self):
        """start must be < end."""
        result = classify_input("chr1:100-100")
        assert result.input_type == "invalid"

    def test_invalid_chromosome(self):
        """chr23 is not a valid chromosome."""
        result = classify_input("chr23:100-200")
        assert result.input_type != "genomic_coordinate"

    def test_chromosome_zero_invalid(self):
        """chr0 is not valid."""
        result = classify_input("chr0:100-200")
        assert result.input_type != "genomic_coordinate"


# ═══════════════════════════════════════════════════════════════════════════
# HGNC GENE SYMBOL PATTERN TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestGeneSymbolPatterns:
    """HGNC gene symbols: 1-40 alphanumeric chars + hyphens."""

    @pytest.mark.parametrize("symbol", [
        "BRCA1",
        "TP53",
        "EGFR",
        "HER2",
        "KRAS",
        "MYC",
        "APC",
        "CDKN2A",
        "HLA-A",
        "HLA-DRB1",
        "C9orf72",
        "A",
    ])
    def test_valid_gene_symbols(self, symbol):
        result = classify_input(symbol)
        assert result.input_type == "gene_symbol"
        assert result.source == "ncbi_gene"
        assert result.error is None

    def test_gene_symbol_with_hyphens(self):
        result = classify_input("HLA-DRB1")
        assert result.input_type == "gene_symbol"
        assert result.source == "ncbi_gene"

    def test_gene_symbol_max_length(self):
        """40 characters is the max."""
        symbol = "A" * 40
        result = classify_input(symbol)
        assert result.input_type == "gene_symbol"

    def test_gene_symbol_too_long(self):
        """41 characters exceeds limit."""
        symbol = "A" * 41
        result = classify_input(symbol)
        assert result.input_type == "invalid"

    def test_gene_symbol_cannot_start_with_hyphen(self):
        """Hyphens not allowed at start."""
        result = classify_input("-BRCA1")
        assert result.input_type == "invalid"

    def test_gene_symbol_invalid_chars(self):
        """Special characters not allowed."""
        result = classify_input("BRCA1@2")
        assert result.input_type == "invalid"

    def test_gene_symbol_with_spaces(self):
        """Spaces not allowed."""
        result = classify_input("BRCA 1")
        assert result.input_type == "invalid"


# ═══════════════════════════════════════════════════════════════════════════
# PATTERN PRECEDENCE TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestPatternPrecedence:
    """Verify NCBI → Ensembl → coordinate → gene symbol precedence."""

    def test_ncbi_takes_precedence(self):
        """NM_ prefix should be classified as NCBI, not gene symbol."""
        result = classify_input("NM_007294")
        assert result.input_type == "ncbi_accession"
        assert result.source == "ncbi"

    def test_ensembl_before_gene_symbol(self):
        """Ensembl ID should not fall through to gene symbol."""
        result = classify_input("ENSG00000141510")
        assert result.input_type == "ensembl_id"
        assert result.source == "ensembl"

    def test_coordinate_before_gene_symbol(self):
        """Coordinate format should not be treated as gene symbol."""
        result = classify_input("chr17:100-200")
        assert result.input_type == "genomic_coordinate"
        assert result.source == "ensembl_region"

    def test_gene_symbol_is_last_resort(self):
        """Simple alpha string without other pattern match → gene symbol."""
        result = classify_input("BRCA1")
        assert result.input_type == "gene_symbol"
        assert result.source == "ncbi_gene"


# ═══════════════════════════════════════════════════════════════════════════
# INPUT VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestInputValidation:
    """Tests for validate_input()."""

    def test_trims_whitespace(self):
        trimmed, error = validate_input("  NM_007294  ")
        assert trimmed == "NM_007294"
        assert error is None

    def test_trims_tabs_and_newlines(self):
        trimmed, error = validate_input("\t NM_007294 \n")
        assert trimmed == "NM_007294"
        assert error is None

    def test_empty_string_error(self):
        trimmed, error = validate_input("")
        assert error is not None
        assert "non-empty" in error

    def test_whitespace_only_error(self):
        trimmed, error = validate_input("   ")
        assert error is not None
        assert "empty after trimming" in error

    def test_none_error(self):
        trimmed, error = validate_input(None)
        assert error is not None

    def test_max_length_exact(self):
        query = "A" * MAX_INPUT_LENGTH
        trimmed, error = validate_input(query)
        assert error is None
        assert len(trimmed) == MAX_INPUT_LENGTH

    def test_exceeds_max_length(self):
        query = "A" * (MAX_INPUT_LENGTH + 1)
        trimmed, error = validate_input(query)
        assert error is not None
        assert "exceeds maximum length" in error
        assert str(MAX_INPUT_LENGTH) in error


# ═══════════════════════════════════════════════════════════════════════════
# BATCH VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestBatchValidation:
    """Tests for validate_batch()."""

    def test_empty_list_error(self):
        valid, errors = validate_batch([])
        assert len(errors) == 1
        assert "No queries" in errors[0].error

    def test_exceeds_max_queries(self):
        queries = ["BRCA1"] * (MAX_QUERIES_PER_REQUEST + 1)
        valid, errors = validate_batch(queries)
        assert len(errors) == 1
        assert "Too many queries" in errors[0].error
        assert str(MAX_QUERIES_PER_REQUEST) in errors[0].error

    def test_exactly_max_queries(self):
        queries = ["BRCA1"] * MAX_QUERIES_PER_REQUEST
        valid, errors = validate_batch(queries)
        assert len(valid) == MAX_QUERIES_PER_REQUEST
        assert len(errors) == 0

    def test_mixed_valid_and_invalid(self):
        queries = ["NM_007294", "", "BRCA1"]
        valid, errors = validate_batch(queries)
        assert len(valid) == 2
        assert len(errors) == 1

    def test_all_valid(self):
        queries = ["NM_007294.4", "ENSG00000141510", "chr17:100-200", "TP53"]
        valid, errors = validate_batch(queries)
        assert len(valid) == 4
        assert len(errors) == 0

    def test_whitespace_trimmed(self):
        queries = ["  NM_007294  ", "\tTP53\n"]
        valid, errors = validate_batch(queries)
        assert valid == ["NM_007294", "TP53"]
        assert len(errors) == 0


# ═══════════════════════════════════════════════════════════════════════════
# PARSE QUERIES TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestParseQueries:
    """Tests for parse_queries() — full parsing pipeline."""

    def test_mixed_input_types(self):
        queries = [
            "NM_007294.4",        # NCBI
            "ENSG00000141510",    # Ensembl
            "chr17:43044295-43125364",  # Coordinate
            "BRCA1",             # Gene symbol
        ]
        results, errors = parse_queries(queries)
        assert len(results) == 4
        assert len(errors) == 0

        assert results[0].input_type == "ncbi_accession"
        assert results[1].input_type == "ensembl_id"
        assert results[2].input_type == "genomic_coordinate"
        assert results[3].input_type == "gene_symbol"

    def test_invalid_queries_produce_errors(self):
        queries = ["!!invalid!!", "BRCA1"]
        results, errors = parse_queries(queries)
        assert len(results) == 1
        assert results[0].input_type == "gene_symbol"
        assert len(errors) == 1
        assert "Unrecognized" in errors[0].error

    def test_restricted_viral_identifier_rejected(self):
        queries = ["EPI_ISL_402124"]
        results, errors = parse_queries(queries)
        assert len(results) == 0
        assert len(errors) == 1

    def test_batch_limit_enforced(self):
        queries = ["BRCA1"] * 51
        results, errors = parse_queries(queries)
        assert len(results) == 0
        assert len(errors) == 1
        assert "Too many queries" in errors[0].error


# ═══════════════════════════════════════════════════════════════════════════
# DETECT SOURCE (LEGACY INTERFACE) TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestDetectSource:
    """Tests for detect_source() — backward-compatible interface."""

    def test_ncbi_accession(self):
        assert detect_source("NM_007294.4") == "ncbi"

    def test_ensembl_id(self):
        assert detect_source("ENSG00000141510") == "ensembl"

    def test_ensembl_region_coordinate(self):
        assert detect_source("chr17:100-200") == "ensembl_region"

    def test_restricted_viral_identifier_not_auto_detected(self):
        assert detect_source("EPI_ISL_402124") is None

    def test_gene_symbol_fallback(self):
        assert detect_source("BRCA1") == "ncbi_gene"

    def test_unrecognized_returns_none(self):
        assert detect_source("!!invalid!!") is None

    def test_whitespace_trimmed(self):
        assert detect_source("  NM_007294  ") == "ncbi"


# ═══════════════════════════════════════════════════════════════════════════
# UNRECOGNIZED FORMAT ERROR TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestUnrecognizedFormats:
    """Tests for proper error reporting on unrecognized inputs."""

    @pytest.mark.parametrize("invalid_input", [
        "!!invalid!!",
        "@#$%^&",
        "chr23:100-200",  # invalid chromosome
        "",
        "A" * 41,  # too long for gene symbol
    ])
    def test_invalid_inputs_classified_as_invalid(self, invalid_input):
        if invalid_input == "":
            # Empty string handled at validation level
            trimmed, error = validate_input(invalid_input)
            assert error is not None
        else:
            result = classify_input(invalid_input)
            assert result.input_type == "invalid"

    def test_error_message_lists_supported_formats(self):
        result = classify_input("@#$%^&*")
        assert result.input_type == "invalid"
        assert "Supported formats" in result.error


# ═══════════════════════════════════════════════════════════════════════════
# FETCH_SEQUENCE VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestFetchSequenceValidation:
    """Tests for fetch_sequence() input validation (no network calls)."""

    def test_empty_query_raises(self):
        from primerforge.engine.sequence_retrieval import fetch_sequence
        with pytest.raises(ValueError, match="non-empty"):
            fetch_sequence("")

    def test_too_long_query_raises(self):
        from primerforge.engine.sequence_retrieval import fetch_sequence
        with pytest.raises(ValueError, match="exceeds maximum length"):
            fetch_sequence("A" * 257)

    def test_unrecognized_format_raises(self):
        from primerforge.engine.sequence_retrieval import fetch_sequence
        with pytest.raises(ValueError, match="does not match any recognized format"):
            fetch_sequence("@#$%^&*")

    def test_unknown_source_raises(self):
        from primerforge.engine.sequence_retrieval import fetch_sequence
        with pytest.raises(ValueError, match="Unknown source"):
            fetch_sequence("BRCA1", source="nonexistent_db")

"""Unit tests for open NCBI Virus routing in sequence_retrieval.py."""

from unittest.mock import patch

import pytest

from primerforge.engine.sequence_retrieval import (
    SequenceRecord,
    _FETCHER_MAP,
    _SOURCE_PATTERNS,
    detect_source,
    fetch_from_ncbi_virus,
    fetch_sequence,
)


class TestNCBIVirusRouting:
    def test_explicit_ncbi_virus_fetcher_in_map(self):
        assert "ncbi_virus" in _FETCHER_MAP
        assert _FETCHER_MAP["ncbi_virus"] is fetch_from_ncbi_virus

    def test_restricted_viral_identifier_not_detected(self):
        assert detect_source("EPI_ISL_402124") is None
        assert all(source != "restricted_viral" for _, source in _SOURCE_PATTERNS)

    def test_ncbi_virus_wrapper_marks_source(self):
        base = SequenceRecord(
            id="NC_045512.2",
            source="ncbi",
            accession="NC_045512.2",
            sequence="ATCG",
            description="SARS-CoV-2 isolate Wuhan-Hu-1",
            length=4,
            metadata={"organism": "Severe acute respiratory syndrome coronavirus 2"},
        )
        with patch("primerforge.engine.sequence_retrieval.fetch_from_ncbi", return_value=base):
            result = fetch_from_ncbi_virus("NC_045512.2")

        assert result.source == "ncbi_virus"
        assert result.metadata["collection"] == "NCBI Virus"
        assert result.metadata["api"] == "ncbi_nucleotide"

    def test_fetch_sequence_explicit_ncbi_virus(self):
        base = SequenceRecord(
            id="NC_045512.2",
            source="ncbi",
            accession="NC_045512.2",
            sequence="ATCG",
        )
        with patch("primerforge.engine.sequence_retrieval.fetch_from_ncbi", return_value=base):
            result = fetch_sequence("NC_045512.2", source="ncbi_virus")

        assert result.source == "ncbi_virus"

    def test_unknown_restricted_source_raises(self):
        with pytest.raises(ValueError, match="Cannot auto-detect source"):
            fetch_sequence("EPI_ISL_402124")

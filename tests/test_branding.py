"""Unit tests for the VigyanLLM branding module."""

import pytest

from primerforge.engine.branding import (
    LEGACY_PREFIXES,
    ORDER_PREFIX,
    SYSTEM_BRAND,
    brand_error,
    brand_response,
    generate_order_id,
)


class TestConstants:
    """Verify brand constants are correctly defined."""

    def test_system_brand_value(self):
        assert SYSTEM_BRAND == "VigyanLLM"

    def test_order_prefix_value(self):
        assert ORDER_PREFIX == "VL-"

    def test_legacy_prefixes(self):
        assert "PF-" in LEGACY_PREFIXES
        assert "Glixtron" in LEGACY_PREFIXES
        assert "PrimerForge" in LEGACY_PREFIXES


class TestBrandResponse:
    """Tests for brand_response()."""

    def test_injects_system_key(self):
        response = {"data": [1, 2, 3]}
        result = brand_response(response)
        assert result["system"] == "VigyanLLM"

    def test_preserves_existing_keys(self):
        response = {"status": "ok", "count": 5, "items": ["a", "b"]}
        result = brand_response(response)
        assert result["status"] == "ok"
        assert result["count"] == 5
        assert result["items"] == ["a", "b"]
        assert result["system"] == "VigyanLLM"

    def test_empty_dict(self):
        response = {}
        result = brand_response(response)
        assert result == {"system": "VigyanLLM"}

    def test_overwrites_existing_system_key(self):
        response = {"system": "OldBrand"}
        result = brand_response(response)
        assert result["system"] == "VigyanLLM"

    def test_returns_same_dict_reference(self):
        response = {"key": "value"}
        result = brand_response(response)
        assert result is response


class TestBrandError:
    """Tests for brand_error()."""

    def test_prefixes_message(self):
        result = brand_error("Something went wrong")
        assert result == "VigyanLLM: Something went wrong"

    def test_empty_message(self):
        result = brand_error("")
        assert result == "VigyanLLM: "

    def test_message_with_special_chars(self):
        result = brand_error("Error: file 'x.txt' not found (code 404)")
        assert result == "VigyanLLM: Error: file 'x.txt' not found (code 404)"


class TestGenerateOrderId:
    """Tests for generate_order_id()."""

    def test_basic_format(self):
        result = generate_order_id("20240115T103000", 1)
        assert result == "VL-20240115T103000-0001"

    def test_starts_with_vl_prefix(self):
        result = generate_order_id("20240101", 42)
        assert result.startswith("VL-")

    def test_seq_number_zero_padded(self):
        result = generate_order_id("20240115", 7)
        assert result == "VL-20240115-0007"

    def test_seq_number_large(self):
        result = generate_order_id("20240115", 9999)
        assert result == "VL-20240115-9999"

    def test_seq_number_exceeds_four_digits(self):
        # Still formats correctly, just wider than 4 digits
        result = generate_order_id("20240115", 10000)
        assert result == "VL-20240115-10000"

    def test_preserves_timestamp(self):
        timestamp = "20240601T235959"
        result = generate_order_id(timestamp, 3)
        assert timestamp in result

    def test_preserves_seq_number(self):
        result = generate_order_id("20240115", 123)
        assert "0123" in result

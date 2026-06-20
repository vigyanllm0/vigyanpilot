"""
Unit tests for the Order Serializer module.

Validates Requirements 28.1–28.7: IDT/Twist payload generation,
compliance enforcement, scale assignment, length limits, and probe fields.
"""

import os

os.environ.setdefault("PRIMERFORGE_SECRET", "unit-test-secret-for-route-import")

import pytest

from primerforge.engine.order_serializer import (
    DEFAULT_SCALE,
    IDT_MAX_LENGTH,
    MAX_OLIGOS_PER_PAYLOAD,
    TWIST_MAX_LENGTH,
    OrderSerializer,
    ValidatedDesign,
)
from primerforge.engine.pipeline_routes import (
    _normalise_order_pair,
    _normalise_order_probe,
)


@pytest.fixture
def serializer():
    return OrderSerializer()


@pytest.fixture
def cleared_design():
    """A minimal biosecurity-cleared design with one primer pair."""
    return ValidatedDesign(
        job_id="job-abc-123",
        compliance_status="biosecurity_cleared",
        primer_pairs=[
            {
                "forward": {"name": "FWD1", "sequence": "ATCGATCGATCGATCGATCG"},
                "reverse": {"name": "REV1", "sequence": "GCTAGCTAGCTAGCTAGCTA"},
            }
        ],
        probes=[],
        application_type="standard_pcr",
    )


@pytest.fixture
def design_with_probe():
    """A cleared design including a dual-labeled probe."""
    return ValidatedDesign(
        job_id="job-probe-001",
        compliance_status="biosecurity_cleared",
        primer_pairs=[
            {
                "forward": {"name": "FWD1", "sequence": "ATCGATCGATCGATCGATCG"},
                "reverse": {"name": "REV1", "sequence": "GCTAGCTAGCTAGCTAGCTA"},
            }
        ],
        probes=[
            {
                "name": "PROBE1",
                "sequence": "ATCGATCGATCGATCGATCGATCG",
                "5_prime_modification": "FAM",
                "3_prime_modification": "BHQ-1",
                "dye_specification": "FAM/BHQ-1",
            }
        ],
        application_type="standard_pcr",
    )


class TestComplianceEnforcement:
    """Requirement 28.6: Refuse serialization if not biosecurity_cleared."""

    def test_idt_refuses_biosecurity_hold(self, serializer):
        design = ValidatedDesign(
            job_id="job-hold",
            compliance_status="biosecurity_hold",
            primer_pairs=[],
        )
        with pytest.raises(ValueError, match="compliance"):
            serializer.serialize_idt(design)

    def test_twist_refuses_biosecurity_hold(self, serializer):
        design = ValidatedDesign(
            job_id="job-hold",
            compliance_status="biosecurity_hold",
            primer_pairs=[],
        )
        with pytest.raises(ValueError, match="compliance"):
            serializer.serialize_twist(design)

    def test_refuses_compliance_unavailable(self, serializer):
        design = ValidatedDesign(
            job_id="job-unavail",
            compliance_status="compliance_unavailable",
            primer_pairs=[],
        )
        with pytest.raises(ValueError):
            serializer.serialize_idt(design)

    def test_accepts_biosecurity_cleared(self, serializer, cleared_design):
        result = serializer.serialize_idt(cleared_design)
        assert result["oligo_count"] == 2


class TestIDTSerialization:
    """Requirement 28.1: IDT bulk order schema."""

    def test_idt_payload_has_required_fields(self, serializer, cleared_design):
        result = serializer.serialize_idt(cleared_design)
        oligo = result["oligos"][0]
        assert "Name" in oligo
        assert "Sequence" in oligo
        assert "Scale" in oligo
        assert "Purification" in oligo

    def test_idt_order_id_has_vl_prefix(self, serializer, cleared_design):
        result = serializer.serialize_idt(cleared_design)
        assert result["order_id"].startswith("VL-")

    def test_idt_vendor_field(self, serializer, cleared_design):
        result = serializer.serialize_idt(cleared_design)
        assert result["vendor"] == "idt"

    def test_idt_oligo_count(self, serializer, cleared_design):
        result = serializer.serialize_idt(cleared_design)
        assert result["oligo_count"] == 2  # forward + reverse


class TestTwistSerialization:
    """Requirement 28.2: Twist Bioscience order schema."""

    def test_twist_payload_has_required_fields(self, serializer, cleared_design):
        result = serializer.serialize_twist(cleared_design)
        oligo = result["oligos"][0]
        assert "name" in oligo
        assert "sequence" in oligo
        assert "length" in oligo
        assert "purification_type" in oligo

    def test_twist_length_field_matches_sequence(self, serializer, cleared_design):
        result = serializer.serialize_twist(cleared_design)
        oligo = result["oligos"][0]
        assert oligo["length"] == len(oligo["sequence"])

    def test_twist_order_id_has_vl_prefix(self, serializer, cleared_design):
        result = serializer.serialize_twist(cleared_design)
        assert result["order_id"].startswith("VL-")

    def test_twist_vendor_field(self, serializer, cleared_design):
        result = serializer.serialize_twist(cleared_design)
        assert result["vendor"] == "twist"


class TestPipelineOrderNormalisation:
    """Pipeline ranked-pair output can be converted to vendor order shape."""

    def test_ranked_pair_normalises_for_order_serialization(self):
        ranked = {
            "pair_id": 3,
            "forward_primer": {"sequence": "ATCGATCGATCGATCGATCG"},
            "reverse_primer": {"sequence": "GCTAGCTAGCTAGCTAGCTA"},
        }

        pair = _normalise_order_pair(ranked, 0)

        assert pair["forward"]["name"] == "VL_3_FWD"
        assert pair["forward"]["sequence"] == "ATCGATCGATCGATCGATCG"
        assert pair["reverse"]["name"] == "VL_3_REV"
        assert pair["reverse"]["sequence"] == "GCTAGCTAGCTAGCTAGCTA"

    def test_probe_normalises_default_dye_labels(self):
        probe = _normalise_order_probe({"sequence": "ATCGATCGATCG"}, 0)

        assert probe["name"] == "VL_PROBE_1"
        assert probe["5_prime_modification"] == "FAM"
        assert probe["3_prime_modification"] == "BHQ-1"
        assert probe["dye_specification"] == "FAM/BHQ-1"


class TestProbeInclusion:
    """Requirement 28.3: Probes with modification fields."""

    def test_idt_includes_probe_modifications(self, serializer, design_with_probe):
        result = serializer.serialize_idt(design_with_probe)
        probe = result["oligos"][2]  # third oligo is the probe
        assert probe["5_prime_modification"] == "FAM"
        assert probe["3_prime_modification"] == "BHQ-1"
        assert probe["dye_specification"] == "FAM/BHQ-1"

    def test_twist_includes_probe_modifications(self, serializer, design_with_probe):
        result = serializer.serialize_twist(design_with_probe)
        probe = result["oligos"][2]
        assert probe["5_prime_modification"] == "FAM"
        assert probe["3_prime_modification"] == "BHQ-1"
        assert probe["dye_specification"] == "FAM/BHQ-1"

    def test_probe_counted_in_oligo_total(self, serializer, design_with_probe):
        result = serializer.serialize_idt(design_with_probe)
        assert result["oligo_count"] == 3  # 2 primers + 1 probe


class TestScaleAssignment:
    """Requirements 28.4, 28.5: Scale by application type."""

    def test_standard_pcr_25nmol(self, serializer):
        design = ValidatedDesign(
            job_id="j1",
            compliance_status="biosecurity_cleared",
            primer_pairs=[{"forward": {"name": "F", "sequence": "A" * 20}, "reverse": {"name": "R", "sequence": "T" * 20}}],
            application_type="standard_pcr",
        )
        result = serializer.serialize_idt(design)
        assert result["scale"] == "25nmol"

    def test_high_throughput_100nmol(self, serializer):
        design = ValidatedDesign(
            job_id="j2",
            compliance_status="biosecurity_cleared",
            primer_pairs=[{"forward": {"name": "F", "sequence": "A" * 20}, "reverse": {"name": "R", "sequence": "T" * 20}}],
            application_type="high_throughput",
        )
        result = serializer.serialize_idt(design)
        assert result["scale"] == "100nmol"

    def test_clinical_250nmol(self, serializer):
        design = ValidatedDesign(
            job_id="j3",
            compliance_status="biosecurity_cleared",
            primer_pairs=[{"forward": {"name": "F", "sequence": "A" * 20}, "reverse": {"name": "R", "sequence": "T" * 20}}],
            application_type="clinical",
        )
        result = serializer.serialize_idt(design)
        assert result["scale"] == "250nmol"

    def test_unrecognized_defaults_to_25nmol(self, serializer):
        design = ValidatedDesign(
            job_id="j4",
            compliance_status="biosecurity_cleared",
            primer_pairs=[{"forward": {"name": "F", "sequence": "A" * 20}, "reverse": {"name": "R", "sequence": "T" * 20}}],
            application_type="exotic_application",
        )
        result = serializer.serialize_idt(design)
        assert result["scale"] == "25nmol"
        assert "notes" in result
        assert any("defaulted" in n.lower() for n in result["notes"])


class TestLengthEnforcement:
    """Requirement 28.7: IDT max 200nt, Twist max 300nt."""

    def test_idt_excludes_over_200nt(self, serializer):
        design = ValidatedDesign(
            job_id="j5",
            compliance_status="biosecurity_cleared",
            primer_pairs=[
                {
                    "forward": {"name": "LONG", "sequence": "A" * 201},
                    "reverse": {"name": "OK", "sequence": "T" * 20},
                }
            ],
        )
        result = serializer.serialize_idt(design)
        assert result["oligo_count"] == 1
        assert len(result["errors"]) == 1
        assert "200" in result["errors"][0]["error"]

    def test_idt_allows_exactly_200nt(self, serializer):
        design = ValidatedDesign(
            job_id="j6",
            compliance_status="biosecurity_cleared",
            primer_pairs=[
                {
                    "forward": {"name": "EXACT", "sequence": "A" * 200},
                    "reverse": {"name": "OK", "sequence": "T" * 20},
                }
            ],
        )
        result = serializer.serialize_idt(design)
        assert result["oligo_count"] == 2
        assert len(result["errors"]) == 0

    def test_twist_excludes_over_300nt(self, serializer):
        design = ValidatedDesign(
            job_id="j7",
            compliance_status="biosecurity_cleared",
            primer_pairs=[
                {
                    "forward": {"name": "LONG", "sequence": "A" * 301},
                    "reverse": {"name": "OK", "sequence": "T" * 20},
                }
            ],
        )
        result = serializer.serialize_twist(design)
        assert result["oligo_count"] == 1
        assert len(result["errors"]) == 1
        assert "300" in result["errors"][0]["error"]

    def test_twist_allows_exactly_300nt(self, serializer):
        design = ValidatedDesign(
            job_id="j8",
            compliance_status="biosecurity_cleared",
            primer_pairs=[
                {
                    "forward": {"name": "EXACT", "sequence": "A" * 300},
                    "reverse": {"name": "OK", "sequence": "T" * 20},
                }
            ],
        )
        result = serializer.serialize_twist(design)
        assert result["oligo_count"] == 2
        assert len(result["errors"]) == 0


class TestMaxOligosLimit:
    """Requirements 28.1, 28.2: Max 96 oligos per payload."""

    def test_idt_caps_at_96(self, serializer):
        pairs = [
            {"forward": {"name": f"F{i}", "sequence": "ATCG" * 5}, "reverse": {"name": f"R{i}", "sequence": "GCTA" * 5}}
            for i in range(50)  # 100 oligos total
        ]
        design = ValidatedDesign(
            job_id="j9",
            compliance_status="biosecurity_cleared",
            primer_pairs=pairs,
        )
        result = serializer.serialize_idt(design)
        assert result["oligo_count"] == MAX_OLIGOS_PER_PAYLOAD
        assert len(result["errors"]) == 4

    def test_twist_caps_at_96(self, serializer):
        pairs = [
            {"forward": {"name": f"F{i}", "sequence": "ATCG" * 5}, "reverse": {"name": f"R{i}", "sequence": "GCTA" * 5}}
            for i in range(50)
        ]
        design = ValidatedDesign(
            job_id="j10",
            compliance_status="biosecurity_cleared",
            primer_pairs=pairs,
        )
        result = serializer.serialize_twist(design)
        assert result["oligo_count"] == MAX_OLIGOS_PER_PAYLOAD
        assert len(result["errors"]) == 4

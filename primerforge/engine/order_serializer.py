"""
VigyanLLM Order Serializer Module
==================================
Formats validated primer/probe designs into IDT and Twist Bioscience
API-compatible order payloads for direct synthesis ordering.

Requirements: 28.1, 28.2, 28.3, 28.4, 28.5, 28.6, 28.7
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from primerforge.engine.branding import generate_order_id


# Maximum oligos per vendor payload (Requirements 28.1, 28.2)
MAX_OLIGOS_PER_PAYLOAD: int = 96

# Vendor length limits in nucleotides (Requirement 28.7)
IDT_MAX_LENGTH: int = 200
TWIST_MAX_LENGTH: int = 300

# Scale mapping by application type (Requirement 28.4)
SCALE_MAP: Dict[str, str] = {
    "standard_pcr": "25nmol",
    "standard": "25nmol",
    "high_throughput": "100nmol",
    "high-throughput": "100nmol",
    "clinical": "250nmol",
    "diagnostic": "250nmol",
}

# Default scale when application type is unrecognized (Requirement 28.5)
DEFAULT_SCALE: str = "25nmol"


@dataclass
class ValidatedDesign:
    """A primer/probe design that has passed compliance screening.

    Attributes:
        job_id: Unique pipeline job identifier.
        compliance_status: Must be "biosecurity_cleared" for serialization.
        primer_pairs: List of primer pair dicts, each containing at minimum
            'forward' and 'reverse' keys with 'name' and 'sequence' sub-keys.
        probes: List of probe dicts with 'name', 'sequence',
            '5_prime_modification', '3_prime_modification', 'dye_specification'.
        application_type: Primer application type determining synthesis scale.
    """

    job_id: str
    compliance_status: str
    primer_pairs: List[Dict[str, Any]]
    probes: List[Dict[str, Any]] = field(default_factory=list)
    application_type: str = "standard_pcr"


class OrderSerializer:
    """Formats validated designs into IDT/Twist API payloads.

    The serializer enforces biosecurity compliance checks before generating
    any order payload. Designs without 'biosecurity_cleared' status are
    refused (Requirement 28.6).
    """

    def serialize_idt(self, design: ValidatedDesign) -> Dict[str, Any]:
        """Generate IDT bulk order payload.

        Fields per oligo: Name, Sequence, Scale, Purification.
        Max 96 oligos per payload (Requirement 28.1).

        Args:
            design: A validated design with biosecurity clearance.

        Returns:
            Dict with 'order_id', 'vendor', 'oligos', 'errors', 'scale',
            'oligo_count', and optionally 'notes'.

        Raises:
            ValueError: If compliance_status is not 'biosecurity_cleared'.
        """
        self._enforce_compliance(design)

        scale = self._assign_scale(design.application_type)
        oligos: List[Dict[str, str]] = []
        errors: List[Dict[str, str]] = []
        notes: List[str] = []

        if scale == DEFAULT_SCALE and design.application_type not in SCALE_MAP:
            notes.append(
                f"Application type '{design.application_type}' not recognized; "
                f"defaulted to {DEFAULT_SCALE} scale."
            )

        # Serialize primer pairs
        for pair in design.primer_pairs:
            for direction in ("forward", "reverse"):
                primer = pair.get(direction, {})
                name = primer.get("name", "")
                sequence = primer.get("sequence", "")

                valid, err_msg = self._validate_length(sequence, "idt")
                if not valid:
                    errors.append({"name": name, "error": err_msg})
                    continue

                if len(oligos) >= MAX_OLIGOS_PER_PAYLOAD:
                    errors.append({
                        "name": name,
                        "error": f"Exceeded maximum of {MAX_OLIGOS_PER_PAYLOAD} oligos per payload."
                    })
                    continue

                oligos.append({
                    "Name": name,
                    "Sequence": sequence,
                    "Scale": scale,
                    "Purification": self._recommend_purification_idt(primer),
                })

        # Serialize probes (Requirement 28.3)
        for probe in design.probes:
            name = probe.get("name", "")
            sequence = probe.get("sequence", "")

            valid, err_msg = self._validate_length(sequence, "idt")
            if not valid:
                errors.append({"name": name, "error": err_msg})
                continue

            if len(oligos) >= MAX_OLIGOS_PER_PAYLOAD:
                errors.append({
                    "name": name,
                    "error": f"Exceeded maximum of {MAX_OLIGOS_PER_PAYLOAD} oligos per payload."
                })
                continue

            oligos.append({
                "Name": name,
                "Sequence": sequence,
                "Scale": scale,
                "Purification": "HPLC",
                "5_prime_modification": probe.get("5_prime_modification", ""),
                "3_prime_modification": probe.get("3_prime_modification", ""),
                "dye_specification": probe.get("dye_specification", ""),
            })

        order_id = self._generate_order_id(design.job_id)

        result: Dict[str, Any] = {
            "order_id": order_id,
            "vendor": "idt",
            "oligos": oligos,
            "oligo_count": len(oligos),
            "scale": scale,
            "errors": errors,
        }
        if notes:
            result["notes"] = notes

        return result

    def serialize_twist(self, design: ValidatedDesign) -> Dict[str, Any]:
        """Generate Twist Bioscience order payload.

        Fields per oligo: name, sequence, length, purification_type.
        Max 96 oligos per payload (Requirement 28.2).

        Args:
            design: A validated design with biosecurity clearance.

        Returns:
            Dict with 'order_id', 'vendor', 'oligos', 'errors', 'scale',
            'oligo_count', and optionally 'notes'.

        Raises:
            ValueError: If compliance_status is not 'biosecurity_cleared'.
        """
        self._enforce_compliance(design)

        scale = self._assign_scale(design.application_type)
        oligos: List[Dict[str, Any]] = []
        errors: List[Dict[str, str]] = []
        notes: List[str] = []

        if scale == DEFAULT_SCALE and design.application_type not in SCALE_MAP:
            notes.append(
                f"Application type '{design.application_type}' not recognized; "
                f"defaulted to {DEFAULT_SCALE} scale."
            )

        # Serialize primer pairs
        for pair in design.primer_pairs:
            for direction in ("forward", "reverse"):
                primer = pair.get(direction, {})
                name = primer.get("name", "")
                sequence = primer.get("sequence", "")

                valid, err_msg = self._validate_length(sequence, "twist")
                if not valid:
                    errors.append({"name": name, "error": err_msg})
                    continue

                if len(oligos) >= MAX_OLIGOS_PER_PAYLOAD:
                    errors.append({
                        "name": name,
                        "error": f"Exceeded maximum of {MAX_OLIGOS_PER_PAYLOAD} oligos per payload."
                    })
                    continue

                oligos.append({
                    "name": name,
                    "sequence": sequence,
                    "length": len(sequence),
                    "purification_type": self._recommend_purification_twist(primer),
                })

        # Serialize probes (Requirement 28.3)
        for probe in design.probes:
            name = probe.get("name", "")
            sequence = probe.get("sequence", "")

            valid, err_msg = self._validate_length(sequence, "twist")
            if not valid:
                errors.append({"name": name, "error": err_msg})
                continue

            if len(oligos) >= MAX_OLIGOS_PER_PAYLOAD:
                errors.append({
                    "name": name,
                    "error": f"Exceeded maximum of {MAX_OLIGOS_PER_PAYLOAD} oligos per payload."
                })
                continue

            oligos.append({
                "name": name,
                "sequence": sequence,
                "length": len(sequence),
                "purification_type": "HPLC",
                "5_prime_modification": probe.get("5_prime_modification", ""),
                "3_prime_modification": probe.get("3_prime_modification", ""),
                "dye_specification": probe.get("dye_specification", ""),
            })

        order_id = self._generate_order_id(design.job_id)

        result: Dict[str, Any] = {
            "order_id": order_id,
            "vendor": "twist",
            "oligos": oligos,
            "oligo_count": len(oligos),
            "scale": scale,
            "errors": errors,
        }
        if notes:
            result["notes"] = notes

        return result

    def _enforce_compliance(self, design: ValidatedDesign) -> None:
        """Refuse to serialize if compliance_status != 'biosecurity_cleared'.

        Requirement 28.6: The serializer SHALL refuse to generate an order
        payload when the Compliance_Module has not cleared a design.

        Raises:
            ValueError: With message indicating compliance clearance is required.
        """
        if design.compliance_status != "biosecurity_cleared":
            raise ValueError(
                f"VigyanLLM: Order serialization refused — compliance status is "
                f"'{design.compliance_status}'. Biosecurity clearance is required "
                f"before generating order payloads."
            )

    def _assign_scale(self, application_type: str) -> str:
        """Assign synthesis scale based on application type.

        Requirement 28.4: 25nmol (standard), 100nmol (high-throughput),
        250nmol (clinical/diagnostic).
        Requirement 28.5: Default to 25nmol if unspecified or unrecognized.

        Args:
            application_type: The application type string.

        Returns:
            Scale string (e.g. '25nmol', '100nmol', '250nmol').
        """
        return SCALE_MAP.get(application_type, DEFAULT_SCALE)

    def _validate_length(self, sequence: str, vendor: str) -> Tuple[bool, str]:
        """Validate oligo sequence length against vendor limits.

        Requirement 28.7: IDT max 200nt, Twist max 300nt.

        Args:
            sequence: The oligonucleotide sequence.
            vendor: Either 'idt' or 'twist'.

        Returns:
            Tuple of (is_valid, error_message). error_message is empty if valid.
        """
        seq_len = len(sequence)

        if vendor == "idt":
            if seq_len > IDT_MAX_LENGTH:
                return (
                    False,
                    f"Sequence length {seq_len}nt exceeds IDT maximum of "
                    f"{IDT_MAX_LENGTH}nt.",
                )
        elif vendor == "twist":
            if seq_len > TWIST_MAX_LENGTH:
                return (
                    False,
                    f"Sequence length {seq_len}nt exceeds Twist maximum of "
                    f"{TWIST_MAX_LENGTH}nt.",
                )

        return (True, "")

    def _recommend_purification_idt(self, primer: Dict[str, Any]) -> str:
        """Recommend purification method for IDT orders.

        Uses PAGE for longer oligos or those flagged for purification;
        defaults to standard desalting.
        """
        if primer.get("purification_recommendation") == "HPLC":
            return "HPLC"
        if primer.get("purification_recommendation") == "PAGE":
            return "PAGE"
        seq = primer.get("sequence", "")
        if len(seq) > 60:
            return "PAGE"
        return "STD"

    def _recommend_purification_twist(self, primer: Dict[str, Any]) -> str:
        """Recommend purification type for Twist orders."""
        if primer.get("purification_recommendation") == "HPLC":
            return "HPLC"
        if primer.get("purification_recommendation") == "PAGE":
            return "PAGE"
        seq = primer.get("sequence", "")
        if len(seq) > 60:
            return "PAGE"
        return "STANDARD"

    def _generate_order_id(self, job_id: str) -> str:
        """Generate a VL- prefixed order ID using the branding module.

        Uses generate_order_id from primerforge.engine.branding to produce
        order IDs in VL-{timestamp}-{seq_number} format.

        Args:
            job_id: The pipeline job ID used as part of sequence numbering.

        Returns:
            A branded order ID string starting with 'VL-'.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        # Use hash of job_id to derive a sequence number for uniqueness
        seq_number = abs(hash(job_id)) % 10000
        return generate_order_id(timestamp, seq_number)

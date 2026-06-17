"""
VigyanLLM Branding Module
==========================
Centralizes brand identity constants and utility functions for consistent
branding across API responses, error messages, and order identifiers.
"""

from typing import Dict

# Brand constants
SYSTEM_BRAND: str = "VigyanLLM"
ORDER_PREFIX: str = "VL-"
LEGACY_PREFIXES: list = ["PF-", "Glixtron", "PrimerForge"]


def brand_response(response: Dict) -> Dict:
    """Inject 'system': 'VigyanLLM' into an API response dictionary.

    Adds the system brand identifier to the response while preserving
    all existing keys and values.

    Args:
        response: The API response dictionary to brand.

    Returns:
        The same dictionary with 'system' key set to 'VigyanLLM'.
    """
    response["system"] = SYSTEM_BRAND
    return response


def brand_error(message: str) -> str:
    """Prefix an error message with the VigyanLLM brand.

    Args:
        message: The error message to prefix.

    Returns:
        The message prefixed with 'VigyanLLM: '.
    """
    return f"{SYSTEM_BRAND}: {message}"


def generate_order_id(timestamp: str, seq_number: int) -> str:
    """Generate a branded order ID in VL-{timestamp}-{seq_number:04d} format.

    Args:
        timestamp: A timestamp string (e.g. '20240115T103000').
        seq_number: A sequence number to uniquely identify the order.

    Returns:
        A string like 'VL-20240115T103000-0001'.
    """
    return f"{ORDER_PREFIX}{timestamp}-{seq_number:04d}"

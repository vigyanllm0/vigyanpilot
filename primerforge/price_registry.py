#!/usr/bin/env python3
"""
VigyanLLM Price Registry — Disrupted Pricing Model
======================================================
Volume-optimized, India-market aggressive pricing.
COGS: ~₹2-5 per run. All tiers maintain 70%+ gross margins.

Tiers:
  - Free Trial: 2 free runs per new user
  - Individual: ₹2,499/mo → 250 designs
  - Institutional: ₹14,999/mo → 2,000 designs, 5 seats
  - Corporate: ₹49,999/mo → 7,500 designs, unlimited seats
  - Top-Up: ₹49 per single run (post-trial/overage)
"""

from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum


class ProductType(Enum):
    SUBSCRIPTION = "subscription"
    TOP_UP = "top_up"


@dataclass(frozen=True)
class ProductConfig:
    product_id: str
    display_name: str
    product_type: ProductType
    price_inr: int              # Exact INR (integer, no decimals)
    designs_included: int       # Monthly design quota (0 for top-up)
    period: str                 # 'monthly', 'one_time'
    max_seats: int              # Multi-user seats
    description: str
    is_active: bool = True


# ═══════════════════════════════════════════════════════════════════════════
# CANONICAL PRICING — Single source of truth
# ═══════════════════════════════════════════════════════════════════════════

PRICE_REGISTRY: Dict[str, ProductConfig] = {
    "individual": ProductConfig(
        product_id="individual",
        display_name="Individual / Researcher",
        product_type=ProductType.SUBSCRIPTION,
        price_inr=2499,
        designs_included=250,
        period="monthly",
        max_seats=1,
        description="250 validated primer/probe designs/month — ~₹10/design"
    ),
    "institutional": ProductConfig(
        product_id="institutional",
        display_name="Lab / Academic Institute",
        product_type=ProductType.SUBSCRIPTION,
        price_inr=14999,
        designs_included=2000,
        period="monthly",
        max_seats=5,
        description="2,000 validated primer/probe designs/month, 5 researcher seats — ~₹7.50/design"
    ),
    "corporate": ProductConfig(
        product_id="corporate",
        display_name="Corporate R&D",
        product_type=ProductType.SUBSCRIPTION,
        price_inr=49999,
        designs_included=7500,
        period="monthly",
        max_seats=999,              # Unlimited
        description="7,500 validated primer/probe designs/month, unlimited seats, dedicated API — ~₹6.67/design"
    ),
}

# Single top-up pricing
TOPUP_PRICE_INR: int = 49  # ₹49 per single primer design run

# Free trial allocation
FREE_TRIAL_RUNS: int = 2


# ═══════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def get_amount_paise(product_id: str, quantity: int = 1) -> int:
    """
    Calculate exact payment amount in paise.
    Integer arithmetic only — no floating point.
    """
    if product_id == "top_up":
        return quantity * TOPUP_PRICE_INR * 100
    product = PRICE_REGISTRY.get(product_id)
    if not product:
        raise ValueError(f"Unknown product_id: {product_id}")
    return product.price_inr * 100


def validate_order_request(product_id: str, quantity: int) -> Optional[str]:
    """
    Validate an order creation request.
    Returns error message string or None if valid.
    """
    if product_id == "top_up":
        if quantity < 1:
            return "Minimum 1 design required."
        if quantity > 100:
            return "Maximum 100 top-up designs per order."
        return None

    if product_id not in PRICE_REGISTRY:
        return f"Unknown plan: {product_id}"

    product = PRICE_REGISTRY[product_id]
    if not product.is_active:
        return f"Plan {product_id} is no longer available."

    return None


def get_designs_for_product(product_id: str, quantity: int = 1) -> int:
    """Get number of design credits for a product purchase."""
    if product_id == "top_up":
        return quantity
    product = PRICE_REGISTRY.get(product_id)
    return product.designs_included if product else 0

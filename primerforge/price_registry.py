#!/usr/bin/env python3
"""
VigyanLLM Price Registry — Disrupted Pricing Model
======================================================
Unified subscription model — each plan includes primer design + docking credits.

Tiers:
  - Free Trial: 2 free runs (primer) + 2 free docking runs per new user
  - Daily:        ₹99/d → 5 designs + 2 docking
  - Individual: ₹2,499/mo → 250 designs + 50 docking
  - Institutional: ₹14,999/mo → 2,000 designs + 500 docking, 5 seats
  - Corporate: ₹49,999/mo → 7,500 designs + 2,000 docking, unlimited seats
  - Top-Up: ₹99/run (covers both primer design and molecular docking)
"""

from dataclasses import dataclass
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
    dock_runs_included: int     # Monthly docking quota (0 for top-up)
    period: str                 # 'daily', 'monthly', 'one_time'
    max_seats: int              # Multi-user seats
    description: str
    is_active: bool = True


# ═══════════════════════════════════════════════════════════════════════════
# CANONICAL PRICING — Single source of truth
# ═══════════════════════════════════════════════════════════════════════════

PRICE_REGISTRY: dict[str, ProductConfig] = {
    "daily": ProductConfig(
        product_id="daily",
        display_name="Daily Pass",
        product_type=ProductType.SUBSCRIPTION,
        price_inr=99,
        designs_included=5,
        dock_runs_included=2,
        period="daily",
        max_seats=1,
        description="5 primer designs + 2 docking runs — valid for 24 hours"
    ),
    "individual": ProductConfig(
        product_id="individual",
        display_name="Individual / Researcher",
        product_type=ProductType.SUBSCRIPTION,
        price_inr=2499,
        designs_included=250,
        dock_runs_included=50,
        period="monthly",
        max_seats=1,
        description="250 primer designs + 50 docking runs/month — ~₹8.33/design"
    ),
    "institutional": ProductConfig(
        product_id="institutional",
        display_name="Lab / Academic Institute",
        product_type=ProductType.SUBSCRIPTION,
        price_inr=14999,
        designs_included=2000,
        dock_runs_included=500,
        period="monthly",
        max_seats=5,
        description="2,000 primer designs + 500 docking runs/month, 5 seats — ~₹6/design"
    ),
    "corporate": ProductConfig(
        product_id="corporate",
        display_name="Corporate R&D",
        product_type=ProductType.SUBSCRIPTION,
        price_inr=49999,
        designs_included=7500,
        dock_runs_included=2000,
        period="monthly",
        max_seats=999,
        description="7,500 primer designs + 2,000 docking runs/month, unlimited seats, API — ~₹5/design"
    ),
}

# Single unified top-up pricing — ₹99 covers ONE run (primer design OR docking)
TOPUP_PRICE_INR: int = 99

# Free trial allocation
FREE_TRIAL_RUNS: int = 2
FREE_DOCK_RUNS: int = 2


# ═══════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def get_amount_paise(product_id: str, quantity: int = 1) -> int:
    """
    Calculate exact payment amount in paise.
    Integer arithmetic only — no floating point.
    """
    if product_id in ("top_up", "dock_top_up"):
        return quantity * TOPUP_PRICE_INR * 100
    product = PRICE_REGISTRY.get(product_id)
    if not product:
        raise ValueError(f"Unknown product_id: {product_id}")
    return product.price_inr * 100


def validate_order_request(product_id: str, quantity: int) -> str | None:
    """
    Validate an order creation request.
    Returns error message string or None if valid.
    """
    if product_id in ("top_up", "dock_top_up"):
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
    if product_id in ("top_up", "dock_top_up"):
        return quantity
    product = PRICE_REGISTRY.get(product_id)
    return product.designs_included if product else 0


def get_dock_runs_for_product(product_id: str, quantity: int = 1) -> int:
    """Get number of docking credits for a product purchase."""
    if product_id in ("dock_top_up", "top_up"):
        return quantity
    product = PRICE_REGISTRY.get(product_id)
    return product.dock_runs_included if product else 0

#!/usr/bin/env python3
"""
VigyanLLM Price Registry — 4-Tier Subscription Model
=====================================================
Free | Pro (₹699/mo or ₹5,999/yr) | Lab (₹3,999/mo or ₹32,999/yr) | Enterprise (custom)

Tiers:
  - Free:        ₹0     → 5 analyses/day, 1 seq/analysis, no batch, no API, no export
  - Pro Monthly:  ₹699  → 100 analyses/day, 50 seq/batch, API 1000 calls/mo, PDF/PPT export
  - Pro Yearly:  ₹5,999 → same as Pro Monthly (2 months free equivalent)
  - Lab Monthly:  ₹3,999 → 500 analyses/day, 200 seq/batch, team collab (5 seats), admin
  - Lab Yearly:  ₹32,999 → same as Lab Monthly
  - Enterprise:  custom → unlimited everything, SSO, SLA, on-premise, dedicated support
"""

from dataclasses import dataclass
from enum import Enum


class BillingCycle(Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"
    ONETIME = "one_time"
    CUSTOM = "custom"


class PlanTier(Enum):
    FREE = "free"
    TRIAL = "trial"
    PRO = "pro"
    LAB = "lab"
    ENTERPRISE = "enterprise"


@dataclass(frozen=True)
class PlanConfig:
    plan_id: str
    tier: PlanTier
    display_name: str
    billing: BillingCycle
    price_inr: int
    daily_analyses: int
    batch_max_seq: int
    api_calls_per_month: int
    max_seats: int
    has_export_pdf: bool
    has_export_ppt: bool
    has_saved_results: bool
    has_advanced_docking: bool
    has_msa_large: bool
    has_crispr_offtarget: bool
    has_collaboration: bool
    has_admin_panel: bool
    has_lims_hooks: bool
    has_custom_branding: bool
    has_sso: bool
    has_on_premise: bool
    has_dedicated_support: bool
    has_sla: bool
    has_custom_tool_dev: bool
    period: str
    description: str
    is_active: bool = True


# ═══════════════════════════════════════════════════════════════════════════
# CANONICAL PRICING — Single source of truth
# ═══════════════════════════════════════════════════════════════════════════

PLAN_REGISTRY: dict[str, PlanConfig] = {
    # ── Free Tier ──────────────────────────────────────────────────────────
    "free": PlanConfig(
        plan_id="free",
        tier=PlanTier.FREE,
        display_name="Free",
        billing=BillingCycle.ONETIME,
        price_inr=0,
        daily_analyses=5,
        batch_max_seq=1,
        api_calls_per_month=0,
        max_seats=1,
        has_export_pdf=False,
        has_export_ppt=False,
        has_saved_results=False,
        has_advanced_docking=False,
        has_msa_large=False,
        has_crispr_offtarget=False,
        has_collaboration=False,
        has_admin_panel=False,
        has_lims_hooks=False,
        has_custom_branding=False,
        has_sso=False,
        has_on_premise=False,
        has_dedicated_support=False,
        has_sla=False,
        has_custom_tool_dev=False,
        period="lifetime",
        description="All 10 tools, basic limits, community support"
    ),
    # ── Pro Monthly ────────────────────────────────────────────────────────
    "pro-monthly": PlanConfig(
        plan_id="pro-monthly",
        tier=PlanTier.PRO,
        display_name="Pro",
        billing=BillingCycle.MONTHLY,
        price_inr=699,
        daily_analyses=100,
        batch_max_seq=50,
        api_calls_per_month=1000,
        max_seats=1,
        has_export_pdf=True,
        has_export_ppt=True,
        has_saved_results=True,
        has_advanced_docking=True,
        has_msa_large=True,
        has_crispr_offtarget=True,
        has_collaboration=False,
        has_admin_panel=False,
        has_lims_hooks=False,
        has_custom_branding=False,
        has_sso=False,
        has_on_premise=False,
        has_dedicated_support=False,
        has_sla=False,
        has_custom_tool_dev=False,
        period="monthly",
        description="100 analyses/day, batch processing, API access, PDF/PPT export"
    ),
    # ── Pro Yearly ─────────────────────────────────────────────────────────
    "pro-yearly": PlanConfig(
        plan_id="pro-yearly",
        tier=PlanTier.PRO,
        display_name="Pro",
        billing=BillingCycle.YEARLY,
        price_inr=5999,
        daily_analyses=100,
        batch_max_seq=50,
        api_calls_per_month=1000,
        max_seats=1,
        has_export_pdf=True,
        has_export_ppt=True,
        has_saved_results=True,
        has_advanced_docking=True,
        has_msa_large=True,
        has_crispr_offtarget=True,
        has_collaboration=False,
        has_admin_panel=False,
        has_lims_hooks=False,
        has_custom_branding=False,
        has_sso=False,
        has_on_premise=False,
        has_dedicated_support=False,
        has_sla=False,
        has_custom_tool_dev=False,
        period="yearly",
        description="Same as Pro monthly — save 28% with annual billing"
    ),
    # ── Lab Monthly ────────────────────────────────────────────────────────
    "lab-monthly": PlanConfig(
        plan_id="lab-monthly",
        tier=PlanTier.LAB,
        display_name="Lab",
        billing=BillingCycle.MONTHLY,
        price_inr=3999,
        daily_analyses=500,
        batch_max_seq=200,
        api_calls_per_month=10000,
        max_seats=5,
        has_export_pdf=True,
        has_export_ppt=True,
        has_saved_results=True,
        has_advanced_docking=True,
        has_msa_large=True,
        has_crispr_offtarget=True,
        has_collaboration=True,
        has_admin_panel=True,
        has_lims_hooks=True,
        has_custom_branding=True,
        has_sso=False,
        has_on_premise=False,
        has_dedicated_support=False,
        has_sla=False,
        has_custom_tool_dev=False,
        period="monthly",
        description="Team collaboration, admin panel, LIMS webhooks, 5 seats"
    ),
    # ── Lab Yearly ─────────────────────────────────────────────────────────
    "lab-yearly": PlanConfig(
        plan_id="lab-yearly",
        tier=PlanTier.LAB,
        display_name="Lab",
        billing=BillingCycle.YEARLY,
        price_inr=32999,
        daily_analyses=500,
        batch_max_seq=200,
        api_calls_per_month=10000,
        max_seats=5,
        has_export_pdf=True,
        has_export_ppt=True,
        has_saved_results=True,
        has_advanced_docking=True,
        has_msa_large=True,
        has_crispr_offtarget=True,
        has_collaboration=True,
        has_admin_panel=True,
        has_lims_hooks=True,
        has_custom_branding=True,
        has_sso=False,
        has_on_premise=False,
        has_dedicated_support=False,
        has_sla=False,
        has_custom_tool_dev=False,
        period="yearly",
        description="Same as Lab monthly — save 31% with annual billing"
    ),
    # ── Enterprise ─────────────────────────────────────────────────────────
    "enterprise": PlanConfig(
        plan_id="enterprise",
        tier=PlanTier.ENTERPRISE,
        display_name="Enterprise",
        billing=BillingCycle.CUSTOM,
        price_inr=0,  # Custom pricing
        daily_analyses=999999,
        batch_max_seq=999999,
        api_calls_per_month=999999,
        max_seats=999999,
        has_export_pdf=True,
        has_export_ppt=True,
        has_saved_results=True,
        has_advanced_docking=True,
        has_msa_large=True,
        has_crispr_offtarget=True,
        has_collaboration=True,
        has_admin_panel=True,
        has_lims_hooks=True,
        has_custom_branding=True,
        has_sso=True,
        has_on_premise=True,
        has_dedicated_support=True,
        has_sla=True,
        has_custom_tool_dev=True,
        period="custom",
        description="Unlimited everything, SSO, SLA, on-premise, dedicated support"
    ),
    # ── Academic Trial ─────────────────────────────────────────────────────
    # Configurable per promo code — limits set dynamically at activation
    # This is a template; actual daily_analyses/batch_max come from promo_codes table
    "trial": PlanConfig(
        plan_id="trial",
        tier=PlanTier.TRIAL,
        display_name="Academic Trial",
        billing=BillingCycle.CUSTOM,
        price_inr=0,
        daily_analyses=50,
        batch_max_seq=20,
        api_calls_per_month=0,
        max_seats=1,
        has_export_pdf=True,
        has_export_ppt=False,
        has_saved_results=True,
        has_advanced_docking=True,
        has_msa_large=True,
        has_crispr_offtarget=False,
        has_collaboration=False,
        has_admin_panel=False,
        has_lims_hooks=False,
        has_custom_branding=False,
        has_sso=False,
        has_on_premise=False,
        has_dedicated_support=False,
        has_sla=False,
        has_custom_tool_dev=False,
        period="trial",
        description="30-day Pro trial with autopay — verify with ₹1, cancel anytime"
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# TRIAL CONFIG — dynamic per promo code
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TrialConfig:
    """Configuration for a trial promo code."""
    code: str
    tier: str = "pro"            # tier to grant AFTER trial ends
    daily_analyses: int = 50     # trial-period daily limit
    batch_max: int = 20          # trial-period batch limit
    has_export: bool = True
    trial_days: int = 30         # configurable per code
    price_inr: int = 699         # recurring price after trial
    currency: str = "INR"        # INR/USD/EUR/GBP
    max_uses: int = 1            # single-use enforcement


# ═══════════════════════════════════════════════════════════════════════════
# ACADEMIC DISCOUNT
# ═══════════════════════════════════════════════════════════════════════════

ACADEMIC_DISCOUNT_PCT: int = 30  # 30% off for .edu / .ac.in emails


def get_academic_price(price_inr: int) -> int:
    """Apply 30% academic discount, rounded to nearest rupee."""
    return int(price_inr * (100 - ACADEMIC_DISCOUNT_PCT) / 100)


# ═══════════════════════════════════════════════════════════════════════════
# LIMITS BY TIER (for usage checking)
# ═══════════════════════════════════════════════════════════════════════════

TIER_LIMITS: dict[str, dict] = {
    "free": {
        "daily_analyses": 5,
        "batch_max_seq": 1,
        "api_calls_per_month": 0,
    },
    "trial": {
        "daily_analyses": 50,
        "batch_max_seq": 20,
        "api_calls_per_month": 0,
    },
    "pro": {
        "daily_analyses": 100,
        "batch_max_seq": 50,
        "api_calls_per_month": 1000,
    },
    "lab": {
        "daily_analyses": 500,
        "batch_max_seq": 200,
        "api_calls_per_month": 10000,
    },
    "enterprise": {
        "daily_analyses": 999999,
        "batch_max_seq": 999999,
        "api_calls_per_month": 999999,
    },
}


def get_tier_limits(tier: str) -> dict:
    """Get usage limits for a given tier. Defaults to free."""
    return TIER_LIMITS.get(tier, TIER_LIMITS["free"])


# ═══════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def get_amount_paise(plan_id: str, quantity: int = 1) -> int:
    """Calculate exact payment amount in paise. Integer arithmetic only."""
    plan = PLAN_REGISTRY.get(plan_id)
    if not plan:
        raise ValueError(f"Unknown plan_id: {plan_id}")
    return plan.price_inr * 100 * quantity


def validate_plan(plan_id: str) -> str | None:
    """Validate a plan ID. Returns error message or None if valid."""
    if plan_id not in PLAN_REGISTRY:
        return f"Unknown plan: {plan_id}"
    plan = PLAN_REGISTRY[plan_id]
    if not plan.is_active:
        return f"Plan {plan_id} is no longer available."
    return None


def get_tier_from_plan(plan_id: str) -> str:
    """Get the tier name from a plan ID."""
    plan = PLAN_REGISTRY.get(plan_id)
    if not plan:
        return "free"
    return plan.tier.value


# ═══════════════════════════════════════════════════════════════════════════
# BACKWARD COMPATIBILITY — Old pg_payment_routes.py / price_registry API
# ═══════════════════════════════════════════════════════════════════════════

FREE_TRIAL_RUNS = 5
TOPUP_PRICE_INR = 0


class _LegacyPlanWrap:
    """Wraps PlanConfig to look like old ProductConfig for pg_payment_routes.py."""
    def __init__(self, plan: PlanConfig):
        self.product_id = plan.plan_id
        self.display_name = plan.display_name
        self.product_type = plan.tier
        self.designs_included = plan.daily_analyses
        self.price_inr = plan.price_inr
        self.period = plan.period
        self.max_seats = plan.max_seats
        self.description = plan.description
        self.is_active = plan.is_active


PRICE_REGISTRY: dict = {k: _LegacyPlanWrap(v) for k, v in PLAN_REGISTRY.items()}


def get_designs_for_product(product_id: str, quantity: int = 1) -> int:
    """Backward compatibility: return daily_analyses from the plan."""
    plan = PLAN_REGISTRY.get(product_id)
    return plan.daily_analyses if plan else 0


def get_dock_runs_for_product(product_id: str, quantity: int = 1) -> int:
    """Backward compatibility: docking not gated by token packs in new model."""
    return 0


def validate_order_request(product_id: str, quantity: int) -> str | None:
    """Backward compatibility: validate plan exists and is active."""
    if product_id not in PLAN_REGISTRY:
        return f"Unknown product: {product_id}"
    plan = PLAN_REGISTRY[product_id]
    if not plan.is_active:
        return f"Product {product_id} is no longer available."
    return None

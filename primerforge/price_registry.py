#!/usr/bin/env python3
"""
VigyanLLM Price Registry — 4-Tier Subscription Model
=====================================================
Free | Pro ($9.99/mo or $89/yr) | Lab ($49/mo or $399/yr) | Enterprise (custom)

ALL amounts in this registry are MINOR UNITS of CURRENCY (USD cents).
  - Free:        $0      → 5 analyses/day, 1 seq/analysis, no batch, no API, no export
  - Pro Monthly:  999¢   → 100 analyses/day, 50 seq/batch, API 1000 calls/mo, PDF/PPT export
  - Pro Yearly:  8900¢   → same as Pro Monthly (save 26% with annual billing)
  - Lab Monthly:  4900¢   → 500 analyses/day, 200 seq/batch, team collab (5 seats), admin
  - Lab Yearly:  39900¢   → same as Lab Monthly (save 32% with annual billing)
  - Enterprise:  custom  → unlimited everything, SSO, SLA, on-premise, dedicated support

Legacy naming: `price_inr` survives as a deprecated property alias that returns
price_minor (the old *100 conversion is intentionally gone — callers must treat
every amount as minor units of CURRENCY).
"""

from dataclasses import dataclass
from enum import Enum

#: Site-wide billing currency. All prices/amounts are minor units of this.
CURRENCY: str = "USD"


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
    price_minor: int  # minor units of CURRENCY (USD cents)
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
    # Docking credits granted per billing period (0 = docking not included).
    # Credits are the ONLY currency docking is priced in — see the credit
    # engine at the bottom of this file (never exposed to clients).
    docking_credits: int = 0

    @property
    def price_inr(self) -> int:
        """Deprecated legacy alias — returns price_minor (minor units of CURRENCY)."""
        return self.price_minor


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
        price_minor=0,
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
        price_minor=999,
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
        description="100 analyses/day, batch processing, API access, PDF/PPT export",
        docking_credits=1000
    ),
    # ── Pro Yearly ─────────────────────────────────────────────────────────
    "pro-yearly": PlanConfig(
        plan_id="pro-yearly",
        tier=PlanTier.PRO,
        display_name="Pro",
        billing=BillingCycle.YEARLY,
        price_minor=8900,
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
        description="Same as Pro monthly — save 26% with annual billing",
        docking_credits=1000
    ),
    # ── Lab Monthly ────────────────────────────────────────────────────────
    "lab-monthly": PlanConfig(
        plan_id="lab-monthly",
        tier=PlanTier.LAB,
        display_name="Lab",
        billing=BillingCycle.MONTHLY,
        price_minor=4900,
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
        description="Team collaboration, admin panel, LIMS webhooks, 5 seats",
        docking_credits=5000
    ),
    # ── Lab Yearly ─────────────────────────────────────────────────────────
    "lab-yearly": PlanConfig(
        plan_id="lab-yearly",
        tier=PlanTier.LAB,
        display_name="Lab",
        billing=BillingCycle.YEARLY,
        price_minor=39900,
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
        description="Same as Lab monthly — save 32% with annual billing",
        docking_credits=5000
    ),
    # ── Enterprise ─────────────────────────────────────────────────────────
    "enterprise": PlanConfig(
        plan_id="enterprise",
        tier=PlanTier.ENTERPRISE,
        display_name="Enterprise",
        billing=BillingCycle.CUSTOM,
        price_minor=0,  # Custom pricing
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
        price_minor=0,
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
        description="30-day Pro trial with autopay — verify with $1, cancel anytime",
        docking_credits=1000
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
    price_minor: int = 999       # recurring price after trial (USD cents)
    currency: str = "USD"        # minor units of this currency
    max_uses: int = 1            # single-use enforcement


# ═══════════════════════════════════════════════════════════════════════════
# ACADEMIC DISCOUNT
# ═══════════════════════════════════════════════════════════════════════════

ACADEMIC_DISCOUNT_PCT: int = 30  # 30% off for .edu / .ac.in emails


def get_academic_price(price_minor: int) -> int:
    """Apply 30% academic discount, truncated to whole minor units (cents)."""
    return int(price_minor * (100 - ACADEMIC_DISCOUNT_PCT) / 100)


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

def get_amount_minor(product_id: str, quantity: int = 1) -> int:
    """Exact payment amount in minor units of CURRENCY (USD cents). Integer arithmetic only.

    Accepts subscription plan ids (pro-monthly, ...) and one-off top-up
    products (top_up, dock_top_up). Raises ValueError for unknown products.
    """
    plan = PLAN_REGISTRY.get(product_id)
    if plan is not None:
        return plan.price_minor * quantity
    pack = TOPUP_PRODUCTS.get(product_id)
    if pack is not None:
        return pack["unit_price_minor"] * quantity
    raise ValueError(f"Unknown product: {product_id}")


def get_amount_paise(plan_id: str, quantity: int = 1) -> int:
    """Deprecated alias of get_amount_minor — kept for legacy imports.

    NOTE: the returned value is minor units of CURRENCY (USD cents),
    NOT paise. No *100 conversion should ever be applied to it.
    """
    return get_amount_minor(plan_id, quantity)


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
TOPUP_PRICE_MINOR = 100  # USD cents per analysis run (legacy constant name kept)

# Docking credits bought per $1.00 top-up. Subscriptions buy credits at
# $1 = 100 credits; the top-up rate is deliberately worse (80) so that
# committed plans, not impulse packs, are the cheap path. Server-side only.
DOCK_TOPUP_CREDITS_PER_UNIT = 80

# One-off pay-as-you-go products (sold via create-order, not subscriptions).
# Prices are minor units of CURRENCY — server-authoritative, never trust client amounts.
# NOTE: Razorpay USD orders have a hard $1.00 (100¢) payment-time minimum — any
# lower amount gets clamped at checkout and then rejected as an amount mismatch.
TOPUP_PRODUCTS: dict[str, dict] = {
    "top_up": {"unit_price_minor": 100, "label": "Analysis run"},          # $1.00 / run
    "dock_top_up": {"unit_price_minor": 100, "label": "Docking credits",   # $1.00 → 80 credits
                    "credits_per_unit": DOCK_TOPUP_CREDITS_PER_UNIT},
}


class _LegacyPlanWrap:
    """Wraps PlanConfig to look like old ProductConfig for pg_payment_routes.py."""
    def __init__(self, plan: PlanConfig):
        self.product_id = plan.plan_id
        self.display_name = plan.display_name
        self.product_type = plan.tier
        self.designs_included = plan.daily_analyses
        # Docking credits granted per billing period. The subscription webhook
        # reads this attribute directly (pg_payment_routes.py) — it must exist
        # on every wrapped product or plan activation throws AttributeError.
        self.dock_runs_included = plan.docking_credits
        self.price_minor = plan.price_minor
        self.price_inr = plan.price_minor  # legacy name — minor units of CURRENCY
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
    """Docking credits granted for a purchase (legacy name kept).

    * Subscription plan → the plan's monthly credit grant (Pro 1,000 /
      Lab 5,000 — quantity is always 1 for plans).
    * `dock_top_up`     → DOCK_TOPUP_CREDITS_PER_UNIT credits per $1 unit.
    * anything else     → 0 (no docking value in the product).
    """
    plan = PLAN_REGISTRY.get(product_id)
    if plan is not None:
        return plan.docking_credits
    if product_id == "dock_top_up":
        try:
            qty = max(0, int(quantity))
        except (TypeError, ValueError):
            return 0
        return DOCK_TOPUP_CREDITS_PER_UNIT * qty
    return 0


def validate_order_request(product_id: str, quantity: int) -> str | None:
    """Validate a create-order request: plan or top-up product, active, qty sane."""
    if product_id in TOPUP_PRODUCTS:
        return None
    if product_id not in PLAN_REGISTRY:
        return f"Unknown product: {product_id}"
    plan = PLAN_REGISTRY[product_id]
    if not plan.is_active:
        return f"Product {product_id} is no longer available."
    return None


# ═══════════════════════════════════════════════════════════════════════════
# DOCKING CREDIT ENGINE — server-side ONLY
# ═══════════════════════════════════════════════════════════════════════════
# Docking is the one metered product; the other nine tools stay free.
# Clients are shown only a computed price quote and the remaining balance —
# this module's arithmetic never leaves the server (no /pricing field, no
# quote-echo of the formula).

#: Credits for one consensus docking run (≤100 ligands, 1 protein, full
#: ESMFold/Vina/GNINA pipeline + report). Keeps the historical "$1 per run"
#: economics at the $1 = 100-credits subscription rate.
CONSENSUS_RUN_CREDITS = 100


def screening_credit_cost(n_ligands: int, n_proteins: int) -> int:
    """Credit price of a virtual screening campaign. Integer-only, no floats.

      base  = 100 + 50·(min(N,100) − 1) + 25·max(0, N − 100)
      total = ceil(base × (1 + 0.5·(P − 1)) × 1.02)

    The first ligand carries the whole setup cost (receptor prep, pocket
    detection, first chunk); ligands 2–100 are bulk; beyond 100 the marginal
    rate halves. Extra proteins share the library prep, so each additional
    target adds 50% of the per-protein base. The 2% covers queue/heartbeat
    overhead. Reference points: 1×1 = 102 · 18×1 = 969 · 10k×1 = 257,601
    · 100k×1 = 2,552,601 credits.
    """
    try:
        n = max(0, int(n_ligands))
        p = max(1, int(n_proteins))
    except (TypeError, ValueError):
        return CONSENSUS_RUN_CREDITS
    if n < 1:
        return CONSENSUS_RUN_CREDITS
    base = 100 + 50 * (min(n, 100) - 1) + 25 * max(0, n - 100)
    # base × (p + 1)/2 × 1.02 == base × (p + 1) × 51 / 100, rounded up.
    return (base * (p + 1) * 51 + 99) // 100

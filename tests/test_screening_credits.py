"""
Docking credit pricing — Phase 1 (2026-10-11).

Docking is the one metered tool (the other nine stay free), and its credit
formula lives SERVER-SIDE ONLY — no /pricing field, no quote echoes the math.
These tests pin:

  1. the price formula's reference numbers (locked economics: $1 = 100 credits
     in subscriptions, 80 credits per $1 top-up, per-ligand pricing with a
     ×1.5 / ×2 multi-protein surcharge, 2% queue overhead),
  2. the plan credit grants (Pro 1,000 / Lab 5,000) including the legacy
     product wrapper attribute the subscription webhook reads directly,
  3. the settle contract — the size-aware `cost` reaches the ledger, legacy
     2-arg consume callables still work, and an unsettled run fires the
     campaign-failure hook instead of stranding a pending campaign,
  4. the refund arithmetic: cancel gives back only the docking that will
     never happen, infrastructure failure gives back everything, and
     bookkeeping cannot double-refund.
"""

import math
from fractions import Fraction

import pytest

from primerforge.price_registry import (
    CONSENSUS_RUN_CREDITS,
    DOCK_TOPUP_CREDITS_PER_UNIT,
    PLAN_REGISTRY,
    PRICE_REGISTRY,
    TOPUP_PRODUCTS,
    get_dock_runs_for_product,
    screening_credit_cost,
)


# ══════════════════════════════════════════════════════════════════════════
# 1. Credit formula
# ══════════════════════════════════════════════════════════════════════════

class TestScreeningCreditCost:
    @pytest.mark.parametrize("n_ligands, n_proteins, expected", [
        (1, 1, 102),            # the locked 1×1 reference price
        (18, 1, 969),           # the locked 18×1 reference price
        (10_000, 1, 257_601),   # the locked 10k×1 reference price
        (100_000, 1, 2_552_601),  # the locked 100k×1 reference price
        (1, 2, 153),            # 2 proteins → ×1.5, rounded up
        (1, 3, 204),            # 3 proteins → ×2
        (18, 2, 1_454),         # 969 × 1.5 = 1453.5 → ceil
        (100, 1, 5_151),        # end of the 50-credit bulk tier
    ])
    def test_reference_prices(self, n_ligands, n_proteins, expected):
        assert screening_credit_cost(n_ligands, n_proteins) == expected

    @pytest.mark.parametrize("n_ligands", [1, 2, 50, 100, 101, 250, 1000, 5000, 100_000])
    @pytest.mark.parametrize("n_proteins", [1, 2, 3, 10])
    def test_matches_locked_formula_exactly(self, n_ligands, n_proteins):
        """base = 100 + 50·(min(N,100)−1) + 25·max(0,N−100)
        total = ceil(base × (1 + 0.5·(P−1)) × 1.02)

        Evaluated with exact rationals — the implementation must be the
        integer form of this, not a float approximation of it.
        """
        base = 100 + 50 * (min(n_ligands, 100) - 1) + 25 * max(0, n_ligands - 100)
        want = math.ceil(Fraction(base) * Fraction(n_proteins + 1, 2) * Fraction(102, 100))
        assert screening_credit_cost(n_ligands, n_proteins) == want

    def test_bulk_rate_drops_after_100_ligands(self):
        """2-credit-adjacent: bulk ligands cost 25 before the 2% overhead,
        so the marginal step must sit well under the first-100 step of 50."""
        early = screening_credit_cost(51, 1) - screening_credit_cost(50, 1)
        late = screening_credit_cost(501, 1) - screening_credit_cost(500, 1)
        assert early > late
        assert late <= 30  # 25 × 1.02 = 25.5 → at most 26, plus ceil slack

    def test_price_never_decreases_with_more_work(self):
        prev = 0
        for n in (1, 2, 3, 10, 99, 100, 101, 500, 5000):
            got = screening_credit_cost(n, 1)
            assert got >= prev
            prev = got

    def test_more_proteins_never_cost_less(self):
        for n in (1, 18, 1000):
            costs = [screening_credit_cost(n, p) for p in (1, 2, 3, 5, 10)]
            assert costs == sorted(costs)

    def test_degenerate_inputs_fall_back_to_a_run_price(self):
        """Unpriceable input → one consensus run's worth, never 0 and never
        a negative credit grant."""
        assert screening_credit_cost(0, 1) == CONSENSUS_RUN_CREDITS
        assert screening_credit_cost(-5, 1) == CONSENSUS_RUN_CREDITS
        assert screening_credit_cost("abc", 1) == CONSENSUS_RUN_CREDITS
        assert screening_credit_cost(None, None) == CONSENSUS_RUN_CREDITS

    def test_protein_count_is_clamped_to_at_least_one(self):
        assert screening_credit_cost(10, 0) == screening_credit_cost(10, 1)
        assert screening_credit_cost(10, -3) == screening_credit_cost(10, 1)

    def test_result_is_an_exact_int(self):
        for n, p in ((1, 1), (18, 2), (100_000, 10)):
            got = screening_credit_cost(n, p)
            assert isinstance(got, int) and not isinstance(got, bool)
            assert got > 0

    def test_consensus_run_is_one_dollar_at_subscription_rate(self):
        assert CONSENSUS_RUN_CREDITS == 100


# ══════════════════════════════════════════════════════════════════════════
# 2. Plan grants & top-up packs
# ══════════════════════════════════════════════════════════════════════════

class TestCreditGrants:
    @pytest.mark.parametrize("plan_id, expected", [
        ("pro-monthly", 1000),
        ("pro-yearly", 1000),
        ("lab-monthly", 5000),
        ("lab-yearly", 5000),
        ("trial", 1000),
        ("free", 0),
        ("enterprise", 0),
    ])
    def test_registry_grants(self, plan_id, expected):
        assert PLAN_REGISTRY[plan_id].docking_credits == expected

    def test_every_wrapped_product_exposes_dock_runs_included(self):
        """Regression: pg_payment_routes' subscription.authenticated webhook
        reads product.dock_runs_included directly — the legacy wrapper lacking
        that attribute was a latent AttributeError inside plan activation."""
        for plan_id, wrapped in PRICE_REGISTRY.items():
            assert isinstance(wrapped.dock_runs_included, int), plan_id
            assert wrapped.dock_runs_included == PLAN_REGISTRY[plan_id].docking_credits

    def test_subscription_webhook_reads_sane_plan_attributes(self):
        product = PRICE_REGISTRY["pro-monthly"]
        # every attribute the webhook branch touches
        assert product.dock_runs_included == 1000
        assert product.designs_included > 0
        assert product.period == "monthly"
        assert product.max_seats >= 1
        assert product.price_minor > 0

    @pytest.mark.parametrize("plan_id, expected", [
        ("pro-monthly", 1000), ("pro-yearly", 1000),
        ("lab-monthly", 5000), ("lab-yearly", 5000),
        ("trial", 1000), ("free", 0),
    ])
    def test_get_dock_runs_for_products_returns_grant(self, plan_id, expected):
        # quantity is meaningless for a subscription and must not scale it
        assert get_dock_runs_for_product(plan_id, 1) == expected
        assert get_dock_runs_for_product(plan_id, 99) == expected

    def test_dock_top_up_buys_eighty_credits_per_dollar(self):
        assert DOCK_TOPUP_CREDITS_PER_UNIT == 80
        assert get_dock_runs_for_product("dock_top_up", 1) == 80
        assert get_dock_runs_for_product("dock_top_up", 3) == 240
        assert get_dock_runs_for_product("dock_top_up", 0) == 0
        assert get_dock_runs_for_product("dock_top_up", "x") == 0

    def test_analysis_top_up_grants_no_docking_credits(self):
        assert get_dock_runs_for_product("top_up", 5) == 0
        assert get_dock_runs_for_product("not-a-product", 5) == 0

    def test_top_up_products_stay_at_the_razorpay_usd_minimum(self):
        """Razorpay rejects sub-$1.00 USD orders — both packs must stay 100¢."""
        for pid, meta in TOPUP_PRODUCTS.items():
            assert meta["unit_price_minor"] == 100, pid
        assert TOPUP_PRODUCTS["dock_top_up"]["credits_per_unit"] == 80
        assert TOPUP_PRODUCTS["dock_top_up"]["label"] == "Docking credits"

    def test_top_up_rate_is_deliberately_worse_than_the_plan_rate(self):
        """$1 in a plan buys 100 credits; a $1 pack buys 80. If somebody
        'optimises' the pack rate this test says the economics changed."""
        plan_rate = PLAN_REGISTRY["pro-monthly"].docking_credits / 9.99
        assert plan_rate > DOCK_TOPUP_CREDITS_PER_UNIT


# ══════════════════════════════════════════════════════════════════════════
# 3. Settle contract — size-aware cost delivery
# ══════════════════════════════════════════════════════════════════════════

_USER = {"email": "u@example.com", "role": "user", "user_id": 7}


class TestSettleCreditCost:
    def test_cost_is_forwarded_to_the_ledger(self):
        from primerforge.primer_server import _settle_docking_job
        seen = {}

        def consume(uid, email, cost=1):
            seen.update(uid=uid, email=email, cost=cost)
            return True

        out = _settle_docking_job("job-cost-1", _USER, True, consume, None,
                                  credit_cost=969)
        assert out is None
        assert seen == {"uid": 7, "email": "u@example.com", "cost": 969}

    def test_default_cost_is_one(self):
        from primerforge.primer_server import _settle_docking_job
        seen = {}

        def consume(uid, email, cost=1):
            seen["cost"] = cost
            return True

        assert _settle_docking_job("job-cost-2", _USER, True, consume, None) is None
        assert seen["cost"] == 1

    def test_legacy_two_arg_consume_callable_still_works(self):
        """Old callers (and the existing settle tests) pass (uid, email) fakes.
        The signature is probed rather than sniffed from a TypeError, which a
        real internal failure would also raise."""
        from primerforge.primer_server import _settle_docking_job
        seen = []

        def consume(uid, email):
            seen.append((uid, email))
            return True

        assert _settle_docking_job("job-cost-3", _USER, True, consume, None,
                                   credit_cost=100) is None
        assert seen == [(7, "u@example.com")]

    def test_unsettled_campaign_fires_the_failure_hook(self):
        """A screening campaign that cannot pay must not be left at `pending`
        forever (the old code only ever cancelled queue jobs)."""
        from primerforge.primer_server import _settle_docking_job
        killed = []

        out = _settle_docking_job("campaign-x", _USER, True,
                                  lambda uid, email, cost=1: False, None,
                                  credit_cost=2_552_601,
                                  on_unsettled=lambda: killed.append("dead"))
        assert out is not None
        body, status = out
        assert status == 402
        assert body["code"] == "PAYMENT_REQUIRED"
        assert body["action"] == "show_docking_payment"
        assert killed == ["dead"]

    def test_ledger_exception_still_fires_the_failure_hook(self):
        from primerforge.primer_server import _settle_docking_job
        killed = []

        def boom(uid, email, cost=1):
            raise RuntimeError("pg down")

        out = _settle_docking_job("campaign-y", _USER, True, boom, None,
                                  on_unsettled=lambda: killed.append("dead"))
        assert out is not None and out[1] == 500
        assert killed == ["dead"]

    def test_success_never_fires_the_failure_hook(self):
        from primerforge.primer_server import _settle_docking_job
        killed = []
        out = _settle_docking_job("campaign-z", _USER, True,
                                  lambda uid, email, cost=1: True, None,
                                  credit_cost=102,
                                  on_unsettled=lambda: killed.append("dead"))
        assert out is None and killed == []

    def test_hook_failure_cannot_mask_the_402(self):
        from primerforge.primer_server import _settle_docking_job

        def bad_hook():
            raise RuntimeError("update failed")

        out = _settle_docking_job("campaign-w", _USER, True,
                                  lambda uid, email, cost=1: False, None,
                                  on_unsettled=bad_hook)
        assert out is not None and out[1] == 402


# ══════════════════════════════════════════════════════════════════════════
# 4. Refund arithmetic
# ══════════════════════════════════════════════════════════════════════════

VALID_SMILES = ["CCO", "CC(=O)Oc1ccccc1C(=O)O", "CN1C=NC2=C1C(=O)N(C)C"]
PROTEIN = {"sequence": "MKTAYIAKQRQISFVKSHFSRQ" * 3}


@pytest.fixture
def vs_dir(monkeypatch, tmp_path):
    """Isolated screening directory — never the repo's docking_queue/."""
    from primerforge.pipelines import virtual_screening as vs
    monkeypatch.setattr(vs, "SCREEN_DIR", str(tmp_path))
    return vs


def _campaign_with_credits(vs, paid=1000, charged=1000, done=0, total=100):
    cid = vs.create_campaign(proteins=[PROTEIN], ligands=VALID_SMILES)
    vs.update_campaign(cid, {
        "credits_charged": charged,
        "credits_paid": paid,
        "credits_refunded": 0,
        "progress": {"stage": "running", "ligands_done": done,
                     "ligands_total": total},
    })
    return cid, vs.get_campaign(cid)


class TestScreeningRefund:
    def test_infrastructure_failure_refunds_everything(self, vs_dir):
        from primerforge.primer_server import _screening_refund
        cid, campaign = _campaign_with_credits(vs_dir, paid=969, done=0, total=18)
        got = _screening_refund(campaign, 7, lambda uid, amt: amt == 969,
                                mode="full")
        assert got == 969
        after = vs_dir.get_campaign(cid)
        assert after["credits_paid"] == 0
        assert after["credits_refunded"] == 969

    def test_cancel_before_start_refunds_the_full_charge(self, vs_dir):
        from primerforge.primer_server import _screening_refund
        cid, campaign = _campaign_with_credits(vs_dir, paid=969, done=0, total=18)
        assert _screening_refund(campaign, 7, lambda uid, amt: True,
                                 mode="cancel") == 969
        assert vs_dir.get_campaign(cid)["credits_paid"] == 0

    def test_cancel_refunds_only_the_docking_that_will_never_run(self, vs_dir):
        from primerforge.primer_server import _screening_refund
        cid, campaign = _campaign_with_credits(vs_dir, paid=1000, done=40, total=100)
        charges = []
        got = _screening_refund(campaign, 7, lambda uid, amt: charges.append(amt) or True,
                                mode="cancel")
        assert charges == [600]          # 60% never docked
        assert got == 600
        after = vs_dir.get_campaign(cid)
        assert after["credits_paid"] == 400   # the finished 40% stays paid for
        assert after["credits_refunded"] == 600

    def test_fully_docked_campaign_refunds_nothing(self, vs_dir):
        from primerforge.primer_server import _screening_refund
        _, campaign = _campaign_with_credits(vs_dir, paid=1000, done=100, total=100)
        called = []
        assert _screening_refund(campaign, 7, lambda uid, amt: called.append(amt) or True,
                                 mode="cancel") == 0
        assert called == []

    def test_free_and_admin_campaigns_refund_nothing(self, vs_dir):
        from primerforge.primer_server import _screening_refund
        _, campaign = _campaign_with_credits(vs_dir, paid=0, charged=102)
        called = []
        assert _screening_refund(campaign, 7, lambda uid, amt: called.append(amt) or True,
                                 mode="full") == 0
        assert called == []

    def test_refund_failure_leaves_bookkeeping_intact(self, vs_dir):
        """If the ledger refuses the credit, the campaign must not claim it
        was refunded (a later resume would then skip the re-charge)."""
        from primerforge.primer_server import _screening_refund
        cid, campaign = _campaign_with_credits(vs_dir, paid=969, done=0, total=18)
        assert _screening_refund(campaign, 7, lambda uid, amt: False, mode="full") == 0
        after = vs_dir.get_campaign(cid)
        assert after["credits_paid"] == 969
        assert after["credits_refunded"] == 0

    def test_no_ledger_no_refund(self, vs_dir):
        """SQLite/dev mode has no credit ledger — nothing is charged, so
        nothing may be handed back."""
        from primerforge.primer_server import _screening_refund
        cid, campaign = _campaign_with_credits(vs_dir, paid=1000, done=0, total=10)
        assert _screening_refund(campaign, 7, None, mode="cancel") == 0
        after = vs_dir.get_campaign(cid)
        assert after["credits_paid"] == 1000
        assert after["credits_refunded"] == 0

    def test_legacy_campaign_without_credit_fields_is_safe(self, vs_dir):
        """Campaigns created before this feature have no credit keys — a
        cancel must not invent a refund for them."""
        from primerforge.primer_server import _screening_refund
        cid = vs_dir.create_campaign(proteins=[PROTEIN], ligands=VALID_SMILES)
        campaign = vs_dir.get_campaign(cid)
        assert "credits_charged" not in campaign
        assert _screening_refund(campaign, 7, lambda uid, amt: True, mode="full") == 0

    def test_refund_roundtrip_cannot_net_a_free_campaign(self, vs_dir):
        """charge → cancel(50%) → resume re-charges what was refunded →
        cancel again refunds only what is still undocked."""
        from primerforge.primer_server import _screening_refund
        cid, campaign = _campaign_with_credits(vs_dir, paid=1000, done=50, total=100)

        refunded = _screening_refund(campaign, 7, lambda uid, amt: True, mode="cancel")
        assert refunded == 500
        state = vs_dir.get_campaign(cid)
        assert state["credits_paid"] == 500
        assert state["credits_refunded"] == 500

        # resume re-charges exactly the outstanding amount (route logic)
        owed = state["credits_refunded"]
        assert owed == 500
        vs_dir.update_campaign(cid, {"credits_paid": state["credits_paid"] + owed,
                                     "credits_refunded": 0})
        resumed = vs_dir.get_campaign(cid)
        assert resumed["credits_paid"] == 1000

        # second cancel at the same progress refunds only what is left
        again = _screening_refund(resumed, 7, lambda uid, amt: True, mode="cancel")
        assert again == 500
        final = vs_dir.get_campaign(cid)
        assert final["credits_paid"] == 500
        assert final["credits_refunded"] == 500

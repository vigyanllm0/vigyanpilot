#!/usr/bin/env python3
"""
VigyanLLM Razorpay Payment Integration — PostgreSQL Version
==============================================================
Hybrid Subscription + Token Pack model with full cost tracking.

Endpoints:
  POST /api/payments/create-order    — Create Razorpay order
  POST /api/payments/verify-payment  — Verify signature & credit tokens
  POST /api/payments/webhook         — Razorpay webhook (server-to-server)
  GET  /api/payments/pricing         — Public pricing data
  GET  /api/payments/token-balance   — User's token balance & subscription
  GET  /api/payments/financial-summary — Admin: P&L and ROI views
"""

import os
import hmac
import hashlib
import time
import json
import logging

import razorpay
from flask import Blueprint, request, jsonify, g

from .database import get_db, get_db_standalone, fetch_one, fetch_all, execute, execute_returning, db_transaction
from .pg_auth import get_current_user, require_auth, require_admin, log_action, check_usage
from .price_registry import PRICE_REGISTRY, TOPUP_PRICE_INR, FREE_TRIAL_RUNS, get_amount_paise, validate_order_request, get_designs_for_product
from .security import validate_quantity

logger = logging.getLogger("primerforge.payments")

payment_bp = Blueprint("payments", __name__)

# ── Razorpay Configuration ────────────────────────────────────────────────
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")

if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
    logger.warning("RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET not set — payment endpoints will fail")

# Fallback webhook secret to key secret if not separately configured
if not RAZORPAY_WEBHOOK_SECRET:
    RAZORPAY_WEBHOOK_SECRET = RAZORPAY_KEY_SECRET

rz_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)) if RAZORPAY_KEY_ID else None


# ── Helper: Verify Razorpay Signature ─────────────────────────────────────

def _verify_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """HMAC-SHA256(order_id|payment_id, secret) == signature"""
    message = f"{order_id}|{payment_id}"
    expected = hmac.new(
        RAZORPAY_KEY_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _credit_tokens_atomic(user_id: int, order_id: str, product_id: str,
                           quantity: int = 1, payment_id: str = "") -> int:
    """
    Atomically credit designs after payment capture. Idempotent.
    - Subscriptions: activate plan + set monthly quota
    - Top-ups: add to balance
    Returns designs credited (0 if already processed).
    """
    db = get_db()
    cur = db.cursor()

    # Conditional update: only if status is still 'initiated' or 'authorized'
    cur.execute(
        """UPDATE payments SET status = 'captured', captured_at = NOW(),
                gateway_payment_id = COALESCE(NULLIF(%s, ''), gateway_payment_id)
           WHERE gateway_order_id = %s AND status IN ('initiated', 'authorized')
           RETURNING id, product_type, tokens_purchased""",
        (payment_id, order_id)
    )
    row = cur.fetchone()

    if not row:
        cur.close()
        return 0  # Already processed (idempotent)

    designs = get_designs_for_product(product_id, quantity)

    if product_id in PRICE_REGISTRY:
        # Subscription plan — activate and set monthly quota
        product = PRICE_REGISTRY[product_id]
        cur.execute(
            """INSERT INTO subscriptions (user_id, is_active, plan_id, plan_type, monthly_quota,
                   quota_used, started_at, expires_at, last_renewed_at, max_seats, quota_reset_at)
               VALUES (%s, TRUE, %s, %s, %s, 0, NOW(), NOW() + INTERVAL '30 days', NOW(), %s, NOW() + INTERVAL '30 days')
               ON CONFLICT (user_id) DO UPDATE SET
                 is_active = TRUE,
                 plan_id = %s,
                 plan_type = %s,
                 monthly_quota = %s,
                 quota_used = 0,
                 expires_at = NOW() + INTERVAL '30 days',
                 last_renewed_at = NOW(),
                 max_seats = %s,
                 quota_reset_at = NOW() + INTERVAL '30 days'""",
            (user_id, product_id, product_id, designs, product.max_seats,
             product_id, product_id, designs, product.max_seats)
        )
    else:
        # Top-up — add to balance directly
        cur.execute(
            """UPDATE token_balances
               SET balance = balance + %s,
                   total_purchased = total_purchased + %s,
                   last_credited_at = NOW()
               WHERE user_id = %s""",
            (designs, designs, user_id)
        )

    db.commit()
    cur.close()
    return designs


# ══════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════

@payment_bp.route("/api/payments/pricing", methods=["GET"])
def get_pricing():
    """Public endpoint: return all product pricing from registry."""
    products = []
    for pid, cfg in PRICE_REGISTRY.items():
        if cfg.is_active:
            products.append({
                "product_id": cfg.product_id,
                "display_name": cfg.display_name,
                "product_type": cfg.product_type.value,
                "price_inr": cfg.price_inr,
                "designs_included": cfg.designs_included,
                "period": cfg.period,
                "max_seats": cfg.max_seats,
                "description": cfg.description,
            })

    return jsonify({
        "products": products,
        "top_up_price_inr": TOPUP_PRICE_INR,
        "free_trial_runs": FREE_TRIAL_RUNS,
        "currency": "INR",
    }), 200


@payment_bp.route("/api/payments/token-balance", methods=["GET"])
@require_auth
def get_token_balance():
    """Get current user's token balance and subscription status."""
    usage = check_usage(g.user["email"])
    return jsonify(usage), 200


@payment_bp.route("/api/payments/create-order", methods=["POST"])
@require_auth
def create_order():
    """Create a Razorpay order. Server-authoritative pricing — never trusts client amounts."""
    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id", "")
    raw_quantity = data.get("quantity", 1)

    # Type safety: reject non-string product_id
    if not isinstance(product_id, str):
        return jsonify({"error": "Invalid product_id."}), 400

    # Validate quantity using centralized validator (handles NaN, Inf, float, etc.)
    valid, quantity, err = validate_quantity(raw_quantity)
    if not valid:
        return jsonify({"error": err}), 400

    # Validate
    error = validate_order_request(product_id, quantity)
    if error:
        return jsonify({"error": error}), 400

    # Calculate amount from server-side registry (NEVER from client)
    amount_paise = get_amount_paise(product_id, quantity)

    # Determine designs to credit for display
    designs = get_designs_for_product(product_id, quantity)

    # Get user info for Razorpay prefill
    user_row = fetch_one(
        "SELECT id, full_name, email FROM users WHERE email = %s",
        (g.user["email"],)
    )
    user_id = user_row["id"]
    import re as _re
    raw_name = user_row.get("full_name") or g.user["email"].split("@")[0]
    user_name = _re.sub(r"[^a-zA-Z\s]", " ", raw_name).strip()
    if len(user_name) < 3:
        user_name = "VigyanLLM User"

    # Create Razorpay order
    receipt = f"pf_{int(time.time())}_{product_id}_{quantity}"
    if not rz_client:
        return jsonify({"error": "Payment service not configured."}), 503
    try:
        rz_order = rz_client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt,
            "notes": {
                "email": g.user["email"],
                "user_id": str(user_id),
                "product_id": product_id,
                "quantity": str(quantity),
                "designs": str(designs),
            }
        })
    except Exception as e:
        logger.error(f"Razorpay order creation failed: {e}")
        return jsonify({"error": "Payment service unavailable."}), 500

    # Persist order in database
    execute(
        """INSERT INTO payments
           (user_id, gateway_order_id, amount, currency, status, product_type, tokens_purchased, metadata)
           VALUES (%s, %s, %s, 'INR', 'initiated', %s, %s, %s)""",
        (user_id, rz_order["id"], amount_paise / 100, product_id, designs,
         json.dumps({"quantity": quantity, "receipt": receipt}))
    )

    log_action(g.user["email"], "order_created",
               f"Order {rz_order['id']} for {product_id} ({designs} designs), ₹{amount_paise // 100}")

    return jsonify({
        "order_id": rz_order["id"],
        "amount": amount_paise,
        "currency": "INR",
        "key_id": RAZORPAY_KEY_ID,
        "product_id": product_id,
        "tokens": designs,
        "description": f"VigyanLLM: {designs} design(s)",
        "theme": {"color": "#2563EB"},
        "prefill": {
            "name": user_name,
            "email": g.user["email"],
        }
    }), 200


@payment_bp.route("/api/payments/verify-payment", methods=["POST"])
@require_auth
def verify_payment():
    """Verify Razorpay payment signature and credit tokens atomically."""
    data = request.get_json(silent=True) or {}
    razorpay_payment_id = data.get("razorpay_payment_id", "")
    razorpay_order_id = data.get("razorpay_order_id", "")
    razorpay_signature = data.get("razorpay_signature", "")

    if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
        return jsonify({"error": "Missing payment verification fields."}), 400

    # Verify HMAC-SHA256 signature
    if not _verify_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
        logger.warning(f"Signature mismatch for order {razorpay_order_id} by {g.user['email']}")
        execute(
            """INSERT INTO system_events (severity, module, message, context)
               VALUES ('WARNING', 'payments', 'Signature verification failed', %s)""",
            (json.dumps({"order_id": razorpay_order_id, "email": g.user["email"]}),)
        )
        return jsonify({"error": "Payment verification failed."}), 400

    # Look up order
    order = fetch_one(
        """SELECT p.id, p.user_id, p.product_type, p.tokens_purchased, p.status,
                  p.metadata
           FROM payments p
           JOIN users u ON u.id = p.user_id
           WHERE p.gateway_order_id = %s AND u.email = %s""",
        (razorpay_order_id, g.user["email"])
    )

    if not order:
        return jsonify({"error": "Order not found."}), 404

    # Get quantity from metadata
    metadata = json.loads(order.get("metadata") or "{}") if isinstance(order.get("metadata"), str) else (order.get("metadata") or {})
    quantity = int(metadata.get("quantity", 1))

    # Atomic idempotent credit
    tokens_credited = _credit_tokens_atomic(
        order["user_id"], razorpay_order_id, order["product_type"],
        quantity, razorpay_payment_id
    )

    log_action(g.user["email"], "payment_verified",
               f"order={razorpay_order_id} payment={razorpay_payment_id} tokens={tokens_credited}")

    # Return updated balance
    usage = check_usage(g.user["email"])
    return jsonify({
        "success": True,
        "tokens_credited": tokens_credited,
        "message": f"{tokens_credited} token(s) credited." if tokens_credited > 0
                   else "Payment already processed.",
        "usage": usage,
    }), 200


@payment_bp.route("/api/payments/webhook", methods=["POST"])
def razorpay_webhook():
    """
    Razorpay server-to-server webhook.
    Always returns 200 to prevent retry storms.
    Uses standalone DB connection (no Flask request auth context).
    """
    raw_body = request.get_data(as_text=True)
    webhook_signature = request.headers.get("X-Razorpay-Signature", "")

    # Verify webhook signature
    expected_sig = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode(),
        raw_body.encode(),
        hashlib.sha256
    ).hexdigest()

    # Store webhook regardless of validation
    validation_status = "verified" if hmac.compare_digest(expected_sig, webhook_signature) else "untrusted"

    try:
        event = json.loads(raw_body)
    except Exception:
        return jsonify({"status": "invalid_json"}), 200

    event_type = event.get("event", "")

    # Log webhook to gateway_webhooks table
    try:
        conn = get_db_standalone()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO gateway_webhooks (raw_payload, event_type, validation_status, http_headers)
               VALUES (%s, %s, %s, %s)""",
            (json.dumps(event), event_type, validation_status,
             json.dumps(dict(request.headers)))
        )
        conn.commit()

        if validation_status == "untrusted":
            logger.warning(f"Webhook signature failed for event: {event_type}")
            cur.close()
            conn.close()
            return jsonify({"status": "signature_invalid"}), 200

        # Process payment.captured
        if event_type == "payment.captured":
            payload = event.get("payload", {}).get("payment", {}).get("entity", {})
            order_id = payload.get("order_id", "")
            payment_id = payload.get("id", "")
            notes = payload.get("notes", {})
            email = notes.get("email", "")
            product_id = notes.get("product_id", "")
            quantity = int(notes.get("quantity", "1"))

            if order_id and email:
                # Find user and order
                cur.execute(
                    """SELECT p.id, p.user_id, p.product_type, p.tokens_purchased, p.status
                       FROM payments p
                       JOIN users u ON u.id = p.user_id
                       WHERE p.gateway_order_id = %s AND u.email = %s""",
                    (order_id, email)
                )
                order_row = cur.fetchone()

                if order_row and order_row["status"] in ("initiated", "authorized"):
                    user_id = order_row["user_id"]
                    tokens = order_row["tokens_purchased"] or quantity

                    # Conditional update (idempotent)
                    cur.execute(
                        """UPDATE payments SET status = 'captured', captured_at = NOW(),
                                  gateway_payment_id = %s
                           WHERE gateway_order_id = %s AND status IN ('initiated', 'authorized')""",
                        (payment_id, order_id)
                    )

                    if cur.rowcount > 0:
                        # Credit tokens
                        cur.execute(
                            """UPDATE token_balances
                               SET balance = balance + %s,
                                   total_purchased = total_purchased + %s,
                                   last_credited_at = NOW()
                               WHERE user_id = %s""",
                            (tokens, tokens, user_id)
                        )

                        # Handle subscription
                        if product_id == "base_subscription":
                            cur.execute(
                                """INSERT INTO subscriptions (user_id, is_active, started_at, expires_at, last_renewed_at)
                                   VALUES (%s, TRUE, NOW(), NOW() + INTERVAL '365 days', NOW())
                                   ON CONFLICT (user_id) DO UPDATE SET
                                     is_active = TRUE, expires_at = NOW() + INTERVAL '365 days', last_renewed_at = NOW()""",
                                (user_id,)
                            )

                        conn.commit()
                        logger.info(f"Webhook: credited {tokens} tokens to user_id={user_id} for order {order_id}")

        elif event_type == "payment.failed":
            payload = event.get("payload", {}).get("payment", {}).get("entity", {})
            order_id = payload.get("order_id", "")
            if order_id:
                cur.execute(
                    """UPDATE payments SET status = 'failed', failed_at = NOW()
                       WHERE gateway_order_id = %s AND status IN ('initiated', 'authorized')""",
                    (order_id,)
                )
                conn.commit()

        # ── Subscription Events ───────────────────────────────────────────
        elif event_type == "subscription.charged":
            # Monthly renewal — reset quota for next billing cycle
            payload = event.get("payload", {}).get("subscription", {}).get("entity", {})
            sub_id = payload.get("id", "")
            if sub_id:
                cur.execute(
                    """UPDATE subscriptions SET quota_used = 0,
                              quota_reset_at = NOW() + INTERVAL '30 days',
                              last_renewed_at = NOW(),
                              expires_at = NOW() + INTERVAL '30 days'
                       WHERE razorpay_subscription_id = %s AND is_active = TRUE""",
                    (sub_id,)
                )
                conn.commit()
                logger.info(f"Webhook: subscription.charged — quota reset for sub {sub_id}")

        elif event_type == "subscription.authenticated":
            # New subscription authorized — activate plan
            payload = event.get("payload", {}).get("subscription", {}).get("entity", {})
            sub_id = payload.get("id", "")
            plan_id = payload.get("notes", {}).get("plan_id", "")
            email = payload.get("notes", {}).get("email", "")
            if sub_id and email and plan_id:
                user_row = cur.execute("SELECT id FROM users WHERE email = %s", (email,))
                user_row = cur.fetchone()
                if user_row and plan_id in PRICE_REGISTRY:
                    product = PRICE_REGISTRY[plan_id]
                    cur.execute(
                        """INSERT INTO subscriptions (user_id, is_active, plan_id, plan_type,
                               monthly_quota, quota_used, started_at, expires_at,
                               last_renewed_at, max_seats, razorpay_subscription_id, quota_reset_at)
                           VALUES (%s, TRUE, %s, %s, %s, 0, NOW(), NOW() + INTERVAL '30 days', NOW(), %s, %s, NOW() + INTERVAL '30 days')
                           ON CONFLICT (user_id) DO UPDATE SET
                             is_active = TRUE, plan_id = %s, plan_type = %s,
                             monthly_quota = %s, quota_used = 0,
                             expires_at = NOW() + INTERVAL '30 days',
                             last_renewed_at = NOW(), max_seats = %s,
                             razorpay_subscription_id = %s,
                             quota_reset_at = NOW() + INTERVAL '30 days'""",
                        (user_row["id"], plan_id, plan_id, product.designs_included, product.max_seats, sub_id,
                         plan_id, plan_id, product.designs_included, product.max_seats, sub_id)
                    )
                    conn.commit()
                    logger.info(f"Webhook: subscription.authenticated — {email} activated {plan_id}")

        elif event_type in ("subscription.halted", "subscription.cancelled"):
            # Subscription stopped — deactivate
            payload = event.get("payload", {}).get("subscription", {}).get("entity", {})
            sub_id = payload.get("id", "")
            if sub_id:
                cur.execute(
                    """UPDATE subscriptions SET is_active = FALSE
                       WHERE razorpay_subscription_id = %s""",
                    (sub_id,)
                )
                conn.commit()
                logger.info(f"Webhook: {event_type} — subscription {sub_id} deactivated")

        cur.close()
        conn.close()

    except Exception as e:
        logger.error(f"Webhook processing error: {e}")

    return jsonify({"status": "ok"}), 200


# ══════════════════════════════════════════════════════════════════════════
# ADMIN: Financial Dashboard Endpoints
# ══════════════════════════════════════════════════════════════════════════

@payment_bp.route("/api/payments/financial-summary", methods=["GET"])
@require_admin
def financial_summary():
    """Admin-only: Get P&L, ROI, and user profitability data."""
    pnl = fetch_all("SELECT * FROM v_monthly_pnl LIMIT 12")
    roi = fetch_all("SELECT * FROM v_roi_dashboard LIMIT 12")
    token_econ = fetch_all("SELECT * FROM v_token_economics LIMIT 12")
    admin_costs = fetch_all("SELECT * FROM v_admin_cost_breakdown LIMIT 50")
    top_users = fetch_all("SELECT * FROM v_user_profitability LIMIT 20")

    return jsonify({
        "monthly_pnl": pnl,
        "roi_dashboard": roi,
        "token_economics": token_econ,
        "admin_cost_breakdown": admin_costs,
        "top_users_by_profit": top_users,
    }), 200


@payment_bp.route("/api/payments/revenue-stats", methods=["GET"])
@require_admin
def revenue_stats():
    """
    Admin-only: Real revenue = only money actually paid to us (captured payments).
    Cost = infrastructure cost from pipeline runs (cost_ledger).
    This separates revenue (payments) from cost (pipeline usage).
    """
    # Revenue: only from captured payments (actual money received)
    rev = fetch_one("""
        SELECT
            COALESCE(SUM(amount), 0) AS total_revenue_inr,
            COUNT(*) AS total_payments,
            COALESCE(SUM(tokens_purchased), 0) AS total_tokens_sold
        FROM payments
        WHERE status = 'captured'
    """)

    # Cost: infrastructure cost from all pipeline runs
    cost = fetch_one("""
        SELECT
            COALESCE(SUM(total_cogs_inr), 0) AS total_cost_inr,
            COUNT(*) AS total_operations,
            COALESCE(SUM(CASE WHEN is_billable THEN total_cogs_inr ELSE 0 END), 0) AS paid_user_cost,
            COALESCE(SUM(CASE WHEN NOT is_billable THEN total_cogs_inr ELSE 0 END), 0) AS admin_free_cost
        FROM cost_ledger
    """) or {"total_cost_inr": 0, "total_operations": 0, "paid_user_cost": 0, "admin_free_cost": 0}

    total_rev = float(rev["total_revenue_inr"]) if rev else 0
    total_cost = float(cost["total_cost_inr"]) if cost else 0
    margin = total_rev - total_cost

    return jsonify({
        "revenue": {
            "total_inr": total_rev,
            "payments_count": rev["total_payments"] if rev else 0,
            "tokens_sold": rev["total_tokens_sold"] if rev else 0,
        },
        "cost": {
            "total_inr": total_cost,
            "operations_count": cost["total_operations"],
            "paid_user_cost_inr": float(cost["paid_user_cost"]),
            "admin_free_cost_inr": float(cost["admin_free_cost"]),
        },
        "margin": {
            "gross_profit_inr": margin,
            "margin_percent": round(margin / total_rev * 100, 1) if total_rev > 0 else 0,
        }
    }), 200


@payment_bp.route("/api/payments/user-profitability/<int:user_id>", methods=["GET"])
@require_admin
def user_profitability(user_id: int):
    """Admin-only: Get financial summary for a specific user."""
    summary = fetch_one("SELECT * FROM fn_user_financial_summary(%s)", (user_id,))
    if not summary:
        return jsonify({"error": "User not found."}), 404
    return jsonify(summary), 200

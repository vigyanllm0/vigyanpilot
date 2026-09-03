#!/usr/bin/env python3
"""
VigyanLLM Razorpay Payment Integration — 4-Tier Subscription
==============================================================
POST /api/payments/create-order  — Create Razorpay order for a plan
POST /api/payments/verify-payment — Verify & activate plan
POST /api/payments/webhook       — Razorpay server-to-server webhook
GET  /api/payments/pricing       — Public pricing endpoint
GET  /api/payments/status        — Get user's current plan status
"""

import hashlib
import hmac
import json
import logging
import os
import time

import razorpay
from flask import Blueprint, g, jsonify, request

from .auth import (
    DB_PATH,
    get_db,
    get_user_plan,
    log_action,
    require_auth,
)
from .price_registry import (
    PLAN_REGISTRY,
    ACADEMIC_DISCOUNT_PCT,
    get_academic_price,
    get_amount_paise,
    validate_plan,
    get_tier_from_plan,
)

logger = logging.getLogger("primerforge.payment")

payment_bp = Blueprint('payment', __name__)

# ── Razorpay Configuration ────────────────────────────────────────────────
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")

rz_client = (
    razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET
    else None
)

if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
    logger.warning("RAZORPAY_KEY_ID/RAZORPAY_KEY_SECRET not set — payment endpoints return 503")


def _current_client():
    return rz_client


def _sanitize_name(raw_name: str) -> str:
    """Sanitize name for Razorpay (letters/spaces only, min 3 chars)."""
    import re
    name = re.sub(r'[^a-zA-Z\s]', ' ', raw_name).strip()
    if len(name) < 3:
        name = "VigyanLLM User"
    return name


def _compute_plan_expiry(plan_id: str) -> int:
    """Compute plan expiry timestamp based on billing cycle."""
    plan = PLAN_REGISTRY.get(plan_id)
    if not plan:
        return 0
    now = time.time()
    if plan.billing.value == "monthly":
        return int(now + 30 * 86400)
    elif plan.billing.value == "yearly":
        return int(now + 365 * 86400)
    elif plan.billing.value == "custom":
        return int(now + 365 * 86400)  # Default 1 year for enterprise
    return int(now + 30 * 86400)


# ══════════════════════════════════════════════════════════════════════════
# CREATE ORDER
# ══════════════════════════════════════════════════════════════════════════

@payment_bp.route('/api/payments/create-order', methods=['POST'])
@payment_bp.route('/api/create-order', methods=['POST'])
@require_auth
def create_order():
    """Create a Razorpay order for a subscription plan.

    Request body: { plan_id: 'pro-monthly' }
    Optional: { plan_id: 'pro-monthly', discount: 30, email: 'user@edu.in' }
    """
    data = request.get_json(silent=True) or {}
    plan_id = data.get("plan_id", "")

    if not plan_id:
        return jsonify({"error": "Missing plan_id. Options: pro-monthly, pro-yearly, lab-monthly, lab-yearly, enterprise"}), 400

    err = validate_plan(plan_id)
    if err:
        return jsonify({"error": err}), 400

    plan = PLAN_REGISTRY[plan_id]

    # Calculate amount
    amount = get_amount_paise(plan_id)

    # Apply academic discount if applicable
    discount = data.get("discount", 0)
    if discount:
        # Verify discount is reasonable (max 30%)
        discount = min(int(discount), ACADEMIC_DISCOUNT_PCT)
        amount = int(amount * (100 - discount) / 100)

    if amount < 100 and amount > 0:
        return jsonify({"error": "Minimum amount is ₹1 (100 paise)."}), 400

    if not _current_client():
        return jsonify({
            "error": "Payment service not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET."
        }), 503

    # Get user info for prefill
    db = get_db()
    user_row = db.execute("SELECT name, email, is_academic FROM users WHERE email=?",
                          (g.user['email'],)).fetchone()
    raw_name = (user_row['name'] if user_row and user_row['name'] else
                g.user['email'].split('@')[0])
    user_name = _sanitize_name(raw_name)
    user_email = g.user['email']

    try:
        order = _current_client().order.create({
            "amount": amount,
            "currency": "INR",
            "receipt": f"pf_{int(time.time())}_{plan_id}",
            "notes": {
                "email": user_email,
                "plan_id": plan_id,
                "plan_name": plan.display_name,
                "tier": plan.tier.value,
                "product": "VigyanLLM Subscription"
            }
        })
    except razorpay.errors.BadRequestError as e:
        logger.error("Razorpay BadRequest: %s", e)
        return jsonify({"error": "Payment service error. Please try again."}), 500
    except Exception as e:
        logger.error("Razorpay error: %s", e)
        return jsonify({"error": "Payment service unavailable."}), 500

    # Store order in DB
    db.execute(
        """INSERT INTO payments (user_email, amount, upi_ref, status, runs_purchased, product_type, plan_id, billing_cycle)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_email, amount // 100, order['id'], "created", 0, "subscription", plan_id, plan.billing.value)
    )
    db.commit()

    log_action(user_email, "order_created",
               f"Order {order['id']} for plan {plan_id}, ₹{amount // 100}")

    return jsonify({
        "order_id": order['id'],
        "amount": amount,
        "currency": "INR",
        "key_id": RAZORPAY_KEY_ID,
        "plan_id": plan_id,
        "plan_name": plan.display_name,
        "tier": plan.tier.value,
        "billing": plan.billing.value,
        "description": f"VigyanLLM {plan.display_name} ({plan.billing.value})",
        "prefill": {
            "name": user_name,
            "email": user_email,
        }
    }), 200


# ══════════════════════════════════════════════════════════════════════════
# VERIFY PAYMENT & ACTIVATE PLAN
# ══════════════════════════════════════════════════════════════════════════

@payment_bp.route('/api/payments/verify-payment', methods=['POST'])
@payment_bp.route('/api/verify-payment', methods=['POST'])
@require_auth
def verify_payment():
    """Verify Razorpay payment signature and activate the subscription plan.

    Request body: { razorpay_payment_id, razorpay_order_id, razorpay_signature }
    """
    data = request.get_json(silent=True) or {}
    razorpay_payment_id = data.get('razorpay_payment_id', '')
    razorpay_order_id = data.get('razorpay_order_id', '')
    razorpay_signature = data.get('razorpay_signature', '')

    if not razorpay_payment_id or not razorpay_order_id or not razorpay_signature:
        return jsonify({"error": "Missing payment verification fields."}), 400
    if not RAZORPAY_KEY_SECRET:
        return jsonify({"error": "Payment service not configured."}), 503

    # Verify signature
    message = f"{razorpay_order_id}|{razorpay_payment_id}"
    expected_sig = hmac.new(
        RAZORPAY_KEY_SECRET.encode(), message.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, razorpay_signature):
        logger.warning("Signature mismatch for order %s", razorpay_order_id)
        return jsonify({"error": "Payment verification failed. Signature mismatch."}), 400

    email = g.user['email']
    db = get_db()

    # Find the order
    order_row = db.execute(
        """SELECT id, amount, plan_id, billing_cycle, status FROM payments
           WHERE user_email=? AND upi_ref=?
           ORDER BY id DESC LIMIT 1""",
        (email, razorpay_order_id)
    ).fetchone()

    if not order_row:
        return jsonify({"error": "Order not found."}), 404

    if order_row["status"] == "verified":
        plan = get_user_plan(email)
        return jsonify({
            "success": True,
            "message": "Payment already verified.",
            "plan": plan,
        }), 200

    # Update payment status
    cur = db.execute(
        """UPDATE payments SET status='verified', upi_ref=?, verified_at=?
           WHERE id=? AND status!='verified'""",
        (f"{razorpay_order_id}|{razorpay_payment_id}", time.time(), order_row["id"])
    )
    if cur.rowcount == 0:
        db.commit()
        return jsonify({"success": True, "message": "Payment already verified."}), 200

    # Activate plan for user
    plan_id = order_row["plan_id"]
    billing_cycle = order_row["billing_cycle"] or "monthly"
    tier = get_tier_from_plan(plan_id)
    expires_at = _compute_plan_expiry(plan_id)

    db.execute(
        """UPDATE users SET
           plan=?, billing_cycle=?, plan_activated_at=?, plan_expires_at=?
           WHERE email=?""",
        (tier, billing_cycle, time.time(), expires_at, email)
    )
    db.commit()

    log_action(email, "plan_activated",
               f"Plan {tier} ({billing_cycle}) activated via Razorpay order {razorpay_order_id}")

    return jsonify({
        "success": True,
        "message": f"Payment verified! {tier.capitalize()} plan activated.",
        "plan": tier,
        "billing": billing_cycle,
        "expires_at": expires_at,
    }), 200


# ══════════════════════════════════════════════════════════════════════════
# PLAN STATUS
# ══════════════════════════════════════════════════════════════════════════

@payment_bp.route('/api/payments/status', methods=['GET'])
@payment_bp.route('/api/payment/status', methods=['GET'])
@require_auth
def payment_status():
    """Get current user's plan and usage status."""
    email = g.user['email']
    db = get_db()
    row = db.execute(
        """SELECT plan, billing_cycle, plan_activated_at, plan_expires_at,
                  is_academic, academic_discount
           FROM users WHERE email=?""",
        (email,)
    ).fetchone()

    if not row:
        return jsonify({"error": "User not found"}), 404

    # Auto-detect academic status if not yet set
    is_academic = bool(row["is_academic"])
    if not is_academic:
        try:
            domain = email.split('@')[1].lower()
            import re
            if re.search(r'\.(edu|ac\.in|edu\.in|ac\.uk|edu\.au|ac\.nz|ac\.jp|edu\.cn|ac\.cn|ac\.kr|edu\.kr|ac\.th|edu\.tw|ac\.za|edu\.mx|ac\.cl|edu\.ar|edu\.sg|edu\.my|edu\.hk|ac\.id|edu\.eg|ac\.ma|edu\.vn|edu\.pk|ac\.ir|edu\.tr|edu\.jo|edu\.lb|ac\.il)(\.[a-z]{2})?$', domain, re.I) or '.edu.' in domain or '.ac.' in domain:
                db.execute("UPDATE users SET is_academic=1 WHERE email=?", (email,))
                db.commit()
                is_academic = True
        except:
            pass

    from .auth import check_daily_usage, check_monthly_api_usage
    daily = check_daily_usage(email)
    monthly_api = check_monthly_api_usage(email)

    role = g.user.get("role", "user") if hasattr(g, 'user') else "user"

    return jsonify({
        "plan": row["plan"] or "free",
        "billing_cycle": row["billing_cycle"] or "monthly",
        "plan_activated_at": row["plan_activated_at"] or 0,
        "plan_expires_at": row["plan_expires_at"] or 0,
        "is_academic": is_academic,
        "academic_discount": row["academic_discount"] or 0,
        "role": role,
        "daily": daily,
        "api": monthly_api,
        "razorpay_key_id": RAZORPAY_KEY_ID,
    }), 200


# ══════════════════════════════════════════════════════════════════════════
# PRICING ENDPOINT
# ══════════════════════════════════════════════════════════════════════════

@payment_bp.route('/api/payments/pricing', methods=['GET'])
def pricing():
    """Public pricing endpoint."""
    plans = []
    for cfg in PLAN_REGISTRY.values():
        if not cfg.is_active:
            continue
        plans.append({
            "plan_id": cfg.plan_id,
            "display_name": cfg.display_name,
            "tier": cfg.tier.value,
            "billing": cfg.billing.value,
            "price_inr": cfg.price_inr,
            "academic_price_inr": get_academic_price(cfg.price_inr) if cfg.price_inr > 0 else 0,
            "daily_analyses": cfg.daily_analyses,
            "batch_max_seq": cfg.batch_max_seq,
            "api_calls_per_month": cfg.api_calls_per_month,
            "max_seats": cfg.max_seats,
            "period": cfg.period,
            "description": cfg.description,
        })

    return jsonify({
        "plans": plans,
        "academic_discount_pct": ACADEMIC_DISCOUNT_PCT,
        "currency": "INR",
    }), 200


# ══════════════════════════════════════════════════════════════════════════
# USAGE CHECK & RECORD (for Phase 2)
# ══════════════════════════════════════════════════════════════════════════

@payment_bp.route('/api/usage/check', methods=['GET'])
@require_auth
def usage_check():
    """Check if user can run an analysis (daily limit)."""
    from .auth import check_daily_usage
    tool = request.args.get("tool", "")
    usage = check_daily_usage(g.user['email'], tool)
    return jsonify(usage), 200


@payment_bp.route('/api/usage/record', methods=['POST'])
@require_auth
def usage_record():
    """Record a completed analysis."""
    data = request.get_json(silent=True) or {}
    tool = data.get("tool", "")
    sequences_count = int(data.get("sequences_count", 1))
    from .auth import record_daily_usage
    record_daily_usage(g.user['email'], tool, sequences_count)
    return jsonify({"success": True}), 200


# ══════════════════════════════════════════════════════════════════════════
# WEBHOOK
# ══════════════════════════════════════════════════════════════════════════

@payment_bp.route('/api/payment/webhook', methods=['POST'])
def razorpay_webhook():
    """Razorpay server-to-server webhook for subscription events."""
    raw_body = request.get_data(as_text=True)
    webhook_signature = request.headers.get('X-Razorpay-Signature', '')
    webhook_secret = os.environ.get('RAZORPAY_WEBHOOK_SECRET', RAZORPAY_KEY_SECRET)

    if not webhook_signature:
        return jsonify({"error": "Missing webhook signature"}), 400

    expected_sig = hmac.new(
        webhook_secret.encode(), raw_body.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, webhook_signature):
        logger.warning("Webhook signature verification failed")
        return jsonify({"error": "Invalid signature"}), 400

    try:
        event = json.loads(raw_body)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    event_type = event.get('event', '')
    logger.info("Razorpay webhook: %s", event_type)

    if event_type == 'payment.captured':
        payload = event.get('payload', {}).get('payment', {}).get('entity', {})
        order_id = payload.get('order_id', '')
        email = payload.get('email', '') or payload.get('notes', {}).get('email', '')

        if order_id and email:
            import sqlite3
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row

            order = conn.execute(
                "SELECT plan_id, billing_cycle, status FROM payments WHERE upi_ref LIKE ? AND user_email=?",
                (f"{order_id}%", email)
            ).fetchone()

            if order and order['status'] != 'verified':
                plan_id = order['plan_id']
                billing_cycle = order['billing_cycle'] or 'monthly'
                tier = get_tier_from_plan(plan_id)
                expires_at = _compute_plan_expiry(plan_id)

                conn.execute(
                    "UPDATE payments SET status='verified', verified_at=? WHERE upi_ref LIKE ? AND user_email=? AND status!='verified'",
                    (time.time(), f"{order_id}%", email)
                )
                conn.execute(
                    "UPDATE users SET plan=?, billing_cycle=?, plan_activated_at=?, plan_expires_at=? WHERE email=?",
                    (tier, billing_cycle, time.time(), expires_at, email)
                )
                conn.commit()
                logger.info("Webhook: activated %s for %s (order %s)", tier, email, order_id)

            conn.close()

    elif event_type == 'payment.failed':
        payload = event.get('payload', {}).get('payment', {}).get('entity', {})
        order_id = payload.get('order_id', '')
        logger.warning("Payment failed for order %s", order_id)

    elif event_type == 'subscription.activated':
        payload = event.get('payload', {}).get('subscription', {}).get('entity', {})
        sub_id = payload.get('id', '')
        logger.info("Subscription activated: %s", sub_id)
        _activate_trial_to_paid(sub_id)

    elif event_type == 'subscription.charged':
        payload = event.get('payload', {}).get('subscription', {}).get('entity', {})
        sub_id = payload.get('id', '')
        logger.info("Subscription charged: %s", sub_id)

    elif event_type == 'subscription.halted':
        payload = event.get('payload', {}).get('subscription', {}).get('entity', {})
        sub_id = payload.get('id', '')
        logger.warning("Subscription halted: %s", sub_id)
        _halt_trial_subscription(sub_id)

    return jsonify({"status": "ok"}), 200


def _activate_trial_to_paid(subscription_id: str):
    """Webhook handler: trial ended, subscription activated → upgrade user to Pro."""
    import sqlite3 as _sqlite3
    conn = _sqlite3.connect(DB_PATH)
    conn.row_factory = _sqlite3.Row
    try:
        sub = conn.execute(
            "SELECT user_email, promo_code FROM trial_subscriptions WHERE razorpay_subscription_id=?",
            (subscription_id,)
        ).fetchone()
        if not sub:
            logger.warning("Trial sub not found for activation: %s", subscription_id)
            return
        email = sub['user_email']
        conn.execute("UPDATE trial_subscriptions SET status='active' WHERE razorpay_subscription_id=?",
                     (subscription_id,))
        conn.execute(
            "UPDATE users SET plan='pro', trial_ends_at=0, plan_activated_at=?, plan_expires_at=0 WHERE email=?",
            (int(time.time()), email)
        )
        conn.commit()
        logger.info("Trial→paid activated for %s", email)
    finally:
        conn.close()


def _halt_trial_subscription(subscription_id: str):
    """Webhook handler: subscription halted (payment failed after retries) → downgrade to free."""
    import sqlite3 as _sqlite3
    conn = _sqlite3.connect(DB_PATH)
    conn.row_factory = _sqlite3.Row
    try:
        sub = conn.execute(
            "SELECT user_email FROM trial_subscriptions WHERE razorpay_subscription_id=?",
            (subscription_id,)
        ).fetchone()
        if not sub:
            return
        email = sub['user_email']
        conn.execute("UPDATE trial_subscriptions SET status='halted' WHERE razorpay_subscription_id=?",
                     (subscription_id,))
        conn.execute(
            "UPDATE users SET plan='free', trial_ends_at=0 WHERE email=?",
            (email,)
        )
        conn.commit()
        logger.info("Trial subscription halted → free for %s", email)
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════
# PROMO CODE VALIDATE
# ══════════════════════════════════════════════════════════════════════════

@payment_bp.route('/api/promo/validate', methods=['POST'])
@require_auth
def validate_promo():
    """Validate a promo code and return trial details.

    Request body: { code: 'IITB-2026-30D' }
    """
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip().upper()

    if not code:
        return jsonify({"error": "Please enter a promo code."}), 400

    db = get_db()
    row = db.execute("SELECT * FROM promo_codes WHERE code=?", (code,)).fetchone()

    if not row:
        return jsonify({"error": "Invalid promo code."}), 404

    # Check expiry
    if row["expires_at"] and row["expires_at"] > 0 and row["expires_at"] < time.time():
        return jsonify({"error": "This promo code has expired."}), 410

    # Check single-use
    if row["used_count"] >= row["max_uses"]:
        return jsonify({"error": "This promo code has already been used."}), 410

    # Check if user already used a promo code
    user_row = db.execute("SELECT promo_code_used FROM users WHERE email=?",
                          (g.user['email'],)).fetchone()
    if user_row and user_row["promo_code_used"]:
        return jsonify({"error": "You have already used a promo code."}), 409

    return jsonify({
        "valid": True,
        "code": code,
        "trial_days": row["trial_days"],
        "daily_analyses": row["daily_analyses"],
        "batch_max": row["batch_max"],
        "has_export": bool(row["has_export"]),
        "price_inr": row["price_inr"],
        "currency": row["currency"],
        "tier": row["tier"],
    }), 200


# ══════════════════════════════════════════════════════════════════════════
# PROMO CODE APPLY — Create Razorpay Subscription + Activate Trial
# ══════════════════════════════════════════════════════════════════════════

@payment_bp.route('/api/promo/apply', methods=['POST'])
@require_auth
def apply_promo():
    """Apply promo code — two-step flow.

    Step 1 (create_order): { code, step: 'create_order' }
    → Returns Razorpay order for ₹1 verification charge

    Step 2 (verify): { code, razorpay_payment_id, razorpay_order_id, razorpay_signature }
    → Verifies payment, creates subscription, activates trial
    """
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip().upper()
    step = data.get("step", "")

    if not code:
        return jsonify({"error": "Missing promo code."}), 400

    db = get_db()

    # ── Validate promo code (shared) ──
    row = db.execute("SELECT * FROM promo_codes WHERE code=?", (code,)).fetchone()
    if not row:
        return jsonify({"error": "Invalid promo code."}), 404
    if row["expires_at"] and row["expires_at"] > 0 and row["expires_at"] < time.time():
        return jsonify({"error": "This promo code has expired."}), 410
    if row["used_count"] >= row["max_uses"]:
        return jsonify({"error": "This promo code has already been used."}), 410

    email = g.user['email']
    user_row = db.execute("SELECT promo_code_used FROM users WHERE email=?", (email,)).fetchone()
    if user_row and user_row["promo_code_used"]:
        return jsonify({"error": "You have already used a promo code."}), 409

    # ── Step 1: Create ₹1 Razorpay order ──
    if step == "create_order":
        if not _current_client():
            return jsonify({"error": "Payment service not configured."}), 503

        user_info = db.execute("SELECT name FROM users WHERE email=?", (email,)).fetchone()
        user_name = _sanitize_name(user_info["name"] if user_info and user_info["name"] else email.split("@")[0])

        try:
            order = _current_client().order.create({
                "amount": 100,  # ₹1 in paise
                "currency": row["currency"] or "INR",
                "receipt": f"promo_{int(time.time())}_{code}",
                "notes": {
                    "email": email,
                    "promo_code": code,
                    "type": "trial_verification"
                }
            })
        except Exception as e:
            logger.error("Failed to create promo order: %s", e)
            return jsonify({"error": "Failed to create payment order."}), 500

        return jsonify({
            "order_id": order["id"],
            "amount": 100,
            "currency": row["currency"] or "INR",
            "key_id": RAZORPAY_KEY_ID,
            "prefill": {"email": email, "name": user_name}
        }), 200

    # ── Step 2: Verify payment + activate trial ──
    rz_payment_id = data.get("razorpay_payment_id", "")
    rz_order_id = data.get("razorpay_order_id", "")
    rz_signature = data.get("razorpay_signature", "")

    if not rz_payment_id or not rz_order_id or not rz_signature:
        return jsonify({"error": "Missing payment verification fields."}), 400
    if not RAZORPAY_KEY_SECRET:
        return jsonify({"error": "Payment service not configured."}), 503

    # Verify Razorpay signature
    message = f"{rz_order_id}|{rz_payment_id}"
    expected_sig = hmac.new(
        RAZORPAY_KEY_SECRET.encode(), message.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected_sig, rz_signature):
        logger.warning("Promo apply: signature mismatch for %s", email)
        return jsonify({"error": "Payment verification failed."}), 400

    # Create Razorpay Plan (if needed)
    plan_id_cached = row["razorpay_plan_id"]
    if not plan_id_cached and rz_client:
        try:
            rz_plan = rz_client.plan.create({
                "item": {
                    "name": f"VigyanLLM Pro ({row['trial_days']}d trial)",
                    "amount": row["price_inr"] * 100,
                    "currency": row["currency"],
                    "description": f"Academic trial — {row['trial_days']} days free, then {row['currency']} {row['price_inr']}/mo"
                },
                "interval": 1,
                "period": "monthly"
            })
            plan_id_cached = rz_plan["id"]
            db.execute("UPDATE promo_codes SET razorpay_plan_id=? WHERE code=?",
                       (plan_id_cached, code))
            db.commit()
        except Exception as e:
            logger.error("Failed to create Razorpay plan: %s", e)
            return jsonify({"error": "Failed to create subscription plan."}), 500

    # Create Razorpay Subscription with trial period
    if rz_client and plan_id_cached:
        trial_seconds = row["trial_days"] * 86400
        try:
            rz_sub = rz_client.subscription.create({
                "plan_id": plan_id_cached,
                "total_count": 12,
                "quantity": 1,
                "customer_notify": True,
                "start_at": int(time.time()) + trial_seconds,
                "notes": {"promo_code": code, "user_email": email}
            })
            sub_id = rz_sub["id"]
        except Exception as e:
            logger.error("Failed to create Razorpay subscription: %s", e)
            return jsonify({"error": "Failed to create subscription."}), 500
    else:
        sub_id = f"sub_dev_{int(time.time())}"

    # Atomically mark promo code used
    cur = db.execute(
        "UPDATE promo_codes SET used_count = used_count + 1 WHERE code=? AND used_count < max_uses",
        (code,)
    )
    if cur.rowcount == 0:
        db.commit()
        return jsonify({"error": "Code was just claimed by another user."}), 410

    # Activate trial
    trial_ends_at = int(time.time()) + (row["trial_days"] * 86400)
    db.execute(
        """UPDATE users SET plan='trial', trial_ends_at=?, promo_code_used=?,
           razorpay_subscription_id=?, plan_activated_at=? WHERE email=?""",
        (trial_ends_at, code, sub_id, int(time.time()), email)
    )
    db.execute(
        """INSERT INTO trial_subscriptions
           (user_email, promo_code, razorpay_subscription_id, razorpay_plan_id,
            trial_days, trial_started_at, trial_ends_at, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'trial')""",
        (email, code, sub_id, plan_id_cached, row["trial_days"], int(time.time()), trial_ends_at)
    )
    db.commit()

    log_action(email, "trial_activated",
               f"Promo {code}, {row['trial_days']}d trial, sub {sub_id}")

    # Log company expenses: ₹1 verification charge + estimated trial service cost
    _log_expense("verification_charge", f"Razorpay verification charge for promo {code}",
                 1.0, promo_code=code, user_email=email, subscription_id=sub_id,
                 metadata={"razorpay_payment_id": rz_payment_id, "razorpay_order_id": rz_order_id})
    estimated_trial_cost = row["daily_analyses"] * row["trial_days"] * 0.50  # ~₹0.50 per analysis infra cost
    _log_expense("trial_service", f"Estimated {row['trial_days']}d trial service cost ({row['daily_analyses']} analyses/day)",
                 estimated_trial_cost, promo_code=code, user_email=email, subscription_id=sub_id,
                 metadata={"daily_analyses": row["daily_analyses"], "trial_days": row["trial_days"],
                           "price_inr": row["price_inr"], "estimated": True})

    return jsonify({
        "success": True,
        "message": f"Your {row['trial_days']}-day trial is active!",
        "trial_days": row["trial_days"],
        "trial_ends_at": trial_ends_at,
        "subscription_id": sub_id,
        "daily_analyses": row["daily_analyses"],
        "batch_max": row["batch_max"],
        "price_inr": row["price_inr"],
    }), 200


# ══════════════════════════════════════════════════════════════════════════
# TRIAL STATUS
# ══════════════════════════════════════════════════════════════════════════

@payment_bp.route('/api/trial/status', methods=['GET'])
@require_auth
def trial_status():
    """Get trial status for the current user."""
    email = g.user['email']
    db = get_db()

    user = db.execute(
        "SELECT plan, trial_ends_at, promo_code_used, razorpay_subscription_id FROM users WHERE email=?",
        (email,)
    ).fetchone()

    if not user:
        return jsonify({"status": "none"}), 200

    if user["plan"] != "trial":
        return jsonify({"status": "none", "plan": user["plan"]}), 200

    now = time.time()
    trial_ends = user["trial_ends_at"] or 0
    days_remaining = max(0, int((trial_ends - now) / 86400)) if trial_ends > 0 else 0
    is_active = trial_ends > 0 and now < trial_ends

    # Get promo code details
    promo = None
    if user["promo_code_used"]:
        promo = db.execute(
            "SELECT daily_analyses, batch_max, has_export, trial_days, price_inr, currency FROM promo_codes WHERE code=?",
            (user["promo_code_used"],)
        ).fetchone()

    return jsonify({
        "status": "active" if is_active else "expired",
        "plan": "trial",
        "trial_ends_at": trial_ends,
        "days_remaining": days_remaining,
        "promo_code": user["promo_code_used"],
        "subscription_id": user["razorpay_subscription_id"],
        "daily_analyses": promo["daily_analyses"] if promo else 50,
        "batch_max": promo["batch_max"] if promo else 20,
        "has_export": bool(promo["has_export"]) if promo else True,
        "price_inr": promo["price_inr"] if promo else 699,
        "currency": promo["currency"] if promo else "INR",
    }), 200


# ══════════════════════════════════════════════════════════════════════════
# ADMIN: CREATE PROMO CODES
# ══════════════════════════════════════════════════════════════════════════

@payment_bp.route('/api/admin/promo/create', methods=['POST'])
def admin_create_promo():
    """Create promo codes. Admin-only.

    Request body: {
        count: 50,
        prefix: "IITB",
        tier: "pro",
        daily_analyses: 50,
        batch_max: 20,
        trial_days: 30,
        price_inr: 699,
        currency: "INR",
        max_uses: 1,
        expires_at: 0
    }
    """
    from .auth import get_current_user
    user = get_current_user()
    if not user or user.get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403

    data = request.get_json(silent=True) or {}
    count = min(int(data.get("count", 1)), 1000)
    prefix = (data.get("prefix") or "TRIAL").upper().replace(" ", "")
    tier = data.get("tier", "pro")
    daily_analyses = int(data.get("daily_analyses", 50))
    batch_max = int(data.get("batch_max", 20))
    has_export = int(data.get("has_export", 1))
    trial_days = int(data.get("trial_days", 30))
    price_inr = int(data.get("price_inr", 699))
    currency = data.get("currency", "INR")
    max_uses = int(data.get("max_uses", 1))
    expires_at = float(data.get("expires_at", 0))

    import secrets
    import string
    db = get_db()
    codes = []

    for _ in range(count):
        while True:
            suffix = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            code = f"{prefix}-{suffix}"
            try:
                db.execute(
                    """INSERT INTO promo_codes
                       (code, tier, daily_analyses, batch_max, has_export, trial_days,
                        price_inr, currency, max_uses, created_by, expires_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (code, tier, daily_analyses, batch_max, has_export, trial_days,
                     price_inr, currency, max_uses, user["email"], expires_at)
                )
                codes.append(code)
                break
            except Exception:
                continue  # duplicate code, retry

    db.commit()
    log_action(user["email"], "promo_codes_created", f"Created {len(codes)} codes with prefix {prefix}")

    return jsonify({
        "success": True,
        "count": len(codes),
        "codes": codes,
        "prefix": prefix,
        "trial_days": trial_days,
        "tier": tier,
    }), 200


# ══════════════════════════════════════════════════════════════════════════
# ADMIN: LIST PROMO CODES
# ══════════════════════════════════════════════════════════════════════════

@payment_bp.route('/api/admin/promo/list', methods=['GET'])
def admin_list_promos():
    """List all promo codes with usage stats. Admin-only."""
    from .auth import get_current_user
    user = get_current_user()
    if not user or user.get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403

    db = get_db()
    rows = db.execute(
        """SELECT code, tier, daily_analyses, batch_max, has_export, trial_days,
                  price_inr, currency, razorpay_plan_id, max_uses, used_count,
                  created_by, created_at, expires_at
           FROM promo_codes ORDER BY created_at DESC LIMIT 500"""
    ).fetchall()

    codes = []
    for r in rows:
        codes.append({
            "code": r["code"],
            "tier": r["tier"],
            "daily_analyses": r["daily_analyses"],
            "batch_max": r["batch_max"],
            "has_export": bool(r["has_export"]),
            "trial_days": r["trial_days"],
            "price_inr": r["price_inr"],
            "currency": r["currency"],
            "razorpay_plan_id": r["razorpay_plan_id"],
            "max_uses": r["max_uses"],
            "used_count": r["used_count"],
            "created_by": r["created_by"],
            "created_at": r["created_at"],
            "expires_at": r["expires_at"],
        })

    # Summary stats
    total = len(codes)
    total_used = sum(c["used_count"] for c in codes)
    total_value = sum(c["used_count"] * c["price_inr"] for c in codes)

    return jsonify({
        "codes": codes,
        "summary": {
            "total_codes": total,
            "total_used": total_used,
            "total_unused": total - total_used,
            "total_trial_value_inr": total_value,
        }
    }), 200


# ══════════════════════════════════════════════════════════════════════════
# ADMIN: EXPENSE LOG
# ══════════════════════════════════════════════════════════════════════════

@payment_bp.route('/api/admin/expenses', methods=['GET'])
def admin_list_expenses():
    """List expense log entries. Admin-only."""
    from .auth import get_current_user
    user = get_current_user()
    if not user or user.get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403

    db = get_db()
    limit = min(int(request.args.get("limit", 200)), 1000)
    category = request.args.get("category", "")

    if category:
        rows = db.execute(
            """SELECT id, category, description, amount_inr, promo_code,
                      user_email, subscription_id, metadata, created_by, created_at
               FROM expense_log WHERE category=? ORDER BY created_at DESC LIMIT ?""",
            (category, limit)
        ).fetchall()
    else:
        rows = db.execute(
            """SELECT id, category, description, amount_inr, promo_code,
                      user_email, subscription_id, metadata, created_by, created_at
               FROM expense_log ORDER BY created_at DESC LIMIT ?""",
            (limit,)
        ).fetchall()

    expenses = [dict(r) for r in rows]

    # Summary by category
    cat_rows = db.execute(
        """SELECT category, COUNT(*) as count, SUM(amount_inr) as total_inr
           FROM expense_log GROUP BY category"""
    ).fetchall()
    by_category = {r["category"]: {"count": r["count"], "total_inr": round(r["total_inr"], 2)} for r in cat_rows}

    grand_total = sum(v["total_inr"] for v in by_category.values())

    return jsonify({
        "expenses": expenses,
        "summary": {
            "by_category": by_category,
            "grand_total_inr": round(grand_total, 2),
            "total_entries": len(expenses),
        }
    }), 200


@payment_bp.route('/api/admin/expenses/record', methods=['POST'])
def admin_record_expense():
    """Manually record an expense. Admin-only."""
    from .auth import get_current_user
    user = get_current_user()
    if not user or user.get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403

    data = request.get_json(silent=True) or {}
    category = (data.get("category") or "other").strip()
    description = (data.get("description") or "").strip()
    amount_inr = float(data.get("amount_inr", 0))
    promo_code = (data.get("promo_code") or "").strip()
    user_email = (data.get("user_email") or "").strip()
    subscription_id = (data.get("subscription_id") or "").strip()
    metadata = json.dumps(data.get("metadata", {}))

    if not description:
        return jsonify({"error": "Description is required"}), 400
    if amount_inr < 0:
        return jsonify({"error": "Amount cannot be negative"}), 400

    db = get_db()
    db.execute(
        """INSERT INTO expense_log
           (category, description, amount_inr, promo_code, user_email,
            subscription_id, metadata, created_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (category, description, amount_inr, promo_code, user_email,
         subscription_id, metadata, user["email"])
    )
    db.commit()

    return jsonify({"success": True, "message": "Expense recorded"}), 201


# ══════════════════════════════════════════════════════════════════════════
# ADMIN: REVENUE STATS (SQLite — mirrors PG endpoint for admin dashboard)
# ══════════════════════════════════════════════════════════════════════════

@payment_bp.route('/api/payments/revenue-stats', methods=['GET'])
def revenue_stats():
    """Admin-only: Revenue vs cost breakdown for the dashboard stats cards."""
    from .auth import get_current_user
    user = get_current_user()
    if not user or user.get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403

    db = get_db()

    # Revenue: from payments table
    try:
        rev = db.execute(
            "SELECT COALESCE(SUM(amount),0) AS total, COUNT(*) AS cnt "
            "FROM payments WHERE status='captured'"
        ).fetchone()
    except Exception:
        rev = {"total": 0, "cnt": 0}

    # Cost: from cost_ledger if it exists
    try:
        cost = db.execute(
            "SELECT COALESCE(SUM(total_cogs_inr),0) AS total FROM cost_ledger"
        ).fetchone()
    except Exception:
        cost = {"total": 0}

    total_rev = float(rev["total"]) if rev else 0
    total_cost = float(cost["total"]) if cost else 0
    margin = total_rev - total_cost

    return jsonify({
        "revenue": {
            "total_inr": total_rev,
            "payments_count": rev["cnt"] if rev else 0,
            "tokens_sold": 0,
        },
        "cost": {
            "total_inr": total_cost,
            "operations_count": 0,
            "paid_user_cost_inr": total_cost,
            "admin_free_cost_inr": 0,
        },
        "margin": {
            "gross_profit_inr": margin,
            "margin_percent": round(margin / total_rev * 100, 1) if total_rev > 0 else 0,
        }
    }), 200


def _log_expense(category, description, amount_inr, promo_code="", user_email="",
                 subscription_id="", metadata=None, created_by="system"):
    """Internal helper: write an expense_log row (SQLite path)."""
    try:
        db = get_db()
        db.execute(
            """INSERT INTO expense_log
               (category, description, amount_inr, promo_code, user_email,
                subscription_id, metadata, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (category, description, amount_inr, promo_code, user_email,
             subscription_id, json.dumps(metadata or {}), created_by)
        )
        db.commit()
    except Exception:
        logger.warning("Failed to log expense: %s %s %.2f", category, description, amount_inr)


@payment_bp.route('/api/payment/callback', methods=['GET'])
def payment_callback():
    """Redirect callback after Razorpay checkout."""
    order_id = request.args.get('razorpay_order_id', '')
    payment_id = request.args.get('razorpay_payment_id', '')
    signature = request.args.get('razorpay_signature', '')

    if not order_id or not payment_id or not signature:
        return '<script>window.location.href="payment-failed.html?reason=Missing+parameters"</script>'

    message = f"{order_id}|{payment_id}"
    expected = hmac.new(RAZORPAY_KEY_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()

    if hmac.compare_digest(expected, signature):
        return f'<script>window.location.href="payment-success.html?order_id={order_id}&payment_id={payment_id}"</script>'
    else:
        return '<script>window.location.href="payment-failed.html?reason=Signature+verification+failed"</script>'

#!/usr/bin/env python3
"""
VigyanLLM Razorpay Payment Integration
==========================================
POST /api/create-order   — Create Razorpay order (₹49 per design)
POST /api/verify-payment — Verify Razorpay payment signature & credit runs
"""

import os
import hmac
import hashlib
import time
import json
import logging

import razorpay
from flask import Blueprint, request, jsonify, g

from .auth import get_db, get_current_user, require_auth, log_action, check_usage, DB_PATH
from .price_registry import (
    FREE_TRIAL_RUNS,
    PRICE_REGISTRY,
    TOPUP_PRICE_INR,
    get_amount_paise,
    get_designs_for_product,
    validate_order_request,
)

logger = logging.getLogger("primerforge.payment")

payment_bp = Blueprint('payment', __name__)

# ── Razorpay Configuration (from environment) ────────────────────────────
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")
PRICE_PER_DESIGN_PAISE = 4900  # ₹49 = 4900 paise

# Initialize Razorpay client
rz_client = (
    razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET
    else None
)

if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
    logger.warning("RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET not set — payment endpoints will return 503")


def _parse_positive_int(value, default: int = 1, maximum: int = 100):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None, "Quantity must be a whole number."
    if parsed < 1:
        return None, "Quantity must be at least 1."
    if parsed > maximum:
        return None, f"Quantity must be at most {maximum}."
    return parsed, None


def _resolve_order_request(data):
    """Support both legacy runs checkout and product_id checkout."""
    product_id = data.get("product_id")
    if product_id:
        if not isinstance(product_id, str):
            return None, "Invalid product_id."
        quantity, err = _parse_positive_int(data.get("quantity", 1), maximum=100)
        if err:
            return None, err
        validation_error = validate_order_request(product_id, quantity)
        if validation_error:
            return None, validation_error
        amount = get_amount_paise(product_id, quantity)
        runs = get_designs_for_product(product_id, quantity)
        product = PRICE_REGISTRY.get(product_id)
        description = (
            f"VigyanLLM: {runs} primer design run(s)"
            if product_id == "top_up"
            else f"VigyanLLM: {product.display_name} ({runs} design credits)"
        )
        return {
            "amount": amount,
            "runs": runs,
            "quantity": quantity,
            "product_id": product_id,
            "description": description,
        }, None

    runs, err = _parse_positive_int(data.get("runs", 1), maximum=100)
    if err:
        return None, err.replace("Quantity", "Runs")
    amount = PRICE_PER_DESIGN_PAISE * runs
    return {
        "amount": amount,
        "runs": runs,
        "quantity": runs,
        "product_id": "top_up",
        "description": f"VigyanLLM: {runs} primer design run(s)",
    }, None


def _current_razorpay_client():
    return rz_client


@payment_bp.route('/api/create-order', methods=['POST'])
@payment_bp.route('/api/payments/create-order', methods=['POST'])
@require_auth
def create_order():
    """Create a Razorpay order for primer design runs."""
    data = request.get_json(silent=True) or {}
    resolved, err = _resolve_order_request(data)
    if err:
        return jsonify({"error": err}), 400

    amount = resolved["amount"]  # in paise
    if amount < 100:
        return jsonify({"error": "Minimum amount is ₹1 (100 paise)."}), 400
    if not _current_razorpay_client():
        return jsonify({
            "error": "Payment service not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET."
        }), 503

    # Get user name from DB for prefill — sanitize for Razorpay (letters/spaces only, min 3 chars)
    db = get_db()
    user_row = db.execute("SELECT name, email FROM users WHERE email=?", (g.user['email'],)).fetchone()
    raw_name = (user_row['name'] if user_row and user_row['name'] else 
                g.user['email'].split('@')[0])
    # Razorpay requires: alphabets and spaces only, min 3 chars
    import re as _re
    user_name = _re.sub(r'[^a-zA-Z\s]', ' ', raw_name).strip()
    if len(user_name) < 3:
        user_name = "VigyanLLM User"

    try:
        order = _current_razorpay_client().order.create({
            "amount": amount,
            "currency": "INR",
            "receipt": f"pf_{int(time.time())}_{resolved['product_id']}_{resolved['quantity']}",
            "notes": {
                "email": g.user['email'],
                "runs": str(resolved["runs"]),
                "product_id": resolved["product_id"],
                "quantity": str(resolved["quantity"]),
                "product": "VigyanLLM Design Runs"
            }
        })
    except razorpay.errors.BadRequestError as e:
        logger.error(f"Razorpay BadRequest: {e}")
        return jsonify({"error": "Payment service error. Please try again."}), 500
    except Exception as e:
        logger.error(f"Razorpay error: {e}")
        return jsonify({"error": "Payment service unavailable."}), 500

    # Store order in DB for tracking
    db = get_db()
    db.execute(
        "INSERT INTO payments (user_email, amount, upi_ref, status, runs_purchased) VALUES (?, ?, ?, ?, ?)",
        (g.user['email'], amount // 100, order['id'], "created", resolved["runs"])
    )
    db.commit()

    log_action(
        g.user['email'],
        "order_created",
        f"Order {order['id']} for {resolved['runs']} run(s), ₹{amount//100}",
    )

    return jsonify({
        "order_id": order['id'],
        "amount": amount,
        "currency": "INR",
        "key_id": RAZORPAY_KEY_ID,
        "runs": resolved["runs"],
        "tokens": resolved["runs"],
        "product_id": resolved["product_id"],
        "description": resolved["description"],
        "verify_endpoint": "/api/verify-payment",
        "prefill": {
            "name": user_name,
            "email": g.user['email'],
            "contact": "9999999999",
        }
    }), 200


@payment_bp.route('/api/verify-payment', methods=['POST'])
@payment_bp.route('/api/payments/verify-payment', methods=['POST'])
@require_auth
def verify_razorpay_payment():
    """Verify Razorpay payment signature and credit runs to user."""
    data = request.get_json(silent=True) or {}
    razorpay_payment_id = data.get('razorpay_payment_id', '')
    razorpay_order_id = data.get('razorpay_order_id', '')
    razorpay_signature = data.get('razorpay_signature', '')

    if not razorpay_payment_id or not razorpay_order_id or not razorpay_signature:
        return jsonify({"error": "Missing payment verification fields."}), 400
    if not RAZORPAY_KEY_SECRET:
        return jsonify({
            "error": "Payment service not configured. Set RAZORPAY_KEY_SECRET."
        }), 503

    # Verify signature: HMAC-SHA256(order_id + "|" + payment_id, KEY_SECRET)
    message = f"{razorpay_order_id}|{razorpay_payment_id}"
    expected_signature = hmac.new(
        RAZORPAY_KEY_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, razorpay_signature):
        logger.warning(f"Signature mismatch for order {razorpay_order_id}")
        return jsonify({"error": "Payment verification failed. Signature mismatch."}), 400

    # Signature valid — credit runs to user
    email = g.user['email']
    db = get_db()

    # Find the order to get runs_purchased
    order_row = db.execute(
        """SELECT id, runs_purchased, status FROM payments
           WHERE user_email=? AND (upi_ref=? OR upi_ref LIKE ?)
           ORDER BY id DESC LIMIT 1""",
        (email, razorpay_order_id, f"{razorpay_order_id}|%")
    ).fetchone()

    if not order_row:
        return jsonify({"error": "Order not found."}), 404

    runs = order_row['runs_purchased']
    if order_row["status"] == "verified":
        usage = check_usage(email)
        return jsonify({
            "success": True,
            "message": "Payment already verified.",
            "runs_purchased": 0,
            "tokens_credited": 0,
            "usage": usage,
        }), 200

    # Update payment status
    cur = db.execute(
        """UPDATE payments SET status='verified', upi_ref=?, verified_at=?
           WHERE id=? AND status!='verified'""",
        (f"{razorpay_order_id}|{razorpay_payment_id}", time.time(), order_row["id"])
    )
    if cur.rowcount == 0:
        db.commit()
        usage = check_usage(email)
        return jsonify({
            "success": True,
            "message": "Payment already verified.",
            "runs_purchased": 0,
            "tokens_credited": 0,
            "usage": usage,
        }), 200

    # Credit runs to user
    db.execute("UPDATE users SET paid_runs = paid_runs + ? WHERE email=?", (runs, email))
    db.commit()

    log_action(email, "payment_verified",
               f"Razorpay: order={razorpay_order_id} payment={razorpay_payment_id} runs={runs}")

    usage = check_usage(email)
    return jsonify({
        "success": True,
        "message": f"Payment verified! {runs} run(s) unlocked.",
        "runs_purchased": runs,
        "tokens_credited": runs,
        "usage": usage,
    }), 200


@payment_bp.route('/api/payment/status', methods=['GET'])
@payment_bp.route('/api/payments/token-balance', methods=['GET'])
@require_auth
def payment_status():
    """Get payment/usage status for current user."""
    usage = check_usage(g.user['email'])
    return jsonify({
        "usage": usage,
        "razorpay_key_id": RAZORPAY_KEY_ID,
        "price_per_design_inr": PRICE_PER_DESIGN_PAISE // 100,
    }), 200


@payment_bp.route('/api/payments/pricing', methods=['GET'])
def pricing():
    """Public pricing endpoint matching the PostgreSQL payment API shape."""
    return jsonify({
        "products": [
            {
                "product_id": cfg.product_id,
                "display_name": cfg.display_name,
                "product_type": cfg.product_type.value,
                "price_inr": cfg.price_inr,
                "designs_included": cfg.designs_included,
                "period": cfg.period,
                "max_seats": cfg.max_seats,
                "description": cfg.description,
            }
            for cfg in PRICE_REGISTRY.values()
            if cfg.is_active
        ],
        "top_up_price_inr": TOPUP_PRICE_INR,
        "free_trial_runs": FREE_TRIAL_RUNS,
        "currency": "INR",
    }), 200


# ═══════════════════════════════════════════════════════════════════════════
# RAZORPAY WEBHOOK (server-to-server callback)
# ═══════════════════════════════════════════════════════════════════════════

@payment_bp.route('/api/payment/webhook', methods=['POST'])
def razorpay_webhook():
    """
    Razorpay server-to-server webhook for payment events.
    Verifies webhook signature and processes payment.captured events.
    Configure this URL in Razorpay Dashboard > Webhooks:
      https://yourdomain.com/api/payment/webhook
    """
    # Get raw body for signature verification
    raw_body = request.get_data(as_text=True)
    webhook_signature = request.headers.get('X-Razorpay-Signature', '')
    webhook_secret = os.environ.get('RAZORPAY_WEBHOOK_SECRET', RAZORPAY_KEY_SECRET)

    if not webhook_signature:
        return jsonify({"error": "Missing webhook signature"}), 400

    # Verify webhook signature
    expected_sig = hmac.new(
        webhook_secret.encode(),
        raw_body.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, webhook_signature):
        logger.warning("Webhook signature verification failed")
        return jsonify({"error": "Invalid signature"}), 400

    # Parse event
    try:
        event = json.loads(raw_body)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    event_type = event.get('event', '')
    logger.info(f"Razorpay webhook: {event_type}")

    if event_type == 'payment.captured':
        payload = event.get('payload', {}).get('payment', {}).get('entity', {})
        order_id = payload.get('order_id', '')
        payment_id = payload.get('id', '')
        amount = payload.get('amount', 0)
        email = payload.get('email', '') or payload.get('notes', {}).get('email', '')

        if order_id and email:
            import sqlite3
            db = sqlite3.connect(DB_PATH)
            db.row_factory = sqlite3.Row

            # Find order and credit runs
            order_row = db.execute(
                "SELECT runs_purchased, status FROM payments WHERE upi_ref LIKE ? AND user_email=?",
                (f"{order_id}%", email)
            ).fetchone()

            if order_row and order_row['status'] != 'verified':
                runs = order_row['runs_purchased']
                db.execute(
                    "UPDATE payments SET status='verified', verified_at=? WHERE upi_ref LIKE ? AND user_email=?",
                    (time.time(), f"{order_id}%", email)
                )
                db.execute("UPDATE users SET paid_runs = paid_runs + ? WHERE email=?", (runs, email))
                db.commit()
                logger.info(f"Webhook: credited {runs} run(s) to {email} for order {order_id}")

            db.close()

    elif event_type == 'payment.failed':
        payload = event.get('payload', {}).get('payment', {}).get('entity', {})
        order_id = payload.get('order_id', '')
        logger.warning(f"Payment failed for order {order_id}")

    # Always return 200 to acknowledge webhook
    return jsonify({"status": "ok"}), 200


@payment_bp.route('/api/payment/callback', methods=['GET'])
def payment_callback():
    """
    Redirect callback after Razorpay checkout (if using redirect mode).
    Checks payment status and redirects to success/failed page.
    """
    order_id = request.args.get('razorpay_order_id', '')
    payment_id = request.args.get('razorpay_payment_id', '')
    signature = request.args.get('razorpay_signature', '')

    if not order_id or not payment_id or not signature:
        return '<script>window.location.href="payment-failed.html?reason=Missing+payment+parameters"</script>'

    # Verify signature
    message = f"{order_id}|{payment_id}"
    expected = hmac.new(RAZORPAY_KEY_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()

    if hmac.compare_digest(expected, signature):
        return f'<script>window.location.href="payment-success.html?order_id={order_id}&payment_id={payment_id}"</script>'
    else:
        return '<script>window.location.href="payment-failed.html?reason=Signature+verification+failed"</script>'

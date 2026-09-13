"""Webhook delivery engine for VigyanLLM developer portal."""
import hmac
import hashlib
import json
import time
import logging
import os
import threading
from urllib.parse import urlparse
import ipaddress

import psycopg2
import requests

log = logging.getLogger('vigyanllm.webhooks')


def _is_safe_url(url):
    """Check if a URL is safe to deliver to (no SSRF)."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ('https',):
        return False
    if not parsed.hostname:
        return False
    blocked = ('localhost', '127.0.0.1', '0.0.0.0', '::1', 'metadata.google.internal')
    if parsed.hostname.lower() in blocked:
        return False
    if parsed.hostname.endswith('.local') or parsed.hostname.endswith('.internal'):
        return False
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    except ValueError:
        pass
    return True


def emit_event(conn, event_type, data):
    """Emit an event to all matching webhooks."""
    cur = conn.cursor()
    cur.execute(
        "SELECT id, url, secret FROM webhooks WHERE is_active = TRUE AND events @> %s",
        (json.dumps([event_type]),)
    )
    webhooks = cur.fetchall()
    if not webhooks:
        return
    payload = json.dumps({'event': event_type, 'timestamp': int(time.time()), 'data': data})
    for hook_id, url, secret in webhooks:
        if not _is_safe_url(url):
            log.warning("Skipping webhook %s — unsafe URL: %s", hook_id, url)
            continue
        sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        # Record delivery attempt
        cur.execute(
            "INSERT INTO webhook_deliveries (webhook_id, event, payload, status) "
            "VALUES (%s, %s, %s, 'pending') RETURNING id",
            (hook_id, event_type, payload)
        )
        delivery_id = cur.fetchone()[0]
        conn.commit()
        # Deliver in background thread
        threading.Thread(target=_deliver, args=(delivery_id, url, payload, sig), daemon=True).start()


def _deliver(delivery_id, url, payload, sig):
    """Deliver webhook with retry."""
    conn = None
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL', ''), connect_timeout=10)
    except Exception as e:
        log.warning("Webhook %s — DB connection failed: %s", delivery_id, e)
        return
    for attempt in range(3):
        try:
            resp = requests.post(url, data=payload, headers={
                'Content-Type': 'application/json',
                'X-VigyanLLM-Signature': sig,
                'X-VigyanLLM-Event': json.loads(payload).get('event', ''),
            }, timeout=10)
            cur = conn.cursor()
            if resp.ok:
                cur.execute(
                    "UPDATE webhook_deliveries SET status = 'delivered', response_code = %s, "
                    "response_body = %s, attempts = %s WHERE id = %s",
                    (resp.status_code, resp.text[:1000], attempt + 1, delivery_id)
                )
                conn.commit()
                log.info("Webhook %s delivered: %s", delivery_id, resp.status_code)
                conn.close()
                return
            else:
                log.warning("Webhook %s failed: %s", delivery_id, resp.status_code)
        except Exception as e:
            log.warning("Webhook %s attempt %s error: %s", delivery_id, attempt + 1, e)
        # Exponential backoff
        time.sleep([5, 30, 300][attempt])
    # All retries failed
    try:
        cur = conn.cursor()
        cur.execute("UPDATE webhook_deliveries SET status = 'failed', attempts = 3 WHERE id = %s",
                    (delivery_id,))
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()

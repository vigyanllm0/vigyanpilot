"""Prometheus-compatible metrics for VigyanLLM.

Exposes /metrics endpoint with request counters, latency histograms,
and active-connection gauges. Uses the prometheus_client library
if available, otherwise falls back to a stub that returns empty metrics.
"""

import time
from functools import wraps

try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

if PROMETHEUS_AVAILABLE:
    REQUEST_COUNT = Counter(
        "vigyanllm_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status"],
    )
    REQUEST_LATENCY = Histogram(
        "vigyanllm_request_duration_seconds",
        "Request latency in seconds",
        ["method", "endpoint"],
        buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )
    ACTIVE_CONNECTIONS = Gauge(
        "vigyanllm_active_connections",
        "Number of currently active connections",
    )
else:
    REQUEST_COUNT = None
    REQUEST_LATENCY = None
    ACTIVE_CONNECTIONS = None


def init_metrics(app):
    """Register the /metrics endpoint on a Flask app."""

    @app.route("/metrics", methods=["GET"])
    def metrics_view():
        if not PROMETHEUS_AVAILABLE:
            return "# prometheus_client not installed\n", 200, {"Content-Type": "text/plain"}
        return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


def track_metrics(f):
    """Decorator to track request count and latency for a Flask route."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        if not PROMETHEUS_AVAILABLE:
            return f(*args, **kwargs)

        method = _req_method()
        endpoint = _req_endpoint()
        ACTIVE_CONNECTIONS.inc()
        start = time.perf_counter()
        try:
            resp = f(*args, **kwargs)
            status = str(resp.status_code) if hasattr(resp, "status_code") else "200"
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
            return resp
        except Exception:
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status="500").inc()
            raise
        finally:
            elapsed = time.perf_counter() - start
            REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(elapsed)
            ACTIVE_CONNECTIONS.dec()

    return wrapper


def _req_method():
    try:
        from flask import request
        return request.method
    except RuntimeError:
        return "UNKNOWN"


def _req_endpoint():
    try:
        from flask import request
        return request.path
    except RuntimeError:
        return "UNKNOWN"

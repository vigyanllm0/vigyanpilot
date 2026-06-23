#!/usr/bin/env python3
"""
VigyanLLM Production Debugger & Error Monitor
=================================================
- Catches all unhandled exceptions with full context
- Stores error traces in PostgreSQL (not exposed to clients)
- Provides admin dashboard for error review
- Performance monitoring (slow queries, slow endpoints)
- Request/response logging for debugging
"""

import os
import time
import json
import traceback
import logging
from datetime import datetime
from collections import defaultdict
from threading import Lock

from flask import request, g, jsonify

logger = logging.getLogger("primerforge.debugger")

# ── Configuration ─────────────────────────────────────────────────────────
SLOW_REQUEST_THRESHOLD_MS = int(os.environ.get("SLOW_REQUEST_MS", "2000"))  # 2 seconds
MAX_ERROR_STORE = 500  # Keep last 500 errors in memory
DEBUG_MODE = os.environ.get("DEBUG_MONITOR", "false").lower() == "true"


# ── Error Store ───────────────────────────────────────────────────────────

class ErrorMonitor:
    """In-memory error tracking with categorization."""

    def __init__(self):
        self._lock = Lock()
        self._errors = []  # [{timestamp, path, method, error_type, message, traceback, user, ip}]
        self._slow_requests = []  # [{timestamp, path, method, duration_ms, user}]
        self._endpoint_stats = defaultdict(lambda: {"count": 0, "errors": 0, "total_ms": 0, "max_ms": 0})
        self._error_counts = defaultdict(int)  # error_type -> count
        self._start_time = time.time()

    def record_error(self, error: Exception, context: dict = None):
        """Record an unhandled exception."""
        with self._lock:
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "error_type": type(error).__name__,
                "message": str(error)[:500],
                "traceback": traceback.format_exc()[-2000:],  # Last 2000 chars of traceback
                "path": context.get("path", "") if context else "",
                "method": context.get("method", "") if context else "",
                "user": context.get("user", "") if context else "",
                "ip": context.get("ip", "") if context else "",
                "request_id": context.get("request_id", "") if context else "",
            }
            self._errors.append(entry)
            if len(self._errors) > MAX_ERROR_STORE:
                self._errors = self._errors[-MAX_ERROR_STORE:]
            self._error_counts[entry["error_type"]] += 1

    def record_slow_request(self, path: str, method: str, duration_ms: int, user: str = ""):
        """Record a slow request."""
        with self._lock:
            self._slow_requests.append({
                "timestamp": datetime.utcnow().isoformat(),
                "path": path,
                "method": method,
                "duration_ms": duration_ms,
                "user": user,
            })
            if len(self._slow_requests) > 200:
                self._slow_requests = self._slow_requests[-200:]

    def record_request(self, path: str, method: str, status: int, duration_ms: int):
        """Record endpoint performance stats."""
        with self._lock:
            key = f"{method} {path}"
            stats = self._endpoint_stats[key]
            stats["count"] += 1
            stats["total_ms"] += duration_ms
            stats["max_ms"] = max(stats["max_ms"], duration_ms)
            if status >= 500:
                stats["errors"] += 1

    def get_errors(self, limit: int = 50, error_type: str = None) -> list:
        """Get recent errors, optionally filtered by type."""
        with self._lock:
            errors = self._errors[::-1]  # Newest first
            if error_type:
                errors = [e for e in errors if e["error_type"] == error_type]
            return errors[:limit]

    def get_stats(self) -> dict:
        """Get overall monitoring stats."""
        with self._lock:
            uptime = time.time() - self._start_time
            total_requests = sum(s["count"] for s in self._endpoint_stats.values())
            total_errors = sum(s["errors"] for s in self._endpoint_stats.values())

            # Top error types
            top_errors = sorted(self._error_counts.items(), key=lambda x: -x[1])[:10]

            # Slowest endpoints
            slowest = sorted(
                [(k, v["total_ms"] / max(v["count"], 1)) for k, v in self._endpoint_stats.items()],
                key=lambda x: -x[1]
            )[:10]

            # Most erroring endpoints
            most_errors = sorted(
                [(k, v["errors"], v["count"]) for k, v in self._endpoint_stats.items() if v["errors"] > 0],
                key=lambda x: -x[1]
            )[:10]

            return {
                "uptime_seconds": int(uptime),
                "total_requests": total_requests,
                "total_errors_500": total_errors,
                "error_rate_percent": round(total_errors / max(total_requests, 1) * 100, 2),
                "errors_in_store": len(self._errors),
                "top_error_types": [{"type": t, "count": c} for t, c in top_errors],
                "slowest_endpoints": [{"endpoint": e, "avg_ms": round(ms, 1)} for e, ms in slowest],
                "most_erroring": [{"endpoint": e, "errors": err, "total": tot} for e, err, tot in most_errors],
                "slow_requests_count": len(self._slow_requests),
            }

    def get_slow_requests(self, limit: int = 50) -> list:
        """Get recent slow requests."""
        with self._lock:
            return self._slow_requests[-limit:][::-1]

    def clear(self):
        """Clear all monitoring data (admin reset)."""
        with self._lock:
            self._errors.clear()
            self._slow_requests.clear()
            self._endpoint_stats.clear()
            self._error_counts.clear()


# Global monitor instance
_monitor = ErrorMonitor()


# ── Flask Integration ─────────────────────────────────────────────────────

def init_debugger(app):
    """Register the production debugger/monitor on the Flask app."""

    if not DEBUG_MODE:
        logger.info("Debug monitor disabled (set DEBUG_MONITOR=true to enable)")
        return

    @app.before_request
    def start_timer():
        """Record request start time."""
        g._request_start = time.time()
        g._request_id = f"{int(time.time()*1000)}-{os.urandom(4).hex()}"

    @app.after_request
    def record_performance(response):
        """Record request duration and detect slow requests."""
        start = getattr(g, "_request_start", None)
        if start is None:
            return response

        duration_ms = int((time.time() - start) * 1000)
        path = request.path
        method = request.method
        user = getattr(g, "user", {}).get("email", "") if hasattr(g, "user") else ""

        # Record stats
        _monitor.record_request(path, method, response.status_code, duration_ms)

        # Flag slow requests
        if duration_ms > SLOW_REQUEST_THRESHOLD_MS:
            _monitor.record_slow_request(path, method, duration_ms, user)
            logger.warning(f"SLOW REQUEST: {method} {path} — {duration_ms}ms (user={user})")

        # Add debug header
        response.headers["X-Request-Id"] = getattr(g, "_request_id", "")
        response.headers["X-Response-Time"] = f"{duration_ms}ms"

        return response

    @app.errorhandler(Exception)
    def catch_unhandled(error):
        """Catch ALL unhandled exceptions — store for debugging, return clean 500."""
        # Don't catch HTTP exceptions (4xx errors)
        from werkzeug.exceptions import HTTPException
        if isinstance(error, HTTPException):
            return error

        context = {
            "path": request.path,
            "method": request.method,
            "user": getattr(g, "user", {}).get("email", "") if hasattr(g, "user") else "",
            "ip": request.remote_addr,
            "request_id": getattr(g, "_request_id", ""),
        }
        _monitor.record_error(error, context)
        logger.error(f"Unhandled exception: {type(error).__name__}: {error}", exc_info=True)

        # Never expose internals to client
        return jsonify({
            "error": "Internal server error.",
            "code": "INTERNAL_ERROR",
            "request_id": context["request_id"],
        }), 500

    # ── Admin Debug Endpoints ─────────────────────────────────────────────
    # Local tests can run without the PostgreSQL auth stack installed. Keep the
    # request/error monitor active and skip only admin-only routes in that case.
    try:
        from .pg_auth import require_admin
    except Exception as exc:
        logger.warning("Debug admin endpoints disabled: %s", exc)
        logger.info(f"Debug monitor initialized (slow_threshold={SLOW_REQUEST_THRESHOLD_MS}ms)")
        return

    @app.route("/api/admin/debug/stats", methods=["GET"])
    @require_admin
    def debug_stats():
        """Admin: Get monitoring statistics."""
        return jsonify(_monitor.get_stats()), 200

    @app.route("/api/admin/debug/errors", methods=["GET"])
    @require_admin
    def debug_errors():
        """Admin: Get recent errors with stack traces."""
        limit = request.args.get("limit", 50, type=int)
        error_type = request.args.get("type", None)
        errors = _monitor.get_errors(limit, error_type)
        return jsonify({"errors": errors, "count": len(errors)}), 200

    @app.route("/api/admin/debug/slow-requests", methods=["GET"])
    @require_admin
    def debug_slow():
        """Admin: Get slow requests."""
        limit = request.args.get("limit", 50, type=int)
        slow = _monitor.get_slow_requests(limit)
        return jsonify({"slow_requests": slow, "count": len(slow), "threshold_ms": SLOW_REQUEST_THRESHOLD_MS}), 200

    @app.route("/api/admin/debug/clear", methods=["POST"])
    @require_admin
    def debug_clear():
        """Admin: Clear all monitoring data."""
        _monitor.clear()
        return jsonify({"success": True, "message": "Monitor data cleared."}), 200

    logger.info(f"Debug monitor initialized (slow_threshold={SLOW_REQUEST_THRESHOLD_MS}ms)")


def get_monitor() -> ErrorMonitor:
    """Get the global error monitor instance."""
    return _monitor

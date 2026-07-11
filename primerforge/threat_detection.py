#!/usr/bin/env python3
"""
VigyanLLM Threat Detection & Auto-Blocking Engine
====================================================
Real-time detection of:
- SQL injection, XSS, command injection patterns in requests
- Bot/scraper fingerprinting
- Brute-force patterns (beyond rate limiting)
- Suspicious file upload payloads
- Path traversal attempts

Auto-response:
- Immediate IP ban (configurable duration)
- Request quarantine and logging
- Alert generation for admin review
"""

import logging
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from threading import Lock

from flask import jsonify, request

logger = logging.getLogger("primerforge.threat")

# ── Configuration ─────────────────────────────────────────────────────────
BAN_DURATION_SECONDS = int(os.environ.get("THREAT_BAN_DURATION", "3600"))  # 1 hour default
MAX_VIOLATIONS_BEFORE_BAN = int(os.environ.get("THREAT_MAX_VIOLATIONS", "5"))
ALERT_WEBHOOK_URL = os.environ.get("THREAT_ALERT_WEBHOOK", "")  # Slack/Discord webhook

# ── Threat Signature Database ─────────────────────────────────────────────

SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|EXEC|UNION)\b.*\b(FROM|INTO|TABLE|WHERE|SET)\b)",
    r"('.*(\bOR\b|\bAND\b).*'?\s*[=<>])",
    r"(--|#|/\*|\*/)",
    r"(\bUNION\b.*\bSELECT\b)",
    r"(\bSLEEP\b\s*\(|\bWAITFOR\b|\bBENCHMARK\b)",
    r"(\bpg_sleep\b|\bpg_read_file\b|\bpg_ls_dir\b)",
    r"(\bCOPY\b.*\bTO\b|\bCOPY\b.*\bFROM\b)",
    r"(\bINTO\s+OUTFILE\b|\bLOAD_FILE\b)",
    r"(;\s*(DROP|DELETE|UPDATE|INSERT|ALTER))",
    r"(\bEXEC\b\s*\(|\bxp_cmdshell\b)",
]

XSS_PATTERNS = [
    r"(<script[^>]*>)",
    r"(javascript\s*:)",
    r"(on(load|error|click|mouseover|submit|focus|blur)\s*=)",
    r"(<\s*(img|svg|iframe|object|embed|link|meta|body|div|input)\b[^>]*(on\w+|src\s*=\s*['\"]?javascript))",
    r"(document\.(cookie|location|write|domain))",
    r"(window\.(location|open|eval))",
    r"(eval\s*\(|Function\s*\(|setTimeout\s*\(|setInterval\s*\()",
    r"(alert\s*\(|confirm\s*\(|prompt\s*\()",
]

COMMAND_INJECTION_PATTERNS = [
    r"(;\s*(cat|ls|id|whoami|pwd|uname|wget|curl|nc|bash|sh|python|perl|ruby|php)\b)",
    r"(\|\s*(cat|ls|id|whoami|bash|sh)\b)",
    r"(\$\(.*\)|\`.*\`)",
    r"(\.\./\.\./|\.\.\\\\\.\.\\\\)",
    r"(/etc/(passwd|shadow|hosts|resolv))",
    r"(/proc/self/|/dev/(tcp|udp)/)",
    r"(%2e%2e%2f|%252e%252e%252f)",
    r"(&&\s*(cat|ls|rm|wget|curl)\b)",
]

BOT_USER_AGENTS = [
    r"(sqlmap|nikto|nmap|masscan|dirbuster|gobuster|wfuzz)",
    r"(havij|acunetix|nessus|openvas|burpsuite)",
    r"(python-requests/|httpx|aiohttp.*bot|scrapy)",
    r"(^$)",  # Empty user agent
]

PATH_TRAVERSAL_PATTERNS = [
    r"(\.\.\/|\.\.\\)",
    r"(%2e%2e%2f|%2e%2e/|..%2f)",
    r"(%252e%252e%252f)",
    r"(\/etc\/|\/proc\/|\/var\/log\/)",
    r"(\\windows\\|\\system32\\)",
]

# Compile patterns for performance
_SQLI_RE = [re.compile(p, re.IGNORECASE) for p in SQL_INJECTION_PATTERNS]
_XSS_RE = [re.compile(p, re.IGNORECASE) for p in XSS_PATTERNS]
_CMD_RE = [re.compile(p, re.IGNORECASE) for p in COMMAND_INJECTION_PATTERNS]
_BOT_RE = [re.compile(p, re.IGNORECASE) for p in BOT_USER_AGENTS]
_PATH_RE = [re.compile(p, re.IGNORECASE) for p in PATH_TRAVERSAL_PATTERNS]


# ── IP Ban Store (in-memory, Redis-backed in production) ──────────────────

class ThreatStore:
    """Thread-safe threat tracking and IP banning."""

    def __init__(self):
        self._lock = Lock()
        self._violations = defaultdict(list)  # ip -> [(timestamp, threat_type, detail)]
        self._banned_ips = {}  # ip -> ban_expires_at
        self._quarantine = []  # [{timestamp, ip, threat_type, path, payload}]

    def record_violation(self, ip: str, threat_type: str, detail: str = ""):
        """Record a security violation. Auto-bans after threshold."""
        with self._lock:
            now = time.time()
            self._violations[ip].append((now, threat_type, detail))

            # Clean old violations (sliding window of 1 hour)
            self._violations[ip] = [
                v for v in self._violations[ip]
                if now - v[0] < 3600
            ]

            # Quarantine the request
            self._quarantine.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "ip": ip,
                "threat_type": threat_type,
                "detail": detail[:500],
                "path": request.path if request else "",
            })
            # Keep quarantine bounded
            if len(self._quarantine) > 10000:
                self._quarantine = self._quarantine[-5000:]

            # Auto-ban check
            recent = [v for v in self._violations[ip] if now - v[0] < 3600]
            if len(recent) >= MAX_VIOLATIONS_BEFORE_BAN:
                self._banned_ips[ip] = now + BAN_DURATION_SECONDS
                logger.warning("IP BANNED: %s — %s violations in 1h (ban: %ss)", ip, len(recent), BAN_DURATION_SECONDS)
                return True  # Newly banned
        return False

    def is_banned(self, ip: str) -> bool:
        """Check if an IP is currently banned."""
        with self._lock:
            if ip in self._banned_ips:
                if time.time() < self._banned_ips[ip]:
                    return True
                else:
                    # Ban expired
                    del self._banned_ips[ip]
                    return False
        return False

    def unban(self, ip: str):
        """Manually unban an IP."""
        with self._lock:
            self._banned_ips.pop(ip, None)
            self._violations.pop(ip, None)

    def get_stats(self) -> dict:
        """Get threat detection stats for admin dashboard."""
        with self._lock:
            now = time.time()
            active_bans = {ip: exp for ip, exp in self._banned_ips.items() if exp > now}
            return {
                "active_bans": len(active_bans),
                "banned_ips": [{"ip": ip, "expires_in_seconds": int(exp - now)} for ip, exp in active_bans.items()],
                "total_violations_tracked": sum(len(v) for v in self._violations.values()),
                "quarantine_size": len(self._quarantine),
                "recent_threats": self._quarantine[-20:][::-1],  # Last 20, newest first
            }

    def get_quarantine(self, limit: int = 100) -> list:
        """Get quarantined requests for review."""
        with self._lock:
            return self._quarantine[-limit:][::-1]


# Global threat store
_store = ThreatStore()


# ── Request Scanner ───────────────────────────────────────────────────────

def scan_request_payload(data: str) -> list:
    """
    Scan a string (request body, URL params, headers) for malicious patterns.
    Returns list of (threat_type, pattern_matched) tuples.
    """
    threats = []

    for pattern in _SQLI_RE:
        if pattern.search(data):
            threats.append(("sql_injection", pattern.pattern[:50]))
            break  # One SQLi match is enough

    for pattern in _XSS_RE:
        if pattern.search(data):
            threats.append(("xss", pattern.pattern[:50]))
            break

    for pattern in _CMD_RE:
        if pattern.search(data):
            threats.append(("command_injection", pattern.pattern[:50]))
            break

    for pattern in _PATH_RE:
        if pattern.search(data):
            threats.append(("path_traversal", pattern.pattern[:50]))
            break

    return threats


def scan_user_agent(ua: str) -> bool:
    """Check if user-agent matches known attack tools."""
    for pattern in _BOT_RE:
        if pattern.search(ua):
            return True
    return False


def scan_file_content(content: bytes, filename: str = "") -> list:
    """
    Scan uploaded file content for malicious patterns.
    Returns list of threat descriptions.
    """
    threats = []

    # Check for PHP/shell backdoors
    text = content[:100000].decode("utf-8", errors="ignore")
    php_patterns = [
        r"<\?php", r"eval\s*\(", r"base64_decode\s*\(",
        r"system\s*\(", r"exec\s*\(", r"passthru\s*\(",
        r"shell_exec\s*\(", r"popen\s*\(",
    ]
    for p in php_patterns:
        if re.search(p, text, re.IGNORECASE):
            threats.append(f"Possible PHP/shell backdoor: {p}")
            break

    # Check for executable headers
    if content[:2] in (b'MZ', b'\x7fE'):  # PE or ELF binary
        threats.append("Binary executable detected in upload")

    # Check filename for double extensions
    if filename:
        suspicious_ext = ['.php', '.exe', '.sh', '.bat', '.cmd', '.ps1', '.vbs', '.jsp']
        lower_name = filename.lower()
        for ext in suspicious_ext:
            if ext in lower_name:
                threats.append(f"Suspicious file extension: {ext}")
                break

    return threats


# ── Flask Middleware ──────────────────────────────────────────────────────

def init_threat_detection(app):
    """Register threat detection middleware on the Flask app."""

    @app.before_request
    def check_threats():
        """Scan every incoming request for malicious patterns."""
        ip = request.remote_addr or "0.0.0.0"

        # Skip threat check for admin threat-management endpoints (to allow unban)
        if request.path.startswith("/api/admin/threats"):
            return

        # Skip threat check for localhost/development (prevents self-ban during testing)
        if ip in ("127.0.0.1", "::1", "0.0.0.0"):
            return

        # 1. Check if IP is banned
        if _store.is_banned(ip):
            return jsonify({
                "error": "Access denied.",
                "code": "IP_BANNED",
            }), 403

        # 2. Scan user-agent
        ua = request.headers.get("User-Agent", "")
        if scan_user_agent(ua):
            _store.record_violation(ip, "malicious_bot", f"UA: {ua[:100]}")
            # Don't block immediately — just record (some legit tools have weird UAs)

        # 3. Scan URL path
        path_threats = scan_request_payload(request.path + "?" + request.query_string.decode("utf-8", errors="ignore"))
        for threat_type, pattern in path_threats:
            banned = _store.record_violation(ip, threat_type, f"Path: {request.path}")
            if banned:
                return jsonify({"error": "Access denied.", "code": "IP_BANNED"}), 403

        # 4. Scan request body (for POST/PUT/PATCH)
        # Skip pipeline and health endpoints — their bodies carry sequence data,
        # not untrusted user input, and scanning large sequences with 35+ regex
        # patterns causes severe latency (>20s on multi-KB payloads).
        if request.method in ("POST", "PUT", "PATCH") \
                and not request.path.startswith("/api/pipeline/") \
                and request.path != "/health":
            body = request.get_data(as_text=True)
            if body and len(body) < 50000:  # Only scan reasonable-size bodies
                body_threats = scan_request_payload(body)
                for threat_type, pattern in body_threats:
                    _store.record_violation(ip, threat_type, f"Body payload ({request.path})")
                    # Don't block on body scan — parameterized queries handle SQLi,
                    # bleach handles XSS. Just record for monitoring.

        # 5. Check for path traversal in URL
        if ".." in request.path or "%2e" in request.path.lower():
            _store.record_violation(ip, "path_traversal", request.path)

    # Admin endpoints for threat management. In local development/test
    # environments the PostgreSQL auth stack may be intentionally absent.
    try:
        from .pg_auth import require_admin
    except Exception as exc:
        logger.warning("Threat admin endpoints disabled: %s", exc)
        logger.info("Threat detection engine initialized")
        return

    @app.route("/api/admin/threats", methods=["GET"])
    @require_admin
    def get_threats():
        """Admin: Get threat detection stats and recent threats."""
        return jsonify(_store.get_stats()), 200

    @app.route("/api/admin/threats/quarantine", methods=["GET"])
    @require_admin
    def get_quarantine():
        """Admin: Get quarantined malicious requests."""
        limit = request.args.get("limit", 100, type=int)
        return jsonify({"quarantine": _store.get_quarantine(limit)}), 200

    @app.route("/api/admin/threats/unban", methods=["POST"])
    @require_admin
    def unban_ip():
        """Admin: Manually unban an IP address."""
        data = request.get_json(silent=True) or {}
        ip = data.get("ip", "")
        if not ip:
            return jsonify({"error": "IP address required."}), 400
        _store.unban(ip)
        return jsonify({"success": True, "message": f"IP {ip} unbanned."}), 200

    @app.route("/api/admin/threats/ban", methods=["POST"])
    @require_admin
    def ban_ip():
        """Admin: Manually ban an IP address."""
        data = request.get_json(silent=True) or {}
        ip = data.get("ip", "")
        duration = data.get("duration", BAN_DURATION_SECONDS)
        if not ip:
            return jsonify({"error": "IP address required."}), 400
        with _store._lock:
            _store._banned_ips[ip] = time.time() + duration
        return jsonify({"success": True, "message": f"IP {ip} banned for {duration}s."}), 200

    logger.info("Threat detection engine initialized")


def get_threat_store() -> ThreatStore:
    """Get the global threat store instance."""
    return _store

#!/usr/bin/env python3
"""
VigyanLLM Tool-Usage Analytics
==============================
Unified, privacy-respecting tool-usage ledger + admin intelligence API.

Purpose (CBO view): answer "how many people use which tools, how often, and
are they coming back?" across BOTH user scenarios:
  1. Logged-in users  → identified by `user_email`.
  2. Anonymous guests → identified by their true client IP (`client_ip`).

Every tool run — server-backed compute *and* pure-browser calculators — is
recorded as a single `tool_usage_events` row. The same table powers the admin
dashboard, so the numbers can never disagree between charts.

Privacy notes:
  * Anonymous visitors are keyed by IP only (never raw browser fingerprint).
  * We store the IP itself (not only a hash) because the CBO requirement is
    "show which IPs return daily" — this is an ADMIN-ONLY surface behind
    `require_admin`, mirroring the existing threat/ban tables which already
    display raw IPs to admins.
  * No payload data is stored — only tool identity, workload size, date,
    identity, and plan tier.

This module is deliberately self-contained and mode-aware: it writes to
PostgreSQL (production) or SQLite (dev/tests) depending on DATABASE_URL, so
it can be registered from both branches of `create_app()` unchanged.
"""

import datetime
import logging
import os
import re
import sqlite3
import time

from flask import Blueprint, jsonify, request

logger = logging.getLogger("primerforge.usage_analytics")

usage_analytics_bp = Blueprint("usage_analytics_bp", __name__)

# ── Tool registry ──────────────────────────────────────────────────────────
# Canonical tool_key → (display label, category). The beacon endpoint only
# accepts keys present here; backend hooks pass these keys directly.
TOOL_REGISTRY = {
    # PCR / primer design
    "primer_auto":      ("Primer Design (Auto)",      "pcr_primer"),
    "primer_manual":    ("Primer Design (Manual)",    "pcr_primer"),
    "pcr_analysis":     ("In-Silico PCR",             "pcr_primer"),
    "pcr_product_calc": ("PCR Product Calculator",    "pcr_primer"),
    "tm_calculator":    ("Tm Calculator",             "pcr_primer"),
    "gc_calculator":    ("GC Calculator",             "pcr_primer"),
    # sequence analysis
    "blast":            ("BLAST",                     "sequence"),
    "msa":              ("MSA",                       "sequence"),
    "dna_to_rna":       ("DNA → RNA",                 "sequence"),
    "reverse_complement": ("Reverse Complement",      "sequence"),
    "dna_to_protein":   ("DNA → Protein",             "sequence"),
    # pharma / lab calculators
    "biostatistics":    ("Biostatistics Calculator",  "pharma_stats"),
    "antibiotic_calc":  ("Antibiotic Stock Calculator", "pharma_stats"),
    # genome engineering
    "restriction_finder": ("Restriction Enzyme Finder", "genome_eng"),
    "cloning_simulator":  ("Cloning Simulator",       "genome_eng"),
    "crispr_analysis":    ("CRISPR Analysis",         "genome_eng"),
    # structural biology
    "docking_consensus":  ("Molecular Docking",       "docking_struct"),
    "virtual_screening":  ("Virtual Screening",       "docking_struct"),
    "protein_quality":    ("Protein Quality",         "docking_struct"),
    "interactions":       ("Interactions",            "docking_struct"),
    "binding_site":       ("Binding Site",            "docking_struct"),
    "dna_3d":             ("3D DNA Viewer",           "docking_struct"),
}

# Beacon dedup window: at most one event per (ip, tool_key) per window. This
# is a per-worker in-memory second layer on top of the frontend's own debounce.
_BEACON_DEDUP_TTL = 15.0
_beacon_cache = {}  # key: "ip|tool_key" → last-recorded monotonic timestamp


# ── Mode + schema helpers ──────────────────────────────────────────────────

def use_postgres() -> bool:
    """True when production PostgreSQL is active."""
    return bool(os.environ.get("DATABASE_URL"))


def _tool_label(tool_key: str) -> str:
    return TOOL_REGISTRY.get(tool_key, (tool_key, "other"))[0]


def _tool_category(tool_key: str) -> str:
    return TOOL_REGISTRY.get(tool_key, (tool_key, "other"))[1]


# ── Input sanitisation (defense-in-depth for untrusted values) ─────────────
# client_ip originates from X-Forwarded-For / socket address — a direct-to-
# origin attacker CAN forge it. We strip it to IP-safe characters only so a
# crafted value can never become a CSV-formula / XSS payload downstream, and
# cap it to the column width (VARCHAR(45) covers the longest IPv6).

_IP_RE = re.compile(r"[^A-Za-z0-9.:]")


def _sanitize_ip(ip) -> str:
    if not ip:
        return "unknown"
    cleaned = _IP_RE.sub("", str(ip))[:45]
    return cleaned or "unknown"


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _sanitize_date(value) -> str:
    """Return a valid YYYY-MM-DD or today's UTC date."""
    if isinstance(value, str) and _DATE_RE.match(value):
        return value
    return _today_utc()


def _coerce_count(value) -> int:
    """Clamp a workload count to a sane 1..100000 range (never raises)."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return 1
    return max(1, min(n, 100000))


def _csv_safe(value) -> str:
    """Neutralise spreadsheet formula injection in CSV export.

    Prefixes a ' (apostrophe) before any cell that would otherwise begin with
    =, +, -, @, tab or CR — the characters Excel/Sheets treat as formula
    triggers.
    """
    s = "" if value is None else str(value)
    if s and s[0] in "=+-@\t\r":
        return "'" + s
    return s


def _client_ip() -> str:
    """True client IP behind CloudFront/nginx (same logic as rate limiting)."""
    try:
        from .security import client_rate_key
        return client_rate_key() or "0.0.0.0"
    except Exception:
        xff = request.headers.get("X-Forwarded-For", "")
        if xff:
            last = xff.split(",")[-1].strip()
            if last:
                return last
        return request.remote_addr or "0.0.0.0"


def _now_utc() -> datetime.datetime:
    """Timezone-aware UTC now (utcnow() is deprecated in py3.13+)."""
    return datetime.datetime.now(datetime.timezone.utc)


def _today_utc() -> str:
    return _now_utc().strftime("%Y-%m-%d")


def _date_list(days: int):
    """Return the last `days` 'YYYY-MM-DD' dates, oldest first, ending today."""
    today = _now_utc().date()
    return [(today - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(days - 1, -1, -1)]


# ── Schema (idempotent, dialect-aware) ─────────────────────────────────────

def ensure_schema():
    """Create the tool_usage_events table if missing (both backends)."""
    try:
        if use_postgres():
            from .database import execute
            execute(_PG_DDL)
        else:
            _ensure_sqlite_schema()
    except Exception as e:
        logger.warning("tool_usage_events schema init failed: %s", e)


_PG_DDL = """
CREATE TABLE IF NOT EXISTS tool_usage_events (
    id BIGSERIAL PRIMARY KEY,
    tool_key VARCHAR(48) NOT NULL,
    tool_category VARCHAR(32) NOT NULL DEFAULT 'other',
    is_authenticated BOOLEAN NOT NULL DEFAULT FALSE,
    user_email VARCHAR(255),
    user_plan VARCHAR(32) NOT NULL DEFAULT 'guest',
    client_ip VARCHAR(45) NOT NULL,
    sequences_count INTEGER NOT NULL DEFAULT 1,
    usage_date VARCHAR(10) NOT NULL,
    created_at DOUBLE PRECISION NOT NULL DEFAULT (EXTRACT(EPOCH FROM NOW()))
);
CREATE INDEX IF NOT EXISTS idx_tue_date ON tool_usage_events(usage_date);
CREATE INDEX IF NOT EXISTS idx_tue_tool_date ON tool_usage_events(tool_key, usage_date);
CREATE INDEX IF NOT EXISTS idx_tue_ip_date ON tool_usage_events(client_ip, usage_date);
CREATE INDEX IF NOT EXISTS idx_tue_email_date ON tool_usage_events(user_email, usage_date);
"""


def _sqlite_db():
    """Standalone SQLite connection (mirrors visitor_routes pattern).

    Reads PRIMERFORGE_DB at call time (not via auth.DB_PATH, which is bound
    once at auth import) so tests can monkeypatch a fresh DB per test.
    """
    from .auth import DB_PATH as _AUTH_DB_PATH
    db_path = os.environ.get("PRIMERFORGE_DB") or _AUTH_DB_PATH
    db = sqlite3.connect(db_path, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    return db


def _ensure_sqlite_schema():
    db = _sqlite_db()
    try:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS tool_usage_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_key TEXT NOT NULL,
                tool_category TEXT NOT NULL DEFAULT 'other',
                is_authenticated INTEGER NOT NULL DEFAULT 0,
                user_email TEXT,
                user_plan TEXT NOT NULL DEFAULT 'guest',
                client_ip TEXT NOT NULL,
                sequences_count INTEGER NOT NULL DEFAULT 1,
                usage_date TEXT NOT NULL,
                created_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tue_date ON tool_usage_events(usage_date);
            CREATE INDEX IF NOT EXISTS idx_tue_tool_date ON tool_usage_events(tool_key, usage_date);
            CREATE INDEX IF NOT EXISTS idx_tue_ip_date ON tool_usage_events(client_ip, usage_date);
            CREATE INDEX IF NOT EXISTS idx_tue_email_date ON tool_usage_events(user_email, usage_date);
        """)
        db.commit()
    finally:
        db.close()


# ── Plan resolution (best-effort; never raises) ────────────────────────────

def _resolve_plan(user) -> str:
    """Derive the plan tier for a logged-in user. Falls back to 'user'."""
    if not user:
        return "guest"
    role = (user or {}).get("role", "")
    if role == "admin":
        return "admin"
    email = (user or {}).get("email", "")
    if not email:
        return "user"
    try:
        if use_postgres():
            from .database import fetch_one
            row = fetch_one("SELECT plan FROM users WHERE email = %s", (email,))
            return (row or {}).get("plan") or "free"
        from .auth import get_user_plan
        return get_user_plan(email) or "free"
    except Exception:
        return "user"


# ── Core writer ────────────────────────────────────────────────────────────

def record_tool_event(tool_key, user=None, sequences_count=1, client_ip=None, usage_date=None):
    """Record one tool run. Never raises — analytics must not break a tool.

    Args:
        tool_key:        key from TOOL_REGISTRY.
        user:            current user dict (None for anonymous). Read from the
                         active request auth if omitted.
        sequences_count: workload size (ligands, sequences, primers…).
        client_ip:       override; otherwise resolved from the request.
        usage_date:      override 'YYYY-MM-DD' (testing / historical backfill).
    """
    if tool_key not in TOOL_REGISTRY:
        return
    try:
        ip = _sanitize_ip(client_ip or _client_ip())
        if ip in ("0.0.0.0", "unknown", ""):
            ip = "unknown"
        is_auth = bool(user)
        email = (user or {}).get("email") or None
        if email is not None:
            email = str(email)[:255]
        plan = (str(_resolve_plan(user) or "guest"))[:32]
        category = _tool_category(tool_key)
        usage_date = _sanitize_date(usage_date)
        now = time.time()
        seq = _coerce_count(sequences_count)

        if use_postgres():
            from .database import execute
            execute(
                """INSERT INTO tool_usage_events
                   (tool_key, tool_category, is_authenticated, user_email,
                    user_plan, client_ip, sequences_count, usage_date, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (tool_key, category, is_auth, email, plan, ip, seq, usage_date, now)
            )
        else:
            db = _sqlite_db()
            try:
                db.execute(
                    """INSERT INTO tool_usage_events
                       (tool_key, tool_category, is_authenticated, user_email,
                        user_plan, client_ip, sequences_count, usage_date, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (tool_key, category, 1 if is_auth else 0, email, plan, ip, seq, usage_date, now)
                )
                db.commit()
            finally:
                db.close()
    except Exception as e:
        logger.debug("record_tool_event suppressed: %s", e)


# ── Fetch raw events ───────────────────────────────────────────────────────

def _fetch_events(start_date: str) -> list:
    """Return all events with usage_date >= start_date as list of dicts."""
    if use_postgres():
        from .database import fetch_all
        rows = fetch_all(
            "SELECT * FROM tool_usage_events WHERE usage_date >= %s ORDER BY usage_date",
            (start_date,)
        )
        return rows or []
    db = _sqlite_db()
    try:
        rows = db.execute(
            "SELECT * FROM tool_usage_events WHERE usage_date >= ? ORDER BY usage_date",
            (start_date,)
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        db.close()


# ── Aggregation ────────────────────────────────────────────────────────────

def _identity(event) -> str:
    """Unique actor key: email for logged-in, ip-prefixed for anonymous."""
    if event.get("is_authenticated"):
        return "u:" + (event.get("user_email") or "")
    return "ip:" + (event.get("client_ip") or "unknown")


def _build_analytics(days=30):
    days = max(7, min(int(days or 30), 90))
    today = _today_utc()
    # Always pull at least 30 days so MAU / cohort cards are correct even when
    # the caller requests a 7-day window.
    window_days = max(days, 30)
    start = (_now_utc().date() - datetime.timedelta(days=window_days - 1)).strftime("%Y-%m-%d")

    try:
        ensure_schema()
    except Exception:
        pass

    events = _fetch_events(start)

    # Admin (ops/probe/test) activity is tracked but kept OUT of the customer
    # metrics — an admin's own runs must never read as "users using my tools".
    admin_events = [e for e in events if e.get("user_plan") == "admin"]
    events = [e for e in events if e.get("user_plan") != "admin"]

    # Partition by scenario.
    anon = [e for e in events if not e.get("is_authenticated")]
    authed = [e for e in events if e.get("is_authenticated")]

    def runs_in(evts, d0, d1):
        return [e for e in evts if d0 <= e["usage_date"] <= d1]

    # ── KPI helpers ────────────────────────────────────────────────────────
    def unique_count(evts):
        return len({_identity(e) for e in evts})

    def _date_range(days_back):
        d1 = today
        d0 = (_now_utc().date() - datetime.timedelta(days=days_back - 1)).strftime("%Y-%m-%d")
        return d0, d1

    def kpi_for(days_back):
        d0, d1 = _date_range(days_back)
        a = runs_in(anon, d0, d1)
        u = runs_in(authed, d0, d1)
        logged_in_users = len({e["user_email"] for e in u if e.get("user_email")})
        anon_ips = len({e["client_ip"] for e in a})
        return {
            "total_runs": len(a) + len(u),
            "logged_in_runs": len(u),
            "anon_runs": len(a),
            "logged_in_users": logged_in_users,
            "anonymous_ips": anon_ips,
            "total_unique_users": logged_in_users + anon_ips,
        }

    kpi_today = kpi_for(1)
    kpi_week = kpi_for(7)
    kpi_month = kpi_for(30)

    # MAU / DAU stickiness.
    mau = kpi_month["total_unique_users"]
    dau = kpi_today["total_unique_users"]
    dau_mau = round(dau / mau, 3) if mau else 0.0

    # Returning rate (>=2 distinct active days in the 30-day window).
    month_events = runs_in(events, _date_range(30)[0], today)
    actor_days = {}
    for e in month_events:
        actor_days.setdefault(_identity(e), set()).add(e["usage_date"])
    returning = sum(1 for d in actor_days.values() if len(d) >= 2)
    total_actors = len(actor_days)
    returning_pct = round(returning / total_actors * 100, 1) if total_actors else 0.0

    # ── Top tool (30d) ─────────────────────────────────────────────────────
    tool_counts = {}
    for e in month_events:
        tool_counts[e["tool_key"]] = tool_counts.get(e["tool_key"], 0) + 1
    total_month_runs = sum(tool_counts.values())
    top_tool_key = max(tool_counts, key=tool_counts.get) if tool_counts else None
    top_tool = None
    if top_tool_key:
        top_tool = {
            "tool_key": top_tool_key,
            "label": _tool_label(top_tool_key),
            "runs": tool_counts[top_tool_key],
            "share_pct": round(tool_counts[top_tool_key] / total_month_runs * 100, 1) if total_month_runs else 0.0,
        }

    # ── Daily series (zero-filled) ─────────────────────────────────────────
    dates = _date_list(days)
    by_date = {}
    for e in events:
        d = e["usage_date"]
        bucket = by_date.setdefault(d, {"logged_in_runs": 0, "anon_runs": 0,
                                        "logged_in_users": set(), "anon_ips": set()})
        if e.get("is_authenticated"):
            bucket["logged_in_runs"] += 1
            if e.get("user_email"):
                bucket["logged_in_users"].add(e["user_email"])
        else:
            bucket["anon_runs"] += 1
            bucket["anon_ips"].add(e["client_ip"])
    daily_series = []
    for d in dates:
        b = by_date.get(d)
        daily_series.append({
            "date": d,
            "logged_in_runs": b["logged_in_runs"] if b else 0,
            "anon_runs": b["anon_runs"] if b else 0,
            "logged_in_users": len(b["logged_in_users"]) if b else 0,
            "anon_ips": len(b["anon_ips"]) if b else 0,
        })

    # ── Tool leaderboard (within requested window) ─────────────────────────
    win0 = dates[0]
    win_events = runs_in(events, win0, today)
    board = {}
    for e in win_events:
        t = e["tool_key"]
        b = board.setdefault(t, {"runs": 0, "logged_in_runs": 0, "anon_runs": 0,
                                 "users": set(), "ips": set(), "actors": set()})
        b["runs"] += 1
        if e.get("is_authenticated"):
            b["logged_in_runs"] += 1
            if e.get("user_email"):
                b["users"].add(e["user_email"])
        else:
            b["anon_runs"] += 1
            b["ips"].add(e["client_ip"])
        b["actors"].add(_identity(e))
    # Returning users per tool: actor seen on >=2 distinct days within window.
    tool_actors_days = {}
    for e in win_events:
        tool_actors_days.setdefault(e["tool_key"], {}).setdefault(_identity(e), set()).add(e["usage_date"])
    tool_leaderboard = []
    for t, b in board.items():
        returning_tool = sum(1 for d in tool_actors_days.get(t, {}).values() if len(d) >= 2)
        tool_leaderboard.append({
            "tool_key": t,
            "label": _tool_label(t),
            "category": _tool_category(t),
            "total_runs": b["runs"],
            "logged_in_runs": b["logged_in_runs"],
            "anon_runs": b["anon_runs"],
            "unique_logged_in": len(b["users"]),
            "unique_anon_ips": len(b["ips"]),
            "returning_users": returning_tool,
        })
    tool_leaderboard.sort(key=lambda x: x["total_runs"], reverse=True)

    # ── Scenario split ─────────────────────────────────────────────────────
    runs_by_plan = {}
    for e in win_events:
        plan = e.get("user_plan") or "guest"
        runs_by_plan[plan] = runs_by_plan.get(plan, 0) + 1
    # Admin (test/probe) volume surfaced as its own segment, not as customers.
    admin_win = [e for e in admin_events if e["usage_date"] >= win0]
    if admin_win:
        runs_by_plan["admin"] = runs_by_plan.get("admin", 0) + len(admin_win)
    scenario_runs = [{"segment": k, "runs": v} for k, v in
                     sorted(runs_by_plan.items(), key=lambda kv: -kv[1])]
    scenario_identities = [
        {"type": "anonymous_ip", "count": len({e["client_ip"] for e in anon})},
        {"type": "logged_in_account", "count": len({e["user_email"] for e in authed if e.get("user_email")})},
    ]

    # ── Return-frequency cohort (30d) ──────────────────────────────────────
    cohort = {"1 day only": 0, "2-3 days": 0, "4-7 days": 0, "8+ days": 0}
    for d in actor_days.values():
        n = len(d)
        if n <= 1:
            cohort["1 day only"] += 1
        elif n <= 3:
            cohort["2-3 days"] += 1
        elif n <= 7:
            cohort["4-7 days"] += 1
        else:
            cohort["8+ days"] += 1
    cohort_buckets = [{"bucket": k, "count": v} for k, v in cohort.items()]

    # ── Returning anonymous IPs (30d) ──────────────────────────────────────
    anon_ip_days = {}
    anon_ip_meta = {}
    for e in month_events:
        if e.get("is_authenticated"):
            continue
        ip = e["client_ip"]
        anon_ip_days.setdefault(ip, set()).add(e["usage_date"])
        m = anon_ip_meta.setdefault(ip, {"runs": 0, "today_runs": 0, "tools": {},
                                         "first": e["usage_date"], "last": e["usage_date"]})
        m["runs"] += 1
        if e["usage_date"] == today:
            m["today_runs"] += 1
        m["tools"][e["tool_key"]] = m["tools"].get(e["tool_key"], 0) + 1
        if e["usage_date"] < m["first"]:
            m["first"] = e["usage_date"]
        if e["usage_date"] > m["last"]:
            m["last"] = e["usage_date"]

    # Link an anonymous IP to a registered account if that IP later logged in.
    ip_to_email = {}
    for e in authed:
        ip = e.get("client_ip")
        email = e.get("user_email")
        if ip and email:
            ip_to_email.setdefault(ip, email)

    def _streak(day_set):
        streak = 0
        d = _now_utc().date()
        while d.strftime("%Y-%m-%d") in day_set:
            streak += 1
            d -= datetime.timedelta(days=1)
        return streak

    returning_anon_ips = []
    for ip, days_set in anon_ip_days.items():
        m = anon_ip_meta[ip]
        fav = sorted(m["tools"].items(), key=lambda kv: -kv[1])
        fav_label = ", ".join(f"{_tool_label(t)}×{c}" for t, c in fav[:3])
        returning_anon_ips.append({
            "ip": ip,
            "active_days": len(days_set),
            "current_streak": _streak(days_set),
            "total_runs": m["runs"],
            "today_runs": m["today_runs"],
            "favorite_tools": fav_label,
            "first_seen": m["first"],
            "last_seen": m["last"],
            "linked_email": ip_to_email.get(ip),
        })
    returning_anon_ips.sort(key=lambda x: (-x["active_days"], -x["total_runs"]))

    # ── Logged-in user activity (30d) ──────────────────────────────────────
    user_meta = {}
    for e in month_events:
        if not e.get("is_authenticated") or not e.get("user_email"):
            continue
        u = e["user_email"]
        m = user_meta.setdefault(u, {"runs": 0, "today_runs": 0, "runs_7d": 0, "runs_30d": 0,
                                     "days": set(), "tools": {}, "last_tool": None,
                                     "last_date": e["usage_date"], "plan": e.get("user_plan", "user"),
                                     "last_ip": e["client_ip"]})
        m["runs"] += 1
        m["runs_30d"] += 1
        m["days"].add(e["usage_date"])
        m["tools"][e["tool_key"]] = m["tools"].get(e["tool_key"], 0) + 1
        if e["usage_date"] == today:
            m["today_runs"] += 1
        if e["usage_date"] >= _date_range(7)[0]:
            m["runs_7d"] += 1
        if e["usage_date"] > m["last_date"]:
            m["last_date"] = e["usage_date"]
            m["last_tool"] = e["tool_key"]
            m["last_ip"] = e["client_ip"]
    logged_in_users = []
    for u, m in user_meta.items():
        fav = sorted(m["tools"].items(), key=lambda kv: -kv[1])
        logged_in_users.append({
            "email": u,
            "plan": m["plan"],
            "active_days": len(m["days"]),
            "runs_today": m["today_runs"],
            "runs_7d": m["runs_7d"],
            "runs_30d": m["runs_30d"],
            "tool_breakdown": ", ".join(f"{_tool_label(t)}×{c}" for t, c in fav),
            "last_tool": _tool_label(m["last_tool"]) if m["last_tool"] else None,
            "last_seen": m["last_date"],
            "last_ip": m["last_ip"],
        })
    logged_in_users.sort(key=lambda x: -x["runs_30d"])

    # ── Tool × scenario matrix ─────────────────────────────────────────────
    tools_matrix = [{
        "rank": i + 1,
        "tool_key": r["tool_key"],
        "label": r["label"],
        "category": r["category"],
        "total_runs": r["total_runs"],
        "logged_in_runs": r["logged_in_runs"],
        "anon_runs": r["anon_runs"],
        "logged_in_pct": round(r["logged_in_runs"] / r["total_runs"] * 100, 1) if r["total_runs"] else 0.0,
        "anon_pct": round(r["anon_runs"] / r["total_runs"] * 100, 1) if r["total_runs"] else 0.0,
        "unique_logged_in": r["unique_logged_in"],
        "unique_anon_ips": r["unique_anon_ips"],
        "returning_users": r["returning_users"],
    } for i, r in enumerate(tool_leaderboard)]

    return {
        "period_days": days,
        "generated_at": _now_utc().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "kpis": {
            "today": kpi_today,
            "week": kpi_week,
            "month": kpi_month,
            "dau_mau_ratio": dau_mau,
            "returning_user_pct": returning_pct,
            "top_tool": top_tool,
            "daily_returning_anon_ips": sum(1 for d in anon_ip_days.values() if len(d) >= 2),
            "admin_runs": len(admin_events),
        },
        "daily_series": daily_series,
        "tool_leaderboard": tool_leaderboard,
        "scenario_split": {
            "runs_by_segment": scenario_runs,
            "identities_by_type": scenario_identities,
        },
        "return_frequency": {"buckets": cohort_buckets},
        "returning_anon_ips": returning_anon_ips,
        "logged_in_users": logged_in_users,
        "tools_matrix": tools_matrix,
    }


# ── Routes ─────────────────────────────────────────────────────────────────

def _admin_or_none():
    """Return the admin user dict, or None (→ 403). Mode-aware."""
    try:
        if use_postgres():
            from .pg_auth import get_current_user
        else:
            from .auth import get_current_user
        user = get_current_user()
        if user and user.get("role") == "admin":
            return user
    except Exception as e:
        logger.warning("usage-analytics admin check failed: %s", e)
    return None


@usage_analytics_bp.route("/api/usage/track-tool", methods=["POST"])
def track_tool():
    """Fire-and-forget beacon for pure-browser calculators."""
    data = request.get_json(silent=True) or {}
    tool_key = data.get("tool_key", "")
    if not isinstance(tool_key, str) or tool_key not in TOOL_REGISTRY:
        return jsonify({"ok": False, "error": "unknown tool"}), 400
    ip = _sanitize_ip(_client_ip())
    cache_key = f"{ip}|{tool_key}"
    now = time.time()
    last = _beacon_cache.get(cache_key)
    if last and (now - last) < _BEACON_DEDUP_TTL:
        return jsonify({"ok": True, "tracked": False})
    _beacon_cache[cache_key] = now
    # Trim cache occasionally to avoid unbounded growth.
    if len(_beacon_cache) > 5000:
        for k in list(_beacon_cache.keys()):
            if now - _beacon_cache[k] > _BEACON_DEDUP_TTL:
                _beacon_cache.pop(k, None)

    # Resolve auth for plan/identity without rejecting anonymous visitors.
    user = None
    try:
        if use_postgres():
            from .pg_auth import get_current_user
        else:
            from .auth import get_current_user
        user = get_current_user()
    except Exception:
        user = None

    record_tool_event(tool_key, user=user, sequences_count=_coerce_count(data.get("count", 1)), client_ip=ip)
    return jsonify({"ok": True, "tracked": True})


@usage_analytics_bp.route("/api/admin/usage-analytics", methods=["GET"])
def admin_usage_analytics():
    if _admin_or_none() is None:
        return jsonify({"error": "Admin access required", "code": "FORBIDDEN"}), 403
    days = request.args.get("days", 30, type=int)
    return jsonify(_build_analytics(days))


@usage_analytics_bp.route("/api/admin/usage-analytics/export.csv", methods=["GET"])
def admin_usage_analytics_csv():
    if _admin_or_none() is None:
        return jsonify({"error": "Admin access required", "code": "FORBIDDEN"}), 403
    days = request.args.get("days", 30, type=int)
    data = _build_analytics(days)

    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf)

    w.writerow(["=== Daily Active Users & Runs ==="])
    w.writerow(["date", "logged_in_runs", "anon_runs", "logged_in_users", "anon_ips"])
    for r in data["daily_series"]:
        w.writerow([r["date"], r["logged_in_runs"], r["anon_runs"], r["logged_in_users"], r["anon_ips"]])

    w.writerow([])
    w.writerow(["=== Tool Performance ==="])
    w.writerow(["rank", "tool", "category", "total_runs", "logged_in_runs", "anon_runs",
                "unique_logged_in", "unique_anon_ips", "returning_users"])
    for r in data["tools_matrix"]:
        w.writerow([r["rank"], r["label"], r["category"], r["total_runs"], r["logged_in_runs"],
                    r["anon_runs"], r["unique_logged_in"], r["unique_anon_ips"], r["returning_users"]])

    w.writerow([])
    w.writerow(["=== Returning Anonymous IPs (last 30 days) ==="])
    w.writerow(["ip", "active_days", "current_streak", "total_runs", "today_runs",
                "favorite_tools", "first_seen", "last_seen", "linked_email"])
    for r in data["returning_anon_ips"]:
        w.writerow([_csv_safe(r["ip"]), r["active_days"], r["current_streak"], r["total_runs"],
                    r["today_runs"], _csv_safe(r["favorite_tools"]), r["first_seen"], r["last_seen"],
                    _csv_safe(r["linked_email"] or "")])

    w.writerow([])
    w.writerow(["=== Logged-in Users (last 30 days) ==="])
    w.writerow(["email", "plan", "active_days", "runs_today", "runs_7d", "runs_30d",
                "tool_breakdown", "last_tool", "last_seen", "last_ip"])
    for r in data["logged_in_users"]:
        w.writerow([_csv_safe(r["email"]), _csv_safe(r["plan"]), r["active_days"], r["runs_today"], r["runs_7d"],
                    r["runs_30d"], _csv_safe(r["tool_breakdown"]), _csv_safe(r["last_tool"]),
                    r["last_seen"], _csv_safe(r["last_ip"])])

    csv_text = buf.getvalue()
    return (
        csv_text,
        200,
        {"Content-Type": "text/csv; charset=utf-8",
         "Content-Disposition": "attachment; filename=vigyanllm-usage-analytics.csv"},
    )

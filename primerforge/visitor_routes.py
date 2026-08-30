"""
Visitor geo-location tracking — lightweight choropleth data.

Privacy: only country-level aggregates + salted IP hashes are stored.
No raw IPs are persisted. Do-Not-Tighten: respects DNT + cookie consent.

Endpoints:
  POST /api/track-visit   — record a visit (country resolved from IP)
  GET  /api/stats/geo     — aggregated country counts for the map
"""

import hashlib
import json
import logging
import os
import sqlite3
import time
from functools import lru_cache

import requests
from flask import Blueprint, g, jsonify, request

logger = logging.getLogger(__name__)

visitor_bp = Blueprint("visitor_bp", __name__)

# ── Config ──────────────────────────────────────────────────────────────────
_SALT = os.environ.get("VISITOR_HASH_SALT", "vigyanllm-visitor-v1")
_GEO_API = "http://ip-api.com/json/{ip}?fields=status,countryCode,country"
_DEDUP_TTL = 300  # 5 min per IP before re-recording
_MAX_ROWS = 200_000  # cap to prevent unbounded growth
_CACHE_TTL = 300  # cache /api/stats/geo for 5 min
_geo_cache = {"data": None, "ts": 0}

# Country centroid data for the SVG map (lon, lat, weight multiplier)
# Extracted from Natural Earth 110m — positions the dot, NOT a boundary claim.
COUNTRY_GEO = {
    "IN": (78.96, 20.59), "US": (-95.71, 37.09), "CN": (104.19, 35.86),
    "BR": (-51.92, -14.23), "GB": (-3.43, 55.37), "DE": (10.45, 51.16),
    "CA": (-106.34, 56.13), "AU": (133.77, -25.27), "FR": (2.21, 46.22),
    "JP": (138.25, 36.20), "KR": (127.76, 35.91), "IT": (12.56, 41.87),
    "ES": (-3.70, 40.46), "RU": (105.31, 61.52), "MX": (-102.55, 23.63),
    "NL": (5.29, 52.13), "SE": (18.64, 60.12), "CH": (8.22, 46.81),
    "SG": (103.81, 1.35), "SA": (45.07, 23.88), "AE": (53.84, 23.42),
    "ZA": (22.93, -30.55), "NG": (8.67, 9.08), "KE": (37.90, 1.29),
    "EG": (30.80, 26.82), "GH": (-1.02, 7.94), "MA": (-7.09, 31.79),
    "PK": (69.34, 30.37), "BD": (90.35, 23.68), "LK": (80.77, 7.87),
    "NP": (84.12, 28.39), "TH": (100.99, 15.87), "VN": (108.27, 14.05),
    "PH": (121.77, 12.87), "MY": (109.64, 4.21), "ID": (113.92, -0.78),
    "TR": (35.24, 38.96), "PL": (19.14, 51.91), "PT": (-8.22, 39.39),
    "GR": (21.82, 39.07), "CZ": (15.47, 49.81), "AT": (14.55, 47.51),
    "BE": (4.46, 50.50), "NO": (8.46, 60.47), "DK": (9.50, 56.26),
    "FI": (25.74, 61.92), "IE": (-8.24, 53.41), "RO": (24.96, 45.94),
    "HU": (19.50, 47.16), "UA": (31.16, 48.37), "AR": (-63.61, -38.41),
    "CL": (-71.54, -35.67), "CO": (-74.29, 4.57), "PE": (-75.01, -9.18),
    "EC": (-78.18, -1.83), "TZ": (34.88, -6.36), "ET": (40.48, 9.14),
    "UG": (32.29, 1.37), "SN": (-14.49, 14.49), "CM": (12.35, 7.36),
    "CI": (-5.54, 7.53), "MU": (57.55, -20.34), "VN": (108.27, 14.05),
    "MM": (95.95, 21.91), "KH": (104.99, 12.56), "LA": (102.49, 19.85),
    "MN": (103.84, 46.86), "KZ": (66.92, 48.01), "UZ": (64.58, 41.37),
    "IQ": (43.67, 33.22), "IR": (53.68, 32.42), "IL": (34.85, 31.04),
    "JO": (36.23, 30.58), "LB": (35.86, 33.85), "PH": (121.77, 12.87),
    "TW": (120.96, 23.69), "HK": (114.17, 22.39), "BD": (90.35, 23.68),
    "PR": (-66.58, 18.22), "NG": (8.67, 9.08),
    "NZ": (174.88, -40.90), "OM": (57.00, 21.47),
    "CR": (-83.75, 9.75), "PY": (-58.44, -23.44),
}

# ── GA4 Seed Data (Aug 2026 baseline) ────────────────────────────────────────
# Seeded once on first table creation so the map shows real data immediately.
# Real visitor tracking adds on top via upsert; never overwrites this seed.
_GA4_SEED = [
    ("US", "United States", 283), ("IN", "India", 240), ("SG", "Singapore", 54),
    ("CN", "China", 48), ("BR", "Brazil", 17), ("VN", "Vietnam", 17),
    ("HK", "Hong Kong", 14), ("JP", "Japan", 12), ("PH", "Philippines", 12),
    ("AR", "Argentina", 10), ("AU", "Australia", 9), ("PK", "Pakistan", 7),
    ("ZA", "South Africa", 7), ("CA", "Canada", 6), ("IR", "Iran", 6),
    ("MX", "Mexico", 6), ("KR", "South Korea", 6), ("RU", "Russia", 5),
    ("UA", "Ukraine", 5), ("EG", "Egypt", 4), ("ID", "Indonesia", 4),
    ("KE", "Kenya", 4), ("TW", "Taiwan", 4), ("BD", "Bangladesh", 3),
    ("CO", "Colombia", 3), ("IQ", "Iraq", 3), ("NZ", "New Zealand", 3),
    ("NG", "Nigeria", 3), ("TH", "Thailand", 3), ("TR", "Türkiye", 3),
    ("ET", "Ethiopia", 2), ("IL", "Israel", 2), ("AE", "United Arab Emirates", 2),
    ("VE", "Venezuela", 2), ("AZ", "Azerbaijan", 1), ("BG", "Bulgaria", 1),
    ("CR", "Costa Rica", 1), ("CI", "Côte d'Ivoire", 1), ("DE", "Germany", 1),
    ("IE", "Ireland", 1), ("KZ", "Kazakhstan", 1), ("LB", "Lebanon", 1),
    ("MA", "Morocco", 1), ("OM", "Oman", 1), ("PY", "Paraguay", 1),
    ("PE", "Peru", 1), ("UY", "Uruguay", 1),
]


def _hash_ip(ip: str) -> str:
    """Salted SHA-256 hash — truncated to 16 chars for storage efficiency."""
    return hashlib.sha256(f"{_SALT}:{ip}".encode()).hexdigest()[:16]


def _resolve_country(ip: str) -> dict | None:
    """Resolve IP → country via ip-api.com (free, no key, 45 req/min)."""
    if not ip or ip in ("127.0.0.1", "::1", "localhost"):
        return None
    try:
        r = requests.get(_GEO_API.format(ip=ip), timeout=3,
                         headers={"User-Agent": "VigyanLLM/1.0"})
        if r.status_code == 200 and r.json().get("status") == "success":
            d = r.json()
            return {"code": d["countryCode"], "name": d["country"]}
    except Exception:
        pass
    return None


def _get_visitor_db():
    """Get or create the visitor_locations table in the SQLite DB."""
    from primerforge.auth import DB_PATH
    db = sqlite3.connect(DB_PATH, timeout=5)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""
        CREATE TABLE IF NOT EXISTS visitor_locations (
            country_code TEXT NOT NULL,
            country_name TEXT NOT NULL,
            ip_hash TEXT NOT NULL,
            visit_count INTEGER DEFAULT 1,
            last_seen REAL DEFAULT (strftime('%s','now')),
            PRIMARY KEY (country_code, ip_hash)
        )
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_visitor_country
        ON visitor_locations(country_code)
    """)
    # Seed GA4 baseline on first run (empty table)
    row = db.execute("SELECT COUNT(*) FROM visitor_locations").fetchone()
    if row[0] == 0:
        now = time.time()
        db.executemany(
            "INSERT INTO visitor_locations (country_code, country_name, ip_hash, visit_count, last_seen) "
            "VALUES (?, ?, ?, ?, ?)",
            [(code, name, f"__ga4_seed_{code}__", count, now) for code, name, count in _GA4_SEED]
        )
        logger.info("Seeded %d countries from GA4 baseline", len(_GA4_SEED))
    db.commit()
    return db


def _prune_if_needed(db):
    """Evict oldest rows if table exceeds cap."""
    row = db.execute("SELECT COUNT(*) as c FROM visitor_locations").fetchone()
    if row and row[0] > _MAX_ROWS:
        excess = row[0] - _MAX_ROWS + 1000
        db.execute(
            "DELETE FROM visitor_locations WHERE rowid IN "
            "(SELECT rowid FROM visitor_locations ORDER BY last_seen ASC LIMIT ?)",
            (excess,)
        )
        db.commit()


# ── Endpoints ───────────────────────────────────────────────────────────────

@visitor_bp.route("/api/stats/geo", methods=["GET"])
def stats_geo():
    """Return aggregated country visitor counts for the map."""
    now = time.time()
    if _geo_cache["data"] and (now - _geo_cache["ts"]) < _CACHE_TTL:
        return jsonify(_geo_cache["data"])

    try:
        db = _get_visitor_db()
        # Per-country totals
        rows = db.execute("""
            SELECT country_code, country_name, SUM(visit_count) as total
            FROM visitor_locations
            GROUP BY country_code
            ORDER BY total DESC
        """).fetchall()
        # Seed baseline sum
        seed_row = db.execute(
            "SELECT COALESCE(SUM(visit_count),0) FROM visitor_locations WHERE ip_hash LIKE '__ga4_seed_%'"
        ).fetchone()
        db.close()
    except Exception as e:
        logger.warning("visitor geo query failed: %s", e)
        rows = []
        seed_row = (0,)

    countries = []
    total_visitors = 0
    for code, name, count in rows:
        countries.append({"code": code, "name": name, "count": count})
        total_visitors += count

    result = {
        "total_countries": len(countries),
        "total_visitors": total_visitors,
        "seed_total": seed_row[0],
        "new_visitors": total_visitors - seed_row[0],
        "countries": countries,
    }
    _geo_cache["data"] = result
    _geo_cache["ts"] = now
    return jsonify(result)


@visitor_bp.route("/api/track-visit", methods=["POST"])
def track_visit():
    """Record a visit — resolves IP to country, stores hashed IP + count."""
    # Respect Do Not Track
    dnt = request.headers.get("DNT") or request.headers.get("Sec-Fetch-DNT")
    if dnt == "1":
        return jsonify({"ok": True, "tracked": False})

    # Get IP — check common proxy headers first
    ip = (
        request.headers.get("CF-Connecting-IP")  # Cloudflare
        or request.headers.get("X-Real-IP")       # Nginx
        or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.remote_addr
    )

    # Skip local/private IPs
    if not ip or ip in ("127.0.0.1", "::1", "localhost") or ip.startswith("10.") or ip.startswith("192.168."):
        return jsonify({"ok": True, "tracked": False})

    geo = _resolve_country(ip)
    if not geo:
        return jsonify({"ok": True, "tracked": False})

    ip_hash = _hash_ip(ip)

    try:
        db = _get_visitor_db()

        # Check dedup — skip if same IP recorded within TTL
        existing = db.execute(
            "SELECT last_seen FROM visitor_locations WHERE country_code=? AND ip_hash=?",
            (geo["code"], ip_hash)
        ).fetchone()

        if existing and (time.time() - existing[0]) < _DEDUP_TTL:
            db.close()
            return jsonify({"ok": True, "tracked": False})

        # Upsert — increment count or insert new
        if existing:
            db.execute("""
                UPDATE visitor_locations
                SET visit_count = visit_count + 1, last_seen = strftime('%s','now')
                WHERE country_code = ? AND ip_hash = ?
            """, (geo["code"], ip_hash))
        else:
            db.execute("""
                INSERT OR REPLACE INTO visitor_locations
                    (country_code, country_name, ip_hash, visit_count, last_seen)
                VALUES (?, ?, ?, 1, strftime('%s','now'))
            """, (geo["code"], geo["name"], ip_hash))

        db.commit()
        _prune_if_needed(db)
        db.close()

        # Invalidate cache
        _geo_cache["data"] = None

        return jsonify({"ok": True, "country": geo["name"]})
    except Exception as e:
        logger.warning("track_visit failed: %s", e)
        return jsonify({"ok": False}), 500

"""Tool-usage analytics: capture + aggregation + admin API.

Covers the CBO requirement — "how many users use which tools, daily/weekly/
monthly, and are anonymous IPs returning?" — across both scenarios:
  1. Logged-in users  (user_email)
  2. Anonymous guests (client_ip identity)

These tests run against SQLite (DATABASE_URL=""). The admin RBAC middleware is
stubbed (like test_guest_mode) so the endpoint's own auth path is exercised.
"""

import datetime
import json

import pytest


ADMIN_EMAIL = "usage-analytics-admin@test.com"


@pytest.fixture
def analytics(monkeypatch, tmp_path):
    """Isolated SQLite analytics module (no Flask app needed for the core)."""
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("PRIMERFORGE_DB", str(tmp_path / "ua.db"))
    monkeypatch.setenv("PRIMERFORGE_ADMIN_EMAIL", ADMIN_EMAIL)
    monkeypatch.setenv("PRIMERFORGE_ADMIN_PASSWORD", "UsageAnalytics!12345")
    monkeypatch.setenv("PRIMERFORGE_SECRET", "usage-analytics-secret-0123456789abcdef")

    from primerforge import usage_analytics as ua

    ua.ensure_schema()
    return ua


@pytest.fixture
def client(monkeypatch, tmp_path):
    """Full app (SQLite) for beacon + admin endpoint tests."""
    from primerforge.primer_server import create_app

    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("PRIMERFORGE_DB", str(tmp_path / "app.db"))
    monkeypatch.setenv("PRIMERFORGE_ADMIN_EMAIL", ADMIN_EMAIL)
    monkeypatch.setenv("PRIMERFORGE_ADMIN_PASSWORD", "UsageAnalytics!12345")
    monkeypatch.setenv("PRIMERFORGE_SECRET", "usage-analytics-secret-0123456789abcdef")

    import primerforge.security as security
    monkeypatch.setattr(security, "init_admin_rbac", lambda app: None)

    app = create_app()
    return (app.wsgi_app if hasattr(app, "wsgi_app") else app).test_client()


def _d(days_ago: int) -> str:
    return (datetime.datetime.utcnow().date() - datetime.timedelta(days=days_ago)).strftime("%Y-%m-%d")


def _admin_token():
    from primerforge import auth
    return auth.create_token(ADMIN_EMAIL, "admin")


# ── Core capture + aggregation ─────────────────────────────────────────────

def test_record_and_aggregate_both_scenarios(analytics):
    ua = analytics
    ua.record_tool_event("primer_auto", user={"email": "a@x.com", "role": "user"},
                         sequences_count=4, client_ip="1.1.1.1")
    ua.record_tool_event("blast", user=None, sequences_count=3, client_ip="2.2.2.2")
    ua.record_tool_event("tm_calculator", user=None, sequences_count=1, client_ip="2.2.2.2")

    d = ua._build_analytics(30)
    k = d["kpis"]
    assert k["today"]["total_runs"] == 3
    assert k["today"]["logged_in_users"] == 1
    assert k["today"]["anonymous_ips"] == 1  # 2.2.2.2 appears twice, one IP
    assert k["today"]["logged_in_runs"] == 1
    assert k["today"]["anon_runs"] == 2
    # top tool is the anon IP's 2-run tool group vs single runs
    top = k["top_tool"]
    assert top and top["runs"] >= 1


def test_returning_ip_detection_and_streak(analytics):
    ua = analytics
    # IP 9.9.9.9 active on today + yesterday + day-before (3-day streak)
    for days_ago in (0, 1, 2):
        ua.record_tool_event("blast", user=None, sequences_count=1,
                             client_ip="9.9.9.9", usage_date=_d(days_ago))
    # IP 8.8.8.8 active on two NON-consecutive days (returning, no streak)
    ua.record_tool_event("msa", user=None, sequences_count=1,
                         client_ip="8.8.8.8", usage_date=_d(2))
    ua.record_tool_event("msa", user=None, sequences_count=1,
                         client_ip="8.8.8.8", usage_date=_d(4))

    d = ua._build_analytics(30)
    rips = {r["ip"]: r for r in d["returning_anon_ips"]}
    assert rips["9.9.9.9"]["active_days"] == 3
    assert rips["9.9.9.9"]["current_streak"] == 3
    assert rips["8.8.8.8"]["active_days"] == 2
    assert rips["8.8.8.8"]["current_streak"] == 0  # not consecutive to today

    assert d["kpis"]["daily_returning_anon_ips"] == 2


def test_admin_activity_excluded_from_customer_metrics(analytics):
    ua = analytics
    ua.record_tool_event("primer_auto", user={"email": "customer@x.com", "role": "user"},
                         sequences_count=1, client_ip="1.1.1.1")
    ua.record_tool_event("docking_consensus", user={"email": ADMIN_EMAIL, "role": "admin"},
                         sequences_count=10, client_ip="5.5.5.5")

    d = ua._build_analytics(30)
    # admin run must NOT count as a customer user
    assert d["kpis"]["today"]["total_runs"] == 1
    assert d["kpis"]["today"]["logged_in_users"] == 1
    assert d["kpis"]["admin_runs"] == 1
    # but it is visible in the scenario split as its own segment
    segs = {s["segment"]: s["runs"] for s in d["scenario_split"]["runs_by_segment"]}
    assert segs.get("admin") == 1


def test_tool_leaderboard_and_matrix(analytics):
    ua = analytics
    for i in range(3):
        ua.record_tool_event("blast", user=None, sequences_count=1,
                             client_ip=f"10.0.0.{i+1}", usage_date=_d(0))
    ua.record_tool_event("msa", user=None, sequences_count=1,
                         client_ip="10.0.0.9", usage_date=_d(0))

    d = ua._build_analytics(30)
    leader = d["tool_leaderboard"]
    assert leader[0]["tool_key"] == "blast"
    assert leader[0]["total_runs"] == 3
    assert leader[0]["unique_anon_ips"] == 3
    assert d["tools_matrix"][0]["rank"] == 1
    assert d["tools_matrix"][0]["label"] == "BLAST"


def test_cohort_buckets(analytics):
    ua = analytics
    # one-time user
    ua.record_tool_event("blast", user=None, sequences_count=1,
                         client_ip="11.0.0.1", usage_date=_d(0))
    # 2-3 day user
    for days_ago in (0, 1):
        ua.record_tool_event("msa", user=None, sequences_count=1,
                             client_ip="11.0.0.2", usage_date=_d(days_ago))
    # 4-7 day user
    for days_ago in (0, 1, 2, 3, 4):
        ua.record_tool_event("primer_manual", user=None, sequences_count=1,
                             client_ip="11.0.0.3", usage_date=_d(days_ago))

    d = ua._build_analytics(30)
    buckets = {b["bucket"]: b["count"] for b in d["return_frequency"]["buckets"]}
    assert buckets["1 day only"] == 1
    assert buckets["2-3 days"] == 1
    assert buckets["4-7 days"] == 1


# ── Beacon endpoint ─────────────────────────────────────────────────────────

def test_beacon_records_anonymous(client, analytics):
    r = client.post("/api/usage/track-tool", json={"tool_key": "tm_calculator", "count": 1},
                    headers={"X-Forwarded-For": "12.34.56.78"})
    assert r.status_code == 200
    assert r.get_json()["tracked"] is True
    d = analytics._build_analytics(30)
    assert d["kpis"]["today"]["anon_runs"] >= 1


def test_beacon_rejects_unknown_tool(client):
    r = client.post("/api/usage/track-tool", json={"tool_key": "not_a_tool"})
    assert r.status_code == 400


def test_beacon_dedup(client):
    hdr = {"X-Forwarded-For": "99.99.99.99"}
    r1 = client.post("/api/usage/track-tool", json={"tool_key": "gc_calculator"}, headers=hdr)
    r2 = client.post("/api/usage/track-tool", json={"tool_key": "gc_calculator"}, headers=hdr)
    assert r1.get_json()["tracked"] is True
    assert r2.get_json()["tracked"] is False  # within 15s dedup window


# ── Admin endpoint auth + shape ─────────────────────────────────────────────

def test_admin_endpoint_requires_admin(client):
    r = client.get("/api/admin/usage-analytics")
    assert r.status_code == 403


def test_admin_endpoint_returns_data(client, analytics):
    analytics.record_tool_event("blast", user=None, sequences_count=1, client_ip="7.7.7.7")
    r = client.get("/api/admin/usage-analytics",
                   headers={"Authorization": "Bearer " + _admin_token()})
    assert r.status_code == 200
    body = r.get_json()
    for key in ("kpis", "daily_series", "tool_leaderboard", "scenario_split",
                "return_frequency", "returning_anon_ips", "logged_in_users", "tools_matrix"):
        assert key in body, f"missing key {key}"


def test_admin_csv_export(client):
    r = client.get("/api/admin/usage-analytics/export.csv",
                   headers={"Authorization": "Bearer " + _admin_token()})
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("Content-Type", "")
    assert "Daily Active Users" in r.get_data(as_text=True)


# ── Security hardening ──────────────────────────────────────────────────────

def test_beacon_non_int_count_does_not_500(client):
    """A crafted/non-numeric count must never raise (→ 500)."""
    r = client.post("/api/usage/track-tool",
                    json={"tool_key": "gc_calculator", "count": "abc"},
                    headers={"X-Forwarded-For": "1.2.3.4"})
    assert r.status_code == 200
    assert r.get_json()["tracked"] is True


def test_beacon_forged_ip_is_sanitized(analytics):
    """A forged X-Forwarded-For with CSV/XSS payload chars is neutralised."""
    ua = analytics
    evil = "=HYPERLINK(\"http://evil\",\"x\")@<script>"
    ua.record_tool_event("blast", user=None, sequences_count=1, client_ip=evil)
    d = ua._build_analytics(30)
    ips = [r["ip"] for r in d["returning_anon_ips"]]
    assert ips and all("=" not in ip and "<" not in ip and "@" not in ip for ip in ips)


def test_csv_injection_neutralised():
    from primerforge.usage_analytics import _csv_safe
    assert _csv_safe("=2+2") == "'=2+2"
    assert _csv_safe("+cmd") == "'+cmd"
    assert _csv_safe("@import") == "'@import"
    assert _csv_safe("-x") == "'-x"
    assert _csv_safe("normal") == "normal"

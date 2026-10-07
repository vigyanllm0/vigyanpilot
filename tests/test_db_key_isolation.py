"""SQLite / PostgreSQL connection-key isolation (P0 fix, 2026-10-07).

Production 500 on POST /api/primer/docking/consensus:

    'psycopg2.extensions.connection' object has no attribute 'execute'

Chain: pg_auth.get_current_user() → verify_token() (DB blacklist fetch_one)
/ set_rls_context() → database.get_db() stores a raw psycopg2 connection in
`g.db`. auth.get_db() used the SAME key, so every SQLite helper in
auth.py (check_daily_usage, record_daily_usage, cookie-consent writes, …)
received the psycopg2 connection and called sqlite-style `.execute()` on it.

Regression window: 2026-08-09 (506ae4c5 added the DB-persisted token
blacklist → verify_token now touches the DB on every authenticated request).
Anonymous guest traffic never calls verify_token, which is why only
logged-in users hit it — and why the anonymous prod E2E never reproduced it.
"""

import sqlite3

import pytest


@pytest.fixture
def ctx(monkeypatch, tmp_path):
    """Flask request context with a sentinel already occupying `g.db`,
    simulating the psycopg2 connection production auth leaves there."""
    from flask import Flask

    # Set before the (possibly first) import so a standalone run never
    # writes to the repo-root default; full-suite runs bind auth.DB_PATH
    # at first import like every other test (session tmp sqlite).
    monkeypatch.setenv("PRIMERFORGE_DB", str(tmp_path / "iso.db"))

    import primerforge.auth as auth

    auth.init_db()  # tables for check_daily_usage (idempotent)
    app = Flask(__name__)
    sentinel = object()  # has no .execute — same failure shape as psycopg2
    with app.test_request_context():
        from flask import g
        g.db = sentinel
        yield auth, g, sentinel


def test_auth_get_db_never_sees_the_pg_connection(ctx):
    auth, g, sentinel = ctx
    db = auth.get_db()
    assert isinstance(db, sqlite3.Connection), (
        "auth.get_db() must create its own SQLite connection, not return "
        "database.py's pooled psycopg2 `g.db`"
    )
    assert g.db is sentinel, "the PG connection must be left untouched"
    assert g.sqlitedb is db


def test_check_daily_usage_survives_poisoned_g_db(ctx):
    """The exact call that 500'd the consensus route for logged-in users."""
    auth, g, sentinel = ctx
    usage = auth.check_daily_usage("iso-test@example.com", "docking")
    assert usage["can_analyze"] is True
    assert usage["daily_used"] == 0
    assert g.db is sentinel  # still untouched — no cross-contamination


def test_close_db_pops_only_the_sqlite_key(ctx):
    auth, g, sentinel = ctx
    auth.get_db()
    assert "sqlitedb" in g and g.db is sentinel
    auth.close_db()
    assert "sqlitedb" not in g
    assert g.db is sentinel, "close_db must never close database.py's pooled conn"

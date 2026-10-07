"""Health SQLite-schema probe (RCA hardening, 2026-10-08).

Prod 500 on POST /api/primer/docking/consensus (logged-in users):

    no such column: trial_ends_at

Root-cause chain:
  1. auth.get_db()/database.get_db() shared Flask key `g.db` — pg_auth stored
     the psycopg2 connection there on every authenticated request, so SQLite
     helpers crashed ('psycopg2.extensions.connection' object has no
     attribute 'execute'; regression window 2026-08-09 → 2026-10-07, pinned
     in tests/test_db_key_isolation.py).
  2. Unmasked by fix 1: PG mode never ran auth.init_db(), so the box's legacy
     primerforge.db kept a pre-`trial_ends_at` users table and
     check_daily_usage → get_user_plan's SELECT 500'd for every logged-in
     run until create_app() started healing the schema at boot.

This test pins the /health detector plus the detect → heal loop CI relies on:
  * healthy schema            → sqlite_schema_ok true
  * stale users table         → sqlite_schema_ok false + the exact prod error
  * auth.init_db() (boot path)→ ok again
"""

import sqlite3

import pytest


@pytest.fixture
def health_env(monkeypatch, tmp_path):
    """SQLite-mode app bound to an isolated tmp DB (auth.DB_PATH rebound at
    call time so full-suite runs — auth already imported — stay isolated)."""
    db_file = str(tmp_path / "health.db")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("PRIMERFORGE_DB", db_file)
    # auth.py refuses to import without these (CI supplies them via workflow
    # env; full-suite runs via test_verification_fix — standalone runs need
    # them here). No-ops for already-imported auth.
    monkeypatch.setenv("PRIMERFORGE_ADMIN_EMAIL", "health-probe@test.com")
    monkeypatch.setenv("PRIMERFORGE_ADMIN_PASSWORD", "HealthProbe!12345")
    monkeypatch.setenv("PRIMERFORGE_SECRET", "health-probe-secret-0123456789abcdef")

    import primerforge.auth as auth

    monkeypatch.setattr(auth, "DB_PATH", db_file)

    import primerforge.security as security

    monkeypatch.setattr(security, "init_admin_rbac", lambda app: None)

    from primerforge.primer_server import create_app

    app = create_app()
    app = app.wsgi_app if hasattr(app, "wsgi_app") else app
    return app.test_client(), auth, db_file


def test_health_ok_on_fresh_schema(health_env):
    client, _auth, _db_file = health_env
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["sqlite_schema_ok"] is True, data


def test_health_detects_and_heals_stale_users_table(health_env):
    client, auth, db_file = health_env

    # Reproduce the legacy prod file: users exists, trial_ends_at doesn't.
    db = sqlite3.connect(db_file)
    db.execute("ALTER TABLE users DROP COLUMN trial_ends_at")
    db.commit()
    db.close()

    data = client.get("/health").get_json()
    assert data["status"] == "degraded", data
    assert data["sqlite_schema_ok"] is False, data
    assert "trial_ends_at" in data.get("sqlite_schema_error", ""), data

    # The production heal: create_app() runs auth.init_db() at boot in both
    # SQLite and PG mode — re-running it restores the missing column.
    auth.init_db()
    healed = client.get("/health").get_json()
    assert healed["sqlite_schema_ok"] is True, healed
    assert healed["status"] == "ok", healed

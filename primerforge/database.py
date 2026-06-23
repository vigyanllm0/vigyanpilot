#!/usr/bin/env python3
"""
VigyanLLM PostgreSQL Database Layer
======================================
Replaces the SQLite connection with PostgreSQL (psycopg2).
Connects to the containerized PostgreSQL via Docker private network.

Usage in app:
    from primerforge.database import get_db, close_db, init_db

The app sets `app.current_user_id` session variable for RLS enforcement.
"""

import os
import time
import logging
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from flask import g

logger = logging.getLogger("primerforge.database")

# ── Connection Configuration ──────────────────────────────────────────────
# When running inside Docker (via docker-compose), use the service name.
# When running locally for development, use localhost + exposed port.

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://vigyanpilot_app:CHANGE_ME_TO_A_64_CHAR_RANDOM_STRING@vigyanpilot_postgres:5432/vigyanpilot_db"
)

# Parse from URL or use individual vars (fallback)
DB_CONFIG = {
    "host": os.environ.get("PGHOST", "vigyanpilot_postgres"),
    "port": int(os.environ.get("PGPORT", "5432")),
    "dbname": os.environ.get("PGDATABASE", "vigyanpilot_db"),
    "user": os.environ.get("PGUSER", "vigyanpilot_app"),
    "password": os.environ.get("PGPASSWORD", ""),
    "connect_timeout": 5,
    "keepalives": 1,
    "keepalives_idle": 30,
    "keepalives_interval": 10,
    "keepalives_count": 5,
    "options": "-c statement_timeout=30000 -c idle_in_transaction_session_timeout=30000",
}


def _get_connection():
    """Create a new PostgreSQL connection with proper settings."""
    try:
        # Try DATABASE_URL first (standard format)
        if DATABASE_URL and "://" in DATABASE_URL:
            conn = psycopg2.connect(DATABASE_URL,
                cursor_factory=psycopg2.extras.RealDictCursor,
                keepalives=1, keepalives_idle=30,
                keepalives_interval=10, keepalives_count=5,
                connect_timeout=5)
        else:
            conn = psycopg2.connect(**DB_CONFIG, cursor_factory=psycopg2.extras.RealDictCursor)

        conn.autocommit = False
        return conn
    except psycopg2.OperationalError as e:
        logger.error(f"PostgreSQL connection failed: {e}")
        raise


def get_db():
    """Get request-scoped database connection (stored in Flask's g).

    Falls back to a standalone connection when no Flask request context is
    available (e.g., background threads running the pipeline). Callers in
    background contexts are responsible for closing the connection.
    """
    try:
        if "db" not in g:
            g.db = _get_connection()
        return g.db
    except RuntimeError:
        return _get_connection()


def close_db(e=None):
    """Close database connection at end of request."""
    db = g.pop("db", None)
    if db is not None:
        try:
            if db.closed == 0:
                db.close()
        except Exception as e:
            logger.warning("Error closing DB connection: %s", e)


def get_db_standalone():
    """
    Get a standalone connection (not request-scoped).
    Used by webhooks and background tasks that don't have Flask request context.
    Caller is responsible for closing.
    """
    return _get_connection()


@contextmanager
def db_transaction():
    """
    Context manager for atomic transactions.
    Usage:
        with db_transaction() as (conn, cur):
            cur.execute("INSERT INTO ...")
            cur.execute("UPDATE ...")
        # Auto-commits on success, rolls back on exception
    """
    conn = get_db()
    cur = conn.cursor()
    try:
        yield conn, cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def set_rls_context(user_id: int):
    """
    Set Row-Level Security context for the current request.
    Call this after authentication to enable RLS policies.
    """
    try:
        db = get_db()
        cur = db.cursor()
        try:
            cur.execute("SET app.current_user_id = %s", (str(user_id),))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            cur.close()
    except Exception:
        pass  # RLS context is best-effort


def init_db():
    """
    Verify PostgreSQL connection on startup.
    Schema is handled by initdb SQL files in Docker, not by the app.
    This just ensures connectivity and creates token_balances for existing users.
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()

        # Verify connection
        cur.execute("SELECT version()")
        version = cur.fetchone()
        logger.info(f"PostgreSQL connected: {version['version'][:50]}...")

        # Ensure token_balances exist for all users that don't have one
        cur.execute("""
            INSERT INTO token_balances (user_id)
            SELECT id FROM users u
            WHERE NOT EXISTS (SELECT 1 FROM token_balances tb WHERE tb.user_id = u.id)
        """)

        conn.commit()
        cur.close()
        conn.close()
        logger.info("Database initialization check complete.")
    except Exception as e:
        logger.error(f"Database init check failed: {e}")
        # Don't crash the app — it might be starting before Postgres is ready
        # Docker healthcheck + depends_on handles ordering


# ── Helper Functions ──────────────────────────────────────────────────────

def fetch_one(query: str, params: tuple = None) -> dict:
    """Execute query and return single row as dict, or None."""
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(query, params or ())
        row = cur.fetchone()
    except Exception:
        db.rollback()
        raise
    finally:
        cur.close()
    return dict(row) if row else None


def fetch_all(query: str, params: tuple = None) -> list:
    """Execute query and return all rows as list of dicts."""
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(query, params or ())
        rows = cur.fetchall()
    except Exception:
        db.rollback()
        raise
    finally:
        cur.close()
    return [dict(r) for r in rows]


def execute(query: str, params: tuple = None, commit: bool = True) -> int:
    """Execute a write query. Returns rowcount. Auto-commits by default."""
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(query, params or ())
        rowcount = cur.rowcount
        if commit:
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        cur.close()
    return rowcount


def execute_returning(query: str, params: tuple = None, commit: bool = True) -> dict:
    """Execute INSERT ... RETURNING and return the inserted row."""
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(query, params or ())
        row = cur.fetchone()
        if commit:
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        cur.close()
    return dict(row) if row else None

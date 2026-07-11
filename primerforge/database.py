#!/usr/bin/env python3
"""
VigyanLLM PostgreSQL Database Layer
======================================
Manages PostgreSQL connections through a psycopg2 ThreadedConnectionPool
to prevent exhausting max_connections during traffic spikes.

Usage in app:
    from primerforge.database import get_db, close_db, init_db

The app sets `app.current_user_id` session variable for RLS enforcement.
"""

import logging
import os
import threading
import time
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
import psycopg2.pool
from flask import g

# ── Logging Configuration (LOG-03 FIX) ────────────────────────────────────
# Standardize all logs to UTC rather than server local time.
logging.Formatter.converter = time.gmtime
logger = logging.getLogger("primerforge.database")

# ── Connection Pool Configuration ─────────────────────────────────────────

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is required. "
        "Set it to your PostgreSQL connection string, e.g.:\n"
        "  postgresql://user:password@host:5432/dbname"
    )

POOL_MIN = int(os.environ.get("DB_POOL_MIN", "2"))
POOL_MAX = int(os.environ.get("DB_POOL_MAX", "10"))
POOL_TIMEOUT = int(os.environ.get("DB_POOL_TIMEOUT", "5"))

_pool = None
_POOL_LOCK = threading.Lock()


def _get_pool():
    """Lazy-init and return the global connection pool (BUG-06 FIX: Thread-safe)."""
    global _pool
    # Double-checked locking pattern
    if _pool is None:
        with _POOL_LOCK:
            if _pool is None:
                try:
                    _pool = psycopg2.pool.ThreadedConnectionPool(
                        POOL_MIN, POOL_MAX,
                        dsn=DATABASE_URL,
                        cursor_factory=psycopg2.extras.RealDictCursor,
                        connect_timeout=POOL_TIMEOUT,
                        keepalives=1,
                        keepalives_idle=30,
                        keepalives_interval=10,
                        keepalives_count=5,
                    )
                    logger.info(
                        "PostgreSQL pool created (min=%d, max=%d, timeout=%ds)",
                        POOL_MIN, POOL_MAX, POOL_TIMEOUT,
                    )
                except psycopg2.OperationalError as e:
                    logger.error("PostgreSQL pool creation failed: %s", e)
                    raise
    return _pool


def _reset_pool():
    """Close and rebuild the pool (recovers from exhaustion caused by leaked connections)."""
    global _pool
    with _POOL_LOCK:
        old_pool = _pool
        _pool = None
    if old_pool is not None:
        try:
            old_pool.close()
        except Exception as e:
            logger.debug("Error closing old pool during reset: %s", e)
    logger.warning("PostgreSQL pool reset (connections may have been leaked)")


def _get_connection():
    """Get a connection from the pool. Retries once on failure, then resets pool."""
    pool = _get_pool()
    try:
        conn = pool.getconn()
        conn.autocommit = False
        # Reset session state for the borrowed connection
        try:
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = '30s'")
                cur.execute("SET idle_in_transaction_session_timeout = '30s'")
        except Exception as e:
            logger.warning("Failed to set session timeouts on connection: %s", e)
        return conn
    except psycopg2.pool.PoolError as e:
        logger.warning("Pool exhausted (max=%s), retrying: %s", POOL_MAX, e)
        time.sleep(0.5)
        try:
            conn = pool.getconn()
            conn.autocommit = False
            return conn
        except psycopg2.pool.PoolError:
            logger.error("Pool still exhausted after retry — resetting pool")
            _reset_pool()
            pool = _get_pool()
            conn = pool.getconn()
            conn.autocommit = False
            return conn


def _put_connection(conn):
    """Return a connection to the pool safely."""
    if conn is None:
        return
    pool = _get_pool()
    try:
        if conn.closed == 0:
            try:
                conn.rollback()
            except Exception as e:
                logger.debug("Rollback failed when returning connection: %s", e)
            pool.putconn(conn)
        else:
            pool.putconn(conn, key=None)
    except Exception as e:
        logger.warning("Error returning connection to pool: %s", e)


def get_db():
    """Get a request-scoped connection from the pool (stored in Flask's g).

    When no Flask request context is available (e.g. background threads),
    falls back to a standalone pool connection. Callers in background
    contexts must close the connection via close_db() or a context manager.
    """
    try:
        if "db" not in g:
            g.db = _get_connection()
        return g.db
    except RuntimeError:
        return _get_connection()


def close_db(e=None):
    """Return the request-scoped connection to the pool at end of request."""
    conn = g.pop("db", None)
    _put_connection(conn)


def get_db_standalone():
    """
    Get a standalone pool connection (not request-scoped).
    Used by webhooks and background tasks that don't have Flask request context.
    Caller MUST return the connection via put_db_standalone().
    """
    return _get_connection()


def put_db_standalone(conn):
    """Return a connection obtained via get_db_standalone() back to the pool."""
    _put_connection(conn)


@contextmanager
def db_transaction():
    """
    Context manager for atomic transactions.
    Usage:
        with db_transaction() as (conn, cur):
            cur.execute("INSERT INTO ...")
            cur.execute("UPDATE ...")
        # Auto-commits on success, rolls back on exception.
        # Connection is returned to pool on exit.
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
        # If no Flask request context, return conn to pool manually
        try:
            from flask import g as _g
            if "db" not in _g:
                _put_connection(conn)
        except (RuntimeError, ImportError):
            _put_connection(conn)


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
        except Exception as e:
            logger.error("Failed to set RLS context: %s", e)
            db.rollback()
        finally:
            cur.close()
    except Exception as e:
        logger.warning("Could not obtain DB connection to set RLS: %s", e)


def init_db():
    """
    Verify PostgreSQL connection on startup.
    Schema is handled by initdb SQL files in Docker, not by the app.
    This just ensures connectivity and creates token_balances for existing users.
    Manages its own connection from the pool.
    """
    conn = None
    try:
        conn = _get_connection()
        cur = conn.cursor()

        # Verify connection
        cur.execute("SELECT version()")
        version = cur.fetchone()
        logger.info("PostgreSQL connected: %s...", version['version'][:50])

        # Ensure token_balances exist for all users that don't have one
        cur.execute("""
            INSERT INTO token_balances (user_id)
            SELECT id FROM users u
            WHERE NOT EXISTS (SELECT 1 FROM token_balances tb WHERE tb.user_id = u.id)
        """)

        # Ensure audit_logs table exists (LOG-05 FIX: TIMESTAMPTZ instead of TIMESTAMP)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                job_id TEXT,
                accession TEXT,
                gene_symbol TEXT,
                action TEXT NOT NULL,
                source TEXT,
                ip_address TEXT,
                user_agent TEXT,
                details TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_accession ON audit_logs(accession)")

        conn.commit()
        cur.close()
        logger.info("Database initialization check complete.")
    except Exception as e:
        logger.error("Database init check failed: %s", e)
        # Don't crash the app — it might be starting before Postgres is ready
        # Docker healthcheck + depends_on handles ordering
    finally:
        if conn is not None:
            _put_connection(conn)


# ── Helper Functions ──────────────────────────────────────────────────────

def log_audit(action: str, accession: str = "", job_id: str = "", gene_symbol: str = "",
               source: str = "", details: str = "", user_id: int = None):
    """
    Insert a row into audit_logs for tracking searches and pipeline runs.
    DPDP-08 FIX: Logs user_id instead of email address to minimise PII.
    """
    try:
        from flask import request as _req
        ip = _req.remote_addr if _req else ""
        ua = (_req.headers.get("User-Agent", "") if _req else "")[:512]
        if user_id is None:
            try:
                from flask import g as _g
                user_id = _g.get("user", {}).get("user_id")
            except Exception:
                user_id = None
        execute("""
            INSERT INTO audit_logs (user_id, job_id, accession, gene_symbol, action, source, ip_address, user_agent, details)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, job_id or None, accession or None, gene_symbol or None,
              action, source or None, ip or None, ua or None, details or None))
    except Exception as e:
        logger.warning("Audit log write failed: %s", e)


def _in_request_context():
    """Return True if we're inside a Flask request context."""
    try:
        from flask import g as _g
        return True
    except (RuntimeError, ImportError):
        return False


def _get_conn_for_query():
    """
    Get a connection appropriate for a one-shot query helper.
    Inside a request context, use get_db() (teardown returns to pool).
    Outside, use get_db_standalone() (caller must return via _put_conn_for_query).
    Returns (conn, standalone).
    """
    if _in_request_context():
        return get_db(), False
    return get_db_standalone(), True


def _put_conn_for_query(conn, standalone: bool):
    """Return a connection obtained via _get_conn_for_query if standalone."""
    if standalone and conn is not None:
        put_db_standalone(conn)


def fetch_one(query: str, params: tuple = None) -> dict:
    """Execute query and return single row as dict, or None."""
    db, standalone = _get_conn_for_query()
    cur = db.cursor()
    try:
        cur.execute(query, params or ())
        row = cur.fetchone()
    except Exception:
        db.rollback()
        raise
    finally:
        cur.close()
        _put_conn_for_query(db, standalone)
    return dict(row) if row else None


def fetch_all(query: str, params: tuple = None) -> list:
    """Execute query and return all rows as list of dicts."""
    db, standalone = _get_conn_for_query()
    cur = db.cursor()
    try:
        cur.execute(query, params or ())
        rows = cur.fetchall()
    except Exception:
        db.rollback()
        raise
    finally:
        cur.close()
        _put_conn_for_query(db, standalone)
    return [dict(r) for r in rows]


def execute(query: str, params: tuple = None, commit: bool = True) -> int:
    """Execute a write query. Returns rowcount. Auto-commits by default."""
    db, standalone = _get_conn_for_query()
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
        _put_conn_for_query(db, standalone)
    return rowcount


def execute_returning(query: str, params: tuple = None, commit: bool = True) -> dict:
    """Execute INSERT ... RETURNING and return the inserted row."""
    db, standalone = _get_conn_for_query()
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
        _put_conn_for_query(db, standalone)
    return dict(row) if row else None

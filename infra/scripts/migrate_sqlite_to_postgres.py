#!/usr/bin/env python3
"""
Migration Script: SQLite → PostgreSQL
=======================================
Migrates existing VigyanLLM users, usage data, and payment history
from the SQLite database to the new PostgreSQL container.

Run this AFTER:
  1. PostgreSQL container is up and schema is initialized
  2. You have the SQLite database file path

Usage:
  python migrate_sqlite_to_postgres.py

Environment variables needed:
   DATABASE_URL=postgresql://user:password@localhost:5432/dbname
  SQLITE_PATH=/path/to/primerforge.db  (defaults to ../primerforge.db)
"""

import os
import sys
import sqlite3
import time

import psycopg2
import psycopg2.extras
import bcrypt

# ── Configuration ─────────────────────────────────────────────────────────
SQLITE_PATH = os.environ.get("SQLITE_PATH", os.path.join(os.path.dirname(__file__), "../../primerforge.db"))
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is required")
    print("  postgresql://user:password@host:5432/dbname")
    sys.exit(1)


def get_sqlite():
    """Connect to SQLite source database."""
    if not os.path.exists(SQLITE_PATH):
        print(f"ERROR: SQLite database not found at {SQLITE_PATH}")
        sys.exit(1)
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_postgres():
    """Connect to PostgreSQL target database."""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    conn.autocommit = False
    return conn


def migrate_users(sqlite_conn, pg_conn):
    """Migrate users table."""
    print("\n[1/4] Migrating users...")
    cursor = sqlite_conn.execute("SELECT * FROM users")
    users = cursor.fetchall()

    pg_cur = pg_conn.cursor()
    migrated = 0
    skipped = 0

    for user in users:
        try:
            pg_cur.execute(
                """INSERT INTO users (email, password_hash, full_name, role, status, created_at)
                   VALUES (%s, %s, %s, %s, 'active', to_timestamp(%s))
                   ON CONFLICT (email) DO NOTHING
                   RETURNING id""",
                (
                    user["email"],
                    user["password_hash"],
                    user.get("name", ""),
                    user.get("role", "user"),
                    float(user.get("created_at", time.time())),
                )
            )
            result = pg_cur.fetchone()
            if result:
                user_id = result["id"]

                # Create token_balances with migrated data
                # Convert existing paid_runs + FREE_RUNS - run_count = remaining balance
                total_allowed = 2 + (user.get("paid_runs", 0) or 0)  # FREE_RUNS=2
                runs_used = user.get("run_count", 0) or 0
                remaining = max(0, total_allowed - runs_used)

                pg_cur.execute(
                    """INSERT INTO token_balances (user_id, balance, total_purchased, total_consumed)
                       VALUES (%s, %s, %s, %s)
                       ON CONFLICT (user_id) DO NOTHING""",
                    (user_id, remaining, total_allowed, runs_used)
                )
                migrated += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  WARNING: Failed to migrate user {user['email']}: {e}")
            skipped += 1

    pg_conn.commit()
    pg_cur.close()
    print(f"  Users migrated: {migrated}, skipped (already exist): {skipped}")


def migrate_payments(sqlite_conn, pg_conn):
    """Migrate payments table."""
    print("\n[2/4] Migrating payment history...")
    cursor = sqlite_conn.execute("SELECT * FROM payments")
    payments = cursor.fetchall()

    pg_cur = pg_conn.cursor()
    migrated = 0

    for pmt in payments:
        try:
            # Find user_id in PostgreSQL
            pg_cur.execute("SELECT id FROM users WHERE email = %s", (pmt["user_email"],))
            user_row = pg_cur.fetchone()
            if not user_row:
                continue

            user_id = user_row["id"]
            amount_inr = pmt.get("amount", 49) or 49
            status_map = {"pending": "initiated", "created": "initiated", "verified": "captured"}
            pg_status = status_map.get(pmt.get("status", ""), "initiated")

            # Parse order_id from upi_ref field (contains "order_id|payment_id" or just "order_id")
            upi_ref = pmt.get("upi_ref", "") or ""
            parts = upi_ref.split("|")
            order_id = parts[0] if parts[0].startswith("order_") else None
            payment_id = parts[1] if len(parts) > 1 else None

            pg_cur.execute(
                """INSERT INTO payments
                   (user_id, gateway_order_id, gateway_payment_id, amount, currency,
                    status, product_type, tokens_purchased, initiated_at, captured_at)
                   VALUES (%s, %s, %s, %s, 'INR', %s, 'custom_topup', %s,
                           to_timestamp(%s), CASE WHEN %s = 'captured' THEN to_timestamp(%s) ELSE NULL END)
                   ON CONFLICT (gateway_order_id) DO NOTHING""",
                (
                    user_id,
                    order_id,
                    payment_id,
                    amount_inr,
                    pg_status,
                    pmt.get("runs_purchased", 1),
                    float(pmt.get("created_at", time.time())),
                    pg_status,
                    float(pmt.get("verified_at", 0) or time.time()),
                )
            )
            migrated += 1
        except Exception as e:
            print(f"  WARNING: Failed to migrate payment ID {pmt.get('id')}: {e}")

    pg_conn.commit()
    pg_cur.close()
    print(f"  Payments migrated: {migrated}")


def migrate_usage_logs(sqlite_conn, pg_conn):
    """Migrate usage_log to system_events."""
    print("\n[3/4] Migrating usage logs to system_events...")
    cursor = sqlite_conn.execute("SELECT * FROM usage_log ORDER BY created_at")
    logs = cursor.fetchall()

    pg_cur = pg_conn.cursor()
    migrated = 0

    for log in logs:
        try:
            pg_cur.execute(
                """INSERT INTO system_events (severity, module, message, context, created_at)
                   VALUES ('INFO', 'user_action', %s, %s, to_timestamp(%s))""",
                (
                    f"{log['action']}: {log.get('details', '')}",
                    f'{{"email": "{log["user_email"]}"}}',
                    float(log.get("created_at", time.time())),
                )
            )
            migrated += 1
        except Exception as e:
            pass  # Non-critical, continue

    pg_conn.commit()
    pg_cur.close()
    print(f"  Usage logs migrated: {migrated}")


def verify_migration(pg_conn):
    """Print verification counts."""
    print("\n[4/4] Verification...")
    pg_cur = pg_conn.cursor()

    pg_cur.execute("SELECT COUNT(*) AS cnt FROM users")
    print(f"  PostgreSQL users: {pg_cur.fetchone()['cnt']}")

    pg_cur.execute("SELECT COUNT(*) AS cnt FROM token_balances")
    print(f"  Token balances: {pg_cur.fetchone()['cnt']}")

    pg_cur.execute("SELECT COUNT(*) AS cnt FROM payments")
    print(f"  Payments: {pg_cur.fetchone()['cnt']}")

    pg_cur.execute("SELECT COUNT(*) AS cnt FROM system_events")
    print(f"  System events: {pg_cur.fetchone()['cnt']}")

    pg_cur.close()


def main():
    print("=" * 60)
    print("VigyanLLM: SQLite → PostgreSQL Migration")
    print("=" * 60)
    print(f"Source: {SQLITE_PATH}")
    print(f"Target: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")

    sqlite_conn = get_sqlite()
    pg_conn = get_postgres()

    try:
        migrate_users(sqlite_conn, pg_conn)
        migrate_payments(sqlite_conn, pg_conn)
        migrate_usage_logs(sqlite_conn, pg_conn)
        verify_migration(pg_conn)
        print("\n✓ Migration complete!")
    except Exception as e:
        pg_conn.rollback()
        print(f"\n✗ Migration failed: {e}")
        raise
    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    main()

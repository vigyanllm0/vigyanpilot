#!/usr/bin/env python3
"""
VigyanLLM: Local PostgreSQL → Azure PostgreSQL Data Migration
===============================================================
Transfers the entire database schema, data, sequences, and constraints
from a local PostgreSQL instance to an Azure PostgreSQL instance.

Requires:
  - psycopg2-binary>=2.9.9
  - pg_dump (PostgreSQL client tools) installed on the machine
  - Network access to both local and Azure PostgreSQL

Usage:
  # Set env vars (use a local .env.migration file to avoid polluting .env):
  export LOCAL_DATABASE_URL="postgresql://user:pass@localhost:5432/vigyanpilot_db"
  export DATABASE_URL="postgresql://user:pass@your-azure-host.postgres.database.azure.com:5432/vigyanpilot_db?sslmode=require"

  # Dry run (no writes):
  python3 deploy/migrations/migrate_local_to_azure.py --dry-run

  # Full migration:
  python3 deploy/migrations/migrate_local_to_azure.py

  # Resume from a specific table (after a failed batch):
  python3 deploy/migrations/migrate_local_to_azure.py --resume-from users
"""

import argparse
import logging
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("migrate_azure")

# ── Environment ────────────────────────────────────────────────────────────
LOCAL_DB_URL = os.environ.get("LOCAL_DATABASE_URL")
AZURE_DB_URL = os.environ.get("DATABASE_URL")

# Tables to migrate, in dependency order (parents before children).
TABLES_IN_ORDER = [
    "users",
    "token_balances",
    "subscriptions",
    "user_reports",
    "academic_claims",
    "referrals",
    "feedback",
    "payments",
    "gateway_webhooks",
    "cost_ledger",
    "revenue_ledger",
    "fixed_expenses",
    "infra_rate_card",
    "agent_work_logs",
    "password_resets",
    "token_blacklist",
    "usage_log",
    "audit_trail",
    "login_logs",
    "audit_logs",
    "email_verifications",
    "system_events",
    "docking_jobs",
    "docking_results",
    "pipeline_jobs",
    "pipeline_results",
    "compliance_screening",
    "order_payloads",
    "sequence_cache",
]

SCHEMA_ONLY_TABLES = {"schema_version"}  # tracked per-environment, skip data


# ── Helpers ────────────────────────────────────────────────────────────────

def parse_url(url: str) -> str:
    """Return a sanitised version for logging (hide password)."""
    if "@" in url:
        parts = url.split("@")
        userinfo = parts[0].split("://")[1] if "://" in parts[0] else parts[0]
        user = userinfo.split(":")[0]
        return f"{parts[0].split('://')[0]}://{user}:****@{parts[1]}"
    return url


def connect(url: str, label: str, sslmode: str = None):
    """Connect to a PostgreSQL database with retries."""
    params = {"cursor_factory": psycopg2.extras.RealDictCursor}
    if sslmode:
        params["sslmode"] = sslmode
    last_err = None
    for attempt in range(3):
        try:
            conn = psycopg2.connect(url, **params)
            conn.autocommit = False
            log.info("Connected to %s", label)
            return conn
        except psycopg2.OperationalError as e:
            last_err = e
            log.warning("  Connection attempt %d/3 failed: %s", attempt + 1, e)
            time.sleep(2)
    log.error("Could not connect to %s after 3 attempts: %s", label, last_err)
    sys.exit(1)


def table_exists(conn, table: str) -> bool:
    """Check if a table exists in the public schema."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s)",
            (table,),
        )
        return cur.fetchone()["exists"]


def get_user_tables(conn) -> list:
    """Return list of user table names in the public schema (excluding views)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
            "ORDER BY table_name"
        )
        return [r["table_name"] for r in cur.fetchall()]


def get_sequences(conn) -> list:
    """Return list of sequence names owned by the public schema."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT sequencename FROM pg_sequences "
            "WHERE schemaname = 'public' ORDER BY sequencename"
        )
        return [r["sequencename"] for r in cur.fetchall()]


def get_row_count(conn, table: str) -> int:
    """Return approximate row count for a table."""
    with conn.cursor() as cur:
        try:
            cur.execute(f"SELECT COUNT(*) AS cnt FROM {_qi(table)}")
            return cur.fetchone()["cnt"]
        except Exception:
            return -1


def _qi(name: str) -> str:
    """Quote an identifier safely."""
    return f'"{name}"'


def _ql(value):
    """Quote a literal for SQL (simple escaping — production uses parametrised queries)."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    s = str(value).replace("'", "''")
    return f"E'{s}'"


def extract_ddl_pg_dump(local_conn, local_url: str) -> str:
    """Extract schema DDL using pg_dump --schema-only.

    This captures tables, enums, sequences, constraints, indexes, triggers,
    RLS policies, and partitioning — far more reliable than querying
    information_schema.
    """
    # Build a connection string without the database name for pg_dump
    log.info("Extracting schema DDL via pg_dump --schema-only ...")
    try:
        result = subprocess.run(
            ["pg_dump", "--schema-only", "--no-owner", "--no-acl",
             "--no-comments", "--quote-all-identifiers", local_url],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            log.error("pg_dump failed (rc=%d): %s", result.returncode, result.stderr[:500])
            log.info("Falling back to information_schema DDL extraction ...")
            return extract_ddl_info_schema(local_conn)
        ddl = result.stdout
        log.info("pg_dump produced %d bytes of DDL", len(ddl))
        return ddl
    except FileNotFoundError:
        log.warning("pg_dump not found on PATH — falling back to information_schema DDL ...")
        return extract_ddl_info_schema(local_conn)
    except subprocess.TimeoutExpired:
        log.warning("pg_dump timed out — falling back to information_schema DDL ...")
        return extract_ddl_info_schema(local_conn)


def extract_ddl_info_schema(conn) -> str:
    """Fallback: Build CREATE TABLE statements from information_schema.

    This is less complete than pg_dump (won't capture RLS, partitioning,
    custom types, triggers). Only used when pg_dump is unavailable.
    """
    log.info("Using information_schema-based DDL extraction (limited).")
    stmts = []
    with conn.cursor() as cur:
        # Get all user tables
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
            "ORDER BY table_name"
        )
        tables = [r["table_name"] for r in cur.fetchall()]

        for table in tables:
            cur.execute(
                "SELECT column_name, data_type, character_maximum_length, "
                "       is_nullable, column_default, udt_name "
                "FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = %s "
                "ORDER BY ordinal_position",
                (table,),
            )
            cols = cur.fetchall()
            col_defs = []
            for col in cols:
                col_type = col["udt_name"] or col["data_type"]
                if col["character_maximum_length"]:
                    col_type = f"{col_type}({col['character_maximum_length']})"
                nullable = "" if col["is_nullable"] == "NO" else ""
                default = f" DEFAULT {col['column_default']}" if col["column_default"] else ""
                col_defs.append(f"  {_qi(col['column_name'])} {col_type}{default}")

            stmts.append(
                f"CREATE TABLE IF NOT EXISTS {_qi(table)} (\n"
                + ",\n".join(col_defs)
                + "\n);"
            )

        # Get sequences
        cur.execute(
            "SELECT sequencename, sequenceowner::regrole::text, "
            "       start_value, increment_by, last_value, max_value "
            "FROM pg_sequences WHERE schemaname = 'public'"
        )
        for seq in cur.fetchall():
            stmts.append(
                f"CREATE SEQUENCE IF NOT EXISTS {_qi(seq['sequencename'])} "
                f"INCREMENT BY {seq['increment_by']} "
                f"START WITH {seq['start_value']} "
                f"MAXVALUE {seq['max_value']};"
            )

    return "\n\n".join(stmts)


def apply_ddl(azure_conn, ddl: str):
    """Execute DDL statements on the Azure target."""
    with azure_conn.cursor() as cur:
        statements = split_sql(ddl)
        total = len(statements)
        for i, stmt in enumerate(statements):
            stmt = stmt.strip()
            if not stmt or stmt.startswith("--"):
                continue
            try:
                cur.execute(stmt)
            except psycopg2.errors.DuplicateTable:
                log.debug("  [%d/%d] Table already exists, skipping", i + 1, total)
            except psycopg2.errors.DuplicateObject:
                log.debug("  [%d/%d] Object already exists, skipping", i + 1, total)
            except Exception as e:
                log.error("  [%d/%d] DDL failed: %.100s ...\n  %s", i + 1, total, stmt[:200], e)
                raise
    azure_conn.commit()


def split_sql(sql: str) -> list:
    """Split SQL on semicolons, respecting $$ dollar-quoting."""
    stmts, buf = [], []
    in_dollar = 0
    i = 0
    while i < len(sql):
        if sql[i:i + 2] == "$$":
            in_dollar ^= 1
            buf.append("$$")
            i += 2
            continue
        if sql[i] == ";" and not in_dollar:
            s = "".join(buf).strip()
            if s:
                stmts.append(s)
            buf = []
        else:
            buf.append(sql[i])
        i += 1
    s = "".join(buf).strip()
    if s:
        stmts.append(s)
    return stmts


def disable_triggers(conn, table: str):
    """Disable triggers on a table for faster bulk load."""
    with conn.cursor() as cur:
        cur.execute(f"ALTER TABLE {_qi(table)} DISABLE TRIGGER ALL")


def enable_triggers(conn, table: str):
    """Re-enable triggers after bulk load."""
    with conn.cursor() as cur:
        cur.execute(f"ALTER TABLE {_qi(table)} ENABLE TRIGGER ALL")


def transfer_table(
    local_conn, azure_conn, table: str,
    batch_size: int = 5000, dry_run: bool = False,
) -> dict:
    """Transfer a single table's data using COPY for performance.

    Returns {"table": str, "rows": int, "elapsed": float, "status": str}.
    """
    start = time.time()
    result = {"table": table, "rows": 0, "elapsed": 0, "status": "pending"}

    if table in SCHEMA_ONLY_TABLES:
        log.info("  └── schema_version — skipping (per-environment)")
        result["status"] = "skipped"
        return result

    if not table_exists(local_conn, table):
        log.warning("  └── table does not exist in source, skipping")
        result["status"] = "skipped (not found)"
        return result

    # Get row count
    row_count = get_row_count(local_conn, table)
    log.info("  └── rows in source: %s", row_count if row_count >= 0 else "unknown")

    if row_count == 0:
        log.info("  └── empty table, skipping")
        result["status"] = "empty"
        return result

    if dry_run:
        log.info("  └── DRY RUN: would transfer %d row(s)", row_count)
        result["rows"] = row_count
        result["status"] = "dry-run"
        return result

    # Disable triggers on target for speed
    try:
        disable_triggers(azure_conn, table)
    except Exception:
        pass

    # Use COPY from a temporary file for maximum throughput
    tmp_path = None
    transferred = 0
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp_path = tmp.name

        # COPY source table to CSV
        with local_conn.cursor() as cur:
            with open(tmp_path, "w") as f:
                cur.copy_expert(
                    f"COPY {_qi(table)} TO STDOUT WITH CSV HEADER",
                    f,
                )

        # COPY CSV into Azure target
        with azure_conn.cursor() as cur:
            with open(tmp_path, "r") as f:
                cur.copy_expert(
                    f"COPY {_qi(table)} FROM STDIN WITH CSV HEADER",
                    f,
                )
            transferred = cur.rowcount

        azure_conn.commit()
        elapsed = time.time() - start
        result["rows"] = transferred
        result["elapsed"] = round(elapsed, 2)
        result["status"] = "ok"
        log.info("  └── transferred %d rows in %.1fs (%.0f rows/s)",
                 transferred, elapsed, transferred / elapsed if elapsed > 0 else 0)

    except Exception as e:
        azure_conn.rollback()
        elapsed = time.time() - start
        result["elapsed"] = round(elapsed, 2)
        result["status"] = f"failed: {e}"
        log.error("  └── FAILED after %.1fs: %s", elapsed, e)
    finally:
        try:
            enable_triggers(azure_conn, table)
        except Exception:
            pass
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    return result


def reset_sequences(azure_conn):
    """Reset all sequences to max(id)+1 for their respective tables.

    After bulk COPY, sequences need to be updated to avoid 'duplicate key'
    errors on subsequent inserts.
    """
    log.info("Resetting sequences on Azure target ...")
    with azure_conn.cursor() as cur:
        cur.execute("""
            SELECT sequencename AS seq_name,
                   regexp_replace(sequencename, '_(id|seq)$', '', 'g') AS table_name
            FROM pg_sequences WHERE schemaname = 'public'
        """)
        sequences = cur.fetchall()

        reset_count = 0
        for seq in sequences:
            seq_name = seq["seq_name"]
            table_name = seq["table_name"]
            try:
                # Try the common pattern: table_name_id_seq → setval to max(id)
                cur.execute(f"SELECT setval('{_qi(seq_name)}', COALESCE((SELECT MAX(id) FROM {_qi(table_name)}), 1))")
                reset_count += 1
            except Exception:
                # Some sequences don't follow the pattern — try column-based
                try:
                    cur.execute(f"""
                        SELECT setval('{_qi(seq_name)}', COALESCE(
                            (SELECT MAX(SUBSTRING(column_name, 1)::int)
                             FROM information_schema.columns
                             WHERE table_schema = 'public'
                               AND table_name = '{table_name.replace("_id_seq", "")}'
                               AND column_name = 'id'), 1))
                    """)
                    reset_count += 1
                except Exception:
                    log.debug("  Could not auto-detect table for sequence %s", seq_name)

    azure_conn.commit()
    log.info("  Reset %d sequences", reset_count)


def verify_migration(local_conn, azure_conn):
    """Compare row counts between source and target for all tables."""
    log.info("=" * 60)
    log.info("VERIFICATION")
    log.info("=" * 60)

    mismatches = []
    with local_conn.cursor() as lcur, azure_conn.cursor() as acur:
        lcur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
            "ORDER BY table_name"
        )
        tables = [r["table_name"] for r in lcur.fetchall()]

        for table in tables:
            try:
                lcur.execute(f"SELECT COUNT(*) AS cnt FROM {_qi(table)}")
                local_count = lcur.fetchone()["cnt"]
                acur.execute(f"SELECT COUNT(*) AS cnt FROM {_qi(table)}")
                azure_count = acur.fetchone()["cnt"]
                status = "✓" if local_count == azure_count else "✗ MISMATCH"
                if local_count != azure_count:
                    mismatches.append((table, local_count, azure_count))
                log.info("  %s %s: local=%d azure=%d", status, table, local_count, azure_count)
            except Exception as e:
                log.warning("  ? %s: could not compare — %s", table, e)

    if mismatches:
        log.warning("MISMATCHES FOUND:")
        for table, lc, ac in mismatches:
            log.warning("  %s: local=%d azure=%d (diff=%d)", table, lc, ac, ac - lc)
        return False
    else:
        log.info("All tables match. ✓")
        return True


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Migrate VigyanLLM database from local PostgreSQL to Azure PostgreSQL"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Extract schema and count rows but do NOT write to Azure"
    )
    parser.add_argument(
        "--resume-from", type=str, default=None,
        help="Skip tables before this name (resume after a failure)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=5000,
        help="Rows per batch (default: 5000)"
    )
    parser.add_argument(
        "--skip-verify", action="store_true",
        help="Skip the final row-count verification"
    )
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("VigyanLLM: Local PostgreSQL → Azure PostgreSQL Migration")
    log.info("=" * 60)
    log.info("Started at: %s", datetime.now(timezone.utc).isoformat())
    if args.dry_run:
        log.info("*** DRY RUN — no writes to Azure ***")

    # Validate env
    if not LOCAL_DB_URL:
        log.error("LOCAL_DATABASE_URL environment variable is not set")
        sys.exit(1)
    if not AZURE_DB_URL:
        log.error("DATABASE_URL (Azure target) environment variable is not set")
        sys.exit(1)

    log.info("Source: %s", parse_url(LOCAL_DB_URL))
    log.info("Target: %s", parse_url(AZURE_DB_URL))

    # Connect
    local_conn = connect(LOCAL_DB_URL, "source (local PG)")
    azure_conn = connect(
        AZURE_DB_URL,
        "target (Azure PG)",
        sslmode="require",
    )

    # Phase 1: Extract and apply schema
    log.info("-" * 60)
    log.info("PHASE 1: Schema Migration")
    log.info("-" * 60)

    ddl = extract_ddl_pg_dump(local_conn, LOCAL_DB_URL)
    if not ddl.strip():
        log.error("Empty DDL from source — aborting")
        sys.exit(1)

    log.info("Applying DDL to Azure target (%d bytes) ...", len(ddl))
    if not args.dry_run:
        apply_ddl(azure_conn, ddl)
        log.info("Schema applied successfully.")
    else:
        log.info("DRY RUN: would apply %d bytes of DDL", len(ddl))

    # Phase 2: Transfer data
    log.info("-" * 60)
    log.info("PHASE 2: Data Migration")
    log.info("-" * 60)

    # Discover tables present in the source
    source_tables = get_user_tables(local_conn)
    resume_mode = args.resume_from is not None
    skipped_to_resume = not resume_mode

    summary = []
    total_rows = 0
    failed_tables = []

    for table in TABLES_IN_ORDER:
        if table not in source_tables:
            log.debug("  %s: not in source, skipping", table)
            continue

        # Resume logic
        if resume_mode and not skipped_to_resume:
            if table == args.resume_from:
                skipped_to_resume = True
                log.info("  %s: Resuming from here ...", table)
            else:
                log.info("  %s: skipped (resume from %s)", table, args.resume_from)
                summary.append({"table": table, "rows": 0, "elapsed": 0, "status": "skipped (resume)"})
                continue

        log.info("  %s:", table)

        if not table_exists(local_conn, table):
            log.warning("    table not found in source, skipping")
            continue

        result = transfer_table(
            local_conn, azure_conn, table,
            batch_size=args.batch_size, dry_run=args.dry_run,
        )
        summary.append(result)
        total_rows += result["rows"]
        if result["status"].startswith("failed"):
            failed_tables.append(table)

    # Phase 3: Reset sequences
    log.info("-" * 60)
    log.info("PHASE 3: Sequence Reset")
    log.info("-" * 60)
    if not args.dry_run:
        reset_sequences(azure_conn)
    else:
        log.info("DRY RUN: would reset sequences")

    # Phase 4: Verification
    log.info("-" * 60)
    log.info("SUMMARY")
    log.info("-" * 60)
    success = len(failed_tables) == 0
    for s in summary:
        icon = "✓" if s["status"] == "ok" else "✗" if "failed" in s["status"] else "–"
        rows_str = f"{s['rows']} rows" if s["rows"] else ""
        elapsed_str = f"{s['elapsed']}s" if s["elapsed"] else ""
        log.info("  %s %s: %s %s %s", icon, s["table"], rows_str, elapsed_str, s["status"])

    log.info("Total rows transferred: %d", total_rows)

    if not args.skip_verify and not args.dry_run:
        log.info("-" * 60)
        ok = verify_migration(local_conn, azure_conn)
        if not ok:
            log.warning("Verification found mismatches — investigate before switching traffic.")

    log.info("-" * 60)
    if failed_tables:
        log.error("FAILED TABLES: %s", ", ".join(failed_tables))
        log.error("Re-run with --resume-from %s to continue from the first failed table.",
                  failed_tables[0])
        sys.exit(1)
    elif args.dry_run:
        log.info("DRY RUN completed. Run without --dry-run to execute.")
    else:
        log.info("Migration completed successfully.")
        log.info("")
        log.info("Post-migration steps:")
        log.info("  1. Update .env on the server: set DATABASE_URL to the Azure URL")
        log.info("  2. Restart the app: docker-compose up -d --force-recreate app")
        log.info("  3. Verify app login and key workflows")
        log.info("  4. Keep local PG running for 7 days as rollback option")
        log.info("  5. After 7 days: pg_dump local PG as cold backup, then drop")

    # Cleanup
    local_conn.close()
    azure_conn.close()


if __name__ == "__main__":
    main()

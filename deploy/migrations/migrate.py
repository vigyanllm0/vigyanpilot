#!/usr/bin/env python3
"""
VigyanLLM Database Migration Runner
=====================================
Applied automatically during CI/CD deploy.
Tracks which migrations have run via `schema_version` table.
"""
import os
import sys
import glob
import re
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent
INITDB_DIR = Path(__file__).parent.parent.parent / "infra" / "initdb"
DATABASE_URL = os.environ.get("DATABASE_URL", "")

if not DATABASE_URL:
    print("No DATABASE_URL set — skipping migrations")
    sys.exit(0)

import urllib.parse

import psycopg2

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cur = conn.cursor()


def get_applied():
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("SELECT version FROM schema_version ORDER BY version")
    return {row[0] for row in cur.fetchall()}


def detect_existing_schema():
    """Check if tables already exist (e.g., from Docker init)."""
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'users'
        )
    """)
    return cur.fetchone()[0]


def apply_file(version, name, sql):
    for stmt in sql.split(";"):
        s = stmt.strip()
        if s:
            cur.execute(s)
    cur.execute(
        "INSERT INTO schema_version (version, name) VALUES (%s, %s)",
        (version, name),
    )
    print(f"  ✓ {version:04d}-{name}")


def main():
    p = urllib.parse.urlparse(DATABASE_URL)
    print("VigyanLLM Migration Runner")
    print(f"  Host: {p.hostname}:{p.port}")
    print(f"  DB:   {p.path.lstrip('/')}")

    applied = get_applied()

    # If tables exist but no migrations tracked, mark infra/initdb as applied
    if not applied and detect_existing_schema():
        print("  Schema exists (from Docker init) — marking as applied...")
        initdb_files = sorted(glob.glob(str(INITDB_DIR / "*.sql")))
        for fpath in initdb_files:
            fname = Path(fpath).name
            match = re.match(r"^(\d{3})[-_]", fname)
            if match:
                version = int(match.group(1))
                cur.execute(
                    "INSERT INTO schema_version (version, name) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (version, fname.replace(".sql", "")),
                )
                print(f"  ✓ {version:03d}-{fname}")
        conn.commit()

    # Run pending migrations from deploy/migrations/
    migration_files = sorted(glob.glob(str(MIGRATIONS_DIR / "*.sql")))
    pending = 0
    for fpath in migration_files:
        fname = Path(fpath).name
        match = re.match(r"^(\d{4})[-_].*\.sql$", fname)
        if not match:
            continue
        version = int(match.group(1))
        if version in applied:
            continue
        with open(fpath) as f:
            sql = f.read()
        print(f"  → Applying {fname} ...", end=" ")
        apply_file(version, fname.replace(".sql", ""), sql)
        pending += 1

    if pending == 0:
        print("  Schema up to date.")
    else:
        print(f"\n  Applied {pending} migration(s).")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Automated data retention cleanup for VigyanLLM."""
import os, sys, psycopg2, logging
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger('retention')

def get_db():
    url = os.environ.get('DATABASE_URL', '')
    if not url:
        log.error('DATABASE_URL not set'); sys.exit(1)
    return psycopg2.connect(url)

def run_cleanup(conn):
    cur = conn.cursor()
    now = datetime.now(timezone.utc)
    results = []
    
    # 1. anon_daily_usage > 7 days
    cur.execute("DELETE FROM anon_daily_usage WHERE usage_date < %s", (now - timedelta(days=7),))
    results.append(f"anon_daily_usage: {cur.rowcount} rows deleted")
    
    # 2. consent_logs > 365 days
    cur.execute("DELETE FROM consent_logs WHERE created_at < %s", (now - timedelta(days=365),))
    results.append(f"consent_logs: {cur.rowcount} rows deleted")
    
    # 3. api_usage_logs > 90 days
    try:
        cur.execute("DELETE FROM api_usage_logs WHERE created_at < %s", (now - timedelta(days=90),))
        results.append(f"api_usage_logs: {cur.rowcount} rows deleted")
    except psycopg2.errors.UndefinedTable:
        results.append("api_usage_logs: table not found, skipped")
        conn.rollback()
    
    # 4. gateway_webhooks > 90 days
    cur.execute("DELETE FROM gateway_webhooks WHERE created_at < %s", (now - timedelta(days=90),))
    results.append(f"gateway_webhooks: {cur.rowcount} rows deleted")
    
    # 5. expired token blacklist
    try:
        cur.execute("DELETE FROM token_blacklist WHERE expires_at < %s", (now,))
        results.append(f"token_blacklist: {cur.rowcount} expired entries deleted")
    except psycopg2.errors.UndefinedTable:
        results.append("token_blacklist: table not found, skipped")
        conn.rollback()
    
    # 6. old audit_logs > 365 days
    try:
        cur.execute("DELETE FROM audit_logs WHERE created_at < %s", (now - timedelta(days=365),))
        results.append(f"audit_logs: {cur.rowcount} rows deleted")
    except psycopg2.errors.UndefinedTable:
        results.append("audit_logs: table not found, skipped")
        conn.rollback()
    
    conn.commit()
    return results

def main():
    log.info("Starting data retention cleanup")
    conn = get_db()
    try:
        results = run_cleanup(conn)
        for r in results:
            log.info(r)
        log.info("Retention cleanup completed successfully")
    except Exception as e:
        log.error(f"Retention cleanup failed: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    main()

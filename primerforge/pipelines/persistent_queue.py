"""
VigyanLLM — Persistent Job Queue

Redis-compatible job queue using SQLite for persistence.
Provides crash resilience without requiring Redis infrastructure.

Features:
- ACID transactions (survives crashes)
- Job locking (no double-processing)
- Priority queues (urgent > normal > batch)
- Automatic stale job recovery
- Queue depth monitoring

Usage:
    from persistent_queue import PersistentQueue
    q = PersistentQueue()
    job_id = q.enqueue(job_data)
    job = q.claim()
    q.complete(job_id, result)
"""

import json
import logging
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

DEFAULT_DB_PATH = os.environ.get('JOB_QUEUE_DB', '/tmp/vigyanllm_queue.db')
STALE_TIMEOUT_MINUTES = 15
MAX_RETRIES = 3

# Job statuses
STATUS_PENDING = 'pending'
STATUS_CLAIMED = 'claimed'
STATUS_RUNNING = 'running'
STATUS_COMPLETE = 'complete'
STATUS_FAILED = 'failed'

# Priority levels
PRIORITY_URGENT = 0
PRIORITY_NORMAL = 1
PRIORITY_BATCH = 2


@dataclass
class Job:
    """A job in the queue."""
    job_id: str
    status: str
    priority: int
    data: dict
    result: dict = None
    error: str = ''
    created_at: float = 0.0
    claimed_at: float = 0.0
    completed_at: float = 0.0
    retries: int = 0
    worker_id: str = ''


class PersistentQueue:
    """
    SQLite-backed persistent job queue.
    Thread-safe with WAL mode for concurrent reads.
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return self._local.conn

    def _init_db(self):
        """Create tables if not exists."""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'pending',
                priority INTEGER NOT NULL DEFAULT 1,
                data TEXT NOT NULL,
                result TEXT,
                error TEXT DEFAULT '',
                created_at REAL NOT NULL,
                claimed_at REAL DEFAULT 0,
                completed_at REAL DEFAULT 0,
                retries INTEGER DEFAULT 0,
                worker_id TEXT DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
            CREATE INDEX IF NOT EXISTS idx_jobs_priority ON jobs(priority, created_at);
            CREATE INDEX IF NOT EXISTS idx_jobs_status_priority ON jobs(status, priority, created_at);

            CREATE TABLE IF NOT EXISTS queue_stats (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                total_enqueued INTEGER DEFAULT 0,
                total_completed INTEGER DEFAULT 0,
                total_failed INTEGER DEFAULT 0,
                last_updated REAL DEFAULT 0
            );

            INSERT OR IGNORE INTO queue_stats (id) VALUES (1);
        """)
        conn.commit()

    def enqueue(self, data: dict, job_id: str = None, priority: int = PRIORITY_NORMAL) -> str:
        """
        Add a job to the queue.

        Args:
            data: Job data (must be JSON-serializable)
            job_id: Optional job ID (auto-generated if not provided)
            priority: Priority level (0=urgent, 1=normal, 2=batch)

        Returns:
            Job ID
        """
        import uuid
        if not job_id:
            job_id = f"job_{int(time.time())}_{uuid.uuid4().hex[:8]}"

        conn = self._get_conn()
        conn.execute(
            "INSERT INTO jobs (job_id, status, priority, data, created_at) VALUES (?, ?, ?, ?, ?)",
            (job_id, STATUS_PENDING, priority, json.dumps(data), time.time())
        )
        conn.execute(
            "UPDATE queue_stats SET total_enqueued = total_enqueued + 1, last_updated = ?",
            (time.time(),)
        )
        conn.commit()

        logger.info("Enqueued job %s (priority=%d)", job_id, priority)
        return job_id

    def claim(self, worker_id: str = None, timeout: float = 5.0) -> Optional[Job]:
        """
        Claim the next pending job.

        Args:
            worker_id: Identifier for this worker
            timeout: How long to wait for a job (seconds)

        Returns:
            Claimed Job or None
        """
        if not worker_id:
            worker_id = f"worker_{os.getpid()}"

        conn = self._get_conn()
        deadline = time.time() + timeout

        while time.time() < deadline:
            # Find and claim highest-priority pending job
            row = conn.execute(
                """SELECT job_id, data, priority, created_at
                   FROM jobs
                   WHERE status = ?
                   ORDER BY priority ASC, created_at ASC
                   LIMIT 1""",
                (STATUS_PENDING,)
            ).fetchone()

            if row:
                now = time.time()
                try:
                    conn.execute(
                        """UPDATE jobs
                           SET status = ?, claimed_at = ?, worker_id = ?
                           WHERE job_id = ? AND status = ?""",
                        (STATUS_CLAIMED, now, worker_id, row['job_id'], STATUS_PENDING)
                    )
                    conn.commit()

                    logger.info("Claimed job %s (worker=%s)", row['job_id'], worker_id)
                    return Job(
                        job_id=row['job_id'],
                        status=STATUS_CLAIMED,
                        priority=row['priority'],
                        data=json.loads(row['data']),
                        created_at=row['created_at'],
                        claimed_at=now,
                        worker_id=worker_id,
                    )
                except Exception:
                    conn.rollback()
                    continue

            # No jobs available — wait briefly
            time.sleep(0.1)

        return None

    def complete(self, job_id: str, result: dict = None):
        """Mark a job as complete."""
        conn = self._get_conn()
        conn.execute(
            """UPDATE jobs
               SET status = ?, result = ?, completed_at = ?
               WHERE job_id = ?""",
            (STATUS_COMPLETE, json.dumps(result or {}), time.time(), job_id)
        )
        conn.execute(
            "UPDATE queue_stats SET total_completed = total_completed + 1, last_updated = ?",
            (time.time(),)
        )
        conn.commit()
        logger.info("Completed job %s", job_id)

    def fail(self, job_id: str, error: str = '', retry: bool = True):
        """
        Mark a job as failed. Optionally retry if retries remaining.
        """
        conn = self._get_conn()

        if retry:
            row = conn.execute(
                "SELECT retries FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()

            if row and row['retries'] < MAX_RETRIES:
                conn.execute(
                    """UPDATE jobs
                       SET status = ?, retries = retries + 1, error = ?, claimed_at = 0, worker_id = ''
                       WHERE job_id = ?""",
                    (STATUS_PENDING, error, job_id)
                )
                conn.commit()
                logger.warning("Retrying job %s (attempt %d)", job_id, row['retries'] + 1)
                return

        conn.execute(
            """UPDATE jobs
               SET status = ?, error = ?, completed_at = ?
               WHERE job_id = ?""",
            (STATUS_FAILED, error, time.time(), job_id)
        )
        conn.execute(
            "UPDATE queue_stats SET total_failed = total_failed + 1, last_updated = ?",
            (time.time(),)
        )
        conn.commit()
        logger.error("Failed job %s: %s", job_id, error)

    def release_stale(self, timeout_minutes: float = STALE_TIMEOUT_MINUTES) -> int:
        """Release jobs that have been claimed/running for too long."""
        conn = self._get_conn()
        cutoff = time.time() - (timeout_minutes * 60)

        result = conn.execute(
            """UPDATE jobs
               SET status = ?, claimed_at = 0, worker_id = ''
               WHERE status IN (?, ?) AND claimed_at < ?""",
            (STATUS_PENDING, STATUS_CLAIMED, STATUS_RUNNING, cutoff)
        )
        conn.commit()

        if result.rowcount > 0:
            logger.warning("Released %d stale jobs", result.rowcount)
        return result.rowcount

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()

        if not row:
            return None

        return Job(
            job_id=row['job_id'],
            status=row['status'],
            priority=row['priority'],
            data=json.loads(row['data']),
            result=json.loads(row['result']) if row['result'] else None,
            error=row['error'] or '',
            created_at=row['created_at'],
            claimed_at=row['claimed_at'] or 0,
            completed_at=row['completed_at'] or 0,
            retries=row['retries'],
            worker_id=row['worker_id'] or '',
        )

    def get_stats(self) -> dict:
        """Get queue statistics."""
        conn = self._get_conn()

        stats = dict(conn.execute("SELECT * FROM queue_stats WHERE id = 1").fetchone())

        # Current counts
        for status in [STATUS_PENDING, STATUS_CLAIMED, STATUS_RUNNING, STATUS_COMPLETE, STATUS_FAILED]:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM jobs WHERE status = ?", (status,)
            ).fetchone()
            stats[f'{status}_count'] = row['cnt']

        # Priority breakdown
        for priority in [PRIORITY_URGENT, PRIORITY_NORMAL, PRIORITY_BATCH]:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM jobs WHERE status = 'pending' AND priority = ?",
                (priority,)
            ).fetchone()
            stats[f'priority_{priority}_pending'] = row['cnt']

        # Average processing time
        row = conn.execute(
            """SELECT AVG(completed_at - created_at) as avg_time
               FROM jobs WHERE status = 'complete' AND completed_at > 0"""
        ).fetchone()
        stats['avg_processing_time'] = round(row['avg_time'] or 0, 2)

        # Failure rate
        total = stats.get('total_enqueued', 0)
        failed = stats.get('total_failed', 0)
        stats['failure_rate'] = round(failed / max(1, total), 3)

        return stats

    def list_jobs(self, status: str = None, limit: int = 50) -> list:
        """List jobs with optional status filter."""
        conn = self._get_conn()
        if status:
            rows = conn.execute(
                "SELECT job_id, status, priority, created_at, error FROM jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT job_id, status, priority, created_at, error FROM jobs ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def cleanup(self, days: int = 7):
        """Remove old completed/failed jobs."""
        conn = self._get_conn()
        cutoff = time.time() - (days * 86400)
        result = conn.execute(
            "DELETE FROM jobs WHERE status IN (?, ?) AND completed_at < ?",
            (STATUS_COMPLETE, STATUS_FAILED, cutoff)
        )
        conn.commit()
        if result.rowcount > 0:
            logger.info("Cleaned up %d old jobs", result.rowcount)
        return result.rowcount


# Singleton instance
_queue = None

def get_queue() -> PersistentQueue:
    """Get or create the singleton queue instance."""
    global _queue
    if _queue is None:
        _queue = PersistentQueue()
    return _queue

"""Azure PostgreSQL for docking results persistence.

Separate database from the main auth/user database.
Used to store completed docking results for queryability and
persistence beyond the file-based job queue.

Connection is configured via DOCKING_DATABASE_URL env var.
If unset, all operations are no-ops (file-based queue works as before).
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

DOCKING_DATABASE_URL = os.environ.get("DOCKING_DATABASE_URL", "")

_conn = None


def _get_conn():
    global _conn
    if not DOCKING_DATABASE_URL:
        return None
    if _conn is None or _conn.closed:
        try:
            import psycopg2
            _conn = psycopg2.connect(DOCKING_DATABASE_URL, sslmode="require", connect_timeout=10)
            _conn.autocommit = False
        except Exception as e:
            logger.warning("Docking DB connection failed: %s", e)
            return None
    return _conn


def close():
    global _conn
    if _conn and not _conn.closed:
        _conn.close()
    _conn = None


def init_schema():
    conn = _get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS docking_jobs (
                job_id VARCHAR(12) PRIMARY KEY,
                sequence TEXT NOT NULL,
                num_ligands INTEGER NOT NULL DEFAULT 0,
                top_n INTEGER DEFAULT 50,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                result JSONB,
                error TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS docking_results (
                id SERIAL PRIMARY KEY,
                job_id VARCHAR(12) REFERENCES docking_jobs(job_id) ON DELETE CASCADE,
                ligand_smiles TEXT,
                ligand_name VARCHAR(255),
                vina_score FLOAT,
                gnina_score FLOAT,
                pdbqt_data TEXT,
                sdf_data TEXT,
                rank INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_docking_jobs_status ON docking_jobs(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_docking_results_job_id ON docking_results(job_id)")
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        logger.warning("Docking DB init_schema failed: %s", e)
        conn.rollback()
        return False


def save_job(job_id: str, sequence: str, ligand_smiles_list: list, top_n: int = 50):
    conn = _get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO docking_jobs (job_id, sequence, num_ligands, top_n, status)
            VALUES (%s, %s, %s, %s, 'pending')
            ON CONFLICT (job_id) DO NOTHING
            """,
            (job_id, sequence, len(ligand_smiles_list), top_n),
        )
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        logger.warning("Docking DB save_job failed: %s", e)
        conn.rollback()
        return False


def complete_job(job_id: str, result: dict | None, error: str | None = None):
    conn = _get_conn()
    if not conn:
        return False
    try:
        status = "failed" if error else "completed"
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE docking_jobs
            SET status = %s, result = %s, error = %s, updated_at = NOW()
            WHERE job_id = %s
            """,
            (status, json.dumps(result) if result else None, error, job_id),
        )
        if result:
            ligands = result.get("ligands") or []
            for i, lig in enumerate(ligands):
                cur.execute(
                    """
                    INSERT INTO docking_results
                        (job_id, ligand_smiles, ligand_name, vina_score, gnina_score,
                         pdbqt_data, sdf_data, rank)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        job_id,
                        lig.get("smiles", ""),
                        lig.get("name", "")[:255] if lig.get("name") else None,
                        lig.get("vina_score"),
                        lig.get("gnina_score"),
                        lig.get("pdbqt"),
                        lig.get("sdf"),
                        i + 1,
                    ),
                )
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        logger.warning("Docking DB complete_job failed: %s", e)
        conn.rollback()
        return False


def get_job(job_id: str) -> dict | None:
    conn = _get_conn()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT job_id, status, result, error, created_at, updated_at FROM docking_jobs WHERE job_id = %s",
            (job_id,),
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            return None
        job = {
            "job_id": row[0],
            "status": row[1],
            "result": row[2] if row[2] else {},
            "error": row[3],
            "created_at": row[4].isoformat() if row[4] else None,
            "updated_at": row[5].isoformat() if row[5] else None,
        }
        cur.execute(
            "SELECT ligand_smiles, ligand_name, vina_score, gnina_score, sdf_data, rank "
            "FROM docking_results WHERE job_id = %s ORDER BY rank",
            (job_id,),
        )
        ligands = []
        for r in cur.fetchall():
            ligands.append({
                "smiles": r[0],
                "name": r[1],
                "vina_score": r[2],
                "gnina_score": r[3],
                "sdf": r[4],
                "rank": r[5],
            })
        job["ligands"] = ligands
        cur.close()
        return job
    except Exception as e:
        logger.warning("Docking DB get_job failed: %s", e)
        return None

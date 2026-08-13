-- 0116: Merge docking tables into main database
-- Run on production PostgreSQL (EC2):
--   psql -U vigyanpilot -d vigyanpilot_db -f deploy/migrations/0116_merge_docking_db.sql

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
);

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
);

CREATE INDEX IF NOT EXISTS idx_docking_jobs_status ON docking_jobs(status);
CREATE INDEX IF NOT EXISTS idx_docking_results_job_id ON docking_results(job_id);

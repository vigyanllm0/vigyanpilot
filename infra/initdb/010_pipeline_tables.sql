-- =============================================================
-- 010: Pipeline Engine Tables
-- VigyanLLM 22-Step Pipeline: jobs, results, and sequence cache
-- =============================================================

-- -----------------------------------------------------------
-- 1. PIPELINE JOBS
-- Tracks each pipeline execution from submission to completion
-- -----------------------------------------------------------

CREATE TABLE IF NOT EXISTS pipeline_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         BIGINT NOT NULL REFERENCES users(id),
    status          VARCHAR(32) DEFAULT 'queued',       -- queued|running|step_N|completed|failed
    current_step    INTEGER DEFAULT 0,
    total_steps     INTEGER DEFAULT 15,
    input_params    JSONB NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    error_log       TEXT
);

-- -----------------------------------------------------------
-- 2. PIPELINE RESULTS
-- Per-step output for each pipeline job
-- -----------------------------------------------------------

CREATE TABLE IF NOT EXISTS pipeline_results (
    id              BIGSERIAL PRIMARY KEY,
    job_id          UUID REFERENCES pipeline_jobs(id) ON DELETE CASCADE,
    step_number     INTEGER NOT NULL,
    step_name       VARCHAR(128) NOT NULL,
    status          VARCHAR(16) DEFAULT 'pending',      -- pending|passed|failed|skipped
    input_data      JSONB,
    output_data     JSONB,
    duration_ms     INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- -----------------------------------------------------------
-- 3. SEQUENCE CACHE
-- Caches sequences from external sources with 7-day TTL
-- -----------------------------------------------------------

CREATE TABLE IF NOT EXISTS sequence_cache (
    id              BIGSERIAL PRIMARY KEY,
    source          VARCHAR(32) NOT NULL,               -- ncbi|ncbi_virus|ensembl|ensembl_region|ena|ddbj
    query_key       VARCHAR(512) NOT NULL,              -- accession or coordinate string
    sequence        TEXT NOT NULL,
    metadata        JSONB,
    fetched_at      TIMESTAMPTZ DEFAULT NOW(),
    expires_at      TIMESTAMPTZ DEFAULT NOW() + INTERVAL '7 days',
    UNIQUE(source, query_key)
);

-- -----------------------------------------------------------
-- INDEXES
-- -----------------------------------------------------------

-- pipeline_jobs: lookup by user and status for dashboard queries
CREATE INDEX idx_pipeline_jobs_user_id ON pipeline_jobs(user_id);
CREATE INDEX idx_pipeline_jobs_status ON pipeline_jobs(status);
CREATE INDEX idx_pipeline_jobs_created_at ON pipeline_jobs(created_at DESC);

-- pipeline_results: lookup by job and step ordering
CREATE INDEX idx_pipeline_results_job_id ON pipeline_results(job_id);
CREATE INDEX idx_pipeline_results_job_step ON pipeline_results(job_id, step_number);

-- sequence_cache: fast lookups by source + key, and expiration cleanup
CREATE INDEX idx_sequence_cache_source_key ON sequence_cache(source, query_key);
CREATE INDEX idx_sequence_cache_expires_at ON sequence_cache(expires_at);

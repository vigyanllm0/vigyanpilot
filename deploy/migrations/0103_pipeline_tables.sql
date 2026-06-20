CREATE TABLE IF NOT EXISTS pipeline_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL REFERENCES users(id),
    status VARCHAR(32) DEFAULT 'queued',
    current_step INTEGER DEFAULT 0,
    total_steps INTEGER DEFAULT 22,
    mode VARCHAR(16) DEFAULT 'full',
    phase VARCHAR(1),
    compliance_status VARCHAR(32),
    input_params JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_log TEXT
);

CREATE INDEX IF NOT EXISTS idx_pipeline_jobs_user_id ON pipeline_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_jobs_status ON pipeline_jobs(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_jobs_created_at ON pipeline_jobs(created_at DESC);

CREATE TABLE IF NOT EXISTS pipeline_results (
    id BIGSERIAL PRIMARY KEY,
    job_id UUID REFERENCES pipeline_jobs(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    step_name VARCHAR(128) NOT NULL,
    status VARCHAR(16) DEFAULT 'pending',
    input_data JSONB,
    output_data JSONB,
    duration_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_results_job_id ON pipeline_results(job_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_results_job_step ON pipeline_results(job_id, step_number);

CREATE TABLE IF NOT EXISTS compliance_screening (
    id BIGSERIAL PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES pipeline_jobs(id) ON DELETE CASCADE,
    status VARCHAR(32) NOT NULL,
    sequences_screened INTEGER NOT NULL DEFAULT 0,
    matched_organism VARCHAR(256),
    matched_gene VARCHAR(256),
    percent_identity NUMERIC(5,2),
    alignment_length INTEGER,
    screened_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS order_payloads (
    id BIGSERIAL PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES pipeline_jobs(id) ON DELETE CASCADE,
    vendor VARCHAR(16) NOT NULL,
    payload JSONB NOT NULL,
    order_id VARCHAR(64) NOT NULL,
    oligo_count INTEGER NOT NULL,
    scale VARCHAR(16) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

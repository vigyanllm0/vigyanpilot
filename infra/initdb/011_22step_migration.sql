-- =============================================================
-- 011: 22-Step Pipeline Migration
-- Upgrades pipeline_jobs for the VigyanLLM 22-step engine
-- =============================================================

-- -----------------------------------------------------------
-- 1. ALTER pipeline_jobs for 22-step pipeline support
-- -----------------------------------------------------------

-- Update total_steps default from 15 to 22
ALTER TABLE pipeline_jobs ALTER COLUMN total_steps SET DEFAULT 22;

-- Add mode column: determines full or express pipeline execution
ALTER TABLE pipeline_jobs ADD COLUMN IF NOT EXISTS mode VARCHAR(16) DEFAULT 'full';

-- Add phase column: tracks current phase (A–E) during execution
ALTER TABLE pipeline_jobs ADD COLUMN IF NOT EXISTS phase VARCHAR(1);

-- Add compliance_status column: IGSC biosecurity screening result
ALTER TABLE pipeline_jobs ADD COLUMN IF NOT EXISTS compliance_status VARCHAR(32);

-- -----------------------------------------------------------
-- 2. COMPLIANCE SCREENING
-- Logs IGSC biosecurity screening results per pipeline job
-- -----------------------------------------------------------

CREATE TABLE IF NOT EXISTS compliance_screening (
    id                  BIGSERIAL PRIMARY KEY,
    job_id              UUID NOT NULL REFERENCES pipeline_jobs(id) ON DELETE CASCADE,
    status              VARCHAR(32) NOT NULL,
    sequences_screened  INTEGER NOT NULL DEFAULT 0,
    matched_organism    VARCHAR(256),
    matched_gene        VARCHAR(256),
    percent_identity    NUMERIC(5,2),
    alignment_length    INTEGER,
    screened_at         TIMESTAMPTZ DEFAULT NOW()
);

-- -----------------------------------------------------------
-- 3. ORDER PAYLOADS
-- Stores serialized IDT/Twist vendor order payloads
-- -----------------------------------------------------------

CREATE TABLE IF NOT EXISTS order_payloads (
    id              BIGSERIAL PRIMARY KEY,
    job_id          UUID NOT NULL REFERENCES pipeline_jobs(id) ON DELETE CASCADE,
    vendor          VARCHAR(16) NOT NULL,
    payload         JSONB NOT NULL,
    order_id        VARCHAR(64) NOT NULL,
    oligo_count     INTEGER NOT NULL,
    scale           VARCHAR(16) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- -----------------------------------------------------------
-- 4. SUBSCRIPTION QUOTA EXTENSIONS
-- Adds quota tracking and tier columns to subscriptions
-- -----------------------------------------------------------

ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS monthly_quota INTEGER DEFAULT 0;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS quota_used INTEGER DEFAULT 0;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS tier VARCHAR(32) DEFAULT 'free';

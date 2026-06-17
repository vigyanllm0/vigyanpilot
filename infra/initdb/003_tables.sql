-- =============================================================
-- 003: Core Tables
-- =============================================================

-- -----------------------------------------------------------
-- 1. USERS & SECURITY AUTHENTICATION
-- -----------------------------------------------------------

CREATE TABLE users (
    id              BIGSERIAL PRIMARY KEY,
    email           VARCHAR(320) NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    full_name       VARCHAR(256),
    organization    VARCHAR(256),
    role            user_role NOT NULL DEFAULT 'user',
    status          user_status NOT NULL DEFAULT 'active',
    failed_login_count INTEGER NOT NULL DEFAULT 0,
    locked_until    TIMESTAMPTZ,
    last_active_at  TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE login_logs (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    logged_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_address          INET NOT NULL,
    user_agent          TEXT,
    session_token_hash  TEXT,
    result              login_result NOT NULL,
    failure_reason      TEXT
);

-- -----------------------------------------------------------
-- 2. MULTI-AGENT OPERATION LOGS
-- -----------------------------------------------------------

CREATE TABLE agent_work_logs (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT REFERENCES users(id) ON DELETE SET NULL,
    agent_name          VARCHAR(128) NOT NULL,
    target_sequence     TEXT,
    sequence_length     INTEGER CHECK (sequence_length IS NULL OR sequence_length >= 0),
    parameters          JSONB NOT NULL DEFAULT '{}',
    execution_ms        INTEGER CHECK (execution_ms IS NULL OR execution_ms >= 0),
    status              task_status NOT NULL DEFAULT 'queued',
    error_log           TEXT,
    -- Link to cost tracking (filled after execution completes)
    cost_entry_id       BIGINT,
    queued_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ
);

-- -----------------------------------------------------------
-- 3. PAYMENT GATEWAY DATA
-- -----------------------------------------------------------

CREATE TABLE payments (
    id                      BIGSERIAL PRIMARY KEY,
    user_id                 BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    gateway_order_id        VARCHAR(128) UNIQUE,
    gateway_payment_id      VARCHAR(128) UNIQUE,
    gateway_signature       TEXT,
    amount                  NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    currency                CHAR(3) NOT NULL DEFAULT 'INR',
    status                  payment_status NOT NULL DEFAULT 'initiated',
    product_type            VARCHAR(64),          -- 'subscription', 'nano_pack', 'growth_pack', etc.
    tokens_purchased        INTEGER DEFAULT 0,    -- How many tokens this payment bought
    initiated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    authorized_at           TIMESTAMPTZ,
    captured_at             TIMESTAMPTZ,
    failed_at               TIMESTAMPTZ,
    refunded_at             TIMESTAMPTZ,
    metadata                JSONB DEFAULT '{}'
);

CREATE TABLE gateway_webhooks (
    id                  BIGSERIAL PRIMARY KEY,
    payment_id          BIGINT REFERENCES payments(id) ON DELETE SET NULL,
    raw_payload         JSONB NOT NULL,
    event_type          VARCHAR(128) NOT NULL,
    validation_status   webhook_trust NOT NULL DEFAULT 'untrusted',
    http_headers        JSONB,
    processed_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processing_notes    TEXT
);

-- -----------------------------------------------------------
-- 4. SYSTEM EVENT LOG
-- -----------------------------------------------------------

CREATE TABLE system_events (
    id              BIGSERIAL PRIMARY KEY,
    severity        event_severity NOT NULL,
    module          VARCHAR(128) NOT NULL,
    message         TEXT NOT NULL,
    context         JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------
-- 5. COMPLETE COMPANY COSTING & FINANCIAL LEDGER
-- Tracks BOTH sides: what it costs us AND what users paid us.
-- Every operation by ANY user (admin or regular) is logged here.
-- -----------------------------------------------------------

-- The unified cost ledger: every resource consumption event
CREATE TABLE cost_ledger (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    
    -- What triggered this cost
    trigger_type        VARCHAR(64) NOT NULL,    -- 'primer_design', 'sequence_fetch', 'llm_query', 'manual_analysis'
    agent_work_log_id   BIGINT,                  -- Link to the specific job (nullable for non-agent costs)
    
    -- Resource consumption metrics (what was actually used)
    cpu_seconds         NUMERIC(10, 4) DEFAULT 0,
    memory_mb_seconds   NUMERIC(12, 2) DEFAULT 0,  -- MB * seconds of RAM usage
    gpu_seconds         NUMERIC(10, 4) DEFAULT 0,
    llm_input_tokens    INTEGER DEFAULT 0,
    llm_output_tokens   INTEGER DEFAULT 0,
    api_calls_external  INTEGER DEFAULT 0,       -- NCBI, Ensembl, etc.
    primers_generated   INTEGER DEFAULT 0,
    storage_mb_used     NUMERIC(8, 2) DEFAULT 0,
    
    -- Cost calculation (what E2E/infra charges us — our COGS)
    infra_cost_inr      NUMERIC(10, 4) NOT NULL DEFAULT 0,  -- Raw infrastructure cost
    llm_cost_inr        NUMERIC(10, 4) NOT NULL DEFAULT 0,  -- LLM API costs (OpenAI/Anthropic/etc)
    external_api_cost_inr NUMERIC(10, 4) NOT NULL DEFAULT 0, -- Third-party API costs
    total_cogs_inr      NUMERIC(10, 4) NOT NULL DEFAULT 0,  -- Total cost of goods sold for this operation
    
    -- Revenue attribution (what the user paid us for this operation)
    revenue_inr         NUMERIC(10, 4) NOT NULL DEFAULT 0,  -- Revenue earned from this operation
    is_billable         BOOLEAN NOT NULL DEFAULT TRUE,       -- FALSE = admin/internal/free-tier
    billing_method      VARCHAR(32) NOT NULL DEFAULT 'token', -- 'token', 'subscription_included', 'admin_free', 'promotional'
    tokens_consumed     INTEGER NOT NULL DEFAULT 0,           -- How many user tokens were deducted
    
    -- Margin (auto-calculated by trigger)
    gross_margin_inr    NUMERIC(10, 4) NOT NULL DEFAULT 0,   -- revenue - total_cogs
    margin_percent      NUMERIC(6, 2) NOT NULL DEFAULT 0,    -- (margin / revenue) * 100
    
    description         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Revenue ledger: tracks all incoming money (linked to payments)
CREATE TABLE revenue_ledger (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    payment_id          BIGINT REFERENCES payments(id) ON DELETE SET NULL,
    
    -- Revenue details
    revenue_type        VARCHAR(64) NOT NULL,    -- 'subscription', 'token_pack', 'custom_topup'
    product_id          VARCHAR(64),             -- 'base_subscription', 'nano_pack', etc.
    gross_amount_inr    NUMERIC(12, 2) NOT NULL, -- Total amount paid by user
    gateway_fee_inr     NUMERIC(10, 4) DEFAULT 0, -- Razorpay/PayU processing fee (typically 2%)
    gst_amount_inr      NUMERIC(10, 4) DEFAULT 0, -- GST component (18% on gateway fee)
    net_revenue_inr     NUMERIC(12, 4) NOT NULL,  -- What we actually receive after fees
    
    -- Token economics
    tokens_credited     INTEGER DEFAULT 0,
    cost_per_token_to_user NUMERIC(8, 4) DEFAULT 0, -- What user effectively paid per token
    
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Fixed/recurring company expenses (server bills, salaries, SaaS tools)
CREATE TABLE fixed_expenses (
    id                  BIGSERIAL PRIMARY KEY,
    expense_category    VARCHAR(64) NOT NULL,    -- 'infrastructure', 'saas_tools', 'domain_ssl', 'salary', 'marketing'
    vendor              VARCHAR(128) NOT NULL,   -- 'E2E Networks', 'OpenAI', 'Razorpay', 'GoDaddy', etc.
    description         TEXT NOT NULL,
    amount_inr          NUMERIC(12, 2) NOT NULL CHECK (amount_inr > 0),
    frequency           VARCHAR(32) NOT NULL DEFAULT 'monthly', -- 'monthly', 'yearly', 'one_time'
    billing_period_start TIMESTAMPTZ,
    billing_period_end  TIMESTAMPTZ,
    is_recurring        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Infrastructure rate card (configurable wholesale rates for cost calculation)
CREATE TABLE infra_rate_card (
    id                  BIGSERIAL PRIMARY KEY,
    resource_type       VARCHAR(64) NOT NULL UNIQUE,  -- 'cpu_second', 'memory_mb_second', 'gpu_second', 'llm_input_token', etc.
    rate_inr            NUMERIC(12, 8) NOT NULL,      -- Cost per unit in INR
    vendor              VARCHAR(64),                   -- 'E2E Networks', 'OpenAI', etc.
    notes               TEXT,
    effective_from      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    effective_until     TIMESTAMPTZ,                   -- NULL = currently active
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Token balance tracking per user
CREATE TABLE token_balances (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE RESTRICT,
    balance             INTEGER NOT NULL DEFAULT 0 CHECK (balance >= 0),
    total_purchased     INTEGER NOT NULL DEFAULT 0,
    total_consumed      INTEGER NOT NULL DEFAULT 0,
    total_expired       INTEGER NOT NULL DEFAULT 0,
    lifetime_revenue_inr NUMERIC(12, 2) NOT NULL DEFAULT 0, -- Total money this user has paid us
    lifetime_cogs_inr   NUMERIC(12, 4) NOT NULL DEFAULT 0,  -- Total cost this user has generated
    last_credited_at    TIMESTAMPTZ,
    last_consumed_at    TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Subscription tracking
CREATE TABLE subscriptions (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE RESTRICT,
    is_active           BOOLEAN NOT NULL DEFAULT FALSE,
    plan_type           VARCHAR(64) NOT NULL DEFAULT 'base', -- 'base', 'pro', 'enterprise' (future)
    started_at          TIMESTAMPTZ,
    expires_at          TIMESTAMPTZ,
    last_renewed_at     TIMESTAMPTZ,
    auto_renew          BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------
-- AUDIT TRAIL (immutable record of sensitive changes)
-- -----------------------------------------------------------

CREATE TABLE audit_trail (
    id              BIGSERIAL PRIMARY KEY,
    table_name      VARCHAR(64) NOT NULL,
    record_id       BIGINT NOT NULL,
    action          VARCHAR(10) NOT NULL,
    old_values      JSONB,
    new_values      JSONB,
    changed_by      TEXT,
    changed_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_address      INET
);

-- -----------------------------------------------------------
-- Add foreign key from agent_work_logs to cost_ledger
-- (deferred because cost_ledger is created after agent_work_logs)
-- -----------------------------------------------------------
ALTER TABLE agent_work_logs
    ADD CONSTRAINT fk_agent_cost_entry
    FOREIGN KEY (cost_entry_id) REFERENCES cost_ledger(id) ON DELETE SET NULL;

-- =============================================================
-- 0105: Complete remaining tables and views
-- Covers all tables referenced by Python code that were missing
-- =============================================================

-- -----------------------------------------------------------
-- 1. PAYMENT TABLES
-- -----------------------------------------------------------

CREATE TABLE IF NOT EXISTS payments (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    gateway_order_id VARCHAR(128) UNIQUE,
    gateway_payment_id VARCHAR(128) UNIQUE,
    gateway_signature TEXT,
    amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    currency CHAR(3) NOT NULL DEFAULT 'INR',
    status VARCHAR(32) NOT NULL DEFAULT 'initiated',
    product_type VARCHAR(64),
    tokens_purchased INTEGER DEFAULT 0,
    initiated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    authorized_at TIMESTAMPTZ,
    captured_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    refunded_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_gateway_order ON payments(gateway_order_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_initiated_at ON payments(initiated_at DESC);

CREATE TABLE IF NOT EXISTS gateway_webhooks (
    id BIGSERIAL PRIMARY KEY,
    payment_id BIGINT REFERENCES payments(id) ON DELETE SET NULL,
    raw_payload JSONB NOT NULL,
    event_type VARCHAR(128) NOT NULL,
    validation_status VARCHAR(32) NOT NULL DEFAULT 'untrusted',
    http_headers JSONB,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processing_notes TEXT
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE RESTRICT,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    plan_id VARCHAR(64),
    plan_type VARCHAR(64) NOT NULL DEFAULT 'base',
    monthly_quota INTEGER DEFAULT 0,
    quota_used INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    last_renewed_at TIMESTAMPTZ,
    quota_reset_at TIMESTAMPTZ,
    max_seats INTEGER DEFAULT 1,
    auto_renew BOOLEAN NOT NULL DEFAULT FALSE,
    razorpay_subscription_id VARCHAR(128),
    tier VARCHAR(32) DEFAULT 'free',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cost_ledger (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    trigger_type VARCHAR(64) NOT NULL,
    agent_work_log_id BIGINT,
    cpu_seconds NUMERIC(10,4) DEFAULT 0,
    memory_mb_seconds NUMERIC(12,2) DEFAULT 0,
    gpu_seconds NUMERIC(10,4) DEFAULT 0,
    llm_input_tokens INTEGER DEFAULT 0,
    llm_output_tokens INTEGER DEFAULT 0,
    api_calls_external INTEGER DEFAULT 0,
    primers_generated INTEGER DEFAULT 0,
    storage_mb_used NUMERIC(8,2) DEFAULT 0,
    infra_cost_inr NUMERIC(10,4) NOT NULL DEFAULT 0,
    llm_cost_inr NUMERIC(10,4) NOT NULL DEFAULT 0,
    external_api_cost_inr NUMERIC(10,4) NOT NULL DEFAULT 0,
    total_cogs_inr NUMERIC(10,4) NOT NULL DEFAULT 0,
    revenue_inr NUMERIC(10,4) NOT NULL DEFAULT 0,
    is_billable BOOLEAN NOT NULL DEFAULT TRUE,
    billing_method VARCHAR(32) NOT NULL DEFAULT 'token',
    tokens_consumed INTEGER NOT NULL DEFAULT 0,
    gross_margin_inr NUMERIC(10,4) NOT NULL DEFAULT 0,
    margin_percent NUMERIC(6,2) NOT NULL DEFAULT 0,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cost_user_id ON cost_ledger(user_id);
CREATE INDEX IF NOT EXISTS idx_cost_created_at ON cost_ledger(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cost_trigger_type ON cost_ledger(trigger_type);

CREATE TABLE IF NOT EXISTS revenue_ledger (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    payment_id BIGINT REFERENCES payments(id) ON DELETE SET NULL,
    revenue_type VARCHAR(64) NOT NULL,
    product_id VARCHAR(64),
    gross_amount_inr NUMERIC(12,2) NOT NULL,
    gateway_fee_inr NUMERIC(10,4) DEFAULT 0,
    gst_amount_inr NUMERIC(10,4) DEFAULT 0,
    net_revenue_inr NUMERIC(12,4) NOT NULL,
    tokens_credited INTEGER DEFAULT 0,
    cost_per_token_to_user NUMERIC(8,4) DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_revenue_user_id ON revenue_ledger(user_id);
CREATE INDEX IF NOT EXISTS idx_revenue_payment_id ON revenue_ledger(payment_id);
CREATE INDEX IF NOT EXISTS idx_revenue_type ON revenue_ledger(revenue_type);

-- -----------------------------------------------------------
-- 2. COST & INFRA TABLES
-- -----------------------------------------------------------

CREATE TABLE IF NOT EXISTS fixed_expenses (
    id BIGSERIAL PRIMARY KEY,
    expense_category VARCHAR(64) NOT NULL,
    vendor VARCHAR(128) NOT NULL,
    description TEXT NOT NULL,
    amount_inr NUMERIC(12,2) NOT NULL CHECK (amount_inr > 0),
    frequency VARCHAR(32) NOT NULL DEFAULT 'monthly',
    billing_period_start TIMESTAMPTZ,
    billing_period_end TIMESTAMPTZ,
    is_recurring BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS infra_rate_card (
    id BIGSERIAL PRIMARY KEY,
    resource_type VARCHAR(64) NOT NULL UNIQUE,
    rate_inr NUMERIC(12,8) NOT NULL,
    vendor VARCHAR(64),
    notes TEXT,
    effective_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    effective_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_work_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    agent_name VARCHAR(128) NOT NULL,
    target_sequence TEXT,
    sequence_length INTEGER CHECK (sequence_length IS NULL OR sequence_length >= 0),
    parameters JSONB NOT NULL DEFAULT '{}',
    execution_ms INTEGER CHECK (execution_ms IS NULL OR execution_ms >= 0),
    status VARCHAR(32) NOT NULL DEFAULT 'queued',
    error_log TEXT,
    cost_entry_id BIGINT,
    queued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_agent_logs_user_id ON agent_work_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_status ON agent_work_logs(status);
CREATE INDEX IF NOT EXISTS idx_agent_logs_queued_at ON agent_work_logs(queued_at DESC);

-- -----------------------------------------------------------
-- 3. USER & AUTH TABLES
-- -----------------------------------------------------------

CREATE TABLE IF NOT EXISTS password_resets (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(256) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_password_resets_user_id ON password_resets(user_id);
CREATE INDEX IF NOT EXISTS idx_password_resets_token ON password_resets(token);

CREATE TABLE IF NOT EXISTS token_blacklist (
    id BIGSERIAL PRIMARY KEY,
    token_hash VARCHAR(128) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS usage_log (
    id BIGSERIAL PRIMARY KEY,
    user_email VARCHAR(320),
    action VARCHAR(128) NOT NULL,
    details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usage_log_user_email ON usage_log(user_email);
CREATE INDEX IF NOT EXISTS idx_usage_log_created_at ON usage_log(created_at DESC);

CREATE TABLE IF NOT EXISTS audit_trail (
    id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(64) NOT NULL,
    record_id BIGINT NOT NULL,
    action VARCHAR(10) NOT NULL,
    old_values JSONB,
    new_values JSONB,
    changed_by TEXT,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_address INET
);

CREATE INDEX IF NOT EXISTS idx_audit_table_record ON audit_trail(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_audit_changed_at ON audit_trail(changed_at DESC);

-- -----------------------------------------------------------
-- 4. REPORTS & REFERRAL TABLES
-- -----------------------------------------------------------

CREATE TABLE IF NOT EXISTS user_reports (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID REFERENCES pipeline_jobs(id) ON DELETE SET NULL,
    title VARCHAR(256) NOT NULL,
    forward_seq TEXT,
    reverse_seq TEXT,
    forward_primer TEXT,
    reverse_primer TEXT,
    full_result JSONB,
    format VARCHAR(16) DEFAULT 'json',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_reports_user_id ON user_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_user_reports_created_at ON user_reports(created_at DESC);

CREATE TABLE IF NOT EXISTS academic_claims (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    institution VARCHAR(256),
    department VARCHAR(256),
    research_area VARCHAR(256),
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    tokens_granted INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_academic_claims_user_id ON academic_claims(user_id);

CREATE TABLE IF NOT EXISTS referrals (
    id BIGSERIAL PRIMARY KEY,
    referrer_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    referred_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    referral_code VARCHAR(64) NOT NULL UNIQUE,
    referred_email VARCHAR(320),
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    tokens_awarded INTEGER DEFAULT 0,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_referrals_referrer_id ON referrals(referrer_id);
CREATE INDEX IF NOT EXISTS idx_referrals_referral_code ON referrals(referral_code);

CREATE TABLE IF NOT EXISTS feedback_submissions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    email VARCHAR(320),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    message TEXT NOT NULL,
    context TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------
-- 5. HELPER VIEWS (for admin dashboard)
-- -----------------------------------------------------------

CREATE OR REPLACE VIEW v_user_profitability AS
SELECT u.id, u.email, u.full_name, u.created_at,
       COALESCE(tb.lifetime_revenue_inr, 0) AS lifetime_revenue_inr,
       COALESCE(tb.lifetime_cogs_inr, 0) AS lifetime_cogs_inr,
       CASE WHEN COALESCE(tb.lifetime_cogs_inr, 0) > 0
            THEN ((COALESCE(tb.lifetime_revenue_inr, 0) - COALESCE(tb.lifetime_cogs_inr, 0)) / tb.lifetime_cogs_inr) * 100
            ELSE 0 END AS margin_percent,
       COALESCE(tb.balance, 0) AS token_balance,
       CASE WHEN s.is_active THEN s.plan_type ELSE 'none' END AS subscription
FROM users u
LEFT JOIN token_balances tb ON tb.user_id = u.id
LEFT JOIN subscriptions s ON s.user_id = u.id;

CREATE OR REPLACE VIEW v_monthly_pnl AS
SELECT month,
       COALESCE(SUM(revenue), 0) AS total_revenue,
       COALESCE(SUM(variable_cogs), 0) AS total_variable_cogs,
       COALESCE(SUM(fixed_costs), 0) AS total_fixed_costs,
       COALESCE(SUM(revenue), 0) - COALESCE(SUM(variable_cogs), 0) - COALESCE(SUM(fixed_costs), 0) AS net_profit
FROM (
    SELECT date_trunc('month', r.created_at) AS month, r.net_revenue_inr AS revenue, 0::numeric AS variable_cogs, 0::numeric AS fixed_costs
    FROM revenue_ledger r
    UNION ALL
    SELECT date_trunc('month', c.created_at) AS month, 0::numeric, c.total_cogs_inr, 0::numeric
    FROM cost_ledger c
    UNION ALL
    SELECT date_trunc('month', f.created_at) AS month, 0::numeric, 0::numeric, f.amount_inr
    FROM fixed_expenses f
) combined
GROUP BY month ORDER BY month DESC;

CREATE OR REPLACE VIEW v_roi_dashboard AS
SELECT date_trunc('month', created_at) AS month,
       COALESCE(SUM(net_revenue_inr), 0) AS revenue,
       COALESCE(SUM(tokens_credited), 0) AS tokens_sold
FROM revenue_ledger GROUP BY month ORDER BY month DESC;

CREATE OR REPLACE VIEW v_token_economics AS
SELECT 'lifetime' AS period,
       COALESCE(SUM(total_purchased), 0) AS total_purchased,
       COALESCE(SUM(total_consumed), 0) AS total_consumed,
       COALESCE(AVG(lifetime_revenue_inr), 0) AS avg_revenue_per_user,
       COALESCE(AVG(lifetime_cogs_inr), 0) AS avg_cogs_per_user
FROM token_balances;

CREATE OR REPLACE VIEW v_admin_cost_breakdown AS
SELECT u.email, c.trigger_type,
       SUM(c.total_cogs_inr) AS total_cost,
       COUNT(*) AS occurrences
FROM cost_ledger c JOIN users u ON u.id = c.user_id
WHERE c.is_billable = FALSE
GROUP BY u.email, c.trigger_type;

-- -----------------------------------------------------------
-- 6. HELPER FUNCTION: record_operation_cost
-- -----------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_record_operation_cost(
    p_user_id BIGINT,
    p_trigger_type VARCHAR,
    p_cpu_seconds NUMERIC DEFAULT 0,
    p_memory_mb_seconds NUMERIC DEFAULT 0,
    p_gpu_seconds NUMERIC DEFAULT 0,
    p_llm_input_tokens INTEGER DEFAULT 0,
    p_llm_output_tokens INTEGER DEFAULT 0,
    p_api_calls_external INTEGER DEFAULT 0,
    p_primers_generated INTEGER DEFAULT 0
) RETURNS BIGINT AS $$
DECLARE
    v_cost_id BIGINT;
    v_cpu_rate NUMERIC(12,8) := 0.0001;
    v_mem_rate NUMERIC(12,8) := 0.00001;
    v_gpu_rate NUMERIC(12,8) := 0.001;
    v_llm_input_rate NUMERIC(12,8) := 0.000001;
    v_llm_output_rate NUMERIC(12,8) := 0.000002;
    v_api_rate NUMERIC(12,8) := 0.001;
BEGIN
    INSERT INTO cost_ledger (
        user_id, trigger_type,
        cpu_seconds, memory_mb_seconds, gpu_seconds,
        llm_input_tokens, llm_output_tokens,
        api_calls_external, primers_generated,
        infra_cost_inr,
        llm_cost_inr,
        external_api_cost_inr,
        total_cogs_inr
    ) VALUES (
        p_user_id, p_trigger_type,
        p_cpu_seconds, p_memory_mb_seconds, p_gpu_seconds,
        p_llm_input_tokens, p_llm_output_tokens,
        p_api_calls_external, p_primers_generated,
        p_cpu_seconds * v_cpu_rate + p_memory_mb_seconds * v_mem_rate + p_gpu_seconds * v_gpu_rate,
        p_llm_input_tokens * v_llm_input_rate + p_llm_output_tokens * v_llm_output_rate,
        p_api_calls_external * v_api_rate,
        0
    ) RETURNING id INTO v_cost_id;
    RETURN v_cost_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_user_financial_summary(p_user_id BIGINT)
RETURNS TABLE (
    total_revenue_inr NUMERIC,
    total_cogs_inr NUMERIC,
    total_margin_inr NUMERIC,
    margin_percent NUMERIC,
    token_balance INTEGER,
    total_purchased INTEGER,
    total_consumed INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT COALESCE(tb.lifetime_revenue_inr, 0) AS total_revenue_inr,
           COALESCE(tb.lifetime_cogs_inr, 0) AS total_cogs_inr,
           COALESCE(tb.lifetime_revenue_inr, 0) - COALESCE(tb.lifetime_cogs_inr, 0) AS total_margin_inr,
           CASE WHEN COALESCE(tb.lifetime_cogs_inr, 0) > 0
                THEN ((COALESCE(tb.lifetime_revenue_inr, 0) - COALESCE(tb.lifetime_cogs_inr, 0)) / tb.lifetime_cogs_inr) * 100
                ELSE 0 END AS margin_percent,
           COALESCE(tb.balance, 0) AS token_balance,
           COALESCE(tb.total_purchased, 0) AS total_purchased,
           COALESCE(tb.total_consumed, 0) AS total_consumed
    FROM token_balances tb WHERE tb.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

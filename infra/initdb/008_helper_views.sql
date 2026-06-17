-- =============================================================
-- 008: Financial Views, Analytics & Utility Functions
-- =============================================================

-- -----------------------------------------------------------
-- VIEW: Per-user profitability (Lifetime Value vs Cost to Serve)
-- Use this to identify your most/least profitable users
-- -----------------------------------------------------------

CREATE VIEW v_user_profitability AS
SELECT
    u.id AS user_id,
    u.email,
    u.role,
    u.organization,
    u.created_at AS user_since,
    
    -- Revenue side
    COALESCE(tb.lifetime_revenue_inr, 0) AS lifetime_revenue,
    COALESCE(tb.total_purchased, 0) AS tokens_purchased,
    COALESCE(tb.total_consumed, 0) AS tokens_consumed,
    COALESCE(tb.balance, 0) AS tokens_remaining,
    
    -- Cost side
    COALESCE(tb.lifetime_cogs_inr, 0) AS lifetime_cogs,
    
    -- Margin
    COALESCE(tb.lifetime_revenue_inr, 0) - COALESCE(tb.lifetime_cogs_inr, 0) AS lifetime_profit,
    CASE
        WHEN COALESCE(tb.lifetime_revenue_inr, 0) > 0
        THEN ((tb.lifetime_revenue_inr - tb.lifetime_cogs_inr) / tb.lifetime_revenue_inr * 100)::NUMERIC(6,2)
        ELSE -100.00
    END AS margin_percent,
    
    -- Activity
    COALESCE(tb.total_consumed, 0) AS total_operations,
    u.last_active_at,
    
    -- Subscription
    s.is_active AS has_active_subscription,
    s.expires_at AS subscription_expires
    
FROM users u
LEFT JOIN token_balances tb ON tb.user_id = u.id
LEFT JOIN subscriptions s ON s.user_id = u.id
ORDER BY lifetime_profit DESC;


-- -----------------------------------------------------------
-- VIEW: Monthly P&L (Profit & Loss) Statement
-- -----------------------------------------------------------

CREATE VIEW v_monthly_pnl AS
WITH monthly_revenue AS (
    SELECT
        DATE_TRUNC('month', created_at) AS month,
        SUM(gross_amount_inr) AS gross_revenue,
        SUM(gateway_fee_inr) AS total_gateway_fees,
        SUM(gst_amount_inr) AS total_gst_on_fees,
        SUM(net_revenue_inr) AS net_revenue,
        COUNT(*) AS transaction_count,
        SUM(tokens_credited) AS tokens_sold
    FROM revenue_ledger
    GROUP BY DATE_TRUNC('month', created_at)
),
monthly_cogs AS (
    SELECT
        DATE_TRUNC('month', created_at) AS month,
        SUM(total_cogs_inr) AS total_cogs,
        SUM(infra_cost_inr) AS infra_costs,
        SUM(llm_cost_inr) AS llm_costs,
        SUM(external_api_cost_inr) AS external_api_costs,
        COUNT(*) AS operations_count,
        SUM(CASE WHEN is_billable THEN total_cogs_inr ELSE 0 END) AS billable_cogs,
        SUM(CASE WHEN NOT is_billable THEN total_cogs_inr ELSE 0 END) AS non_billable_cogs
    FROM cost_ledger
    GROUP BY DATE_TRUNC('month', created_at)
),
monthly_fixed AS (
    SELECT
        DATE_TRUNC('month', billing_period_start) AS month,
        SUM(amount_inr) AS fixed_expenses
    FROM fixed_expenses
    WHERE is_recurring = TRUE OR billing_period_start IS NOT NULL
    GROUP BY DATE_TRUNC('month', billing_period_start)
)
SELECT
    COALESCE(r.month, c.month, f.month) AS month,
    
    -- Revenue
    COALESCE(r.gross_revenue, 0) AS gross_revenue,
    COALESCE(r.total_gateway_fees, 0) AS gateway_fees,
    COALESCE(r.total_gst_on_fees, 0) AS gst_on_fees,
    COALESCE(r.net_revenue, 0) AS net_revenue,
    COALESCE(r.transaction_count, 0) AS transactions,
    COALESCE(r.tokens_sold, 0) AS tokens_sold,
    
    -- Variable costs (COGS)
    COALESCE(c.total_cogs, 0) AS variable_costs,
    COALESCE(c.infra_costs, 0) AS infra_costs,
    COALESCE(c.llm_costs, 0) AS llm_costs,
    COALESCE(c.external_api_costs, 0) AS api_costs,
    COALESCE(c.operations_count, 0) AS total_operations,
    COALESCE(c.billable_cogs, 0) AS billable_ops_cost,
    COALESCE(c.non_billable_cogs, 0) AS admin_internal_cost,
    
    -- Fixed costs
    COALESCE(f.fixed_expenses, 0) AS fixed_expenses,
    
    -- Margins
    COALESCE(r.net_revenue, 0) - COALESCE(c.total_cogs, 0) AS gross_profit,
    COALESCE(r.net_revenue, 0) - COALESCE(c.total_cogs, 0) - COALESCE(f.fixed_expenses, 0) AS net_profit,
    
    -- Margin percentages
    CASE WHEN COALESCE(r.net_revenue, 0) > 0
        THEN (((r.net_revenue - COALESCE(c.total_cogs, 0)) / r.net_revenue) * 100)::NUMERIC(6,2)
        ELSE 0 END AS gross_margin_pct,
    CASE WHEN COALESCE(r.net_revenue, 0) > 0
        THEN (((r.net_revenue - COALESCE(c.total_cogs, 0) - COALESCE(f.fixed_expenses, 0)) / r.net_revenue) * 100)::NUMERIC(6,2)
        ELSE 0 END AS net_margin_pct,
    
    -- Unit economics
    CASE WHEN COALESCE(r.tokens_sold, 0) > 0
        THEN (COALESCE(r.net_revenue, 0) / r.tokens_sold)::NUMERIC(8,2)
        ELSE 0 END AS avg_revenue_per_token_sold,
    CASE WHEN COALESCE(c.operations_count, 0) > 0
        THEN (COALESCE(c.total_cogs, 0) / c.operations_count)::NUMERIC(8,4)
        ELSE 0 END AS avg_cogs_per_operation

FROM monthly_revenue r
FULL OUTER JOIN monthly_cogs c ON c.month = r.month
FULL OUTER JOIN monthly_fixed f ON f.month = COALESCE(r.month, c.month)
ORDER BY month DESC;


-- -----------------------------------------------------------
-- VIEW: ROI Dashboard (Return on Investment per period)
-- -----------------------------------------------------------

CREATE VIEW v_roi_dashboard AS
WITH period_data AS (
    SELECT
        DATE_TRUNC('month', created_at) AS period,
        SUM(net_revenue_inr) AS revenue
    FROM revenue_ledger
    GROUP BY DATE_TRUNC('month', created_at)
),
period_costs AS (
    SELECT
        DATE_TRUNC('month', created_at) AS period,
        SUM(total_cogs_inr) AS variable_cost
    FROM cost_ledger
    GROUP BY DATE_TRUNC('month', created_at)
),
period_fixed AS (
    SELECT
        DATE_TRUNC('month', billing_period_start) AS period,
        SUM(amount_inr) AS fixed_cost
    FROM fixed_expenses
    GROUP BY DATE_TRUNC('month', billing_period_start)
)
SELECT
    COALESCE(r.period, c.period) AS month,
    COALESCE(r.revenue, 0) AS net_revenue,
    COALESCE(c.variable_cost, 0) + COALESCE(f.fixed_cost, 0) AS total_investment,
    COALESCE(r.revenue, 0) - COALESCE(c.variable_cost, 0) - COALESCE(f.fixed_cost, 0) AS net_return,
    CASE
        WHEN (COALESCE(c.variable_cost, 0) + COALESCE(f.fixed_cost, 0)) > 0
        THEN (
            (COALESCE(r.revenue, 0) - COALESCE(c.variable_cost, 0) - COALESCE(f.fixed_cost, 0))
            / (COALESCE(c.variable_cost, 0) + COALESCE(f.fixed_cost, 0))
            * 100
        )::NUMERIC(8,2)
        ELSE 0
    END AS roi_percent
FROM period_data r
FULL OUTER JOIN period_costs c ON c.period = r.period
FULL OUTER JOIN period_fixed f ON f.period = COALESCE(r.period, c.period)
ORDER BY month DESC;


-- -----------------------------------------------------------
-- VIEW: Admin usage breakdown (what admins cost us)
-- -----------------------------------------------------------

CREATE VIEW v_admin_cost_breakdown AS
SELECT
    u.email AS admin_email,
    DATE_TRUNC('month', cl.created_at) AS month,
    cl.trigger_type,
    COUNT(*) AS operations,
    SUM(cl.total_cogs_inr) AS total_cost_to_company,
    SUM(cl.primers_generated) AS primers_designed,
    SUM(cl.llm_input_tokens + cl.llm_output_tokens) AS total_llm_tokens,
    SUM(cl.cpu_seconds) AS total_cpu_seconds
FROM cost_ledger cl
JOIN users u ON u.id = cl.user_id
WHERE u.role = 'admin'
  AND cl.billing_method = 'admin_free'
GROUP BY u.email, DATE_TRUNC('month', cl.created_at), cl.trigger_type
ORDER BY month DESC, total_cost_to_company DESC;


-- -----------------------------------------------------------
-- VIEW: Token economics (what each token costs us vs earns)
-- -----------------------------------------------------------

CREATE VIEW v_token_economics AS
SELECT
    DATE_TRUNC('month', created_at) AS month,
    
    -- What users pay us per token (average)
    AVG(revenue_inr) FILTER (WHERE is_billable AND tokens_consumed > 0) AS avg_revenue_per_token,
    
    -- What it costs us to serve one token's worth of compute
    AVG(total_cogs_inr) FILTER (WHERE tokens_consumed > 0) AS avg_cogs_per_token,
    
    -- Margin per token
    AVG(revenue_inr - total_cogs_inr) FILTER (WHERE is_billable AND tokens_consumed > 0) AS avg_margin_per_token,
    
    -- Volume
    SUM(tokens_consumed) AS total_tokens_consumed,
    SUM(tokens_consumed) FILTER (WHERE is_billable) AS billable_tokens,
    SUM(tokens_consumed) FILTER (WHERE NOT is_billable) AS free_tokens_admin,
    
    -- Total numbers
    SUM(revenue_inr) AS total_revenue,
    SUM(total_cogs_inr) AS total_cogs
    
FROM cost_ledger
WHERE tokens_consumed > 0
GROUP BY DATE_TRUNC('month', created_at)
ORDER BY month DESC;


-- -----------------------------------------------------------
-- VIEW: Stale payments (stuck orders for debugging)
-- -----------------------------------------------------------

CREATE VIEW v_stale_payments AS
SELECT
    p.id, p.user_id, u.email,
    p.gateway_order_id, p.amount, p.currency,
    p.status, p.initiated_at,
    NOW() - p.initiated_at AS age
FROM payments p
JOIN users u ON u.id = p.user_id
WHERE p.status = 'initiated'
  AND p.initiated_at < NOW() - INTERVAL '30 minutes';


-- -----------------------------------------------------------
-- VIEW: Failed/untrusted webhooks (last 24h)
-- -----------------------------------------------------------

CREATE VIEW v_failed_webhooks_24h AS
SELECT
    gw.id, gw.event_type,
    gw.raw_payload->>'order_id' AS order_id,
    gw.validation_status, gw.processing_notes, gw.processed_at
FROM gateway_webhooks gw
WHERE gw.validation_status = 'untrusted'
  AND gw.processed_at > NOW() - INTERVAL '24 hours'
ORDER BY gw.processed_at DESC;


-- -----------------------------------------------------------
-- VIEW: User security risk assessment
-- -----------------------------------------------------------

CREATE VIEW v_user_security_risk AS
SELECT
    u.id AS user_id, u.email, u.status, u.locked_until,
    COUNT(ll.id) FILTER (WHERE ll.result != 'success' AND ll.logged_at > NOW() - INTERVAL '1 hour') AS failures_last_hour,
    COUNT(DISTINCT ll.ip_address) FILTER (WHERE ll.logged_at > NOW() - INTERVAL '1 hour') AS distinct_ips_last_hour
FROM users u
LEFT JOIN login_logs ll ON ll.user_id = u.id
GROUP BY u.id, u.email, u.status, u.locked_until
HAVING COUNT(ll.id) FILTER (WHERE ll.result != 'success' AND ll.logged_at > NOW() - INTERVAL '1 hour') > 0;


-- -----------------------------------------------------------
-- FUNCTION: Record operation cost (called by FastAPI after each job)
-- Works for ALL users (admin and regular)
-- -----------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_record_operation_cost(
    p_user_id BIGINT,
    p_trigger_type VARCHAR(64),
    p_agent_work_log_id BIGINT DEFAULT NULL,
    p_cpu_seconds NUMERIC DEFAULT 0,
    p_memory_mb_seconds NUMERIC DEFAULT 0,
    p_gpu_seconds NUMERIC DEFAULT 0,
    p_llm_input_tokens INTEGER DEFAULT 0,
    p_llm_output_tokens INTEGER DEFAULT 0,
    p_api_calls_external INTEGER DEFAULT 0,
    p_primers_generated INTEGER DEFAULT 0,
    p_storage_mb_used NUMERIC DEFAULT 0,
    p_tokens_consumed INTEGER DEFAULT 1,
    p_revenue_per_token NUMERIC DEFAULT 49.00  -- Default ₹49/token for paying users
) RETURNS BIGINT AS $$
DECLARE
    v_infra_cost NUMERIC;
    v_llm_cost NUMERIC;
    v_api_cost NUMERIC;
    v_revenue NUMERIC;
    v_is_admin BOOLEAN;
    v_billing_method VARCHAR(32);
    v_cost_id BIGINT;
    
    -- Rates (fetched from infra_rate_card or hardcoded fallbacks)
    r_cpu NUMERIC := 0.0015;        -- ₹0.0015 per CPU second
    r_memory NUMERIC := 0.0001;     -- ₹0.0001 per MB-second
    r_gpu NUMERIC := 0.05;          -- ₹0.05 per GPU second
    r_llm_input NUMERIC := 0.002;   -- ₹0.002 per input token
    r_llm_output NUMERIC := 0.006;  -- ₹0.006 per output token
    r_api_call NUMERIC := 0.50;     -- ₹0.50 per external API call
BEGIN
    -- Check if user is admin
    SELECT (role = 'admin') INTO v_is_admin FROM users WHERE id = p_user_id;
    
    -- Try to get current rates from rate card (use defaults if not found)
    SELECT rate_inr INTO r_cpu FROM infra_rate_card
        WHERE resource_type = 'cpu_second' AND effective_until IS NULL LIMIT 1;
    SELECT rate_inr INTO r_llm_input FROM infra_rate_card
        WHERE resource_type = 'llm_input_token' AND effective_until IS NULL LIMIT 1;
    SELECT rate_inr INTO r_llm_output FROM infra_rate_card
        WHERE resource_type = 'llm_output_token' AND effective_until IS NULL LIMIT 1;
    SELECT rate_inr INTO r_gpu FROM infra_rate_card
        WHERE resource_type = 'gpu_second' AND effective_until IS NULL LIMIT 1;
    SELECT rate_inr INTO r_api_call FROM infra_rate_card
        WHERE resource_type = 'external_api_call' AND effective_until IS NULL LIMIT 1;
    
    -- Calculate costs
    v_infra_cost := (p_cpu_seconds * r_cpu)
                  + (p_memory_mb_seconds * r_memory)
                  + (p_gpu_seconds * r_gpu)
                  + (p_storage_mb_used * 0.001);  -- ₹0.001 per MB
    
    v_llm_cost := (p_llm_input_tokens * r_llm_input)
                + (p_llm_output_tokens * r_llm_output);
    
    v_api_cost := p_api_calls_external * r_api_call;
    
    -- Determine revenue and billing method
    IF v_is_admin THEN
        v_revenue := 0;
        v_billing_method := 'admin_free';
    ELSE
        v_revenue := p_tokens_consumed * p_revenue_per_token;
        v_billing_method := 'token';
    END IF;
    
    -- Insert cost record
    INSERT INTO cost_ledger (
        user_id, trigger_type, agent_work_log_id,
        cpu_seconds, memory_mb_seconds, gpu_seconds,
        llm_input_tokens, llm_output_tokens,
        api_calls_external, primers_generated, storage_mb_used,
        infra_cost_inr, llm_cost_inr, external_api_cost_inr,
        revenue_inr, is_billable, billing_method, tokens_consumed,
        description
    ) VALUES (
        p_user_id, p_trigger_type, p_agent_work_log_id,
        p_cpu_seconds, p_memory_mb_seconds, p_gpu_seconds,
        p_llm_input_tokens, p_llm_output_tokens,
        p_api_calls_external, p_primers_generated, p_storage_mb_used,
        v_infra_cost, v_llm_cost, v_api_cost,
        v_revenue, NOT v_is_admin, v_billing_method, p_tokens_consumed,
        format('%s: %s primers, %s LLM tokens, %s CPU sec',
               p_trigger_type, p_primers_generated,
               p_llm_input_tokens + p_llm_output_tokens, p_cpu_seconds)
    ) RETURNING id INTO v_cost_id;
    
    -- Link back to agent_work_log if provided
    IF p_agent_work_log_id IS NOT NULL THEN
        UPDATE agent_work_logs SET cost_entry_id = v_cost_id
        WHERE id = p_agent_work_log_id;
    END IF;
    
    RETURN v_cost_id;
END;
$$ LANGUAGE plpgsql;


-- -----------------------------------------------------------
-- FUNCTION: Get user financial summary (for dashboard API)
-- -----------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_user_financial_summary(p_user_id BIGINT)
RETURNS TABLE (
    total_paid NUMERIC,
    total_cost_generated NUMERIC,
    net_margin NUMERIC,
    margin_percent NUMERIC,
    tokens_remaining INTEGER,
    tokens_consumed INTEGER,
    avg_cost_per_operation NUMERIC,
    subscription_active BOOLEAN,
    subscription_expires TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COALESCE(tb.lifetime_revenue_inr, 0)::NUMERIC AS total_paid,
        COALESCE(tb.lifetime_cogs_inr, 0)::NUMERIC AS total_cost_generated,
        (COALESCE(tb.lifetime_revenue_inr, 0) - COALESCE(tb.lifetime_cogs_inr, 0))::NUMERIC AS net_margin,
        CASE WHEN COALESCE(tb.lifetime_revenue_inr, 0) > 0
            THEN ((tb.lifetime_revenue_inr - tb.lifetime_cogs_inr) / tb.lifetime_revenue_inr * 100)::NUMERIC(6,2)
            ELSE 0::NUMERIC(6,2)
        END AS margin_percent,
        COALESCE(tb.balance, 0) AS tokens_remaining,
        COALESCE(tb.total_consumed, 0) AS tokens_consumed,
        CASE WHEN COALESCE(tb.total_consumed, 0) > 0
            THEN (tb.lifetime_cogs_inr / tb.total_consumed)::NUMERIC(8,4)
            ELSE 0::NUMERIC(8,4)
        END AS avg_cost_per_operation,
        COALESCE(s.is_active, FALSE) AS subscription_active,
        s.expires_at AS subscription_expires
    FROM token_balances tb
    LEFT JOIN subscriptions s ON s.user_id = tb.user_id
    WHERE tb.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

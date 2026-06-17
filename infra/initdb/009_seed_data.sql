-- =============================================================
-- 009: Seed Data — Infrastructure Rate Card & Initial Config
-- =============================================================

-- -----------------------------------------------------------
-- Infrastructure wholesale rates (what E2E/providers charge us)
-- Update these when your hosting costs change
-- -----------------------------------------------------------

INSERT INTO infra_rate_card (resource_type, rate_inr, vendor, notes) VALUES
    ('cpu_second',          0.0015,   'E2E Networks',  'C3 instance compute: ~₹5.4/hr amortized per vCPU'),
    ('memory_mb_second',    0.0001,   'E2E Networks',  'RAM usage cost component'),
    ('gpu_second',          0.0500,   'E2E Networks',  'GPU instance amortized rate (if applicable)'),
    ('llm_input_token',     0.0020,   'OpenAI/Anthropic', 'Average across GPT-4o/Claude Sonnet input pricing'),
    ('llm_output_token',    0.0060,   'OpenAI/Anthropic', 'Average across GPT-4o/Claude Sonnet output pricing'),
    ('external_api_call',   0.5000,   'NCBI/Ensembl',  'Avg cost per bioinformatics API call (rate-limited)'),
    ('storage_mb',          0.0010,   'E2E Networks',  'SSD block storage per MB per operation'),
    ('network_egress_mb',   0.0005,   'E2E Networks',  'Outbound data transfer per MB');

-- -----------------------------------------------------------
-- Fixed recurring company expenses (update monthly)
-- -----------------------------------------------------------

INSERT INTO fixed_expenses (expense_category, vendor, description, amount_inr, frequency, billing_period_start, billing_period_end) VALUES
    ('infrastructure', 'E2E Networks',   'C3 Cloud Node (4 vCPU, 8GB RAM, 200GB SSD)', 3500.00, 'monthly', '2026-06-01', '2026-06-30'),
    ('infrastructure', 'E2E Networks',   'Additional block storage 200GB',              500.00,  'monthly', '2026-06-01', '2026-06-30'),
    ('saas_tools',     'Razorpay',       'Payment gateway platform fee',                0.00,    'monthly', '2026-06-01', '2026-06-30'),  -- They charge per-txn, tracked in revenue_ledger
    ('domain_ssl',     'GoDaddy/CF',     'Domain registration + SSL certificate',       1200.00, 'yearly',  '2026-01-01', '2026-12-31'),
    ('saas_tools',     'OpenAI',         'LLM API monthly estimated base cost',         5000.00, 'monthly', '2026-06-01', '2026-06-30'),
    ('infrastructure', 'Docker Hub',     'Container registry (free tier)',               0.00,    'monthly', '2026-06-01', '2026-06-30');

-- -----------------------------------------------------------
-- Example: How the app should call fn_record_operation_cost
-- after a primer design completes
-- -----------------------------------------------------------
-- SELECT fn_record_operation_cost(
--     p_user_id := 1,
--     p_trigger_type := 'primer_design',
--     p_agent_work_log_id := 42,
--     p_cpu_seconds := 12.5,
--     p_memory_mb_seconds := 1024.0,
--     p_llm_input_tokens := 3500,
--     p_llm_output_tokens := 800,
--     p_api_calls_external := 2,
--     p_primers_generated := 4,
--     p_tokens_consumed := 1,
--     p_revenue_per_token := 49.00
-- );
--
-- This will:
-- 1. Calculate infra cost from rate card
-- 2. Calculate LLM cost from rate card  
-- 3. Set revenue = ₹49 (1 token consumed × ₹49/token) for regular users
-- 4. Set revenue = ₹0 for admin users (auto-detected)
-- 5. Calculate margin automatically via trigger
-- 6. Update the user's lifetime totals in token_balances

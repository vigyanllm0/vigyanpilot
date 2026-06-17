-- =============================================================
-- 004: Indexes (B-tree, GIN, Partial, Expression)
-- =============================================================

-- --- Users ---
CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_users_role ON users (role);
CREATE INDEX idx_users_status ON users (status);
CREATE INDEX idx_users_locked ON users (locked_until)
    WHERE locked_until IS NOT NULL;
CREATE INDEX idx_users_org ON users (organization)
    WHERE organization IS NOT NULL;

-- --- Login Logs ---
CREATE INDEX idx_login_logs_user_id ON login_logs (user_id);
CREATE INDEX idx_login_logs_logged_at ON login_logs (logged_at DESC);
CREATE INDEX idx_login_logs_ip ON login_logs (ip_address);
CREATE INDEX idx_login_logs_failures ON login_logs (user_id, logged_at DESC)
    WHERE result != 'success';

-- --- Agent Work Logs ---
CREATE INDEX idx_agent_logs_user_id ON agent_work_logs (user_id);
CREATE INDEX idx_agent_logs_agent_name ON agent_work_logs (agent_name);
CREATE INDEX idx_agent_logs_status ON agent_work_logs (status);
CREATE INDEX idx_agent_logs_queued_at ON agent_work_logs (queued_at DESC);
CREATE INDEX idx_agent_logs_parameters ON agent_work_logs USING GIN (parameters);
CREATE INDEX idx_agent_logs_cost_entry ON agent_work_logs (cost_entry_id)
    WHERE cost_entry_id IS NOT NULL;

-- --- Payments ---
CREATE INDEX idx_payments_user_id ON payments (user_id);
CREATE INDEX idx_payments_gateway_order ON payments (gateway_order_id);
CREATE INDEX idx_payments_gateway_payment ON payments (gateway_payment_id);
CREATE INDEX idx_payments_status ON payments (status);
CREATE INDEX idx_payments_product_type ON payments (product_type);
CREATE INDEX idx_payments_initiated_at ON payments (initiated_at DESC);
CREATE INDEX idx_payments_captured_at ON payments (captured_at DESC)
    WHERE captured_at IS NOT NULL;
CREATE INDEX idx_payments_pending ON payments (user_id, initiated_at DESC)
    WHERE status IN ('initiated', 'authorized');

-- --- Gateway Webhooks ---
CREATE INDEX idx_webhooks_payload ON gateway_webhooks USING GIN (raw_payload);
CREATE INDEX idx_webhooks_order_id ON gateway_webhooks ((raw_payload->>'order_id'));
CREATE INDEX idx_webhooks_nested_payment_id ON gateway_webhooks
    ((raw_payload->'payload'->'payment'->'entity'->>'id'));
CREATE INDEX idx_webhooks_event_type ON gateway_webhooks (event_type);
CREATE INDEX idx_webhooks_validation ON gateway_webhooks (validation_status);
CREATE INDEX idx_webhooks_processed_at ON gateway_webhooks (processed_at DESC);
CREATE INDEX idx_webhooks_untrusted ON gateway_webhooks (processed_at DESC)
    WHERE validation_status = 'untrusted';

-- --- System Events ---
CREATE INDEX idx_events_severity ON system_events (severity);
CREATE INDEX idx_events_module ON system_events (module);
CREATE INDEX idx_events_created_at ON system_events (created_at DESC);
CREATE INDEX idx_events_critical ON system_events (created_at DESC)
    WHERE severity IN ('ERROR', 'CRITICAL');
CREATE INDEX idx_events_message_trgm ON system_events USING GIN (message gin_trgm_ops);

-- --- Cost Ledger ---
CREATE INDEX idx_cost_user_id ON cost_ledger (user_id);
CREATE INDEX idx_cost_trigger_type ON cost_ledger (trigger_type);
CREATE INDEX idx_cost_created_at ON cost_ledger (created_at DESC);
CREATE INDEX idx_cost_billable ON cost_ledger (is_billable, created_at DESC);
CREATE INDEX idx_cost_agent_log ON cost_ledger (agent_work_log_id)
    WHERE agent_work_log_id IS NOT NULL;
-- For margin analysis queries
CREATE INDEX idx_cost_margin ON cost_ledger (user_id, created_at DESC)
    WHERE revenue_inr > 0;
-- For finding loss-making operations
CREATE INDEX idx_cost_negative_margin ON cost_ledger (created_at DESC)
    WHERE gross_margin_inr < 0;

-- --- Revenue Ledger ---
CREATE INDEX idx_revenue_user_id ON revenue_ledger (user_id);
CREATE INDEX idx_revenue_payment_id ON revenue_ledger (payment_id);
CREATE INDEX idx_revenue_type ON revenue_ledger (revenue_type);
CREATE INDEX idx_revenue_created_at ON revenue_ledger (created_at DESC);
CREATE INDEX idx_revenue_product ON revenue_ledger (product_id);

-- --- Fixed Expenses ---
CREATE INDEX idx_fixed_exp_category ON fixed_expenses (expense_category);
CREATE INDEX idx_fixed_exp_vendor ON fixed_expenses (vendor);
CREATE INDEX idx_fixed_exp_recurring ON fixed_expenses (is_recurring, frequency);

-- --- Infra Rate Card ---
CREATE INDEX idx_rate_card_resource ON infra_rate_card (resource_type);
CREATE INDEX idx_rate_card_active ON infra_rate_card (resource_type, effective_from DESC)
    WHERE effective_until IS NULL;

-- --- Token Balances ---
CREATE INDEX idx_token_bal_user ON token_balances (user_id);
CREATE INDEX idx_token_bal_balance ON token_balances (balance)
    WHERE balance > 0;

-- --- Subscriptions ---
CREATE INDEX idx_subs_user ON subscriptions (user_id);
CREATE INDEX idx_subs_active ON subscriptions (expires_at)
    WHERE is_active = TRUE;

-- --- Audit Trail ---
CREATE INDEX idx_audit_table_record ON audit_trail (table_name, record_id);
CREATE INDEX idx_audit_changed_at ON audit_trail (changed_at DESC);
CREATE INDEX idx_audit_changed_by ON audit_trail (changed_by);

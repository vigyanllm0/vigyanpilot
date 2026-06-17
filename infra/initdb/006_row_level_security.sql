-- =============================================================
-- 006: Row-Level Security (RLS)
-- =============================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_service') THEN
        CREATE ROLE app_service NOLOGIN;
    END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO app_service;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_service;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_service;
GRANT app_service TO vigyanpilot_app;

-- Enable RLS on user-facing tables
ALTER TABLE login_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_work_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE cost_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE revenue_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE token_balances ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;

-- Users see only their own data; admins see everything
CREATE POLICY rls_login_logs ON login_logs FOR ALL TO app_service
    USING (
        user_id::TEXT = current_setting('app.current_user_id', TRUE)
        OR EXISTS (SELECT 1 FROM users WHERE id::TEXT = current_setting('app.current_user_id', TRUE) AND role = 'admin')
    );

CREATE POLICY rls_agent_logs ON agent_work_logs FOR ALL TO app_service
    USING (
        user_id::TEXT = current_setting('app.current_user_id', TRUE)
        OR user_id IS NULL
        OR EXISTS (SELECT 1 FROM users WHERE id::TEXT = current_setting('app.current_user_id', TRUE) AND role = 'admin')
    );

CREATE POLICY rls_payments ON payments FOR ALL TO app_service
    USING (
        user_id::TEXT = current_setting('app.current_user_id', TRUE)
        OR EXISTS (SELECT 1 FROM users WHERE id::TEXT = current_setting('app.current_user_id', TRUE) AND role = 'admin')
    );

CREATE POLICY rls_cost_ledger ON cost_ledger FOR ALL TO app_service
    USING (
        user_id::TEXT = current_setting('app.current_user_id', TRUE)
        OR EXISTS (SELECT 1 FROM users WHERE id::TEXT = current_setting('app.current_user_id', TRUE) AND role = 'admin')
    );

CREATE POLICY rls_revenue_ledger ON revenue_ledger FOR ALL TO app_service
    USING (
        user_id::TEXT = current_setting('app.current_user_id', TRUE)
        OR EXISTS (SELECT 1 FROM users WHERE id::TEXT = current_setting('app.current_user_id', TRUE) AND role = 'admin')
    );

CREATE POLICY rls_token_balances ON token_balances FOR ALL TO app_service
    USING (
        user_id::TEXT = current_setting('app.current_user_id', TRUE)
        OR EXISTS (SELECT 1 FROM users WHERE id::TEXT = current_setting('app.current_user_id', TRUE) AND role = 'admin')
    );

CREATE POLICY rls_subscriptions ON subscriptions FOR ALL TO app_service
    USING (
        user_id::TEXT = current_setting('app.current_user_id', TRUE)
        OR EXISTS (SELECT 1 FROM users WHERE id::TEXT = current_setting('app.current_user_id', TRUE) AND role = 'admin')
    );

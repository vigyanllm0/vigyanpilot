-- 0128: Tool-usage analytics ledger (admin dashboard)
-- Records every tool run for BOTH scenarios:
--   1. Logged-in users  (user_email)
--   2. Anonymous guests (client_ip — true IP behind CloudFront/nginx)
-- The same table powers the admin "Usage & Behavior" dashboard. Idempotent.

CREATE TABLE IF NOT EXISTS tool_usage_events (
    id BIGSERIAL PRIMARY KEY,
    tool_key VARCHAR(48) NOT NULL,
    tool_category VARCHAR(32) NOT NULL DEFAULT 'other',
    is_authenticated BOOLEAN NOT NULL DEFAULT FALSE,
    user_email VARCHAR(255),
    user_plan VARCHAR(32) NOT NULL DEFAULT 'guest',
    client_ip VARCHAR(45) NOT NULL,
    sequences_count INTEGER NOT NULL DEFAULT 1,
    usage_date VARCHAR(10) NOT NULL,
    created_at DOUBLE PRECISION NOT NULL DEFAULT (EXTRACT(EPOCH FROM NOW()))
);

CREATE INDEX IF NOT EXISTS idx_tue_date ON tool_usage_events(usage_date);
CREATE INDEX IF NOT EXISTS idx_tue_tool_date ON tool_usage_events(tool_key, usage_date);
CREATE INDEX IF NOT EXISTS idx_tue_ip_date ON tool_usage_events(client_ip, usage_date);
CREATE INDEX IF NOT EXISTS idx_tue_email_date ON tool_usage_events(user_email, usage_date);

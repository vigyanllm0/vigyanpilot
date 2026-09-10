-- Migration 0125: API Key Management
-- Creates api_keys and api_usage_logs tables

CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(64) NOT NULL UNIQUE,
    key_prefix VARCHAR(12) NOT NULL,
    name TEXT NOT NULL DEFAULT 'Default API Key',
    scopes JSONB NOT NULL DEFAULT '["primer", "blast", "msa"]'::jsonb,
    rate_limit INTEGER NOT NULL DEFAULT 60,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DOUBLE PRECISION NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW()),
    last_used_at DOUBLE PRECISION,
    expires_at DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);

CREATE TABLE IF NOT EXISTS api_usage_logs (
    id SERIAL PRIMARY KEY,
    api_key_id INTEGER NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
    endpoint TEXT NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER NOT NULL,
    latency_ms INTEGER NOT NULL,
    created_at DOUBLE PRECISION NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())
);

CREATE INDEX IF NOT EXISTS idx_api_usage_key ON api_usage_logs(api_key_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_created ON api_usage_logs(created_at);

-- Webhook tables
CREATE TABLE IF NOT EXISTS webhooks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    events JSONB NOT NULL DEFAULT '["primer.complete"]'::jsonb,
    secret VARCHAR(64) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DOUBLE PRECISION NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())
);

CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id SERIAL PRIMARY KEY,
    webhook_id INTEGER NOT NULL REFERENCES webhooks(id) ON DELETE CASCADE,
    event TEXT NOT NULL,
    payload JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    response_code INTEGER,
    response_body TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    next_retry_at DOUBLE PRECISION,
    created_at DOUBLE PRECISION NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())
);

CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_status ON webhook_deliveries(status);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_retry ON webhook_deliveries(next_retry_at) WHERE status = 'pending';

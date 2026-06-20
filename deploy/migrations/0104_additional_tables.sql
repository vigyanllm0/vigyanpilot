CREATE TABLE IF NOT EXISTS sequence_cache (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(32) NOT NULL,
    query_key VARCHAR(512) NOT NULL,
    sequence TEXT NOT NULL,
    metadata JSONB,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '7 days',
    UNIQUE(source, query_key)
);

CREATE INDEX IF NOT EXISTS idx_sequence_cache_source_key ON sequence_cache(source, query_key);
CREATE INDEX IF NOT EXISTS idx_sequence_cache_expires_at ON sequence_cache(expires_at);

CREATE TABLE IF NOT EXISTS user_quotas (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    month DATE NOT NULL,
    quota_used INTEGER DEFAULT 0,
    monthly_quota INTEGER DEFAULT 0,
    UNIQUE(user_id, month)
);

CREATE TABLE IF NOT EXISTS login_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    logged_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_address INET NOT NULL,
    user_agent TEXT,
    session_token_hash TEXT,
    result VARCHAR(32) NOT NULL,
    failure_reason TEXT
);

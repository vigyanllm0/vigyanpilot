-- Migration 0123: Anonymous daily usage tracking (1/day limit)
-- Anonymous users get 1 free analysis per day, tracked by IP+UA fingerprint.

CREATE TABLE IF NOT EXISTS anon_daily_usage (
    id SERIAL PRIMARY KEY,
    fingerprint VARCHAR(64) NOT NULL,
    usage_date VARCHAR(10) NOT NULL,
    count INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(fingerprint, usage_date)
);

CREATE INDEX IF NOT EXISTS idx_anon_daily_usage_lookup
    ON anon_daily_usage (fingerprint, usage_date);

-- Clean up entries older than 7 days periodically
-- (handled by application code or pg_cron if available)

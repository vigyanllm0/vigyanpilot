-- Migration 0113: Token blacklist table for persistent session revocation
-- Stores hashed tokens that have been invalidated (logout, password change).
-- Prevents server-restart from allowing revoked tokens to be reused.

CREATE TABLE IF NOT EXISTS token_blacklist (
    id          SERIAL PRIMARY KEY,
    token_hash  VARCHAR(64) NOT NULL UNIQUE,
    expires_at  TIMESTAMP WITH TIME ZONE,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_token_blacklist_hash ON token_blacklist (token_hash);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_expires ON token_blacklist (expires_at);

-- Auto-cleanup: periodically remove expired entries (tokens older than their expiry)
-- This is a safety net; the app also prunes on startup and during operations.

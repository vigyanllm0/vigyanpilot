-- Migration 0118: Expense log table for tracking company expenses (promo trials, verification charges, etc.)
-- Run after 0117_promo_codes_trial_subscriptions.sql

CREATE TABLE IF NOT EXISTS expense_log (
    id              BIGSERIAL PRIMARY KEY,
    category        VARCHAR(64) NOT NULL DEFAULT 'promo_trial',   -- 'promo_trial', 'verification_charge', 'trial_service', 'fixed_cost', 'other'
    description     TEXT NOT NULL DEFAULT '',
    amount_inr      NUMERIC(12, 2) NOT NULL DEFAULT 0,
    promo_code      VARCHAR(64) DEFAULT '',
    user_email      VARCHAR(255) DEFAULT '',
    subscription_id VARCHAR(128) DEFAULT '',
    metadata        JSONB DEFAULT '{}',
    created_by      VARCHAR(255) DEFAULT 'system',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_expense_log_category ON expense_log(category);
CREATE INDEX IF NOT EXISTS idx_expense_log_created ON expense_log(created_at);
CREATE INDEX IF NOT EXISTS idx_expense_log_promo ON expense_log(promo_code);

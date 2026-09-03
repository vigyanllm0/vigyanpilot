-- Migration 0117: Promo codes + trial subscriptions
-- Adds promo_codes table, trial_subscriptions table, and new user columns for academic trial system

-- New user columns
ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_ends_at DOUBLE PRECISION DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS promo_code_used TEXT DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS razorpay_subscription_id TEXT DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS razorpay_customer_id TEXT DEFAULT '';

-- Promo codes table
CREATE TABLE IF NOT EXISTS promo_codes (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    tier TEXT NOT NULL DEFAULT 'pro',
    daily_analyses INTEGER DEFAULT 50,
    batch_max INTEGER DEFAULT 20,
    has_export INTEGER DEFAULT 1,
    trial_days INTEGER NOT NULL DEFAULT 30,
    price_inr INTEGER NOT NULL DEFAULT 699,
    currency TEXT DEFAULT 'INR',
    razorpay_plan_id TEXT DEFAULT '',
    max_uses INTEGER DEFAULT 1,
    used_count INTEGER DEFAULT 0,
    created_by TEXT DEFAULT 'admin',
    created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    expires_at DOUBLE PRECISION DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_promo_codes_code ON promo_codes(code);

-- Trial subscriptions table
CREATE TABLE IF NOT EXISTS trial_subscriptions (
    id SERIAL PRIMARY KEY,
    user_email TEXT NOT NULL,
    promo_code TEXT NOT NULL,
    razorpay_subscription_id TEXT UNIQUE NOT NULL,
    razorpay_plan_id TEXT NOT NULL,
    trial_days INTEGER NOT NULL,
    trial_started_at DOUBLE PRECISION NOT NULL,
    trial_ends_at DOUBLE PRECISION NOT NULL,
    status TEXT DEFAULT 'trial',
    created_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);

CREATE INDEX IF NOT EXISTS idx_trial_subscriptions_email ON trial_subscriptions(user_email);
CREATE INDEX IF NOT EXISTS idx_trial_subscriptions_sub_id ON trial_subscriptions(razorpay_subscription_id);

-- VigyanLLM Initial Schema
-- This is the baseline schema matching infra/initdb/*.sql
-- Applied automatically by deploy/migrations/migrate.py on first deploy

-- Extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(256) DEFAULT '',
    role VARCHAR(20) DEFAULT 'user',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    run_count INTEGER DEFAULT 0,
    paid_runs INTEGER DEFAULT 0,
    failed_login_count INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    last_active_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Token balances
CREATE TABLE IF NOT EXISTS token_balances (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    balance INTEGER DEFAULT 0,
    total_purchased INTEGER DEFAULT 0,
    total_consumed INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Usage log
CREATE TABLE IF NOT EXISTS usage_log (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    action VARCHAR(255) NOT NULL,
    details TEXT DEFAULT '',
    ip_address VARCHAR(45) DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Payments
CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    amount INTEGER NOT NULL,
    razorpay_order_id VARCHAR(255),
    razorpay_payment_id VARCHAR(255),
    razorpay_signature VARCHAR(512),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

-- User reports
CREATE TABLE IF NOT EXISTS user_reports (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    job_id VARCHAR(255) NOT NULL,
    title TEXT DEFAULT '',
    forward_seq TEXT DEFAULT '',
    reverse_seq TEXT DEFAULT '',
    tm FLOAT,
    gc_percent FLOAT,
    amplicon_size INTEGER,
    delta_g FLOAT,
    report_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Academic claims
CREATE TABLE IF NOT EXISTS academic_claims (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    institution TEXT NOT NULL,
    department TEXT DEFAULT '',
    use_case TEXT DEFAULT '',
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Referrals
CREATE TABLE IF NOT EXISTS referrals (
    id SERIAL PRIMARY KEY,
    referrer_email VARCHAR(255) NOT NULL,
    referred_email VARCHAR(255) DEFAULT '',
    referral_code VARCHAR(50) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Feedback submissions
CREATE TABLE IF NOT EXISTS feedback_submissions (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    context TEXT DEFAULT '',
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Login logs
CREATE TABLE IF NOT EXISTS login_logs (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45) DEFAULT '',
    user_agent TEXT DEFAULT '',
    result VARCHAR(20) DEFAULT 'success',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_token_balances_user ON token_balances(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_log_user ON usage_log(user_email);
CREATE INDEX IF NOT EXISTS idx_usage_log_created ON usage_log(created_at);
CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_email);
CREATE INDEX IF NOT EXISTS idx_user_reports_user ON user_reports(user_email);

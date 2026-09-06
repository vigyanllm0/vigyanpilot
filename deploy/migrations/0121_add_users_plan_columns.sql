-- 0121: Add plan-related columns to users table for admin panel
-- These columns are referenced by pg_auth_routes.py list_users() but were never migrated

ALTER TABLE users ADD COLUMN IF NOT EXISTS plan VARCHAR(20) DEFAULT 'free';
ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_activated_at DOUBLE PRECISION DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_academic BOOLEAN DEFAULT FALSE;

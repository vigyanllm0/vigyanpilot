-- 0114: Add first_login_ip column to users table
-- pg_auth.py INSERTs into this column but it was never created via migration.

ALTER TABLE users ADD COLUMN IF NOT EXISTS first_login_ip VARCHAR(45);
CREATE INDEX IF NOT EXISTS idx_users_first_login_ip ON users(first_login_ip);

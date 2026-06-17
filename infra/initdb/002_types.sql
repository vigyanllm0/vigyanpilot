-- =============================================================
-- 002: Custom ENUM Types
-- =============================================================

CREATE TYPE user_status AS ENUM ('active', 'suspended');
CREATE TYPE user_role AS ENUM ('user', 'admin');
CREATE TYPE login_result AS ENUM ('success', 'failed_wrong_password', 'blocked');
CREATE TYPE task_status AS ENUM ('queued', 'processing', 'completed', 'crashed');
CREATE TYPE payment_status AS ENUM ('initiated', 'authorized', 'captured', 'failed', 'refunded');
CREATE TYPE webhook_trust AS ENUM ('verified', 'untrusted');
CREATE TYPE event_severity AS ENUM ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL');
CREATE TYPE expense_type AS ENUM ('user_query', 'admin_internal_test');

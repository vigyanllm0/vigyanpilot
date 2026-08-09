-- 0115: Add UNIQUE constraint on token_balances.user_id
-- Without this, ON CONFLICT (user_id) in verify_email_with_token() always fails
-- because PostgreSQL requires a unique index for ON CONFLICT to work.
-- This caused ALL email verifications to silently roll back.

ALTER TABLE token_balances ADD CONSTRAINT token_balances_user_id_unique UNIQUE (user_id);

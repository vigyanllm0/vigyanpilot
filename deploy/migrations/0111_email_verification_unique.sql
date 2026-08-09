-- Add UNIQUE constraint on email_verifications.user_id
-- Required by ON CONFLICT (user_id) in create_verification_token()
ALTER TABLE email_verifications ADD CONSTRAINT IF NOT EXISTS email_verifications_user_id_unique UNIQUE (user_id);

-- Add UNIQUE constraint on email_verifications.user_id
-- Required by ON CONFLICT (user_id) in create_verification_token()
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'email_verifications_user_id_unique'
        AND conrelid = 'email_verifications'::regclass
    ) THEN
        ALTER TABLE email_verifications ADD CONSTRAINT email_verifications_user_id_unique UNIQUE (user_id);
    END IF;
END $$;

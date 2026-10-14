-- 0128: referral program — one row per referred person (multi-referral)
--
-- The referrer's code row was the ONLY row per code: apply_referral()
-- UPDATEd it, so the 2nd person to use any referral code got "code not
-- found or already used" — every referrer was capped at ONE lifetime
-- referral (observed in QA on both DB paths). The model now INSERTs a new
-- pending_design row per referred person while the code row stays reusable,
-- which requires referral_code to no longer be UNIQUE.
--
-- (Also reconciles a legacy 0100-shape referrals table if one ever existed:
-- 0100 created the table first and 0105's CREATE IF NOT EXISTS skipped on
-- top of it, leaving no referrer_id column. Production is verified on the
-- 0105 shape; a fresh sequential 0100→0105 run would hit this branch with
-- an empty table. The legacy shape is unusable by current code either way.)

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'referrals' AND column_name = 'referrer_id'
    ) THEN
        DROP TABLE referrals;
        CREATE TABLE referrals (
            id BIGSERIAL PRIMARY KEY,
            referrer_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            referred_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
            referral_code VARCHAR(64) NOT NULL,
            referred_email VARCHAR(320),
            status VARCHAR(32) NOT NULL DEFAULT 'active',
            tokens_awarded INTEGER DEFAULT 0,
            completed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX idx_referrals_referrer_id ON referrals(referrer_id);
        CREATE INDEX idx_referrals_referral_code ON referrals(referral_code);
    END IF;
END $$;

-- Shared code must be reusable across referral events; lookups stay fast on
-- the existing non-unique idx_referrals_referral_code index.
ALTER TABLE referrals DROP CONSTRAINT IF EXISTS referrals_referral_code_key;

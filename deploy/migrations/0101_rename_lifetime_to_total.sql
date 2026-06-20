-- Rename lifetime_purchased to total_purchased for consistency with application code
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='token_balances' AND column_name='lifetime_purchased') THEN
    ALTER TABLE token_balances RENAME COLUMN lifetime_purchased TO total_purchased;
  END IF;
END $$;

-- Add total_consumed column if not exists (referenced by code but missing from schema)
ALTER TABLE token_balances ADD COLUMN IF NOT EXISTS total_consumed INTEGER DEFAULT 0;

-- Rename lifetime_purchased to total_purchased for consistency with application code
ALTER TABLE token_balances RENAME COLUMN lifetime_purchased TO total_purchased;

-- Add total_consumed column if not exists (referenced by code but missing from schema)
ALTER TABLE token_balances ADD COLUMN IF NOT EXISTS total_consumed INTEGER DEFAULT 0;

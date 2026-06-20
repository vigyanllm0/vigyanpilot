ALTER TABLE token_balances ADD COLUMN IF NOT EXISTS total_purchased INTEGER DEFAULT 0;
ALTER TABLE token_balances ADD COLUMN IF NOT EXISTS total_consumed INTEGER DEFAULT 0;
UPDATE token_balances SET total_purchased = lifetime_purchased WHERE total_purchased IS NULL AND lifetime_purchased IS NOT NULL;
ALTER TABLE token_balances DROP COLUMN IF EXISTS lifetime_purchased;

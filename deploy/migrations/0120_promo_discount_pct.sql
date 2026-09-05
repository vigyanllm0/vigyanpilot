-- Migration 0120: Add discount_pct to promo_codes for checkout discounts
-- promo_codes with promo_type='discount' will use this to reduce the checkout amount.

ALTER TABLE promo_codes ADD COLUMN IF NOT EXISTS discount_pct INTEGER DEFAULT 0;

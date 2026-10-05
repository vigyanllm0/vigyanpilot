-- 0126: USD pricing migration
-- ============================================================
-- From this release, ALL amounts are minor units of the row's
-- currency (USD cents for new orders, `currency` column = 'USD').
--
-- Storage rules (documented once, enforced by application code):
--   * payments.amount: 'USD' rows = minor units (cents)
--     legacy 'INR' rows (pre-0126) = MAJOR rupees (readers
--     normalise per-row by currency — no data rewrite needed).
--   * promo_codes.price_inr: legacy field NAME kept — from now on
--     the value is MINOR units of promo_codes.currency.
--
-- Legacy promo codes stored MAJOR rupees (e.g. 699 = ₹699).
-- Re-reading those rows as minor units would silently turn a
-- ₹699 trial into ₹6.99, so instead of guessing an FX rate we
-- RETIRE every INR-priced code — admins re-issue USD codes.
-- ============================================================

-- 1) Retire redeemed-capable INR codes: pin max_uses to used_count so
--    every validation path (validate/apply/create-order) rejects them.
UPDATE promo_codes
   SET max_uses = used_count
 WHERE currency = 'INR'
   AND price_inr > 0
   AND max_uses > used_count;

-- 2) Unlimited INR codes (max_uses = 0): expire them instead.
UPDATE promo_codes
   SET expires_at = 1
 WHERE currency = 'INR'
   AND price_inr > 0
   AND max_uses = 0
   AND (expires_at = 0 OR expires_at > 1);

-- 3) New-code defaults follow the USD regime (values are always supplied
--    explicitly by the app, which keeps the schema honest for manual inserts).
ALTER TABLE promo_codes ALTER COLUMN price_inr SET DEFAULT 999;
ALTER TABLE promo_codes ALTER COLUMN currency SET DEFAULT 'USD';

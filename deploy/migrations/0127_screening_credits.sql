-- 0127: docking credit ledger (credit-based docking pricing)
--
-- Docking moves from a flat "$1 per run" token to a credit ledger:
--   * subscriptions grant credits every billing period
--       Pro / trial  = 1,000 credits   Lab = 5,000 credits
--   * a $1.00 dock top-up credits 80 credits into dock_credit_balance
--     (deliberately worse than the subscription rate — plans are the cheap path)
--   * a virtual screening campaign debits a size-aware amount up front and
--     refunds the unperformed share when it is cancelled
-- The existing analysis-token `balance` column is untouched: it still pays
-- for the other nine tools and is never spent on docking.

ALTER TABLE token_balances ADD COLUMN IF NOT EXISTS dock_credit_balance INTEGER NOT NULL DEFAULT 0;

-- Subscriptions sold before docking credits existed carried a dock quota of 0
-- (the old registry returned 0 docking runs for every plan). Give active
-- Pro/Lab/trial subscriptions their credit grant. `dock_quota_used` is left
-- alone — a mid-period subscriber keeps their consumption history.
UPDATE subscriptions
SET dock_monthly_quota = CASE
        WHEN plan_id IN ('pro-monthly', 'pro-yearly', 'trial') THEN 1000
        WHEN plan_id IN ('lab-monthly', 'lab-yearly') THEN 5000
        ELSE dock_monthly_quota
    END
WHERE is_active = TRUE
  AND dock_monthly_quota < CASE
        WHEN plan_id IN ('pro-monthly', 'pro-yearly', 'trial') THEN 1000
        WHEN plan_id IN ('lab-monthly', 'lab-yearly') THEN 5000
        ELSE 0
    END;

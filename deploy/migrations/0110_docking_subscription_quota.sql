-- Add docking quota columns to subscriptions table
-- Each subscription plan now includes both primer design and docking credits

ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS dock_monthly_quota INTEGER DEFAULT 0;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS dock_quota_used INTEGER DEFAULT 0;

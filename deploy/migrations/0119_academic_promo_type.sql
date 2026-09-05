-- Migration 0119: Academic promo type + pro expiry
-- Adds promo_type column to promo_codes (trial vs academic)
-- Adds pro_expires_at column to users (for academic auto-downgrade)

-- New user columns
ALTER TABLE users ADD COLUMN IF NOT EXISTS pro_expires_at DOUBLE PRECISION DEFAULT 0;

-- Promo codes: add promo_type
ALTER TABLE promo_codes ADD COLUMN IF NOT EXISTS promo_type TEXT DEFAULT 'trial';
-- 'trial' = Rs.1 verification → trial period → auto-debit Pro
-- 'academic' = free Pro access for X days, no payment, no Razorpay subscription

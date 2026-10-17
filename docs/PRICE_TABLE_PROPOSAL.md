# Revenue ③ — Proposed ₹/$ Price Table (Market Pricing, No FX)

**Status:** Awaiting founder approval
**Date:** 2026-10-17

## Proposed Pricing

| Tier | USD (existing) | INR (proposed) | Rationale |
|------|---------------|----------------|-----------|
| Free | $0 | ₹0 | Same — no payment needed |
| Pro (monthly) | $9.99/mo | ₹799/mo | Indian market: ~₹800 is the "impulse buy" threshold for grad students; $9.99 ≈ ₹830 at market rate but we price lower to capture volume |
| Pro (yearly) | $89/yr (save 26%) | ₹6,999/yr (save 27%) | Annual discount slightly higher in INR to encourage commitment |
| Lab (monthly) | $49/mo | ₹3,999/mo | Lab budget: ₹4K/mo is within typical PI discretionary spend |
| Lab (yearly) | $399/yr (save 32%) | ₹32,999/yr (save 32%) | Same discount ratio |
| Enterprise | Quote | Quote (INR) | Custom pricing per institution |
| Top-up (100 runs) | $0.99 | ₹79 | Matches Pro per-run cost |
| Docking top-up (100 runs) | $0.49 | ₹39 | Matches docking per-run cost |

## GST Options (for founder decision)

**Option A — Exclusive (recommended):**
- Display price excludes GST
- GST (18%) added at checkout
- Invoice shows base + GST separately
- Pro: ₹799 + ₹143.82 GST = ₹942.82 total

**Option B — Inclusive:**
- Display price includes GST
- Invoice shows "GST included"
- Pro: ₹799 (incl. 18% GST) = ₹677.12 base + ₹121.88 GST

**Recommendation:** Option A (exclusive) — standard for SaaS in India, transparent, easier accounting.

## Payment Methods

- **INR orders:** UPI (primary), Cards, Net Banking, Wallets — all Razorpay-supported
- **USD orders:** Cards only (Razorpay auto-hides UPI on USD)
- Currency locked at order creation (no mid-checkout switching)

## Implementation Notes

- Currency selector: IP-based default (India → INR, else → USD) + manual override, persisted in localStorage
- Razorpay: separate product IDs per currency (already supported via `product_id` parameter)
- GA4: `transaction_id` + `currency` on every purchase event (already built in Phase 3)
- Pricing sweep: all customer-facing pages must show both currencies or auto-detect

## Founder Decision Needed

1. Approve ₹ amounts (or adjust)
2. Choose GST option (A or B)
3. Confirm UPI as primary for INR
4. Approve deployment of pricing surface
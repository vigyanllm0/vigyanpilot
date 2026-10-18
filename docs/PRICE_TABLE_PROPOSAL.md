# Revenue ③ — Proposed ₹/$ Price Table (Market Pricing, No FX) — v2, SIGN-READY

**Status:** Awaiting founder signature — sign THIS file, not chat
**v2 date:** 2026-10-18 (v1: 2026-10-17, commit `efa45081`)

## What changed in v2 (and why)

1. **Top-up unit corrected.** v1's table said "Top-up (100 runs)". The live registry sells
   **`$1.00 = 1 analysis run`** (`price_registry.py` `TOPUP_PRODUCTS["top_up"]`, label "Analysis
   run"; `dock_top_up` = $1.00 → 80 docking credits). The INR product must be the same product,
   per-run — otherwise two different things wear the same name. **All prices below are per 1 run**
   (dock: per 80-credit unit).
2. **Three competing tables retired.** v1 (this doc) and two chat-only tables (₹499/₹2,499/₹49)
   disagreed — the classic artifact-vs-chat divergence. Only the two candidate tables below remain
   in play, both rendered in corrected per-run units.
3. **GST adjudicated** (dev + advisor, independently): **Option A exclusive + shelf-total display**,
   pending the founder's 5-minute CA confirmation (verification of display obligations — not a
   blocker to signing the direction).

## Candidate tables — founder picks ONE (or adjusts numbers and initials)

**Option I — Conservative (v1's plan shape, top-up unit fixed):**

| Tier | USD | INR |
|------|-----|-----|
| Free | $0 | ₹0 |
| Pro (monthly) | $9.99 | **₹799** |
| Pro (yearly) — save ~27% | $89 | **₹6,999** |
| Lab (monthly) | $49 | **₹3,999** |
| Lab (yearly) — save ~31% | $399 | **₹32,999** |
| Top-up — 1 analysis run | $1.00 | **₹49** (v1 said ₹79 under the mislabeled unit; dev + advisor converged on ₹49 as the UPI impulse price — override if you disagree) |
| Dock top-up — 80 credits | $1.00 | **₹39** |
| Enterprise | Quote | Quote (INR) |

**Option II — Split-by-buyer (advisor-recommended):**

| Tier | USD | INR | Logic |
|------|-----|-----|-------|
| Free | $0 | ₹0 | — |
| Pro (monthly) | $9.99 | **₹599** | The volume tier — students price-shop; ₹499 vs ₹599 is not the decision variable, habit is. Still an unmistakable India price (~₹60/$) |
| Pro (yearly) — save ~30% | $89 | **₹4,999** | Preserves the yearly discount |
| Lab (monthly) | $49 | **₹3,499** | Institutional — procurement compares against global tools, not Indian ones; no consumer discount |
| Lab (yearly) — save ~29% | $399 | **₹29,999** | Institutional-grade number, ~30% yearly savings |
| Top-up — 1 analysis run | $1.00 | **₹49** | The UPI impulse tap — the cheapest acquisition experiment you own; ₹79 crosses a psychological line ₹49 doesn't |
| Dock top-up — 80 credits | $1.00 | **₹79** | 80 credits is a heavier action than 1 run |
| Enterprise | Quote | Quote (INR) | — |

Principle behind Option II: **discount where price-sensitivity lives (students, top-ups); hold
price where it doesn't (labs).** If you prefer one of the two original tables wholesale, take the
v1 track (Option I) — it is the more conservative bet — but both candidates already carry the
₹49 per-run top-up for the impulse reason alone.

Both options are deliberate **geo-pricing** (~₹49–80 per $1 vs the ₹94.96 mid-market of
2026-10-17), fenced by the UPI-only rule for INR orders (foreign users cannot arbitrage without an
Indian bank account). Sign conscious of that — this is a strategy, not a rounding.

## GST — adjudicated: Option A exclusive + shelf-total

- Display price **excludes** GST; 18% added at checkout; invoice shows base + GST separately.
- **Mandatory mitigation:** the total appears **on the pricing page, not first at checkout** —
  e.g. "₹599 + GST = ₹706.82" (Option II) / "₹799 + GST = ₹942.82" (Option I) rendered at the
  shelf. Kills the exclusive-display surprise on the impulse UPI tap while keeping the
  institutional-friendly tax-exclusive number + proper invoice.
- Option B (inclusive) from v1 is retained in git history for reference — not recommended:
  institutional procurement wants the tax-exclusive number.
- Open verification (not a blocker): 5-minute CA confirmation of display obligations. You are not
  yet GST-registered, so no display choice changes money collected today; the decision is on buyer
  priority (institutional vs consumer) and is reversible with a quarter of funnel data.

## Payment methods (agreed, unchanged)

- **INR orders:** UPI (primary), Cards, Net Banking, Wallets — all Razorpay-supported
- **USD orders:** Cards only (Razorpay auto-hides UPI on USD)
- Currency locked at order creation (no mid-checkout switching)

## Implementation notes (agreed — build starts only AFTER signature)

- Currency selector: IP-based default (India → INR, else → USD) + manual override, persisted in
  localStorage
- Razorpay: separate product IDs per currency (already supported via `product_id` parameter)
- GA4: `transaction_id` + `currency` on every purchase event (already built and live)
- Pricing-consistency sweep across homepage / pricing / tools / checkout / docs in **both**
  currencies = release gate, validated against **this file**
- Display rule from the GST adjudication: shelf shows price + computed total; checkout must never
  be the first place a customer sees GST

## Signature

- [ ] **Option I** — ₹799 / ₹6,999 / ₹3,999 / ₹32,999 / ₹49 / ₹39
- [ ] **Option II** — ₹599 / ₹4,999 / ₹3,499 / ₹29,999 / ₹49 / ₹79
- [ ] **Adjusted** (write numbers): ______________________________
- [ ] GST: **A exclusive + shelf-total** confirmed
- Signed: ______________________  Date: ____________

On signature the dev rewrites this file to the single signed table (alternatives removed), then:
build ③ to the adjudicated mechanics → consistency sweep validates against the signed table →
deploy behind the currency selector.

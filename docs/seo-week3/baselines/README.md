# GSC Baseline — Week-3 SEO Batch (captured 2026-10-26)

Files in this directory:

| File | What it is |
|---|---|
| `gsc-performance-2026-10-26.xlsx` | Performance export, **Last 3 months** (2026-07-25 → 2026-10-24), all sheets (Chart/Queries/Pages/Countries/Devices) |
| `gsc-coverage-2026-10-26.xlsx` | Coverage export at baseline |
| `gsc-coverage-2026-10-24.xlsx` | Coverage export 2 days earlier — the pre-deploy comparison anchor |

> **Scope note:** the Performance export's Filters sheet says *Last 3 months*.
> The 28-day figures below are computed from its daily Chart sheet, not read
> off a 28-day GSC view. Queries/Pages sheets are **3-month** totals.

## Performance baseline (VERIFIED from export)

### Last 28 days (2026-09-27 → 2026-10-24) — the Day-0 baseline

| Metric | Value |
|---|---|
| Clicks | **1,262** |
| Impressions | **137,323** |
| CTR | **0.92%** |
| Avg position | **8.5** (impression-weighted) |

### Full 3-month window (2026-07-25 → 2026-10-24)

| Metric | Value |
|---|---|
| Clicks | **2,387** |
| Impressions | **365,215** |
| CTR | **0.65%** |
| Avg position | **9.8** (impression-weighted) |

### Trajectory across the window (the strongest story in the data)

- First 7 days (Jul 25–31): 68 clicks ≈ **9.7/day**
- Last 28 days: 1,262 clicks ≈ **45/day**
- → **~4.6× growth in daily clicks** from window start to window end
- CTR rises within the window too: 3-month avg 0.65% vs recent 28d 0.92%

⚠️ **Correction to the handoff report:** the claimed 28-day baseline
(~1,340 clicks / ~155,000 impressions / 0.86% / pos 8.7) does not reproduce
from the export — neither the 3-month totals nor the computed 28-day window
match it. The figures above are computed directly from the daily Chart sheet
and are the ones that should be used for Day-30 comparison.
Also note: the original "0.55% CTR baseline" quoted in chat mixed windows —
both windows above are internally consistent, and CTR direction is **up**
(0.65% → 0.92%).

## Top queries (3-month, by clicks — VERIFIED)

| # | Query | Clicks | Impr | CTR | Pos |
|---|---|---|---|---|---|
| 1 | vigyanllm | 111 | 138 | 80.4% | 1.0 |
| 2 | primer blast | 33 | 36,521 | 0.09% | 6.7 |
| 3 | ncbi primer blast | 24 | 23,377 | 0.10% | 6.0 |
| 4 | pcr product size calculator | 13 | 64 | 20.3% | 3.5 |
| 5 | dna to rna converter | 12 | 665 | 1.8% | 5.7 |

## Top pages (3-month, by clicks — VERIFIED)

| # | Page | Clicks | Impr | CTR | Pos |
|---|---|---|---|---|---|
| 1 | /dna-3d | 288 | 2,449 | 11.8% | 7.4 |
| 2 | /blog/ncbi-primer-blast-guide | 206 | 142,579 | 0.14% | 6.7 |
| 3 | /pcr-product-calculator | 203 | 6,804 | 3.0% | 5.2 |
| 4 | /dna-to-rna | 166 | 5,019 | 3.3% | 7.4 |
| 5 | / (home) | 161 | 708 | 22.7% | 4.2 |

**#1 CTR opportunity (verified):** `/blog/ncbi-primer-blast-guide` —
142,579 impressions at 0.14% CTR. A position-6 page at even 1% CTR would be
~1,400 clicks/3mo instead of 206.

**Hidden opportunity (verified):** `/primer3-vs-idt` — 7 clicks /
37,682 impressions / **0.02% CTR** / pos 5.96 (3-month). Title/meta rewrite
candidate — must be top-5 in any meta pass.

**Data hygiene footnote:** the Pages sheet contains a malformed row
`https://www.vigyanllm.in/vigyanllm.in/primer3-vs-idt` (1 impression) —
an absolute-URL-as-path artifact Google picked up. Not actionable; noted so
future exports don't alarm anyone.

## Coverage delta (VERIFIED from both exports)

| Issue | Oct 24 | Oct 26 | Δ |
|---|---|---|---|
| Page with redirect | 314 | 0 | −314 |
| Alternative page w/ proper canonical | 112 | 15 | −97 |
| Excluded by noindex tag | 77 | 17 | −60 |
| Crawled, currently not indexed | 99 | 31 | −68 |
| Discovered, currently not indexed | 92 | 89 | −3 |
| Duplicate, Google chose different canonical | 5 | 2 | −3 |
| Soft 404 | 1 | 0 | −1 |
| Not found (404) | 46 | 0 | −46 |
| Redirect error | 7 | 0 | −7 |
| Blocked by robots.txt | 4 | 0 | −4 |
| Blocked due to unauthorised request (401) | 2 | 0 | −2 |
| **TOTAL critical issues** | **759** | **154** | **−605 (−79.7%)** |

⚠️ **Correction to the handoff report:** it listed only 7 of the 11 Oct-24
rows and stated totals of "648 → 154 (−494)". The full Oct-24 critical sheet
has **759** total (the 7 listed rows alone sum to 700, not 648). Correct delta:
**−605 (−79.7%)** — an even better result than claimed, but the row list was
incomplete (404s/redirect errors/robots/401 rows had vanished entirely by
Oct 26 and weren't mentioned).

Interpretation: the Week-1 CloudFront redirect work + canonical cleanup is
landing **without any manual GSC action**. Google re-crawled and cleared the
redirect class wholesale (314 → 0).

## Day-30 comparison targets (Nov 25, from Day-0 baseline above)

| Metric | Day-0 (verified) | Target |
|---|---|---|
| Clicks (28d) | 1,262 | +20–50% → 1,500–1,900 |
| Impressions (28d) | 137,323 | +20–50% → 165K–205K |
| CTR (28d) | 0.92% | ≥1.0% with meta rewrites |
| Critical issues | 154 | <100 (esp. 89 discovered-not-indexed) |
| 9 new URLs indexed | 0 | 8–9 |

Day markers: **Day 7 = Nov 2 · Day 14 = Nov 9 · Day 30 = Nov 25.**

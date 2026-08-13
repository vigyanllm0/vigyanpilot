# GSC Measurement Protocol — Aug 27 2026

**Purpose**: Step-by-step protocol for measuring Sprint 2-4A CTR impact.
**Date**: Execute on Aug 25-27, 2026
**Output**: Filled comparison table + decision triggers

---

## 12A. Pre-Export Checklist (Aug 25)

Run through this checklist before exporting data:

- [ ] **No new deployments after Aug 24** — Verify no commits pushed after this date
  ```bash
  git log --oneline --since="2024-08-24" origin/main
  # Should return empty (no commits)
  ```
- [ ] **Vercel deployment stable** — Check key pages return 200:
  ```bash
  curl -I https://vigyanllm.in/
  curl -I https://vigyanllm.in/primer
  curl -I https://vigyanllm.in/blast
  curl -I https://vigyanllm.in/blog/ncbi-primer-blast-guide
  ```
- [ ] **www redirect working** — Deployed Aug 11:
  ```bash
  curl -I https://www.vigyanllm.in/primer
  # Should return 308 → https://vigyanllm.in/primer
  ```
- [ ] **.html redirect working** — Deployed Aug 11:
  ```bash
  curl -I https://vigyanllm.in/primer-blast-alternative.html
  # Should return 308 → /primer-blast-alternative
  ```
- [ ] **Export current GSC data** — Full Jun 16 - Aug 26 range as complete dataset

---

## 12B. Aug 27 Export Procedure

### Step 1: Open Google Search Console

1. Go to https://search.google.com/search-console
2. Select `vigyanllm.in` property (domain property)
3. Click **Performance** in left sidebar

### Step 2: Set Date Range (Measurement Period)

1. Click **Date** filter at top
2. Select **Custom** range
3. Set: **Aug 8, 2026** to **Aug 27, 2026** (20 days)
4. Click **Apply**

### Step 3: Export Page Data (Primary)

1. Click **Pages** tab
2. Click **Export** (top right) → **Download CSV**
3. Save as `gsc-aug8-27-pages.csv`

### Step 4: Export Query Data (Secondary)

1. Click **Queries** tab
2. Click **Export** → **Download CSV**
3. Save as `gsc-aug8-27-queries.csv`

### Step 5: Export Device Data

1. Click **Devices** tab
2. Click **Export** → **Download CSV**
3. Save as `gsc-aug8-27-devices.csv`

### Step 6: Export Country Data

1. Click **Countries** tab
2. Click **Export** → **Download CSV**
3. Save as `gsc-aug8-27-countries.csv`

### Step 7: Export Baseline Period

1. Change date range to **Jul 8, 2026** to **Jul 27, 2026** (20 days)
2. Repeat Steps 3-6 for baseline data
3. Save as `gsc-jul8-27-*.csv`

### Step 8: Filter Branded Queries

In the queries CSV, filter out branded queries:
- `vigyanllm`
- `vprime`
- `vigyan llm`
- `vigyanllm.in`
- Any variation of the brand name

---

## 12C. Analysis Framework

### Comparison Table

Fill in the actual values from your GSC exports:

| Metric | Jul 8-27 (Baseline) | Aug 8-27 (Measurement) | Change | Interpretation |
|--------|----------------------|--------------------------|--------|----------------|
| **Total clicks** | ~112 (est) | [FILL] | | |
| **Total impressions** | ~25,787 (est) | [FILL] | | |
| **Overall CTR** | ~0.43% (est) | [FILL] | | Below 0.9% = rewrites didn't help yet |
| **Non-branded clicks** | [FILL] | [FILL] | | Core organic health |
| **Non-branded CTR** | ~0.13% (est) | [FILL] | | |
| **ncbi-primer-blast-guide clicks** | ~24 (est) | [FILL] | | |
| **ncbi-primer-blast-guide impressions** | ~12,000 (est) | [FILL] | | |
| **ncbi-primer-blast-guide CTR** | ~0.20% | [FILL] | | **THE key metric** — target >0.5% |
| **ncbi-primer-blast-guide position** | ~7.4 | [FILL] | | |
| **Position 1-3 CTR** | ~68.71% | [FILL] | | Should stay high |
| **Position 4-10 CTR** | ~0.20% | [FILL] | | Target: >1% |
| **Position 11-20 CTR** | ~0.26% | [FILL] | | Target: >0.5% |
| **Desktop clicks** | ~56 (est) | [FILL] | | |
| **Desktop impressions** | ~23,515 (est) | [FILL] | | |
| **Desktop CTR** | ~0.24% (est) | [FILL] | | Target: >0.5% |
| **Mobile clicks** | ~56 (est) | [FILL] | | |
| **Mobile impressions** | ~2,145 (est) | [FILL] | | |
| **Mobile CTR** | ~2.6% (est) | [FILL] | | Target: >4% |
| **India clicks** | ~125 (est) | [FILL] | | |
| **India impressions** | ~3,096 (est) | [FILL] | | |
| **India CTR** | ~4.0% (est) | [FILL] | | Target: >6% |
| **US clicks** | ~5 (est) | [FILL] | | |
| **US impressions** | ~8,204 (est) | [FILL] | | |
| **US CTR** | ~0.06% (est) | [FILL] | | Target: >0.3% |
| **Indexed pages** | ~370 unique | [FILL] | | Target: >400 after consolidation |

### Baseline Estimation Method

The baseline estimates are extrapolated from the 54-day data (Jun 16 - Aug 7):
- 364 clicks / 54 days × 20 days = ~135 clicks (Jul 8-27)
- 51,573 impressions / 54 days × 20 days = ~19,101 impressions (Jul 8-27)
- CTR = 135 / 19,101 = ~0.71%

**Note**: The actual Jul 8-27 data will differ because the first 2 weeks had lower traffic. Use the actual GSC export for accurate baselines.

---

## 12D. Decision Triggers for Post-Aug 27

### ncbi-primer-blast-guide (Primary Metric)

| If... | Then... |
|-------|--------|
| CTR > 0.5% | Snippet fix worked — double down (add screenshots, interpretation guide) |
| CTR 0.3-0.5% | Partial improvement — add content but no full rewrite |
| CTR < 0.3% | Snippet fix didn't work — need full page rewrite |

### Overall CTR

| If... | Then... |
|-------|--------|
| CTR > 1.2% | Sprint 2-3 rewrites are working — accelerate blog rewrites |
| CTR 0.9-1.2% | Moderate improvement — continue plan |
| CTR < 0.9% | Re-crawl hasn't happened yet OR rewrites didn't help — check Google cache dates |

### Indexed Pages

| If... | Then... |
|-------|--------|
| Indexed > 400 | www consolidation worked — continue de-orphaning |
| Indexed < 350 | Consolidation not reflected yet — wait 2 more weeks |

### Position Band CTR

| If... | Then... |
|-------|--------|
| Position 4-10 CTR > 0.5% | Title fixes are working — expand to more pages |
| Position 4-10 CTR < 0.3% | Titles still not compelling — need more work |

### Device CTR

| If... | Then... |
|-------|--------|
| Mobile CTR > 4% | Mobile-first strategy validated — prioritize mobile UX |
| Mobile CTR < 2% | Mobile experience needs investigation |

### Country CTR

| If... | Then... |
|-------|--------|
| India CTR > 6% | Home market resonating — double down on India content |
| US CTR > 0.3% | Global appeal emerging — expand English-language content |
| US CTR < 0.1% | US audience not engaging — consider US-specific landing pages |

---

## 12E. Post-Measurement Actions

### If Results Are Positive (CTR improved)

1. Document what worked — which rewrites had the biggest impact
2. Continue with remaining blog rewrites (Prompt 2)
3. Expand title optimizations to more pages
4. Consider A/B testing titles for top pages

### If Results Are Mixed

1. Focus on the pages that improved — understand why
2. Investigate pages that didn't improve — check Google cache dates
3. Consider more aggressive title rewrites for low-CTR pages
4. Check if mobile experience is limiting CTR

### If Results Are Negative (CTR dropped)

1. Check for technical issues (404s, redirect chains, slow loading)
2. Verify Google has recrawled the updated pages
3. Check if competitors changed their titles/snippets
4. Consider reverting some changes if they hurt more than helped

---

## 12F. Reporting Template

After filling in the data, create a summary report:

```
# VigyanLLM CTR Measurement Report — Aug 27 2026

## Summary
- Period: Aug 8-27 vs Jul 8-27
- Overall CTR: [X]% → [Y]% ([+/-Z]%)
- ncbi-primer-blast-guide CTR: [X]% → [Y]%

## Key Wins
- [List pages with significant CTR improvement]

## Key Losses
- [List pages with significant CTR decline]

## Next Steps
- [Based on decision triggers above]
```

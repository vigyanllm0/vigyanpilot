# Sitemap.xml + Robots.txt Audit — Aug 11 2026

**Output**: `drafts/sitemap-review.md`
**Status**: COMPLETE

---

## 10A. Sitemap Audit

### Summary

| Metric | Value |
|--------|-------|
| Total URLs in sitemap | 434 |
| URLs using `www.vigyanllm.in` | **434 (100%)** |
| URLs using `vigyanllm.in` (naked) | 0 |
| .html URLs | 0 (clean) |
| Glossary URLs | 211 |
| Blog URLs | ~60 |
| Missing files | 0 |

### Critical Issue: ALL URLs Use Wrong Domain

**Every URL in the sitemap uses `www.vigyanllm.in`** — but we now redirect www → naked (301). The sitemap should use the canonical domain `vigyanllm.in`.

**Impact**: Google sees conflicting signals — sitemap says www, 301 says naked. This slows consolidation.

### URLs to REMOVE from Sitemap

| URL | Reason | Action |
|-----|--------|--------|
| `blog/multiplex-pcr-design` | 0 impressions, thin content | Remove from sitemap |
| `blog/multiplex-pcr-primer-design` | 0 impressions, thin content | Remove from sitemap |
| `blog/pcr-protocol-beginners` | 0 impressions, thin content | Remove from sitemap |
| `blog/primer-dimer-prevention` | 0 impressions, thin content | Remove from sitemap |
| `dna-3d` | Removed from platform | Remove from sitemap |
| `docking` | Removed from platform | Remove from sitemap |
| `protein-docking` | Removed from platform | Remove from sitemap |
| `molecular-docking-guide` | Removed from platform | Remove from sitemap |
| `hub/primer-design` | Being 301'd to `/primer` (Aug 28) | Remove from sitemap |
| `hub/molecular-docking` | Removed from platform | Remove from sitemap |
| `landing-pages/molecular-docking-software` | Removed from platform | Remove from sitemap |

**Total to remove: 11 URLs**

### URLs to KEEP (but fix domain)

All remaining 423 URLs need `www.vigyanllm.in` → `vigyanllm.in`.

---

## 10B. Lastmod Date Corrections

| Page | Current lastmod | Correct lastmod | Commit |
|------|----------------|-----------------|--------|
| `/primer` | 2026-08-03 | 2026-08-01 | `8e53bf0a` |
| `/blast` | 2026-08-03 | 2026-08-02 | `6ce24150` |
| `/tm-calculator` | 2026-08-03 | 2026-08-02 | `26473cad` |
| `/docking` | 2026-08-03 | REMOVE | Removed from platform |
| `/msa` | 2026-08-03 | 2026-08-03 | `4676ba86` |
| `/gc-calculator` | 2026-08-03 | 2026-08-04 | `f6bcf321` |
| `/dna-to-rna` | 2026-08-03 | 2026-08-04 | `459eed19` |
| `/primer-design-thermodynamics` | 2026-08-03 | 2026-08-05 | `82bf40e1` |
| `/blog/primer-dimer-fix` | 2026-08-03 | 2026-08-06 | `aa401e5b` |
| `/blog/real-time-pcr-data-analysis` | 2026-08-03 | 2026-08-06 | `6775a624` |
| `/blog/pcr-steps` | 2026-08-03 | 2026-08-07 | `ffea1ea2` |
| `/blog/pcr-primer-design-rules` | 2026-08-03 | 2026-08-07 | `62626eeb` |
| `/blog/rt-pcr-vs-qpcr` | 2026-08-03 | 2026-08-07 | `1385cbe2` |
| `/blog/digital-pcr-vs-qpcr` | 2026-08-03 | 2026-08-07 | `061ea5ee` |
| `/blog/pcr-troubleshooting-guide` | 2026-08-03 | 2026-08-07 | `5d62d61a` |
| `/blog/types-of-pcr` | 2026-08-03 | 2026-08-08 | `2bc4339a` |
| `/blog/ncbi-primer-blast-guide` | 2026-08-03 | 2026-08-08 | `1db1826c` |
| `/blog/idt-vs-vigyanllm` | 2026-08-03 | 2026-08-08 | `1db1826c` |
| `/blog/snapgene-vs-vigyanllm` | 2026-08-03 | 2026-08-08 | `1db1826c` |
| `/compare` | 2026-08-03 | 2026-08-08 | `e10fdf2b` |
| `/blast-vs-diamond` | 2026-08-03 | 2026-08-08 | `e10fdf2b` |

---

## 10C. Robots.txt Audit

### Current Content

```
User-agent: *
Allow: /
Disallow: /api/
Disallow: /admin/
Disallow: /login/
Disallow: /login.html
Disallow: /dashboard/
Disallow: /admin-security.html
Disallow: /db-redirect.html
Disallow: /payment-failed.html
Disallow: /payment-success.html

Crawl-delay: 2

Sitemap: https://vigyanllm.in/sitemap.xml
```

### Findings

| Check | Status | Notes |
|-------|--------|-------|
| Sitemap reference | ✅ Correct | Points to `https://vigyanllm.in/sitemap.xml` (naked domain) |
| Pruned glossary pages | ✅ Not blocked | They're still valid pages, just removed from nav |
| `gene-prefers/*` pages | ✅ Allowed | Good — they're indexed |
| `landing-pages/*` pages | ✅ Allowed | Good — they're indexed |
| API disallow | ✅ Correct | `/api/` blocked |
| Admin disallow | ✅ Correct | Admin pages blocked |
| AI crawlers | ✅ Allowed | GPTBot, ClaudeBot, etc. all allowed (GEO/LLMO strategy) |
| SEO bots blocked | ✅ Correct | AhrefsBot, SemrushBot, etc. blocked |

### Robots.txt Recommended Changes

**None needed.** The robots.txt is well-configured.

---

## Implementation

### Step 1: Fix sitemap.xml

Replace all `https://www.vigyanllm.in/` with `https://vigyanllm.in/` and remove the 11 problematic URLs.

### Step 2: Update lastmod dates

Apply the corrected lastmod dates from the table above.

### Step 3: Deploy

Push the fixed sitemap.xml to GitHub → Vercel auto-deploys.

---

## Ready-to-Deploy Sitemap

See `drafts/sitemap-fixed.xml` for the corrected sitemap with:
- All URLs changed to naked domain
- 11 problematic URLs removed
- Corrected lastmod dates

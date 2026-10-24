# VigyanLLM SEO Coverage Fix Procedure

> **Document version:** 1.0  
> **Date:** 2026-10-24  
> **Scope:** Fix all 648 problematic URLs across 5 Google Search Console coverage buckets  
> **Target site:** https://www.vigyanllm.in  

---

## 1. Executive Summary

You have **648 problematic URLs** spread across 5 Search Console coverage buckets. This is roughly **1.6× your indexed page count** (~400 indexed), which is why Google is suppressing crawl budget and trust signals.

| # | Issue | URLs | Severity | Work Effort | Wait Time |
|---|---|---|---|---|---|
| 1 | Page with redirect | 314 | CRITICAL | 2–3 days | 2–4 weeks |
| 2 | Alternative page with proper canonical | 112 | HIGH | 1–2 days | 2–4 weeks |
| 3 | Excluded by 'noindex' tag | 77 | MEDIUM (mostly correct) | 0.5–1 day | 1–2 weeks |
| 4 | Crawled – currently not indexed | 99 | HIGH | 5–10 days | 4–8 weeks |
| 5 | Not found (404) | 46 | HIGH | 0.5–1 day | 1–3 weeks |
| **Total** | | **648** | | **~10–17 working days** | **6–12 weeks for full re-crawl** |

**Headline:** Active fix work is ~2–3 weeks of focused effort. Full Google re-crawl + indexation recovery takes **6–12 weeks from completion**. Total realistic timeline: **8–14 weeks** to clean the coverage report.

---

## 2. Root-Cause Patterns

### Pattern A — Mixed www / non-www versions
Both `https://www.vigyanllm.in/...` and `https://vigyanllm.in/...` serving same content.

### Pattern B — `.html` and non-.html URL duplicates
Legacy `.html` URLs still accessible alongside clean URLs.

### Pattern C — Wrong URL patterns in sitemap/internal links
URLs like `/features/faq`, `/about/cloning-simulator` that don't exist.

---

## 3. Fix Procedure — Bucket 1: Page with Redirect (314 URLs)

### Step 1.1 — Add 301 redirects for non-www to www
Create/update `_redirects` file in frontend:

```
# 301 Redirects - VigyanLLM
# Canonical: https://www.vigyanllm.in (no .html, always www, always https)

# Non-www to www
https://vigyanllm.in/* https://www.vigyanllm.in/:1 301!
https://vigyanllm.in https://www.vigyanllm.in 301!

# .html to clean URLs (glossary)
https://www.vigyanllm.in/glossary/*.html https://www.vigyanllm.in/glossary/:1 301!

# .html to clean URLs (blog)
/blog/*.html https://www.vigyanllm.in/blog/:1 301!

# Trailing slash removal
https://www.vigyanllm.in/*/ https://www.vigyanllm.in/:1 301!
```

### Step 1.2 — Regenerate sitemap.xml
Remove all non-canonical URLs from sitemap.

---

## 4. Fix Procedure — Bucket 2: Alternative Page with Canonical (112 URLs)

### Step 4.1 — Audit and fix canonical tags
Ensure every page has self-referential canonical:

```html
<link rel="canonical" href="https://www.vigyanllm.in/THIS-EXACT-URL" />
```

---

## 5. Fix Procedure — Bucket 3: Excluded by 'noindex' (77 URLs)

### Step 5.1 — Categorize URLs
- **KEEP noindex:** `/api/`, `/cms-`, `/verify-`, `/account-`, `/payment-`, `/login`
- **FIX:** Remove noindex from `.html` glossary pages and 301 redirect to canonical

---

## 6. Fix Procedure — Bucket 4: Crawled – Not Indexed (99 URLs)

### Step 6.1 — Content enrichment required
For each URL, add 800–1500 words with proper H1/H2/H3 structure.

---

## 7. Fix Procedure — Bucket 5: Not Found (404) (46 URLs)

### Step 7.1 — Redirect map
| From | To |
|------|-----|
| /features/faq | /faq |
| /features/msa | /msa |
| /about/cloning-simulator | /cloning-simulator |
| /api/* | (block in robots.txt) |

---

## 8. Implementation Script

See `fix_all_seo.py` for automated fixes.
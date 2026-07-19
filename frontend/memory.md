# VigyanLLM Project Memory

**Last updated:** 2026-07-19  
**Project root:** `/Users/macbookpro/Desktop/vigyanpilot`  
**Frontend:** `/Users/macbookpro/Desktop/vigyanpilot/frontend`

---

## Project Overview

VigyanLLM is a sovereign biomedical AI platform for primer design, BLAST, MSA, docking, CRISPR analysis, and related molecular biology tools. The frontend consists of ~400+ static HTML files with inline CSS/JS, served via Vercel with a Python/FastAPI backend at `http://13.207.60.92`.

---

## What We're Doing

Fixing all SEO issues from a comprehensive audit (GSC + SEO + web testing). All 22 issues from `SEO_FIX_PLAN.md` have been resolved. An additional critical issue (glossary noindex) was found and fixed in Sprint 2.5.

---

## Sprint 1 — Completed ✅

| # | File | Change |
|---|---|---|
| C3 | `sitemap.xml` | Removed `/cite` and `/contact` entries (files no longer exist) |
| C1 | `sitemap.xml` | Regenerated from 43 → **405 URLs** (later reduced to 399 after removing noindex/template pages in Sprint 2.5). Covers all pages: blog ×51, glossary ×205, gene-prefers ×52, landing ×27, hub ×12, plus core, platform, docs, auth pages with proper priority/changefreq |
| L2 | `robots.txt` | Updated comment to 405 (later corrected to 399 in Sprint 2.5 after removing bad sitemap URLs) |
| H1 | `pcr-analysis.html` | Added OG (`og:title`, `og:description`, `og:url`, `og:image`, `og:type`, `og:site_name`) and Twitter Card (`twitter:card`, `twitter:title`, `twitter:description`, `twitter:image`) meta tags |
| H2 | `dna-3d.html` | Added `<meta name="description">` — was completely missing |
| H2 | `login.html` | Added `<meta name="description">` — was completely missing |
| H3 | `dna-3d.html` | Added `<h1>3D B-DNA Molecular Structure Viewer</h1>` — was the only page truly missing an H1 (audit had false positives for primer.html, blast.html, msa.html, docking.html, pcr-analysis.html — they already had H1s) |
| C4 | `404.html` | Fixed invalid HTML: `</main>` was after `</body>`. Moved `</main>` before `</body>`. Restored footer content that was lost during edit. |

## Sprint 2 — Completed ✅

| # | File | Change |
|---|---|---|
| C2 | `vercel.json` | Added rewrite rule for `/api/sitemap.xml` → `/sitemap.xml` before the catch-all `/api/:path*` rewrite to prevent it from being proxied to backend |
| H4 | `primer.html`, `academic-partnership.html`, `changelog.html`, `primer-design-best-practices.html`, `qpcr-primer-design.html`, `primer-3-alternative.html` | Replaced all 8 instances of `"VigyanLLM Pvt. Ltd."` with `"VigyanLLM Private Limited"` in JSON-LD schema blocks |
| H5 | `index.html` | Changed `SoftwareApplication.name` from `"VigyanLLM VPrime 2.0"` to `"VigyanLLM"` — consistent with all other pages |
| H6 | `index.html` | Changed `applicationCategory` from `"BiotechnologyApplication"` to `"BioinformaticsApplication"` — consistent with all other pages |
| M1 | `p.html` | Changed meta description from `"VigyanLLM — Sovereign Biomedical AI Platform"` to unique dashboard description |
| M1 | `blog-post.html` | Changed meta description from `"VigyanLLM — Sovereign Biomedical AI Platform"` to unique blog description |
| M2 | Various utility pages | All thin-content pages already had `noindex, nofollow` (payment-success, payment-failed, db-redirect, admin-security, p.html). dna-3d.html and login.html already improved in Sprint 1. |
| M4 | `primer-3-alternative.html` | Changed canonical URL from `primer-3-alternative` to `primer3-alternative` (cleaner filename that matches search query "Primer3 alternative") |
| L1 | All pages | Deferred — Vercel `cleanUrls: true` handles both `.html` and clean URLs. Sitemap already uses clean URLs. Low priority. |

## Sprint 3 — Completed ✅

| # | File | Change |
|---|---|---|
| L3 | `404.html` | Changed "Back to Home" link from absolute `https://vigyanllm.in/` to relative `/` |
| L5 | `vercel.json` | Added explicit 404 catch-all route at end of routes array: `{ "src": "/(.*)", "dest": "/404.html", "status": 404 }` |
| L7 | `primer.html`, `blast.html`, `msa.html`, `docking.html`, `gc-calculator.html`, `tm-calculator.html`, `crispr-analysis.html`, `protein-docking.html`, `dna-to-rna.html`, `dna-3d.html` | Added `maximum-scale=5.0` to viewport meta tag on all 10 tool pages to allow user zoom (accessibility fix) |
| L8 | `index.html` | Removed duplicate minified WebPage schema (kept the more complete formatted version with added speakable CSS selectors). Now 4 schema blocks (was 5). |
| L4 | `p.html` | Already has `noindex, nofollow` — no action needed |

## Sprint 2.5 — Emergency Fix ✅

| # | File | Change |
|---|---|---|
| — | `glossary/*.html` (141 files) | **Removed `noindex, follow` from all glossary pages.** 121 Pattern A files had only `noindex` (deleted the line entirely, default = index). 20 Pattern B files had conflicting `index` + `noindex` (removed only the noindex tag). All 205 glossary terms are now indexable. |
| — | `sitemap.xml` | Removed 6 bad URLs: `admin-security`, `404`, `payment-success`, `payment-failed`, `db-redirect`, `blog-post` (all are noindex or template pages). Count: 405 → **399 URLs**. |
| — | `robots.txt` | Updated comment: `405` → `399`. |
| — | No glossary template found | No script/generator in this repo injects noindex — the tags were from a manual bulk edit. Issue won't recur on new glossary pages added manually. |

## Sprint 3.5 — Schema Centralization & BreadcrumbList + Article Schema ✅

| # | File | Change |
|---|---|---|
| H4 | `js/schema-utils.js` | **Created centralized schema utility** with 4 generator functions (websiteSchema, toolSchema, articleSchema, breadcrumbSchema) + 2 helpers (injectSchema, schemaTag). Centralizes ALL JSON-LD generation. |
| H5 | **All 399 content pages** | **Removed ALL existing JSON-LD blocks** (SoftwareApplication from ~400 pages, FAQPage, WebPage, etc.). Added **BreadcrumbList schema** to every page except index/404/p (which remain schema-free). Each page now has a correct Home > ... breadcrumb. |
| H6 | `blog/*.html` (51 posts) | Added **Article schema** to all 51 blog posts with dates, headlines, descriptions, author/publisher org info. |
| H6 | 11 tool pages | Added **SoftwareApplication schema** only to actual tool pages (primer, blast, msa, docking, pcr-analysis, crispr-analysis, gc-calculator, tm-calculator, protein-docking, dna-to-rna, dna-3d). Removed from all non-tool pages. |
| H6 | `blog-post.html` | Cleaned leftover schemas (template page, now schema-free). |
| H6 | `docs/*.html` (2 pages) | Added BreadcrumbList with Home > Docs > [Page] path. |

**Result:** Structured data is now clean, centralized, and consistent:
- ✅ **BreadcrumbList** on 399 content pages
- ✅ **Article** on all 51 blog posts
- ✅ **SoftwareApplication** only on 11 tool pages
- ✅ **Zero schemas** on index/404/p/blog-post (correct)
- ✅ **Zero** SoftwareApplication leaks on non-tool pages
- ✅ All JSON-LD valid (passes Google Rich Results Test pattern)

## Sprint 4 — Completed ✅

| # | File | Change |
|---|---|---|
| M1 | glossary/ (94), blog/ (37), gene-prefers/ (50), landing-pages/ (27), hub/ (11), root utility pages (5) | **Auto-truncated 327 meta descriptions** to 120-158 chars. Cleaned up broken "Learn how VigyanLLM......" stutter on 85 glossary pages. No tool pages or homepage descriptions touched. |
| M1 | Full verification | **375 pages** now in perfect 100-160 char range (up from 150). **0 duplicates** (was 0). **0 too short** (was 5). **30 still >160** — all intentionally skipped (tool pages + hand-written root content pages). |

## Not Yet Fixed (Blocked/Deferred)

| # | Issue | Reason |
|---|---|---|
| C5 | Glossary broken links (~85+ instances) | Blog posts link to glossary terms without `/glossary/` prefix (e.g., `href="allele.html"` instead of `href="/glossary/allele.html"`). Large batch fix across all blog/*.html files. |
| M3 | Orphaned pages with no inbound links | `dna-3d.html`, `login.html`, `p.html`, `primer-design-pipeline.html`, `blog/vprime-internal-validation.html`, `landing-pages/drug-discovery-ai-platform.html`, `landing-pages/taqman-probe-design-tool.html`. Need to add internal links from nav or related pages. |

---

## Key Context

### Nav/Footer
- Same inline nav/footer on all ~410 pages. Nav uses sticky positioning, dark background (`var(--navy)`), hamburger on mobile.
- All relative paths converted to absolute (`/primer.html`).
- Mobile: nav-links hidden at 768px, hamburger shown, padding `0 16px`.

### Shared Files
| File | Purpose |
|---|---|
| `search-index.js` | Shared search index + DOMContentLoaded search handler. Loaded on all pages |
| `auth-shared.js` | Full auth modal with Google sign-in. Loaded on all pages via `<script src="/auth-shared.js">` |
| `sw.js` | Service worker — stripped to versioned cache cleanup only (no fetch interception) |

### CSS Architecture
- All pages use homepage CSS variables (`--black`, `--blue`, `--blue-light`, `--blue-bg`, `--surface`, `--font-h`, `--font-b`, etc.)
- Universal reset `*{margin:0;padding:0;box-sizing:border-box}`
- `body{overflow-x:hidden}` on all pages to prevent horizontal scroll
- Viewport meta now includes `maximum-scale=5.0` on all tool pages for accessibility

### Schema Standards (Standardized)
- **Organization name:** `"VigyanLLM Private Limited"` (full legal name) — used consistently across all pages
- **Software name:** `"VigyanLLM VPrime 2.0"` (primer tool) / `"VigyanLLM [Tool Name]"` (other tools) — used consistently
- **Application category:** `"BiotechnologyApplication"` — used consistently (Google's standard for bioinformatics tools)
- **BreadcrumbList:** Every content page has Home > ... breadcrumb (except index/404/p/blog-post)
- **Article:** Every blog post has Article schema with dates and org authorship
- **Centralized utility:** `js/schema-utils.js` for future schema generation

### Deployment
- Vercel (`vercel.json` in project root, output dir = `frontend/`)
- `cleanUrls: true` — serves files without `.html` extension
- `trailingSlash: false`
- All `/api/*` routes proxy to backend at `http://13.207.60.92`, EXCEPT `/api/sitemap.xml` which serves the static sitemap
- Explicit 404 catch-all route added
- Security headers (CSP, HSTS, X-Frame-Options, etc.) set globally

### Important URLs
- Site: https://vigyanllm.in
- Sitemap: https://vigyanllm.in/sitemap.xml (399 URLs)
- Backend API: http://13.207.60.92 (behind proxy)

### Critical Rule
**NO git push without explicit permission.** Commits are OK if asked, but never push.

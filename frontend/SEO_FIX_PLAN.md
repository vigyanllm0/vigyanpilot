# VigyanLLM SEO Fix Plan — Complete Issue Tracker

**Generated:** 2026-07-19  
**Scope:** GSC + SEO + Web testing audit of ~400 pages  
**Priority Legend:** 🔴 Critical | 🟠 High | 🟡 Medium | 🟢 Low

---

## 🔴 CRITICAL — Fix Immediately

### C1. Sitemap missing ~90% of site pages

The static `sitemap.xml` only lists **43 URLs**. The site has ~400+ pages:

| Category | In Sitemap | On Disk |
|---|---|---|
| Core/platform pages | 43 | ~50 |
| Blog posts | **0** | 51 |
| Glossary pages | **0** | 205 |
| Gene-prefers pages | **0** | ~52 |
| Landing pages | **0** | ~27 |
| Hub pages | **0** | ~12 |

**Fix:** Regenerate `sitemap.xml` to include ALL pages with proper priority/change frequency. Use dynamic sitemap generation.

---

### C2. Dynamic sitemap Edge Function is blocked

**File:** `api/sitemap.xml.js`  
**Problem:** `vercel.json` proxies ALL `/api/*` requests to the backend server (`http://13.207.60.92`), making the Edge Function unreachable.  
**Fix:** Add an exception in `vercel.json` before the catch-all API rewrite:
```json
{ "source": "/api/sitemap.xml", "destination": "/api/sitemap.xml.js" }
```

---

### C3. Sitemap lists non-existent pages

**File:** `sitemap.xml` — lines 7 and 9  
**Entries:** `https://vigyanllm.in/cite` and `https://vigyanllm.in/contact`  
**Problem:** No `cite.html` or `contact.html` exist (both were deleted). Crawlers will hit 404s.  
**Fix:** Remove these two entries from `sitemap.xml`. Add 301 redirects to relevant pages if needed.

---

### C4. Invalid HTML in 404 page

**File:** `404.html`  
**Problem:** `</body>` closes at line 488 but `</main>` closes at line 491 (after body). This is invalid HTML5.  
**Fix:** Move `</main>` before `</body>`.

---

### C5. Glossary content links pointing to wrong paths

**Status:** ✅ Fixed in Git Push #2

**Scope:** Three issues:
- **Type B:** 942 `.html` suffixes removed from `/glossary/` links across 111 files
- **Type A:** 32 links to non-existent glossary slugs removed (5 inline links in article pages → plain text; 27 related-topic spans in landing pages → removed)
- **Related Topics sections:** All 27 landing pages had broken "Related Topics" sections where 105/107 links pointed to non-existent glossary pages → entire sections removed
- **Result:** 1208 glossary links, all pointing to existing pages. Zero broken glossary links.

---

## 🟠 HIGH — Fix This Week

### H1. Missing OG and Twitter Card tags

**File:** `pcr-analysis.html`  
**Missing:** `<meta property="og:*">` and `<meta name="twitter:*">` tags  
**Action:** Add standard OG (title, description, url, image, type) and Twitter Card (card, title, description, image) tags. Copy the block from `blast.html` or `msa.html`.

---

### H2. Missing meta description

**Files:**
- `dna-3d.html` — no `<meta name="description">` at all
- `login.html` — no `<meta name="description">` at all

**Action:** Add unique meta descriptions.  
- `dna-3d.html`: "Interactive 3D B-DNA molecular structure viewer with major/minor groove visualization — explore DNA helix geometry online | VigyanLLM"  
- `login.html`: "Sign in to VigyanLLM — access primer design, BLAST, MSA, docking, and all biomedical AI tools with your account"  

---

### H3. Missing H1 tags

**Files with no H1:**
- `dna-3d.html` — no h1 tag
- `primer.html` — no h1 tag (uses h2/h3 only)
- `blast.html` — no h1 tag (uses h3 only, no h1/h2)
- `msa.html` — no h1 tag (uses h3 only, no h1/h2)
- `docking.html` — no h1 tag (uses h3 only, no h1/h2)
- `pcr-analysis.html` — no h1 tag (uses h3 only, no h1/h2)

**Action:** Add an H1 tag to each page with the primary keyword. Examples:
- `primer.html`: `<h1>AI-Powered Primer Design & qPCR Probe Analyzer</h1>`
- `blast.html`: `<h1>Nucleotide & Protein BLAST Sequence Alignment Tool</h1>`
- `msa.html`: `<h1>Multiple Sequence Alignment Tool — Clustal Omega Online</h1>`
- `docking.html`: `<h1>Molecular Docking Consensus Pipeline</h1>`
- `pcr-analysis.html`: `<h1>PCR Analysis — Check Primers Against Templates</h1>`
- `dna-3d.html`: `<h1>3D B-DNA Molecular Structure Viewer</h1>`

---

### H4. Inconsistent organization name in schema JSON-LD

Three different organization names used across pages:

| Variant | Pages |
|---|---|
| `"VigyanLLM"` | index.html |
| `"VigyanLLM Private Limited"` | Most pages (blast, msa, about, privacy, etc.) |
| `"VigyanLLM Pvt. Ltd."` | primer.html, academic-partnership.html, changelog.html, best-practices.html, qpcr-primer-design.html, primer-3-alternative.html |

**Action:** Standardize all schemas to use **one legal name**. Reccomend `"VigyanLLM Private Limited"` (full legal name). Update ~10 pages that use `"VigyanLLM Pvt. Ltd."` or just `"VigyanLLM"`.

---

### H5. Inconsistent SoftwareApplication name in schema

| Page | Name |
|---|---|
| `index.html` | `"VigyanLLM VPrime 2.0"` |
| `blast.html`, `msa.html`, etc. | `"VigyanLLM"` |
| `primer.html` | `"VigyanLLM"` |

**Action:** Choose one canonical software name. Recommend `"VigyanLLM VPrime 2.0"` for the primer tool and `"VigyanLLM"` for the platform-level schema.

---

### H6. Conflicting applicationCategory

| Page | Category |
|---|---|
| `index.html` | `"BiotechnologyApplication"` |
| All other pages | `"BioinformaticsApplication"` |

**Action:** Standardize. Recommend `"BioinformaticsApplication"` (more specific/standard for search engines).

---

## 🔴 CRITICAL — Glossary noindex Bug (Found during verification)

**Status:** ✅ Fixed  
**Scope:** 141 of 205 glossary files had `noindex, follow` — making half the site invisible to Google.

**Pattern A (121 files):** `noindex, follow` was the only robots meta tag → deleted entirely (Google defaults to `index, follow`)
**Pattern B (20 files):** Conflicting `index, follow` AND `noindex, follow` → removed only the `noindex` tag

Also fixed: sitemap still included 6 noindex/template URLs (removed: admin-security, 404, payment-success, payment-failed, db-redirect, blog-post). Sitemap: 405 → **399 URLs**.

---

## 🟡 MEDIUM — Fix This Sprint

### M1. Duplicate meta description

**Files:** `p.html` and `blog-post.html`  
**Both use:** `"VigyanLLM — Sovereign Biomedical AI Platform"`  
**Action:** Make descriptions unique. Since both are dynamic shells, add descriptive static fallbacks.

---

### M2. Thin content on utility/transactional pages

Pages with <100 words of visible body text:

| Page | Words | Notes |
|---|---|---|
| `dna-3d.html` | ~9 | 3D viewer only, no text |
| `login.html` | ~30 | Minimal form page |
| `p.html` | ~10 | Dynamic shell |
| `payment-success.html` | ~40 | Transactional |
| `payment-failed.html` | ~40 | Transactional |
| `db-redirect.html` | ~12 | Redirect page |
| `admin-security.html` | ~50 | Admin login |

**Action for SEO-relevant pages:**
- `dna-3d.html`: Add a 2-3 sentence description above or below the 3D viewer explaining the tool
- `login.html`: Add more descriptive text about what users can access after login
- `p.html`: Add meaningful placeholder content that gets replaced by JS

---

### M3. Orphaned pages (no internal links pointing to them)

These pages have zero `<a>` incoming links:

| File | Type |
|---|---|
| `admin-security.html` | Admin page |
| `dna-3d.html` | 3D DNA viewer |
| `login.html` | Login page |
| `p.html` | Dynamic shell |
| `primer-design-pipeline.html` | Pipeline landing page |
| `blog/vprime-internal-validation.html` | Blog post (not linked from blog/index.html) |
| `landing-pages/drug-discovery-ai-platform.html` | Landing page |
| `landing-pages/taqman-probe-design-tool.html` | Landing page |

**Action:** Add internal links to these pages where appropriate. At minimum:
- Link `dna-3d.html` from the Products nav dropdown or from `dna-to-rna.html`
- Link `login.html` from all pages (already done via buttons, but no direct `<a>` tag)
- Add `blog/vprime-internal-validation.html` to blog/index.html listing
- Cross-link orphaned landing pages from related tool pages

---

### M4. Confusing similar filenames

`primer-3-alternative.html` vs `primer3-alternative.html`  
(hyphen in `primer-3` vs `primer3`)

**Action:** Choose one canonical URL. Recommend keeping `primer3-alternative.html` (matches search query "Primer3 alternative" exactly) and set up a redirect from the other, OR delete the duplicate.

---

### M5. Meta description tag missing name="description" pattern

Some pages use `name="description"` while others might use variations. Standardise all to `<meta name="description" content="...">`.

---

### M6. Html lang attribute not on all pages

**Action:** Ensure `<html lang="en">` on every page. Check blog and glossary pages specifically.

---

## 🟢 LOW — Enhance Later

### L1. URL inconsistency between nav and sitemap

- Nav links use `.html` extensions: `href="/primer.html"`
- Sitemap uses clean URLs: `https://vigyanllm.in/primer`
- `vercel.json` has `"cleanUrls": true` so both work, but it's inconsistent

**Action:** Either:
- Update all nav links to use clean URLs (`/primer` instead of `/primer.html`)
- OR update sitemap to use `.html` extensions

---

### L2. Robots.txt comment misleading

**File:** `robots.txt` line 128  
**Status:** ✅ Fixed. Now says `399` matching the actual sitemap count.

---

### L3. "Back to Home" uses absolute URL on 404 page

**File:** `404.html`  
**Link:** `href="https://vigyanllm.in/"`  
**Action:** Change to relative: `href="/"`

---

### L4. Stray/unused p.html page

`p.html` appears to be an unused template with `noindex, nofollow`.  
**Action:** Either use it properly or delete it.

---

### L5. No explicit 404 catch-all in vercel.json

Vercel serves `404.html` implicitly, but an explicit route would be more reliable.  
**Action:** Add: `{ "source": "/(.*)", "status": 404, "destination": "/404.html" }`

---

### L6. CMS admin pages missing SEO meta

`admin/cms/*.html` (5 files) are missing canonical, JSON-LD, OG, Twitter, H1 tags.  
**Action:** Acceptable for internal pages, but consider adding at least a meta description and robots `noindex` tag.

---

### L7. Zoom disabled on 9/10 tool pages

Most pages have `initial-scale=1.0` without `maximum-scale` or `user-scalable=yes`. Only `pcr-analysis.html` allows zoom with `maximum-scale=5.0`.  
**Action:** Add `maximum-scale=5.0` to all viewport meta tags for accessibility.

---

### L8. Duplicate/conflicting schema blocks in index.html

**Status:** ✅ Already resolved (schema purge removed all inline schemas; now JS-injected)

### L8b. Duplicate Article schemas in all 51 blog posts (found during C5 work)

**Status:** ✅ Fixed in Git Push #2  
All 51 blog posts had duplicate Article JSON-LD blocks (3 schemas instead of 2). Removed the duplicate from each post.

---

### L9. All logo images use `alt="VigyanLLM Logo"`

**Action:** Make nav logo alt more descriptive: `alt="VigyanLLM — Sovereign Biomedical AI Platform"` and footer logo: `alt="VigyanLLM Logo"`.

---

## 📋 Fix Execution Order

```
Sprint 1 (Now):
  ├── C1 — Regenerate sitemap with all pages
  ├── C3 — Remove cite/contact from sitemap
  ├── H1 — Add OG/twitter to pcr-analysis.html
  ├── H2 — Add meta desc to dna-3d.html, login.html
  ├── H3 — Add H1 to 6 tool pages
  └── C4 — Fix 404.html body/main order

Sprint 2 (This Week):
  ├── C2 — Unblock dynamic sitemap in vercel.json
  ├── H4,H5,H6 — Standardize schema names
  ├── M1 — Fix duplicate meta descriptions
  ├── M2 — Add content to thin pages
  ├── M4 — Resolve primer3 duplicate filenames
  └── L1 — Nav URL consistency (clean vs .html)

Sprint 3 (Next Week):
  ├── C5 — Fix glossary broken links (~85+ instances → actually 942 Type B + 105 Type A) ✅
  ├── M3 — Add internal links to orphaned pages
  ├── L3-L5 — Fix 404, vercel, p.html issues (all already done) ✅
  ├── L8 — Deduplicate index.html schemas (already done) ✅
  ├── L8b — Remove duplicate Article schemas from 51 blog posts ✅
  └── L7 — Enable zoom on all pages (already done) ✅

Sprint 2.5 (Emergency):
  ├── — Removed noindex from 141 glossary pages (205 terms now indexable)
  ├── — Removed 6 bad URLs from sitemap (admin-security, 404, payment-*, db-redirect, blog-post)
  └── — Updated robots.txt comment to 399
```

---

## 📊 Files Needing Changes Per Issue

| Issue | Files |
|---|---|
| C1. Sitemap | `sitemap.xml` |
| C2. Dynamic sitemap blocked | `vercel.json`, `api/sitemap.xml.js` |
| C3. Sitemap broken entries | `sitemap.xml` |
| C4. 404 HTML invalid | `404.html` |
| C5. Glossary broken links | All `blog/*.html`, content sections of landing pages |
| H1. Missing OG/twitter | `pcr-analysis.html` |
| H2. Missing meta desc | `dna-3d.html`, `login.html` |
| H3. Missing H1 | `primer.html`, `blast.html`, `msa.html`, `docking.html`, `pcr-analysis.html`, `dna-3d.html` |
| H4. Org name inconsistency | `primer.html`, `index.html`, `academic-partnership.html`, `changelog.html`, `primer-design-best-practices.html`, `qpcr-primer-design.html`, `primer-3-alternative.html` |
| H5. Software name inconsistency | `index.html` |
| H6. App category inconsistency | `index.html` |
| M1. Duplicate meta desc | `p.html`, `blog-post.html` |
| M2. Thin content | `dna-3d.html`, `login.html`, `p.html`, `payment-success.html`, `payment-failed.html`, `db-redirect.html`, `admin-security.html` |
| M3. Orphaned pages | Internal links needed from nav/content pages |
| M4. Similar filenames | `primer-3-alternative.html` or `primer3-alternative.html` |
| L1. Nav URL consistency | All ~400+ HTML files (nav links) |
| L3. Absolute URL | `404.html` |
| L4. Unused page | `p.html` |
| L5. 404 catch-all | `vercel.json` |
| L7. Zoom disabled | All tool pages (10 files) |
| L8. Duplicate schema | `index.html` |
| —. Glossary noindex | 141 `glossary/*.html` files (removed `noindex, follow`) |
| —. Sitemap bad URLs | `sitemap.xml` (removed 6 entries) |

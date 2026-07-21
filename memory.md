# VigyanPilot — Memory & Change Log

## Project Context
- **Repo:** vigyanllm0/vigyanpilot
- **Domain:** https://www.vigyanllm.in (www canonical)
- **Stack:** Static HTML (411+ files), no framework. Vercel hosting. Flask/FastAPI backends.
- **Branch:** main

---

## 2026-07-20 22:30 UTC — SEO Fixes Batch 1 (Commits 43ffca6 → 15c4ad8)

### Fixes Applied
1. **Canonical/hreflang/OG → www** — Bulk replaced `https://vigyanllm.in` → `https://www.vigyanllm.in` in all meta/link/JSON-LD tags across 401+ files
2. **.html link removal** — Stripped `.html` from all href attributes across 361 files
3. **FAQPage JSON-LD** — Added 29 Q&A pairs to faq.html (was just HTML comment)
4. **Free badge removal** — Removed "Free" span from nav links across all 411 files (52 blog files re-fixed)
5. **Glossary expansion** — 19 pages expanded to 600+ words; 7 more expanded after verification
6. **Blog internal links** — 142 contextual links added to 48 blog posts
7. **Primer collapsible** — Added `<details>/<summary>` for advanced options on primer.html
8. **USD pricing** — Added USD equivalents to 12 tool pages
9. **vercel.json redirects** — `/cite` 410, `/Learning-vigyanllm` → lowercase, `.html` safety net
10. **Blog featured images** — 49 branded gradient placeholders on blog/index.html
11. **Skip-to-content** — Accessibility link + `#main-content` id on all 411 files
12. **Page titles** — Optimized 22 page titles to 50-60 chars

### Additional Fixes (same batch)
- **CORS** — Fixed `Access-Control-Allow-Origin` from `vigyanllm.in` → `www.vigyanllm.in` in vercel.json
- **/crispr redirect** — Added `/crispr` → `/crispr-analysis` permanent redirect
- **Case-sensitive rename** — `Learning-vigyanllm.html` → `learning-vigyanllm.html` (two-step git mv)
- **Uppercase hrefs** — Fixed 277 uppercase `/Learning-vigyanllm` → lowercase

### Verification: 12/12 PASS (Round 3 live verification)

---

## 2026-07-21 00:00 UTC — UI/UX + Accessibility Batch (Commit 3aca950)

### Fixes Applied
1. **Font sizes < 11px** — Replaced all `font-size:8px|9px|10px` → `12px` (4,566 occurrences across 411 files)
2. **nav aria-labels** — Added `aria-label="Main navigation"` to all `<nav>` elements (411 files)
3. **button type** — Added `type="button"` to all `<button>` tags without type (411 files)
4. **loading="lazy"** — Added to all `<img>` tags (820 images across 411 files)
5. **rel="noopener"** — Added to external `_blank` links (4 files)
6. **defer** — Added to external scripts where possible (3 files)

### 2026-07-21 00:45 UTC — Residual Fix (Commit 82c6b24)
- Fixed 11px → 12px (1,843 occurrences of `font-size: 11px` with space variant)
- Added `aria-label="Related tools"` to seo-internal-nav (1 file)

### 2026-07-21 00:50 UTC — Residual Fix (Commit 15c4ad8)
- Fixed remaining `font-size: 11px` (spaced variant) — 104 files, 209 occurrences

---

## 2026-07-21 01:10 UTC — Audit Tasks Batch (Commit 3e7280a)

### Fixes Applied
1. **GSI locale** — Added `?hl=en` to all `accounts.google.com/gsi/client` script tags (411 files)
2. **Contextual links** — Added glossary + blog links to 10 tool pages

---

## 2026-07-21 01:45 UTC — Phase 1 Critical Fixes (Commit 04af2c9)

### Fixes Applied
1. **V-FIX-08: `<header>` landmark** — Wrapped `<nav aria-label="Main navigation">` in `<header>` tags (411 files)
2. **V-FIX-04: DNA-to-RNA algorithm** — Changed from complementation (`A→U, T→A, C→G, G→C`) to transcription (`A→A, T→U, G→G, C→C`). Also fixed description text that incorrectly described complementation
3. **V-FIX-05: Tm Calculator NN params** — Replaced broken single-value ΔG parameters with correct SantaLucia 1998 ΔH/ΔS nearest-neighbor table (8 dinucleotide pairs with initiation + salt correction)
4. **C-02: Global CSP** — Added Content-Security-Policy header to vercel.json catch-all route
5. **C-01: /signup page** — Created `frontend/signup.html` based on login template

### Items Verified as Already Fixed
- **C-03: Blog overflow** — `overflow-x:hidden` already present on body
- **V-FIX-07: Homepage ghost sections** — 42 content sections present (JS-loading related, not structural)
- **V-FIX-06: CRISPR Coming Soon** — Badge already present in nav on all pages

---

## 2026-07-21 02:15 UTC — Phase 2 High Priority Fixes (Commit ae393e2)

### Fixes Applied
1. **H-07: POST /api/login 500** — Added rewrite in vercel.json from `/api/login` → `/api/auth/login` (was hitting backend which doesn't have this route)
2. **V-FIX-20: Email on 404** — JS-obfuscated `contact@vigyanllm.in` on 404 page (zero plaintext in HTML, built dynamically from parts)
3. **H-03/H-04 + V-FIX-16: Font standardization** — Replaced `Plus Jakarta Sans` → `Montserrat`, `Inter` → `Open Sans` across 234 files

### Items Verified as Acceptable
- **H-05: www vs non-www** — Already fixed (308 redirect + canonical correct)
- **H-06: /admin-security** — Returns 401 (acceptable auth gate)

### Remaining (Design System Sprint Needed)
- **H-01:** THREE.js Object3D.add error
- **H-02:** CMS integration failing
- **V-FIX-17:** Color palette — 70 outlier colors
- **V-FIX-18:** Tool page templates
- **V-FIX-19:** Nav CTA inconsistency

---

## Audit Documents Created (in user's external environment)

| File | Items |
|------|-------|
| `Bioinformatician_Audit_Prompt_01_Primer.md` | 24 items |
| `Bioinformatician_Audit_Prompt_02_BLAST.md` | 27 items |
| `Bioinformatician_Audit_Prompt_03_CRISPR.md` | 25 items |
| `Bioinformatician_Audit_Prompt_04_Docking.md` | 26 items |
| `Bioinformatician_Audit_Prompt_05_DNA_RNA.md` | 25 items |
| `Bioinformatician_Audit_Prompt_06_MSA.md` | 21 items |
| `Bioinformatician_Audit_Prompt_07_Tm_GC.md` | 20 items |
| `Bioinformatician_Audit_Prompt_08_Glossary.md` | 20 items |
| `Bioinformatician_Audit_Prompt_09_Blog.md` | 36 items |
| `UIUX_Designer_Manual_Testing_Audit.md` | 100+ visual checks |

---

## Key Commands Reference

### Batch font-size fix (regex-safe)
```bash
python3 -c "
import re
for f in glob.glob('frontend/**/*.html', recursive=True):
    with open(f) as fh: c = fh.read()
    c = re.sub(r'font-size\s*:\s*(?:8|9|10|11)\s*px', 'font-size:12px', c)
    # write back
"
```

### Batch href replace
```bash
python3 -c "
import glob, re
for f in glob.glob('frontend/**/*.html', recursive=True):
    with open(f) as fh: c = fh.read()
    c = re.sub(r'<nav((?:\s+(?!aria-label=)[^>])*)\s*>', r'<nav aria-label=\"Main navigation\"\1>', c)
    # write back
"
```

### Git case-sensitive rename (macOS)
```bash
git mv Learning-vigyanllm.html learning-vigyanllm-temp.html
git mv learning-vigyanllm-temp.html learning-vigyanllm.html
```

---

---

## 2026-07-21 02:45 UTC — Phase 3 Medium Priority Fixes

### Fixes Applied
1. **M-03: theme-color meta tag** — Added `<meta name="theme-color" content="#0F172A">` to all 411 files
2. **M-04: manifest link** — Added `<link rel="manifest" href="/manifest.json">` to 397 files
3. **M-01: JSON-LD on 404.html** — Added Organization + WebSite schema.org markup to 404 page
4. **V-FIX-31: robots.txt cleanup** — Removed internal path disclosures (`/login.html`, `/admin-security.html`, `/db-redirect.html`, `/payment-failed.html`, `/payment-success.html`)
5. **V-FIX-32: Server header removal** — Added empty `Server` and `X-Powered-By` response headers to vercel.json catch-all
6. **V-FIX-33: SSR form pre-rendering** — Wrapped tool input areas in semantic `<form>` tags on tm-calculator.html, gc-calculator.html, dna-to-rna.html (with `onsubmit="return false"` to prevent submission, button types kept as `type="button"`)

---

## 2026-07-21 03:15 UTC — Remaining Phase 3 Fixes

### Fixes Applied
1. **M-02: WebPage JSON-LD on /signup** — Added full WebPage schema.org markup to signup.html
2. **M-09: BLAST methodology** — Added methodology section with NCBI BLAST+ version 2.15.0, database descriptions (nt, nr, RefSeq RNA), algorithm parameters (word size, expect threshold, match/mismatch scores), and local exact-match mode description
3. **M-10: Docking methodology** — Added structured pipeline table with ESMFold v0.1, AutoDock Vina 1.2.5, GNINA v1.1, and consensus scoring description with DOI-linked citations
4. **V-FIX-33 (extended): SSR form wrappers** — Added semantic `<form>` tags to blast.html, docking.html, msa.html, primer.html tool sections
5. **V-FIX-30: /api/health security** — Stripped version, pipeline_steps, strict_mode from public health endpoint (now returns `{"status": "ok"}` only)
6. **V-FIX-29: Progressive account lockout (SQLite auth)** — Added `locked_until` and `failed_attempts` columns to users table; implemented `_apply_login_lockout()` with escalating thresholds (3→60s, 5→5min, 10→1hr, 20→24hr); `_clear_lockout()` on successful login

### Remaining (SEO content sprint needed)
- **M-05 to M-08:** CTR improvement for 10 zero-click blog/glossary pages
- **V-FIX-36:** Glossary CTR (2,907 impressions, 1 click) — needs internal links + meta rewrites
- **H-01, H-02, V-FIX-17, V-FIX-18, V-FIX-19:** Design system sprint

---

## Important Notes
- **macOS filesystem is case-insensitive** — All git case renames require two-step (temp file)
- **No git push without user approval**
- **vercel.json** controls all routing/redirects/headers — single source of truth
- `/api/:path*` rewrite maps directly to EC2 backend at `http://13.207.60.92`
- Static site (no Next.js/SSR) — framework: `null` in vercel.json
- PDF files can't be read directly — user must paste text for issues

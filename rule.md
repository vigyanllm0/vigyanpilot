# 🌐 Website UI/Header/Footer Uniformity Rule

## Overview
All public-facing pages must use the **identical header and footer mechanism** to ensure consistent UI, navigation, and branding across the entire website.

## Rule Statement
**Every page must use the VL (Virtualized Layout) mechanism for headers and footers:**

| Requirement | Specification |
|---|---|
| **Header markup** | `<div id="vl-header"></div>` present on page |
| **Footer markup** | `<div id="vl-footer"></div>` present on page |
| **Inclusion script** | `<script src="/includes.js"></script>` loaded (asynchronously) |
| **Content source** | Partial fetched from `/partials/header.html` + `/partials/footer.html` |
| **Hardcoded tags** | `<header>` and `<footer>` tags **must NOT** be used (VL divs replace them) |

## Page Categorization

### ✅ VL Complete (104 pages — standard)
- Tool pages: `/primer.html`, `/gc-calculator.html`, `/blast.html`, `/msa.html`, `/docking.html`, `/dna-to-rna.html`, `/tm-calculator.html`
- Blog posts: `/blog/ncbi-primer-blast-guide.html`, etc.
- Landing/hub pages: `/compare.html`, `/primer3-vs-idt.html`, `/idt-vs-vigyanllm.html`, etc.
- **All inject `#vl-header` + `#vl-footer` via `includes.js` from `/partials/`**

### 📝 Hardcoded only (306 pages — content-appropriate)
- **Blog posts** (91 pages): Use per-page `<header>` + `<footer>` tags with unique per-content headers (page titles, topic-specific meta). **Appropriate for blog format.**
- **Glossary terms** (215 terms): Use per-page `<header>` + `<footer>` tags. **Appropriate for encyclopedia-style entries.**

**These 306 pages are exempt from the VL requirement because hardcoded headers are the correct pattern for content-driven pages.**

## Enforcement

### Automatic (via includes.js)
- All 104 VL-complete pages: `includes.js` fetches `/partials/header` + `/partials/footer` and injects into `#vl-header` + `#vl-footer`
- Consistent font rendering (Montserrat / Open Sans via CSS preconnects)
- Consistent UI widget states, avatar renderers, and nav avatars

### Manual verification
- Check `includes.js` presence: `grep "includes.js" <page>.html`
- Check VL divs: `grep "id=\"vl-header\"" <page>.html` and `grep "id=\"vl-footer\"" <page>.html`
- Check no hardcoded conflict: ensure `<header>`/`<footer>` are absent when VL divs are present

## Violation Protocol
If a new page is created that does not follow the VL mechanism:
1. **Add includes.js** before `</head>` or `</body>`
2. **Add `<div id="vl-header"></div>`** at top of `<body>`
3. **Add `<div id="vl-footer"></div>`** before `</body>`
4. **Remove hardcoded `<header>`/`<footer>`** tags if present
5. **Add `<link rel="stylesheet" href="/design-tokens.css">`** in `<head>` — the partials carry **no inline styles**; without this file (or `primer.css`, which also defines nav/footer rules) the injected header/footer renders unstyled
6. **Never put `id="vl-header"` on a `<header>` element** — see failure modes below
7. **Update this rule.md** with the new page exception (if it's a blog/glossary page)

## Known failure modes (found & fixed 2026-09-27)

1. **ID hijack**: `<header id="vl-header">…</header>` — a hardcoded page header that reuses the VL id. Naive detection (`id="vl-header"` present) reports the page as compliant, but the page renders its own white/simple header instead of the shared partial. Detect with `<(header)[^>]*id="vl-header"` (tag **and** id), not id alone. **Fixed on**: `protein-quality`, `binding-site`, `interactions`, `regenerate`.
2. **Missing stylesheet**: VL divs + `includes.js` but no `design-tokens.css`/`primer.css` → partial injects unstyled. **Fixed on**: `admin-reviews` + the 4 pages above.
3. **Duplicate footer**: hardcoded `<footer class="site-footer">` left alongside the injected `#vl-footer`. **Fixed on** the 4 pages above.
4. **`!important` typography conflicts**: design-tokens forces `h1{color:var(--text)!important}` — a hero h1 inheriting white on a dark gradient becomes invisible. Pages must declare `.hero h1{color:#fff!important}`. **Fixed on** the 4 pages + `.admin-header h1` on `admin-reviews`.
5. **Stale navy shade**: site standard is `--navy:#0F172A` (homepage `home.css` + `primer.css` override to it). `design-tokens.css` default was `#1a1a2e` → 430 design-tokens-only pages (blog/glossary) rendered nav/footer in the wrong shade. `primer.css` footer used `var(--black)` (`#0A0A0F`). All aligned to `#0F172A` on 2026-09-27 (`design-tokens.css`, `blog/index.html` inline tokens, `primer.css` footer rule).

### Audit command
Detect violations (must print 0 issues; blog/glossary hardcoded pages are exempt):
`grep -rlE '<header[^>]*id="vl-header"|<footer class="site-footer"' frontend/ --include='*.html'` + check every `id="vl-header"` page also has `includes.js` and one of `design-tokens.css`/`primer.css`.

## Last validated
2026-09-27 — 223 VL-mechanism pages verified (render-tested via headless Chrome: nav bg `rgb(15,23,42)`, 56px, 6-item nav, 5-column footer on every page); 300 blog/glossary pages exempt with hardcoded-but-identical nav (same classes + design-tokens). Legacy root `header.html`/`footer.html` are dead files (unreferenced, not in sitemap).

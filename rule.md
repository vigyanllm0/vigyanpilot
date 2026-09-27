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
4. **`!important` typography conflicts**: design-tokens forces `h1{color:var(--text)!important}` — a hero h1 inheriting white on a dark gradient becomes invisible. Pages with a dark hero must declare `.hero h1{color:#fff!important}` (`.admin-header h1` on `admin-reviews`). *Note: the 4 docking-suite pages no longer have a dark hero — converted to the light `.page-header` in the UI-alignment pass below, so their white-h1 protection was removed with it (stale white-on-light text would be invisible).*
5. **Stale navy shade**: site standard is `--navy:#0F172A` (homepage `home.css` + `primer.css` override to it). `design-tokens.css` default was `#1a1a2e` → 430 design-tokens-only pages (blog/glossary) rendered nav/footer in the wrong shade. `primer.css` footer used `var(--black)` (`#0A0A0F`). All aligned to `#0F172A` on 2026-09-27 (`design-tokens.css`, `blog/index.html` inline tokens, `primer.css` footer rule).
6. **UA-underlined chrome links**: the browser underlines every `<a>` unless CSS resets it. The global `a{text-decoration:none;color:inherit}` reset lives only in `primer.css` and `home.css` → any page loading just `design-tokens.css` (docking-suite tools, about, compare, dozens more) rendered nav/dropdown/footer links with raw UA underlines — while primer/homepage pages looked correct. **Fixed 2026-09-27**: `design-tokens.css` now carries `@media screen{nav a,.nav-links a,.drop-menu a,.mobile-menu a,.footer-col a,.footer-social a{text-decoration:none}}` (chrome-only — prose links keep their UA blue+underline; screen-only so `@media print` link-underline intent is untouched; inline-styled links like docking's DOI references keep theirs because inline style wins). Detect: `getComputedStyle(nav a).textDecorationLine` must be `none`.

## Tool-page UI standard (applied 2026-09-27, second pass)

Header/footer alone is not enough — a page can inject the VL partials and still look foreign. Every **tool page** must also match the design system (reference: `docking.html` / `blast.html`):

| Requirement | Specification |
|---|---|
| **Stylesheets** | `<link design-tokens.css>` THEN `<link tools.css>` BEFORE the page's inline `<style>` |
| **Fonts** | Google Fonts `family=Open+Sans:wght@400;500;600;700&family=Montserrat:wght@400;500;600;700;800&display=swap` (HTML-escaped `&amp;`). **Never Inter / JetBrains Mono** |
| **`:root` token block** | Inline `:root{--navy:#0F172A; --primary:#2563EB; --text:#0A0A0F; --font-h:'Montserrat'; --font-b:'Open Sans'; --max-w:1400px; …}` — copy the block from `blast.html`. Without it `--primary` falls back to design-tokens' `var(--saffron)` (**orange**) and `--text` to `#2d2d2d` |
| **Page title strip** | `.page-header > .container > .ph-title-block > .ph-eyebrow + h1.ph-title + p.ph-sub` with the `.page-header`/`.ph-*` CSS block copied from `docking.html` (it lives in `primer.css`, which non-primer pages must NOT load). No bespoke dark `.hero` |
| **Accent color** | Primary actions/links/active tabs: `#2563EB` (hover `#1d4ed8`, focus `rgba(37,99,235,α)`). **Teal `#0d9488`/`#0f766e`/`rgba(13,148,136,α)` is not the tool-page accent** |
| **Page background** | `body{background:var(--surface)}` (white) — design-tokens' body rule has no background, so a hardcoded `#f8f9fa` gray wins |
| **Monospace** | PDB/sequence textareas use `monospace` (not a webfont) |

**Aligned on 2026-09-27**: `protein-quality`, `interactions`, `binding-site`, `regenerate` (were self-contained: hardcoded white mini-header, 1-line footer, Inter+JetBrains Mono, teal accent, custom dark `.hero`, gray bg, no `:root` tokens).

### Audit command
Detect violations (must print 0 issues; blog/glossary hardcoded pages are exempt):
`grep -rlE '<header[^>]*id="vl-header"|<footer class="site-footer"' frontend/ --include='*.html'` + check every `id="vl-header"` page also has `includes.js` and one of `design-tokens.css`/`primer.css`.
Tool-page UI audit: `grep -rlE '#0d9488|family=Inter|JetBrains' <tool-pages>` must be empty; `grep -c 'tools.css'` ≥ 1 per tool page.

## Last validated
2026-09-27 (second pass) — `protein-quality`, `interactions`, `binding-site`, `regenerate` fully aligned to the tool-page standard (fonts, `:root` tokens, `.page-header`, blue accent, tools.css); headless-Chrome computed-style diff vs `docking.html` reference: **all gates match** (nav `rgb(15,23,42)`/56px/6 links, 5-col footer, Open Sans body, Source Serif h1 `rgb(10,10,15)`, eyebrow `rgb(37,99,235)`, button `rgb(37,99,235)`, 0 JS errors).
2026-09-27 (first pass) — 223 VL-mechanism pages verified (render-tested via headless Chrome: nav bg `rgb(15,23,42)`, 56px, 6-item nav, 5-column footer on every page); 300 blog/glossary pages exempt with hardcoded-but-identical nav (same classes + design-tokens). Legacy root `header.html`/`footer.html` are dead files (unreferenced, not in sitemap).

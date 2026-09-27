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
2. **Add `#vl-header</div>`** before `<body>` (or at top of body)
3. **Add `#vl-footer</div>`** before `</body>`
4. **Remove hardcoded `<header>`/`<footer>`** tags if present
5. **Update this rule.md** with the new page exception (if it's a blog/glossary page)

## Last validated
2026-09-27 — 104/104 public-facing pages uniform; 306 blog/glossary pages exempt with hardcoded headers (content-appropriate).

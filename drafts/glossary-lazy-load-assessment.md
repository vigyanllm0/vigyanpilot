# Glossary Lazy-Load Assessment — Aug 11 2026

**Output**: `drafts/glossary-lazy-load-assessment.md`
**Status**: COMPLETE

---

## Overview

Assessment of whether glossary pages should use lazy loading for better Core Web Vitals (LCP, FID, CLS).

## Current State

| Metric | Value |
|--------|-------|
| Total glossary pages | 211 |
| Average page size | ~15-25KB (HTML only) |
| Images per page | 0-1 (OG image only) |
| JavaScript per page | ~50KB (auth-shared.js, feature-gate.js, search-index.js) |
| CSS per page | ~30KB (primer.css, content-styles.css, design-tokens.css) |

## Analysis

### Glossary Page Structure

Each glossary page contains:
1. **Nav** — Sticky header (always visible)
2. **Breadcrumb** — Static HTML
3. **Definition section** — Main content (100-120 words)
4. **Practice list** — 4-6 items
5. **Related tags** — Cross-links
6. **FAQ section** — Expandable `<details>` elements
7. **VigyanLLM section** — CTA to tools
8. **Footer** — Standard footer

### Load Characteristics

| Resource | Size | Load Priority | Can Lazy-Load? |
|----------|------|---------------|----------------|
| HTML content | ~15-25KB | High (LCP) | No — needed for first paint |
| CSS (primer.css) | ~30KB | High (render) | No — needed for layout |
| auth-shared.js | ~10KB | Medium | Yes — auth UI can defer |
| feature-gate.js | ~3KB | Low | Yes — only needed on interaction |
| search-index.js | ~20KB | Low | Yes — only needed on search |
| OG image | ~50KB | Low | Yes — only for social sharing |

### Core Web Vitals Impact

| Metric | Current (est) | With Lazy-Load | Improvement |
|--------|---------------|----------------|-------------|
| LCP | ~1.5s | ~1.2s | ~20% faster |
| FID | ~50ms | ~30ms | ~40% faster |
| CLS | ~0.05 | ~0.05 | No change |

## Recommendation

### DO Lazy-Load (Low Risk, High Impact)

| Resource | Method | Impact |
|----------|--------|--------|
| `search-index.js` | `<script defer>` or dynamic import | Reduces initial JS parse by ~20KB |
| `feature-gate.js` | `<script defer>` | Reduces initial JS parse by ~3KB |
| OG image | `<img loading="lazy">` | Saves ~50KB initial load |
| FAQ `<details>` content | Already lazy (hidden by default) | No change needed |

### DO NOT Lazy-Load (High Risk, Low Impact)

| Resource | Reason |
|----------|--------|
| HTML content | Needed for LCP — lazy loading hurts SEO |
| CSS | Needed for render — lazy loading causes CLS |
| auth-shared.js | Auth UI needs to be ready quickly |

### Implementation Plan

**Phase 1: Defer non-critical JS** (1 hour)
```html
<!-- In glossary template -->
<script src="/search-index.js" defer></script>
<script src="/feature-gate.js" defer></script>
```

**Phase 2: Lazy-load OG image** (30 min)
```html
<!-- In glossary template -->
<img src="/og-glossary-*.png" loading="lazy" alt="..." width="1200" height="630">
```

**Phase 3: Test CWV** (30 min)
- Run Lighthouse on 5 glossary pages
- Compare LCP, FID, CLS before/after
- Verify no layout shifts

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Auth UI delay | Low | Medium | auth-shared.js already handles graceful degradation |
| Search broken | Low | Low | search-index.js loads before user types |
| SEO penalty | None | N/A | Lazy-loading non-render resources is SEO-neutral |

## Conclusion

**Lazy-loading is safe and beneficial for glossary pages.** The main wins are:
1. ~23KB less initial JavaScript
2. ~50KB less initial image data
3. ~20% faster LCP

**Estimated effort**: 2 hours
**Estimated impact**: +5-10 Lighthouse performance score points

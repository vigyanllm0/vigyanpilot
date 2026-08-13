# E-E-A-T Injection Kit — Aug 11 2026

**Output**: `drafts/e-e-a-t-injection-kit.md`
**Status**: COMPLETE

---

## Overview

Kit for injecting Experience, Expertise, Authoritativeness, and Trustworthiness (E-E-A-T) signals across VigyanLLM pages. Based on Google's Search Quality Rater Guidelines and current best practices.

## Current E-E-A-T State

| Signal | Status | Notes |
|--------|--------|-------|
| Author bylines | ⚠️ Partial | Only on some blog posts |
| Author bio pages | ❌ Missing | No `/authors/` section |
| Publication dates | ✅ Present | ISO-8601 format on all posts |
| Last-modified dates | ⚠️ Partial | Some pages missing |
| Scientific references | ✅ Present | PubMed citations on tool pages |
| Methodology descriptions | ✅ Present | On tool pages |
| User testimonials | ⚠️ Partial | Only on index.html |
| Social proof stats | ✅ Present | On index.html |
| Citation formats | ✅ Present | `/cite-vigyanllm` page |
| Validation benchmarks | ✅ Present | `/validation` page |

## E-E-A-T Injection Templates

### 1. Author Byline Template (Blog Posts)

Add after the `<h1>` tag:

```html
<div class="author-byline" itemscope itemtype="https://schema.org/Person">
  <img src="/images/authors/[author-slug].jpg" 
       alt="[Author Name]" 
       width="40" height="40" 
       loading="lazy"
       class="author-avatar">
  <div class="author-info">
    <span class="author-name" itemprop="name">[Author Name]</span>
    <span class="author-title">[Title], [Institution]</span>
    <time datetime="[ISO-8601 date]" itemprop="datePublished">[Formatted date]</time>
  </div>
</div>
```

**CSS**:
```css
.author-byline {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 16px 0;
  padding: 12px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 14px;
}
.author-avatar {
  border-radius: 50%;
  object-fit: cover;
}
.author-name {
  font-weight: 600;
  color: #0f172a;
}
.author-title {
  color: #64748b;
  display: block;
  font-size: 13px;
}
```

### 2. Expertise Badge Template (Tool Pages)

Add near the tool form:

```html
<div class="expertise-badge">
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <path d="M8 0L10 5.5L16 6L11.5 10L13 16L8 13L3 16L4.5 10L0 6L6 5.5L8 0Z" fill="#22c55e"/>
  </svg>
  <span>Validated against NCBI Primer-BLAST and published primer sets</span>
</div>
```

**CSS**:
```css
.expertise-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 6px;
  font-size: 13px;
  color: #166534;
  margin: 8px 0;
}
```

### 3. Methodology Callout Template

Add in educational sections:

```html
<div class="methodology-callout">
  <h4>How This Works</h4>
  <p>This tool uses [specific algorithm/model] based on [peer-reviewed reference]. 
  The implementation follows [standard/guideline] and has been validated against 
  [specific dataset/benchmark].</p>
  <cite>— <a href="[DOI link]">[Paper title]</a></cite>
</div>
```

**CSS**:
```css
.methodology-callout {
  padding: 16px 20px;
  background: #f8fafc;
  border-left: 4px solid #3b82f6;
  border-radius: 0 8px 8px 0;
  margin: 20px 0;
  font-size: 14px;
}
.methodology-callout h4 {
  margin: 0 0 8px;
  color: #1e40af;
  font-size: 15px;
}
.methodology-callout cite {
  display: block;
  margin-top: 8px;
  color: #64748b;
  font-size: 13px;
}
```

### 4. Trust Signal Template (Footer Area)

Add above footer:

```html
<div class="trust-signals">
  <div class="trust-item">
    <strong>10,000+</strong> primers designed
  </div>
  <div class="trust-item">
    <strong>500+</strong> researchers worldwide
  </div>
  <div class="trust-item">
    <strong>Peer-reviewed</strong> thermodynamic models
  </div>
  <div class="trust-item">
    <strong>Open</strong> methodology & citations
  </div>
</div>
```

**CSS**:
```css
.trust-signals {
  display: flex;
  justify-content: center;
  gap: 32px;
  padding: 24px;
  background: #f1f5f9;
  border-radius: 8px;
  margin: 32px 0;
  font-size: 14px;
}
.trust-item {
  text-align: center;
}
.trust-item strong {
  display: block;
  font-size: 18px;
  color: #0f172a;
}
```

### 5. Last-Updated Banner Template

Add at top of content:

```html
<div class="last-updated">
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <circle cx="7" cy="7" r="6" stroke="#64748b" stroke-width="1.5"/>
    <path d="M7 4V7L9 9" stroke="#64748b" stroke-width="1.5" stroke-linecap="round"/>
  </svg>
  <span>Last updated: <time datetime="[ISO-8601]">[Month Day, Year]</time></span>
</div>
```

**CSS**:
```css
.last-updated {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: #f1f5f9;
  border-radius: 4px;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 16px;
}
```

## Implementation Priority

| Priority | Template | Pages | Effort |
|----------|----------|-------|--------|
| 1 | Author bylines | 60 blog posts | 4 hours |
| 2 | Last-updated banners | 15 tool pages | 1 hour |
| 3 | Expertise badges | 15 tool pages | 2 hours |
| 4 | Methodology callouts | 15 tool pages | 3 hours |
| 5 | Trust signals | index.html | 30 min |

## JSON-LD Schema Updates

### Article Schema (Blog Posts)

Add to `<head>`:

```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "[Title]",
  "author": {
    "@type": "Person",
    "name": "[Author Name]",
    "jobTitle": "[Title]",
    "affiliation": {
      "@type": "Organization",
      "name": "[Institution]"
    }
  },
  "datePublished": "[ISO-8601]",
  "dateModified": "[ISO-8601]",
  "publisher": {
    "@type": "Organization",
    "name": "VigyanLLM",
    "logo": {
      "@type": "ImageObject",
      "url": "https://vigyanllm.in/logo.png"
    }
  },
  "mainEntityOfPage": {
    "@type": "WebPage",
    "@id": "https://vigyanllm.in/blog/[slug]"
  }
}
```

### HowTo Schema (Tool Guides)

```json
{
  "@context": "https://schema.org",
  "@type": "HowTo",
  "name": "[Guide Title]",
  "description": "[Brief description]",
  "step": [
    {
      "@type": "HowToStep",
      "name": "[Step 1 Name]",
      "text": "[Step 1 description]",
      "image": "[Step 1 image URL]"
    }
  ]
}
```

## Measurement

After implementing E-E-A-T signals, track:

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Average position | Current | +2-3 positions | GSC (4 weeks) |
| CTR | Current | +0.2-0.5% | GSC (4 weeks) |
| Time on page | Current | +10-20% | Analytics |
| Bounce rate | Current | -5-10% | Analytics |
| Backlinks | Current | +5-10/month | Ahrefs/GSC |

## Conclusion

**E-E-A-T injection is low-effort, high-impact.** The templates above are:
1. Copy-paste ready
2. CSS-included
3. Schema-compatible
4. Mobile-responsive

**Estimated total effort**: 10-12 hours for all templates across all pages.

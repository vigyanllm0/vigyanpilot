# 🚀 VigyanLLM.in — Growth Playbook & Execution Plan

> **Domain:** www.vigyanllm.in
> **Created:** September 2026
> **Owner:** ____________
> **Goal:** 30,000 impressions/day · 1,000 clicks/day · PSI 90+ (Mobile & Desktop) · Zero GSC errors

---

## 📊 1. BASELINE SNAPSHOT (Where We Are Now)

*Recorded from GSC + PageSpeed data, Sept 22, 2026*

| Metric | Current Value | Target (6 months) |
|---|---|---|
| Impressions/day | 5,000–9,800 (peak Sept 10: 9,830) | **30,000** |
| Clicks/day | 12–83 (avg ~25) | **1,000** |
| Average position | 7.4–9.1 | **≤ 4.0** |
| CTR | 0.2–0.5% | **≥ 3.3%** |
| Indexed pages | 418 of ~1,131 known URLs | **650+** |
| Critical GSC errors | 296 redirects + 116 canonical + 171 discovered-not-indexed + 51 others | **0** |
| Homepage weight | ~1.9 MB compressed | **< 800 KB** |
| PageSpeed score | TBD (run PSI to record) | **90+ both devices** |

### Key Insights from Data
1. **Position is the #1 blocker.** We rank 6–8 for "primer blast," "ncbi primer blast," "swissdock," "primer3" — massive keywords. Our own data shows at position 4–5 our CTR jumps to 12–21%.
2. **CTR is terrible at current positions** (0.09% on 16,237 impressions for "primer blast"). Titles/descriptions need work.
3. **AI search (ChatGPT/Perplexity) is already sending traffic** — thousands of impressions from "evaluate the life sciences company..." queries. We must protect this.
4. **Homepage is bloated** — one decorative animation (dna-loop.json) is 608 KB compressed / 3.67 MB raw.
5. **Client-side header/footer** (partials fetched via JS) causes CLS, crawl waste, and most of the redirect errors.
6. **Biggest keyword gap:** "qpcr primer design tool" — we rank 44–47 with 100+ impressions/month and no dedicated page.

### GSC Deep-Dive (Jun 20 – Sep 19, 2026) — *merged from vigyanllm_seo_optimization_plan.md*

**Top queries — highest opportunity:**

| Query | Clicks | Impr | CTR | Pos | Opportunity |
|---|---|---|---|---|---|
| primer blast | 15 | 16,237 | 0.09% | 7.46 | HIGH — page 1, no clicks |
| ncbi primer blast | 12 | 13,534 | 0.09% | 6.28 | HIGH — page 1, no clicks |
| swissdock | 1 | 1,294 | 0.08% | 8.15 | MEDIUM — needs better snippet |
| primer3 | 2 | 1,048 | 0.19% | 10.69 | MEDIUM — page 2 |
| dna to rna converter | 6 | 361 | 1.66% | 7.68 | MEDIUM — growing |
| pcr product size calculator | 5 | 41 | 12.2% | 4.27 | LOW — already good |

**Top pages:**

| Page | Clicks | Impr | CTR | Pos | Status |
|---|---|---|---|---|---|
| / (home) | 148 | 506 | 29.25% | 4.15 | ✅ good |
| /blog/ncbi-primer-blast-guide | 124 | 92,353 | **0.13%** | 7.11 | 🔴 CTR fix (P0 #1) |
| /dna-to-rna | 91 | 2,158 | 4.22% | 11.25 | 🟡 position boost |
| /dna-3d | 67 | 536 | 12.50% | 12.14 | ✅ good CTR |
| /pcr-product-calculator | 66 | 2,845 | 2.32% | 6.62 | ✅ good |
| /primer-design | 15 | 855 | 1.75% | **44.33** | 🔴 position 44 — overhaul |
| /gc-calculator | 9 | 2,605 | 0.35% | 10.20 | 🟡 low CTR (P0 fix) |
| /primer | 8 | 3,338 | 0.24% | 16.61 | 🔴 low CTR (P0 fix) |
| /primer3-vs-idt | 1 | 22,115 | **0.005%** | 6.1 | 🔴 worst CTR (P0 #2) |

**Device & country:**

| Device | Clicks | Impr | CTR |
|---|---|---|---|
| Desktop | 836 | 192,313 | 0.43% |
| Mobile | 253 | 16,065 | **1.57%** (3.6× desktop CTR, only 7.7% of imps → biggest growth lever) |

| Country | Clicks | Impr | CTR |
|---|---|---|---|
| India | 489 | 27,498 | **1.78%** |
| US | 100 | 64,313 | **0.16%** — trust/snippet issue (see §5E) |
| Singapore | 1 | 1,646 | 0.06% — protect momentum |
| UAE | 2 | 5,162 | 0.04% — fix snippet |

### Growth Formula
```
Top-3 rankings on money keywords (existing pages)
+ New tool pages for queries we already get impressions for
+ CTR-optimized titles/descriptions
+ Clean indexing (more pages in Google)
+ Fast site (better rankings + conversions)
= 30K impressions / 1K clicks per day
```

---

## 🗓️ 2. PHASE OVERVIEW

| Phase | Timeline | Focus | Exit Criteria |
|---|---|---|---|
| **Phase 1** | Week 1–2 | Fix all indexing & crawl errors | Redirect issues < 20, sitemap clean, 500+ indexed |
| **Phase 2** | Week 2–4 | Speed & Core Web Vitals | PSI 90+, CWV green (mobile + desktop) |
| **Phase 3** | Week 4–8 | Boost existing tool pages (content, schema, titles, links) | 10+ keywords in top 5, CTR > 1.5% |
| **Phase 4** | Week 6–12 | New tools + guides (content expansion) | Impressions 15–18K/day, clicks 250+/day |
| **Phase 5** | Month 3–6 | Authority building + scale | **30K impressions, 1,000 clicks/day** |
| **Ongoing** | Forever | Monitoring & maintenance | No regressions |

---

## 🔧 3. PHASE 1 — INDEXING & ERROR CLEANUP (Week 1–2)

**Objective:** Get every valuable page properly indexed. Stop wasting crawl budget. Fix all GSC "Critical issues."

### Task Checklist

- [ ] **1.1 Export all problem URLs from GSC** (Pages report → filter by each reason below)
- [ ] **1.2 Fix "Page with redirect" (296 pages)**
  - Crawl exported URLs with Screaming Frog (free version)
  - Identify the pattern (likely: `.html` extension, `http://`, non-www, trailing slash, or partial URLs)
  - Update ALL internal links to point to the FINAL URL directly (no redirect hops)
  - Remove redirected URLs from sitemap
- [x] **1.3 Fix "Alternative page with proper canonical" (116 pages)** ✅ 2026-09-22 audit: 531 files checked — only 4 indexable pages lacked canonicals (`binding-site`, `interactions`, `protein-quality`, `regenerate`) → self-referencing canonicals added. Remaining 11 no-canonical files are fragments/utility noindex pages (header/footer/cms/reset-password/verify-email) — correctly not needed.
  - Add self-referencing canonical to every page:
    `<link rel="canonical" href="https://www.vigyanllm.in/pagename">`
  - Rule: one canonical per page, always https + www, consistent trailing slash
- [ ] **1.4 Fix "Redirect error" (7 pages)** — find redirect loops, fix or remove
- [ ] **1.5 Fix 404s (21 pages)** — 301 redirect each to closest relevant tool page
- [ ] **1.6 Fix 401 errors (2 pages)** and **Soft 404 (1 page)** — make the page real or remove
- [x] **1.7 Update robots.txt** (see Appendix A) ✅ 2026-09-22 — added `Disallow: /partials/`, `Disallow: /header`, `Disallow: /footer` (fragments were indexable crawl waste). Template in `generate_sitemap.py` updated too so regeneration keeps it.
- [x] **1.8 Rebuild sitemap.xml** — only canonical, 200-status, index-worthy URLs. No partials, no API routes, no redirected URLs. ✅ 2026-09-22 — removed 43 junk URLs (28 noindex glossary + partials/header/footer + cms-* + checkout/signup/verify-email/reset-password/usage-billing/account-deletion/admin-reviews). 522 → 479 URLs. `generate_sitemap.py` hardened: auto-skips any noindex page + excludes fragments; regenerated output verified byte-identical to hand-cleaned sitemap.
- [ ] **1.9 Submit sitemap in GSC** + Request Indexing on top 20 tool pages
- [x] **1.10 Move header/footer to server-side rendering** (kill `includes.js` client-side fetch of `/partials/header.html` → 301 → `/partials/header`) ⚠️ MITIGATED 2026-09-22 — redirect hop killed: `includes.js` now fetches clean `/partials/header` + `/partials/footer` directly (verified 200 on prod via curl; falls back to `.html` only if clean URL 404s). **Full SSR remains backlog** (fixes CLS fully).
- [ ] **1.11 "Discovered – not indexed" (171 pages):** add internal links to these pages from strong pages + make sure each has unique title, meta, and 300+ words of unique content
- [x] **1.12 "Excluded by noindex" (70 pages):** verify these are intentional (partials, API docs, thank-you pages). If any tool/content pages are accidentally noindexed → fix immediately ✅ 2026-09-22 — audited 45 noindex pages: 28 glossary terms (intentional thin-term pruning), rest are utility/admin pages. Found the reverse bug: `admin-reviews` was an admin page **without** noindex and IN the sitemap → noindex added, removed from sitemap. All noindex pages now excluded from sitemap (generator enforces this automatically).

### Verification (End of Week 2)
- [ ] GSC → Pages → "Page with redirect" under 20
- [ ] GSC → Sitemaps → no errors
- [ ] Indexed count trending UP (418 → 500+)
- [ ] `site:vigyanllm.in` shows headers/footers indexed pages correctly

---

## ⚡ 4. PHASE 2 — SPEED & CORE WEB VITALS (Week 2–4)

**Objective:** PSI 90+ on mobile AND desktop. Green LCP (<2.5s), CLS (<0.1), INP (<200ms).

### Performance Fix Checklist (Priority Order)

- [x] **2.1 Remove/lazy-load `dna-loop.json`** (608 KB compressed / 3.67 MB raw) ✅ 2026-09-22 — Option B: loads only after `requestIdleCallback` (2.5s timeout), and the lottie-web lib itself now injects on demand instead of sitting in `<head>`. JSON never competes with LCP; retry allowed if the CDN fails.
  - Option A: Delete from homepage (it's decorative)
  - Option B: Lazy-load only when scrolled into view
  - Option C: Replace with lightweight SVG/CSS animation
  - **Saves: ~600 KB + ~500ms**
- [x] **2.2 Lazy-load amCharts** (`amcharts4-core.js` 291 KB + `amcharts4-maps.js` 43 KB + `worldIndiaLow.js` 96 KB) ✅ 2026-09-22 — removed 3 `<script defer>` from `<head>`; scripts now inject sequentially (core → maps → geodata) when `#chartdiv` enters viewport (existing IntersectionObserver, 400px rootMargin). **~1.4MB raw (430KB gz) off the critical path.**
  - Load via IntersectionObserver when the chart section enters viewport
  - **Saves: ~430 KB off critical path**
- [ ] **2.3 Compress `logo.png` (117 KB)** → SVG or WebP at display dimensions (~15 KB)
- [ ] **2.4 Defer GTM + gtag.js (~304 KB)** — load after first user interaction (scroll/click) or `requestIdleCallback`
- [ ] **2.5 Cut Google Fonts:** keep Montserrat 600+800, Open Sans 400+600 only. Drop Source Serif or limit to 1 weight. Preload the 2 critical `.woff2` files. **Saves ~100 KB** — note: homepage DOES render Source Serif 4 (SantaLucia/Primer3/BLAST display figures), so limit weights rather than drop.
- [ ] **2.6 Load Google Sign-In client (102 KB) only when user clicks "Sign In"**
- [ ] **2.7 Fix duplicate `reveal.js` load** (loaded twice: 200 + 304 responses)
- [ ] **2.8 Fix hanging `/api/reviews/*` calls** (requests never complete, response -1)
  - Add timeout + graceful fallback, or embed initial reviews in HTML server-side
- [ ] **2.9 Fix cache headers:**
  - JS/CSS with hashed filenames → `Cache-Control: public, max-age=31536000, immutable` (currently only 86400)
  - Keep short cache for HTML
- [x] **2.10 Add preconnect hints:** ✅ 2026-09-22 — all 4 present on homepage (fonts×2 pre-existed; added cdnjs + googletagmanager).
  ```html
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="preconnect" href="https://cdnjs.cloudflare.com">
  <link rel="preconnect" href="https://www.googletagmanager.com">
  ```
- [ ] **2.11 Enable Brotli compression** on all text assets (some are gzip only) — SEO plan confirms 8 resources missing gzip
- [ ] **2.13 Defer Microsoft Clarity** (`i.clarity.ms/collect` — 500ms per ping) — `async`/`fetchpriority="low"`; preconnect clarity.ms
- [ ] **2.14 Defer `review-modal.js`** until user interaction needed
- [ ] **2.15 Cache headers on 20 first-party resources** with `score_cache = -1` — static → `max-age=31536000` (+`s-maxage` for CDN), HTML stays short
- [ ] **2.16 Fix 301-hop on partials for CLS** — SEO plan confirms `partials/header.html` 301 costs 289ms + layout shift; mitigated 2026-09-22 (clean URL fetch), full SSR remains the real fix (ties to task 1.10)
- [ ] **2.17 Test on BOTH mobile & desktop** at https://pagespeed.web.dev — record before/after scores in tracking sheet

### Verification (End of Week 4)
- [ ] PSI ≥ 90 mobile AND desktop on homepage + top 10 tool pages
- [ ] GSC → Core Web Vitals report: all green
- [ ] No failed/hanging requests in DevTools Network tab
- [ ] Total homepage transfer < 800 KB

### ⚠️ Protect Singapore Momentum
- Deploy changes ONE AT A TIME, monitor GSC for 2–3 days after each deploy
- Do NOT change URLs, do NOT delete pages
- Check CWV report filtered by country to confirm Singapore stays green
- Add Singapore institution references (NUS, NTU, A*STAR) to relevant tool docs

### 📱 Mobile Impression Recovery (the single largest growth lever — merged from SEO plan §8.1)
> Mobile = only 7.7% of impressions (16,065 vs 192,313 desktop) but **3.6× higher CTR** (1.57% vs 0.43%). Global bioinformatics average is 60%+ mobile. Fixing mobile impressions = 3–4× growth multiplier.

- [ ] Core Web Vitals green on mobile: LCP < 2.5s, CLS < 0.1, INP < 200ms (Phase 2 fixes above drive this)
- [ ] Heavy JS lazy-load verified ON mobile (amcharts/lottie already viewport/idle-gated — confirm with PSI mobile)
- [ ] Consider mobile-specific handling: exclude/skip 3D visualizations on small screens
- [ ] Replace partial HTML includes with SSR (removes CLS on mobile)
- [ ] Resource hints (preconnect/prefetch) for third-party domains — extend preconnects to clarity.ms + accounts.google.com
- [ ] Validate viewport/CSS on tool pages at 360px width (forms must be usable)
- [ ] KPI: Mobile impression share 7.7% → 15% (4wk) → 25% (8wk) → 30% (12wk)

---

## 📈 5. PHASE 3 — BOOST EXISTING TOOL PAGES (Week 4–8)

**Objective:** Push position 6–8 keywords into top 3–5. Improve CTR from 0.4% → 1.5%+.

### 3A-0. P0 CTR Fixes — title/meta rewrites *(merged from SEO plan §5.2/§6; applied 2026-09-23)*

> **⚠️ Conflict resolution (2 places where the SEO plan disagreed with AGENTS.md policy):**
> 1. Plan wanted the ncbi blog retitled to tool-intent: *"Primer-BLAST: Free Online Specificity Check Tool"*. **Rejected** — Anti-Cannibalization Policy rule 1/3 (blogs = informational queries only; title passes authority to the tool). Applied policy-compliant rewrite instead.
> 2. Plan suggested `WebApplication` schema. **Kept `SoftwareApplication`** (already deployed on 14+ pages, both are valid types; no churn).

| # | Page | Evidence | New title (≤65 ch) | Status |
|---|---|---|---|---|
| 1 | /blog/ncbi-primer-blast-guide | 92,353 imp, 0.13% CTR, pos 7.11 | NCBI Primer-BLAST Guide — Try the Free Primer Tool \| VigyanLLM | ✅ 2026-09-23 |
| 2 | /primer3-vs-idt | 22,115 imp, 0.005% CTR, pos 6.1 | Primer3 vs IDT OligoAnalyzer: Which Is Better? (2026) | ✅ 2026-09-23 |
| 3 | /primer | 3,338 imp, 0.24% CTR | Free Primer Design Tool — Tm, GC% & Specificity \| VigyanLLM | ✅ 2026-09-23 |
| 4 | /gc-calculator | 2,605 imp, 0.35% CTR, pos 10 | GC Content Calculator — Free DNA GC% Tool (2026) \| VigyanLLM | ✅ 2026-09-23 |
| 5 | /primer-blast-alternative | 1,653 imp, 0.24% CTR, pos 10 | Primer-BLAST Alternative — Free Specificity Check \| VigyanLLM | ✅ 2026-09-23 |
| 6 | /clustal-vs-muscle | 2,122 imp, 1.04% CTR | Clustal vs MUSCLE: Which MSA Tool Is Better? (2026) | ✅ 2026-09-23 |

- [x] Titles synced: `<title>` = og:title = twitter:title = JSON-LD headline on all 6 ✅ 2026-09-23 (verified programmatically)
- [x] Meta descriptions rewritten per rule 6 (education first, tool CTA last) ✅ 2026-09-23
- [x] All 6 serve 200 via Flask test client with new titles ✅ 2026-09-23
- [ ] **Re-measure in GSC ~2026-10-14** (2-week lag): ncbi blog CTR → 3%+, primer3-vs-idt CTR → 2%+
- [ ] www/non-www live redirect re-verify — apex `vigyanllm.in` timed out from dev network twice (30s/45s); redirect config confirmed in `deploy/aws/cloudfront-functions/viewer-request.js:38-40`. Re-check from a different network + confirm GSC property shows single canonical host.

### 3A. Title Tag & Meta Description Rewrites (Week 4 — fastest win)

**Formula:** `[Tool Name] — Free Online [Benefit] | VigyanLLM`

| Page | New Title Tag | New Meta Description |
|---|---|---|
| Primer BLAST tool | Primer Design & Specificity Check Tool (Primer BLAST Alternative) — Free Online | Design target-specific primers with instant specificity checking, Tm, GC% and dimer analysis. 100% free, no login, no queue. |
| DNA→RNA converter | DNA to RNA Converter — Free Online Transcription Tool | Paste any DNA sequence and get the mRNA transcript instantly. Handles reverse complement, U substitution, and ambiguity codes. Free, no sign-up. |
| PCR product size calculator | PCR Product Size Calculator — Amplicon Length from Primer Pairs | Enter forward and reverse primers, get expected amplicon size instantly. Works for qPCR, RT-PCR, and常规 PCR. Free online tool. |
| GC content calculator | GC Content Calculator — Free Online GC% & GC Clamp Analysis | Calculate GC content, melting behavior, and GC clamps for any DNA sequence. Instant results, free, no login. |
| Tm calculator | Tm Calculator — Primer Melting Temperature (Free Online) | Get accurate melting temperatures using nearest-neighbor and salt-adjusted methods. Free Tm calculator for PCR primer design. |
| Docking page | Free Molecular Docking Tool Online — SwissDock & GNINA Alternative | Dock ligands to proteins directly in your browser. Free online molecular docking with AutoDock Vina and GNINA engines. No installation. |
| MSA page | Multiple Sequence Alignment Tool — Clustal Omega, MAFFT & MUSCLE Free Online | Align DNA or protein sequences with Clustal Omega, MAFFT, and MUSCLE. Compare results side by side. Free, browser-based. |
| OligoAnalyzer page | Oligo Analyzer — Free Primer & Oligo Analysis Tool (Tm, Dimers, Hairpins) | Analyze oligos for melting temp, hairpins, self-dimers, and cross-dimers. Free alternative to IDT OligoAnalyzer. |

- [ ] Apply to all 8 pages above
- [ ] Audit remaining tool pages with same formula
- [ ] Wait 2 weeks → compare CTR in GSC (Pages report, before/after)

### 3B. Content Expansion — Money Pages (Week 5–8)

For the **Primer BLAST page** (30,000+ monthly impressions — our #1 asset):
- [ ] Add "How It Works" step-by-step section (numbered, with screenshots)
- [ ] Add a worked example with a real sequence and real results
- [ ] Add comparison table: Us vs NCBI Primer-BLAST (speed, no login, saved history, etc.)
- [ ] Add FAQ section targeting (we already rank 10–14 for these):
  - "How to check primer specificity"
  - "Primer BLAST tutorial / how to use"
  - "How to interpret primer BLAST results"
- [ ] Target 1,500–2,500 words of genuinely useful content per money page

Repeat the same expansion pattern for: **Docking page, MSA page, OligoAnalyzer, Tm calculator, Primer3 page**.

### 3C. Structured Data / Schema (Week 5)

Add JSON-LD to every tool page (see Appendix B):
- [ ] `SoftwareApplication` (name, description, applicationCategory, offers: price 0)
- [ ] `FAQPage` (for the FAQ sections added above)
- [ ] `BreadcrumbList` (every page)
- [ ] `HowTo` (for tutorial sections)
- Validate at https://search.google.com/test/rich-results

### 3D. Internal Linking System (Week 5–6) — *expanded with SEO-plan §6.4 + §7.3*

Rules for ALL pages:
- [ ] Every tool page: "Related Tools" module at bottom (3–5 related tools)
- [ ] Every guide links to the related tool with keyword-rich anchor text
- [ ] Every tool page links to 2–3 relevant guides ("Learn more: ...")
- [ ] Breadcrumbs on every page: Home → Category → Tool (BreadcrumbList schema)
- [ ] Homepage: link to ALL tool categories (crawl path ≤ 3 clicks to any tool)
- [ ] **Create `/tools` hub page** — every tool listed with 1–2 line description + link (authority hub, target for internal links)
- [ ] Contextual inline links in blog posts → tools: "GC content"→/gc-calculator, "docking"→/docking, "primer design"→/primer-design, "PCR product"→/pcr-product-calculator

**Tool clusters (hub + spokes — build internal links in this shape):**

| Cluster | Hub | Spokes |
|---|---|---|
| Primer Design | /primer-design | /gc-calculator, /pcr-product-calculator, /primer, /primer-blast-alternative |
| Sequence Analysis | /blast | /dna-to-rna, /dna-3d, /msa |
| Docking | /docking | /autodock-vs-swissdock, /blast-vs-diamond |
| MSA | /msa | /clustal-vs-muscle, /clustal-vs-mafft |

### 3E. Glossary Consolidation (Week 7–8) — *merged from SEO plan §7.4*

> 100+ glossary pages have zero clicks (e.g. /glossary/sanger-sequencing 2,780 imp @ pos 59 → 0 clicks; /glossary/qpcr 779 imp @ 54 → 0 clicks). Thin content dilutes the site.

- [ ] Consolidate 100+ thin glossary pages → **20–30 comprehensive concept pages** (e.g. merge qpcr + rt-pcr + real-time-pcr → one `real-time-pcr` concept page)
- [ ] **301 redirect** every old glossary URL → its consolidated page (S3/CloudFront redirect rules)
- [ ] Very low-volume terms → become sections inside relevant tool pages instead of standalone pages
- [ ] Remove standalone glossary pages with <50 impressions AND no clicks (after 301)
- [ ] Expected result: ~612 → ~400 indexed pages, authority concentrated
- [ ] ⚠️ Coordinate with Phase 1 rule (sitemap regeneration auto-skips noindex) — after consolidation, regenerate sitemap

### 3F. /primer-design Position 44 Rescue (Week 5–6) — *merged from SEO plan §7.1*

Most critical tool-page improvement — position 44 = invisible for the core keyword.

- [ ] Major content overhaul: 1,500+ word guide on primer design principles
- [ ] Input parameter explanations with real examples; common use cases (cloning, qPCR, sequencing)
- [ ] Results interpretation guide + comparison with NCBI Primer-BLAST output
- [ ] 3+ internal links to related tools, 2–3 blog links
- [ ] Decide consolidation of competing pages (/primer vs /primer-design) — SEO plan says make /primer-design canonical; needs product decision before any redirect
- [ ] HowTo + FAQ schema
- [ ] **Target:** pos 10–15 in 4 weeks, top 5 in 8 weeks

### Phase 3 Exit Criteria
- [ ] 10+ keywords in top 5 positions
- [ ] Overall CTR > 1.5%
- [ ] Clicks/day > 100
- [ ] Rich results showing for tool pages

---

## 🆕 6. PHASE 4 — CONTENT EXPANSION (Week 6–12)

**Objective:** Capture queries we already get impressions for but rank poorly (or don't have pages for).

### New Pages — Priority Order (backed by GSC evidence)

| # | Page Type | Page | Evidence (impressions, current pos) | Priority |
|---|---|---|---|---|
| 1 | **Tool** | qPCR Primer Design Tool page | "qpcr primer design tool" 72 imp @ pos 44; "qpcr design tool" 51 @ 47; "qpcr primer design online" 60 @ 47 | 🔥🔥🔥 |
| 2 | **Tool** | Primer Dimer Checker | "primer dimer" 162 @ 27; "primer dimer check" 81 @ 28 | 🔥🔥🔥 |
| 3 | **Tool page upgrade** | GC Content Calculator (dedicated page) | 321+150+368+17 imp @ pos 8–18 | 🔥🔥🔥 |
| 4 | **Guide** | RT-PCR vs qPCR vs dPCR (pillar) | dozens of comparison queries @ pos 13–40 | 🔥🔥 |
| 5 | **Guide** | Sanger Sequencing Explained | 421+216+162+149 imp @ pos 53–64 | 🔥🔥 |
| 6 | **Guide** | What is an Amplicon + Amplicon Sequencing | 444+188+116 imp @ pos 52–74 | 🔥🔥 |
| 7 | **Guide** | Molecular Docking Tools Compared (SwissDock vs GNINA vs AutoDock vs Smina) | 1,294+26+20 imp @ pos 8–19 | 🔥🔥 |
| 8 | **Guide** | Clustal Omega vs MAFFT vs MUSCLE (consolidate) | We already rank 2–8 — consolidate into pillar | 🔥🔥 |
| 9 | **Guide** | TaqMan vs SYBR Green | 82+71+20 imp @ pos 12–24 | 🔥 |
| 10 | **Guide** | ADME & Pharmacokinetics basics | 102+93+22 imp @ pos 63–86 | 🔥 |

### Production Schedule
- **Weeks 6–7:** Pages 1–2 (new tools)
- **Weeks 8–9:** Pages 3–5
- **Weeks 10–11:** Pages 6–8
- **Weeks 12+:** Pages 9–10, then continue at 2 tools + 4 guides per month

### Content Template (every tool page must have)
1. H1 + 100-word intro (what it does, who it's for)
2. The tool itself (above the fold)
3. How to use (numbered steps)
4. Worked example
5. FAQ (5–8 questions from GSC/PAA)
6. Related tools module
7. Schema: SoftwareApplication + FAQPage + BreadcrumbList

### Content Template (every guide must have)
1. H1 = the exact query ("RT-PCR vs qPCR: Difference Explained")
2. Quick answer box (40–60 words, bolded — wins featured snippets)
3. Comparison table
4. Detailed sections with H2/H3
5. "Try the tool" CTA linking to our tool
6. FAQ + schema

### Phase 4 Exit Criteria
- [ ] Impressions 15–18K/day
- [ ] Clicks 250+/day
- [ ] New pages indexed within 7 days of publication
- [ ] 2+ new pages in top 10

---

## 🏆 7. PHASE 5 — AUTHORITY & SCALE (Month 3–6)

**Objective:** 30,000 impressions/day, 1,000 clicks/day.

### 5A. Backlinks (light but consistent — 5–8 hours/month)
- [ ] Submit to **awesome-bioinformatics** GitHub list (pull request)
- [ ] Answer questions on **r/bioinformatics** and **Biology StackExchange** where our tool genuinely solves the problem (no spam)
- [ ] Outreach to university bioinformatics course "resources" pages (they link free tools) — 10 emails/month
- [ ] Publish 1 linkable asset per quarter: "Best Free Primer Design Tools 2026," "Free Bioinformatics Tools for Students"
- [ ] Target: 5–10 quality referring domains/month

### 5B. AI Search Visibility (protect & grow — we're ALREADY cited by ChatGPT/Perplexity)
- [ ] Add `llms.txt` file at root
- [ ] Keep tool pages static HTML with clean, crawlable content (no heavy client-side rendering)
- [ ] Plain-text FAQs on every page
- [ ] Monitor GSC for AI-referral query patterns

### 5C. Retention & Engagement (turn clicks into rankings)
- [ ] Add "save my results" (free account) to tool pages
- [ ] Email capture on tool results (optional export)
- [ ] Monitor engagement in GA4 — engaged sessions > 60s correlate with rankings
- [ ] Investigate the **Sept 16 spike (83 clicks)** in GA4 — find the referral source, replicate it

### 5E. International Strategy — US / SG / UAE (merged from SEO plan §8.3/§9)

**US (64,313 imp, only 0.16% CTR — 11× worse than India):**
- [ ] Snippet optimization for US search patterns (US researchers add "NCBI"/"tool" to queries)
- [ ] US-centric examples in content (ClinVar, dbSNP, RefSeq)
- [ ] Trust signals: .edu backlinks, US institution testimonials
- [ ] Root causes to test: .in TLD trust, snippet mismatch, avg pos 14.52

**Singapore (protect + grow):**
- [ ] Weekly SG-specific GSC check; alert on position drops on key queries
- [ ] NUS/NTU/A*STAR references in tool documentation
- [ ] No technical change may ship without 2–3 day SG monitor (see Phase 2 guard)

**UAE (5,162 imp, 0.04% CTR) + replicate to AU/HK/KR/JP/TW:**
- [ ] Fix UAE snippet (same title/meta pattern as P0 fixes)
- [ ] Confirm CloudFront edge performance for these regions
- [ ] Region-specific examples in tool docs; institutional backlinks

**hreflang (from SEO plan §5.4):**
- [ ] Add hreflang `en-IN` / `en-US` / `en-SG` + `x-default` sitewide (primer.html already has en + en-IN + x-default as the pattern — roll out to all pages via shared header)
- [ ] Keep GSC preferred domain = www (config already redirects apex → www)

### 5F. Academic Partnership Backlinks (expanded from SEO plan §9.3)
- [ ] Bioinformatics department outreach — free coursework access + "Recommended by X University" badge
- [ ] Embeddable widgets for course pages (attribution link)
- [ ] Tool validation/benchmark papers citing vigyanllm.in (use /validation as the hook — Phase 2 credibility asset already live)
- [ ] Expand /academic-partnership page (118 imp, 10 clicks today)
- [ ] KPI: +5 referring .edu/.ac.in domains per quarter

### 5D. Scale Checks
- [ ] Repeat keyword-gap analysis monthly (GSC queries with 100+ impressions, position 8–30 → new/expansion targets)
- [ ] Refresh top 20 pages every quarter (update year in titles, add new FAQs)
- [ ] Keep publishing: 2 tools + 4 guides per month, indefinitely

---

## 📋 8. ONGOING — WEEKLY OPERATING RHYTHM

| Day | Task | Time |
|---|---|---|
| Monday | Check GSC: clicks, impressions, position, new errors | 15 min |
| Monday | Check GSC → Pages for new crawl errors | 10 min |
| Wednesday | Check PSI on 1 rotating page (homepage + top tools cycle) | 10 min |
| Friday | Content work (new pages / expansions) | 3–5 hrs |
| Monthly | Keyword-gap analysis, CWV report, backlink check, this document update | 2 hrs |

---

## 🎯 9. KPI MILESTONES

### 9A. Primary KPIs — 4/8/12-week view (merged from SEO plan §11.1)

| KPI | Baseline (Sep 2026) | 4-Week | 8-Week | 12-Week |
|---|---|---|---|---|
| Daily impressions | ~5,500 | 10,000 | 20,000 | **30,000** |
| Daily clicks | ~25 | 100 | 400 | **1,000** |
| Site-wide CTR | 0.52% | 1.0% | 2.0% | 3.3% |
| Avg position (desktop) | 12.48 | 10 | 8 | 6 |
| Avg position (mobile) | 10.63 | 8 | 6 | 5 |
| Mobile impression share | 7.7% | 15% | 25% | 30% |

### 9B. Secondary KPIs (merged from SEO plan §11.2)

| KPI | Baseline | Target | Track via |
|---|---|---|---|
| ncbi blog CTR | 0.13% | **3%+** | GSC page filter (re-measure ~2026-10-14) |
| primer3-vs-idt CTR | 0.005% | **2%+** | GSC page filter (re-measure ~2026-10-14) |
| /primer-design position | 44.33 | <15 (4wk), <5 (8wk) | GSC query filter |
| US CTR | 0.16% | 0.5%+ | GSC country filter |
| Indexed pages (clean) | ~418 | <400 after glossary consolidation | GSC index coverage |
| Core Web Vitals (mobile) | unknown | all "Good" | PSI / CrUX |
| Schema rich results | partial | 10+ pages with rich results | GSC enhancements |
| New .edu/.ac.in domains | baseline | +5/quarter | Ahrefs/Majestic |

### 9C. Weekly Tracking Checklist (merged from SEO plan §11.3)

- [ ] Download GSC 7-day data, compare vs previous week (clicks/impr/CTR/pos)
- [ ] Check GSC Enhancements report for new rich results
- [ ] Run PSI on homepage + top 5 tool pages (mobile AND desktop)
- [ ] Check GA4: organic traffic, bounce, session duration on tool pages
- [ ] Verify no new crawl errors in GSC coverage
- [ ] Monitor top 20 target query rankings
- [ ] Review backlink profile for new .edu/.ac.in links

### 9D. Long-Range Milestones (original table)

| Milestone | Impressions/day | Clicks/day | CTR | Avg Pos | Indexed |
|---|---|---|---|---|---|
| Baseline (now) | 6,000 | 25 | 0.4% | 8.0 | 418 |
| Day 30 | 10,000 | 100 | 1.0% | 6.5 | 500+ |
| Day 60 | 15,000 | 250 | 1.7% | 5.5 | 600+ |
| Day 90 | 25,000 | 500 | 2.0% | 4.5 | 700+ |
| Day 180 | **30,000+** | **1,000** | **3.3%** | **≤ 4.0** | 800+ |

---

## ⚡ 2.5 PRIORITY MATRIX (merged from SEO plan §10 — impact vs effort)

| Priority | Action | Impact | Effort | Timeline | Status |
|---|---|---|---|---|---|
| **P0** | Fix ncbi-blog CTR | +29 clicks/day | 2h | Week 1 | ✅ 2026-09-23 |
| **P0** | Fix primer3-vs-idt CTR | +12 clicks/day | 1h | Week 1 | ✅ 2026-09-23 |
| **P0** | URL canonicalization | authority consolidation | 4h | Week 1 | ✅ canonicals/robots/sitemap done 2026-09-22; www redirect config verified (live re-check pending — network timeout) |
| **P1** | Remaining title/meta audit (all below-avg CTR pages) | +15–20 clicks/day | 8h | Week 2–3 | ⬜ = Phase 3A table |
| **P1** | Schema on tool pages | rich results | 8h | Week 2 | ◐ SoftwareApplication/FAQPage deployed; HowTo/Breadcrumb rollout = 3C |
| **P1** | Core Web Vitals / mobile | 3–4× mobile imps | 16h | Week 9 | ◐ Phase 2 in progress |
| **P2** | /primer-design overhaul | pos 44 → 10–15 | 16h | Week 5–6 | ⬜ = 3F |
| **P2** | Internal linking + /tools hub | authority flow | 8h | Week 3–4 | ⬜ = 3D |
| **P2** | Glossary consolidation | remove thin content | 16h | Week 7–8 | ⬜ = 3E |
| **P3** | New blog content (8–12 posts) | +2–3K imps/day | 40h | Week 9–12 | ⬜ = Phase 4 |
| **P3** | Academic backlink outreach | authority | ongoing | Week 5+ | ⬜ = 5F |

**Week-by-week rollup:** W1 canonicalization + P0 CTR fixes → W2 schema + sitemap/robots → W3–4 below-avg CTR titles + internal linking + /tools hub → W5–6 /primer-design overhaul + tool enrichment → W7–8 cross-tool linking + glossary consolidation → W9 mobile CWV + new content → W10–12 remaining content + US optimization → ongoing SG monitoring + academic outreach.

---

## 📎 APPENDIX A — robots.txt

```
User-agent: *
Allow: /
Disallow: /partials/
Disallow: /api/

Sitemap: https://www.vigyanllm.in/sitemap.xml
```

## 📎 APPENDIX B — Schema Template (SoftwareApplication)

```json
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "Primer Design & Specificity Check Tool",
  "applicationCategory": "ScienceApplication",
  "operatingSystem": "Web",
  "description": "Free online primer design tool with BLAST-based specificity checking, Tm calculation, GC analysis and dimer detection.",
  "offers": { "@type": "Offer", "price": "0", "priceCurrency": "USD" }
}
```

## 📎 APPENDIX C — Master Update List ("What We Need To Update")

**Files/Code:**
1. `robots.txt` — add Disallow rules + sitemap
2. `sitemap.xml` — rebuild, canonical URLs only
3. `includes.js` — replace client-side partial loading with server-side includes
4. `dna-loop.json` — remove or lazy-load (homepage)
5. `amcharts4-core.js`, `amcharts4-maps.js`, `worldIndiaLow.js` — lazy-load
6. `logo.png` — convert to SVG/WebP
7. Font loading (Google Fonts link) — cut weights, preload critical fonts
8. GTM/gtag snippet — defer to user interaction
9. Google Sign-In script — load on demand
10. `reveal.js` — remove duplicate load
11. `/api/reviews/*` calls — add timeout/fallback or server-render
12. Cache-Control headers on all static assets — 1 year immutable
13. Add preconnect link hints in `<head>`
14. Canonical tags on all pages
15. Title tags + meta descriptions (all tool pages — see Phase 3A table)
16. Add JSON-LD schema to all tool pages
17. Add breadcrumbs + Related Tools module to all pages
18. Add `llms.txt` at site root

**Content:**
19. Expand 6 money pages (Primer BLAST first)
20. 10 new pages per Phase 4 table
21. Ongoing: 2 tools + 4 guides/month

---

> **Sources merged:** this playbook + `vigyanllm_seo_optimization_plan.md` (GSC Jun 20–Sep 19 2026 + PSI, dated Sep 22 2026). Where the two conflicted, resolution notes are inline (anti-cannibalization policy wins for blog titles; `SoftwareApplication` kept over `WebApplication`).
> **Last updated:** Sept 23 2026 · Update this file at every monthly review

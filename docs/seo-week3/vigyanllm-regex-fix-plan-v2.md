# VigyanLLM Regex Fix Plan — v2 (Execution Supplement)

**Date:** 26 Oct 2026
**Supersedes:** v1 volume projections and timeline (v1 audit data still valid)
**Context:** Week 3 closed (`c0c314ba`), 9 URLs in GSC queue, 154 critical coverage issues remaining, next checkpoint Nov 2
**Status:** Fact-checked + fixes baked into main body (2026-10-26). Safe to execute without reading §12.

---

## 0. What changed since v1

v1 was written without knowing Week 3 just closed. Three things now differ:

1. **8 comparison pages are already live** (`/autodock-vs-vina`, `/blast-vs-bowtie2`, `/free-blast-alternative`, `/free-molecular-docking`, `/free-msa-software`, `/free-primer-design-tool`, `/msa-tools-comparison`, `/primer-design-software-comparison`). v1's Issue E ("/vs/ hub — build 30-40 comparison pages") is **partially done**. Adjust remaining scope to ~22-32 pages, not 30-40.
2. **FAQ schema blocks for 10 pages are already written** (Week 2 deliverables, now committed at `docs/seo-week3/vigyanllm-week2-ctr-optimization-deliverables.md`). v1's Sprint 2 ("Add FAQPage schema to each of those 30 pages") is **partially done** for the highest-value pages.
3. **`/blog/ncbi-primer-blast-guide` has NOT been refreshed yet.** Issue F (Prime Mover) is still 100% open. This remains the single highest-leverage action.

---

## 1. Honest volume re-projection (corrected from v1)

v1's "conservative +1,535 clicks (+68%)" was actually moderate-to-aggressive. Title/meta rewrites typically lift CTR 20-50%, not 3-7x. Featured snippet wins are binary and slow. New pages take 60-90 days to compound. Here's the honest version:

### Per-issue honest uplift (90-day horizon)

| Issue | v1 "conservative" | v2 honest conservative | v1 "moderate" | v2 honest moderate | Why the correction |
|---|---|---|---|---|---|
| A (AI-leak pages) | +135 | **+30** | +400 | **+150** | Bot/human mix unknown; even human queries want AI answers, not webpages |
| B (Title/meta + schema, 30pg) | +330 | **+100** | +780 | **+250** | Title rewrites lift CTR 20-50%, not 3-7x. 0.18% → 0.3-0.4% realistic |
| C (Featured snippets) | +125 | **+50** | +250 | **+150** | Snippet wins are binary; expect 2-5 wins in 90 days, not 10 |
| D (Glossary refresh) | +250 | **+50** | +500 | **+150** | Glossary pages rank 50-90; internal links alone won't push to top 20 in 90 days |
| E (/vs/ hub) | +150 | **+50** | +600 | **+200** | 8 already live; 22 new pages × 2-9 clicks each in first 90 days is realistic |
| F (Prime Mover blog) | +365 | **+200** | +835 | **+500** | CTR 0.14% → 0.3-0.5% realistic in 90 days; 1.0% requires 6+ months |
| G (Calculator internal links) | +150 | **+75** | +400 | **+200** | 3-5 calculators move from pos 11-19 to pos 5-10; each gains 15-40 clicks |
| H (/india/ cluster) | +30 | **+15** | +200 | **+60** | India keywords are low volume; 6 pages might generate 500-2K imp in 90 days |
| **TOTAL (90-day)** | **+1,535** | **+570** | **+3,965** | **+1,660** | |
| **% uplift** | +68% | **+25%** | +177% | **+74%** | |

### Impression uplift (90-day horizon)

| Scenario | v1 claim | v2 honest |
|---|---|---|
| Conservative | +18,000 | **+5,000 to +10,000** |
| Moderate | +75,000 | **+25,000 to +40,000** |

### 6-month and 12-month honest projections

| Horizon | Clicks | Impressions | Δ vs baseline |
|---|---|---|---|
| 90 days (conservative) | 2,236 → **2,800** | 365K → **372K** | +25% clicks |
| 90 days (moderate) | 2,236 → **3,900** | 365K → **395K** | +74% clicks |
| 6 months (conservative) | 2,236 → **3,200** | 365K → **400K** | +43% clicks |
| 6 months (moderate) | 2,236 → **4,500** | 365K → **425K** | +101% clicks |
| 12 months (aggressive) | 2,236 → **5,600** | 365K → **445K** | +150% clicks |

> **Baseline note:** the "2,236" is v1's 3-month click figure carried over for continuity.
> The VERIFIED 28-day baseline (Day-0 comparison anchor) is **1,262 clicks / 137,323
> impressions / 0.92% CTR / pos 8.5** (commit `4457f38a`). Use 1,262 for 28-day KPI
> comparisons; use 2,236 only when comparing 3-month rolling windows like the table above.

**The honest takeaway:** Issue F (Prime Mover blog refresh) is still the single biggest lever at +200 to +500 clicks in 90 days. Everything else is supporting cast. If you only do ONE thing in November, do Issue F.

---

## 2. Day 0 pre-flight (do this BEFORE Sprint 0)

Before any of the v1 sprints start, run these 3 checks. They take 30 minutes total and prevent wasted work.

### Pre-flight 1 — AI-leak validation (Issue A decision)

v1 says "decide by Week 2 if file 2's 27K impressions are bot or human." Do it in 30 minutes instead:

1. Open incognito browser
2. Search Google for these 5 queries (sampled from file 2):
   - `evaluate the life sciences company integrated dna technologies on oligoanalyzer tool`
   - `can i access trusted primer design resources for free?`
   - `what tools are popular for calculating melting temperature?`
   - `how do i choose a leading oligoanalyzer for dna studies?`
   - `who offers a reliable online oligoanalyzer with detailed metrics?`
3. For each, note:
   - Does Google's AI Overview appear at top? (Yes/No)
   - Does VigyanLLM appear in top 10? (Yes/No, position)
   - Does the snippet look like it answers the question? (Yes/No)
4. **Decision rule:**
   - If AI Overview appears on 4/5 → these are AI-stolen, NOT bot traffic. Build `/vs/evaluate-*` answer pages (Issue A2 path). Skip the bot hypothesis.
   - If AI Overview appears on 0-1/5 → these may be bot traffic. Exclude from analytics (Issue A1 path).
   - Mixed → build answer pages for the human-shaped queries, exclude the rigid "evaluate X on Y" queries.

### Pre-flight 2 — Current title/meta audit

Pull current title tags and meta descriptions for the top 30 pages (use `curl -s URL | grep -i '<title>\|description'` or Screaming Frog). Save to `docs/seo-week3/title-meta-audit-baseline.csv`. You need this baseline to measure Sprint 2 impact.

### Pre-flight 3 — Reconcile with existing Week 2-6 deliverables

Before Sprint 2 starts, check what's already done:

- [ ] `/primer-design` — has FAQ schema been added? (Week 2 deliverable)
- [ ] `/tm-calculator` — has FAQ schema been added? (LIVE: already has FAQPage ✓ — skip)
- [ ] `/idt-vs-vigyanllm` — full HTML deployed? (LIVE: yes, has FAQPage ✓ — skip)
- [ ] `/ncbi-primer-blast-vs-vigyanllm` — full HTML deployed?
- [ ] 8 new comparison pages from Week 3 — are they indexed? (check GSC URL Inspection)

Anything already done → remove from Sprint 2 scope.

---

## 3. Concrete templates for Sprint 1 (Prime Mover — Issue F)

v1 says "rewrite title/meta" but doesn't give the actual strings. Here are the exact strings to use.

> **⚠ BEFORE PASTING ANY FAQ SCHEMA BELOW:** This site enforces a FAQ-mirror gate — the
> visible FAQ items on a page must EXACTLY match that page's FAQPage schema (questions
> and answers, character-for-character after link-text flattening). `/blog/ncbi-primer-blast-guide`
> currently has **5 visible FAQ items + a matching 5-question schema**. The template in §3.5
> is pre-built to the correct **7-question** state (existing 5 kept verbatim + 2 new added
> to BOTH visible and schema). If you use §3.5, paste BOTH the visible snippet (§3.5a) AND
> the full schema (§3.5b). Never paste schema without adding the same items to the visible FAQ.

### 3.1 — `/blog/ncbi-primer-blast-guide` title + meta

**Current title (61 ch):** `NCBI Primer-BLAST Guide — Free Primer Design Tool | VigyanLLM`

**New title (59 chars):**
```
NCBI Primer-BLAST Guide 2026: Free Primer Design Tutorial
```

**New meta description (155 chars):**
```
Complete 2026 guide to NCBI Primer-BLAST. Free online PCR primer design tool with specificity check. Step-by-step tutorial, results, and free alternatives.
```

### 3.2 — Definitional answer block (insert as FIRST paragraph after H1)

```html
<p class="lead"><strong>NCBI Primer-BLAST</strong> is a free online tool from the National Center for Biotechnology Information that designs target-specific PCR primers using the Primer3 algorithm and validates them with BLAST specificity searches against the user-selected organism database. It is widely used in published research protocols worldwide.</p>
```

*(50 words, definitional, snippet-eligible. Note: the original ">10,000 peer-reviewed publications" claim was removed — no source = no claim, per the site's verifiable-claims rule.)*

### 3.3 — Quick Verdict table (insert immediately after the answer block)

```html
<h2>Quick Verdict: NCBI Primer-BLAST</h2>
<table>
  <thead><tr><th>Feature</th><th>NCBI Primer-BLAST</th></tr></thead>
  <tbody>
    <tr><td>Free?</td><td>Yes</td></tr>
    <tr><td>Login required?</td><td>Yes (NCBI account)</td></tr>
    <tr><td>Speed</td><td>2-5 minutes per design</td></tr>
    <tr><td>Specificity check</td><td>Yes (whole-genome BLAST)</td></tr>
    <tr><td>Best for</td><td>Research-grade primers, published protocols</td></tr>
    <tr><td>Free alternative</td><td><a href="/primer-design">VigyanLLM Primer Design</a> (no login, same Primer3 engine)</td></tr>
  </tbody>
</table>
```

### 3.4 — Related tools sidebar (insert after the verdict table)

```html
<aside class="related-tools">
  <h3>Related VigyanLLM Tools</h3>
  <ul>
    <li><a href="/pcr-product-calculator">PCR Product Size Calculator</a></li>
    <li><a href="/tm-calculator">Tm Calculator</a></li>
    <li><a href="/gc-calculator">GC Content Calculator</a></li>
    <li><a href="/primer">Primer Specificity Check</a></li>
    <li><a href="/primer-blast-alternative">Primer-BLAST Alternative</a></li>
    <li><a href="/blast">Free BLAST Tool</a></li>
    <li><a href="/msa">Multiple Sequence Alignment</a></li>
    <li><a href="/docking">Molecular Docking</a></li>
  </ul>
</aside>
```

*(All 8 links verified 200/0-hops/canonical-exact live on 2026-10-26.)*

### 3.5 — FAQ schema — MIRROR-SAFE 7-question version

The page already has these 5 questions (KEEP them verbatim — do not edit). We ADD 2 new ones for a 7-item mirror-matched set.

**Existing 5 (already on page, keep as-is):**
1. What is the difference between Primer3 and Primer-BLAST?
2. What database should you use for Primer-BLAST specificity checking?
3. How many off-target hits are acceptable for a primer pair?
4. Can I use Primer-BLAST for qPCR primer design?
5. How is VigyanLLM different from NCBI Primer-BLAST?

**2 NEW questions to add to BOTH visible FAQ section AND schema:**
6. Is NCBI Primer-BLAST free?
7. What is the best free NCBI Primer-BLAST alternative?

#### 3.5a — Visible FAQ HTML for the 2 NEW items (append to the existing FAQ section, after item 5)

Paste these two blocks right after the 5th existing FAQ `<div itemscope itemtype="https://schema.org/Question">…</div>`, using the SAME markup structure the page already uses:

```html
<div itemscope itemtype="https://schema.org/Question" style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;padding:24px;margin:24px 0 32px">
  <h3 itemprop="name">Is NCBI Primer-BLAST free?</h3>
  <div itemprop="acceptedAnswer" itemscope itemtype="https://schema.org/Answer">
    <p itemprop="text" style="color:#475569;font-size:14px">Yes, NCBI Primer-BLAST is completely free, but requires a free NCBI account (email registration). For a no-login alternative with the same Primer3 v2.6.1 engine, use <a href="/primer-design">VigyanLLM Primer Design</a>.</p>
  </div>
</div>
<div itemscope itemtype="https://schema.org/Question" style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;padding:24px;margin:24px 0 32px">
  <h3 itemprop="name">What is the best free NCBI Primer-BLAST alternative?</h3>
  <div itemprop="acceptedAnswer" itemscope itemtype="https://schema.org/Answer">
    <p itemprop="text" style="color:#475569;font-size:14px">The best free NCBI Primer-BLAST alternative is <a href="/primer-design">VigyanLLM Primer Design</a>. It uses the same Primer3 v2.6.1 engine, includes whole-genome BLAST specificity checking, requires no login, and typically returns results in under a minute.</p>
  </div>
</div>
```

#### 3.5b — Full 7-question FAQPage schema (replace the existing `<script type="application/ld+json">` FAQPage block in `<head>`)

The flattened visible text of items 1–5 below matches the existing schema verbatim; items 6–7 match §3.5a's visible text (link text flattened). This keeps the mirror exact.

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "What is the difference between Primer3 and Primer-BLAST?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Primer-BLAST adds BLAST specificity checking on top of Primer3's design algorithm. Primer3 alone designs primers based on thermodynamic parameters but does not verify that they bind uniquely to the intended target."
      }
    },
    {
      "@type": "Question",
      "name": "What database should you use for Primer-BLAST specificity checking?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Use the RefSeq mRNA database for cDNA targets and the whole-genome database (refseq_genomes or nt) for genomic DNA. For human targets, the Genome Reference Consortium (GRCh38/hg38) is the most up-to-date."
      }
    },
    {
      "@type": "Question",
      "name": "How many off-target hits are acceptable for a primer pair?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Ideally zero with perfect 3′-end complementarity. Up to 2–3 mismatches in the last 5 bases of the 3′ end may be tolerated, but any perfect match in the 3′ half with ≥15 bp homology should be rejected."
      }
    },
    {
      "@type": "Question",
      "name": "Can I use Primer-BLAST for qPCR primer design?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes, Primer-BLAST supports qPCR primer design. Select the \"Primer must span an exon-exon junction\" option to ensure mRNA specificity. Set amplicon size to 70–150 bp for optimal qPCR efficiency. VigyanLLM also offers dedicated qPCR primer design with probe compatibility checking."
      }
    },
    {
      "@type": "Question",
      "name": "How is VigyanLLM different from NCBI Primer-BLAST?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "VigyanLLM builds on Primer-BLAST's foundation by adding 24-step biophysical validation, secondary structure and primer-dimer prediction, SNP masking via dbSNP/ClinVar, multiplex compatibility scoring, and batch processing up to 100 designs. It also provides PDF/Excel reports and a REST API for automated workflows."
      }
    },
    {
      "@type": "Question",
      "name": "Is NCBI Primer-BLAST free?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes, NCBI Primer-BLAST is completely free, but requires a free NCBI account (email registration). For a no-login alternative with the same Primer3 v2.6.1 engine, use VigyanLLM Primer Design."
      }
    },
    {
      "@type": "Question",
      "name": "What is the best free NCBI Primer-BLAST alternative?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "The best free NCBI Primer-BLAST alternative is VigyanLLM Primer Design. It uses the same Primer3 v2.6.1 engine, includes whole-genome BLAST specificity checking, requires no login, and typically returns results in under a minute."
      }
    }
  ]
}
</script>
```

*(Note: "typically returns results in under a minute" — the original "~30 seconds" SLA claim was softened; no benchmark backs a 30-second promise.)*

### 3.6 — HowTo schema (insert in `<head>` after the FAQ schema)

The page already has 1 HowTo block. This is an OPTIONAL improved replacement — only paste if you intend to replace the existing HowTo, not add a second one (duplicate HowTo = schema spam risk).

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "HowTo",
  "name": "How to Use NCBI Primer-BLAST",
  "totalTime": "PT5M",
  "step": [
    {"@type": "HowToStep", "position": 1, "name": "Go to NCBI Primer-BLAST", "text": "Visit https://www.ncbi.nlm.nih.gov/tools/primer-blast/"},
    {"@type": "HowToStep", "position": 2, "name": "Paste your DNA sequence", "text": "Paste your target DNA sequence in FASTA or plain text format"},
    {"@type": "HowToStep", "position": 3, "name": "Set parameters", "text": "Set PCR product size, primer Tm range (58-62°C), GC content (40-60%)"},
    {"@type": "HowToStep", "position": 4, "name": "Select organism database", "text": "Choose the organism for specificity checking (e.g., Homo sapiens)"},
    {"@type": "HowToStep", "position": 5, "name": "Click 'Get Primers'", "text": "Submit and wait 2-5 minutes for results"},
    {"@type": "HowToStep", "position": 6, "name": "Review primer pairs", "text": "Evaluate top primer pairs by Tm, GC content, specificity, and self-complementarity"}
  ]
}
</script>
```

---

## 4. Title/meta rewrite templates for top 10 pages (Sprint 2 starter pack)

These are the 10 highest-priority pages for Sprint 2. Each row gives the exact title + meta to use.

| URL | New Title (≤60ch) | New Meta Description (≤155ch) |
|---|---|---|
| `/primer3-vs-idt` | Primer3 vs IDT PrimerQuest: 2026 Comparison | Primer3 vs IDT PrimerQuest vs VigyanLLM — which primer design tool wins? Free vs paid, features, accuracy. Try VigyanLLM free. |
| `/blog/best-primer-design-software-2026` | Best Primer Design Software 2026: Free + Paid | Top primer design software 2026. Free and paid tools ranked. VigyanLLM, SnapGene, Primer3, IDT, Benchling compared. |
| `/blog/best-free-primer-design-tool-2026` | Best Free Primer Design Tool 2026: Top 10 Ranked | Ranked list of best free primer design tools 2026. VigyanLLM, Primer3, NCBI, IDT compared. Features, accuracy, ease of use. |
| `/tm-calculator` | Free Tm Calculator — Primer Melting Temperature Online | Calculate primer melting temperature (Tm) free online. SantaLucia 1998 nearest-neighbor method. Salt and Mg2+ corrections. No login. |
| `/blog/primer-design-tool-comparison` | Primer Design Tool Comparison 2026: 10 Tools Ranked | 10 primer design tools compared. IDT, Primer3, NCBI, VigyanLLM, Benchling, SnapGene. Features, accuracy, price. Free. |
| `/blog/rt-pcr-vs-qpcr` | RT-PCR vs qPCR: What's the Difference? [2026 Guide] | RT-PCR vs qPCR vs RT-qPCR explained clearly. Differences, when to use each, primer design considerations. Free tools included. |
| `/idt-vs-vigyanllm` | IDT OligoAnalyzer vs VigyanLLM: 2026 Comparison | IDT vs VigyanLLM — free primer design comparison. Features, pricing, accuracy. See why researchers switch to VigyanLLM. |
| `/blog/taqman-vs-sybr-green` | TaqMan vs SYBR Green: Which qPCR Chemistry Wins? | TaqMan vs SYBR Green qPCR — which is better? Cost, sensitivity, specificity, primer design. Free probe design tool. |
| `/autodock-vs-swissdock` | AutoDock Vina vs SwissDock: 2026 Comparison | AutoDock Vina vs SwissDock — which docking tool wins? Compare speed, accuracy, ease of use, GPU support. Free alternatives. |
| `/clustal-vs-muscle` | Clustal Omega vs MUSCLE: 2026 MSA Comparison | Clustal Omega vs MUSCLE vs MAFFT — which MSA tool is best? Compare accuracy, speed, output. Free online MSA tools. |

### FAQ schema status (verified live 2026-10-26) — read before adding ANY schema

**8 of these 10 pages ALREADY have FAQPage schema deployed.** Adding a second, different FAQPage block to a page that already has one = schema spam risk + mirror-gate breakage. So:

| URL | Title/meta rewrite? | Add FAQ schema? |
|---|---|---|
| `/primer3-vs-idt` | ✅ yes | ❌ already has FAQPage — skip |
| `/blog/best-primer-design-software-2026` | ✅ yes | ✅ **YES — no FAQPage yet** |
| `/blog/best-free-primer-design-tool-2026` | ✅ yes | ❌ already has FAQPage — skip |
| `/tm-calculator` | ✅ yes | ❌ already has FAQPage — skip |
| `/blog/primer-design-tool-comparison` | ✅ yes | ❌ already has FAQPage — skip |
| `/blog/rt-pcr-vs-qpcr` | ✅ yes | ❌ already has FAQPage — skip |
| `/idt-vs-vigyanllm` | ✅ yes | ❌ already has FAQPage — skip |
| `/blog/taqman-vs-sybr-green` | ✅ yes | ✅ **YES — no FAQPage yet** |
| `/autodock-vs-swissdock` | ✅ yes | ❌ already has FAQPage — skip |
| `/clustal-vs-muscle` | ✅ yes | ❌ already has FAQPage — skip |

**Net: Sprint 2 FAQ-schema work on this list = 2 pages** (`/blog/best-primer-design-software-2026` and `/blog/taqman-vs-sybr-green`), not 6. Title/meta rewrites still apply to all 10.

**Reminder:** any FAQ schema you add must have a matching visible FAQ section on the page (mirror gate). Don't paste schema onto a page with no visible FAQ items — build both together.

---

## 5. Adjusted timeline (start Nov 3, not "today")

v1 says "Day 1-3: Pull blog content for Sprint 1." Wrong — Week 3 just closed, Google is mid-crawl, you don't want to push more changes until the Day 7 check (Nov 2) confirms the 9 new URLs are indexing cleanly.

### Revised calendar

| Date | Phase | Action |
|---|---|---|
| **Oct 27 - Nov 2** | Crawl freeze | No changes. Let Google index the 9 new URLs. Run Day 0 pre-flight (30 min). |
| **Nov 2** | Day 7 check | URL Inspection on 9 URLs. If ≥5 indexed → proceed. If <5 → diagnose before Sprint 1. |
| **Nov 3-9** | Sprint 1 (Prime Mover) | Issue F: refresh `/blog/ncbi-primer-blast-guide` using §3 templates above (mirror-safe 7-Q FAQ). 5-day sprint. |
| **Nov 10** | Sprint 1 measure | Submit refreshed blog URL to GSC. Wait 14 days. |
| **Nov 10 - Dec 7** | Sprint 2 (Title/meta + schema) | Issues B + C + D. 30 pages, batched 10/week. Use §4 templates for top 10 (only 2 need FAQ schema). |
| **Dec 8 - 31** | Sprint 3 (/vs/ hub) | Issue E. Build 15-22 new comparison pages (8 already live). |
| **Jan 1 - 15** | Sprint 4 (Calculator promotion) | Issue G. Add sidebars to top 3 blog pages. |
| **Jan 16 - 31** | Sprint 5 (India cluster kickoff) | Issue H. Build 3 India pages. |
| **Feb 1** | Day 90 review | Full KPI check vs baseline. Decide whether to scale (moderate scenario) or iterate. |

---

## 6. Reconciliation with existing Week 2-6 deliverables

Before executing any v1 sprint, check what's already done. Here's the mapping:

| v1 Sprint | v1 Scope | Already done (Week 2-6) | Remaining scope |
|---|---|---|---|
| Sprint 2 (Title/meta + FAQ schema) | 30 pages | FAQ schema for 8 of top-10 (live-verified) + Week 2 blocks for 10 | Title/meta for 30 pages + FAQ schema for ~20 more (only 2 of the §4 top-10) |
| Sprint 3 (/vs/ hub) | 30-40 pages | 8 comparison pages live (Week 3) | 22-32 new pages |
| Sprint 4 (AI-leak landing pages) | 5-20 pages | 0 done | 5-20 pages (after Day 0 pre-flight decision) |
| Sprint 5 (India cluster) | 3-6 pages | 0 done | 3-6 pages |

**Net:** v1's total scope is ~25% already done. Adjust effort estimates down accordingly.

---

## 7. Updated regex filter recommendations

v1 §7 recommendations are correct. Add these 2 new filters:

### 7.7 — New filter: VigyanLLM comparison queries

```
vigyanllm.+(vs|versus|alternative|compared|better|or)
```

**Use case:** Track queries where searchers are comparing VigyanLLM to competitors (e.g., "vigyanllm vs idt", "vigyanllm alternative"). This is your direct comparison-page performance.

### 7.8 — New filter: Tool-action queries (high commercial intent)

```
(design|check|calculate|run|find|search).+(primer|blast|msa|docking|pcr|grna|amplicon)
```

**Use case:** Track queries where the user wants to USE a tool right now (e.g., "design primers for pcr", "calculate tm for primer", "run blast search"). These are your highest-conversion-intent queries. Cross-reference with `/primer-design`, `/blast`, `/docking` page filters.

---

## 8. Risks (v1 risks + 3 new ones)

### v1 risks (still valid)

1. AI-leak classification uncertainty (Issue A)
2. Featured snippet cannibalization (Issue F vs `/glossary/pcr-blast`)
3. India cluster DPDP/Sovereign AI sensitivity
4. Title-tag rewrite ranking risk
5. Mobile vs desktop CTR inversion

### New risks (v2)

6. **Sprint 1 timing risk:** Refreshing `/blog/ncbi-primer-blast-guide` while Google is still indexing the 9 new Week 3 URLs may cause crawl-budget contention. **Mitigation:** Wait until Nov 2 Day 7 check confirms ≥5/9 indexed before starting Sprint 1.

7. **FAQ schema duplication risk:** 8 of the 10 §4 pages already have FAQPage live. Adding a second, different FAQPage block = schema spam + mirror breakage. **Mitigation:** §4 table above now flags exactly which 2 pages need schema; skip the other 8. For any page that already has schema, either skip or merge new questions into the EXISTING visible+schema pair (never add schema alone).

8. **Comparison page cannibalization risk:** 8 new comparison pages from Week 3 (`/autodock-vs-vina`, `/blast-vs-bowtie2`, etc.) may cannibalize v1's planned `/vs/` pages. For example, `/autodock-vs-vina` (live) vs `/vs/autodock-vina-vs-gnina` (planned) target overlapping keywords. **Mitigation:** Before building Sprint 3 pages, audit the 8 live pages' target keywords. Skip any `/vs/` page that overlaps >50% with an existing page.

---

## 9. Measurement update

> **Baseline note:** the "from 1,340" figures in the original v2 draft were the *claimed*
> numbers. The VERIFIED 28-day baseline is **1,262 clicks / 137,323 impressions / 0.92% CTR /
> pos 8.5** (commit `4457f38a`). The "from" values below now use 1,262.

### Week-by-week tracking (v2)

| Week | Metric | Target |
|---|---|---|
| Nov 2 (Week 1) | 9 new URLs indexed | ≥5/9 |
| Nov 9 (Week 2) | Sprint 1 blog refresh live | Done |
| Nov 16 (Week 3) | Blog CTR (post-refresh, 7 days) | ≥0.2% (from 0.14%) |
| Nov 23 (Week 4) | Sprint 2 first 10 pages live | Done |
| Nov 30 (Week 5) | Sprint 2 next 10 pages live | Done |
| Dec 7 (Week 6) | Sprint 2 last 10 pages live | Done |
| Dec 14 (Week 7) | Total CTR (top 30 pages) | ≥0.4% (from 0.18%) |
| Dec 21 (Week 8) | Sprint 3 first 8 /vs/ pages live | Done |
| Dec 28 (Week 9) | Sprint 3 next 8 /vs/ pages live | Done |
| Jan 4 (Week 10) | Total clicks (rolling 28-day) | ≥1,800 (from 1,262) |
| Jan 11 (Week 11) | Sprint 4 calculator sidebars live | Done |
| Jan 18 (Week 12) | Sprint 5 India pages live | Done |
| Jan 25 (Week 13) | Day 90 review | Conservative target: ≥2,800 clicks (3-mo rolling) |

### Day 90 acceptance criteria (revised)

- [ ] Total clicks ≥ 2,800 (vs v1's 3,000 — more honest)
- [ ] `/blog/ncbi-primer-blast-guide` CTR ≥ 0.3% (vs v1's 0.5% — more honest)
- [ ] At least 1 featured snippet win
- [ ] At least 22 `/vs/` pages live (8 existing + 14-22 new)
- [ ] `/india/` cluster live with 3 pages
- [ ] At least 5 `/vs/evaluate-*` pages live (if Day 0 pre-flight confirms AI-leak is human traffic)

---

## 10. What to do RIGHT NOW (today, Oct 26)

1. **Save this v2 document** alongside v1. v1 has the audit data; v2 has the execution plan.
2. **Run Day 0 pre-flight 1** (AI-leak validation, 30 min) — this determines whether Issue A is worth pursuing.
3. **Run Day 0 pre-flight 3** (reconciliation audit, 30 min) — check what's already done before Sprint 2.
4. **Schedule Sprint 1 for Nov 3** — the day after Day 7 check. Block 5 days of writer time.
5. **Do NOT push any changes until Nov 2** — let the Week 3 crawl settle.

---

## 11. Summary of v2 corrections to v1

| Item | v1 | v2 | Why |
|---|---|---|---|
| Conservative 90-day clicks | +1,535 (+68%) | **+570 (+25%)** | v1 assumed 3-7x CTR lifts; realistic is 1.5-3x |
| Moderate 90-day clicks | +3,965 (+177%) | **+1,660 (+74%)** | Same correction |
| Conservative impressions | +18,000 | **+5,000-10,000** | New pages take 60-90 days to gain impressions |
| Sprint 1 start | "Today" | **Nov 3** | Don't disturb Week 3 crawl |
| /vs/ hub scope | 30-40 new pages | **22-32 new pages** | 8 already live |
| Sprint 2 FAQ schema scope | 30 pages | **~20 pages** (only 2 of top-10) | 8 of top-10 already have live schema |
| Day 90 click target | ≥3,000 | **≥2,800** | More honest |
| Day 90 blog CTR target | ≥0.5% | **≥0.3%** | More honest |

**Net:** v2 is ~30% more conservative than v1, but the priorities are unchanged. Issue F (Prime Mover) is still the single highest-leverage action. The timeline is shifted by 1 week to respect the Week 3 crawl.

---

## 12. Changelog — what was fact-checked + baked in (2026-10-26)

v2 was originally drafted against the *claimed* baseline and cross-references a file not in the repo. Verified against the live site + git; all fixes now live in the main body above (this section is audit trail only — safe to skip when executing).

| # | Issue found | Where | Fix baked into |
|---|---|---|---|
| 1 | **CRITICAL: §3.5 FAQ schema (4 questions) would break the site's FAQ-mirror gate** — page has 5 visible + 5 schema (not 6+6 as first mis-counted; the 6th `itemprop=name` is a `<p>` how-to intro, not an FAQ item) | §3.5 | Rewritten as mirror-safe **7-question** set (existing 5 kept verbatim + 2 new added to BOTH visible §3.5a and schema §3.5b). §3 header now carries a before-pasting gate warning. |
| 2 | **Unverified numeric claim** ">10,000 peer-reviewed publications" — no source | §3.2 | Replaced with "widely used in published research protocols worldwide" |
| 3 | **Unverified SLA claim** "returns results in ~30 seconds" — no benchmark | §3.5 | Softened to "typically returns results in under a minute" |
| 4 | **Cross-reference to file not in repo** — v2 §0 cited `docs/seo-week3/vigyanllm-week2-ctr-optimization-deliverables.md` which lived only in `~/Downloads/` | §0 | File now committed to `docs/seo-week3/` alongside this plan |
| 5 | **§4 FAQ-schema scope overstated** — claimed "4 of 10 already have schema"; live check shows **8 of 10 already have FAQPage** | §4, §6, §11 | Added per-URL table; Sprint 2 FAQ work on the top-10 = 2 pages, not 6 |
| 6 | Baseline drift — §9 used claimed "1,340" not verified 1,262 | §1, §9 | Corrected to 1,262 (with note that 2,236 is the 3-mo rolling figure) |

**Verified safe, no change needed:**
- All 8 internal links in the §3.4 sidebar resolve 200/0-hops/canonical-exact live
- "same Primer3 v2.6.1 engine" claim — consistent with existing site claims
- "2-5 minutes per design" for NCBI — about a competitor, widely documented
- §3.2/3.3/3.4 additions (answer block, verdict table, sidebar) are genuinely new to the target page — no conflicts

---

*End of v2. Main body is safe to execute without reading §12. Execute starting Nov 3.*

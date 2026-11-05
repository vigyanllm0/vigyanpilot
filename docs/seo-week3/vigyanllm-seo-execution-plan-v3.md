# VigyanLLM — SEO Execution Plan v3 (Fix-or-Create Decision Matrix)

> **Document version:** 3.0
> **Date:** 2026-11-05
> **Author:** QA / SEO Manager (acting)
> **Data sources:** v1 SEO Fix Plan (your prior .md) + GSC Performance export Jun 16 – Nov 5 2026 (6 months)
> **Purpose:** Convert the v1 audit findings into a page-by-page decision matrix — **fix existing meta** vs **create new page** — with paste-ready deliverables and internal linking wiring
> **Pre-deploy state:** Crawl freeze active until Nov 2; Wave 1-4 audit fixes (C1/C2/C3/C4) deploy Nov 3-6; this plan starts Sprint 2 on Nov 10

---

> ## ⚠️ QA PATCH — READ FIRST (2026-11-05)
>
> **This annotated edition supersedes the raw v3.** Owner approved "approve v3 with QA
> patches" after a repo + GSC-baseline audit that found nine defects (**P1–P9**, itemised
> in **§10 QA errata**). Corrections appear inline as `> **QA:**` callouts. **Where a
> callout and the original text disagree, the callout wins.**
>
> Headline changes:
> 1. **P1 — Baseline:** KPIs anchor to the verified **1,262 clicks / 28d** (commit `4457f38a`), not the "~540 clicks/month" 6-month average. "3–5x/4–7x growth" framing is void.
> 2. **P2 — Sprint 1 stays owned by v2:** `/blog/ncbi-primer-blast-guide` uses v2 §3.1 title/meta + §3.4 sidebar verbatim. Tier-1 row #1 and Block 1 are dropped (page would otherwise be title-changed twice in one week).
> 3. **P4 — Timeline:** the Nov 2 Day-7 GSC checkpoint has NOT run (owner-side) and gates Sprint 1 per v2 line "≥5/9 indexed". No live-site change ships before it clears. "Wave 1-4 (C1/C2/C3/C4)" and "QA report Critical 3" could not be located in this repo — confirm source or drop.
> 4. **P5 — Tier 2: 10 → 2 builds + 4 merges + 3 drops + 1 hold** (6 of 10 rows cannibalised existing pages; 2 contradicted v3's own §6.7/Tier 3).
> 5. **P6 — Link Blocks 2/3** must not link to pages that don't exist yet (would ship ~6 weeks of internal 404s). Existing-target versions below.
> 6. **P8 — Two Tier-1 rows held:** `/primer` (retargeting risk) and `/clustal-vs-muscle` (already 1.47% CTR).
> 7. **Ops gates (missing from raw v3):** `pre_gsc_check.sh` pre-flight · surgical `aws s3 cp` only — **NEVER `deploy/aws/sync-frontend.sh`** (TICKET-1 / GitHub #8 P0) · CloudFront invalidation · `deploy/aws/indexnow_ping.sh` · `scripts/rules_lint.py` 0 errors · FAQ-mirror gate before any FAQ/schema change · GSC Request-Indexing ≈10 URLs/day, ≥30 s apart · commit/push/deploy only on explicit owner go.

---

## 0. What v3 adds on top of v1 (read this first)

v1 is comprehensive on the audit side. v3 adds 4 things v1 didn't cover:

1. **Mobile vs desktop CTR inversion** — Mobile CTR (1.29%) is HIGHER than Desktop (0.65%). Unusual. Diagnosed below with a concrete fix.
2. **USA position crisis** — USA has 103K impressions (your largest market by impressions) but position 14.71 and CTR 0.32%. India has 71K impressions at position 8.99 and CTR 1.44%. The USA bucket is dragging your global CTR down. Title/meta must prioritize USA search intent.
3. **AI Overview capture, not "evaluate-X" page creation** — v1 recommends building `/vs/evaluate-idt-on-primer-design-tool` pages. v3 disagrees. Those queries are AI Overview follow-ups; the right fix is to make the EXISTING pages snippet-eligible, not build new pages nobody clicks.
4. **Fix-or-Create decision matrix** — For every priority opportunity in v1, v3 says explicitly: "fix meta on existing page X" OR "create new page Y at URL Z with this brief." No more "rewrite titles" without saying which page.

---

## 1. Honest baseline (6-month data, not 3-month)

v1 worked from 3-month data. The 6-month export shows the site is healthier than v1 implied:

| Metric | v1 (3-mo) | v3 (6-mo) | Read |
|---|---|---|---|
| Total clicks | ~2,236 | ~3,240 | +45% — site is climbing |
| Total impressions | ~365K | ~449K | +23% — rankings improving |
| Brand clicks (`vigyanllm`) | 111 | 217 | +95% — brand awareness growing |
| Brand CTR | 80.4% | 69.3% | Down — more competitive brand SERP |
| `primer blast` position | 6.73 | 6.73 | Flat — ranking stuck |
| `primer blast` CTR | 0.10% | 0.10% | Flat — title problem persists |
| `/blog/ncbi-primer-blast-guide` impressions | 142,576 | 160,916 | +13% — still the single biggest opportunity |
| `/blog/ncbi-primer-blast-guide` CTR | 0.14% | 0.15% | Flat — Title NOT yet refreshed (Sprint 1 not started) |
| `/pcr-product-calculator` CTR | 2.98% | 3.02% | Flat — already winning |
| `/dna-3d` CTR | 11.77% | 10.82% | Slight dip — still winning |

**Key signal:** The site has been climbing on its own — brand search doubled, total impressions grew 23%. The CTR crisis is still real but the foundation is solid. Sprint 1 (refresh `/blog/ncbi-primer-blast-guide` per the v2 §3 templates) remains the single highest-ROI action.

---

## 2. The 4 new findings v3 adds

### Finding N1 — Mobile CTR (1.29%) > Desktop CTR (0.65%)

**Why this matters:** This is inverted. Industry norm is desktop CTR > mobile CTR (desktop snippets are wider, more visible). Your inversion means desktop snippets are getting clipped or your desktop title tags exceed the ~600px pixel width Google uses for desktop truncation.

**Diagnosis:**
- Mobile truncates at ~680px (roughly 50-60 chars in narrow fonts)
- Desktop truncates at ~580px (roughly 55-65 chars in wider fonts)
- Your titles are likely 60-76 chars (per the audit finding "Title is 76 chars" on `/`)
- On desktop, these get clipped mid-phrase; on mobile they fit cleanly
- Result: mobile users see complete titles, desktop users see "Free Bioinformatics Tools — Primer Design, BLAS…"

**Fix:** Apply the v2 §4 title templates. Specifically:
- Cap titles at 55 chars (not 60) to leave pixel headroom for desktop
- Front-load the focus keyword in the first 35 chars
- Drop the `| VigyanLLM` suffix on tool pages (the brand is in the URL)

**Verification after fix:**
```bash
# Check pixel width approximation (1 wide char ≈ 10px, 1 narrow ≈ 5px)
title="Free PCR Product Size Calculator - No Login"
# Count wide letters (W, M, m, w) and narrow (i, l, t, 1, I)
# Target: ≤580px ≈ 55 chars in mixed fonts
```

### Finding N2 — USA is your largest impression market but worst-performing

| Country | Clicks | Impressions | CTR | Position |
|---|---|---|---|---|
| United States | 334 | 103,832 | 0.32% | 14.71 |
| India | 1,031 | 71,624 | 1.44% | 8.99 |
| Philippines | 171 | 7,278 | 2.35% | 12.33 |

**Why this matters:** USA has 1.5x India's impressions but earns 1/3 the clicks. USA position (14.71) is dramatically worse than India (8.99). Two possible causes:
1. **USA SERP is more competitive** — NCBI, IDT, SnapGene, Benchling all rank well in USA SERPs
2. **Your titles don't match USA search intent** — USA searchers want "Free", "Online", "No login", "Alternative to [competitor]"

**Fix:** For the top 30 pages, write titles that include the commercial-intent modifier:
- ❌ "Primer Design Tool | VigyanLLM" (descriptive, no intent signal)
- ✅ "Free Primer Design Tool — No Login, Online | VigyanLLM" (matches USA intent)

**Target:** USA CTR 0.32% → 0.6% by Day 60 (still below India's 1.44% because USA SERP is harder, but doubled).

### Finding N3 — AI Overview capture, NOT new "evaluate-X" pages

v1 §3.1 recommends building `/vs/evaluate-idt-on-primer-design-tool` and similar pages. v3 disagrees.

**Why:** The "evaluate the life sciences company X on Y" queries (27K impressions, 0 clicks) are not human searches. They are Google's AI Overview follow-up queries — Google's AI generates these queries internally to expand its Overview, cites your page as a source, but the user never clicks because the Overview answers them. Building `/vs/evaluate-*` pages won't capture these clicks because the AI Overview will still answer them.

**Evidence:**
- 27K impressions at position 5-7 with 0.00% CTR
- If real humans were searching, position 5-7 would earn 0.5-1.5% CTR minimum
- The query phrasing "evaluate the life sciences company X on Y" is not natural English — it's AI-generated

**Right fix:** Make your existing high-authority pages (`/blog/ncbi-primer-blast-guide`, `/primer-design`, `/idt-vs-vigyanllm`) snippet-eligible with definitional answer blocks (40-55 words at the top). This is what v2 §3 already prescribes for Sprint 1. **Do not build the 20 `/vs/evaluate-*` pages v1 recommends.**

**Decision:** Strike v1 Issue A from the plan. The 27K "AI-leak" impressions are not recoverable clicks — they're AI Overview citations. Focus the energy on Issue F (Prime Mover) instead.

### Finding N4 — The 2 winning calculators prove the template

`/pcr-product-calculator` and `/amplicon-size-calculator` are both at position 3.18-3.24 with 19-30% CTR. These are your only 2 pages with healthy CTR.

**Pattern of winners:**
1. URL is keyword-exact (`/pcr-product-calculator` matches `pcr product size calculator`)
2. Title is descriptive + functional ("PCR Product Size Calculator")
3. Page has an interactive tool above the fold
4. Page has a clear "what is X" section below
5. Page has FAQ schema

**Implication:** Replicate this pattern on every calculator page. The calculators stuck on page 2 (`/tm-calculator` at pos 7.80, `/gc-calculator` at pos 8.74) don't need new content — they need:
- Internal links from `/blog/ncbi-primer-blast-guide` (the 160K-impression fountain)
- Title rewrites to match the winning pattern

> **QA (P7) — Finding N4's evidence is defective, pattern still valid:**
> - **`/amplicon-size-calculator` 404s live and never existed in git history** — it is not a winning page. (Side-action: if GSC still shows that URL with impressions, 301 it to `/pcr-product-calculator`.)
> - The **19–30% CTRs are query-level** (audit query table), not page-level. Page-level `/pcr-product-calculator` = **3.0%** (verified baseline).
> - Keep the *pattern* (URL-exact, tool above fold, "what is X", FAQ schema) — but cite only `/pcr-product-calculator` (3.0%) and `/dna-3d` (11.8%) as winners.

---

## 3. The Fix-or-Create Decision Matrix

For each priority opportunity in v1, here's the explicit decision: **FIX META on existing page** OR **CREATE NEW PAGE**.

### Tier 1 — FIX META (existing pages, paste-ready rewrites)

These pages already rank on page 1 with high impressions. They need title/meta rewrites only. No new content, no new pages.

| # | URL | Current impr | Current CTR | New title (≤55ch) | New meta (≤155ch) | Target CTR (60-day) |
|---|---|---|---|---|---|---|
| 1 | `/blog/ncbi-primer-blast-guide` | 160,916 | 0.15% | Primer-BLAST Guide 2026: Free Tutorial + Alternative | Complete NCBI Primer-BLAST tutorial. Free online primer design with specificity check. Step-by-step + best free alternative. | 0.5-1.0% |
| 2 | `/primer3-vs-idt` | 39,145 | 0.02% | Primer3 vs IDT: 2026 Primer Tool Comparison | Primer3 vs IDT PrimerQuest — which primer tool wins? Free vs paid, features, accuracy. VigyanLLM free alternative compared. | 0.5-0.8% |
| 3 | `/idt-vs-vigyanllm` | 3,661 | 0.05% | IDT vs VigyanLLM: Free Primer Design Comparison | IDT vs VigyanLLM — free primer design comparison. Features, accuracy, no-login access. See why researchers switch. | 0.8-1.5% |
| 4 | `/blog/best-primer-design-software-2026` | 8,761 | 0.21% | Best Primer Design Software 2026: Free + Paid | Top primer design software 2026 ranked. VigyanLLM, SnapGene, Primer3, IDT, Benchling compared. Free + paid tools. | 1.0-1.5% |
| 5 | `/blog/best-free-primer-design-tool-2026` | 7,641 | 0.29% | Best Free Primer Design Tool 2026: Top 10 | Ranked list of best free primer design tools 2026. VigyanLLM, Primer3, NCBI, IDT compared. Features, accuracy, ease of use. | 1.0-1.5% |
| 6 | `/blog/primer-design-tool-comparison` | 8,290 | 0.39% | Primer Design Tool Comparison 2026: 10 Ranked | 10 primer design tools compared. IDT, Primer3, NCBI, VigyanLLM, Benchling, SnapGene. Features, accuracy, price. | 1.0-1.5% |
| 7 | `/tm-calculator` | 6,179 | 0.16% | Free Tm Calculator — Primer Melting Temp Online | Calculate primer melting temperature (Tm) free online. SantaLucia 1998 nearest-neighbor. Salt + Mg2+ corrections. No login. | 0.8-1.2% |
| 8 | `/primer` | 5,793 | 0.73% | Free Primer Specificity Check — BLAST Against Genome | Check primer specificity free. BLAST primers against whole genome. NCBI Primer-BLAST alternative. No login required. | 1.0-1.5% |
| 9 | `/gc-calculator` | 4,309 | 0.51% | Free GC Content Calculator — Primer GC% Online | Calculate GC content of DNA primers free. Get GC%, length, Tm estimate. PCR primer design. No login required. | 0.8-1.2% |
| 10 | `/autodock-vs-swissdock` | 4,949 | 0.77% | AutoDock Vina vs SwissDock: 2026 Docking Comparison | AutoDock Vina vs SwissDock — which docking tool wins? Speed, accuracy, GPU, ease of use. Free alternatives compared. | 1.0-1.5% |
| 11 | `/clustal-vs-muscle` | 3,615 | 1.47% | Clustal Omega vs MUSCLE: 2026 MSA Comparison | Clustal Omega vs MUSCLE vs MAFFT — which MSA tool is best? Compare accuracy, speed, output. Free online MSA. | 1.5-2.5% |
| 12 | `/primer-blast-alternative` | 2,085 | 0.43% | Primer-BLAST Alternative: Free No-Login Tool | Best free NCBI Primer-BLAST alternative. Same Primer3 engine, no login, faster. VigyanLLM primer design tool. | 1.0-1.5% |
| 13 | `/swissdock-vs-haddock` | 1,480 | 0.27% | SwissDock vs HADDOCK: 2026 Docking Comparison | SwissDock vs HADDOCK — which docking tool wins? Compare speed, accuracy, ease of use. Free alternatives included. | 1.0-1.5% |
| 14 | `/reverse-complement` | 3,494 | 0.23% | Free Reverse Complement Tool — DNA Converter | Free reverse complement tool online. Convert DNA sequence to reverse complement. No login, no install, instant results. | 1.0-1.5% |
| 15 | `/blog/rt-pcr-vs-qpcr` | 5,240 | 0.10% | RT-PCR vs qPCR: Difference + When to Use [2026] | RT-PCR vs qPCR vs RT-qPCR explained. Differences, when to use each, primer design considerations. Free tools included. | 1.0-1.5% |

**Total Tier 1 scope:** 15 pages, paste-ready rewrites above. Effort: 2-3 days of dev work to apply, batch 5 pages/week starting Nov 10.

> **QA (P2/P8) — Tier 1 patched scope: 15 → 14 rows → 11 actionable.**
> - **Row #1 REMOVED from Tier 1** — `/blog/ncbi-primer-blast-guide` is owned by **Sprint 1 / v2 §3.1** (title `NCBI Primer-BLAST Guide 2026: Free Primer Design Tutorial`, 59ch — NOT the 52ch string in this table). Applying both would change the same page's title twice in one week.
> - **Row #8 `/primer` HELD** — current title "Free PCR Primer Design Tool — No Queue, No Sign-up (2026)" at **0.73% CTR** (best in the table). Rewriting to "Primer Specificity Check" retargets the flagship tool page at a secondary intent, violates the anti-cannibalization rule (tool pages answer tool-intent), and competes with `/primer-blast-alternative`. No change.
> - **Row #11 `/clustal-vs-muscle` HELD** — already **1.47% CTR**; a rewrite risks regression (violates this plan's own §6.6). Measure-only.
> - **Remaining 11 rows, patched execution order (by CTR-gap × impressions), batch 5/week:**
>   - **Batch A (Nov 10–16):** #2 `/primer3-vs-idt` (39,145 impr @0.02% — biggest single fix), #15 `/blog/rt-pcr-vs-qpcr`, #3 `/idt-vs-vigyanllm`, #7 `/tm-calculator`, #14 `/reverse-complement`
>   - **Batch B (Nov 17–23):** #4 `/blog/best-primer-design-software-2026`, #5 `/blog/best-free-primer-design-tool-2026`, #6 `/blog/primer-design-tool-comparison`, #13 `/swissdock-vs-haddock`, #12 `/primer-blast-alternative`
>   - **Batch C (Nov 24–30):** #9 `/gc-calculator`, #10 `/autodock-vs-swissdock`, + existing-target link blocks (see §4.3)

**Volume impact (Tier 1 only, conservative 60-day):**
- Current clicks from these 15 pages: ~640/month
- Target clicks after meta fix: ~1,400-2,000/month
- **Net new: +760 to +1,360 clicks/month**

### Tier 2 — CREATE NEW PAGES (with briefs)

These are keyword clusters with high impressions but NO existing page (or only a thin existing page that can't rank). Build new pages with the structure from v2 §3 (definitional answer block + quick verdict table + related tools sidebar + FAQ schema).

| # | New URL | Target keyword(s) | Estimated monthly impr | Page brief |
|---|---|---|---|---|
| 1 | `/oligoanalyzer-comparison` | "what's the most accurate oligoanalyzer" + 12 related (4,423 impr) + "evaluate the life sciences company X on oligoanalyzer" (3,475 impr) | ~8,000 | Comparison of IDT OligoAnalyzer, VigyanLLM, NEB, Thermo, Qiagen. Definitional first paragraph answering "what's the most accurate oligoanalyzer used in research." Comparison table. FAQ schema. Internal links to `/primer-design`, `/tm-calculator`, `/gc-calculator`. |
| 2 | `/best-tm-calculator` | "what tools are popular for calculating melting temperature" (2,529 impr) + "which tm calculator is used by top molecular biology labs" (195 impr) + "what's the best non-neb tool for calculating primer tm" (108 impr) | ~3,000 | Ranked list of Tm calculators: VigyanLLM, NEB, IDT, Thermo, Promega. Definitional first paragraph. Comparison table (Tm method = SantaLucia 1998 across all). FAQ schema. |
| 3 | `/free-online-molecular-docking` | "molecular docking online free" (28 impr) + "free molecular docking software" (12 impr) + "free software for molecular docking" (14 impr) + "online molecular docking" (10 impr) | ~500 | Landing page for free online docking. CTA to `/docking`. Definitional answer block. Comparison of free docking tools. FAQ schema. |
| 4 | `/crispr-guide-design-tool` | "crispr design tool" (92 impr) + "crispr grna design tool" (49 impr) + "what is the best crispr design tool" (9 impr at pos 4.78) | ~200 | Tool-focused landing page. CTA to `/crispr-analysis`. Comparison: VigyanLLM, CHOPCHOP, CRISPOR, Benchling. FAQ schema. |
| 5 | `/best-primer-design-tool-for-research` | "where can i find a reliable primer design tool for research" (1,782 impr) + "where do researchers go for trusted primer designer tools" (1,751 impr) + "what's the most reliable primer designer for molecular work" (1,505 impr) | ~5,000 | Research-focused landing page. Definitional first paragraph answering the exact question. Trust signals (SantaLucia, Primer3 citations). CTA to `/primer-design`. FAQ schema. |
| 6 | `/best-oligoanalyzer-for-biotech-labs` | "what are the top oligoanalyzer tools used in biotech labs" (620 impr) + "which oligoanalyzer tools are most used by researchers" (917 impr) + "what's the best oligoanalyzer tool for checking secondary structures" (833 impr) | ~2,400 | Listicle + comparison. Definitional first paragraph. Top 5 oligoanalyzers ranked. FAQ schema. |
| 7 | `/india/sovereign-ai-bioinformatics` | "sovereign llm" (21 impr) + "sovereign ai platform" (12 impr) + India cluster (36 impr total in 6-mo) | ~100 (growth market) | India-specific landing page. Sovereign AI for biotech. DPDP compliance. CTA to academic partnership. FAQ schema. |
| 8 | `/pcr-primer-design-for-qpcr` | "qpcr primer design" (64 impr at pos 58) + "qpcr primer design tool" (119 impr at pos 39) + "qpcr primer design online" (90 impr at pos 44) + "how to design qpcr primers" (31 impr at pos 48) | ~300 | Tutorial hub for qPCR primer design. Exon-junction spanning. SYBR Green vs TaqMan considerations. CTA to `/primer-design`. FAQ schema. |
| 9 | `/msa-tool-comparison` | "msa tool" (66 impr) + "multiple sequence alignment tool" (81 impr) + "msa tools" (44 impr) + "msa alignment" (95 impr) | ~300 | Comparison hub. Clustal Omega, MUSCLE, MAFFT, T-Coffee ranked. Definitional first paragraph. CTA to `/msa`. FAQ schema. |
| 10 | `/docking-score-calculator` | "docking score" (161 impr at pos 4.88) + "what is a good docking score" (25 impr at pos 4.32) + "docking score meaning" (34 impr at pos 4.26) | ~250 | Tool + interpretation page. CTA to `/docking`. Definitional first paragraph. Score interpretation table (Vina, Gnina, AutoDock 4). FAQ schema. |

**Total Tier 2 scope:** 10 new pages, ~1,500-2,000 words each. Effort: 3-4 weeks of writer time (1 page per 2-3 days). Batch starting Dec 8 (Sprint 3).

> **QA (P5) — Tier 2 patched: 10 rows → 2 BUILDS + 4 MERGES + 3 DROPS + 1 HOLD.**
> Six of the ten rows cannibalise pages that already exist in this repo (two of them are in the live GSC batch of 9), one contradicts this plan's own §6.7, and one promises a tool that doesn't exist.
>
> | # | v3 row | Disposition | Reason / target |
> |---|---|---|---|
> | 1 | `/oligoanalyzer-comparison` | ✅ **BUILD** | Genuinely new; absorbs row #6's keywords as a section |
> | 2 | `/best-tm-calculator` | ✅ **BUILD** | Genuinely new (~3K impr) |
> | 3 | `/free-online-molecular-docking` | ❌ **DROP** | `/free-molecular-docking` **exists** (59ch title, in GSC batch of 9) → optimize existing instead |
> | 4 | `/crispr-guide-design-tool` | ⏸️ **HOLD** | CRISPR tool is *In Development* (PA-09) — no tool to land on; ~200 impr. Revisit when tool ships |
> | 5 | `/best-primer-design-tool-for-research` | 🔀 **MERGE** | 4th variant of a cluster Tier 1 #4/#5/#6 already own → add definitional answer block to `/blog/best-primer-design-software-2026` + `/blog/best-free-primer-design-tool-2026` |
> | 6 | `/best-oligoanalyzer-for-biotech-labs` | 🔀 **MERGE** | Duplicate of row #1 → section inside `/oligoanalyzer-comparison` |
> | 7 | `/india/sovereign-ai-bioinformatics` | ❌ **DROP** | **Contradicts this plan's own §6.7** ("Do NOT prioritize India… build Q1 2027"); 36 impr/6-mo |
> | 8 | `/pcr-primer-design-for-qpcr` | 🔀 **MERGE** | `/blog/qpcr-primer-probe-design` exists (enriched 2026-10-16) → enrich with exon-junction + SYBR/TaqMan sections |
> | 9 | `/msa-tool-comparison` | ❌ **DROP** | `/msa-tools-comparison` **exists** (55ch title, in GSC batch of 9) → optimize existing instead |
> | 10 | `/docking-score-calculator` | 🔀 **MERGE** | No such tool exists (tool-promise risk) **and** it contradicts Tier 3's own "enrich `/blog/docking-score-interpretation` instead" → add a score-interpretation table there |
>
> **Patched Sprint 3 (Dec 8 – Jan 4):** 2 new pages (`/oligoanalyzer-comparison`, `/best-tm-calculator`) + 4 merge/enrich actions (rows 5, 6, 8, 10) + 2 optimize-existing actions (rows 3, 9) → then measure before any further builds.

**Volume impact (Tier 2 only, conservative 90-day after launch):**
- Target impressions from new pages: ~20,000/month combined
- Target clicks at 1.0% CTR: ~200/month
- **Net new: +200 clicks/month by Day 90 post-launch**

### Tier 3 — DO NOT BUILD (v1 recommendations to strike)

| v1 recommendation | v3 verdict | Reason |
|---|---|---|
| Build 20 `/vs/evaluate-X-on-Y` pages | ❌ STRIKE | AI Overview follow-up queries, not human searches. See Finding N3. |
| Build `/swissdock-review`, `/vinascore-explained`, `/smina-review` | ❌ STRIKE | Low impression volume (SwissDock 2,656 / VinaScore 957 / Smina 61). Better to enrich `/autodock-vs-swissdock` and `/blog/docking-score-interpretation` instead. |
| Build `/clustal-vs-mafft` (v1 says "exists, optimize") | ✅ ALREADY DONE | Page exists, ranks at pos 5.12, CTR 2.46%. No action needed. |
| De-duplicate "is it [query]" variants via canonical | ⚠️ DEFER | These are AI Overview artifacts, not duplicate content. Canonical won't help. Defer until AI Overview behavior stabilizes. |

---

## 4. Internal Linking Wiring Diagram (the missing piece from v1)

v1 mentions internal links but doesn't specify them. Here's the explicit wiring.

### 4.1 Fountain pages (high authority, must link OUT)

| Fountain page | Impr | Link to (sprinkler pages) |
|---|---|---|
| `/blog/ncbi-primer-blast-guide` | 160,916 | `/primer-design`, `/pcr-product-calculator`, `/tm-calculator`, `/gc-calculator`, `/primer-blast-alternative`, `/idt-vs-vigyanllm`, `/oligoanalyzer-comparison` (new), `/best-tm-calculator` (new) |
| `/primer3-vs-idt` | 39,145 | `/primer-design`, `/idt-vs-vigyanllm`, `/oligoanalyzer-comparison` (new), `/best-primer-design-tool-for-research` (new) |
| `/pcr-product-calculator` | 8,445 | `/primer-design`, `/tm-calculator`, `/gc-calculator` |
| `/blog/best-primer-design-software-2026` | 8,761 | `/primer-design`, `/idt-vs-vigyanllm`, `/primer3-vs-idt`, `/best-primer-design-tool-for-research` (new) |
| `/blog/best-free-primer-design-tool-2026` | 7,641 | `/primer-design`, `/idt-vs-vigyanllm`, `/free-primer-design-tool` (existing) |
| `/blog/primer-design-tool-comparison` | 8,290 | `/primer-design`, `/idt-vs-vigyanllm`, `/primer3-vs-idt`, `/oligoanalyzer-comparison` (new) |
| `/dna-3d` | 3,328 | `/dna-to-rna`, `/reverse-complement`, `/docking` (cross-category link for topical authority) |
| `/docking` | 2,883 | `/autodock-vs-swissdock`, `/swissdock-vs-haddock`, `/blog/docking-score-interpretation`, `/free-online-molecular-docking` (new), `/docking-score-calculator` (new) |
| `/blog/docking-score-interpretation` | 6,769 | `/docking`, `/autodock-vs-swissdock`, `/docking-score-calculator` (new) |
| `/autodock-vs-swissdock` | 4,949 | `/docking`, `/swissdock-vs-haddock`, `/free-online-molecular-docking` (new) |

### 4.2 Sprinkler pages (need authority, must receive links)

| Sprinkler page | Current pos | Target pos | Receives links from |
|---|---|---|---|
| `/tm-calculator` | 7.80 | ≤5.0 | `/blog/ncbi-primer-blast-guide`, `/pcr-product-calculator`, `/primer-design` |
| `/gc-calculator` | 8.74 | ≤5.0 | `/blog/ncbi-primer-blast-guide`, `/pcr-product-calculator`, `/primer-design` |
| `/primer-blast-alternative` | 10.84 | ≤7.0 | `/blog/ncbi-primer-blast-guide`, `/primer-design`, `/idt-vs-vigyanllm` |
| `/primer-design` | 33.39 | ≤15.0 | `/blog/ncbi-primer-blast-guide`, `/primer3-vs-idt`, `/idt-vs-vigyanllm`, `/blog/best-primer-design-software-2026` |
| `/reverse-complement` | 8.43 | ≤5.0 | `/dna-to-rna`, `/dna-3d` |
| `/msa` | 14.90 | ≤10.0 | `/clustal-vs-muscle`, `/clustal-vs-mafft`, `/muscle-vs-mafft` |
| `/blast` | 11.05 | ≤7.0 | `/blog/ncbi-primer-blast-guide`, `/blast-vs-diamond`, `/blog/blastn-vs-blastp` |

### 4.3 The 3 internal-link blocks to add (paste-ready)

**Block 1 — Add to `/blog/ncbi-primer-blast-guide` (after the definitional answer block from v2 §3.2):**

```html
<aside class="related-tools">
  <h3>Related VigyanLLM Tools</h3>
  <ul>
    <li><a href="/primer-design">Free Primer Design Tool</a> — same Primer3 engine, no login</li>
    <li><a href="/pcr-product-calculator">PCR Product Size Calculator</a> — calculate amplicon size</li>
    <li><a href="/tm-calculator">Tm Calculator</a> — primer melting temperature</li>
    <li><a href="/gc-calculator">GC Content Calculator</a> — primer GC%</li>
    <li><a href="/primer-blast-alternative">Primer-BLAST Alternative</a> — free, no login</li>
    <li><a href="/idt-vs-vigyanllm">IDT vs VigyanLLM</a> — comparison</li>
  </ul>
</aside>
```

> **QA (P2) — Block 1 superseded by v2 §3.4.** v2's Sprint-1 sidebar (`Related VigyanLLM Tools`, **8 links**, all link-verified 200) already targets this page — the two blocks are the same `<aside class="related-tools">` construct. **Paste ONE sidebar only.** Recommended: use v2 §3.4 as-is, optionally adding Block 1's two extra links (`/primer-design`, `/idt-vs-vigyanllm` — both verified live) → 10 links. Never both.
> Also: `related-tools` has **no CSS anywhere in `frontend/`** (0 usages) — decide in Sprint 1 whether to add ~10 lines of styles or accept an unstyled block.

**Block 2 — Add to `/primer3-vs-idt` (after the comparison table):**

```html
<aside class="related-tools">
  <h3>Compare More Primer Tools</h3>
  <ul>
    <li><a href="/idt-vs-vigyanllm">IDT vs VigyanLLM</a> — full feature comparison</li>
    <li><a href="/primer-design">Free Primer Design Tool</a> — try VigyanLLM</li>
    <li><a href="/oligoanalyzer-comparison">Oligoanalyzer Comparison</a> — IDT vs alternatives</li>
    <li><a href="/best-tm-calculator">Best Tm Calculator</a> — ranked list</li>
  </ul>
</aside>
```

**Block 3 — Add to `/docking` and `/blog/docking-score-interpretation` (after main content):**

```html
<aside class="related-tools">
  <h3>Related Docking Resources</h3>
  <ul>
    <li><a href="/autodock-vs-swissdock">AutoDock Vina vs SwissDock</a> — comparison</li>
    <li><a href="/swissdock-vs-haddock">SwissDock vs HADDOCK</a> — comparison</li>
    <li><a href="/docking-score-calculator">Docking Score Calculator</a> — interpret your scores</li>
    <li><a href="/free-online-molecular-docking">Free Online Docking</a> — no install required</li>
  </ul>
</aside>
```

> **QA (P6) — Blocks 2 & 3 contain links to pages that won't exist until Jan 5** (`/oligoanalyzer-comparison`, `/best-tm-calculator`, `/docking-score-calculator`, `/free-online-molecular-docking`), but the timeline schedules these blocks for **Nov 24–30** → ~6 weeks of internal 404s. **Ship the existing-target versions below; add the new-page links only when Sprint 3c ships those pages.**
>
> **Block 2 — patched (existing targets only, safe for Nov 24–30):**
> ```html
> <aside class="related-tools">
>   <h3>Compare More Primer Tools</h3>
>   <ul>
>     <li><a href="/idt-vs-vigyanllm">IDT vs VigyanLLM</a> — full feature comparison</li>
>     <li><a href="/primer-design">Free Primer Design Tool</a> — try VigyanLLM</li>
>     <li><a href="/tm-calculator">Tm Calculator</a> — primer melting temperature</li>
>     <li><a href="/primer-blast-alternative">Primer-BLAST Alternative</a> — free, no login</li>
>   </ul>
> </aside>
> ```
>
> **Block 3 — patched (existing targets only):**
> ```html
> <aside class="related-tools">
>   <h3>Related Docking Resources</h3>
>   <ul>
>     <li><a href="/autodock-vs-swissdock">AutoDock Vina vs SwissDock</a> — comparison</li>
>     <li><a href="/swissdock-vs-haddock">SwissDock vs HADDOCK</a> — comparison</li>
>     <li><a href="/blog/docking-score-interpretation">Docking Score Interpretation</a> — what the numbers mean</li>
>     <li><a href="/free-molecular-docking">Free Molecular Docking</a> — no install required</li>
>   </ul>
> </aside>
> ```

---

## 5. Updated execution timeline (integrates with Wave 1-4 deploy)

| Date | Phase | Action | Owner |
|---|---|---|---|
| **Nov 3-6** | Wave 1-4 (already planned) | C1/C2/C3/C4 audit fixes deploy | Dev team |
| **Nov 7-9** | Sprint 1 (Prime Mover) | Refresh `/blog/ncbi-primer-blast-guide` per v2 §3 templates + add internal-link Block 1 | Writer |
| **Nov 10-16** | Sprint 2a (Tier 1 meta fixes batch 1) | Apply new title/meta to pages 1-5 from §3 Tier 1 table | Dev |
| **Nov 17-23** | Sprint 2b (Tier 1 meta fixes batch 2) | Apply new title/meta to pages 6-10 from §3 Tier 1 table | Dev |
| **Nov 24-30** | Sprint 2c (Tier 1 meta fixes batch 3) | Apply new title/meta to pages 11-15 from §3 Tier 1 table + add internal-link Blocks 2 & 3 | Dev |
| **Dec 1-7** | Sprint 2d (measurement) | Measure CTR delta on Tier 1 pages. Target: avg CTR 0.4% → 0.8% | SEO |
| **Dec 8-21** | Sprint 3a (Tier 2 new pages batch 1) | Build new pages 1-5 from §3 Tier 2 table. Each: 1,500-2,000 words, definitional answer block, comparison table, FAQ schema, internal links. | Writer |
| **Dec 22 - Jan 4** | Sprint 3b (Tier 2 new pages batch 2) | Build new pages 6-10 from §3 Tier 2 table. | Writer |
| **Jan 5-11** | Sprint 3c (new page deploy + GSC submission) | Deploy 10 new pages, submit to GSC, add to sitemap | Dev |
| **Jan 12-25** | Sprint 4 (measurement + iteration) | Measure new page impressions. Identify underperformers. Add internal links from fountain pages. | SEO |
| **Jan 26 - Feb 1** | Day 90 review | Full KPI check vs baseline. Decide: scale (build 10 more) or iterate (enrich underperformers). | CBO |

> **QA (P3/P4) — Timeline corrections:**
> 1. **The Nov 2 Day-7 GSC checkpoint has not run** (owner-side: URL Inspection on the 9 URLs, Coverage delta vs 154, Performance filter, Sprint 1 go/no-go, Pre-flight 1 AI-leak validation). v2 gates Sprint 1 on it (**≥5/9 indexed**). **Nothing on this table ships before that checkpoint clears.** As of 2026-11-05 the checkpoint is overdue — run it first.
> 2. **"Wave 1-4 (C1/C2/C3/C4)" and "QA report Critical 3" are conversation artifacts** from the prior 437-finding QA conversation — **no such doc exists in this repo** (grep: `Wave 1`, `C1/C2`, `QA report` → 0 hits). **RESOLVED 2026-11-05: dropped as dependencies** — they do not gate anything in this plan; if they ever need to be source-of-truth, write them into a repo doc first.
> 3. **Sprint 1 window conflict:** v2 says **Nov 3–9** (5-day sprint); this table says Nov 7–9. Use **Nov 3–9 minus whatever the checkpoint delays** — i.e. start the day after the checkpoint clears, ≤5 working days.
> 4. Sprint 2 batch A must start **after** Sprint 1's title change lands on the same page — row #1 already removed from Tier 1 (see §3 callout), so no double-touch remains.
> 5. Every "Dev" row above = surgical `aws s3 cp` + CloudFront invalidation + IndexNow + live verify (see banner ops gates). **Never `deploy/aws/sync-frontend.sh`** (TICKET-1 / GitHub #8, P0, open).

---

## 6. What NOT to do (prevent mistakes)

1. **Do NOT build `/vs/evaluate-X-on-Y` pages** (v1 Issue A). AI Overview follow-up queries, not human searches. See Finding N3.
2. **Do NOT rewrite titles beyond 55 chars** to "fit more keywords." Desktop truncation at 580px will clip them. See Finding N1.
3. **Do NOT change URL slugs** on existing pages. The 301 redirect cost outweighs the SEO benefit. Fix meta, not URLs.
4. **Do NOT add FAQ schema to pages without visible FAQ** (the audit found 80+ pages with this). The mirror gate will fail. Fix the build pipeline first (Critical 3 from QA report).
   > **QA (P9) — guardrail correct, number stale.** A re-run today (2026-11-05) finds **37 of 209 FAQPage pages** whose schema questions do not appear in visible text (e.g. `solution.html`/`compare.html` share two boilerplate questions present only in JSON-LD). Not 80+ — the Oct 3 mirror sweep fixed most, this residue is real. **Action: raise a separate ticket for the 37** (independent of Sprint 1; do not block Sprint 1 on it). Re-verify with the FAQ-mirror gate before any FAQ/schema edit in Sprint 2.
5. **Do NOT build all 10 Tier 2 new pages at once.** Batch 5 + 5 with a 2-week gap. Measure first batch before building second.
6. **Do NOT touch `/dna-3d` or `/pcr-product-calculator`.** They're winning (10-30% CTR). Any change risks regression.
7. **Do NOT prioritize India cluster yet.** Only 36 impressions in 6 months. The market will grow organically as brand search grows. Build India pages in Q1 2027, not now.
8. **Do NOT strip the "no data leaves" claims** on browser-only calculators. They're verified architectural facts, kept per claims ledger.

---

## 7. Volume impact summary (v3 conservative projections)

| Tier | Action | Clicks impact (60-day) | Clicks impact (90-day) |
|---|---|---|---|
| Tier 1 | Meta rewrites on 15 pages | +760 to +1,360/month | +1,000 to +1,800/month |
| Tier 2 | 10 new pages | 0 (not yet launched) | +200/month (post-launch) |
| Internal links | 3 link blocks on fountain pages | +100 to +200/month | +200 to +400/month |
| Sprint 1 (Prime Mover) | `/blog/ncbi-primer-blast-guide` refresh | +200 to +500/month | +300 to +700/month |
| **TOTAL (conservative)** | | **+1,060 to +2,060/month** | **+1,700 to +3,100/month** |

**Net new baseline:**
- Current (6-mo rolling): ~540 clicks/month
- 60-day target: ~1,600 to 2,600 clicks/month (3-5x)
- 90-day target: ~2,200 to 3,600 clicks/month (4-7x)

> **QA (P1) — the "current" figure and the growth multiples are wrong.** "~540 clicks/month" is the **6-month average** (3,240 ÷ 6), not the current run-rate. The **verified baseline is 1,262 clicks / 28 days ≈ 1,360/month** (commit `4457f38a`, `docs/seo-week3/baselines/README.md`). Measured against reality, the targets above are **~1.2–1.9x (60-day) and ~1.6–2.6x (90-day)**, not 3–7x.
>
> **Authoritative KPI anchors (do not restate 540 anywhere):**
> - Day-0 baseline: **1,262 clicks / 137,323 impr / 0.92% CTR / pos 8.5** (28-day)
> - Jan 4 (Week 10) KPI: **≥1,800 rolling-28-day clicks** (v2 §KPI)
> - GSC workflow gate: clicks 1,262 → 1,500–1,900 · impr 137K → 165–205K · CTR ≥1.0% · critical issues <100
> - Tier-1 "+760 to +1,360 clicks/month" is **unverified modelling** — treat as hypothesis; measure Batch A's CTR delta on Dec 1 before repeating the claim.

These are conservative because they assume:
- Title rewrites lift CTR 1.5-3x (industry standard 1.5-2.5x)
- New pages take 60-90 days to compound
- Internal links push 3-5 calculators from page 2 to top 5

---

## 8. Decision required from you

1. **Approve Tier 1 meta rewrites** (§3 table — 15 pages, paste-ready)? Reply "approve tier 1" to start Nov 10.
2. **Approve Tier 2 new page list** (§3 table — 10 pages)? Reply "approve tier 2" to start Dec 8.
3. **Confirm Strike of v1 Issue A** (no `/vs/evaluate-*` pages)? Reply "strike issue a" to confirm.
4. **Approve internal linking blocks** (§4.3 — 3 paste-ready HTML blocks)? Reply "approve links" to include in Sprint 2.

Or reply "approve v3" to approve all 4 at once.

---

## 9. Changelog (what v3 changes vs v1)

| Item | v1 | v3 | Reason |
|---|---|---|---|
| AI-leak pages (Issue A) | Build 20 `/vs/evaluate-*` pages | STRIKE — make existing pages snippet-eligible instead | AI Overview follow-up queries, not human searches |
| Mobile vs desktop CTR | Not mentioned | Diagnosed — desktop snippet clipping | New finding from 6-mo device data |
| USA position crisis | Not mentioned | Diagnosed — title intent mismatch | New finding from 6-mo country data |
| Tier 1 meta rewrites | "Rewrite titles" (generic) | 15-page table with paste-ready strings | Execution-ready |
| Tier 2 new pages | 30-40 `/vs/` pages | 10 targeted pages with briefs | Focused, higher-ROI |
| Internal linking | "Add internal links" (generic) | 3 paste-ready HTML blocks + wiring diagram | Execution-ready |
| Volume projections | +1,535 to +3,965 clicks (3-mo) | +1,060 to +2,060 clicks (60-day) — more honest | Title rewrites lift CTR 1.5-3x, not 3-7x |
| Timeline | "Week 1-2" (vague) | Nov 3 - Feb 1 (date-specific) | Integrates with Wave 1-4 deploy |

---

## 10. QA errata (2026-11-05 — the nine patches this edition applies)

Audited against the repo (`~/Desktop/vigyanpilot`, `wip/mega-menu` @ `6d2fc663`) and our verified GSC baseline exports (`docs/seo-week3/baselines/`). Owner decision: **"approve v3 with QA patches."**

| # | Defect | Severity | Patch applied |
|---|---|---|---|
| **P1** | §7 baseline "~540 clicks/month" = 6-month average, not run-rate; "3–5x/4–7x" growth is an artifact | 🔴 | KPIs re-anchored to **1,262 clicks/28d**; multiples restated; §7 callout |
| **P2** | Sprint 1 page specified twice, differently (v2 §3.1 title 59ch vs this table's 52ch; v2 §3.4 8-link sidebar vs Block 1 6-link) | 🔴 | Tier-1 row #1 **removed**; Block 1 **superseded by v2 §3.4** (one sidebar only) |
| **P3** | "Wave 1-4 (C1/C2/C3/C4)" and "QA report Critical 3" don't exist in this repo | 🟠 | Flagged in §5 callout — confirm source or drop; not a dependency |
| **P4** | Timeline assumes the Nov 2 Day-7 checkpoint ran; it hasn't, and v2 gates Sprint 1 on it (≥5/9 indexed) | 🔴 | §5 callout: **nothing ships until the checkpoint clears**; Sprint 1 = day after it clears |
| **P5** | 6 of 10 Tier-2 rows cannibalise existing pages; row 7 contradicts §6.7; row 10 contradicts Tier 3 + promises a non-existent tool | 🔴 | Tier 2 → **2 builds + 4 merges + 3 drops + 1 hold** (table in §3) |
| **P6** | Blocks 2/3 link to pages not shipping until Jan 5 but scheduled Nov 24–30 → ~6 weeks of internal 404s | 🔴 | Existing-target versions of Blocks 2/3 added in §4.3; new links added only in Sprint 3c |
| **P7** | Finding N4 cites `/amplicon-size-calculator` (live **404**, never in git) and mixes query-level 19–30% CTRs with page-level data | 🟠 | §2 callout: winners = `/pcr-product-calculator` 3.0% + `/dna-3d` 11.8%; side-action = 301 the 404 URL if GSC still shows it |
| **P8** | Tier-1 #8 would retarget `/primer` (0.73% CTR) at a secondary intent; #11 rewrites a 1.47%-CTR near-winner | 🔟 | Both **HELD**; 11 actionable rows reordered into Batches A/B/C by CTR-gap (§3 callout) |
| **P9** | §6.4 "80+ schema-only FAQ pages" stale; no ops gates referenced anywhere (deploy path, pre-flight, quotas, lint) | 🟠 | Real count today = **37/209** → separate ticket, doesn't block Sprint 1; ops gates added to banner + §5 |

**Independently VERIFIED correct (kept as-is):** Finding N1 mobile>desktop CTR inversion (our export: desktop 0.59% / 324K impr vs mobile 1.19% — desktop = 89% of impressions) · Finding N2 USA crisis (our export: USA 85,156 impr @0.30% pos 13.34 vs India 56,538 @1.20% pos 9.25) · all 15 Tier-1 URLs exist and proposed titles are ≤55ch · Block 1's 6 link targets all resolve · Strike Issue A is sound (AI-artifact phrasing; anti-cannibalization-aligned) · §6.1/6.3/6.6/6.8 guardrails match house rules.

**Side findings raised during QA (not part of v3):**
1. **37 FAQPage pages carry schema questions absent from visible text** — needs its own ticket (see §6.4 callout).
2. **`/amplicon-size-calculator` 404** — check GSC for residual impressions on that URL; if present, 301 → `/pcr-product-calculator`.
3. **Broken git ref `refs/remotes/origin/main 3`** (space in name, warned on every git command) — **removed** 2026-11-05 via `git update-ref -d`.
4. `related-tools` class has **zero CSS** in `frontend/` — style decision owed in Sprint 1.

**Execution gates for every row of this plan** (from repo ops, absent in raw v3): `scripts/pre_gsc_check.sh` 9/9 PASS before any GSC submission · surgical `aws s3 cp` only, **never `deploy/aws/sync-frontend.sh`** (TICKET-1 / GitHub #8 P0 — still open) · verify 8/8 CMS uploads intact around any S3 op · CloudFront invalidation (include both clean + `.html` forms) · `deploy/aws/indexnow_ping.sh` after deploy · `scripts/rules_lint.py` 0 errors · FAQ-mirror gate (visible == schema, character-exact) before any FAQ/schema edit · GSC Request-Indexing ≈10 URLs/day, ≥30 s apart · crawl freeze until the Day-7 checkpoint clears · commit/push/deploy only on explicit owner go.

---

*End of v3 (QA-patched edition). Save alongside v1 and v2. **Execution order: Day-7 checkpoint (owner, overdue) → Sprint 1 per v2 §3 templates → Sprint 2 Tier 1 batches A/B/C from Nov 10 (post-checkpoint) → Sprint 3 = 2 builds + 4 merges → measurement.***

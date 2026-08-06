# VigyanLLM GEO Baseline — AI-Search Visibility
**Baseline captured: 2026-08-06**
**Method:** 10 core bioinformatics tool queries run through web search (proxy for the index that Perplexity / ChatGPT / Google SGE cite from). Score per term: whether `vigyanllm.in` surfaced at all, and in what form (tool page vs blog vs absent).

---

## Verdict
**2 / 10 terms surface VigyanLLM. 8 / 10 are completely invisible in AI-search index results.**
The one true citation is the `/primer` tool page (queried content is being indexed and parsed). One blog post (`/blog/best-free-bioinformatics-tools-2026`) surfaces for BLAST — but **not** the `/blast` tool page itself. Every other tool page we maintain (`tm-calculator`, `gc-calculator`, `dna-to-rna`, `reverse-complement`, `msa`, `docking`, `blast`) is absent.

## Term-by-term results

| # | Query (approx) | VigyanLLM surfaced? | Form | Notes |
|---|----------------|--------------------|------|-------|
| 1 | best primer design tool free online | ✅ | `/primer` tool page | Only direct tool-page citation found |
| 2 | best free online BLAST tool | 🟡 | blog post only | `/blog/best-free-bioinformatics-tools-2026`, not `/blast` |
| 3 | primer Tm calculator online | ❌ | — | sciencecodons, biotoolshub, tmcalculator.us, thermofisher dominate |
| 4 | qPCR primer design tool | ❌ | — | IDT owns this SERP |
| 5 | free online molecular docking tool | ❌ | — | SeamDock, ProteinIQ, moleculardocking.online, mcule |
| 6 | free online multiple sequence alignment | ❌ | — | EBI/MAFFT/CUSABIO + vectorbuilder |
| 7 | GC content calculator DNA | ❌ | — | biotoolskit, codontable, nucleoscan, biologicscorp |
| 8 | reverse complement calculator | ❌ | — | vectorbuilder, sciencecodons, biotoolskit, qiagen |
| 9 | DNA to protein translation tool | ❌ | — | sciencecodons, seqanalysis, biotoolskit, proteinIQ |
| 10 | CRISPR gRNA design tool | ❌ | — | genscript, synthego, IDT, benchling, CRISPick/CRISPOR |

## Emerging competitor pattern (important)
A wave of **new, low-competition tool aggregator sites** published/refreshed in **2026** dominate the long-tail tool terms where we are absent:
- `sciencecodons.com`, `biotoolskit.com`, `biotoolshub.org`, `seqanalysis.org`, `simulations4all.com`, `tmcalculator.us`, `calculorium.com`, `calculatorlib.com`

These are exactly the "5 targeted pages capturing untapped long-tail queries" opportunity — but being taken by smaller, faster movers. They are beatable (thin content, generic templates) but the window is closing as they accumulate indexation and links.

## Recommended next moves (ranked)
1. **Fix the BLAST gap** (cheapest win): the blog post ranks but `/blast` doesn't. Add GEO-appropriate FAQ content + a definitional block to the `/blast` and internal-link from the blog post to the tool page.

## Status update — GEO blocks shipped 2026-08-06
The GEO Quick-Answer block pattern (below-H1, "What is this tool?" + "How do I use it online?") has now been applied to all **8** core tool pages: `/blast`, `/msa`, `/docking`, `/tm-calculator`, `/gc-calculator`, `/dna-to-rna`, `/reverse-complement`, `/dna-to-protein`. FAQPage JSON-LD added to the 2 that lacked it (`reverse-complement`, `dna-to-protein`). Combined tool-page impressions covered: blast 285 + msa 114 + docking 156 + tm-calc 239 + gc-calc 437 + dna-to-rna 352 ≈ **1,583 impressions** now carry crawlable direct answers. Re-measure at 2026-08-27 against the term table above.
2. **GEO-answer blocks on tool pages**: add short "Quick Answer" definition + FAQ blocks directly answerable by LLM crawlers (many competitors already do this — see tmcalculator.us, simulations4all "Quick Answer").
3. **Re-measure 2026-08-27** alongside the GSC CTR check (Option 3). Track this doc's table as the before/after.

## Methodology honesty
- This used web-search results as a proxy for AI-assistant citation. It measures the **index layer** both Perplexity/ChatGPT/SGE retrieve from. It is not a literal Perplexity/ChatGPT query (those require per-platform UI access), but index-visibility is the necessary condition for any citation, so an absence here is a real gap signal.
- A literal per-platform check (Perplexity/Google AI Overviews/ChatGPT with browsing) is a follow-up worth doing manually since it's UI-bound.

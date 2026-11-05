# TICKET-FAQ-85 — FAQ mirror violations across 85 pages (3 classes)

> **Scope extended 2026-11-05** by owner decision (was: "37 schema-only"). `scripts/faq_mirror.py`
> (commit `63e433f7`) quantified 3 violation classes on the same 209-page corpus. Filename kept
> as `ticket-faq-schema-only-37.md` for reference stability (cited by `scripts/faq_mirror.py`);
> the ticket ID is **TICKET-FAQ-85**. Same root cause (build-pipeline FAQ drift), same fix
> mechanism (build template), same owner — do not split.

- **Priority:** P2 (after Wave 1-4 deploy + Sprint 1); scope extension due before **Nov 13**
- **Owner:** dev team
- **Raised:** 2026-11-05 (QA of execution plan v3, P9) · **extended:** 2026-11-05 (Day-7 checkpoint)
- **Dependency:** per owner, blocked on the Wave 2 (C3) build-pipeline fix deploy (2026-11-04) —
  that fix addresses the schema-generation bug class; verify it landed before starting.
- **Gate:** any fix here must pass `scripts/faq_mirror.py` site-wide (0 violations) and
  `scripts/rules_lint.py` 0 errors.

## Violation classes (2026-11-05 measurement, `python3 scripts/faq_mirror.py`)

| Class | Pages | Severity | Fix |
|---|---|---|---|
| **Q-miss** (schema Q absent from visible text) | **37** | High — Google may flag as spam | Wave-2/C3 dependency; disposition split: Class A (34 boilerplate, remove schema) + Class B (3 real, add visible) below |
| **A-miss** (answer present but NOT character-exact) | **50** | Medium — drift | Likely template variable substitution; fix template, batch-fix |
| **microdata ≠ JSON-LD** (item count/order mismatch) | **39** | Medium — build bug | JSON-LD and microdata rendered with different filters; unify the filter |
| **Union (unique pages)** | **85** | | q_only=0 · a_only=9 · md_only=35 (37+50+39 = 126 with overlaps) |

**Execution priority: Q-miss (37) → A-miss (50) → microdata (39).**

## Problem

Re-run of the FAQ-mirror detector on 2026-11-05: **209 pages have FAQPage JSON-LD; on 85 of
them (union) at least one of the three violations above is present.** Q-miss alone = 37 pages
where a schema question does not appear anywhere in the page's visible text.
(The v3 plan's "80+" figure was stale — the Oct 3 mirror sweep fixed most; the three classes are the residue.)

Root cause splits cleanly into two classes:

### Q-miss disposition Class A — identical boilerplate block injected in 34 files (remove schema)

All **34** files contain the *byte-identical* 3-question block:

1. `Is VigyanLLM data secure?`
2. `Does VigyanLLM use external APIs?`
3. `What makes VigyanLLM's 24-step pipeline ...`

…present **only** in JSON-LD, never rendered. This is a global injection artifact (source:
find the script/partial that wrote it — `grep -rl 'Is VigyanLLM data secure' frontend --include='*.html'`
= the 34 below; no partials/ hit, so it was likely a one-off batch edit).

**Disposition (b): remove the FAQPage block** on all 34. Reasons: the questions are
site-boilerplate, not page-specific; rendering them visibly on utility pages
(`login`, `terms`, `payment-success`, `404`…) would be nonsense; and keeping schema the mirror
gate fails by definition. Any page here that later deserves a real FAQ gets a **page-specific**
visible+schema pair in a separate content pass.

| # | URL | Schema-only Qs |
|---|---|---|
| 1 | `/404` | 3 (boilerplate) |
| 2 | `/academic-partnership` | 3 (boilerplate) |
| 3 | `/architecture` | 3 (boilerplate) |
| 4 | `/biomedical-ai-platform` | 3 (boilerplate) |
| 5 | `/changelog` | 3 (boilerplate) |
| 6 | `/compare` | 3 (boilerplate) |
| 7 | `/cookies` | 3 (boilerplate) |
| 8 | `/db-redirect` | 3 (boilerplate) |
| 9 | `/demo` | 3 (boilerplate) |
| 10 | `/dna-3d` | 3 (boilerplate) |
| 11 | `/login` | 3 (boilerplate) |
| 12 | `/p` | 3 (boilerplate) |
| 13 | `/payment-failed` | 3 (boilerplate) |
| 14 | `/payment-success` | 3 (boilerplate) |
| 15 | `/pcr-analysis` | 3 (boilerplate) |
| 16 | `/platform` | 3 (boilerplate) |
| 17 | `/primer-blast-alternative` | 3 (boilerplate) |
| 18 | `/primer-design-best-practices` | 3 (boilerplate) |
| 19 | `/primer-design-india` | 3 (boilerplate) |
| 20 | `/primer-design-pipeline` | 3 (boilerplate) |
| 21 | `/primer3-alternative` | 3 (boilerplate) |
| 22 | `/privacy` | 3 (boilerplate) |
| 23 | `/problem` | 3 (boilerplate) |
| 24 | `/protein-docking` | 3 (boilerplate) |
| 25 | `/qpcr-primer-design` | 3 (boilerplate) |
| 26 | `/refund` | 3 (boilerplate) |
| 27 | `/roadmap` | 3 (boilerplate) |
| 28 | `/search` | 3 (boilerplate) |
| 29 | `/security` | 3 (boilerplate) |
| 30 | `/sitemap` | 3 (boilerplate) |
| 31 | `/solution` | 3 (boilerplate) |
| 32 | `/terms` | 3 (boilerplate) |
| 33 | `/validated-primer-design-report` | 3 (boilerplate) |
| 34 | `/validated-primer-design` | 3 (boilerplate) |

### Q-miss disposition Class B — real page-specific FAQs missing their visible counterpart (add visible FAQ)

These three carry **page-relevant** questions the page should be showing. **Disposition (a):
add the visible FAQ block matching the schema exactly** (mirror-safe: paste both together).

| # | URL | Schema-only Qs | Disposition |
|---|---|---|---|
| 35 | `/clustal-vs-tcoffee` | **10** — e.g. "What is Clustal and how does it work?", "What is T-Coffee and how does it differ from Clustal…" | (a) Add visible 10-Q FAQ matching schema verbatim |
| 36 | `/ncbi-primer-blast-vs-vigyanllm` | **10** — e.g. "What is NCBI Primer-BLAST and how does it work?" | (a) Add visible 10-Q FAQ matching schema verbatim |
| 37 | `/osmolarity-calculator` | **1** — "What is normal saline osmolarity?" | (a) Add visible 1-Q FAQ (or (b) remove if content direction says no) |

### Class C — A-miss: answers present but not character-exact (50 pages, disposition: fix template + batch-sync)

Schema answer text and visible answer text differ at character level (e.g. schema
"…specific salt form used, and divide by purity percent" vs visible "…specific salt form, and
divide by purity percentage"). Same question is visible — only the answer drifted. Likely build-
template variable substitution. **Fix the template, then batch-sync these 50** (visible text is
the source of truth unless the schema wording is the more accurate one):

- `/404`
- `/academic-partnership`
- `/antibiotic-stock-calculator`
- `/architecture`
- `/arrhenius-calculator`
- `/biomedical-ai-platform`
- `/biostatistics-calculator`
- `/blast-for-primer-specificity`
- `/blog/multiple-sequence-alignment-tools`
- `/blog/pcr-primer-design-step-by-step`
- `/blog/primer-design-rules`
- `/blog/primer-specificity-check`
- `/changelog`
- `/clustal-vs-tcoffee`
- `/compare`
- `/cookies`
- `/db-redirect`
- `/demo`
- `/dna-3d`
- `/dna-to-rna`
- `/docking`
- `/dose-response-calculator`
- `/gc-calculator`
- `/login`
- `/ncbi-primer-blast-vs-vigyanllm`
- `/osmolarity-calculator`
- `/p`
- `/payment-failed`
- `/payment-success`
- `/pcr-analysis`
- `/pk-pd-calculator`
- `/platform`
- `/primer-blast-alternative`
- `/primer-design-best-practices`
- `/primer-design-india`
- `/primer-design-pipeline`
- `/primer3-alternative`
- `/privacy`
- `/problem`
- `/protein-docking`
- `/qpcr-primer-design`
- `/refund`
- `/roadmap`
- `/search`
- `/security`
- `/sitemap`
- `/solution`
- `/terms`
- `/validated-primer-design-report`
- `/validated-primer-design`

### Class D — microdata ≠ JSON-LD item count/order (39 pages, disposition: unify render filter)

JSON-LD has more (or differently ordered) questions than the visible microdata FAQPage — both are
generated from the same `faqs` array but through different filters (the original build-pipeline
bug class). **Fix the build template so both render from the same filtered array:**

- `/blog/ai-in-molecular-biology`
- `/blog/annealing-temperature-optimization`
- `/blog/autodock-vina-tutorial`
- `/blog/biotech-ai-future-2026`
- `/blog/blast-results-interpretation`
- `/blog/blastn-vs-blastp`
- `/blog/colony-pcr-primer-design`
- `/blog/covid-19-rt-pcr-primers`
- `/blog/crispr-guide-design-comparison`
- `/blog/degenerate-primer-design`
- `/blog/diamond-blastx-guide`
- `/blog/dna-to-rna-transcription-online`
- `/blog/docking-score-interpretation`
- `/blog/free-blast-tool-online`
- `/blog/gc-content-calculator-guide`
- `/blog/hepatitis-b-virus-pcr`
- `/blog/hiv-viral-load-pcr`
- `/blog/hpv-genotyping-pcr`
- `/blog/isothermal-amplification-primers`
- `/blog/listeria-detection-pcr`
- `/blog/llm-for-genomics`
- `/blog/local-blast-setup`
- `/blog/molecular-docking-software-guide`
- `/blog/multiple-sequence-alignment-tools`
- `/blog/multiplex-primer-design`
- `/blog/pcr-pipette-technique`
- `/blog/pcr-primer-design-step-by-step`
- `/blog/pcr-steps`
- `/blog/primer-design-rules`
- `/blog/primer-design-tool-comparison`
- `/blog/primer-dimer-formation`
- `/blog/primer-specificity-check`
- `/blog/protein-ligand-docking-guide`
- `/blog/sequencing-primer-design`
- `/blog/snapgene-vs-vigyanllm`
- `/blog/swissdock-tutorial`
- `/blog/taqman-probe-troubleshooting`
- `/blog/touchdown-pcr-protocol`
- `/blog/what-is-pcr`

## Acceptance criteria

- [ ] **0/209 FAQPage pages with ANY violation** — `python3 scripts/faq_mirror.py` exit 0
      (site-wide: Q-miss 0 + A-miss 0 + microdata mismatch 0; was 37 / 50 / 39 = 85 union)
- [ ] Single-page deploys: `python3 scripts/faq_mirror.py <URL>` exit 0 on every changed page
- [ ] Injection source for Class A identified and no longer re-adds the block
- [ ] `scripts/rules_lint.py` 0 errors
- [ ] Surgical `aws s3 cp` deploy of changed files only — **never `deploy/aws/sync-frontend.sh`**
      (TICKET-1 / GitHub #8) — verify 8/8 CMS uploads around the S3 op, CloudFront invalidation,
      `deploy/aws/indexnow_ping.sh`
- [ ] Commit/push/deploy only on explicit owner go

## Out of scope

- Adding *new* page-specific FAQs to Class A pages (separate content pass, Sprint 3+)
- CRISPR FAQ work (held per v3 Tier 2 row #4)

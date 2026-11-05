# TICKET-FAQ-37 — 37 pages carry FAQPage schema questions with no visible FAQ

- **Priority:** P2 (after Wave 1-4 deploy + Sprint 1)
- **Owner:** dev team
- **Raised:** 2026-11-05 (QA of execution plan v3, P9)
- **Dependency:** per owner, blocked on the Wave 2 (C3) build-pipeline fix deploy (2026-11-04) —
  that fix addresses the schema-generation bug class; verify it landed before starting.
- **Gate:** any fix here must pass the FAQ-mirror gate (visible == schema, character-exact) and
  `scripts/rules_lint.py` 0 errors.

## Problem

Re-run of the FAQ-mirror detector on 2026-11-05: **209 pages have FAQPage JSON-LD; on 37 of them
at least one schema question does not appear anywhere in the page's visible text.**
(The v3 plan's "80+" figure was stale — the Oct 3 mirror sweep fixed most; this is the residue.)

Root cause splits cleanly into two classes:

### Class A — identical boilerplate block injected in 34 files (remove schema)

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

### Class B — real page-specific FAQs missing their visible counterpart (add visible FAQ)

These three carry **page-relevant** questions the page should be showing. **Disposition (a):
add the visible FAQ block matching the schema exactly** (mirror-safe: paste both together).

| # | URL | Schema-only Qs | Disposition |
|---|---|---|---|
| 35 | `/clustal-vs-tcoffee` | **10** — e.g. "What is Clustal and how does it work?", "What is T-Coffee and how does it differ from Clustal…" | (a) Add visible 10-Q FAQ matching schema verbatim |
| 36 | `/ncbi-primer-blast-vs-vigyanllm` | **10** — e.g. "What is NCBI Primer-BLAST and how does it work?" | (a) Add visible 10-Q FAQ matching schema verbatim |
| 37 | `/osmolarity-calculator` | **1** — "What is normal saline osmolarity?" | (a) Add visible 1-Q FAQ (or (b) remove if content direction says no) |

## Acceptance criteria

- [ ] FAQ-mirror detector: **0** of 209 FAQPage pages with schema-Q absent from visible text
      (re-run the 2026-11-05 script; target 209 → 206 pages or fewer, 0 misses)
- [ ] Injection source for Class A identified and no longer re-adds the block
- [ ] `scripts/rules_lint.py` 0 errors
- [ ] Surgical `aws s3 cp` deploy of changed files only — **never `deploy/aws/sync-frontend.sh`**
      (TICKET-1 / GitHub #8) — verify 8/8 CMS uploads around the S3 op, CloudFront invalidation,
      `deploy/aws/indexnow_ping.sh`
- [ ] Commit/push/deploy only on explicit owner go

## Out of scope

- Adding *new* page-specific FAQs to Class A pages (separate content pass, Sprint 3+)
- CRISPR FAQ work (held per v3 Tier 2 row #4)

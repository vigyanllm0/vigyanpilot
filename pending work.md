# Pending Work

> Created 2026-09-30 (GSC Tier-1 session). Items completed in past sessions are in `AGENTS.md`; plans older than that are in `PENDING_PLANS.md`.

## ⚠️ 0. Committed but NOT live — deploy required

The Tier-1 fixes (and the earlier auth/CSP batch) are **committed locally, not deployed**:

| What | Where | Deploy step |
|---|---|---|
| Nav 404 leak (299 files), CTR titles (5 money pages), guide CTAs (5 guides), `favicon.ico` | frontend/ (Tier-1) | `deploy/aws/sync-frontend.sh` + CloudFront invalidation |
| **Tier-2**: 223-file baked header/footer, duplicate-URL fixes, 50 noindex flips, sitemap 479→429, 10 gene expansions + fabricated-table removal | frontend/, `generate_sitemap.py`, `bake_partials.py` | same `sync-frontend.sh` + invalidation (frontend only) |
| **CloudFront function redirect map** (`/index`→`/`, `/blog/index`→`/blog`, `/header`→`/`, `/footer`→`/`) | `deploy/aws/cloudfront-functions/viewer-request.js` | **CloudFront console → Functions → update the viewer-request function code** (not covered by sync-frontend.sh) |
| CSP hosts (jsdelivr/clarity/sheetjs) + cdnjs (Tier-2 lottie), anonymous `/api/auth/me`, auth fixes | `primerforge/security.py`, `auth*.py`, `pg_auth*.py` (commits `4a7aa061`, Tier-2) | scp changed backend files to `ubuntu@13.235.133.206` + restart API — **CSP fix only takes effect after backend deploy** |
| Pipeline pocket-detector / thresholds (commit `244cee46`) | `primerforge/` | same backend deploy |
| Lambda@Edge CSP **still not attached** (prod pages serve NO CSP; live HSTS 63072000 ≠ repo 31536000) and repo file lacks the additive hosts (clarity/sheetjs/jsdelivr style+font, cdnjs) | `deploy/aws/lambda-edge/csp-headers.py` | **decision needed**: update hosts → publish Lambda@Edge version → attach to `E394TCXPIP8P6R` behavior (doing so also changes HSTS max-age — align the two values first) |

After deploy: re-check `https://www.vigyanllm.in/favicon.ico` (was live 404, now shipped), spot-check one glossary + one blog nav link on prod, confirm `/blog/index` and `/index` 301 on prod, and confirm one gene page serves the baked header (view-source: no `/partials/` fetch).

---

## 1. GSC plan — TIER 2 ✅ COMPLETE in-repo (2026-09-30) — deploy pending (§0), export items below remain

- [x] **Consolidate duplicate clusters** — in-repo portion done: internal-link audit found **0** non-canonical hrefs (no `.html`/apex/http links); `/blog/index`→`/blog` fixed in 305 files + partials + vprime JS menu; cms-admin `/index`→`/`; `blog-post.html` canonical → `/blog`; sitemap serves clean form; CloudFront redirect map now also catches `/index`, `/blog/index`, `/header`, `/footer` (needs function deploy, §0). **Remaining (data-dependent)**: enumerate the GA4/GSC URL variants for the tool clusters (DNA→RNA 6+, GC calc 7+, docking 5+, PCR calc 3+, primer/BLAST/MSA 3–5 each) and 301 any live stragglers — needs the export; re-measure **Oct 3**.
- [x] **Thin-page triage**
  - **Noindex**: 50 flips done (42 gene pages + 8 species pages), verification errors 0; sitemap regenerated **479→429** (−50 exact), robots.txt regenerated, all 10 keep genes verified indexed in sitemap.
  - **Machine translations**: **none exist in this repo** — the locale list (Korean/Japanese/Russian/…) must be identified from a GSC Pages export first, then noindexed wherever they're served from.
  - **Keep + expand (10)**: ✅ KRAS, TP53, BRCA1, BRCA2, EGFR, BRAF, HER2/ERBB2, APOE, ALK, JAK2 — **+668–711 words each** (article now 930–998 words): engine-designed 3-pair primer table (sequences, Tm, GC, amplicon + 1-based nt coordinates), pair-quality/annealing notes, **honest specificity callout** (automated Primer-BLAST = INCONCLUSIVE, not a pass), gene-specific design guidance, references. All **30 pairs re-verified position-exact** against their RefSeq accessions (fwd at product_start−1, rev-comp ending at product_end−1) in a real browser + offline.
- [x] **Server-side header/footer** — baked: 223 files carry static header/footer between `<!--vl-*-bake-start/end-->` markers via **`bake_partials.py`** (idempotent, `--check` mode, 0 stale). `includes.js` kept (a11y + `vl-includes-loaded`) but skips the fetch when content exists. Partials absolutized first (52+27 hrefs — also fixed broken nav on 115 subdir pages). Double-hamburger wiring removed from 66 files. **Fixed a pre-existing defect**: `partials/header.html` had **2 extra `</div>`** (invisible under `innerHTML` injection, real document-structure damage once baked). Browser-verified on 5 page types: 0 `/partials/` fetches, nesting assertions pass, 0 console errors; structure-check across all 529 modified HTML = 0 new issues.

### 1b. New findings from Tier-2 (need action later)

- [ ] **~44 noindexed gene pages still carry fabricated "Recommended Primer Sequences" tables** (introduced in commit `f7b365cd`). Evidence: spot-check of 3 pages × 4 sequences = **12/12 zero match** against their own claimed transcripts. The 3 keep pages (brca2/alk/jak2) were fixed in this session (tables replaced with real engine output); **bulk-fix the rest before ever re-indexing them** (replace with engine-designed pairs or delete the section).
- [ ] **Primer-BLAST specificity check is structurally inconclusive**: `auto_designer._primer_blast_check` does a single GET + heuristic regex (no RID polling), so it always returns "INCONCLUSIVE — no expected target parsed". Fix = implement RID poll + proper result parse. Until then: no "specificity verified" claims anywhere (the 10 gene pages now state this explicitly; 2 engine tests enforce inconclusive ≠ pass).
- [ ] **Hotspot-constrained gene designs (content upgrade)**: the 10 example pairs are default whole-transcript designs (stated on-page). A follow-up pass could target the variant region per gene (KRAS codon 12, BRAF V600 exon 15, JAK2 exon 14, APOE c.388–c.526, EGFR exon 19/21) using the engine's target-region support — much stronger money content.

## 2. GSC plan — TIER 3 (Oct 13–26): re-earn positions

- [ ] **Expand the Primer BLAST money page** (`/blast-for-primer-specificity`) with an FAQ section targeting already-ranking queries: "how to use primer blast" (80 imp), "primer blast tutorial" (80), "primer blast results" (41), "primer blast check specificity" (121) + SoftwareApplication/FAQPage schema.
- [ ] **Speed fixes from Phase 2** — remove `dna-loop.json` 608 KB first; then rest of Phase-2 speed list (Core Web Vitals are part of every reassessment).
- [ ] **3–5 real backlinks**: awesome-bioinformatics GitHub PR (bio.tools already sends 7 referral sessions), 2–3 university course resource pages. (Manual/outreach — no buying links.)

## 3. Data-dependent (needs user's GSC/GA4 export)

- [ ] Export GSC → Pages → "Not found (404)" (23 URLs as of Sep 30) and 301 any **legacy/external** URLs. *Internal-source 404s are already fixed by the site-wide crawl (see §4); the export is to catch old URLs still linked from outside the site.*
- [ ] Re-measure **Oct 3** — Sept 26–30 GSC data is incomplete (lag + weekend); don't judge the drop before then. **Tier-2 signals to look for**: noindexed thin pages dropping out of the index within days; "Page with redirect" errors falling (redirect map goes live with §0 deploy); impressions/CTR on the 10 expanded gene pages.
- [ ] Daily 10-min position watch Oct 1–20 on: *primer blast, ncbi primer blast, swissdock, primer3, oligoanalyzer*.
- [ ] Decision signals: impressions ≥4,500/weekday = recovery; "primer blast" >10 for 7+ days = ship money-page expansion + link building immediately.
- [ ] Check Google core-update status again — **Sept 24 spike was the September 2026 spam update (global, 2-week rollout → ~Oct 8)**, not a core update (last core update: May 2026).

## 4. Done in this session (for the record — no action needed)

- ✅ **404 leak**: crawled all 582 internal URLs; fixed 299 subdirectory files (90 blog + 209 glossary) whose header/footer nav used relative hrefs (`primer` → `/blog/primer` → 404) — 21,461 hrefs absolutized; 107 wrong absolute links retargeted (`/hub/bioinformatics` → `/hub/bioinformatics-tools`, `/landing-pages/taqman-probe-design` → `…-tool`, missing `/blog/` prefixes, comparison pages pointing into `/blog/` from wrong root, etc.); 3 links to never-built glossary terms retargeted, 3 unlinked (GAPDH/MIQE); dead "Forensic DNA Analysis Tool" tag removed; `favicon.ico` generated from logo (was live 404). Final crawl: **every internal link resolves 200** (remaining local-only 404s = dev-server static quirks; all verified 200 on live).
- ✅ **robots.txt**: already compliant with the plan's block (Allow /, Disallow /partials/ + /api/, Sitemap line) — generated 2026-09-22, no change needed.
- ✅ **CTR rewrites (5 money pages)**: `<title>` + meta + og + twitter updated per plan — specificity check (58 ch), primer design (57), oligo analyzer (53), docking (56), dna-to-rna (49). Brand suffix dropped to keep ≤65 chars; first title trimmed 66→58 ("Primer Design & Specificity Check…" → "Primer Specificity Check…"). Verified in live DOM.
- ✅ **Guide CTAs + exact anchors**: pcr-steps, docking-score-interpretation, ncbi-primer-blast-guide (had boxes; added exact anchors), dna-3d + pcr-product-calculator (2 teal CTA boxes each + exact anchors) — all 5 guides now funnel to money pages with "primer design tool" / "check primer specificity" / "free molecular docking tool" anchors.
- ✅ Core-update check (spam update Sep 24 — see §3).

## 5. Pre-existing defects (need a decision or out of scope)

- [ ] **CMS sidebar nav missing**: `cms-admin.html` JS references `.sidebar-nav a[data-tab]` (lines ~510–511) but that markup exists nowhere — tabs only switch via in-content buttons. Rebuild needs user input on items + order.
- [ ] **59-page modal variant without × close button** — those modals close only via backdrop click/Esc; audit + add close button (needs approval, cosmetic pass over 59 files).
- [ ] **Local Postgres.app refuses connections** — dev environment only; run server with forced SQLite (`/tmp/run_sqlite_server.py`).
- [ ] **Apex `vigyanllm.in` A record → 13.235.133.206** in hPanel (user action; www works).
- [ ] **Local dev server doesn't serve** `/blog/` dir-index, `robots.txt`, `favicon.ico`, `*.mp4` (prod serves all — verified live 200). Dev-parity nicety only.
- [ ] **Double-tracking risk**: 58 pages load direct `gtag.js` AND GTM — decide inside GTM container whether GA4 fires there (config decision, not code).
- [ ] Dev-only: `/api/reviews/public` 500s on SQLite (missing `rating` column — prod is PG). Harmless in prod; add column to the SQLite schema if local testing needs reviews.
- [ ] Design-audit Sprint 2+ (inline-style → design-token extraction, primer.html 338 inline styles first).
- [ ] Functional testing pass (Agents 73–80): buttons, forms, APIs, links, JS errors on live site.
- [ ] CMS decline-cookie re-verify · DB plan/token diff · final sweep (old AGENTS sprint items).

## 6. Earlier-session leftovers

- [ ] Primer BLAST verification (engine vs NCBI) — deferred.
- [ ] Gene-specific parameter tuning — deferred.
- [ ] Faculty outreach emails using `/validation` as the credibility hook (Task 2.3) — drafted, not sent (user action).
- [ ] Directory submissions (bio.tools, AlternativeTo, TAAFT, OMICtools) — payload ready in `biotools-payload.json` (user action).

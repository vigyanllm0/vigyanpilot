# Pending Work

> Created 2026-09-30 (GSC Tier-1 session). Items completed in past sessions are in `AGENTS.md`; plans older than that are in `PENDING_PLANS.md`.

## ⚠️ 0. Committed but NOT live — deploy required

The Tier-1 fixes (and the earlier auth/CSP batch) are **committed locally, not deployed**:

| What | Where | Deploy step |
|---|---|---|
| Nav 404 leak (299 files), CTR titles (5 money pages), guide CTAs (5 guides), `favicon.ico` | frontend/ (this session, newest commit) | `deploy/aws/sync-frontend.sh` + CloudFront invalidation |
| CSP hosts (jsdelivr/clarity/sheetjs), anonymous `/api/auth/me`, auth fixes | `primerforge/security.py`, `auth*.py`, `pg_auth*.py` (commit `4a7aa061`) | scp changed backend files to `ubuntu@13.235.133.206` + restart API — **CSP fix only takes effect after backend deploy** |
| Pipeline pocket-detector / thresholds (commit `244cee46`) | `primerforge/` | same backend deploy |

After deploy: re-check `https://www.vigyanllm.in/favicon.ico` (was live 404, now shipped) and spot-check one glossary + one blog nav link on prod.

---

## 1. GSC plan — TIER 2 (week of Oct 6–12): remove the quality drag

- [ ] **Consolidate duplicate clusters** (attacks 298 "Page with redirect" + 116 canonical errors + ranking instability simultaneously). Pick ONE canonical URL per keyword → 301 the rest → update internal links → remove from sitemap. Clusters from GA4 titles:
  - DNA→RNA converter: 6+ variants
  - GC content calculator: 7+ variants
  - Molecular docking: 5+ variants
  - PCR product size calculator: 3 variants
  - Primer design tool / BLAST / MSA: 3–5 variants each
  - Needs the user's GA4/GSC export to enumerate exact URLs (previous analysis offered to draft the canonical + redirect list).
- [ ] **Thin-page triage**
  - Keep + expand (10): KRAS, TP53, BRCA1, BRCA2, EGFR, BRAF, HER2, APOE, ALK, JAK2 — add 500+ words of genuinely useful content each (real primer sequences, amplicon sizes, references).
  - **Noindex (~60):** remaining gene pages, species pages (rice/wheat/yeast/zebrafish…), ALL machine translations (Korean, Japanese, Russian, Hebrew, Vietnamese, Portuguese, Spanish, Turkish, Chinese — 0–2 views, ~100% bounce). Don't delete; noindex now, rebuild if demand appears. (Supersedes the old "prune 130 thin pages" idea.)
- [ ] **Server-side header/footer** — kill the `includes.js` client-side partial fetch (`/partials/header.html` → 301 → `/partials/header` chain wastes crawl budget on every page that uses it).

## 2. GSC plan — TIER 3 (Oct 13–26): re-earn positions

- [ ] **Expand the Primer BLAST money page** (`/blast-for-primer-specificity`) with an FAQ section targeting already-ranking queries: "how to use primer blast" (80 imp), "primer blast tutorial" (80), "primer blast results" (41), "primer blast check specificity" (121) + SoftwareApplication/FAQPage schema.
- [ ] **Speed fixes from Phase 2** — remove `dna-loop.json` 608 KB first; then rest of Phase-2 speed list (Core Web Vitals are part of every reassessment).
- [ ] **3–5 real backlinks**: awesome-bioinformatics GitHub PR (bio.tools already sends 7 referral sessions), 2–3 university course resource pages. (Manual/outreach — no buying links.)

## 3. Data-dependent (needs user's GSC/GA4 export)

- [ ] Export GSC → Pages → "Not found (404)" (23 URLs as of Sep 30) and 301 any **legacy/external** URLs. *Internal-source 404s are already fixed by the site-wide crawl (see §4); the export is to catch old URLs still linked from outside the site.*
- [ ] Re-measure **Oct 3** — Sept 26–30 GSC data is incomplete (lag + weekend); don't judge the drop before then.
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
- [ ] Design-audit Sprint 2+ (inline-style → design-token extraction, primer.html 338 inline styles first).
- [ ] Functional testing pass (Agents 73–80): buttons, forms, APIs, links, JS errors on live site.
- [ ] CMS decline-cookie re-verify · DB plan/token diff · final sweep (old AGENTS sprint items).

## 6. Earlier-session leftovers

- [ ] Primer BLAST verification (engine vs NCBI) — deferred.
- [ ] Gene-specific parameter tuning — deferred.
- [ ] Faculty outreach emails using `/validation` as the credibility hook (Task 2.3) — drafted, not sent (user action).
- [ ] Directory submissions (bio.tools, AlternativeTo, TAAFT, OMICtools) — payload ready in `biotools-payload.json` (user action).

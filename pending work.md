# Pending Work

> Created 2026-09-30 (GSC Tier-1 session). Items completed in past sessions are in `AGENTS.md`; plans older than that are in `PENDING_PLANS.md`.

## ⚠️ 0. Deploy status — frontend + CloudFront function LIVE (2026-09-30); backend deploy BLOCKED

**✅ LIVE & verified on prod (2026-09-30, 18:40–19:00 UTC):**
- **Tier-1 + Tier-2 frontend** via `deploy/aws/sync-frontend.sh` (dry-run: 537 up / 0 del; bucket = 793-file mirror, md5 == local) + CloudFront invalidation `I90UWDAZZD8DYNV8A96B3ND5KF`. Post-checks: favicon 404→200, sitemap 479→429 (0 noindexed), robots 429, 10 gene expansions live + fabricated seqs gone, 50 noindex live, baked headers (0 `/partials/` fetches, nesting OK), CTR titles/guide CTAs live, 15/15 key URLs 200, browser pass clean.
- **CloudFront function** `vigyanllm-clean-urls-v6` → repo `viewer-request.js` (live-vs-repo diff was a strict superset: only the 4 new redirects) via `update-function` + `publish-function` (comment v13). Verified: `/index`, `/blog/index`, `/header`, `/footer` → 301 canonical; `.html` strip, `/tools/*`, `/crispr`, trailing-slash, AhrefsBot 403, `/api/*` passthrough all intact. Rollback assets: old code `/tmp/cf_fn_live.js`, pre-ETag `E3AEGXETSR30VB`, dist config `/tmp/dist_cfg_orig.json`.
- **Unclosed hero `<header>` defect fixed (276 pages)** — found by the deploy gate; pre-existing (verified at pre-Tier-1 revision). 181 glossary `term-header` + 84 blog heroes + 6 `article-header` + 4 `gz-hero` + 1 `lh-hero` were missing their second `</header>`, nesting the whole article inside a `header` (the `@media print` rule hid the article body; header landmark swallowed the page). Inserted `</header>` at each hero/section boundary learned from the 6 already-correct reference files; assertions (h1 in hero, no h2) + DOM gate 11/11 pages PASS + 0 imbalanced files + `bake_partials.py --check` OK. Screen rendering and links were already fine (all resolve 200) — print + semantics were the impact.

**Still pending:**

| What | Where | Deploy step |
|---|---|---|
| CSP hosts (jsdelivr/clarity/sheetjs) + cdnjs (Tier-2 lottie), anonymous `/api/auth/me`, auth fixes | `primerforge/security.py`, `auth*.py`, `pg_auth*.py` (commit `4a7aa061`) | scp to `ubuntu@13.235.133.206` + restart API — **CSP fix only takes effect after backend deploy** |
| Pipeline pocket-detector / thresholds (commit `244cee46`) | `primerforge/pipelines/*`, `primer_server.py` | same backend deploy |
| **BLOCKED: backend access** — SSH `ubuntu@13.235.133.206` publickey rejected (local key not authorized); `13.207.60.92:22` times out; no SSM agent; `ec2-instance-connect:SendSSHPublicKey` denied for IAM user `vigyanllm-deploy`. Server = `i-05d610fc36db577c9`, `/home/ubuntu/vigyanpilot` (`vigyan.service`); **9 files** pending. | | Unblock options: **(A)** authorize local pubkey (in session transcript) in ubuntu's `authorized_keys`, **(B)** grant `SendSSHPublicKey` to `vigyanllm-deploy`, or **(C)** user runs the provided scp + `systemctl restart vigyan` commands |
| Lambda@Edge CSP **still not attached** (prod pages serve NO CSP; live HSTS 63072000 ≠ repo 31536000) and repo file lacks the additive hosts (clarity/sheetjs/jsdelivr style+font, cdnjs) | `deploy/aws/lambda-edge/csp-headers.py` | **decision needed**: update hosts → publish Lambda@Edge version → attach to `E394TCXPIP8P6R` behavior (doing so also changes HSTS max-age — align the two values first) |

Post-backend-deploy checks: anon `/api/auth/me` shape, sign-in round-trip, CSP header on API responses (still none on HTML until the Lambda@Edge decision above).

---

## 1. GSC plan — TIER 2 ✅ COMPLETE (2026-09-30) — live on prod 2026-09-30 (§0); export items below remain

- [x] **Consolidate duplicate clusters** — in-repo portion done: internal-link audit found **0** non-canonical hrefs (no `.html`/apex/http links); `/blog/index`→`/blog` fixed in 305 files + partials + vprime JS menu; cms-admin `/index`→`/`; `blog-post.html` canonical → `/blog`; sitemap serves clean form; CloudFront redirect map now also catches `/index`, `/blog/index`, `/header`, `/footer` (**function deployed to prod 2026-09-30, §0**). **Remaining (data-dependent)**: enumerate the GA4/GSC URL variants for the tool clusters (DNA→RNA 6+, GC calc 7+, docking 5+, PCR calc 3+, primer/BLAST/MSA 3–5 each) and 301 any live stragglers — needs the export; re-measure **Oct 3**.
- [x] **Thin-page triage**
  - **Noindex**: 50 flips done (42 gene pages + 8 species pages), verification errors 0; sitemap regenerated **479→429** (−50 exact), robots.txt regenerated, all 10 keep genes verified indexed in sitemap.
  - **Machine translations**: **none exist in this repo** — the locale list (Korean/Japanese/Russian/…) must be identified from a GSC Pages export first, then noindexed wherever they're served from.
  - **Keep + expand (10)**: ✅ KRAS, TP53, BRCA1, BRCA2, EGFR, BRAF, HER2/ERBB2, APOE, ALK, JAK2 — **+668–711 words each** (article now 930–998 words): engine-designed 3-pair primer table (sequences, Tm, GC, amplicon + 1-based nt coordinates), pair-quality/annealing notes, **honest specificity callout** (automated Primer-BLAST = INCONCLUSIVE, not a pass), gene-specific design guidance, references. All **30 pairs re-verified position-exact** against their RefSeq accessions (fwd at product_start−1, rev-comp ending at product_end−1) in a real browser + offline.
- [x] **Server-side header/footer** — baked: 223 files carry static header/footer between `<!--vl-*-bake-start/end-->` markers via **`bake_partials.py`** (idempotent, `--check` mode, 0 stale). `includes.js` kept (a11y + `vl-includes-loaded`) but skips the fetch when content exists. Partials absolutized first (52+27 hrefs — also fixed broken nav on 115 subdir pages). Double-hamburger wiring removed from 66 files. **Fixed a pre-existing defect**: `partials/header.html` had **2 extra `</div>`** (invisible under `innerHTML` injection, real document-structure damage once baked). Browser-verified on 5 page types: 0 `/partials/` fetches, nesting assertions pass, 0 console errors; structure-check across all 529 modified HTML = 0 new issues.

### 1b. New findings from Tier-2 (need action later)

- [ ] **~44 noindexed gene pages still carry fabricated "Recommended Primer Sequences" tables** (introduced in commit `f7b365cd`). Evidence: spot-check of 3 pages × 4 sequences = **12/12 zero match** against their own claimed transcripts. The 3 keep pages (brca2/alk/jak2) were fixed in this session (tables replaced with real engine output); **bulk-fix the rest before ever re-indexing them** (replace with engine-designed pairs or delete the section).
- [ ] **Primer-BLAST specificity check is structurally inconclusive**: `auto_designer._primer_blast_check` does a single GET + heuristic regex (no RID polling), so it always returns "INCONCLUSIVE — no expected target parsed". Fix = implement RID poll + proper result parse. Until then: no "specificity verified" claims anywhere (the 10 gene pages now state this explicitly; 2 engine tests enforce inconclusive ≠ pass).
- [ ] **Hotspot-constrained gene designs (content upgrade)**: the 10 example pairs are default whole-transcript designs (stated on-page). A follow-up pass could target the variant region per gene (KRAS codon 12, BRAF V600 exon 15, JAK2 exon 14, APOE c.388–c.526, EGFR exon 19/21) using the engine's target-region support — much stronger money content.

## 2. GSC plan — TIER 3 (Oct 13–26): re-earn positions — **STARTED Oct 1**

- [x] **Expand the Primer BLAST money page** — DONE 2026-10-01 (`29b4551f`): 4 new FAQ items (9 total; inline + FAQPage JSON-LD mirrored 1:1) targeting the 4 queries above; +327 words → 1,533; internal links to `/blog/ncbi-primer-blast-guide` + `/primer`; dropped unused `gsi/client` loader. Verified: test-client 200, tag balance, browser gate (9 FAQs in DOM, in-browser mirror OK, 0 console errors). ⚠ **Not yet on prod** — ship with next frontend sync.
- [x] **Speed fixes from Phase 2** — DONE 2026-10-01 (`23624425`): `dna-loop.json` (3.67 MB raw / 608 KB gz) + lottie loader + hero container **removed** (2.1 Option A; hero-left now full-width, home.css adjusted); `logo.png` **117 KB → 20 KB** quantized (2.3; alpha + display-size fidelity verified); `gsi/client` removed from **88 pages** — sole consumer is `primer-app.js`, which keeps it on `/primer` (2.6; ~100 KB off every other page). Verified-resolved without change: 2.7 reveal.js loads once (3/3 runs), 2.8 `/api/reviews/public` prod 200/0.64 s, 2.11 CloudFront `Compress=True`, 2.14 review-modal already `defer`. **Deferred (decision/risk):** 2.4 GTM/gtag defer (changes analytics semantics), 2.5 font-weight cut (faux-bold risk), 2.13 Clarity (already async, 4 pages). ⚠ **Not yet on prod** — ship with next frontend sync.
- [ ] **3–5 real backlinks** — **IN PROGRESS** 2026-10-01: PRs **OPEN** → danielecook/Awesome-Bioinformatics **#172** (new `## Primer Design` section: Primer3, Primer-BLAST, PrimerBank, VigyanLLM) + brandonhimpfen/awesome-bioinformatics **#29** (one entry). 3 university outreach drafts **ready to send** (Medford CSU `June.Medford@colostate.edu`, BYU DNASC `dnasc@byu.edu`, ASU LibGuide) — full briefs + email copy in **`docs/TIER3_BACKLINKS.md`**. **User actions: send the 3 emails; re-check both PRs Oct 3 / Oct 8.** Rejected targets (fit/dead/403): Leeds Omics, bioinformatics2.pitt.edu, UMass RNA tools. Pre-existing counted link: bio.tools (already live).

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

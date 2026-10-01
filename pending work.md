# Pending Work

> Created 2026-09-30 (GSC Tier-1 session). Items completed in past sessions are in `AGENTS.md`; plans older than that are in `PENDING_PLANS.md`.

## ⚠️ 0. Deploy status — frontend LIVE (latest refresh 2026-10-01); backend deploy BLOCKED

**✅ LIVE & verified on prod (2026-10-02, HQ propagation signals):** **Search/AI entity push for New Delhi** (`e2d12204` — sitemap lastmod bumps, `/about` Organization+FAQPage+FAQ section, homepage PostalAddress city/region, sovereign-ai address, `llms.txt`, IndexNow key+ping script) — dry-run 6 up / 0 del → `sync-frontend.sh` (bucket **794** = local+2 new, md5 **6/6**, cache headers intact) + invalidation `IA7XZXHI76ONCC2OFY5VKZYXRA` Completed. **Live gates 15/15** (schema types, FAQ exact mirror, address fields, lastmods, llms.txt + key file 200, 0× gurgaon/haryana). IndexNow ping → **HTTP 202**. GitHub location edit = user action (account `vigyanllm` is a User, token `vigyanllm0` can't edit → 404). User click-list: `docs/HQ_PROPAGATION.md`.

**✅ LIVE & verified on prod (2026-10-01, HQ update):** **HQ Gurgaon → New Delhi** (`5e87eb05`, 9 lines / 4 files — badges, Headquarters, GST→Delhi, JSON-LD foundingLocation, prose, registered-company line; audit §2c) — dry-run 4 up / 0 del → `sync-frontend.sh` (bucket **792** = local, md5 **4/4** on the changed files, HTML cache `max-age=300` intact) + invalidation `I7UQN85KK9KIS9ZNYUVQOC8C49` Completed. **Live gates 4/4**: `/about`, `/team`, `/about/sovereign-ai`, `/primer-design-india` all 200 with new wording + **0× gurgaon/haryana**, sovereign-ai JSON-LD parses.

**✅ LIVE & verified on prod (2026-10-01):** **Tier-3 (money page + speed fixes) + backlog fixes (Fix #8 retitle, Fix #6 gc-clamp, 22→24-step sweep)** — dry-run 148 up / 0 del → `sync-frontend.sh` (final bucket **792 = local**, `dna-loop.json` deleted, md5 8/8 on key files incl. `primer-design.html`, `gc-clamp.html`, `logo.png`, `home.css`; cache headers intact: HTML 300s, PNG immutable, CSS SWR) + invalidation `IDGE6B1LVZLQYKAZR8NMEX4T6Q` Completed. **Live gates: 37/37** (new title/H1/breadcrumb + 9-FAQ money page + gc-clamp depth H1/5th FAQ/no false claims + no dna-loop/lottie + logo 20,161 B + gsi only on /primer + 24-step everywhere, 0× 22-step, RSS valid) + **prod browser gate PASS** (amCharts4 map renders SVG, 0 console errors).

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

- [x] **Expand the Primer BLAST money page** — DONE 2026-10-01 (`29b4551f`): 4 new FAQ items (9 total; inline + FAQPage JSON-LD mirrored 1:1) targeting the 4 queries above; +327 words → 1,533; internal links to `/blog/ncbi-primer-blast-guide` + `/primer`; dropped unused `gsi/client` loader. Verified: test-client 200, tag balance, browser gate (9 FAQs in DOM, in-browser mirror OK, 0 console errors). **LIVE on prod 2026-10-01 (§0).**
- [x] **Speed fixes from Phase 2** — DONE 2026-10-01 (`23624425`): `dna-loop.json` (3.67 MB raw / 608 KB gz) + lottie loader + hero container **removed** (2.1 Option A; hero-left now full-width, home.css adjusted); `logo.png` **117 KB → 20 KB** quantized (2.3; alpha + display-size fidelity verified); `gsi/client` removed from **88 pages** — sole consumer is `primer-app.js`, which keeps it on `/primer` (2.6; ~100 KB off every other page). Verified-resolved without change: 2.7 reveal.js loads once (3/3 runs), 2.8 `/api/reviews/public` prod 200/0.64 s, 2.11 CloudFront `Compress=True`, 2.14 review-modal already `defer`. **Deferred (decision/risk):** 2.4 GTM/gtag defer (changes analytics semantics), 2.5 font-weight cut (faux-bold risk), 2.13 Clarity (already async, 4 pages). **LIVE on prod 2026-10-01 (§0).**
- [ ] **3–5 real backlinks** — **IN PROGRESS** 2026-10-01: PRs **OPEN** → danielecook/Awesome-Bioinformatics **#172** (new `## Primer Design` section: Primer3, Primer-BLAST, PrimerBank, VigyanLLM) + brandonhimpfen/awesome-bioinformatics **#29** (one entry). 3 university outreach drafts **ready to send** (Medford CSU `June.Medford@colostate.edu`, BYU DNASC `dnasc@byu.edu`, ASU LibGuide) — full briefs + email copy in **`docs/TIER3_BACKLINKS.md`**. **User actions: send the 3 emails; re-check both PRs Oct 3 / Oct 8.** Rejected targets (fit/dead/403): Leeds Omics, bioinformatics2.pitt.edu, UMass RNA tools. Pre-existing counted link: bio.tools (already live).

## 2b. Backlog fixes (Fix #8, Fix #6, honesty sweep) — ✅ DONE 2026-10-01, LIVE on prod (§0)

Fresh Sep-30 GSC export drove the decisions (position for `/primer-design` 32–44 for months; gc-clamp 972 imp / pos 8.1 / 2 clicks).

- [x] **Fix #8 — `/primer-design` differentiation** (`7711b8eb`) — **user chose "Differentiate the title"**. Original premise evaporated: "ai primer design" returns **0 rows in every export since Aug 22** (page actually gets clicks now: 891 imp + 740 apex, 1.7% CTR); real defect = title was a near-copy of `/primer`'s tool title → Google split them. Retitled **"Automated Primer Design — How It Works, Step by Step (2026)"** (title/H1/meta/OG/Twitter/breadcrumb visible + JSON-LD), new informational-led meta, +11 false `22-step`→`24` on this page. FAQPage answers re-synced from visible text (en-dash drift Q3/Q4). Gate: title==og==tw, 7/7 exact FAQ mirror, 0 console errors. **No new page created** (would worsen the cluster; the old `/free-primer-design-tool` idea is dead).
- [x] **Fix #6 — `/glossary/gc-clamp` expansion** (`63707d46`, `bf091b9c`) — H1 was still bare (missed by the Task-2 H1 pass) → depth clause **"GC clamp, the G or C bases at a primer's 3' end that anchor it to the template"**; new tip-card in first 300 words → `/gc-calculator` (varied anchor #3, claim verified: GC% + Tm outputs); FAQ 4→**5** ("How do I check whether my primer has a GC clamp?", inline + JSON-LD exact mirror); removed false claim "evaluates 3' stability at **step 18** (thermodynamic scoring)" (step 18 = Population Variant Filter/dbSNP); removed false claim "**Tm calculator reports the effect of terminal G/C bases separately**" (outputs are Tm/GC/len/MW/ΔG/oligo only) → honest before/after instruction. 1,580→1,707 words. Gate: 5/5 exact mirror, 0 errors.
- [x] **Honesty sweep — `22-step` → `24-step`** (`ad5a3be7`) — ground truth: `engine/tasks.py` registers steps 1–24 (`total_steps = 24`); `orchestrator.py`'s `total_steps: int = 22` is only a dataclass default. 69 occurrences across 58 files (50 glossary boilerplate, 6 blogs incl. FAQPage JSON-LD, biostatistics-calculator, blog/index) + `blog/rss.xml` (valid XML re-checked). Zero `22-step` left anywhere in `frontend/`. (Separate claim "22 additional validation checks" in `blog/ncbi-primer-blast-vs-vigyanllm.html` left alone — not a step count.)

### 2b follow-ups (new, need action later)

- [ ] **FAQPage mirror drift audit across the other FAQ pages** — pattern found on 2 pages (en-dash vs hyphen, US/UK spellings, inline-link text): could not have broken any previously-mirrored pair (both sides changed identically), but other pages may have **pre-existing** drift. Reusable script: `/tmp/sync_faq_ld.py` (syncs JSON-LD from visible text; extend pattern per template) — run audit across all FAQPage pages, fix diffs.
- [ ] **Orphan amCharts 5 files** — `frontend/amcharts-index.js`, `amcharts-map.js`, `amcharts-worldLow.js`, `amcharts-worldIndiaLow.js` are referenced by **nothing** (homepage lazy-loads amCharts 4: `amcharts4-*.js`, verified rendering on prod). They deploy to S3 (dead weight, ~hundreds of KB). Cleanup candidate — grep every extension for dynamic refs before deleting.

## 2c. HQ address change (Gurgaon → New Delhi) + name audit — ✅ DONE 2026-10-01

**User request**: audit for names "chinh AI / Subbrain / legal AI / VigyanLLM AI"; HQ moved Gurgaon → New Delhi (current address: New Delhi, Delhi, India).

- [x] **Name audit (repo + 4 SQLite/CMS DBs incl. 265-page `backend/cms.db` snapshot + all SQL + 517 live pages crawled)**: **ChinhAI** = 11 matches / 8 files (7 live pages + `fix_all_seo.py`); **SubBrain** = 7 matches / 6 files; **"legal AI"** = **0 anywhere**; **"VigyanLLM AI"** = **0 anywhere** (nearest legit = blog callout "VigyanLLM: AI-Native Molecular Biology Tools"). Both found names are part of the invented "three-agent (Core, SubBrain, ChinhAI)" story. **User decision: leave agent names untouched for now** → see deferred item §7.
- [x] **HQ change — 9 lines / 4 files, all verified + LIVE on prod 2026-10-01 (§0)**: `team.html:315` + `about.html:312` badges "Building from Gurgaon"→"Building from New Delhi"; `about.html:352` "Headquarters: Gurgaon, Haryana, India"→"New Delhi, India"; `about.html:353` "Registered under Haryana GST"→"Delhi GST" (**user chose: change all, GST included**); `about/sovereign-ai.html:187` JSON-LD `foundingLocation`→"New Delhi, India"; `sovereign-ai:391,427` prose→"New Delhi"; `primer-design-india.html:328`→"New Delhi"; `primer-design-india:396` registered-company line→"New Delhi, Delhi, India" (full form per user's address). Gate: repo grep **0** `gurgaon|gurugram|haryana`; JSON-LD parses (2/2); tag balance 4/4; test-client 200 ×4; browser gate PASS (0 console errors, new text rendered, old text absent).
- Note: `terms.html` jurisdiction already said "New Delhi" (no change needed); `index.html` Organization JSON-LD has only `addressCountry: IN` (unchanged — no city claim).

## 2d. HQ propagation to search & AI (flip "Gurgaon" → "New Delhi") — 🔄 SHIPPED 2026-10-02, awaiting user actions

**Trigger:** Google SERP + AI Overview still show Gurgaon (stale index of pre-10-01 `/about`; AI Overview cites our old pages). Full plan/status board: **`docs/HQ_PROPAGATION.md`**.

- [x] **Shipped 10-02** (verify in deploy below): sitemap `lastmod` bumps (about/sovereign-ai/index→10-02, team/india→10-01); `/about` gains **Organization + PostalAddress + FAQPage** (2 HQ Q&As, exact visible↔JSON-LD mirror); homepage Organization PostalAddress += `addressLocality: New Delhi`, `addressRegion: Delhi`; sovereign-ai Organization += address; new `llms.txt`; new IndexNow key `frontend/0ee82…831b.txt` + `deploy/aws/indexnow_ping.sh` (run after each deploy — NOT sync-frontend.sh, that file stays run-only).
- [ ] **User (today):** GSC request-indexing ×4 URLs (`/about` first) — exact steps in HQ_PROPAGATION.md §6; LinkedIn company location → New Delhi (§8); GitHub profile location (log in as `vigyanllm` account — NOT an org; my token `vigyanllm0` can't edit it, API 404).
- [ ] **User (this week):** Bing Webmaster verify + sitemap (§7); X bio, Crunchbase, DPIIT/Startup India profiles (§9–10); MCA INC-22 filing via CA (§11).
- [ ] **Re-check 10-05 + 10-08/09:** SERP `vigyanllm headquarters`, AI Overview, ChatGPT/Perplexity/Gemini "Where is VigyanLLM headquartered?" → log in `docs/GEO_BASELINE.md` § HQ question baseline (Google AI Overview baseline = Gurgaon, 10-01).

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

- [ ] **Invented agent names "ChinhAI" / "SubBrain" (the "three-agent" story) — deferred by user 2026-10-01** ("for now change registration address, no need to change other things"). Present in 8/6 files → 7 live pages: `solution.html`, `architecture.html`, `about.html`, `biomedical-ai-platform.html`, `primer-design-pipeline.html`, `validated-primer-design.html`, `roadmap.html` + would re-inject via `fix_all_seo.py` if re-run. Same class as PA-09's removed "VigyanInferenceEngine". When approved: reword to functional labels (Stage 1–3 / "verification layer" / "domain reasoning") — plan was specced in chat 2026-10-01.
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

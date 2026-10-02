# WEBSITE_UPDATE_PLAN.md — VigyanLLM Website Update Plan

**Status:** ✅ **EXECUTED 2026-10-02 — approved, committed (6 logical commits `4542626a`..`1433b5b6`, 541 files) + pushed to `origin/main`. Prod deploy NOT yet done (separate run-only sync action).** Final plan Steps 1–7 complete: governance (GOV-01 `rules.md` Part 1 governing + GOV-02 `docs/CLAIMS_LEDGER.md` + `scripts/rules_lint.py` gate), P0 trust/security/privacy (aggregateRating out, `/support`, 3-button cookie banner, robots routes, SEO-01..05), TRUST-04 (D-04), TRUST-02 (D-03 hosted-only truth), TRUST-03 (`audit-ready`/`lab-ready`/`clinical-grade` → 0 site-wide), PRIV-02 (D-06b GTM-only: 487 gtag loaders stripped, 494 pages GTM+consent, 0 page-level Clarity). All gates green: rules_lint 0 errors/2 accepted warnings, bake 0 stale, route smoke 432/432, browser gate 27/27, pytest baseline-identical, JSON-LD 1011/1011. Full record + queued user actions (incl. GTM Clarity consent setting): **`pending work.md` §7**; board: `AGENTS.md`.
**Prepared:** 2026-10-02 (OpenCode read-only audit & planning pass — at that stage PLAN ONLY, no code changed in producing the document)
**Deliverable location note:** Written to `/Users/macbookpro/.opencode/plan/` because the session runs in
Plan mode (plan files may only be written there). On approval, copy verbatim to the repository root
(`/Users/macbookpro/Desktop/vigyanpilot/WEBSITE_UPDATE_PLAN.md`) together with the `rules.md` merge (GOV-01).

**Inputs reviewed (all read, none substituted):**

| # | Input | Where it lives now | Status |
|---|---|---|---|
| 1 | Human-First Rules (212 lines) | `Downloads/VigyanLLM Website Rules_ Human-First Content, Design, and Review.md` | ✅ read in full |
| 2 | `vigyanllm_audit_report.md` (678 lines) | `Downloads/` + zip | ✅ read in full |
| 3 | `vigyanllm_route_by_route_appendix.md` (7,054 lines) | `Downloads/` + zip | ✅ structure, agent roster, sample route reviews |
| 4 | `vigyanllm_page_reviews.json` (434 reviews) | `Downloads/` + zip | ✅ structure + coverage reconciliation |
| 5 | `opencode_website_update_plan_prompt.md` (61 lines) | `Downloads/` | ✅ read — this document follows its required 11-section format |
| 6 | Desktop concept mockup PNG | `Downloads/vigyanllm_homepage.png` | ✅ viewed (concept only) |
| 7 | **Mobile concept mockup PNG** — provided 2026-10-02 as `02-homepage-mobile-concept.png` inside `vigyanllm_website_pngs.zip` (whole PNG pack: 7 assets + 2 `.mmd` sources + README, extracted to `Downloads/vigyanllm_website_pngs/`) | `Downloads/vigyanllm_website_pngs.zip` | ✅ available (concept only) — supersedes the earlier "unavailable" flag; per pack README every asset is concept-stage and needs owner/scientific approval before publishing |
| 8 | zip extras: `SKILL.md`, `output.txt`, `final_submit.json` | zip (streamed) | ✅ read |

**Repository is the source of truth for current implementation.** Every code-level recommendation below cites an
actual path verified during this session. Observed facts, site-stated claims, and unknowns are labeled separately.

---

## 1. Executive recommendation

**Recommended order of work, and why:**

1. **Governance first (GOV-01/GOV-02, Days 0–7):** adopt the Human-First rules as the repo's `rules.md`
   standard and build the claims ledger. Reason: every copy, schema, and design change that follows must be
   judged against a written acceptance standard; today the repo has *two contradictory rules documents*
   (see §10, D-01) and no claims register — changing 88+ files before settling the standard guarantees rework.
2. **P0 trust/security/privacy blockers (Days 1–21):** fabricated star ratings, the homepage
   sovereignty contradiction, admin-surface exposure, consent sequencing, apex DNS. Reason: these are legal/safety
   exposures and audit *release blockers* — the audit's own Gate 1 says "do not buy traffic into unresolved
   high-risk pages." They are also mostly small, surgical fixes.
3. **P1 foundations (Days 7–45):** accessibility/responsive defects, SEO hygiene (case-variant 22-Step,
   escaped Unicode, missing H1s, hreflang, sitemap accuracy), `/support` path, performance baseline.
   Reason: cheap, mechanical, removes crawl/UX noise that would mask later experiments.
4. **P2 workflow/content (Days 30–75):** glossary/blog consolidation, content registry, intent-matched CTAs,
   evidence cards. Reason: needs the ledger + registry from Phase 0 to avoid re-cannibalizing (site already has
   a documented anti-cannibalization policy).
5. **P3 measured growth (Days 60–90):** measurement contract, then the five gated experiments. Reason: no
   experiment may run before baseline + privacy review (audit rule; also our own sprint discipline).

**Tools must keep working after every phase** — §11 Release checklist + Appendix D define the per-phase gates
(pytest subset → test-client → rules linter → headless browser gate → post-deploy live gates → anon/logged-in
tool smoke).

---

## 2. Repository snapshot

### 2.1 Framework & route structure
- **Static site, no build system.** `frontend/` holds **531 HTML files** total; public inventory = **434 routes**
  (blog 91 files in `frontend/blog/`, glossary **215** in `frontend/glossary/`, landing pages **45** in
  `frontend/landing-pages/`, plus tool pages, hubs, glossary index, legal, account shells).
- Clean URLs + HTML→clean redirects handled by a **CloudFront Function** (verified live:
  `/about.html` → 301 `/about`). Local dev = Flask test client/server on port 5199 (`/tmp/run_sqlite_server.py`).
- **Shared components:** `frontend/partials/header.html`, `frontend/partials/footer.html` (+ root-level
  `frontend/header.html`, `frontend/footer.html`) — **baked into pages by `bake_partials.py`** (Tier-2 process).
  No runtime include; edits must be re-baked to propagate.
- **Design system:** `frontend/design-tokens.css` (tokens, `@media print`, `prefers-reduced-motion:reduce`
  global kill-switch at line 325), `frontend/primer.css`, `frontend/content-styles.css`, `frontend/cms-design.css`.
  Known debt: 338 inline styles on `primer.html` fight the tokens.
- **Shared JS:** `auth-shared.js`, `feature-gate.js`, `results-ui.js`, `batch-ui.js`, `cookie-banner.js`,
  `cookie-consent.js`, `search-index.js`, `primer-app.js` (minified — edited historically via Python `str.replace`),
  `config.js` (`VIGYAN_BACKEND_URL='/api'`), `admin-app.js` + `cms-content.js`/`cms-editor.html` (CMS admin UI).

### 2.2 Backends (dual — a structural fact, not an accident)
- **`primerforge/` — Flask app (tools + auth + payments).** `wsgi.py`/`primer_server.py`; SQLite dev path
  (`auth.py`) vs Postgres prod path (`pg_auth.py`, `pg_auth_routes.py`); `engine/orchestrator.py` +
  `engine/steps/step01…step22` (the **24-step pipeline**, with duplicate-numbered variant files such as
  `step06_primer3_design.py` vs `step06_msa_conservation.py`); `engine/pipeline_routes.py` (PG production
  blueprint with `allow_guest`); `payment_routes.py` (Razorpay subscriptions), `reports_routes.py` (review
  system + exports), `pg_api_routes.py`, `webhook_engine.py` (outbound user webhooks), `visitor_routes.py`
  (geo-IP), `file_scanner.py`, `threat_detection.py`.
- **`backend/` — FastAPI CMS (separate trust boundary).** `backend/routes/pages.py` (CMSPage CRUD + publish
  status), `public.py` (`/api/v1/pages` public reads + view tracking), `review.py` (CMS editorial review queue),
  `auth.py`; DB `backend/cms.db` (SQLite, 265 CMS pages); import scripts `import_static_blogs.py`,
  `import_blogs_to_cms.py` go **static → CMS only**.
- **Unknown:** no **CMS → static publish path exists** in the repo. The CMS editing surface appears
  parallel/independent of the live static site (see §10, D-12).

### 2.3 Deploy & topology (verified live this session)
- **Frontend:** `deploy/aws/sync-frontend.sh` → S3 `vigyanllm-frontend` (run-only, never edit) → CloudFront
  `E394TCXPIP8P6R` invalidation. HTML cache max-age=300/SWR=600. **www.vigyanllm.in → S3 (verified:
  `server: AmazonS3`, `x-cache: … from cloudfront`).**
- **EC2 origin nginx** (`deploy/deploy-nginx-ec2.sh`, HTTP only — "CloudFront handles SSL"):
  - `server_name vigyanllm.in` → `301 https://www.vigyanllm.in$request_uri` (apex→www over HTTP);
  - `location /api/v1/cms/` → `127.0.0.1:8001` (FastAPI CMS) with `allow 127.0.0.1; deny all;`
  - `location ~ ^/(admin|admin-reviews|cms-admin)` → **403**;
  - everything else → gunicorn `127.0.0.1:11436` (Flask).
- **Servers/DNS:** apex `vigyanllm.in` A → `13.207.60.92` (same as API origin). **HTTPS on apex times out**
  (EC2 listens on :80 only). CloudFront *already answers* `Host: vigyanllm.in` with **301 → https://www.vigyanllm.in/**
  (verified via Host-header probe) — the redirect exists at CF; only DNS points at the wrong target.
  Backend deploy target `ubuntu@13.235.133.206` (SSH blocked; unblock options A/B/C pending, §10 D-08).
  A GPU box exists (`deploy/aws/deploy-gpu.sh` → gunicorn under `/opt/vigyanllm`).
- **Legacy/inert:** `vercel.json` (www-redirect "Fix #1" + `/api/:path*` rewrites) and `middleware.js`
  — www is served by CloudFront/S3, live `/api` goes CF→EC2 origin. Treat as dead config pending verification (§10 D-07).

### 2.4 Integration inventory (what talks to what)

| Integration | Where in repo | Used for | Plan relevance |
|---|---|---|---|
| Razorpay | `primerforge/payment_routes.py`, `checkout.html`, `pricing.html` | Subscriptions Free/Pro/Lab/Enterprise, 30% academic discount | untouched by P0/P1; smoke-tested every phase |
| Google OAuth | `auth_routes.py`, `pg_auth_routes.py` (tokeninfo), `login/signup.html` | Sign-in | untouched; smoke-tested |
| Resend (email) | `pg_auth_routes.py`, migration `0112_resend_logs.sql` | Verification emails | untouched |
| GTM `GTM-KRP5LLPR` + direct gtag | 113 pages; **58 pages load BOTH**, all pre-consent | Analytics | PRIV-02 (consent gating + dedup) |
| CloudFront + S3 | `deploy/aws/*` | Hosting | INFRA-01 apex fix |
| nginx EC2 | `deploy/deploy-nginx-ec2.sh` | API proxy, apex HTTP 301, 403 admin paths | SEC-01/SEC-02 interplay |
| Razorpay webhook, user `webhook_engine.py` | `webhook_engine.py:80` | Outbound events | unchanged |
| NCBI E-utilities | `tests/test_sequence_retrieval_ncbi_virus.py`, sequence retrieval | Reference data | unchanged (audit: external lookups must be disclosed — PRIV/TRUST) |
| Engine binaries (subprocess) | `blastn`/`makeblastdb`, `mafft`, `muscle`, `obabel`, `bowtie2`, `tabix`, Primer3 | Tool computation | must keep working — Appendix D gates |
| Geo-IP API | `visitor_routes.py:101` | Visitor country (world map) | disclose in data-flow matrix (TRUST-02) |
| GitHub `vigyanllm0/vigyanpilot` | gh CLI authed | Repo | unchanged |
| IndexNow + `llms.txt` | key file + `deploy/aws/indexnow_ping.sh`, `frontend/llms.txt` (shipped 2026-10-02) | Crawl notification | keep — run after each deploy |
| Google Fonts (Montserrat/Open Sans) | font `<link>`s (434 files, `display=swap`) | Typography | PERF-01 |
| amCharts5 local | `amcharts-*.js` on homepage | World map | A11Y-01 reduced-motion gating |

### 2.5 Tests & existing verification assets
- `tests/`: 19 files — `test_guest_mode.py` (6), `test_http_only_cookie_auth.py` (3), `test_primer_server.py`,
  `test_payment_routes.py`, `test_scientific_accuracy.py`, `test_branding.py`, step tests
  (bisulfite/degenerate/mask/primer3/ranking), NCBI retrieval, promo/expense, metrics.
- Known pre-existing failures (documented in AGENTS): 4 payment tests (test-client wrapper) + 2 primer tests
  (PG enum divergence) on local Postgres; **local Postgres.app refuses connections** (§10 D-13).
- Root one-off scripts: `bake_partials.py`, `generate_sitemap.py` (**stamps `TODAY` on every URL**),
  `check_html_structure.py`, `security_audit.py`, `add_defined_term_schema.py`, `fix_all_seo.py`, `expand_glossary.py`, …
- Ad-hoc gates exist only in `/tmp` (`t_backlog_gate.py`, `sync_faq_ld.py`, `cdplib.py` browser gate) —
  **not in the repo**; GOV-02/priority `scripts/rules_lint.py` formalizes them.

### 2.6 Significant unknowns
1. Is anything still deployed on Vercel? (vercel.json exists; live headers say AWS.)
2. Which physical host is `13.207.60.92` vs `13.235.133.206` (origin vs deploy target)? Repo doesn't say.
3. How does the CMS `/api/v1/pages` public API ever reach the static site? (No publish path found.)
4. Where does `127 reviews @ 4.8★` come from? Live prod has **4 reviews @ 5.0★** (`/api/reviews/public`).
5. GTM container internal configuration (whether GA4 tag fires both via container and direct script).
6. `nginx allow 127.0.0.1; deny all;` on `/api/v1/cms/` — does prod CMS admin actually work through CF? (Owner must verify; we do not probe.)

---

## 3. Verified scope and caveats

- **Coverage:** audit declares 434 inventory routes; specialist output = 434 records across **433 unique URLs**
  (`/blog/primer3-vs-vigyanllm` reviewed twice; `/blog/phylogenetic-tree-construction` covered by a supplemental
  review); final coverage 434/434 via supplement. The team was **79 temporary specialists + 1 governance
  controller = 80 temporary audit agents — not deployed agents.** Retrieval dates 2026-10-01→10-02.
- **Visual evidence mixed:** many route reviews are HTML-only ("visual review unavailable"); no aesthetic claim
  is made for those routes.
- **Mockups are concepts**, not screenshots or capability proof. The desktop PNG (`vigyanllm_homepage.png`)
  shows concept pricing (₹9 / ₹14,999 / ₹49,999) and a "Three Agents: Core / SubBrain / ChinhAI" section —
  both **contradict current reality** (Free/Pro ₹699/Lab/Enterprise; ChinhAI/SubBrain = deferred invented-name
  issue). **Do not build either without owner confirmation.** The mobile PNG arrived later inside
  `vigyanllm_website_pngs.zip` as `02-homepage-mobile-concept.png` (concept-only, same rule applies).
- **This plan's own verification:** all repository claims below were re-checked against the live repo this
  session (counts, files, headers, routes). Where evidence is insufficient, the item is an open question (§10),
  not a conclusion. No traffic, conversion, ranking, revenue, or scientific outcome is forecast anywhere in this
  document. The "50,000 impressions/day, 10,000 clicks/day" figure in the audit is **aspirational and implies
  20% CTR — not a baseline or forecast.**
- **Read-only boundary respected:** admin/account/billing 200 responses were treated as *exposure observations*
  from public GETs already documented in the audit; no login attempts, credential tests, token guesses, form
  submissions, or control probing were performed, and none are planned from this side.

---

## 4. Prioritized backlog

Priority scale: **P0** = trust/security/privacy/science blockers · **P1** = foundations & UX/accessibility ·
**P2** = workflow/conversion/content · **P3** = measured growth. Effort = coarse relative (XS…XL).

### P0 — must fix before any promotion / traffic scaling

| ID | Affected | Evidence | Proposed change | Owner | Deps | Effort | Risk if delayed | Acceptance criteria |
|---|---|---|---|---|---|---|---|---|
| **GOV-01** | `rules.md` (repo root, 371 lines, currently "Anti-AI-Detection Design & Content Guidelines") | User instruction + attached Human-First rules; existing §1B–§1E directly **contradict** new rule #4 ("Never try to beat AI detectors") | Merge attached Human-First rules into `rules.md` as the **governing Part 1**; mark/retire anti-detector tactics sections (burstiness, detector-signal, paraphrasing-cue guidance) pending owner decision D-01; add precedence clause; reference from `AGENTS.md` pre-publish checklist | Editorial + Product | D-01 | XS | Every subsequent edit judged by wrong/contradictory standard; E-E-A-T risk (detector-gaming guidance conflicts with Google policy the audit cites) | `rules.md` contains all 12 Human-First sections verbatim; precedence statement present; no section instructs detector evasion; AGENTS.md links it |
| **GOV-02** | new `docs/CLAIMS_LEDGER.md` | Audit C2/High ("evidence-free numbers"); rules #6/#11 | Ledger: every high-consequence claim → id, page(s), exact wording, status (retain/qualify/remove), evidence, owner, review date, expiry. Seed with measured inventory (Appendix B) | Scientific QA + Legal | GOV-01 | M | Rewrites happen ad-hoc with no evidence trail; audit re-finds same issues | Ledger covers 100% of claims in the audit's list + Appendix B seeds; each row has owner+status |
| **TRUST-01** | 13 files carrying `"ratingValue":"4.8","ratingCount":"127"` (`primer, blast, docking, msa, tm-calculator, gc-calculator, dna-to-rna, demo, biostatistics-calculator, blast-for-primer-specificity, docking-for-drug-discovery, gc-calculator-for-pcr, primer-design-for-cloning, primer-design-for-qpcr` — `.html`) | Repo grep + live `/api/reviews/public` = **4 reviews, avg 5.0** | **Remove `aggregateRating` blocks** (recommendation; alternative = true count, D-02) | Frontend | none | XS | Google rich-result policy violation; rules #6 breach proven | `grep -r '"ratingCount":"127"'` = 0; all JSON-LD still parses; test-client 200 |
| **TRUST-02** | `frontend/index.html` (lines ~307, ~471 + hero/FAQ), `platform.html`, `privacy.html`, `security.html`, `dpdp.html` | Audit C3; repo grep: same file says on-premises×5, air-gapped, "US data center", "100% on-premise, zero external API", "in the browser" | One **dated mode-by-mode data-flow matrix** (browser demo vs hosted vs self-hosted: payloads, external lookups incl. NCBI/geo-IP/fonts/GTM/Razorpay, regions, retention) + rewrite contradictory copy to a single product truth | Product (decision D-03) + Privacy | D-03 | M | Users/regulators see mutually exclusive claims on one page; audit release blocker | Zero contradictory statements on homepage; matrix published and linked from privacy/security; no "zero egress/never leaves India" without evidence |
| **TRUST-03** | **audit-ready: 88 files**, lab-ready: 13, air-gapped: 7, "zero external API": 7, "no data leaves": 5, clinical-grade: 3, "validated": **313 files** (triage, not blanket) | Repo grep this session; audit C2/High | Freeze amplification → per-ledger rewrite to bounded research/computational wording; batch by template (shared footers/hero patterns), then per-page triage of "validated" (validation-data contexts may legitimately stay) | Editorial + Scientific QA | GOV-02 | L | Legal/safety exposure persists; audit's release-blocker stands | Re-run grep: 0 unqualified hits per retained-ledger rule; linter passes; spot browser gate |
| **TRUST-04** | `index.html` "Trusted by Researchers in 50+ Countries", "10K+ …" social-proof section; also `team.html` stats | Repo grep; no evidence supplied | Remove or link dated evidence (D-04) | Marketing | GOV-02 | XS | Fabricated-adoption perception; rules #6 breach | Numbers either evidence-linked in ledger or gone |
| **TRUST-05** | All 434 routes mentioning FDA/CLIA/CE/IVD/GLP/MIQE/regulatory submission vs research-only `terms.html` | Audit High | Legal/scientific copy sweep → remove regulatory-use implications or add explicit "not for clinical/regulatory use" bounds per page | Legal + Editorial | GOV-02 | L | Terms vs pages contradiction = strongest legal exposure after C3 | Sweep report: every hit retained-or-fixed; terms boundary intact and controlling |
| **TRUST-06** | Comparison pages (`primer3-vs-vigyanllm` blog, `primer-3-alternative`, `idt-vs-vigyanllm`, `autodock-vs-swissdock`, `blast-vs-diamond`, `clustal-vs-muscle`, `snapgene-vs-…`, `ncbi-primer-blast-vs-vigyanllm`) | Audit High | Versioned, source-linked, neutral matrices: state what was tested, versions, metric, limitations; official links (Primer3, Primer-BLAST, IDT, Vina) | Scientific QA | GOV-02 | M | Unverified competitor negatives | Each matrix has version/date/source; no "head-to-head" claim without protocol |
| **SEC-01** | `frontend/partials/footer.html:59-60` ("CMS Login", "Admin Panel") + `frontend/partials/header.html` (`/dashboard`, `/usage-billing`), **baked into 407 public pages** (measured); `admin-security.html` title "Admin Command Center"; `cms-login.html` | Repo grep; audit C1; live shells | (a) remove both footer links + public header entries → **re-bake 407 pages** via `bake_partials.py`; (b) redirect `/cms-login` + `/admin-security` → `/login` (D-05) or replace content with generic "login required"; (c) keep `/dashboard` + `/usage-billing` as client-gated product surfaces, strip admin-branded titles/labels; (d) owner-led server-side authz review (SEC-03) | Frontend + Security | D-05 | S | Public discovery of admin UX; audit release blocker; crawl/trust noise | `grep -rl "cms-login\|admin-security" frontend/**` = 0 public pages; shells 301/403 or generic; login/auth flows + all tools still pass gates |
| **SEC-02** | `frontend/robots.txt` | Audit robots table vs repo: Disallow `/dashboard/`, `/admin/` **do not match** real routes (`/dashboard`, `/cms-login`, `/admin-security`, `/usage-billing` have no trailing slash/`/admin` prefix) | Make disallows match real gated routes exactly (or delete no-ops); keep comment that robots ≠ authorization; keep AI-bot allowances (GEO policy) | SEO | SEC-01 | XS | False sense of control; crawl rules mislead | Live robots.txt updated; rules verified against actual routes |
| **SEC-03** | Prod server-side authorization (owner-led) | Audit C1 action line | Owner verifies: authenticated authorization before data/actions on account/billing/admin APIs, MFA for privileged ops, rate limiting, generic failures, audit logs. (We provide the checklist; **no probing from our side**) | Security (owner) | none | L | Real compromise risk remains if exposure is more than shell-level | Written owner sign-off with evidence per audit action line |
| **PRIV-01** | `cookie-banner.js` (buttons: **Accept All + Decline only** — verified), banner CSS | Audit High; repo grep | Equal-prominence **Accept All / Reject All / Manage Preferences** dialog: purpose/vendor/retention per category, non-obstructive (reserved space or compact bottom sheet, no content/CTA covering at 390×844), re-openable from footer, focus management, global non-essential default-denied | Privacy + Design | D-06 | S | Consent non-compliance perception; CTAs obscured; audit experiment 3 blocked | Banner: 3 equal buttons; manage view with categories; no overlap of CTAs at 390px; preference reopens; browser gate clean |
| **PRIV-02** | Direct `gtag/js` on 58 pages **and** GTM container; all fire pre-consent | Known GTM double-tracking item + audit consent sequencing | Gate all tag init behind consent (Google Consent Mode v2 or code-level init), remove direct gtag where GTM governs (or vice-versa — container decision D-06b), QA tag firing post-change | Analytics | PRIV-01 | S | Pre-consent optional firing (audit blocks measurement experiments until fixed) | Network capture: no gtag/GTM request before accept; no double-count after; page performance unchanged |
| **INFRA-01** | hPanel DNS: apex `A → 13.207.60.92` | This session: apex HTTPS timeout; CF answers `Host: vigyanllm.in` with 301→www | Repoint apex A to CloudFront (or CF alias) so the **already-configured** apex→www HTTPS 301 works; verify http+https apex afterwards | Owner/IT | none | XS | `https://vigyanllm.in` stays dead (timeout); non-www impressions persist; SEO equity leaks | `curl -I https://vigyanllm.in` = 301 → https://www.vigyanllm.in/ (200 chain); GSC fetch success |
| **INFRA-02** | `vercel.json`, `middleware.js` | Repo vs live headers | Verify nothing deployed on Vercel → remove inert www-redirect/API-rewrite config (or document as legacy) | Backend/IT | none | S | Config drift; future editor "fixes" a non-system (Fix #1 already suffered this) | One hosting story documented in `pending work.md`; no live route depends on vercel.json |
| **INFRA-03** | 9 pending backend files on `ubuntu@13.235.133.206` | `pending work.md` blocked item | Unblock via option A/B/C (owner choice) and deploy; run backend test subset after | Backend | D-08 | S | Backend drift vs frontend claims (e.g., review/rating data path) | Deploy recorded; prod smoke passes |

### P1 — foundations & UX/accessibility

| ID | Affected | Evidence | Proposed change | Owner | Effort | Acceptance |
|---|---|---|---|---|---|---|
| **A11Y-01** | JS motion: amCharts world map hover, homepage DNA canvas, reveal-on-scroll | CSS kill-switch exists (`design-tokens.css:325`) but audit's motion claim applies to **JS-driven** motion | Gate animations with `matchMedia('(prefers-reduced-motion: reduce)')` (map hover scale, DNA anim, smooth-scroll) | Frontend | S | With OS reduce-motion on: no continuous animation; focus/state still visible |
| **A11Y-02** | Near-black hero headings on dark navy; pale Related Terms chips; low-contrast metadata (audit visual section) | Audit renders | Token-level contrast fixes → WCAG AA (automated axe/contrast check + human spot review) | Design | S | 0 critical contrast failures in regression set |
| **A11Y-03** | Routes with 1,463px / 574px document widths at 390px viewport; clipped search/sign-in/header at 390px | Audit (identified pages via headless 390px sweep of top templates) | Responsive width contract (320/375/390/768); stack tables/cards; hide or collapse search instead of clipping; responsive header component | Design + Frontend | M | 0 horizontal overflow at agreed widths on swept set |
| **A11Y-04** | Missing programmatic labels/focus indicators; fixed overlays | Audit | Label/focus/focus-trap pass on tool forms, modals (auth/gate), consent dialog | Frontend | M | Keyboard-traversable critical flows; inline errors associated to inputs |
| **SEO-01** | `blog/best-primer-design-software-2026.html:563`, `blog/ncbi-primer-blast-vs-vigyanllm.html:422,534`, `primer-design.html:421` — literal "22-Step" (**case variants missed by earlier case-sensitive sweep**) | Repo grep `22-step` case-insensitive = 4 hits | → "24-Step" (engine ground truth = 24 steps) | Editorial | XS | repo-wide case-insensitive `22-step` = 0 |
| **SEO-02** | 16 files with literal `\u2013`/`\u00b0` sequences (e.g. `faq.html`, `primer.html`, `tm-calculator.html`, `validation.html`, 8 blog posts) | Repo grep | Decode to real characters; add linter rule | Frontend | XS | grep `\\u2013\|\\u00b0` in HTML = 0 |
| **SEO-03** | Missing `<h1>`: `developer-webhooks.html`, `account-deletion.html`, `developer-keys.html`, `blog/best-primer-design-software-2026.html`, `blog/ncbi-primer-blast-vs-vigyanllm.html`, `blog/best-free-bioinformatics-tools-2026.html` | Repo scan (9 hits − 2 partials − admin-security) | Add accurate H1s | Editorial | S | Every public page exactly ≥1 H1; linter rule added |
| **SEO-04** | hreflang `en`+`en-IN`+`en-US`+`x-default` on **80 files**, all same content | Repo grep; audit International SEO | Trim to `en` + `x-default` (D-09) — no locale variants exist to justify en-IN/en-US; revisit only if real localized pages ship | SEO | S | 80 files emit ≤2 hreflang tags; validators clean |
| **SEO-05** | `generate_sitemap.py` stamps `TODAY` for **all** URLs (would clobber hand-set lastmods); sitemap currently 429 URLs | Repo read; audit "reconcile 429 vs 434" | (a) lastmod from per-file mtime; (b) **document reconciliation**: 433 unique inventory − 4 admin shells = 429 ✓ (no legit page missing; +1 inventory dup explained) | SEO + Backend | S | Regenerating sitemap keeps per-URL dates; reconciliation note in `pending work.md` |
| **SEO-06** | DefinedTerm schema mismatch: `definedTermSet` vs `inDefinedTermSet`; pages labeled "Schema: DefinedTerm" without JSON-LD (audit Medium) | Audit technical SEO §4 | Fix property semantics; ensure visible-label↔JSON-LD parity across 215 glossary leaves; linter enforces parity | Frontend | S | All glossary JSON-LD parses; parity label=block; definedTerm relation corrected |
| **SEO-07** | Metadata/content mismatches (e.g. BLAST glossary meta promising a tool while body is a definition), malformed snippets, legacy canonicals | Audit technical SEO §3 | Route-level meta/canonical fixes for flagged pages (use appendix evidence list during execution) | SEO | S | Flagged routes: meta describes body; canonical self-referential |
| **UX-01** | No `/support`, `/help`, `/status`, `/contact` page (verified `ls` = none) | Audit Medium "operational support gap"; rules #10 | Create minimal `/support`: contact channel, issue taxonomy, account-recovery path, response expectations, **privacy-safe rules** (never request sequences/health/credentials/tokens); add to footer + sitemap | Product + Support | M | Page live 200, in sitemap, footer-linked; FAQPage optional; no sensitive-data request language |
| **PERF-01** | Multiple scripts, external fonts, duplicate cookie init, lazy above-fold logos without dimensions, ~4s curl in one env (audit: "opportunities, not measured failures") | Audit | Establish lab+field CWV baseline first; then: logo `width/height`, avoid lazy LCP, defer noncritical auth/search/analytics work **after consent**, remove duplicate initializers | Frontend + Analytics | M | Baseline recorded before/after; no regressions in gates |

### P2 — workflow / conversion / content

| ID | Affected | Evidence | Proposed change | Owner | Effort | Acceptance |
|---|---|---|---|---|---|---|
| **CONTENT-01** | Glossary 215 leaves: **identical paragraph "Common challenges include data quality issues…" on 49 files** (measured); generic "Applications" template blocks on mismatched leaves (audit names confocal, glycolysis, karyotype, phage, FACS, dose-response, drug-discovery) | Repo measurement + audit Medium/template section | Term-specific template: definition, context, primary references, assumptions, limitations, reviewer/date/version, related terms, **one relevant research-only CTA**; delete irrelevant primer/ordering/audit-ready product claims from mismatched leaves | Editorial | L | Shared-paragraph duplication count → 0; mismatched leaves purged; leaf word counts above thin threshold |
| **CONTENT-02** | Blog duplicate clusters: primer-design (basics / rules / complete-guide / step-by-step), multiplex (**4 files**: multiplex-pcr-design, multiplex-pcr-primer-design, multiplex-primer-design, pcr-multiplex-optimization), primer-dimer (formation/fix/prevention), listicles (**3**: best-free-bioinformatics-tools-2026, best-primer-design-software-2026, best-free-primer-design-tool-2026), BLAST/docking comparisons | Repo `ls` + audit Blog section + existing anti-cannibalization policy | Canonical-hub plan per cluster: keep/merge/301/differentiate decisions recorded; hub/leaf breadcrumbs; no keyword-stuffed boilerplate; **respect existing 6-rule anti-cannibalization policy** (blog=informational, tool CTAs) | Editorial + SEO | L | Cluster decision table recorded; merges shipped with 301s; no intent overlap left unrecorded |
| **CONTENT-03** | Whole content surface | Audit 31–60d deliverable | Content registry: canonical intent, audience, owner, reviewer/date, evidence level, primary CTA, deprecation status — machine-readable (`docs/CONTENT_REGISTRY.md`) | Editorial | M | Registry covers all 434 routes (or explicit exclusions) |
| **CONTENT-04** | Scientific pages lacking author/reviewer/date/version/DOI | Audit Medium | Add reviewer/date/version/source metadata to blog + glossary + hub templates (reuse existing `article:published_time` pattern) | Editorial | M | Templates emit reviewer+date; FAQ/claims reference sources |
| **CONTENT-05** | IA: canonical hubs for primer design, primer dimer, multiplex PCR, CRISPR, docking, BLAST, glossary (audit Technical SEO §5) | Audit | Hub pages + bidirectional breadcrumbs + topic internal links | SEO + Editorial | M | Each cluster has hub; breadcrumbs present; internal links bidirectional |
| **UX-02** | Generic `/primer` handoffs regardless of intent (RNA-seq, NGS, docking, glossary leaves) + missing input/data notices at tool inputs | Audit funnel leakage | Intent-matched CTA component (labels → correct tool: `/pcr-analysis`, `/blast`, `/docking`, `/tm-calculator`…); at each sequence/structure input: processing location, external services, retention, no-sensitive-data warning | Product + Frontend | M | CTAs route by context; notices present on 4 core tools; no CTA interruptions mid-bullet (audit visual defect) |
| **DESIGN-01** | Inline-style debt (338 on `primer.html`) vs tokens | Design audit (older) + rules #5 | Extract to token classes, starting with pages touched by P0/P1 (avoid blanket redesign of 434 pages) | Design + Frontend | XL (opportunistic) | Touched pages use tokens; untouched pages unchanged (no blanket redesign) |

### P3 — measured growth (only after P0 exit + baseline)

| ID | Proposed change | Owner | Effort | Acceptance |
|---|---|---|---|---|
| **MEAS-01** | Measurement contract per audit §analytics: event taxonomy (`page_view, cta_click, tool_start, valid_input, result_view, export, completion, error` + commercial events + consent events), definitions (dedup, consent state, attribution, bot treatment, retention), **never send sequences/structures/health/emails/IPs/credentials/payment-ids as payloads**; GSC baseline export; bot filtering | Analytics | L | Contract written **before** any event ships; 14–28-day reproducible baseline exists |
| **GROWTH-01..05** | The audit's five experiments (trust copy; intent routing; consent UX; pricing clarity; content consolidation) — each only with hypothesis, control, primary metric, denominator, time window, guardrails, stop rule, rollback (see §9) | Analytics + Product | M each | Pre-registration doc per experiment; guardrails green or rollback executed |
| **GROWTH-06** | Enterprise/support pack: due-diligence (deployment matrix, security/privacy evidence, SBOM/API docs), Help/Status pages, support escalation owner | Product + Security | L | Pack published; no compliance certification claimed |

---

## 5. Design-system and component plan

**Source standards:** `rules.md` (after GOV-01 merge) + attached Human-First rules + `design-tokens.css`.
Mockups = **concept** inputs only.

| Component / decision | Spec | Source | Status |
|---|---|---|---|
| **Consent dialog** | Compact non-obstructive bottom sheet (no full-height cover), 3 equal buttons, category/purpose/retention table, re-open from footer, focus trap, default-denied | Rules §10 + audit High | P0 build (PRIV-01) |
| **Evidence card** | Reusable block: method · scope · dataset/sample · comparator · uncertainty · version/date · limitations · source link; used on tool pages + `/validation` + blog claims | Rules #6/#11, audit "evidence cards" | P0/P2 |
| **Data-flow matrix** | Table: mode (browser demo / hosted / self-hosted) × payload × external service (NCBI, GTM, Razorpay, fonts, geo-IP) × region × retention × deletion | Audit C3 | P0 (TRUST-02) |
| **Intent-matched CTA** | Gradient CTA variant (existing teal 0d9488→0f766e pattern) with per-context label+target; never interrupts mid-bullet | Anti-cannibalization policy + audit UX-02 | P2 |
| **Responsive header contract** | 320/375/390/768 breakpoints; search hidden/collapsed at ≤390; no clipped controls; auth/user menu items (`/usage-billing`, `/dashboard`) only in authenticated state | Audit visual | P1 (A11Y-03, SEC-01) |
| **Tokens & typography** | Keep Montserrat/Open Sans (loaded fonts — Inter is NOT loaded; body uses `--font-b`); fix contrast tokens to WCAG AA; readable max measure; stacked tables/cards on mobile | Design audit + audit visual | P1 (A11Y-02/03) |
| **Motion** | CSS reduce-motion exists; extend to JS (map, DNA anim, reveal-on-scroll, `scroll-behavior:smooth`) | Audit motion | P1 (A11Y-01) |
| **Visual assets** | Original captioned diagrams with provenance/date/version/meaningful alt; label simulated vs observed; **no generic stock microscopy as evidence**; no fabricated authors/labs/experiments (rules #3) | Rules #7 + audit Low | P2 |
| **Mockup-only states (CONCEPT — not approved)** | "4-Hour Problem" hero, pricing ₹9/₹14,999/₹49,999, "Three Agents (Core/SubBrain/ChinhAI)", stats "70/20/1/14" | `vigyanllm_homepage.png` | ⛔ concept until owner confirms; conflicts with live pricing AND the deferred ChinhAI/SubBrain invented-name issue (rules #3 — do not ship invented agent names) |
| **Inline styles → tokens** | Gradual extraction on touched pages only (no blanket 434-page redesign) | rules #5 | P2 (DESIGN-01) |

---

## 6. Route and content plan

**Cluster decisions (map → repo files):**

| Cluster | Files | Retain / merge / rewrite / qualify / remove | Notes |
|---|---|---|---|
| Core tools | `primer.html`, `blast.html`, `docking.html`, `msa.html`, + calculators | **Retain** (product core) | Rewrite claims per TRUST-03; add input notices (UX-02); keep FAQ↔JSON-LD mirror |
| Account shells | `dashboard.html`, `usage-billing.html` | **Retain** (client-gated product) | Remove public header discovery; de-branded titles (SEC-01) |
| Admin shells | `cms-login.html`, `admin-security.html` | **Redirect/neutralize** (D-05) | Public discovery removed; nginx already 403s `/admin*` |
| Landing pages (45) | `landing-pages/*.html` | **Retain + qualify** | PA-09 sweep already ran once; re-run under ledger (TRUST-03) |
| Blog (91 files) | clusters per CONTENT-02 | **Merge/differentiate** per decision table | Citations, research-only limits, dates preserved on merges |
| Glossary (215) | term leaves | **Retain + rewrite** generic blocks | Term-specific template (CONTENT-01); education not conversion surface |
| Comparison pages | TRUST-06 list | **Rewrite (versioned/neutral)** | Official source links + tested-protocol honesty |
| Legal/privacy | `terms.html`, `privacy.html`, `cookies.html`, `security.html`, `dpdp.html` | **Rewrite (reconcile with matrix)** | Keep research-only boundary controlling; separate HIPAA/DPDP/GDPR regimes |
| Validation | `validation.html` + `validation-data.json` | **Retain as-is (model page)** | Audit calls it "a useful model for honest scope" — do not generalize beyond 3 pairs |
| Hubs | `hub/*`, `glossary/index`, `blog/index` | **Retain + strengthen** (IA hubs, breadcrumbs) | CONTENT-05 |
| New | `/support` | **Create** | UX-01 |
| sitemap/robots/llms | `sitemap.xml`, `robots.txt`, `llms.txt` | **Update** | SEO-02/05, SEC-02; keep IndexNow ping step |

Route-specific exceptions are preserved: e.g. `/validation` stays limited (never generalized);
`crispr-analysis.html` keeps its "In Development" maturity label (rules #12).

---

## 7. Technical and quality plan

- **SEO/crawlability:** robots exact-route fix (SEC-02); sitemap lastmod accuracy + reconciliation doc (SEO-05);
  hreflang trim (SEO-04); canonical/meta parity (SEO-06/07); keep clean-URL CF function + IndexNow ping after
  each deploy; no doorway/thin expansion — consolidation only (CONTENT-01/02).
- **Metadata/schema:** visible↔JSON-LD parity enforced by `scripts/rules_lint.py` (new): JSON-LD parse,
  FAQ mirror exact-match, `aggregateRating` only if ledger-backed, H1 presence, no literal `\u` escapes,
  no case-variant `22-step`, no banned unqualified claims vs ledger, no shell links in baked partials,
  sitemap↔inventory parity. Run as documented pre-step before `sync-frontend.sh` (script file itself stays run-only).
- **Security & authorization:** SEC-01 (surface reduction), SEC-03 (owner-led server-side authz/MFA/rate-limit/
  audit-log review), CSP still **not deployed** — continue the pending Lambda@Edge decision: report-only first,
  then enforce with rollback (audit Low); keep existing positive headers (X-Frame-Options DENY, nosniff,
  Referrer-Policy). **No security certification is claimed anywhere.**
- **Privacy/data-flow:** TRUST-02 matrix + UX-02 input notices; reconcile Privacy Policy ↔ UI ↔ implementation
  (browser-only vs hosted vs on-prem); consent (PRIV-01/02); DPDP page must stop implying unverified compliance
  ("DPDP-compliant" phrasing → bounded wording per ledger). Separate HIPAA/DPDP/GDPR — no conflation (audit Legal).
- **Accessibility:** A11Y-01..04 (reduced-motion, contrast, overflow/390px, focus/labels) + consent focus trap.
- **Performance:** PERF-01 (baseline → targeted fixes; no optimization claims without measurement).
- **Responsive QA:** headless sweep at 320/375/390/768 of tool pages + top templates; axe/contrast on regression set.
- **Regression tests:** existing pytest (19 files) + new linter + browser gate (CDP, console-error-free) +
  test-client route assertions + **post-deploy live gates** (schema/FAQ/lastmod/robots/llms/key-file checks as
  used in the 2026-10-01/02 deploys).

---

## 8. 30/60/90-day sequence

| Window | Phase | Entry criteria | Deliverables | Exit criteria (owner) |
|---|---|---|---|---|
| **Days 0–7** | **0 · Governance** | Owner approves plan + D-01..D-06 | `rules.md` merged (GOV-01); `CLAIMS_LEDGER.md` seeded (GOV-02); `scripts/rules_lint.py` v1; AGENTS.md checklist; **decisions D-01..D-06 recorded** | Ledger covers audit claim list; linter runs clean on unclaimed items; standards single & non-contradictory |
| **Days 1–21** | **P0 · Trust/Security/Privacy** | Phase 0 exit; D-03 sovereignty truth chosen | TRUST-01..06 (batched), SEC-01..02, PRIV-01..02, INFRA-01..02 | All P0 acceptance criteria green; **Appendix D full gate + tool smoke passes**; live gates green post-deploy |
| **Days 7–45** (parallel after D-01) | **P1 · Foundations** | P0 batches for same templates done (avoid double-editing files) | A11Y-01..04, SEO-01..07, UX-01, PERF-01 baseline | 0 overflow at agreed widths; 0 contrast failures; unicode/H1/22-step sweeps = 0; `/support` live; sitemap dates stable |
| **Days 30–75** | **P2 · Content & workflow** | GOV-02 ledger + CONTENT-03 registry started | CONTENT-01..05, UX-02, DESIGN-01 (touched pages), evidence cards | Cluster decision tables recorded; shared-paragraph dupes = 0; CTAs intent-matched; reviewer/date metadata live |
| **Days 60–90** | **P3 · Measured growth** | P0 complete; MEAS-01 baseline ≥14 days; privacy/science review per experiment | MEAS-01 contract + GROWTH-01..05 experiments (pre-registered) + GROWTH-06 pack | Each experiment has baseline/denominator/stopping rule/rollback; guardrails monitored; **no P0 regression** |

**Hard gate (audit + ours):** P0 claim/authorization/privacy/science decisions must precede paid promotion or
traffic scaling. Owner capacity/legal review delays → re-plan, don't compress verification.

---

## 9. Measurement and growth plan

**Measurement contract (write BEFORE shipping events — MEAS-01):**
- **Reach:** GSC impressions, clicks, CTR (= clicks/impressions), avg position, query/page splits, indexing status.
- **Page (consented):** `page_view`, `engaged_session`, scroll milestone, `evidence_open`, `citation_click`.
- **Activation:** `cta_impression`, `cta_click`, `tool_start`, `valid_input`, `result_view`, `export`,
  `completion`, `error`, `retry`.
- **Commercial:** `pricing_view`, `signup_start/complete`, `trial_start`, `payment_start/success`, `renewal`,
  `cancel`, `qualified_inquiry`.
- **Safety/privacy:** consent choice, policy view, claim-misunderstanding report. **Never** send sequences,
  structures, health data, raw emails, IPs, credentials, tokens, payment IDs, admin details.
- **Definitions:** identity (anon/pseudonymous), dedup, consent state, attribution window, bot treatment,
  denominators, retention, uncertainty, owner, rollback flag — all written first.

**Experiments (each requires baseline, denominator, source, control, time box, stopping rule, privacy/science/legal
review, uncertainty reporting, rollback; none promises rankings/revenue/safety/scientific outcomes):**

| # | Hypothesis | Control vs variant | Primary metric (+denominator) | Window | Guardrails | Stop rule / rollback |
|---|---|---|---|---|---|---|
| GROWTH-01 | Evidence/limitations panel increases qualified trust | current copy vs panel | qualified tool starts / eligible session | 14–28d | complaints, privacy, a11y, unsupported-claim flags | any claim regression → rollback |
| GROWTH-02 | Intent-matched CTA beats generic `/primer` handoff | generic vs task-specific (NGS/docking/calculator) | tool starts / eligible session | 14–28d | error rate, backtracking | error↑ → rollback |
| GROWTH-03 | Equal-prominence consent doesn't reduce accept-rate materially & improves comprehension | current banner vs new (PRIV-01) | zero obstruction + zero pre-choice optional tags | 14d | consent comprehension, a11y | obstruction persists → fix forward |
| GROWTH-04 | Explicit price/renewal/cancellation clarity improves activated trials | current vs explicit | activated trial / eligible session | 14–28d | chargebacks, complaints, payment errors | complaint spike → rollback |
| GROWTH-05 | Consolidated clusters improve qualified organic | cluster vs holdout | organic qualified sessions + intent-matched CTA starts | 6–8w | indexing errors, scientific QA | index errors → revert merges |

**Goal framing:** the audit's 50,000 impressions/day + 10,000 clicks/day implies **20% CTR** — labeled
*aspirational arithmetic, not forecast*; Gates 0–4 (instrument → fix blockers → 28-day baseline → evidence-led
canonical pages → scale only on measured lift) apply. Existing cadence integrates: GSC re-measure Oct 3;
HQ SERP/AI recheck Oct 5 + Oct 8/09 (`docs/GEO_BASELINE.md`, `docs/HQ_PROPAGATION.md`).

---

## 10. Open decisions and owner questions

| # | Decision | Options | Recommendation |
|---|---|---|---|
| **D-01** | Existing `rules.md` is *"Anti-AI-Detection Design & Content Guidelines"* — its §1B–§1E (burstiness, detector signals, paraphrasing cues) **contradict** Human-First rule #4 ("Never try to beat AI detectors") and rule #5 | (a) Human-First rules become governing; anti-detector tactics retired/rewritten (b) keep both as-is | **(a)** — also aligns with Google's stated policy the audit cites |
| **D-02** | `aggregateRating` 4.8/127 (live truth = 4 reviews/5.0) | remove vs show true count | **remove** until review volume is meaningful |
| **D-03** | **Sovereignty product truth**: on-prem/air-gapped vs secure-cloud/AWS vs browser-only | pick one mode story + matrix | ✅ **OWNER DECIDED 2026-10-02: hosted-only today, on-prem on roadmap** (no dates). Rewrite scope = homepage + platform/privacy/security/dpdp + features/on-premises + about/sovereign-ai + landing/blog/faq mentions |
| **D-04** | "50+ Countries", "10K+" | remove vs evidence | ✅ **OWNER DECIDED: REMOVE ALL** — adoption numbers, institution name-drop, 99.5% uptime, both testimonials (incl. named person); technical "10,000+ sequences" capability contexts retained |
| **D-05** | `/cms-login` + `/admin-security` | 301→`/login` vs generic gate page | ✅ **OWNER DECIDED: leave as-is for now** — footer links already removed; shell neutralization + real 301 (CloudFront) deferred to deploy phase |
| **D-06** | Consent strictness | (a) default-denied + equal 3 buttons (recommended by audit) vs (b) current | **(a)** |
| **D-06b** | GTM vs direct gtag (471 pages double-load — audit's "58" undercounted) | keep GTM only vs gtag only | ✅ **OWNER DECIDED: GTM only** — remove direct gtag block from all dual-load pages, add GTM loader to the 16 gtag-only pages, replace inline consent-default with a pure `dataLayer` push; owner confirms GA4 lives in the GTM container |
| **D-07** | Vercel still provisioned? | verify → retire vercel.json/middleware.js vs keep documented legacy | verify this week (INFRA-02) |
| **D-08** | Backend deploy unblock (9 files @ 13.235.133.206) | options A/B/C (already specced in `pending work.md`) | owner picks |
| **D-09** | hreflang `en-IN`/`en-US` | trim vs keep | trim (no locale variants exist) |
| **D-10** | CSP attach (Lambda@Edge) + HSTS mismatch (63072000 vs repo 31536000) | report-only first → enforce vs defer | report-only first (audit Low) |
| **D-11** | Mobile mockup PNG | supply file vs proceed without | ✅ resolved — provided 2026-10-02 as `02-homepage-mobile-concept.png` in the PNG pack; still concept-stage, owner confirmation required before any build |
| **D-12** | CMS role: does the FastAPI CMS ever publish to the static site? | wire a publish path vs document as parallel/internal tool | document reality first (repo shows import static→CMS only) |
| **D-13** | Local Postgres.app refusing connections (dev test runs) | fix local PG vs run suite in SQLite mode | fix or formally document SQLite-forced test invocation |
| **D-14** | Mockup's "Three Agents" vs ChinhAI/SubBrain deferral | mockup ships later with names vs names retired | consistent decision needed; currently deferred cleanup **and** a mockup reintroducing them |
| **D-15** | Review-count truth (`127` anywhere?) | data source found vs fabricated → remove | treated as fabricated until proven (TRUST-01) |

## 11. Release checklist (human approval, rules.md-aligned)

Every change, every phase — all boxes required:

1. [ ] Named human owner assigned to each edited public page (rules #1).
2. [ ] Qualified reviewer signed off on any scientific/privacy/security/pricing claim touched (rules #2, #6).
3. [ ] No invented author, reviewer, credential, lab, experiment, customer, quote, testimonial, award,
      institution, or user number (rules #3) — `CLAIMS_LEDGER` row exists for retained numbers.
4. [ ] No detector-evasion techniques introduced (rules #4) — D-01 resolved accordingly.
5. [ ] AI-assisted drafts reviewed before publication (rules #5); evidence links present (rules #6).
6. [ ] Citations resolvable, scope/uncertainty stated, limitations preserved (rules #6, #7).
7. [ ] No fake urgency, engagement hacks, hidden CTAs, or manipulative schema (rules #8, #9).
8. [ ] Support path exists and never requests sequences/health/credentials (rules #10).
9. [ ] Generic application blocks accurate & relevant per page (rules #11); maturity labels honest (rules #12).
10. [ ] `scripts/rules_lint.py` passes (JSON-LD parse, FAQ mirror, H1, no `\u` escapes, no case-variant
      `22-step`, no unqualified banned claims, sitemap parity, no shell links, aggregateRating ledger-backed).
11. [ ] Visual: WCAG AA contrast spot-check, no 390px overflow, reduced-motion respected, consent non-obstructive.
12. [ ] Schema↔visible parity on every edited page (200-OK text contains what JSON-LD claims).
13. [ ] **Tool gates (Appendix D)**: pytest subset green → test-client 200 on all tool routes → browser gate
      0 console errors → anon + logged-in smoke (primer run, BLAST, MSA, docking single-ligand, pricing/checkout
      render) → post-deploy live gates green.
14. [ ] Rollback noted (previous commit + S3 invalidation path); no uncommitted forbidden files
      (`bandit-report.json`, `docking_queue/`; `sync-frontend.sh` untouched).

---

## Appendix A — Findings verification log (audit claim → verdict)

| Audit claim | Verdict | Evidence (this session) |
|---|---|---|
| C1 admin/account surfaces public | **CONFIRMED + amplified** | 4 shells exist; **407 public pages** carry baked "CMS Login"/"Admin Panel" footer links (`partials/footer.html:59-60`); titles "Admin Command Center" etc.; robots `/dashboard/`,`/admin/` don't match real routes; nginx 403 covers only `^/(admin\|admin-reviews\|cms-admin)` |
| C2 scientific overclaiming | **CONFIRMED (measured)** | audit-ready 88 files · validated 313 · lab-ready 13 · air-gapped 7 · zero-external-API 7 · no-data-leaves 5 · clinical-grade 3 |
| C3 sovereignty contradiction | **CONFIRMED** | `index.html` simultaneously: on-premises×5, air-gapped, "US data center", "100% on-premise, zero external API", "in the browser" |
| "Remove unsupported aggregate ratings" | **CONFIRMED & escalated** | 13 pages hardcode 4.8★/127; live `/api/reviews/public` = **4 reviews, 5.0 avg** → proven fabricated |
| Consent lacks Manage Preferences | **CONFIRMED** | `cookie-banner.js`: Accept All + Decline only |
| No support/status path | **CONFIRMED** | no support/help/status/contact file exists |
| 22/24-step contradictions | **MOSTLY FIXED; 4 case-variant leftovers** | `22-step` case-insensitive = 4 hits (3 files) — earlier sweep was case-sensitive |
| Malformed Unicode `\u2013`/`\u00b0` | **CONFIRMED** | 16 files |
| Missing H1s | **CONFIRMED** | 9 files → 6 real public (2 partials + admin-security excluded) |
| hreflang same-content en/en-IN/x-default | **CONFIRMED** | 80 files, 4 tags each, identical content |
| Glossary boilerplate/thin leaves | **CONFIRMED (measured)** | identical paragraph on **49/215** glossary files; audit's mismatched-leaf examples |
| Blog duplicate clusters | **CONFIRMED** | 4 multiplex files, 3 listicles, 4 primer-design guides, primer-dimer trio |
| Sitemap 429 vs inventory 434 | **RECONCILED** | 433 unique inventory − 4 admin shells = **429 ✓** (+1 inventory duplicate) — no legit page missing |
| "No prefers-reduced-motion" | **REFUTED (CSS) / partial** | `design-tokens.css:325` global kill-switch exists; **JS-driven** motion (amCharts, DNA canvas) still ungated → A11Y-01 |
| "Sitemap links to legacy .html" | **REFUTED** | 0 `.html` hrefs in `sitemap.html` (fixed in Tier-2) |
| CSP absent | **CONFIRMED** | Lambda@Edge CSP still pending (known decision D-10) |
| GTM/gtag pre-consent + duplicates | **CONFIRMED** | 58 pages double-load; fires pre-consent |
| Performance "4s curl / duplicate cookie init" | **OPEN (unmeasured here)** | audit labels it opportunity, not failure → PERF-01 baseline first |

## Appendix B — Claim inventory seeds for GOV-02 ledger

Measured counts to seed the ledger (file counts, not claim verdicts — per-context triage required for "validated"):
`audit-ready` 88 · `validated` 313 · `lab-ready` 13 · `air-gapped` 7 · `zero external API` 7 · `no data leaves` 5 ·
`clinical-grade` 3 · `4.8/127 aggregateRating` 13 · homepage "50+ Countries" ×1, "10K+" ×1 ·
"24-step" = ground truth (24 steps) · HIPAA/DPDP/GDPR conflation scan pending (DPDP page + terms/privacy).

## Appendix C — Change inventory (what files each phase touches)

- **GOV-01/02:** `rules.md` (merge), `docs/CLAIMS_LEDGER.md` (new), `AGENTS.md`, `scripts/rules_lint.py` (new),
  `WEBSITE_UPDATE_PLAN.md` (this file → repo root).
- **P0:** `frontend/*.html` ×13 (aggregateRating), `frontend/index.html` + `platform/privacy/security/dpdp.html`
  (TRUST-02/03), claim batches across `frontend/**` (TRUST-03/05), `partials/footer.html` + `partials/header.html`
  + re-bake via `bake_partials.py` (407 pages), `cms-login.html`/`admin-security.html` (redirect/neutralize),
  `robots.txt`, `cookie-banner.js` (+ banner markup), GTM/gtag init across 58 pages, `docs/HQ`-adjacent DNS step
  (hPanel, owner), `vercel.json`/`middleware.js` (retire), `pending work.md` deploy record.
- **P1:** `design-tokens.css`/`primer.css` (contrast), templates touched by overflow sweep, `sitemap.xml` +
  `generate_sitemap.py`, hreflang ×80, glossary schema fixes, `support.html` (new) + footer/sitemap link,
  performance files as baselined.
- **P2:** glossary leaves (215-scoped), blog cluster files (CONTENT-02 list), `docs/CONTENT_REGISTRY.md` (new),
  tool pages (input notices + CTAs), template metadata (reviewer/date).
- **P3:** analytics init (consented events), experiment landing variants, `docs/` measurement docs.
- **Never:** `bandit-report.json`, `docking_queue/`, edits to `deploy/aws/sync-frontend.sh` (run-only).

## Appendix D — Tool-safety verification gates (run after every phase)

```bash
# 1. Unit/integration (SQLite-forced where local PG is down, D-13)
python3 -m pytest tests/test_guest_mode.py tests/test_http_only_cookie_auth.py \
                 tests/test_primer_server.py tests/test_branding.py -q

# 2. Static quality
python3 scripts/rules_lint.py            # new — JSON-LD parse, FAQ mirror, H1, unicode,
                                         # 22-step, banned-claims, sitemap parity, shell links
python3 check_html_structure.py          # existing tag-balance check

# 3. Serve + route smoke (Flask test client): every tool route 200
#    /primer /blast /msa /docking /tm-calculator /gc-calculator /dna-to-rna
#    /pricing /checkout /dashboard /support  + JSON-LD assertions on edited pages

# 4. Headless browser gate (CDP): 0 console errors; render text assertions;
#    real anon analysis run on /primer (HBB) renders pairs; auth modal opens;
#    consent dialog shows 3 equal buttons and does not cover the CTA at 390px

# 5. Post-deploy live gates
#    curl checks: schema types + FAQ mirror + robots routes + sitemap lastmod
#    + llms.txt + IndexNow key + apex/www redirects (after INFRA-01)
bash deploy/aws/indexnow_ping.sh          # after every frontend deploy
```
Tool smoke (anon **and** logged-in): primer auto-design 1 pair, BLAST short query, MSA 3 seqs,
single-ligand docking, pricing render, checkout render (no payment). Any failure → stop the phase, fix or revert.

---

**Final statement:** No website code or live content was changed to produce this plan. Where evidence was
insufficient, items are marked as open questions (§10) rather than conclusions. The once-unavailable input
`vigyanllm_homepage_mobile.png` was later supplied (2026-10-02) as `02-homepage-mobile-concept.png` in the
PNG pack — concept-only, owner confirmation still required before building from it.

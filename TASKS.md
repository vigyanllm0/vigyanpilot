# VIGYANLLM — MASTER TASK TRACKER

**Source:** Product & Conversion Audit (Jul 2025) + Internal SEO Sprints  
**Updated:** 2026-07-20 (All PA + SEC-01..15 done)  
**Status Legend:** ✅ Done | 🟡 Partial | 🔴 Pending | ⏸️ Hold

---

## EXECUTIVE SUMMARY

| Category | Total | ✅ Done | 🟡 Partial | 🔴 Pending | Completion |
|----------|-------|---------|------------|------------|------------|
| **SEO & Content** | 14 | 10 | 1 | 3 | 71% |
| **Product & Credibility (Audit)** | 15 | 15 | 0 | 0 | 100% |
| **Business/Conversion** | 6 | 0 | 0 | 6 | 0% |
| **Backend/Security (AUDIT_REPORT.md)** | 110 | 65 | 7 | 38 | 59% |
| **TOTAL** | **145** | **90** | **8** | **47** | **62%** |

---

## SPRINT 1: SEO FOUNDATION ✅ DONE

| # | Task | Files | Status | Notes |
|---|------|-------|--------|-------|
| S1-01 | Schema markup (Organization, WebApplication, FAQ, Breadcrumb) | ~15 | ✅ Done | Foundation structured data |
| S1-02 | OG/Twitter meta tags | ~15 | ✅ Done | Social share previews |
| S1-03 | Custom 404 page | 1 | ✅ Done | Usable error page |
| S1-04 | robots.txt + noindex cleanup | 1 | ✅ Done | |
| S1-05 | Canonical URLs | ~15 | ✅ Done | |

## SPRINT 2: GLOSSARY UNBLOCK ✅ DONE

| # | Task | Files | Status | Notes |
|---|------|-------|--------|-------|
| S2-01 | Remove noindex from 141 glossary pages | 141 | ✅ Done | Doubled indexable pages |
| S2-02 | Fix glossary hreflang/self-referencing | 205 | ✅ Done | |

## SPRINT 3: SCHEMA STANDARDIZATION ✅ DONE

| # | Task | Files | Status | Notes |
|---|------|-------|--------|-------|
| H4-H6 | Standardized schema on all pages | 399 | ✅ Done | Full structured data coverage |

## SPRINT 4: META DESCRIPTIONS ✅ DONE

| # | Task | Files | Status | Notes |
|---|------|-------|--------|-------|
| M1 | Add/improve meta descriptions | 327 | ✅ Done | CTR optimization |

## SPRINT 5: BROKEN LINKS ✅ DONE

| # | Task | Files | Status | Notes |
|---|------|-------|--------|-------|
| C5-A | Remove .html suffix from glossary links | 111 | ✅ Done | 942 links fixed |
| C5-B | Fix non-existent glossary targets | 111 | ✅ Done | 32 targets fixed |
| C5-C | Remove broken Related Topics sections | 27 | ✅ Done | 105 broken links removed |

## SPRINT 6: HREFLANG ✅ DONE

| # | Task | Files | Status | Notes |
|---|------|-------|--------|-------|
| T3 | Add hreflang (en, en-IN, x-default) | 396 | ✅ Done | International targeting |

## SPRINT 7: PAGE TITLES ✅ DONE

| # | Task | Files | Status | Notes |
|---|------|-------|--------|-------|
| M5 | Optimize top page titles | 11 | ✅ Done | 40-65 chars, keyword front-loaded |

## SPRINT 8: ORPHANED PAGES ✅ DONE

| # | Task | Files | Status | Notes |
|---|------|-------|--------|-------|
| M3 | Orphan page nav links + cross-links | 4 | ✅ Done | docking, dna-3d, vprime blog |

## SPRINT 9: SITEMAP / VERCEL ✅ DONE

| # | Task | Files | Status | Notes |
|---|------|-------|--------|-------|
| V-01 | Fix vercel.json catch-all (was breaking all pages) | 1 | ✅ Done | Legacy `routes` removed |
| V-02 | Update sitemap + robots to www | 2 | ✅ Done | |

## SPRINT 10: INTERNAL LINKS ✅ DONE

| # | Task | Links | Status | Notes |
|---|------|-------|--------|-------|
| T8-A | Blog→Glossary links | 593 | ✅ Done | 50 blog posts |
| T8-B | Blog→Tool links | 120 | ✅ Done | |
| T8-C | Glossary→Tool (Try it badges) | 58 | ✅ Done | |
| T8-D | Glossary→Glossary cross-links | 996 | ✅ Done | 205 pages, 5 links max each |

---

## PRODUCT AUDIT — CRITICAL 🔴

Findings from the external Product & Conversion Audit.

| # | Finding | Severity | Status | Effort | Notes |
|---|---------|----------|--------|--------|-------|
| PA-01 | **Pricing page 404** — `/pricing` returns 404, kills conversions | 🔴 Critical | ✅ Done | 1 hr | Created frontend/pricing.html (5 plans, free-tools grid, compare table, FAQ, JSON-LD, OG/hreflang); replaced inline pricing on primer.html+docking.html with "View Pricing Plans →"; added Pricing nav link to all 411 pages; added /pricing to sitemap.xml, generate_sitemap.py, api/sitemap.xml.js |
| PA-02 | **CRISPR "Coming Soon"** — Listed in nav as live product, page is stub | 🔴 Critical | ✅ Done | 1 hr | Rewrote crispr-analysis.html from stub to honest "In Development" with Cas variants, scoring algos, blog link, email capture; amber badge on nav |
| PA-03 | **BLAST "local infrastructure" claim** — Says "runs on your local infrastructure" but uses NCBI API | 🔴 Critical | ✅ Done | 30 min | Removed false on-premises claim; replaced with honest "connects to NCBI BLAST API" description |
| PA-04 | **Compare page dishonest** — Compares to AlphaFold/Schrödinger/Benchling/Recursion, all ✓ for VP, all ✗ for competitors | 🔴 Critical | ✅ Done | 1 hr | Rewritten against real competitors (Primer3, Primer-BLAST, IDT PrimerQuest, SnapGene, Benchling) with 14 accurate feature rows using ✓/◐/✗ |
| PA-05 | **Leaked developer notes** — "Production UI should show availability", "Plan amounts come from backend price registry" visible in production | 🔴 Critical | ✅ Done | 1 hr | Removed 6 leaked dev notes from primer.html ("Production Trust Controls Buyers Expect", "backend price registry", "production UI should show", etc.) |
| PA-06 | **Future-dated content** — Blog posts dated "June 2026", copyright "© 2026" | 🔴 Critical | ✅ Done | 30 min | Verified no future-dated content — all dates at or before Jul 2026 |

## PRODUCT AUDIT — HIGH 🟠

| # | Finding | Severity | Status | Effort | Notes |
|---|---------|----------|--------|--------|-------|
| PA-07 | **Title inconsistency** — "22 Checks" in H1 vs "24-step pipeline" in text on primer page | 🟠 High | ✅ Done | 5 min | Fixed "22 Checks" → "24 Checks" in H1, schema description, FAQ; changed "24-step pipeline" → "24-check pipeline" |
| PA-08 | **No method validation/citations** — No benchmarks, no papers, no citations for any tool | 🟠 High | ✅ Done | 4 hr | Added "Scientific References" sections to 8 tool pages (primer, docking, blast, msa, tm-calc, gc-calc, pcr-analysis, compare) with proper citations |
| PA-09 | **"AI-powered" undefined** — No explanation of what ML models used, where trained | 🟠 High | ✅ Done | 4 hr | Removed false AI claims across ~30+ pages; "AI-powered" → "Automated" for primer/PCR; removed "VigyanInferenceEngine"; kept real AI for GNINA/ESMFold |
| PA-11 | **HIPAA compliance claim** — No certification, no documentation, contradicts Razorpay/web setup | 🟠 High | ✅ Done | 4 hr | Removed HIPAA from all product pages; rewrote hipaa-compliant-genomics → "Genomic Data Sovereignty"; roadmap marked aspirational |
| PA-12 | **BLAST "local exact match" unexplained** — What algorithm? What database? | 🟠 High | ✅ Done | 1 hr | Documented local exact-match mode in revised BLAST description |

## PRODUCT AUDIT — MEDIUM 🟡

| # | Finding | Severity | Status | Effort | Notes |
|---|---------|----------|--------|--------|-------|
| PA-13 | **Glossary template leaks** — "Search volume: high" visible, broken text truncation | 🟡 Medium | ✅ Done | 2 hr | Removed visible "Search volume: high/medium/low" badge from all 205 glossary HTML files |
| PA-14 | **MSA backend inconsistency** — Title says Clustal Omega, FAQ says ClustalW/MUSCLE | 🟡 Medium | ✅ Done | 30 min | Changed "ClustalW/MUSCLE-based alignment" → "Clustal Omega alignment" in FAQ and body; removed "backend compute resources" leak |
| PA-15 | **Oligo concentration on Tm calc** — Missing required input for SantaLucia NN model | 🟡 Medium | ✅ Done | 1 hr | Added field (default 0.25 μM, range 0.01-10), JS formula update, result display, FAQ |
| PA-16 | **Login gating inconsistency** — No clear policy on what requires login | 🟡 Medium | ✅ Done | 1 hr | Fixed login gating on dna-3d.html (see PA-10) — added preview above gate |
| PA-17 | **Sign-in link uses javascript:void(0)** — Nav link doesn't work | 🟡 Medium | ✅ Done | 5 min | Replaced href="javascript:void(0)" with href="#" + return false for sign-in and search trigger links across all 411 HTML files |

## PRODUCT AUDIT — LOW 🔵

| # | Finding | Severity | Status | Effort | Notes |
|---|---------|----------|--------|--------|-------|
| PA-18 | **USD pricing** — Only INR limits international market | 🔵 Low | ✅ Done | 2 hr | Added USD equivalents on pricing page (~$1.20, ~$30/mo, ~$180/mo, ~$600/mo) |
| PA-19 | **"Autonomous" overused/vague** — No clear definition | 🔵 Low | ✅ Done | 1 hr | Changed "autonomous" → "automated" in primer.html meta title and FAQ |
| PA-20 | **Docking exhaustiveness=4** — Low Vina setting raises accuracy concerns | 🔵 Low | ✅ Done | 1 hr | Added exhaustiveness docs note near Top N slider on docking.html |
| PA-21 | **Kinase Library button unexplained** | 🔵 Low | ✅ Done | 30 min | Added tooltip "Pre-loaded kinase panel for drug discovery screens" next to Kinase Library button on docking.html |
| PA-22 | **PDBbind RMSD error** — Says RMSD on PDBbind but should be RMSE/correlation | 🔵 Low | ✅ Done | 30 min | Fixed "RMSD on PDBbind core set" → "RMSE on PDBbind core set" on docking.html |

---

## BACKEND/SECURITY (AUDIT_REPORT.md) 🔴🔵

Full 110-item audit tracked in `AUDIT_REPORT.md`. Key remaining items:

| # | Finding | Severity | Status | Notes |
|---|---------|----------|--------|-------|
| SEC-01 | Hardcoded admin creds in source code | 🔴 Critical | ✅ Done | Audited — `import_static_blogs.py` reads from env vars (`CMS_ADMIN_EMAIL`, `CMS_ADMIN_PASSWORD`), no hardcoded creds |
| SEC-02 | Default JWT fallback secret | 🔴 Critical | ✅ Done | Audited — `config.py` requires `JWT_SECRET` env var, crashes if missing |
| SEC-03 | Thread-unsafe SQLite legacy auth | 🔴 Critical | ✅ Done | Uses Flask `g` (request-scoped) which is thread-safe per request; WAL mode moved to module init; added `timeout=5` |
| SEC-04 | `subprocess(shell=True)` without sanitization | 🔴 Critical | ✅ Done | Audited — all subprocess calls use lists (not `shell=True`) |
| SEC-05 | No tests/security in CI | 🟠 High | ✅ Done | Added bandit security scan, safety dependency check, and pytest to deploy.yml CI workflow |
| SEC-06 | Local-only backups, no DR | 🟠 High | ✅ Done | Added optional S3 upload to backup_daily.sh via `S3_BACKUP_BUCKET` env var |
| SEC-07 | PII in logs | 🟠 High | ✅ Done | Added PIIMaskFilter regex filter to both Flask and FastAPI logging setup — emails masked as [EMAIL REDACTED] |
| SEC-08 | deprecated `datetime.utcnow()` | 🟠 High | ✅ Done | Audited — no occurrences found |
| SEC-09 | CORS wildcard on docking server | 🟠 High | ✅ Done | Audited — `allow_origins=["https://vigyanllm.in", "http://localhost:11436", "http://localhost:5000"]` |
| SEC-10 | No data portability (DPDP) | 🟠 High | ✅ Done | `GET /api/auth/export` endpoint exists at `pg_auth_routes.py:791` |
| SEC-11 | Single gunicorn worker | 🟡 Medium | ✅ Done | Audited — `workers = multiprocessing.cpu_count()` (auto-detect) |
| SEC-12 | Edge middleware RBAC bypass | 🟡 Medium | ✅ Done | Fixed — proper cookie parsing with `Object.fromEntries()`, no substring match |
| SEC-13 | No step output validation | 🟡 Medium | ✅ Done | Added `validate_step_output()` in orchestrator.py — logs warnings on non-dict/empty output |
| SEC-14 | WAL mode per request | 🟡 Medium | ✅ Done | Moved `PRAGMA journal_mode=WAL` to module init (`_init_db_schema()`) in auth.py |
| SEC-15 | No retry on SQLite lock | 🟡 Medium | ✅ Done | Added `@_retry_on_lock(max_attempts=3)` decorator with exponential backoff |
Full detail: see `AUDIT_REPORT.md`

---

## PROPOSED SPRINT ORDER

| Sprint | Focus | Items | Est. Effort | Priority |
|--------|-------|-------|-------------|----------|
| **A** | 🆘 Kill critical trust-killers | PA-01 through PA-06 | 4-5 hr | **THIS WEEK** |
| **B** | 🚀 High-credibility fixes | PA-07 through PA-12 | 2-3 days | Next |
| **C** | 🧹 Clean up programmatic content | PA-13 through PA-17 | 4 hr | Next |
| **D** | 🌍 International + polish | PA-18 through PA-22 | 5 hr | Soon |
| **E** | 🔒 Backend security (from AUDIT_REPORT.md) | SEC-01 through SEC-15 | 2-3 days | Ongoing |

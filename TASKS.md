# VIGYANLLM — MASTER TASK TRACKER

**Source:** Product & Conversion Audit (Jul 2025) + Internal SEO Sprints  
**Updated:** 2026-07-19  
**Status Legend:** ✅ Done | 🟡 Partial | 🔴 Pending | ⏸️ Hold

---

## EXECUTIVE SUMMARY

| Category | Total | ✅ Done | 🟡 Partial | 🔴 Pending | Completion |
|----------|-------|---------|------------|------------|------------|
| **SEO & Content** | 14 | 10 | 1 | 3 | 71% |
| **Product & Credibility (Audit)** | 15 | 0 | 1 | 14 | 3% |
| **Business/Conversion** | 6 | 0 | 0 | 6 | 0% |
| **Backend/Security (AUDIT_REPORT.md)** | 110 | 56 | 9 | 45 | 51% |
| **TOTAL** | **145** | **66** | **11** | **68** | **45%** |

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
| PA-01 | **Pricing page 404** — `/pricing` returns 404, kills conversions | 🔴 Critical | 🔴 Pending | 1 hr | Create `/pricing` page with all plan tiers, INR + USD |
| PA-02 | **CRISPR "Coming Soon"** — Listed in nav as live product, page is stub | 🔴 Critical | 🔴 Pending | 1 hr | Either build the tool or demote to "Coming Soon" in nav |
| PA-03 | **BLAST "local infrastructure" claim** — Says "runs on your local infrastructure" but uses NCBI API | 🔴 Critical | 🔴 Pending | 30 min | Fix the copy — remove false on-premises claim |
| PA-04 | **Compare page dishonest** — Compares to AlphaFold/Schrödinger/Benchling/Recursion, all ✓ for VP, all ✗ for competitors | 🔴 Critical | 🔴 Pending | 1 hr | Rewrite against real competitors (Primer3, IDT, SnapGene, OligoAnalyzer) |
| PA-05 | **Leaked developer notes** — "Production UI should show availability", "Plan amounts come from backend price registry" visible in production | 🔴 Critical | 🔴 Pending | 1 hr | Audit and remove all dev notes from primer, docking, and other pages |
| PA-06 | **Future-dated content** — Blog posts dated "June 2026", copyright "© 2026" | 🔴 Critical | 🔴 Pending | 30 min | Fix dates to current, remove future timestamps |

## PRODUCT AUDIT — HIGH 🟠

| # | Finding | Severity | Status | Effort | Notes |
|---|---------|----------|--------|--------|-------|
| PA-07 | **Title inconsistency** — "22 Checks" in H1 vs "24-step pipeline" in text on primer page | 🟠 High | 🔴 Pending | 5 min | Pick one number, apply consistently |
| PA-08 | **No method validation/citations** — No benchmarks, no papers, no citations for any tool | 🟠 High | 🔴 Pending | 1-2 days | Add validation data, benchmark comparisons, citations |
| PA-09 | **"AI-powered" undefined** — No explanation of what ML models used, where trained | 🟠 High | 🔴 Pending | 4 hr | Define "AI": what models, training data, accuracy metrics |
| PA-10 | **DNA-3D login gate** — Tool requires login with no preview, demo, or screenshot | 🟠 High | 🔴 Pending | 1 hr | Add demo mode or at minimum screenshot gallery |
| PA-11 | **HIPAA compliance claim** — No certification, no documentation, contradicts Razorpay/web setup | 🟠 High | 🔴 Pending | 4 hr | Either certify or remove claim |
| PA-12 | **BLAST "local exact match" unexplained** — What algorithm? What database? | 🟠 High | 🔴 Pending | 1 hr | Document the local exact match mode |

## PRODUCT AUDIT — MEDIUM 🟡

| # | Finding | Severity | Status | Effort | Notes |
|---|---------|----------|--------|--------|-------|
| PA-13 | **Glossary template leaks** — "Search volume: high" visible, broken text truncation | 🟡 Medium | 🔴 Pending | 2 hr | Fix templates across all 205 glossary pages |
| PA-14 | **MSA backend inconsistency** — Title says Clustal Omega, FAQ says ClustalW/MUSCLE | 🟡 Medium | 🔴 Pending | 30 min | Pick one and be consistent |
| PA-15 | **Oligo concentration on Tm calc** — Missing required input for SantaLucia NN model | 🟡 Medium | 🔴 Pending | 1 hr | Add oligo concentration field |
| PA-16 | **Login gating inconsistency** — No clear policy on what requires login | 🟡 Medium | 🔴 Pending | 1 hr | Define and communicate consistent policy |
| PA-17 | **Sign-in link uses javascript:void(0)** — Nav link doesn't work | 🟡 Medium | 🔴 Pending | 5 min | Fix to proper URL |

## PRODUCT AUDIT — LOW 🔵

| # | Finding | Severity | Status | Effort | Notes |
|---|---------|----------|--------|--------|-------|
| PA-18 | **USD pricing** — Only INR limits international market | 🔵 Low | 🔴 Pending | 2 hr | Add USD/EUR pricing |
| PA-19 | **"Autonomous" overused/vague** — No clear definition | 🔵 Low | 🔴 Pending | 1 hr | Define or reduce usage |
| PA-20 | **Docking exhaustiveness=4** — Low Vina setting raises accuracy concerns | 🔵 Low | 🔴 Pending | 1 hr | Document or raise default |
| PA-21 | **Kinase Library button unexplained** | 🔵 Low | 🔴 Pending | 30 min | Add tooltip or context |
| PA-22 | **PDBbind RMSD error** — Says RMSD on PDBbind but should be RMSE/correlation | 🔵 Low | 🔴 Pending | 30 min | Fix scientific error on docking page |

---

## BACKEND/SECURITY (AUDIT_REPORT.md) 🔴🔵

Full 110-item audit tracked in `AUDIT_REPORT.md`. Key remaining items:

| # | Finding | Severity | Status | Notes |
|---|---------|----------|--------|-------|
| SEC-01 | Hardcoded admin creds in source code | 🔴 Critical | 🔴 Pending | `import_static_blogs.py:16` — email+password in plaintext |
| SEC-02 | Default JWT fallback secret | 🔴 Critical | 🔴 Pending | `config.py:5` — `"vp-cms-secret-key-change-in-production-2025"` |
| SEC-03 | Thread-unsafe SQLite legacy auth | 🔴 Critical | 🔴 Pending | `auth.py:53-59` — per-request connect with threads |
| SEC-04 | `subprocess(shell=True)` without sanitization | 🔴 Critical | 🔴 Pending | `colab_t4_docking_server.py:29` |
| SEC-05 | No tests/security in CI | 🟠 High | 🔴 Pending | `.github/workflows/deploy.yml` |
| SEC-06 | Local-only backups, no DR | 🟠 High | 🔴 Pending | No S3/cloud upload |
| SEC-07 | PII in logs | 🟠 High | 🔴 Pending | Emails logged in plaintext at 8+ locations |
| SEC-08 | deprecated `datetime.utcnow()` | 🟠 High | 🔴 Pending | 8 occurrences |
| SEC-09 | CORS wildcard on docking server | 🟠 High | 🔴 Pending | `allow_origins=["*"]` |
| SEC-10 | No data portability (DPDP) | 🟠 High | 🔴 Pending | No export endpoint |
| SEC-11 | Single gunicorn worker | 🟡 Medium | 🔴 Pending | `workers = 1` |
| SEC-12 | Edge middleware RBAC bypass | 🟡 Medium | 🔴 Pending | Cookie-based admin check |
| SEC-13 | No step output validation | 🟡 Medium | 🔴 Pending | Pipeline step outputs not validated |
| SEC-14 | WAL mode per request | 🟡 Medium | 🔴 Pending | Legacy SQLite |
| SEC-15 | No retry on SQLite lock | 🟡 Medium | 🔴 Pending | No retry logic |

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

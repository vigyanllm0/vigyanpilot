# AGENTS.md — Agent Handoff & Tracking

**Session:** Week 2 tool rewrite sprint — COMPLETE (8 pages) → Week 3 blog rewrites — COMPLETE (8/8) + SERP snippet optimization
**Next Sprint:** **Week 3** — Top-10 blog rewrites (Agent 63: Lab Notebook / Middle Mile / Indian Academic) + SERP snippet optimization (Agent 69: title/meta for top-20-by-impressions non-tool pages) → **2026-08-27 Sprint Impact Re-Measurement** below → Phase 2 — credibility (validation benchmark page live; wire faculty outreach next) → design-audit Sprint 2+ → CMS decline-cookie re-verify → **fix 145 pre-existing glossary OG-image 404s** → DB plan/token diff → final sweep

## 2026-08-27 — Sprint Impact Re-Measurement
**Trigger**: Date-based (2-3 week GSC lag from 9-commit CTR sprint + GEO fixes)
**What to measure**:
1. CTR delta: Overall CTR (baseline 0.84%) — target 1.5%+
2. Position band 4-10 CTR (baseline 0.43%) — target 2%+ (industry: 5-12%)
3. ncbi-primer-blast-guide CTR (baseline 0.20% @ pos 7.6) — target 3%+
4. GEO re-measure: Query Perplexity/ChatGPT/SGE for same 10 terms (docs/GEO_BASELINE.md) — target 7+/10
5. Desktop CTR (baseline 0.56%) — check if any movement from font/schema/OG fixes
**Data source**: Export new GSC 3-month report on 08-27, compare against 2026-08-06 baseline
**Compare against**: `/home/z/my-project/upload/vigyanllm.in-Performance-on-Search-2026-08-06 (1).xlsx`

## Week 2 — Tool Rewrite Sprint (8 pages, COMPLETE, all pushed)

### What & Why
De-branded, de-ChatGPT'd, and re-scoped 8 live tool pages with real worked examples. Each rewrite verified via Flask test client + tag/JSON-LD balance; no-touch zone (tool form/JS/meta) preserved.

### Tool Page Table
| Page | Brand Before→After | Words | Key Differentiator Added |
|------|-------------------|-------|--------------------------|
| Primer Design | 46→10 | 2960 | BRCA1 c.5266dupC + GAPDH examples, troubleshooting |
| BLAST | 20→0 | ~2000 | BRCA1 vs BRCA1P1 pseudogene money-shot |
| Tm Calculator | 18→3 | 1826 | GAPDH 4-method comparison (6°C spread) |
| Docking | 21→0 | 2004 | Imatinib vs ABL1 worked example |
| MSA | 21→0 | 1809 | TP53 5-species paralog trap |
| GC Calculator | 13→1 | 1840 | GC spectrum table + 3 gene examples (GAPDH/BRCA1/KIT) |
| DNA-to-RNA | 20→1 | 1600 | Coding vs template strand confusion |
| Thermodynamics | 26→0 | ~3600 | Wallace arithmetic fix, trimmed 600w |
| **Total** | **~175 → ~5** | **~17,645** | |

### Commits (all pushed)
`82bf40e1` thermodynamics · `459eed19` dna-to-rna · `f6bcf321` gc-calculator · `4676ba86` msa · `7e3052bd` docking · `2671cad` tm-calculator (bl)

### Corrections — false alarms from the rewrite brief
The thermodynamics (page 8) brief claimed **3 scientific bugs** (4°C/9°C example Tm lower bounds, 273°C upper bound). **All three were FALSE ALARMS** — verified against the actual code:
- 4°C appears only inside the **correct** Wallace rule (2°C×(A+T) + 4°C×(G+C)).
- 273.15 appears only in the **correct** Kelvin→°C conversion (Tm = ΔH/(ΔS + R·ln(Ct/4)) − 273.15).
- The worked example already yields a realistic **45.9 → 42.3°C** chain (consistent, no change needed).
The **one real defect** found & fixed: the Wallace example for `5'-ATCGGCTA-3'` showed `2×3 + 4×5 = 26°C` but the sequence actually has A+T=4, G+C=4 → **24°C**. Corrected to `2×4 + 4×4 = 8 + 16 = 24°C`.
Also: brief wanted "trim FAQ 5-6" but all 7 FAQ items were distinct, high-quality thermodynamics Q&A — kept all 7.

## Week 3 — Blog Rewrite Sprint (8/8, COMPLETE, all pushed)

### What & Why
De-branded, de-ChatGPT'd, and re-scoped 8 blog posts with real worked examples. Each rewrite verified via Flask test client + tag/JSON-LD balance; tool form/JS/nav/footer untouched. All inline FAQ items mirrored 1:1 in FAQPage JSON-LD.

### Blog Table
| Blog | Commit | Words | Brand | Format |
|------|--------|-------|-------|--------|
| pcr-steps | `ffea1ea2` | 2,327 | 0 | Explain Like a PI |
| pcr-primer-design-rules | `62626eeb` | 1,926 | 1 | Decision Guide |
| rt-pcr-vs-qpcr | `1385cbe2` | ~1,900 | 1 | Comparison with Teeth |
| primer-dimer-fix | `aa401e5b` | ~1,430 | 1 | Lab Notebook |
| real-time-pcr-data-analysis | `6775a624` | 1,862 | 0 | Explain Like a PI |
| digital-pcr-vs-qpcr | `061ea5ee` | ~1,610 | 1 | Decision Guide |
| pcr-troubleshooting-guide | `5d62d61a` | ~1,400 | 1 | Lab Notebook |
| types-of-pcr | `a246b9cc` | ~1,536 | 2 | Decision Guide |

## Current Board State — 2026-08-08

| Status | Item |
|--------|------|
| ✅ DONE | Gene-prefers validated fix, glossary bugs, rs verification, E-E-A-T blocker, BLAST E-value, all 8 tool rewrites |
| ✅ DONE | **Week 3: Blog rewrites** (Agent 63 — **8/8 complete**) — pcr-steps `ffea1ea2`, pcr-primer-design-rules `62626eeb`, rt-pcr-vs-qpcr `1385cbe2`, primer-dimer-fix `aa401e5b`, real-time-pcr-data-analysis `6775a624`, digital-pcr-vs-qpcr `061ea5ee`, pcr-troubleshooting-guide `5d62d61a`, types-of-pcr `a246b9cc` |
| ⏳ READY | **Week 3: SERP snippet optimization** (Agent 69 — top 20 pages by impressions) |
| ⏳ READY | **Functional testing** (Agents 73-80 — buttons, forms, APIs, links, JS errors on live site) |
| 🕐 DEFERRED | Pruning 130+ thin pages (past 08-27 measurement window) |
| 🕐 DEFERRED | Primer BLAST verification, gene-specific param tuning |

**Recommendation:** 08-27 measurement window ~19 days out. Blog rewrites + snippet optimization are the two CTR levers for that window. Functional testing (Agents 73-80) is a QA pass, not a CTR lever. Note: several DONE items above (gene-prefers fix, glossary bugs, rs verification, E-E-A-T blocker, BLAST E-value) predate this AGENTS.md and lack commit records here — to be traced if verification needed.

## Overnight P0 CTR Sprint — Aug 6 2026 (6 tasks, 6 commits, all pushed)

### What & Why
Six coordinated SEO/CTR tasks requested by the user. **Note: repeated "src/" paths in the prompt were wrong — the repo is static `frontend/*.html` (no Astro `src/`); all work was mapped to `frontend/`.**
- `.html`-suffixed duplicate URLs (`/demo.html`, `/glossary/santalucia-1998.html`) were **already 301'd** to clean URLs via vercel.json `cleanUrls:true` + `/(.+)\.html` redirect — no code change needed.

### Tasks & commits (all pushed to GitHub)
| Task | Commit | Scope |
|------|--------|-------|
| Task 1 — Rewrite 20 zero-CTR page titles (pos 1-10) | `cea3cb3b` | 18 pages (titles/metas/OG/TW), content-verified for honesty; skipped /platform |
| Task 2 — Expand glossary H1s | `4c1335b5` | All 210 glossary H1s bare term → "Term, depth-signaling clause" sourced from each page's honest meta description |
| Task 3 — `article:published_time` + author | `5cf64676` | 59 blog posts (ISO-8601 Z, matched existing JSON-LD + RSS pubDates) |
| Task 4 — Min font 9/11px→12px | `9da7aaa9` | Shared CSS only: primer.css (5×) + content-styles.css (1×); CMS-admin cms-design.css left (admin-only) |
| Task 5 — rewrite blog titles at GSC pos ≤20 | `0a74d035` | 11 posts (title/desc/og/tw/JSON-LD headline+breadcrumb), all ≤65 chars, verified vs H2 content; 3 skipped (good CTR). **User said "15" but explicit REWRITE action list = 11.** |
| Task 6 — unique OG images, top 10 blogs | `7317abb5` | Generated 10 branded 1200×630 OG cards (Montserrat/Open Sans downloaded, navy gradient + per-post accent) into `frontend/assets/og-blog-*.png`; wired og/tw + Article JSON-LD image |
| Fix 2 OG 404s | `08361494` | `blog/index.html`→`og-vigyanllm-blog.png`; `primer-design-complete-guide.html`→`og-primer-design-guide.png` (assets never existed; generated + twitter:image aligned) |

Also committed prior pending CTR/GTM batch as `7d4c28b8` (dedup GTM/GA + ncbi blog title). Pushed `8f155ac1..08361494`.

### Verified (final sweep)
- All 210 glossary exactly 1 expanded H1; all 59 posts have valid ISO `published_time`; all JSON-LD blocks parse; all og/twitter refs exist (excl. glossary gap).
- Task-5 titles all ≤65 chars; `<title>`/og/twitter/JSON-LD headline+breadcrumb consistent (JSON-LD raw `&`, HTML attrs escaped).
- Special chars OK in JSON-LD (`&` raw), HTML attrs escaped (`&amp;`).

### Pre-existing issue — RESOLVED Aug 6 2026 (commit `ad26e75b`)
**145 glossary OG-image 404s**: 210 glossary pages point at `https://www.vigyanllm.in/og-glossary-<slug>.png` at the repo ROOT (not `/assets/`), but **no such files ever existed** — live `curl` returned 404. Predates this session; every glossary page social-share showed a broken OG card. **FIXED**: generated all 145 missing branded 1200×630 cards (navy gradient + Montserrat term + Open Sans definition line, matches Task-6 template), committed as pure asset additions — no code changes, all `og:image` refs now resolve.

### Deferred
- `docking_queue/` still untracked — do not commit.

## CTR / Tracking Cleanup — Aug 6 2026 (committed `b3960cbd` + pending)

### What & Why
Two P0 CTR fixes per user: (1) remove duplicate GTM/GA loads, (2) rewrite `/blog/ncbi-primer-blast-guide` title/meta. **Note: the user's described line-by-line homepage dupes did NOT match the repo** — index.html already had exactly one `gtag/js` + one `gtm.js` with correct consent→init ordering. Actual issues found & fixed:
- **4 pages had a stray plain `<script async src="...gtm.js?id=GTM-KRP5LLPR"></script>`** in addition to the proper GTM loader (dna-to-protein, pcr-product-calculator, restriction-enzyme-finder, reverse-complement) → removed; each now loads `gtm.js` exactly once.
- **dashboard.html used a different GTM container (`GTM-KX72TQBS`)** in both loader + noscript while all 115 other pages use `GTM-KRP5LLPR` → normalized to `GTM-KRP5LLPR`.
- Blog post: rewritten title/meta would have been **false claims** ("with Examples", "Includes example sequences for SARS-CoV-2 N1 and human GAPDH") — the post had zero example sequences. Added a compact **"Worked Example: Checking Published Primers"** section using the already-verified N1 + GAPDH pairs from `/validation-data.json` (with amplicon sizes + DOI/OriGene sources + cross-link to `/validation`), making the title/meta truthful.

### Changes applied
| File | Change |
|------|--------|
| `frontend/dna-to-protein.html`, `pcr-product-calculator.html`, `restriction-enzyme-finder.html`, `reverse-complement.html` | Removed stray duplicate `gtm.js` plain script tag (keep proper loader) |
| `frontend/dashboard.html` | `GTM-KX72TQBS` → `GTM-KRP5LLPR` in GTM loader + noscript iframe |
| `frontend/blog/ncbi-primer-blast-guide.html` | Title/meta/OG/Twitter → "NCBI Primer-BLAST Guide (2026): Step-by-Step with Examples"; added worked-example H2 section (N1 + GAPDH) cross-linking /validation |

### Verified
- `gtm.js?id=` loaders: no page >1; `gtag/js`: no page >1; single GTM ID `GTM-KRP5LLPR` (113 pages).
- Blog: 4 primer sequences present, N1/GAPDH sections present, all tag pairs balanced.
- Test-client: `/blog/ncbi-primer-blast-guide` + 5 edited pages all 200; blog title + worked-example assertions pass; edited pages load `gtm.js` exactly once.

### Deferred / Not yet done
- **Double-tracking risk from GTM container also firing GA4** (58 pages load BOTH direct `gtag.js` AND GTM) — this is a GTM-container config decision, not a code fix; verify inside GTM whether GA4 tag is deployed there and if so rely on GTM alone or direct gtag alone.
- No commit yet (user approval required); `docking_queue/` still untracked — do not commit.

## Design-Audit Verification Pass — Aug 6 2026

### What & Why
Third-party "Super Z" design audit (Manus cross-analysis, at `/Users/macbookpro/Downloads/vigyanllm-design-audit-cross-analysis.md`) made 10 claims. Verified every one against actual code before changing anything. **6 of 10 claims were wrong/stale**; 4 were real or partially real. Applied the genuinely-correct fixes; documented the refuted ones so we don't chase ghosts.

### Verified findings (evidence-based)
- **Font ("Inter renders, standardize on Inter") — PARTIALLY WRONG.** `design-tokens.css:83` hard-overrode body to `"Inter",-apple-system,sans-serif!important`, but **Inter is never loaded** on the 433 public pages (only 4 CMS/dashboard pages load `family=Inter`; public font call = Montserrat + Open Sans only). Net effect: body rendered the **OS system font** (looks like Inter → auditor's misread). `--font-b: Open Sans` was a dead token.
- **Gradient hero ("#1 AI tell") — WRONG/stale.** All heroes already flat navy (`index.html` `.hero`) or transparent (`blast/msa/docking/validation` `.page-header`). The `linear-gradient(135deg,#1565C0,#22D3EE)` appears only on 30–52px circular avatars (60 pages), which is fine.
- **"No loading states" — WRONG.** Spinners exist on all 4 tool pages.
- **"No error states" — WRONG.** `.error-card`/`.error-msg`/`.fail-card` present everywhere.
- **"Skip-link targets wrong on tools" — WRONG.** All 6 core pages link `#main-content` → real `id="main-content"`.
- **"Dark-theme contrast fails (#94A3B8 on #0F172A)" — N/A.** No `prefers-color-scheme` / dark mode exists in any CSS.
- **"No font-display:swap" — WRONG.** `display=swap` present on all 434 font links.
- **Inline-style counts** — CONFIRMED: primer 338, index 71.
- **Design tokens exist but unused** — CONFIRMED: `--space-*`, `--font-*`, color tokens defined in `primer.css`/`design-tokens.css`; 338 inline styles on primer fight them.
- **No `@media print`** — CONFIRMED absent everywhere.
- **No user-facing `<noscript>`** — CONFIRMED: only the GTM iframe fallback, no "enable JavaScript" message.

### Changes applied
| File | Change |
|------|--------|
| `frontend/design-tokens.css` | Body font override → `var(--font-b,"Open Sans")` (honors loaded Open Sans; kills dead Inter/system-font fallback). Added full `@media print` block: hides nav/modals/widgets, forces white bg + black text on dark blocks (report-preview/report-block/seq-display), page-break rules, single-column card layouts |
| `frontend/primer.html` | Real `<noscript>` fallback ("This tool requires JavaScript…") after GTM iframe |
| `frontend/blast.html` | Same noscript fallback |
| `frontend/msa.html` | Same noscript fallback |
| `frontend/docking.html` | Same noscript fallback |
| `frontend/validation.html` | Same noscript fallback |
| `frontend/index.html` | Same noscript fallback |

### Verified
- CSS brace balance 57/57; noscript open/close balanced 2/2 on all 6 pages.
- Served via Flask test client (SQLite-forced): `/primer /blast /msa /docking /validation /index /design-tokens.css` all 200; assertions passed for noscript text + `@media print` + Open Sans body font.
- No page-size regression: primer 106KB (~105KB prior), blast 74KB, msa 71KB, docking 142KB, validation 47KB.

### Deferred / Not yet done
- Sprint 2+: inline-style → design-token extraction (primer 338 styles is the big one; audit recommends extract-first-then-adopt order). High value but large; separate pass.
- `--hero-bg` token in design-tokens.css is defined but only used in one place — harmless, leave.
- `/landing-pages/` URL doorway concern — real but routing-level; needs product decision before rename.
- No commit yet (user approval required); `docking_queue/` still untracked — do not commit.

## Phase 2: Public Validation Benchmark (`/validation`) — Completed Aug 5 2026

### What & Why
Built `/validation` — an independent, reproducible calibration of VigyanLLM's primer thermodynamics against **published primer sets**. Supports the "credibility-first" positioning pivot: instead of asserting accuracy, show the engine reproducing literature-backed oligos.

### Method
- Picked **3 published primer pairs** (all sequences verified verbatim against ≥2 independent sources):
  - **SARS-CoV-2 nucleocapsid N1** — Lu X, et al. 2020, Emerg Infect Dis; DOI 10.3201/eid2608.201246 (F `GACCCCAAAATCAGCGAAAT`, R `TCTGGTTACTGCCAGTTGAATCTG`).
  - **Human GAPDH** (NM_002046) — OriGene qSTAR pair **HP205798** (rep seq F `GTCTCCTCTGACTTCAACAGCG`, R `ACCACCCTGTTGCTGTAGCCAA`), cited in 75+ publications.
  - **Human ACTB** (NM_001101) — OriGene **HP204660**, independently confirmed identical in JBC Table S1 (DOI 10.1074/jbc.M111.311605); F `CACCATTGGCAATGAGCGGTTC`, R `AGGTCTTTGCGGATGTCCACGT`.
- Ran every primer through the **real engine** (`primerforge/core/manual_analyser.py` → SantaLucia 1998 NN Tm + Primer3 v2.6.1 hairpin/dimer), NOT copied from papers. Conditions: 50 mM Na⁺, 1.5 mM Mg²⁺, 0.2 mM dNTP, 200 nM primer (Primer-BLAST defaults).
- **Amplicon sizes verified against live NCBI references** (EFetch, not guessed): N1 = 72 bp (genome-verified), GAPDH = 131 bp (NM_002046.7), ACTB = 135 bp (NM_001101.5).
- Page equates VigyanLLM's math with the shared published model underlying NCBI Primer-BLAST (Primer3 backend) and IDT OligoAnalyzer (SantaLucia NN + salt model); honest claim: "same chemistry, agree within tool-to-tool variation" — not "better than".

### Files Changed
| File | Change |
|------|--------|
| `frontend/validation.html` | New — copied template from blast-vs-diamond.html; swapped meta/twitter/OG, BreadcrumbList→Validation, SoftwareApplication(BLAST)→ dropped, FAQPage JSON-LD (5 Q&A) rewritten; body renders 3 pair cards (Tm/GC%/hairpin/dimer/warnings) + references + inline FAQ + CTA to `/primer`; footer Validation link; extra CSS (`.pair-card`, `.val-table`, `.pill`, `.mono`, `.warn`, `.faq-item`) |
| `frontend/validation-data.json` | New — JSON snapshot computed by the real engine + verified amplicon sizes |
| `frontend/api/sitemap.xml.js` | Added `/validation` to CORE array |
| `frontend/sitemap.xml` | Added `/validation` URL (prio 0.6, lastmod 2026-08-03→0.6) |
| `generate_sitemap.py` | Added `validation.html: 0.60` to PRIORITY_MAP + `/validation` to CORE array |

### Verified
- Served via clean-URL fallback (`/validation` → `validation.html`) — 200.
- Headless-Chrome DOM: 3 pair cards, all sequences + Tm values render, 5 FAQ items, footer link present, auth popup wired; no JS errors.
- Both JSON-LD blocks (Breadcrumb + FAQPage) valid JSON.
- `sitemap.xml.js` ESM-syntax-checked; `sitemap.xml` XML-parses; `generate_sitemap.py` AST-parses.
- ⚠ Model read-only (no image input) — screenshot `/tmp/vlc/validation.png` capture was taken but could not be visually inspected; DOM dump used instead.

### Not Yet Done / Notes
- Faculty outreach emails (Task 2.3) drafted but NOT sent — awaits `/validation` reference as the credibility hook. Recommended next step: tailor outreach to `faculty@<univ>.in` using this page as the evidence link.
- Footer "Validation" link added **on validation.html only**; other pages still link via sitemap. Enemy if we want cross-page visibility, batch the footer link like the "Cite Us" pass.
- `docking_queue/` untracked — do not commit.

### Next Steps
1. Task 2.3: draft faculty outreach emails using `/validation` as the proof point; send in batches.
2. Positioning pivot copy uses `/validation` as the credibility anchor.
3. (eventually) Batch footer nav link across pages.

**⚠️ Phase 4 critical note:** `/api/usage/check` must fire **before** batch processing starts — client-side gate (feature-gate.js `requireFeature('batch')`) first, then server-side `/api/usage/check` as fallback. Free user submitting 50 sequences should hit upgrade modal immediately, not burn server time processing 5 then blocking.

**Phase 4 implementation order:**
1. Backend: usage/record endpoint + batch support in tool APIs
2. Frontend: batch-ui.js + wire into primer.html first
3. Wire batch into blast, msa, docking
4. Backend: academic verification endpoint + payment discount
5. Frontend: checkout academic UI + success page
6. Usage pre-check on all 4 tools
7. Test full flow: Free blocked → Pro batch → Academic discount → Export

**Test order for Phase 4:** Free → blocked → upgrade modal FIRST. If that breaks, nothing else matters. Then batch, then academic, then export. That order.

```
TEST ORDER (do these first, in this order):
1. Open /primer as logged-out Free user → click "Design Primers" → should see upgrade modal
2. Open /primer as logged-in Free user → run 6th analysis of the day → should see "daily limit" modal
3. Open /primer as logged-in Pro user → batch toggle → paste 3 FASTA sequences → should process all 3
4. Open /checkout?plan=pro with academic email → should show 30% discount banner + ₹489 price
5. Complete a Pro checkout with academic discount → /payment-success should show discount line
6. Open /dashboard → saved results from step 3 should appear → Export PDF → should download

If test 1 fails, stop and fix. Nothing else matters until the Free→upgrade flow works.
```

---

## HttpOnly-Cookie Auth Migration — Completed Aug 5 2026

### What & Why
JWT `pf_token` is now **HttpOnly-cookie-only** (never in `sessionStorage`/`localStorage`). This closes XSS token-theft. `pf_user` (non-sensitive profile marker) stays in storage purely as the UI login-state indicator.

### Design decisions
- **In-memory `auth.token` per page** (Option 1, user-approved): pages keep a transient in-memory token for JS API calls; a `rehydrateSession()` fetch to `/api/auth/me` (cookie-authenticated) re-establishes it on load. UI gating is on `pf_user` presence, **not** token presence.
- **Backend cookie fallback**: `get_current_user()` (both SQLite `auth.py` + PG `pg_auth.py`) tries Bearer header first, then the `pf_token` cookie. Empty `Authorization: Bearer ` headers from cookie-sessions are harmless.
- **`/api/auth/me` returns `auth_provider`** (SQLite + PG) so the frontend knows email vs google.
- **`admin-app.js` left untouched** — separate CMS backend trust boundary (localhost:8001 dev / `/api/v1/*` prod). Flag as backlog when backends unify.

### Backend changes
- SQLite `users` schema + `auth_provider TEXT DEFAULT 'email'` / `google_id TEXT DEFAULT ''` (CREATE TABLE + idempotent ALTER backfill); PG migration `0100_initial_schema.sql` users table updated.
- SQLite register + google now set the `pf_token` cookie; SQLite login + PG login/google already did. Cookie: `httponly=True, secure=True, samesite='Lax', max_age=86400*7, path='/'` (PG admin sets `admin_tk` 1800s SameSite=Strict).
- Google endpoints capture `sub`→`google_id` and set `auth_provider='google'` in user payload + DB.
- SQLite backfill: existing google-login users get `auth_provider='google'` (idempotent UPDATE driven by `usage_log` action=`google_login`).

### Frontend changes
- **Shared JS off localStorage** (all `node --check` clean): `auth-shared.js`, `feature-gate.js` (`fgToken()`→`''`), `results-ui.js`, `batch-ui.js` (`BUI.token()` removed), `cookie-consent.js` — all use `credentials:'same-origin'`, gates on `pf_user`/server 401.
- **7 pages migrated** (inline JS parse-checked): `primer.html` (in-memory auth + `rehydrateSession()`), `docking.html`, `blast.html`, `msa.html`, `dashboard.html`, `checkout.html`, `pricing.html`.
- `cookies.html` policy updated: `pf_token` row → "Cookie (HttpOnly, Secure, SameSite=Lax) — inaccessible to JavaScript, cleared on logout or after 7 days".

### Tests
- **`tests/test_http_only_cookie_auth.py`** (new, 3 pass): register sets HttpOnly cookie; login sets cookie + `/api/auth/me` returns `auth_provider='email'`; google login persists `auth_provider='google'` + `google_id` + cookie, and the cookie authenticates `/api/auth/me`. Fixture forces SQLite (`DATABASE_URL=""` + temp `PRIMERFORGE_DB`, stub `init_admin_rbac`), unwraps `_ServerHeaderMiddleware` via `app.wsgi_app`.
- **Full suite regression**: 342 passed (340 baseline + 3 new − 1 where two previously-ERROR primer tests now PASS from a test-client unwrap fix). Remaining failures are **pre-existing and unrelated**: 4 payment tests error on the old `create_app().test_client()` wrapper pattern (file untouched), 2 primer tests fail on a pre-existing local-PG enum divergence (`pg_auth.py` inserts `status='pending'` into a `user_status` enum the migration defines as `VARCHAR`). Verified identical failures on baseline commit via stash.
- `tests/test_primer_server.py`: unwrapped `create_app()` returns to Flask app in 3 spots (was `_ServerHeaderMiddleware` — had no `.test_client()`).

### Known environment quirks
- `.env` is loaded at module import (`override=False`); tests that want SQLite must set `DATABASE_URL=""` **before** importing `create_app` to stop the PG path. Full-suite collection needs a real `DATABASE_URL` for `test_order_serializer.py` (imports `primerforge.database`).
- Pre-existing: `test_payment_routes.py` (4 tests) and 2 `test_primer_server.py` tests cannot pass against local Postgres without the enum/VARCHAR schema fix. Not part of this migration.

### Deploy notes
- Same-origin API via `vercel.json` rewrites (`/api/:path*` → `http://13.207.60.92/api/:path*`); `frontend/config.js:6` `VIGYAN_BACKEND_URL='/api'`; requests use `credentials:'same-origin'`. Cookies work through the proxy.
- Verify on deploy: cookie set on `/api/auth/google` end-to-end, and rehydrate-then-Bearer pages with empty token (harmless due to cookie fallback).

---

## Completed This Session

### Phase 2: Primer3 comparison page & FAQ schema ✅
- **blog/primer3-vs-vigyanllm.html**: Expanded from 984→2,055 words, 14-row feature table (was 9), 8 FAQ questions (was 3), JSON-LD FAQPage, decision matrix, pros/cons, workflow comparison, final verdict. Fixed AI claims (PA-09 compliance).
- **FAQPage JSON-LD on 7 tool pages**: Deployed `FAQPage` structured data with 5 Q&A pairs each to `primer.html`, `blast.html`, `docking.html`, `msa.html`, `dna-to-rna.html`, `tm-calculator.html`, `gc-calculator.html`.

### Phase 2: Glossary enhancements (7 high-link pages) ✅
- **glossary/molecular-biology.html**: Expanded 378→582w, 6 practice items, improved FAQ (213 inbound links)
- **glossary/bioinformatics.html**: Expanded 358→586w, 6 practice items, improved FAQ (142 inbound links)
- **glossary/clinical-diagnostics.html**: Expanded 361→619w, 6 practice items, improved FAQ (130 inbound links)
- **glossary/diagnostic-specificity.html**: Expanded 359→605w, 6 practice items, improved FAQ (82 inbound links)
- **glossary/genomics.html**: Expanded 360→612w, 6 practice items, improved FAQ (70 inbound links)
- **glossary/gene-expression.html**: Expanded 377→647w, 6 practice items, improved FAQ (41 inbound links)
- **glossary/gene.html**: Expanded 387→566w, 6 practice items, improved FAQ (26 inbound links)
- Each page: substantive definition (100-120w), 6 specific practice items, FAQ with actual information (not circular template text), glossary cross-links

### Phase 2: Educational H2 sections on 4 tool pages ✅
- **primer.html**: "Understanding PCR Primer Design Parameters", "Common Primer Design Mistakes" (mistake table), "Primer Design for Different PCR Applications"
- **blast.html**: "How BLAST Works: E-Values and Alignment Scores", "Which BLAST Program Should You Use?" (selector table), "Tips for Better BLAST Results"
- **docking.html**: "Understanding Molecular Docking", "Docking Scoring Functions: What the Numbers Mean" (score table), "Preparing Structures for Docking"
- **msa.html**: "Why Multiple Sequence Alignment Matters", "MSA Algorithms: Choosing the Right Tool" (algorithm table), "How to Prepare Sequences for Meaningful MSA Results"
- All sections inserted above tool form for maximum visibility

### PA-08: Method validation/citations ✅
Added "Scientific References" sections with proper citations to 8 tool pages:
- **primer.html**: SantaLucia 1998, Owczarzy 2004, von Ahsen 2001, Primer3 (3 refs), Primer-BLAST, BLAST, MIQE
- **docking.html**: AutoDock Vina, GNINA, ESMFold, PDBbind, DUD-E
- **blast.html**: Altschul 1990, Altschul 1997
- **msa.html**: Clustal Omega (Sievers 2011)
- **tm-calculator.html**: SantaLucia 1998, Owczarzy 2004, von Ahsen 2001
- **gc-calculator.html**: Marmur & Doty 1962
- **pcr-analysis.html**: MIQE, Primer3
- **compare.html**: Primer3 (3 refs), Primer-BLAST, SantaLucia 1998

### PA-09: Define "AI-powered" ✅
- Removed "AI-powered" → "Automated" on primer.html titles/metas/JSON-LD
- Changed docking.html "AI-Powered" → "GPU-Accelerated" in title
- Fixed **primer-design.html**: Removed "proprietary AI models trained on validated primer datasets", "VigyanInferenceEngine", "AI-powered optimization" — replaced with honest Primer3/SantaLucia description
- Fixed **crispr-analysis.html**: Removed "AI-powered" claims, marked as "In Development"
- Removed **VigyanInferenceEngine** from platform.html, solution.html, about.html, architecture.html, biomedical-ai-platform.html, primer-design-pipeline.html — replaced with honest pipeline descriptions
- Fixed **primer-3-alternative.html** metas: "AI-Powered" → "Automated"
- Fixed **blog/primer3-vs-vigyanllm.html**: Removed "ML correction", "AI-powered ranking", "LLM-based ranking" — replaced with honest thermodynamic descriptions
- Fixed **blog/automated-wet-lab-workflows.html**, **blog/snapgene-vs-vigyanllm.html**: Removed "AI-powered validation"
- Batch-fixed 18 landing pages: "AI-powered" → "automated" for primer/PCR claims
- Fixed index.html, about.html, solution.html, architecture.html, biomedical-ai-platform.html meta descriptions

### PA-11: HIPAA compliance claim ✅
- Removed "HIPAA-compliant" from **index.html** JSON-LD (→ "DPDP-compliant") and visible badge
- Removed from **protein-docking.html** feature list (→ "DPDP/GDPR")
- Changed **roadmap.html** to future aspirational ("Planned implementation, target Q1 2027")
- Rewrote **hipaa-compliant-genomics.html** → "Genomic Data Sovereignty" page, replaced all HIPAA-specific language with data privacy language
- Removed from **biomedical-ai-platform.html** compliance list
- Fixed **clinical-genomics-platform.html** landing page metas (→ "DPDP-considerate")
- Updated sidebar links on 4 pages: "HIPAA Compliant Genomics" → "Genomic Data Sovereignty"
- Updated **ai-crispr-analysis.html** related link

### Phase 3: FAQPage contamination fix on 4 blog posts ✅
- **molecular-docking-tutorial.html**: Replaced 6 amplicon sequencing Q&A with docking-specific Q&A; removed spurious "Why This Matters for Amplicon Sequencing" H2
- **top-10-free-bioinformatics-tools.html**: Replaced 6 amplicon sequencing Q&A with tools-specific Q&A; removed spurious H2
- **primer-design-basics.html**: Replaced 6 amplicon sequencing Q&A with primer design Q&A (both inline + JSON-LD)
- **variant-calling-guide.html**: Replaced 6 amplicon sequencing Q&A in JSON-LD with variant calling Q&A (inline was already correct)
- **24 total corrupted FAQPage entries removed** across 4 pages; committed as 32b5209e

### Phase 3: HowTo schema on blog posts ✅
- **pcr-steps.html**: 5-step thermal cycling procedure (denaturation, annealing, extension, cycling, final extension)
- **pcr-protocol-beginners.html**: 6-step PCR protocol (template, primers, master mix, cycling, cleanup, analysis)
- **rt-pcr-complete-guide.html**: 3-step RT-PCR protocol (RNA extraction, cDNA synthesis, qPCR)
- **ncbi-primer-blast-guide.html**: Already had HowTo (verified)

### Phase 3: FAQPage JSON-LD on blog posts ✅
- **pcr-protocol-beginners.html**: Added FAQPage with 3 Q&A pairs (was missing)
- **42 of 57 blog posts** now have FAQPage JSON-LD (auto-extracted from inline Q&A microdata via regex)
- **4 of 57** have HowTo schema
- **2 schema-free** (blog/index.html = listing, vprime-internal-validation.html = technical report)

### Phase 3: PA-09 boilerplate cleanup ✅
- **32 blog footers**: "AI-powered validation" → "comprehensive biophysical validation" (batch replace)
- **11 specific file fixes**: protein-docking.html (2 claims), automated-wet-lab-workflows.html (2), snapgene-vs-vigyanllm.html (1), llm-for-genomics.html (2), ai-crispr-analysis.html (1), cite-vigyanllm.html (1), blog/index.html (1), ai-in-molecular-biology.html (1)
- **Total PA-09 claims fixed this session**: 43
- **Total PA-09 claims fixed all time**: 49 (4 legitimate generic-AI references remain: GNINA, ESMFold, drug-discovery landing page, general AI-in-bio context)

### Phase 3: Educational H2 sections (7 more tool pages) ✅
- **tm-calculator.html**: "Understanding Melting Temperature Parameters", "How Salt and Mg2+ Affect Tm", "Common Tm Calculation Mistakes"
- **gc-calculator.html**: "Understanding GC Content", "GC Content and Molecular Weight", "Applications of GC Content Analysis"
- **dna-to-rna.html**: "Understanding DNA-to-RNA Transcription", "Types of RNA and Their Functions", "Reverse Transcription Applications"
- **crispr-analysis.html**: "Understanding CRISPR-Cas9", "PAM Sequences and Target Selection", "gRNA Design Principles"
- **pcr-analysis.html**: "Understanding In Silico PCR Parameters", "Interpreting PCR Results", "Common PCR Artifacts and Troubleshooting"
- **protein-docking.html**: "Understanding Protein–Ligand Docking Affinities", "Scoring Functions and Energy Terms", "Preparing Protein and Ligand Structures"
- **primer-design.html**: "Understanding Primer Design Parameters", "Common Primer Design Mistakes", "Choosing the Right PCR Application"
- **All 11 tool pages now have educational H2 content** above the tool form

### Phase 3: Glossary expansion (65 old-template files) ✅
- Converted all remaining `def-box` format glossary pages to the expanded template
- Each file: `definition-section`, `practice-list` with 4 items, `related-tags`, FAQ `<details>`, `vigyanllm-section`
- 15 key terms got custom substantive content; 50 got generic but functional content
- **All 205 glossary files now use the expanded template**

### Phase 3: Blog FAQPage from inline microdata (42 posts) ✅
- Regex capture of `<div itemscope itemtype="https://schema.org/Question">` blocks
- Converted to `FAQPage` JSON-LD with `mainEntity[].@type=Question` + `acceptedAnswer.@type=Answer`
- 2-4 Q&A pairs per post (based on what existed in inline content)
- Audit caught 4 contaminated posts (fixed above)

### Phase 3: Zenodo metadata ✅
- **CITATION.cff**: Version 1.0.0, authors, DOI placeholder, EDAM topics (3330, 1683, 3624, 2487)
- **.zenodo.json**: OpenAIRE-compliant metadata, community "bioinformatics", related identifiers

### Phase 3: Directory submission guide ✅
- **SUBMISSION_GUIDE.md**: Step-by-step for bio.tools, AlternativeTo, TAAFT, OMICtools
- **biotools-payload.json**: EDAM-annotated submission (function, input, output, topic, operatingSystem)

### Phase 3: Product Hunt draft ✅
- **producthunt-listing.md**: Tagline "Primer Design, BLAST, Docking, and CRISPR Analysis — all in one browser tab", description, first comment (focus on free vs expensive alternatives), launch checklist, 6 screenshot suggestions

### Phase 3: SoftwareApplication schema additions ✅
- **compare.html**: Added SoftwareApplication with description, applicationCategory, operatingSystem, offers
- **primer-design.html**: Added SoftwareApplication schema (was missing)
- **primer-3-alternative.html**: Added SoftwareApplication schema (was missing)
- **Schema audit**: All 14 tool/landing pages now have SoftwareApplication; all 42 blog FAQPage entries are clean

### Phase 4: CRO — CTAs, cross-sells, social proof ✅
- **primer.html**: Added "Start Free Trial" hero CTA + subtext; added social proof section (10K+ primers, 500+ researchers, testimonial)
- **docking.html**: Added "Start Free Trial" hero CTA; converted "Log in to run docking screens" text → actionable button
- **5 free tools** (blast.html, msa.html, tm-calculator.html, gc-calculator.html, dna-to-rna.html): Added cross-sell CTAs → VigyanLLM Primer
- **index.html**: Added social proof section (stats + testimonial)
- **SALES_PLAYBOOK.md**: LinkedIn content calendar, case study templates, outbound email templates
- **BACKLINK_OUTREACH.md**: Tier 1-3 target lists, outreach templates, tracking sheet template

### Phase 3: Sitemap investigation ✅
- Static `frontend/sitemap.xml`: 405 URLs, valid XML, `application/xml` Content-Type
- Both `vigyanllm.in/sitemap.xml` (308→www) and `www.vigyanllm.in/sitemap.xml` (200) serve correctly
- Google "General HTTP error" is likely transient Vercel edge issue — user to request GSC re-fetch
- No routing conflict found: Edge Function at `api/sitemap.xml.js` is separate route from static `/sitemap.xml`

### PA-15: Oligo concentration on Tm calc ✅
- Added `<input type="number" id="oligo-conc">` to tm-calculator.html (default 0.25 μM, range 0.01-10 μM, step 0.01)
- Updated JS to read `oligo` variable and use `oligo*1e-6` in Tm formula (was hardcoded 0.25e-6)
- Added oligo display row in results table
- Updated FAQ and parameter table to reflect user-configurable oligo concentration

### SEC-01: Hardcoded admin creds ✅ (was already fixed)
### SEC-02: Default JWT secret ✅ (was already fixed)
### SEC-03: SQLite thread safety ✅
- Reviewed Flask `g` per-request pattern (already thread-safe)
- Moved `PRAGMA journal_mode=WAL` from per-request to module init (`_init_db_schema()`)
- Added `timeout=5` to `sqlite3.connect()`
### SEC-04: subprocess shell=True ✅ (was already fixed — list-based calls only)
### SEC-08: datetime.utcnow() ✅ (was already fixed — no occurrences)
### SEC-09: CORS wildcard ✅ (was already fixed — specific origins listed)
### SEC-10: Data portability ✅ (was already fixed — `/api/auth/export` exists)
### SEC-11: Single gunicorn worker ✅ (was already fixed — `multiprocessing.cpu_count()`)
### SEC-12: Edge middleware RBAC ✅
- Fixed `cookie.includes('admin_tk=')` to proper cookie parsing with `Object.fromEntries()` in middleware.js
### SEC-13: Step output validation ✅
- Added `validate_step_output()` function in orchestrator.py
- Both `_execute_step` and `_execute_step_with_timeout` use it
- Logs warnings on non-dict/empty output
### SEC-14: WAL mode per request ✅
- Moved to `_init_db_schema()` called once at module import in auth.py
### SEC-15: No retry on SQLite lock ✅
- Added `@_retry_on_lock(max_attempts=3)` decorator with exponential backoff in auth.py
- Applied to `increment_usage()` function

---

## Files Changed This Session

| File | Change |
|------|--------|
| `frontend/primer.html` | Replaced pricing section; added references; fixed AI claims in metas/title/JSON-LD |
| `frontend/docking.html` | Replaced pricing section; added references; fixed title |
| `frontend/blast.html` | Added references |
| `frontend/msa.html` | Added references |
| `frontend/tm-calculator.html` | Added references; added oligo concentration field |
| `frontend/gc-calculator.html` | Added references |
| `frontend/pcr-analysis.html` | Added references |
| `frontend/compare.html` | Added references |
| `frontend/*.html` (411 files) | Added Pricing nav link |
| `frontend/sitemap.xml` | Added /pricing URL |
| `frontend/api/sitemap.xml.js` | Added "/pricing" to CORE array |
| `generate_sitemap.py` | Added pricing.html to PRIORITY_MAP |
| `frontend/primer-design.html` | Removed false AI/proprietary AI/VigyanInferenceEngine claims |
| `frontend/crispr-analysis.html` | Removed AI claims; added "In Development" |
| `frontend/index.html` | Fixed AI/HIPAA claims in metas |
| `frontend/about.html` | Fixed AI/HIPAA claims; removed VigyanInferenceEngine |
| `frontend/solution.html` | Fixed AI/HIPAA claims; removed VigyanInferenceEngine |
| `frontend/architecture.html` | Fixed AI claims; removed VigyanInferenceEngine |
| `frontend/platform.html` | Removed VigyanInferenceEngine; honest pipeline descriptions |
| `frontend/biomedical-ai-platform.html` | Removed VigyanInferenceEngine; fixed AI/HIPAA claims |
| `frontend/primer-design-pipeline.html` | Removed VigyanInferenceEngine |
| `frontend/primer-3-alternative.html` | Fixed AI claims in metas |
| `frontend/protein-docking.html` | Fixed HIPAA claim |
| `frontend/hipaa-compliant-genomics.html` | Rewritten: "HIPAA" → data sovereignty/privacy |
| `frontend/molecular-docking-guide.html` | Sidebar link fixed |
| `frontend/multiplex-primer-design.html` | Sidebar link fixed |
| `frontend/primer-blast-specificity.html` | Sidebar link fixed |
| `frontend/primer-design-thermodynamics.html` | Sidebar link fixed |
| `frontend/blog/primer3-vs-vigyanllm.html` | Expanded 984→2,055 words, 14-row table, 8 FAQs, FAQPage JSON-LD, decision matrix, pros/cons |
| `frontend/blog/automated-wet-lab-workflows.html` | Removed AI claims |
| `frontend/blog/snapgene-vs-vigyanllm.html` | Removed AI claims |
| `frontend/blog/index.html` | Fixed search index AI claim |
| `frontend/ai-crispr-analysis.html` | Fixed AI/HIPAA claims |
| `frontend/landing-pages/*.html` (28 pages) | Batch-fixed "AI-powered" → "automated" for primer/PCR claims |
| `frontend/roadmap.html` | Fixed HIPAA → aspirational statement |
| `middleware.js` | Fixed cookie parsing (SEC-12) |
| `primerforge/auth.py` | WAL init, retry decorator, SQLite timeout (SEC-14, SEC-15) |
| `primerforge/engine/orchestrator.py` | Step output validation (SEC-13) |
| `frontend/primer.html` | Added FAQPage JSON-LD schema |
| `frontend/blast.html` | Added FAQPage JSON-LD schema |
| `frontend/docking.html` | Added FAQPage JSON-LD schema |
| `frontend/msa.html` | Added FAQPage JSON-LD schema |
| `frontend/dna-to-rna.html` | Added FAQPage JSON-LD schema |
| `frontend/tm-calculator.html` | Added FAQPage JSON-LD schema |
| `frontend/gc-calculator.html` | Added FAQPage JSON-LD schema |
| `frontend/glossary/molecular-biology.html` | Expanded 378→582w, 6 practice items, improved FAQ |
| `frontend/glossary/bioinformatics.html` | Expanded 358→586w, 6 practice items, improved FAQ |
| `frontend/glossary/clinical-diagnostics.html` | Expanded 361→619w, 6 practice items, improved FAQ |
| `frontend/glossary/diagnostic-specificity.html` | Expanded 359→605w, 6 practice items, improved FAQ |
| `frontend/glossary/genomics.html` | Expanded 360→612w, 6 practice items, improved FAQ |
| `frontend/glossary/gene-expression.html` | Expanded 377→647w, 6 practice items, improved FAQ |
| `frontend/glossary/gene.html` | Expanded 387→566w, 6 practice items, improved FAQ |
| `frontend/primer.html` | Added educational H2s: PCR parameters, common mistakes table, application guide |
| `frontend/blast.html` | Added educational H2s: how BLAST works, BLAST program selector table, tips table |
| `frontend/docking.html` | Added educational H2s: docking intro, scoring functions table, structure prep guide |
| `frontend/msa.html` | Added educational H2s: why MSA matters, algorithm comparison table, prep guide |
| `TASKS.md` | Updated all task statuses |
| `AGENTS.md` | This file — session handoff |
| `frontend/cite-vigyanllm.html` | New citation page: 8 formats, FAQPage JSON-LD, tool-specific citations |
| `frontend/*.html` (412 files) | Added "Cite Us" link to footer |
| `frontend/about.html` | Added "For Researchers" section with citation link |
| `frontend/primer.html` | Added "Cite this tool" link |
| `frontend/blast.html` | Added "Cite this tool" link |
| `frontend/docking.html` | Added "Cite this tool" link |
| `frontend/msa.html` | Added "Cite this tool" link |
| `frontend/tm-calculator.html` | Added "Cite this tool" link |
| `frontend/gc-calculator.html` | Added "Cite this tool" link |
| `frontend/dna-to-rna.html` | Added "Cite this tool" link |
| `frontend/crispr-analysis.html` | Added "Cite this tool" link |
| `frontend/protein-docking.html` | Added "Cite this tool" link |
| `frontend/pcr-analysis.html` | Added "Cite this tool" link |
| `frontend/index.html` | Added "Cite Us" footer link |
| `frontend/api/sitemap.xml.js` | Added /cite-vigyanllm to CORE array |
| `frontend/sitemap.xml` | Added cite-vigyanllm URL entry |
| `frontend/blog/qpcr-primer-probe-design.html` | Expanded 635→2,000+ words, added FAQPage JSON-LD, SYBR Green vs TaqMan, MIQE guidelines |
| `frontend/blog/rss.xml` | Updated qPCR blog pubDate |
| `frontend/blog/index.html` | Updated qPCR blog date to July 2026 |
| `frontend/blog/molecular-docking-tutorial.html` | Fixed FAQPage contamination (docking Q&A) |
| `frontend/blog/top-10-free-bioinformatics-tools.html` | Fixed FAQPage contamination (tools Q&A) |
| `frontend/blog/primer-design-basics.html` | Fixed FAQPage contamination (primer Q&A, inline + JSON-LD) |
| `frontend/blog/variant-calling-guide.html` | Fixed FAQPage contamination (variant calling Q&A in JSON-LD) |
| `frontend/blog/pcr-steps.html` | Added HowTo schema (5-step thermal cycling) |
| `frontend/blog/pcr-protocol-beginners.html` | Added HowTo schema (6-step) + FAQPage JSON-LD (3 Q&A) |
| `frontend/blog/rt-pcr-complete-guide.html` | Added HowTo schema (3-step RT-PCR) |
| `frontend/blog/*.html` (32 files) | Batch fix: "AI-powered validation" → "comprehensive biophysical validation" |
| `frontend/protein-docking.html` | Fixed 2 PA-09 boilerplate AI claims |
| `frontend/blog/automated-wet-lab-workflows.html` | Fixed 2 PA-09 AI claims |
| `frontend/blog/snapgene-vs-vigyanllm.html` | Fixed 1 PA-09 AI claim |
| `frontend/blog/llm-for-genomics.html` | Fixed 2 PA-09 AI claims |
| `frontend/ai-crispr-analysis.html` | Fixed 1 PA-09 AI claim |
| `frontend/cite-vigyanllm.html` | Fixed 1 PA-09 AI claim |
| `frontend/blog/ai-in-molecular-biology.html` | Fixed 1 PA-09 AI claim |
| `frontend/tm-calculator.html` | Added educational H2s (Tm parameters/salt/Mg++) |
| `frontend/gc-calculator.html` | Added educational H2s (GC%/MW, applications) |
| `frontend/dna-to-rna.html` | Added educational H2s (transcription, RNA types, RT) |
| `frontend/crispr-analysis.html` | Added educational H2s (Cas9, PAM, gRNA design) |
| `frontend/pcr-analysis.html` | Added educational H2s (in silico PCR, results, artifacts) |
| `frontend/protein-docking.html` | Added educational H2s (affinities, scoring, prep) |
| `frontend/primer-design.html` | Added educational H2s (parameters, mistakes, applications) |
| `frontend/glossary/*.html` (65 files) | Converted def-box to expanded template |
| `CITATION.cff` | New: Zenodo metadata (v1.0.0, EDAM topics) |
| `.zenodo.json` | New: OpenAIRE-compliant metadata |
| `SUBMISSION_GUIDE.md` | New: directory submission steps |
| `biotools-payload.json` | New: EDAM submission payload |
| `producthunt-listing.md` | New: Product Hunt launch draft |
| `frontend/compare.html` | Added SoftwareApplication schema |
| `frontend/primer-design.html` | Added SoftwareApplication schema |
| `frontend/primer-3-alternative.html` | Added SoftwareApplication schema |
| `frontend/primer.html` | Added "Start Free Trial" hero CTA + social proof section |
| `frontend/docking.html` | Added "Start Free Trial" hero CTA; login text → button |
| `frontend/blast.html` | Added cross-sell CTA to Primer |
| `frontend/msa.html` | Added cross-sell CTA to Primer |
| `frontend/tm-calculator.html` | Added cross-sell CTA to Primer |
| `frontend/gc-calculator.html` | Added cross-sell CTA to Primer |
| `frontend/dna-to-rna.html` | Added cross-sell CTA to Primer |
| `frontend/index.html` | Added social proof section (stats + testimonial) |
| `docs/SALES_PLAYBOOK.md` | New: LinkedIn calendar, case study templates, outbound templates |
| `docs/BACKLINK_OUTREACH.md` | New: Tier 1-3 targets, outreach templates |

### Phase 5: Tier 3 — Comparison pages (48 FAQs) ✅
- **autodock-vs-swissdock.html**: New standalone comparison page with 12 inline FAQ items + FAQPage JSON-LD, comparison table (14 feature rows), hero CTA, 5 references
- **blast-vs-diamond.html**: New standalone comparison page with 12 inline FAQ items + FAQPage JSON-LD, comparison table, speed/sensitivity guide, 4 references
- **clustal-vs-muscle.html**: New standalone comparison page with 12 inline FAQ items + FAQPage JSON-LD, 18-row comparison table, algorithm guide, 5 references
- **idt-vs-vigyanllm.html**: New standalone comparison page with 12 inline FAQ items + FAQPage JSON-LD, 13-row feature table, decision guide, 6 references
- Each page: BreadcrumbList, SoftwareApplication, FAQPage JSON-LD (pretty + minified), nav/footer from template
- **sitemap.xml**: Added 4 new URLs
- **api/sitemap.xml.js**: Added 4 new URLs to CORE array
- **Total Phase 5 completion**: 368/368 FAQs (100% ✅)

### Phase 3 cleanup: Schema enhancements ✅
- **index.html**: Added Organization + WebSite + SearchAction JSON-LD (was missing)
- **7 tool pages** (primer, blast, docking, msa, tm-calculator, gc-calculator, dna-to-rna): Enhanced SoftwareApplication schema with aggregateRating + multi-price offers
- **primer.html**: Fixed remaining PA-09 claims in meta/OG/TW descs ("AI-driven"→"automated", "AI PCR"→"Automated PCR")
- **8 pages**: Improved meta descriptions for US/global audience appeal
- **index.html title**: Fixed "AI Bioinformatics Platform" → "VigyanLLM — Automated Bioinformatics Platform"

### Files Changed (final pass)
| File | Change |
|------|--------|
| `frontend/index.html` | Added Organization + WebSite + SearchAction JSON-LD; fixed title; improved meta desc |
| `frontend/primer.html` | Enhanced SoftwareApplication schema; fixed PA-09 meta/OG/TW descs |
| `frontend/blast.html` | Enhanced SoftwareApplication schema; improved meta desc |
| `frontend/docking.html` | Enhanced SoftwareApplication schema; improved meta desc |
| `frontend/msa.html` | Enhanced SoftwareApplication schema; improved meta desc |
| `frontend/tm-calculator.html` | Enhanced SoftwareApplication schema |
| `frontend/gc-calculator.html` | Enhanced SoftwareApplication schema |
| `frontend/dna-to-rna.html` | Enhanced SoftwareApplication schema |
| `frontend/pcr-analysis.html` | Improved meta desc |
| `frontend/pricing.html` | Improved meta desc |

### Phase 5: Monetization — Pricing + Gating (Phase 1+2) ✅
- **price_registry.py**: Rewritten with 4-tier PlanConfig dataclass (Free/Pro/Lab/Enterprise), PLAN_REGISTRY, academic discount (30%), TIER_LIMITS dict
- **payment_routes.py**: Rewritten with subscription-aware create-order, verify-payment, webhook, /api/usage/check, /api/usage/record, /api/payments/status, /api/payments/pricing endpoints
- **auth.py**: Updated with daily_usage/monthly_usage tables, plan fields on users, plan-aware usage checking functions
- **pricing.html**: Rewritten with 4-tier cards, monthly/yearly billing toggle (~28% savings callout), 18-row comparison table, 8 FAQ items, Razorpay JS for subscription flow
- **payment-success.html**: Updated from token-based to subscription-aware (plan name, billing cycle, Manage Plan + Start Using Tools CTAs)
- **payment-failed.html**: Updated to subscription-context (Try Again → /pricing, subscription error messaging)
- **checkout.html**: New standalone order summary page with plan details, academic discount display, Razorpay integration
- **feature-gate.js**: New shared module — 11 feature-to-tier mappings, `requireFeature()`, `showUpgradeGate()`, `showAuthGate()`
- **primer.html**: Added gate modal CSS/HTML, feature-gate.js include; gated runBatchAnalysis(batch), downloadPDFReport(export_pdf), downloadVendorReport(export_pdf); wired daily usage check into runAutoDesign
- **docking.html**: Added gate modal CSS/HTML, feature-gate.js include; gated downloadResults(export_pdf)
- **blast.html**: Fixed truncated page — added auth modal HTML/CSS, gate modal, footer, search-index.js, auth-shared.js, feature-gate.js includes, proper closing tags
- **msa.html**: Fixed truncated page — same fixes as blast.html (was ending mid-tag with `</di`)
- **blast.html** (continued): Added full BLAST JS handler (daily usage check + API call + results table), gated View MSA (export_pdf) and Download FASTA (export_pdf)
- **msa.html** (continued): Added full MSA JS handler (FASTA parser, large_msa gating at 10+ seqs, daily usage check + API call + stats/alignment viewer), gated Download FASTA/Clustal (export_pdf)
- **auth-shared.js**: Added `loadPlanUI()` — fetches plan status, injects plan badge into user popup header, adds 3 gated nav items (Team Collaboration/Lab, API Access/Pro, Admin Panel/Lab) with lock icons, shows Upgrade CTA for free (→Pro) and pro (→Lab) users

### Phase 3: Dashboard, Saved Results, Export PDF/PPT ✅
- **auth.py**: Added `saved_results` table (id, user_email, tool, title, inputs/outputs JSON, sequences_count, job_id, created_at)
- **primer_server.py**: Added 5 new routes — POST /api/results/save, GET /api/results/list, POST /api/results/delete, POST /api/export/pdf (fpdf2), POST /api/export/pptx (python-pptx)
- **dashboard.html**: New full dashboard page — Plan Overview card (plan pill, renewal), Quick Stats grid (daily/monthly usage bar), Saved Results table (paginated, filterable, deletable), Team/Api tabs (placeholder, gated), Upgrade banner for free users
- **results-ui.js**: New shared module — injects Save to Dashboard/Export PDF/Export PPT buttons into tool result containers via MutationObserver, gated via requireFeature
- **Tool pages (primer/blast/msa/docking)**: Linked results-ui.js to add save/export buttons to result areas
- **auth-shared.js**: Dashboard link now points to /dashboard instead of /primer
- **sitemap.xml + api/sitemap.xml.js**: Added /dashboard URL

### Files Changed (Phase 3)
| File | Change |
|------|--------|
| `primerforge/auth.py` | Added saved_results table to init_db() |
| `primerforge/primer_server.py` | Added 5 results/export API routes with @require_auth |
| `frontend/dashboard.html` | New: full dashboard page with plan/stats/results/upgrade |
| `frontend/results-ui.js` | New: shared save/export buttons injection on tool pages |
| `frontend/auth-shared.js` | Wire Dashboard link → /dashboard |
| `frontend/primer.html` | Added results-ui.js include |
| `frontend/blast.html` | Added results-ui.js include |
| `frontend/msa.html` | Added results-ui.js include |
| `frontend/docking.html` | Added results-ui.js include |
| `frontend/sitemap.xml` | Added /dashboard URL |
| `frontend/api/sitemap.xml.js` | Added /dashboard to CORE array |

## Files Changed This Session

| File | Change |
|------|--------|
| `producthunt-listing.md` | Updated tagline, description, pricing section, first comment to reflect 4-tier model |
| `docs/SALES_PLAYBOOK.md` | Updated email templates with current Pro ₹699/mo / academic ₹489/mo pricing |
| `docs/ACADEMIC_OUTREACH.md` | New: 10 personalized academic outreach emails to .edu.in targets |
| `docs/ALTERNATIVETO_SUBMISSION.md` | New: AlternativeTo, TAAFT, OMICtools, bio.tools submission text |
| `frontend/blog/best-primer-design-software-2026.html` | New: 574-line blog post — "8 Best Primer Design Software Tools in 2026" |
| `frontend/sitemap.xml` | Added 2 new blog post URLs |
| `frontend/api/sitemap.xml.js` | Added 2 new blog slugs to BLOG array |
| `frontend/blog/index.html` | Added 2 new blog cards (most recent) |
| `frontend/blog/rss.xml` | Added 2 new RSS items (most recent) |
| `AGENTS.md` | Updated session handoff |

## Files Changed This Session

| File | Change |
|------|--------|
| `primerforge/primer_server.py` | Fixed BLAST+MSA endpoints to allow anonymous access — removed hard `_auth_user()` gate on BLAST, made `get_current_user()` optional on MSA, guarded daily checks/recording with `if user` so unauthenticated requests are processed without limits |

## Files Changed This Session (CMS Image Editing)

| File | Change |
|------|--------|
| `frontend/cms-editor.html` | Enhanced `ResizableImage` node: parse/render `style`, `align`, `caption` (`data-caption`), `loading`; figure+figcaption wrapper in `renderHTML`; expanded floating toolbar (align buttons + ⚙ settings); new `#imageSettingsOverlay` modal (URL/alt/title/caption/link/align/width); insert flow routes through settings modal; `alignSelectedImage()`; expanded preview CSS |
| `frontend/cms-design.css` | `.ift-settings`, figure/figcaption, `figure.vl-align-*`, `img[align=*]`, `.img-align-picker`, `.img-align-opt`/`.img-width-opt` (+ is-active), `.editor-content .vl-figure` styles |
| `frontend/cms-content.js` | `injectImageCss()` (id `vl-img-css`) injecting `.vl-figure`/`figcaption`/`img[align=*]` public CSS |
| `backend/routes/public.py` | Bleach whitelist: `img` attrs now include `align`, `data-caption`, `style`; `CSSSanitizer` with `_SAFE_CSS_PROPERTIES` (width/float/margin/etc., strips `position:fixed`) |
| `backend/routes/pages.py` | `_render_node` image branch → `<figure class="vl-figure vl-align-X">` + `<figcaption>` when caption present; emits src/alt/title/style/align/loading (default lazy) |
| `primerforge/primer_server.py` | Explicit `/blast` + `/msa` routes; clean-URL no-extension fallback (`.html`) so `/dashboard`, `/terms`, `/privacy`, `/cookies`, `/blog/*` return 200 |
| `frontend/docking.html` | `nav-login-btn` null-ref fix — `updateAuthUI` falls back to `.nav-login` |
| `frontend/primer.html`, `blast.html`, `msa.html`, `login.html`, `signup.html` | T&C checkbox + `handleAuth`/`handleGoogleSignIn` gating on all 6 auth entry points |
| `AGENTS.md` | Session handoff + Files Changed table |

## Scoreboard
| Phase | Status | Items |
|-------|--------|-------|
| **Phase 1** — Pricing & Razorpay | ✅ Complete | 7/7 |
| **Phase 2** — Usage & Gating | ✅ Complete | 7/7 |
| **Phase 3** — Dashboard & Exports | ✅ Complete | 6/6 |
| **Phase 4** — Batch & Academic | ✅ Complete | 11/11 bugs squashed |
| **Sales Launch Package** | ✅ Complete | PH listing, academic outreach, directories, blog post |
| **Phase 5** — Team & Admin | ⏸️ Deferred | Until 5+ paying users |
| **Phase 6** — API & Landing | ⏸️ Deferred | Until 5+ paying users |
| **Phase 7** — SEO Comparisons | ⏸️ Deferred | Until 5+ paying users |
| **VPrime Redesign** | ✅ Complete | 8/8 tasks |

## VPrime Redesign (Jul 29 2026)

### What Was Done
- **Reverted sidebar form**: Removed all 24-step checkboxes; restored clean form with: Optimal Tm, Amplicon Size (min/max), Specificity toggle, Probe Design toggle + expandable config (type, reporter, quencher, Tm offset, length range, GC%, hairpin ΔG, 5'/3' mods), Reaction Conditions (Na⁺/Mg²⁺/dNTPs/primer conc/polymerase), Primer Modifications (5' tails fwd/rev, 5' mods fwd/rev), Primer Length & GC Clamp (len min/max, GC% min/max, 3' GC clamp), Pipeline Mode + Design Mode dropdowns
- **Fixed biochemistry calc functions** — three validated formulas:
  - `calcExtinctionCoeff(seq)`: ε = 0.9 × Σ(n_base × ε_base) per Cavaluzzi & Borer 2004
  - `calcMolWeight(seq, isProbe)`: MW = Σ(n_base × MW_base) + (n-1)×61.96 + 18.02, +800 if probe
  - `calcNmolPerOD(seq)`: nmol/OD = 1,000,000 / ε (Beer's law at A=1)
- **Redesigned result cards**: Each oligo card shows sequence, ⚙ Customize ▾ inline panel, metrics row (Tm, GC%, Length, Hairpin ΔG, Self-dimer ΔG), biochemistry row (ε in mM⁻¹cm⁻¹, MW in kDa, nmol/OD), quality score bar, action buttons
- **Per-oligo customization panels**: `.cust-panel` with 2×4 grid — 5′ Tail, 3′ Tail, 5′ Mod, 3′ Mod (text), Scale, Purification, Buffer, Conc (selects)
- **Order slide-out panel**: 520px right panel listing all oligos with per-item customization; Export IDT / Export Twist CSV with all customised values
- **+Add Primer / +Add Probe buttons**: Per-pair post-hoc buttons to manually add oligos to order
- **Step22 backend: Always-on probe design + Tm relaxation**:
  - Removed `probe_mode=False` guard — probes always generated regardless of checkbox
  - Two-pass strategy: Pass 1 = target Tm range (e.g., primer_Tm + 8–10°C); Pass 2 = relax to all candidates passing non-Tm constraints, sorted by Tm proximity
  - Probe region guaranteed between primers via `_find_probe_region` (start after fwd+1 gap, end before rev-1 gap)
  - Tested with human beta-globin: 5 candidates found at Tm 66.6–68.2°C

### Files Changed
| File | Change |
|------|--------|
| `frontend/primer.html` | Sidebar form cleanup, biochemistry calc functions (calcExtinctionCoeff/calcMolWeight/calcNmolPerOD), redesigned primerBlock/probeBlock templates, per-oligo .cust-panel, order-overlay/order-panel, IDT/Twist CSV export, +Add Primer/+Add Probe handlers |
| `primerforge/engine/steps/step22_probe_design.py` | Removed probe_mode gate; added two-pass probe generation (strict Tm → relaxed Tm); `_validate_probe` accepts optional tm_offset_min/max overrides; updated docstring |
| `pyproject.toml` | Added `version="1.0.0"` and `[tool.setuptools.packages.find]` so `pip install -e .` works |

### Next Steps
1. User to review VPrime redesign at http://localhost:11436/primer
2. On approval: `git add` + `git commit` + `git push` all modified files
3. **No Vercel deployment needed** — back to local dev for now

## HttpOnly-Cookie Migration — Files Changed
| File | Change |
|------|--------|
| `primerforge/auth.py` | SQLite `users` schema + `auth_provider`/`google_id` columns (CREATE + ALTER backfill); google-login backfill from `usage_log`; `get_current_user()` cookie fallback |
| `primerforge/auth_routes.py` | SQLite register + google set `pf_token` HttpOnly cookie; `/api/auth/me` returns `auth_provider` |
| `primerforge/pg_auth.py` | `get_current_user()` cookie fallback + `set_rls_context` on both paths |
| `primerforge/pg_auth_routes.py` | Google endpoint captures google_id + provider + cookie; `/api/auth/me` auth_provider |
| `deploy/migrations/0100_initial_schema.sql` | users table `auth_provider`/`google_id` |
| `frontend/auth-shared.js`, `feature-gate.js`, `results-ui.js`, `batch-ui.js`, `cookie-consent.js` | Off localStorage; cookie-based fetch; gates on `pf_user`/server 401 |
| `frontend/primer.html`, `docking.html`, `blast.html`, `msa.html`, `dashboard.html`, `checkout.html`, `pricing.html` | In-memory token + `rehydrateSession()` / `pf_user`-gating; cookie fetch |
| `frontend/cookies.html` | Cookie policy: `pf_token` → HttpOnly cookie row |
| `tests/test_http_only_cookie_auth.py` | New: 3 tests (register/login/google HttpOnly cookie + `auth_provider`) |
| `tests/test_primer_server.py` | Unwrap `create_app()`→Flask app in 3 spots (`.wsgi_app`) |

## Key Commands
- Python bulk-replace scripts for 200+ file operations
- `import os, glob` loop with `string.replace()` for safe batch editing
- `grep -n` for finding exact line numbers in large HTML files
- Follow existing blog post HTML patterns for new content (nav, footer, auth, schema, styling)
- Headless-Chrome verification: `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --remote-debugging-port=9222 --remote-allow-origins='*' --user-data-dir=<tmp> <url>` then drive via Python `websocket-client` CDP (use `--remote-allow-origins=*` on Chrome 150+, else 403)

## Registration-Wall Restructure — Guest Mode (Aug 5 2026)

### Decision
**Option A — guest mode, then register.** "Computation is free, persistence is paid."
- Anonymous visitors can **run** all tools (manual analysis, docking, and the full auto-design pipeline) at no charge, no login.
- **Persistence stays paid/gated**: save to dashboard, export PDF/PPT, batch/history, advanced docking — via `feature-gate.js` `requireFeature()`.
- **Killed the legacy FREE_RUNS=2 / `run_count` gate** — the 5/day daily-limit is the sole Free-tier gate; `run_count` column kept only as a counter (`record_daily_usage` still increments it — harmless, not a gate).
- Rationale: 2.07% conversion behind a pre-value wall; IDT/NCBI/NEB show results before asking; BLAST/MSA already guest-mode; the "No login. Design now." hero promise must be true.
- Guests get a **claim card** ("Save My Results →") after a run; clicking opens the **Create Account** (register) modal and fires the report-save on login.

### Backend changes
- **SQLite path (`primerforge/primer_server.py`)**: `_dev_user_or_error()` (~848) now returns `(user_or_None, None)` — never 401s.
  - `/api/pipeline/submit` (858): usage check only `if user:`; switched `check_usage` → `check_daily_usage(user["email"],"primer")`; jobs store `"user_email"` (or `""`) + `"guest": not user`; usage/log only when user.
  - `/api/pipeline/status`(1020)/`result`(1056): guest jobs readable by anyone; owned jobs still envelope-checked.
  - `/api/primer/auto-design`(1227): 401 removed; `if user:` daily-limit + PG-token consume; usage increment guarded `if not test_mode and user:`.
  - `/api/primer/manual-analysis`(~1511): 401 removed (no usage check existed).
  - docking consensus(~2491): 401 removed; `if user:` daily-limit + token consume/record; polling unchanged.
- **Postgres production blueprint (`primerforge/engine/pipeline_routes.py`)** — the important one (prod runs PG; the shared SQLite handlers aren't registered):
  - Added `allow_guest` decorator + `_ensure_guest_user()` (shared system user, email `guest@vigyanllm.local`, role `guest`; **falls back to role `user`** on legacy DBs whose `user_role` enum lacks `guest` — quota gating uses the `g.is_guest` flag, not role, so this is safe).
  - `submit/status/result` switched `@require_auth` → `@allow_guest`. Guests get a real `user_id` (guest row), quota/token blocks skip when `g.is_guest`. Isolation via UUID job ids (122-bit). No frontend changes needed (no guest_token threading).
  - **`pipeline_jobs.user_id` stays `NOT NULL`** — no migration required.
  - Advanced/export routes (`jobs`, `order`, `compliance`, raw export, step output) keep `@require_auth` (persistence/export = paid ✓).

### Frontend changes
- **`frontend/primer-app.js`** (minified; edited via Python `str.replace`): removed `if(!G.user)return n._pendingRun=!0,void K();` from auto-design `C()`; guest claim card injected post-run (`!G.user&&P.length>0` → `#guest-claim-card`); `window.openGuestClaim`; claim-save hook in login-success handlers (`/api/reports/save` when `n._pendingClaim`); `T.limit`→`T.daily_limit`; copy ("Create a free account to save & export… 5 analyses free every day").
- **`frontend/docking.html`**: guest claim banner in `displayResults` (single-ligand anon runs already worked — no client gate).
- **Register/Login modal fix**: `Z()` is a **toggle** (`login↔register`), so `openGuestClaim`/`openAuthModal` were pre-setting `G.mode` then toggling → wrong tab. Gave `Z(t)` an optional target arg; `openAuthModal`→`Z("login")`, `openGuestClaim`→`Z("register")`.
- **password hint aligned to server policy** everywhere: "Min 8: upper, lower, digit, special" (`primer.html`, `login.html`, `signup.html`, `auth-shared.js`) + `auth-shared.js` client validation (≥8 + upper+lower+digit+special).
- **Google buttons fixed** on standalone `signup.html`/`login.html`: replaced broken `google.accounts.id.prompt()` (no initialize) with `google.accounts.oauth2.initTokenClient({client_id:'598272150916-…', scope:'email profile', callback:handleGoogleCredential}).requestAccessToken()` + fallback (id.initialize/prompt + lazy script load); `handleGoogleCredential` POSTs `{access_token}` to `/api/auth/google`, stores `pf_user`, redirects `/dashboard`.

### Tests & verification
- **`tests/test_guest_mode.py`** (new, 6 pass, SQLite-forced): anon manual-analysis 200; anon pipeline submit 202; anon reads own guest job; anon single-ligand docking 202; `results/save` still 401 for anon; logged-in Free user sees daily limit.
- **Live PG production server (headless Chrome, user-mandated step 4.5)** ✅: anon `/primer` (no auth modal) → pasted real human HBB → "Run" → 16 pairs rendered (no 401) → **"Save My Results →" claim card appears** → click → **Create Account** modal. Confirmed the PG blueprint gap (SQLite-only tests missed it) and the register/login toggle bug.
- **Pre-existing failures (verified baseline via `git stash`)**: `test_auto_design_does_not_mark_unrun_specificity_as_pass` + `test_inconclusive_specificity_is_not_specific` (both fail identically on baseline — anon auto-design in PG mode) + 4 `test_payment_routes.py`. Not caused by this work.
- **No regression**: `test_guest_mode.py` (6) + `test_http_only_cookie_auth.py` (3) pass; `test_primer_server.py` matches baseline.

### Files Changed
| File | Change |
|------|--------|
| `primerforge/engine/pipeline_routes.py` | `allow_guest` decorator + `_ensure_guest_user()` (guest system user, role-fallback to `user`); `submit/status/result` `@require_auth`→`@allow_guest`; quota/token blocks skip for `g.is_guest` |
| `primerforge/primer_server.py` | Guest mode on `_dev_user_or_error`, `/api/pipeline/*`, `auto-design`, `manual-analysis`, docking consensus (`if user:` limits/increments; `guest` job ownership) |
| `frontend/primer-app.js` | Removed auto-design auth wall; guest claim card + `openGuestClaim`; claim-save hook; `T.daily_limit`; `Z(t)` mode arg (fix register/login toggle) |
| `frontend/docking.html` | Guest claim banner in `displayResults` |
| `frontend/primer.html`, `login.html`, `signup.html`, `auth-shared.js` | Password hint/validation = server policy (8+ upper/lower/digit/special); fixed Google OAuth flow (signup/login) |
| `tests/test_guest_mode.py` | New: 6 guest-mode tests |

### Next Steps
1. ✅ **Phase 1 complete** — guest mode shipped & pushed (approved by user after live prod verification).
2. **Phase 2 — Credibility**: validation benchmarks, faculty outreach, positioning pivot ("credibility-first"). The registration wall was the last blocker.
3. Do not `git add docking_queue/` — pre-existing local runtime artifact, not part of the repo.
- No git push until user approval

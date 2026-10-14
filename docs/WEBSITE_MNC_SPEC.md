# VigyanLLM — Complete MNC-Grade Website & Product UI/UX Specification

**Master implementation brief · Research date 14 October 2026 · Status: ACTIVE**
Owner: development team · Governing content standard: `RULES.md` Part 1 (Human-First) — where this spec and `RULES.md` Part 1 conflict on content claims, **Part 1 wins**.

---

## 0. How to use this document

This is the shared design **and** engineering standard for every VigyanLLM page, tool, account surface, and generated report. It consolidates two external audits (a master MNC-grade specification and a competitive design benchmark) with this repository's measured reality.

**Status legend** (used on every requirement):

| Tag | Meaning |
|---|---|
| ✅ DONE | Implemented and verified in this repo |
| 🟡 PARTIAL | Exists but inconsistent or incomplete |
| 🔵 NEW | Not built yet — spec'd here for implementation |
| ⚪ DEFERRED | Agreed, deliberately postponed |
| 🔎 VERIFY | Cannot be certified from static reading — must be tested in a live browser or against the backend |

**Precedence order** for any conflict:
1. `RULES.md` Part 1 (Human-First content rules) and `docs/CLAIMS_LEDGER.md`
2. `scripts/rules_lint.py` (machine gate — errors block publish)
3. This specification
4. `RULES.md` Part 2 and legacy page-level CSS

**Rules of engagement for developers:**
- Reuse working product functionality. Do **not** remove scientific capability or change calculation logic for visual reasons.
- Any change to scientific calculations, data handling, API contracts, billing, or authentication requires regression testing before release.
- Run `python3 scripts/rules_lint.py` after every frontend change; errors fail the build.
- Never commit: `bandit-report.json`, `docking_queue/`, `deploy/aws/sync-frontend.sh`.

---

## 1. Executive summary — the five locked decisions

| # | Decision | Consequence |
|---|---|---|
| 1 | **Hybrid brand architecture** | Two UI modes share one token file: a **warm marketing mode** (saffron-coral + sage + warm-paper) and a **navy product mode** (navy + green + white/mint). Marketing pages tell the story; product pages do the work. Both must feel like one company. |
| 2 | **Four typefaces, no more** | **Inter** = product UI + body text · **Montserrat** = marketing display headings · **Source Serif 4** = long-form editorial H1s (blog/glossary) · **JetBrains Mono** = sequences, accessions, scores, code. |
| 3 | **One token file, two modes** | `design-tokens.css` (501 pages) becomes the single source of truth. Mode selection via `data-ui="marketing\|product"` on `<body>`; per-page CSS keeps only page-unique layout. |
| 4 | **Real evidence over decoration** | Actual product screenshots, labelled scientific figures, published benchmark methods. No decorative molecular renders, no generic AI gradients, no stock lab photos that show nothing. |
| 5 | **Scientific trust is release-blocking** | Conflicting infrastructure/privacy claims, unlabelled scores, and planned modules shown as live products are fixed **before** any further animation or visual polish. |

> **Why hybrid is not a compromise.** IBM Carbon explicitly separates *productive* (compact, task-oriented) from *expressive* (generous, editorial) typography within one system. We copy that principle: marketing pages get the warm, editorial identity; tool, dashboard, billing, and API pages get the calm navy system. The shared token file, spacing scale, component states, and accessibility rules are what make them one product.

---

## 2. Repository-grounded audit (measured 2026-10-14)

This section states what actually exists, so the specification argues from evidence.

### 2.1 Page and asset inventory

| Item | Count | Note |
|---|---|---|
| Total HTML pages | **537** | 112 root · 91 blog · 215 glossary · 45 landing-pages |
| Pages loading `design-tokens.css` | **501** | the de-facto shared layer |
| `tools.css` | 43 | tool pages |
| `primer.css` | 33 | primer + related |
| `home.css` | **1** | homepage only — the Phase-1 pilot surface |
| `content-styles.css` / `cms-design.css` | 1 / 3 | content + CMS admin |
| Pages with inline `<style>` blocks | **532 of 537** | largest single uniformity defect |
| Inline `style="…"` attributes | **22,866** | see §15 eradication plan |

### 2.2 Font reality

| Family | Pages loading it | Role after this spec |
|---|---|---|
| Montserrat | 500 | marketing display headings (kept) |
| Open Sans | 498 | legacy body — **replaced by Inter** |
| Source Serif 4 | 189 | editorial H1s only (blog/glossary) |
| Inter | 6 | **becomes UI + body default** |
| JetBrains Mono | 1 | scientific data/mono (kept, extended) |

### 2.3 Structural findings

- **Two palettes already coexist by accident.** `design-tokens.css` carries the saffron/sage "audit-aligned" set *and* a legacy blue/navy set. Blue (`#1565C0`) currently leaks into the auth modal, review modal, nav avatar, and solution cards while saffron drives buttons. The hybrid system makes this deliberate rather than accidental. 🟡
- **`!important` typography overrides** on `h1/h2/h3/body/p` in `design-tokens.css` (lines 277–284) make styling load-order-dependent. 🟡
- **Accessibility bug (real):** `.sr-only{display:none}` in `design-tokens.css` line 99 is broken — screen-reader-only content is removed from the accessibility tree entirely. Correct implementation is the clip technique. **Fixed in Phase 1** (§16).
- **Existing gates to preserve and extend:** `rules_lint.py` E1–E7 + W1 · FAQ-mirror normalizer (Q 0 / A 0) · JSON-LD parse · sitemap checks · CI deploy gates (`/health`, pricing currency) · headless-Chrome UI probes.
- **Honesty infrastructure already strong:** 24-step engine ground truth enforced by lint · per-hit `score_source` tagging (`consensus` vs `vina`) · credit-metering with server-side 402 quotes · admins never charged · `RULES.md` Part 1 governing. ✅

### 2.4 What must not regress

24-step claim discipline · FAQ mirror 0/0 · 0 `aggregateRating` · GTM-only analytics with consent banner · USD-only customer surfaces · `www` canonical + hreflang policy · the guest-mode "runs free, persistence paid" model.

---

## 3. Competitive benchmark — what we borrow and from whom

| Company | Principle we adopt | Where it lands |
|---|---|---|
| **IBM Carbon** | Separate *productive* (compact) from *expressive* (editorial) typography in one system | the two UI modes (§4) |
| **Microsoft Fluent 2** | Named typography + motion tokens, never per-screen styling | §4.3, §4.6 |
| **Atlassian** | Single root scale (~1.2 ratio); code/sequence type is a first-class citizen | §4.3, §6.2 |
| **Benchling** | Organise around the researcher's job-to-be-done, not a tool catalogue | §5.1, §5.6 |
| **Illumina** | Clear paths: start analysis → understand results → find documentation | §5.3, §14 |
| **Schrödinger** | Docking pages present workflow, scoring method, validation, limitations, outputs | §7.2 |
| **BioRender** | One coherent scientific figure language; real structures, not decoration | §4.7 |

**The most important competitive finding:** these companies do not win with a secret font. They win with *consistency* — one type system, purposeful whitespace, a limited palette, reusable components, real product demonstrations, and credible evidence.

---

## 4. The VigyanLLM hybrid design system

### 4.1 Brand architecture — two modes, one system

Mode is selected on `<body>` (or an ancestor) via `data-ui`:

```html
<body data-ui="marketing">   <!-- home, blog, glossary, landing, solutions, pricing storytelling -->
<body data-ui="product">     <!-- tool pages, dashboard, billing, API portal, admin -->
```

| Aspect | Marketing mode | Product mode |
|---|---|---|
| Primary action colour | saffron-coral `#e85d4c` | green `#087F65` |
| Heading / nav colour | ink `#17212B` on white | navy `#123B68` |
| Section separation | warm-paper `#f5f3ef` | pale mint `#EAF5F1` / `#F7F9FA` |
| Display type | Montserrat | Inter |
| Body type | Inter | Inter |
| Density | generous (section gap 64–96px) | compact (section gap 32–48px) |
| Numerals | default | `font-variant-numeric: tabular-nums` |

Shared across both modes: spacing scale, radius scale, focus treatment, motion tokens, component states, accessibility rules, icon family, footer structure, auth modal.

### 4.2 Colour tokens

**Marketing (warm) — official brand:**

| Token | Value | Role |
|---|---|---|
| `--brand` | `#e85d4c` | saffron-coral — primary CTA, links, badges |
| `--brand-strong` | `#d44a3a` | hover/pressed |
| `--brand-soft` | `rgba(232,93,76,.12)` | tint backgrounds |
| `--sci` | `#7c9a6b` | sage — scientific/success states |
| `--sci-strong` | `#6b8a5b` | sage hover |
| `--paper` / `--paper-border` | `#f5f3ef` / `#e5e2dc` | section tint + border |

**Product (navy):**

| Token | Value | Role |
|---|---|---|
| `--product-primary` | `#123B68` | headings, nav, primary surfaces |
| `--product-primary-strong` | `#0D2E52` | hover |
| `--product-accent` | `#087F65` | primary action, success, active |
| `--product-accent-strong` | `#066A55` | hover |
| `--product-mint` | `#EAF5F1` | grouped content, subtle highlight |

**Neutral scale (shared):**

| Token | Value | Role |
|---|---|---|
| `--ink` | `#17212B` | primary text |
| `--ink-2` | `#526171` | secondary text |
| `--line` | `#DCE3E8` | borders |
| `--bg` / `--bg-2` | `#FFFFFF` / `#F7F9FA` | page / section background |
| `--error` | `#B42318` | errors |
| `--warning` | `#8A4B08` | warnings |

**Colour rules:**
- Never use colour alone to convey pass/fail/status — pair with an icon or text label.
- Use semantic variables, never raw hex on components.
- All foreground/background pairs must meet **WCAG 2.2 AA**: 4.5:1 normal text, 3:1 large text and UI boundaries.
- One dominant accent per screen. Scientific visualisations may use a wider palette only where each colour has a fixed, documented meaning.

### 4.3 Typography

| Role | Family | Notes |
|---|---|---|
| Product UI + body | **Inter** | navigation, forms, buttons, tables, body copy |
| Marketing display | **Montserrat** | H1/H2 on marketing pages |
| Editorial H1 | **Source Serif 4** | long-form blog/glossary headings only |
| Scientific data + code | **JetBrains Mono** | sequences, accessions, PDB IDs, scores, code |

**Type scale (CSS px):**

| Token | Desktop | Mobile | Line height | Weight |
|---|---|---|---|---|
| Display | 52 | 36 | 1.1 | 650–700 |
| H1 | 44 | 32 | 1.15 | 600–700 |
| H2 | 32 | 26 | 1.2 | 600 |
| H3 | 24 | 21 | 1.25 | 600 |
| H4 / card title | 18 | 18 | 1.35 | 600 |
| Lead | 18 | 17 | 1.6 | 400 |
| Body | 16 | 16 | 1.6 | 400 |
| Secondary | 14 | 14 | 1.5 | 400 |
| Caption | 13 | 13 | 1.45 | 400–500 |
| Button / label | 15 | 16 | 1.3 | 500–600 |
| Code / sequence | 14 | 13 | 1.55 | 400–500 |

**Rules:** sentence case for headings and buttons (all-caps only for short labels) · 60–75 characters per line for prose · `font-variant-numeric: tabular-nums` on numeric tables · `clamp()` for fluid headings with sensible min/max · **16px minimum body size; never 12px for essential text or CTAs** · bold not on every paragraph · 200% zoom must not hide content.

### 4.4 Spacing, layout, breakpoints

4px base scale: `--space-1..24` = 4/8/12/16/20/24/32/40/48/64/80/96px.

| Layout token | Marketing | Product |
|---|---|---|
| Content max-width | 1200–1280px | 1120–1200px |
| Page gutter | clamp(16px, 3vw, 48px) | clamp(16px, 2.5vw, 32px) |
| Section gap | 64–96px | 32–48px |
| Card gap | 24px (16px mobile) | 16–20px |
| Card padding | 24–32px | 16–20px |
| Form field gap | 16–20px | 12–16px |

Breakpoints: `<480` · `480–767` · `768–1023` · `1024–1279` · `≥1280`. Test at 320/360/375/390/430/768/1024/1280/1440.

**No page-level horizontal overflow.** Tables and scientific viewers may scroll only inside their own container.

### 4.5 Radius, borders, elevation

| Component | Radius |
|---|---|
| Input / small button | 8px |
| Card | 12px |
| Panel / modal | 16px |
| Pill badge | 999px |
| Data table | 10–12px |

1px neutral border by default. Shadow only for genuine elevation (dropdown, modal). Never nest card inside card.

### 4.6 Motion tokens

| Token | Duration | Use |
|---|---|---|
| `--motion-fast` | 140ms | hover, focus, button state |
| `--motion-standard` | 200ms | dropdowns, tabs, small panels |
| `--motion-emphasis` | 280ms | drawer/modal entrance |
| `--motion-data` | 200–400ms | chart/result updates |

Ease: `cubic-bezier(.2,0,0,1)` for entrances, ease-in-out for state changes.

**Animate:** button feedback, dropdown/nav transitions, tabs/disclosures, job-status changes, chart updates on real data.
**Do not animate:** constantly moving backgrounds, particles, large parallax, pulsing cards, infinite loops competing with results, intro animations delaying tool access, motion implying a scientific event that has not happened.
`prefers-reduced-motion: reduce` must remove non-essential movement while preserving status and meaning. Never animate layout properties.

### 4.7 Iconography, imagery, scientific figures

- **Icons:** one family, consistent stroke width and optical size. SVG preferred.
- **Hierarchy:** real product screenshots → scientific workflow diagrams → accurate molecular structures with labels (structure, ligand, target, score) → icons → photography only when it adds context.
- **Images:** WebP/AVIF for photos; intrinsic width/height or `aspect-ratio` to prevent layout shift; responsive sizes; meaningful alt text; decorative images marked decorative; never put essential text or controls only in an image.
- **Figures:** caption every scientific figure and state whether it is an actual result, a worked example, or an illustration.
- **3D viewers:** use a real molecular rendering library with validated structure data. Never fake a structure with decorative 3D artwork.
- **Forbidden:** mixing cartoon illustration, photorealistic stock, neon 3D, and unrelated icon styles on one page.

---

## 5. Page templates and information architecture

### 5.1 Homepage (8 bands)

| Band | Content | Rules |
|---|---|---|
| 01 Header | logo · Products · Services · Resources · sign-in · one CTA | |
| 02 Hero | one value proposition, one dominant CTA + secondary service CTA, real product visual | no competing prompts |
| 03 Product entry | 4 problem-led cards → working tools | each names the user problem |
| 04 Proof | validation, sample report, versions, limitations | evidence, not adjectives |
| 05 How it works | 3–4 steps with real product imagery | |
| 06 Use cases & services | researchers · academic labs · biotech · custom pipelines | |
| 07 Trust & resources | docs · tutorials · FAQ · privacy · security · contact | |
| 08 Footer | products · services · developer docs · legal · support · contact | |

**CTA rules (release-blocking):** one main action per section · specific labels ("Run primer design", "Try the docking example") · a CTA must lead to what its label promises · **never send users to an account page when the promised action works without login** · where login is required, say so before the user invests time entering data.

### 5.2 Marketing / editorial (blog, glossary, landing)

Editorial H1 (Source Serif 4), Inter body, above-fold CTA within 300 words linking the relevant tool, `Article` schema only (never `SoftwareApplication`), anti-cannibalisation rules from `RULES.md`/AGENTS policy apply.

### 5.3 Tool page template

`inputs & configuration → progress → results → explanation & export`. Monospace for sequences, inline format help, validation that says how to fix, real progress or an honest indeterminate state, results carry provenance (method, parameters, versions, timestamp), export beside results.

### 5.4 Dashboard / account / billing

Summary and recent activity first, then usage, saved results, account controls. Currency-aware, tabular numerals, every amount labelled with currency.

### 5.5 Developer / API portal

Sidebar on wide screens, collapsible on mobile. Getting started · auth + scoped keys · endpoint docs with examples · error codes · rate limits · versioning/deprecation · changelog + status. Only advertise endpoints and integrations that are tested.

### 5.6 Products vs Services split

Two distinct navigation paths already exist (`Products ▾` / `Services ▾`) and must stay distinct: **Products** = self-service tools; **Services** = custom pipelines, consulting, project enquiries. Service pages must not look like tool pages and vice versa.

---

## 6. Component library

### 6.1 Buttons

Four levels: **primary** (one per action area) · **secondary** · **tertiary** (low emphasis) · **destructive**.
States: default · hover · focus-visible · pressed · disabled · loading. Never allow double submission while an operation is running.

### 6.2 Forms and scientific input

Every input: visible label · format/unit requirements · concise help · inline validation that names the fix · error state not colour-only · keyboard accessible with visible focus · safe paste/upload handling.

Sequence/molecular inputs must state: alphabet, accepted formats, min/max limits, file types, whether ambiguous residues are allowed.
**Never silently alter scientific input.** If the system normalises a sequence, strips invalid characters, changes units, or applies defaults, explain it and record the effective input/parameters in the result provenance.

### 6.3 Async state model (every tool)

`Idle → Validating → Queued → Running → Completed → Partial success → Failed → Cancelled → Expired`

- Never fabricate percentage progress; use an indeterminate indicator when real progress is unmeasurable.
- Completed shows results + provenance + export. Partial success names which stages completed and which failed. Failed explains the failure and safe recovery. Cancelled confirms and states what remains. Expired explains retention and whether rerunning is required.

### 6.4 Tables and result panels

Consistent alignment and precision · units in headers · sorting only where order is meaningful · state which ranking/scoring method produced the order · accessible labels on icon-only controls · no truncation without copy/view-full · CSV export where tabular · empty and error states designed.

### 6.5 Modals, toasts, tooltips

Modals only for decisions requiring attention · toasts for short confirmations, important errors stay in the page · tooltips must not hold essential info unavailable on touch · destructive actions confirm consequences · manage keyboard focus on open/close and return it sensibly.

### 6.6 Header, cards, footer

One logo treatment, one nav pattern, one card system (padding/radius/border/hover), one footer across all pages. Sticky headers must never hide focused controls, headings, or error messages.

---

## 7. Product-specific requirements

### 7.1 Primer design

**Input:** sequence/accession · organism/reference · PCR type + amplicon constraints · thermodynamic/reaction parameters with sensible defaults · advanced settings in a labelled disclosure · FASTA/TXT/CSV upload instructions + validation · one-click known test case.
**Results:** forward/reverse in monospace · length, GC%, Tm and thermodynamics · amplicon + specificity results · pass/warn/fail matrix with per-check explanation · method, parameter values, database/reference version, analysis time · PDF/CSV/JSON export · copy action with confirmation.
**Integrity:** document how each check is calculated · distinguish computationally passing from experimentally validated · include reference/database versions · preserve input + parameter provenance for reproduction · verify against known cases before claiming equivalence.

### 7.2 Molecular docking

**Workflow must be legible as numbered stages:** structure preparation → docking → scoring/rescoring → result review — matching the real ESMFold → Vina → GNINA implementation.
**Input/config:** protein sequence or structure upload · ligand SMILES/formats · helpful format errors · binding-box/pocket config with explained defaults · candidate count + engine parameters · explicit size and compute limits · clear indication of what needs credits or auth.
**Job management:** queued/running/completed/failed/cancelled · honest progress · job ID + creation time · clear cancellation · safe recovery from transient failures · documented retention/deletion.
**Results:** real 3D viewer with keyboard-accessible controls · protein/ligand/binding-site views · **separate score columns per engine with method-specific units** · documented consensus formula · pose comparison · CSV/SDF exports tested end-to-end · visible disclaimer that scores are predictions, not measurements of binding.
**Disclosure:** production runs **GNINA v1.1** (deviation from newer releases) — must remain disclosed until resolved.

### 7.3 Custom pipeline development

Treat as a professional scientific service: problem → intake (data types, outputs, tools, scale, constraints, deadline) → feasibility → written proposal (deliverables, validation, price, timeline, ownership, deployment, support) → milestones → delivery with documentation, reproducibility instructions, and agreed source/deployment artifacts.
Form: short initial form, optional longer technical brief, never require confidential data to request a quote, state how submissions are stored and who can access them, confirm submission with a response expectation only if it can be met.

### 7.4 Developer and API experience

Getting-started guide · authentication + scoped keys · endpoint docs with request/response examples · error codes + troubleshooting · rate limits and quotas · sandbox with safe samples · webhook signing/retry docs if used · versioning + deprecation policy · changelog and service status. **Every advertised feature must be tested, not merely displayed.**

### 7.5 Scientific validation centre

A public hub publishing methods, tool versions, benchmark datasets, reproducible example inputs, expected outputs, and known limitations — separating independently verified results from internal testing. `/validation` is the seed; this becomes the credibility anchor for outreach.

---

## 8. Scientific trust and claims governance

| Requirement | Rule |
|---|---|
| Infrastructure/privacy claims | label each tool browser-side, hosted server-side, or on-prem only if that deployment actually exists |
| Product availability | explicit states: `Available` · `Beta` · `Coming soon` · `Planned`. Planned modules must never look fully functional |
| Docking scores | label method + units; explain predictions ≠ measured affinity |
| Pricing & access | homepage, pricing page, tool screens, API docs, and billing must agree on free limits, credits, subscriptions, account requirements |
| Validation claims | never "clinically validated"/"experimentally proven" without evidence; benchmark methods must be reproducible |
| Banned claims | `audit-ready` / `lab-ready` / `air-gapped` / `zero external API` / `clinical-grade` / "no data leaves" — enforced by `rules_lint` W1 and `CLAIMS_LEDGER.md` |

These are **release-blocking**: a polished interface cannot compensate for contradictory claims.

---

## 9. Engineering standards

- Shared design-token file as single source of truth; **no new inline styles** (see §15).
- Reusable, documented components; business logic separate from presentation.
- API contracts and validation schemas; consistent error format with a request/trace ID.
- Strong typing where compatible with the stack; linting + formatting + automated checks in CI.
- Unit tests for calculation/validation logic; integration tests for database, file, job, payment flows; E2E for core journeys.
- Pin scientific-engine and dependency versions where reproducibility requires it; review licences and advisories.
- Separate dev/staging/prod; versioned migrations with tested backups; rollback strategy; changelog.
- **Frontend never enforces security or billing.** Authorisation, credits, quotas, permissions are server-side. Secrets never in client code.
- Bounded job queues isolated from web requests; timeouts, retries, cancellation, cleanup; no duplicate billing on retry; documented retention; structured logs excluding raw research inputs and secrets.

**Test coverage by behaviour (not percentage):** valid/invalid sequence input · missing/malformed files · known scientific reference cases · numerical calculation and rounding · job retry and cancellation · interrupted uploads · export correctness · permission and cross-account isolation · credit deduction and duplicate submission · payment webhook retries · mobile keyboard and focus · network loss and timeouts · large inputs and resource limits.

---

## 10. Security, privacy, and operations

**Security:** HTTPS everywhere · secure sessions · server-side authorisation on all protected resources · rate limiting and abuse prevention · input validation and output encoding · security headers + documented CSP · dependency and secret scanning · least-privilege services · restricted admin access with audit logging.

**Known gaps to close (from live systems):** unauthenticated legacy `queue/*` routes · `REDIS_URL` absent so rate-limit counters are per-worker · upload validation hardening (extension + content + size, generated storage filenames, outside web root, path-traversal and decompression-bomb guards, per-user isolation).

**Privacy:** document where each data category is processed, what is retained and why, deletion mechanisms, third-party processors and transfers. Never promise on-premises/air-gapped/zero-external-API unless verified per tool and deployment. Privacy wording must match actual behaviour. Review Indian DPDP obligations with qualified counsel.

**Operations:** error tracking + alerting · health checks (`/health` with `sqlite_schema_ok`) · queue/utilisation monitoring · disk and memory alerts · backup restore testing · incident ownership · status communication for material outages · recovery for failed/abandoned jobs · cost monitoring for compute-heavy features.

**Open operational items (registry, §19):** production verification-email transport not configured (password-signup funnel blocked) · GNINA v1.1 acknowledgment pending · 0 captured payments to date · Clarity consent gating is a GTM-side user action.

---

## 11. Accessibility — WCAG 2.2 Level AA

Required: full keyboard navigation · visible focus indicators · semantic headings and landmarks · correct labels and accessible names · error messages wired to inputs · accessible dialogs/menus/tabs/tables · screen-reader announcements for async job-state changes · no keyboard traps · no colour-only signalling · text zoom and reflow · captions/transcripts for meaningful video · reduced-motion support · accessible chart summaries or tabular alternatives · ~44×44px primary mobile touch targets. Also test Windows high contrast and keyboard-only journeys.

---

## 12. Performance, SEO, discoverability

**Core Web Vitals targets (75th percentile):** LCP ≤ 2.5s · INP ≤ 200ms · CLS ≤ 0.1. These are targets to measure against, not claims about the current site.

Requirements: no molecular viewers or heavy libraries on pages that don't need them · lazy-load non-critical imagery and below-fold components · reserve image dimensions · minimise third-party scripts · compress and cache static assets · split large bundles · never block rendering on non-essential animation · immediate interaction feedback even while a backend job runs · test on mid-range mobile and slow networks.

**SEO per important page:** unique title + meta description · one H1 and logical hierarchy · canonical · index/noindex policy · valid sitemap and robots · working internal links and breadcrumbs · Open Graph/social metadata · descriptive alt text · structured data only where the page genuinely qualifies · **no fake reviews, endorsements, or misleading structured data** · titles and snippets must promise only what the page can substantiate.

---

## 13. Analytics, conversion, product feedback

**Required events** (stable schema, documented properties): `page_view` · `primary_cta_clicked` · `tool_started` · `input_validation_failed` · `job_submitted` · `job_completed` · `job_failed` · `result_exported` · `example_loaded` · `documentation_opened` · `signup_started` · `signup_completed` · `pricing_viewed` · `checkout_started` · `payment_succeeded` · `payment_failed` · `contact_form_submitted`.

**Privacy rule:** never send raw DNA/protein sequences, ligand libraries, uploaded filenames, access tokens, or sensitive project detail to analytics. Use non-sensitive identifiers and aggregates.

**Funnel to measure:** landing → CTA click → tool started → valid input → job completed → result viewed/exported → return visit or signup. This distinguishes a design problem from a validation, backend-reliability, or product-value problem.

---

## 14. Content, trust, and documentation

Per tool, publish: purpose and intended use · supported inputs/outputs · engine versions · parameters and defaults · scientific assumptions and limitations · reference cases and benchmark methods · reproducibility information · sample report · citation instructions · troubleshooting and common failure modes · privacy and retention behaviour · a route to report bugs or scientific discrepancies.

For research services, also: scope and deliverables · acceptance criteria · turnaround · validation responsibilities · source-code and IP terms · data handling and confidentiality · post-delivery support.

**Language:** avoid "100% accurate", "guaranteed binding", "clinically validated" unless the exact claim is substantiated and scoped.

---

## 15. Inline-style eradication plan (the uniformity engine)

**Problem:** 532 of 537 pages carry inline `<style>` blocks and 22,866 inline `style="…"` attributes. This is the single largest cause of drift — every inline value is a one-off decision that cannot be tokenised, audited, or updated centrally.

**Strategy — batched by template, never all at once:**

| Wave | Scope | Method |
|---|---|---|
| 0 | Homepage (Phase-1 pilot) | migrate hero/trust/tech-strip inline styles to classes in `home.css`; prove the pattern |
| 1 | Tool pages (`tools.css` + 43 pages) | extract repeated inline patterns to tool components; add `data-ui="product"` |
| 2 | Dashboard, billing, account, checkout | same |
| 3 | Blog + glossary (306 pages) | template-driven; mostly chrome and callouts |
| 4 | Landing pages (45) | final sweep |

**Rules:** no new inline styles in any commit (enforce with a `rules_lint` warning, promote to error after Wave 2) · each wave verified with headless-Chrome screenshots at 375px and 1440px, zero JS errors, zero overflow · each wave ships only after `rules_lint` is green and the FAQ mirror stays 0/0.

**Acceptable exceptions:** per-instance values that are genuinely data (e.g. a chart height bound to data), and elements whose style is set by JS at runtime. Document any exception in the wave's PR.

---

## 16. Phased rollout

### Phase 1 — Audit and foundation (pilot: homepage) ✅ IN PROGRESS
- ✅ Grounded audit (§2) recorded.
- ✅ Hybrid token layer + Inter typography applied to homepage (`home.css`, homepage-only — zero impact on other pages).
- ✅ Hero CTA honesty fix: primary CTA now leads to the promised action (`/primer`), not an account modal.
- ✅ `.sr-only` accessibility fix in `design-tokens.css` (clip technique replaces `display:none`).
- 🔎 Verify: desktop + mobile screenshots, zero JS errors, no overflow, `rules_lint` green.
- **Acceptance:** homepage renders in marketing mode with Inter body, one dominant CTA per band, AA contrast on text pairs, no layout shift, all existing gates still green.

### Phase 2 — Design-system foundation (platform-wide)
- Promote the homepage token layer into `design-tokens.css` as the two-mode system; add `data-ui` mode switching.
- Components: buttons (4 levels × 6 states), forms, cards, tables, modals/toasts, nav, footer — built once, reused.
- Retire the `!important` typography overrides in favour of properly cascading rules.
- **Acceptance:** a new page can be built with zero custom hex values and zero inline styles.

### Phase 3 — Core product experiences
Homepage refinement → primer design → molecular docking → custom pipeline service. Real screenshots, clearer workflows, scientific provenance, complete loading/error states, one-click examples.
**Acceptance:** each page passes the §17 checklist for its category.

### Phase 4 — Platform-wide consistency
Remaining tools, dashboard, account/billing, documentation, developer pages. Waves 1–4 of §15.

### Phase 5 — Engineering hardening
Security gaps (§10), integration testing, scientific regression benchmarks, accessibility audit, performance optimisation, analytics events, operational monitoring.

### Phase 6 — Release and improvement
Staging QA → defect resolution → deploy with rollback → monitor errors and funnels → prioritise from real user feedback.

---

## 17. Release checklist (every item needs an owner and recorded pass/fail)

### A. Brand and visual system
- [ ] One consistent logo, palette, typography, icon family
- [ ] Shared spacing, radius, border, shadow, motion tokens
- [ ] Heading hierarchy and line heights applied consistently
- [ ] No decorative effects interfering with scientific content

### B. Responsive experience
- [ ] Tested at 320/360/375/390/430/768/1024/1280/1440px
- [ ] No accidental page-level horizontal overflow
- [ ] Navigation, forms, cards, tables, viewers work on mobile
- [ ] Sticky elements never cover focused controls or content

### C. Components and interaction
- [ ] Buttons, forms, dropdowns, tabs, modals, tooltips have complete states
- [ ] Keyboard navigation and visible focus work
- [ ] Loading, empty, success, warning, failure, cancellation states implemented
- [ ] Form errors explain how to fix the problem
- [ ] Reduced-motion preference respected

### D. Scientific validity
- [ ] Known reference cases have automated tests
- [ ] Engine versions, parameters, units, database versions recorded
- [ ] Input transformations and defaults transparent
- [ ] Reports carry enough provenance to reproduce the analysis
- [ ] Predictions never presented as experimental or clinical proof

### E. Integrations and backend
- [ ] All advertised API endpoints and integrations tested
- [ ] Retries, timeouts, cancellation, partial failures handled
- [ ] File validation and job resource limits enforced
- [ ] Auth, permissions, credits, quotas enforced server-side
- [ ] Exports tested with actual downloaded files

### F. Security and privacy
- [ ] No secrets or private keys in client code
- [ ] Cross-user data access tests pass
- [ ] Retention and deletion policies match real behaviour
- [ ] Uploads and downloads protected
- [ ] Privacy and infrastructure claims accurate

### G. Accessibility
- [ ] WCAG 2.2 AA audit for critical journeys
- [ ] Contrast, focus, keyboard, labels, error announcements tested
- [ ] Text zoom and reflow work
- [ ] Charts and scientific visualizations have accessible alternatives

### H. Performance and reliability
- [ ] Core Web Vitals measured on real pages
- [ ] Large libraries load only when needed
- [ ] No significant layout shifts during loading
- [ ] Error monitoring and operational alerts active
- [ ] Backup restoration and rollback tested

### I. SEO, analytics, and content
- [ ] Titles, descriptions, canonical URLs, sitemap, indexing rules checked
- [ ] All primary CTAs lead to the promised action
- [ ] Analytics events documented and free of sensitive research data
- [ ] Pricing, availability, infrastructure claims agree across pages
- [ ] Legal, contact, support, documentation links work

### J. Final sign-off
- [ ] Critical end-to-end journeys pass on desktop and mobile
- [ ] No open critical or high-severity defects
- [ ] Staging approval and production rollback plan completed
- [ ] Developer documentation and handover complete
- [ ] Post-launch monitoring and issue ownership assigned

> Checking a box is a project-management action, not proof the work was done. The developer or QA owner must verify each item.

---

## 18. Measurement plan

Baseline first, then compare after release. Do not set conversion targets without measuring the current site.

| Metric | What it tells you |
|---|---|
| Core Web Vitals (mobile + desktop) | load and responsiveness |
| Mobile engagement | whether phone visitors can use the pages |
| Tool-start rate | whether visitors begin an analysis |
| Tool completion rate | whether they finish successfully |
| Service enquiry rate | whether service pages generate leads |
| CTA click-through rate | whether calls to action work |
| Return usage | whether researchers find enough value to return |

---

## 19. Outstanding-issues registry (must be honest, tracked, and resolved or disclosed)

| Item | Status | Notes |
|---|---|---|
| GNINA v1.1 on production | ⚪ disclosed, acknowledgment pending | v1.3.2 links CUDA libs unusable on the GPU-less host |
| Production verification email | 🔵 open | no Brevo/SMTP credentials configured → password-signup funnel blocked; Google OAuth unaffected |
| Captured payments | ⚪ 0 to date | Razorpay live; international payments may need enabling on the account |
| Clarity consent gating | ⚪ user action | GTM container-side; repo cannot gate container tags |
| Unauthenticated `queue/*` routes | 🔵 open | legacy, id-guarded; `/queue/reset/<id>` pre-existing concern |
| `REDIS_URL` absent | 🟡 | rate-limit counters are per-worker, limits ≈ ×workers |
| ~610 inert CMS notifications | ⚪ | no delete endpoint; harmless |
| 3 content pages still show ₹ | ⚪ by design | third-party India context; customer payment surfaces are USD-only |

---

## 20. Final instruction to the developer

Implement this document as the shared design and engineering standard for VigyanLLM. Reuse working functionality. Do not remove scientific capabilities or change calculation logic for visual reasons. Any change to scientific calculations, data handling, API contracts, billing, or authentication requires regression testing.

**Before release, provide:**
1. A list of pages and components changed.
2. A list of known limitations and unresolved issues.
3. Desktop and mobile screenshots of the main journeys.
4. Automated test results and a manual QA report.
5. Accessibility and performance results.
6. Scientific benchmark results for affected tools.
7. Security and privacy verification results.
8. A production deployment and rollback plan.

**Priority order:** scientific trust → consistent UI → responsive behaviour → reliable tool execution, before any additional animation or decorative graphics. That is what makes VigyanLLM a serious international bioinformatics platform rather than a visually polished website.

This document is the standard, not a certification. Final status depends on implementation evidence and QA sign-off.

# CLAIMS_LEDGER.md — VigyanLLM Public-Claims Register

**Created:** 2026-10-02 (WEBSITE_UPDATE_PLAN.md → GOV-02)
**Governing standard:** `rules.md` Part 1 (Human-First rules), especially #2 (qualified review), #3 (never fake
human involvement / numbers), #6 (evidence for claims), #11 (accurate application blocks).
**Scope:** every high-consequence, numeric, scientific, security/privacy, or adoption claim that appears on a
public page. Ledger row required before such a claim may ship (or stay shipped).

**Status values:**
- `REMOVE` — proven unsupported by any available evidence; deletion scheduled.
- `PENDING-EVIDENCE` — may only stay if the owner supplies dated, sourced evidence (else → REMOVE).
- `PENDING-D-03` — blocked on the sovereignty/deployment product-truth decision (plan §10 D-03).
- `PENDING-SCIENTIFIC-REVIEW` — needs a qualified scientific reviewer with a citation.
- `FREEZE` — amplification frozen; rewrite queued (WEBSITE_UPDATE_PLAN TRUST-03).
- `RETAIN` — evidence exists in-repo; row kept for audit trail.
- `RESOLVED` — issue fixed in working tree (2026-10-02 batch), kept for the record.

Counts/locations measured 2026-10-02 against the working tree.

| ID | Claim (as published) | Type | Where (measured 2026-10-02) | Evidence status | Status | Owner role |
|---|---|---|---|---|---|---|
| CLM-001 | `aggregateRating` 4.8★ / 127 ratings | Schema | 13 files: primer, blast, msa, docking, tm-calculator, gc-calculator, dna-to-rna, biostatistics-calculator, blast-for-primer-specificity, docking-for-drug-discovery, gc-calculator-for-pcr, primer-design-for-cloning, primer-design-for-qpcr | Live `/api/reviews/public` = **4 reviews, avg 5.0** → count fabricated | REMOVE (TRUST-01) | Frontend |
| CLM-002 | `aggregateRating` 4.7★ / 312 ratings | Schema | `frontend/demo.html` (SoftwareApplication) | No data source anywhere; differs from CLM-001 (inconsistent fakes) | REMOVE (TRUST-01) | Frontend |
| CLM-003 | "Trusted by Researchers in 50+ Countries" | Adoption | `frontend/index.html` hero | No analytics export in repo | ✅ RESOLVED 2026-10-02 — trust-signals section removed (D-04: remove all) | Marketing |
| CLM-004 | "Used at IITs, AIIMS, MIT, Stanford, Oxford, and 500+ research institutions worldwide" | Adoption / institution names | `frontend/index.html` hero | **No evidence of institutional use anywhere in repo**; named elite institutions = highest rule-#3 risk on site | ✅ RESOLVED 2026-10-02 — removed with trust-signals section | Marketing |
| CLM-005 | "10K+ Researchers" / "50+ Countries" / "500+ Institutions" / "1M+ Primers Designed" stats | Adoption | `frontend/index.html` hero stats (also `academic-partnership.html` stats-bar, `docking.html` "10K+ Docking Runs", `team.html`/`about.html` "serves researchers at IISc/AIIMS/CSIR" + "Institutional Users" chips) | None | ✅ RESOLVED 2026-10-02 — all removed (D-04); one extra scope-extend pass caught team/about chips | Marketing |
| CLM-006 | "10,000+ Primer pairs designed" / "500+ Active researchers" / "99.5% Pipeline uptime" | Adoption + SLO | `frontend/primer.html` social-proof section | None (uptime would need monitoring data) | ✅ RESOLVED 2026-10-02 — `#social-proof` section removed | Marketing + Backend |
| CLM-007 | Testimonial: "VigyanLLM's validation pipeline caught dimer issues… — Principal Scientist, Molecular Diagnostics Lab" | Testimonial | `frontend/primer.html` social-proof | No attribution source, no consent record | ✅ RESOLVED 2026-10-02 — removed | Marketing |
| CLM-008 | Testimonial: "We switched from Primer3… — Dr. Priya Nair, Molecular Diagnostics Lab, Bangalore" | Testimonial + **named person** | `frontend/primer3-alternative.html` | No source/consent record in repo; named individual = invented-authorship risk | ✅ RESOLVED 2026-10-02 — Testimonials section removed | Marketing |
| CLM-009 | "Trusted by labs across India and beyond" (reviews section heading) | Adoption | `frontend/index.html` reviews grid | Section is `display:none` and only renders with ≥10 approved real reviews (moderated `/api/reviews/public`, 4 live) | ⚠️ CONDITIONAL — evidence-gated dynamic block kept; re-check heading wording when reviews reach 10 | Marketing |
| CLM-010 | "air-gapped deployment" | Security/deployment | 7 files (repo-wide count 2026-10-02) | No deployment evidence | ✅ RESOLVED 2026-10-02 (D-03: hosted-only today) — removed as current claim; air-gapped survives only as clearly-marked "Planned/roadmap" text on `features/on-premises.html`, `about/sovereign-ai.html`, `platform.html` (generic on-prem table + note) and as factual references to Primer3/local-BLAST third-party tools | Product |
| CLM-011 | "zero external API" / "zero external API calls" | Privacy/security | 7 files | Contradicted in-code: GTM/gtag, Google Fonts, Razorpay, geo-IP (`visitor_routes.py`), NCBI retrieval, Google OAuth | ✅ RESOLVED 2026-10-02 — replaced with scoped "no third-party LLM APIs in the pipeline" (evidence: deterministic Primer3/SantaLucia/Vina/GNINA pipeline); removed elsewhere; browser calculators keep device-scoped claims | Privacy + Product |
| CLM-012 | "no data leaves" / "never leaves your browser/India" family | Privacy | 5 files | Contradicted for hosted mode; true only for browser-only calculators | ✅ RESOLVED 2026-10-02 (mode-by-mode) — hosted pages now say "runs on our hosted servers under our Privacy policy"; browser-only tools (cloning-simulator, biostatistics-calculator, t-test, restriction-cloning, index cloning card) keep device-scoped claims (true, client-side code) | Privacy |
| CLM-013 | "clinical-grade" | Scientific/clinical | 3 files | Terms = Research Use Only | RESOLVED 2026-10-02 (TRUST-03) — all 4 occurrences rewritten/removed; 0 remain | Scientific QA + Legal |
| CLM-014 | "lab-ready" (reports/deployment) | Scientific | 13 files | Undefined term; no evidence pack | RESOLVED 2026-10-02 (TRUST-03) — 26 occurrences → validated/complete/(recommended); 0 remain | Scientific QA |
| CLM-015 | "audit-ready" (reports) | Scientific/regulatory-adjacent | 88 files | "Audit-ready" undefined; no audit framework referenced → cannot imply regulatory acceptance | RESOLVED 2026-10-02 (TRUST-03) — 136 occurrences → fully documented/complete/documented reporting; 0 remain | Scientific QA + Legal |
| CLM-016 | "validated" (unqualified) | Scientific | 313 files (triage, not blanket removal) | Legit where bound to `/validation` 3-pair benchmark or published citations; illegit as free-floating badge | TRIAGE per-context (TRUST-03) | Scientific QA |
| CLM-017 | Sovereignty bundle on homepage: "on-premises", "air-gapped", "US data center", "100% on-premise, zero external API", "in the browser" — all in one page | Product truth (C3) | `frontend/index.html` + `platform.html`, `privacy.html`, `security.html`, `dpdp.html` | Mutually exclusive as written | ✅ RESOLVED 2026-10-02 (D-03) — index rewritten to hosted-only story (H1 "for Primer Design, CRISPR & Docking", Web Browser OS, India-hosted badges, "Enterprise self-hosting is on our roadmap"); `platform.html` table reframed generic + note; `privacy/security/dpdp.html` had no D-03 content (nav baseline only) | Product + Privacy |
| CLM-018 | "24-step validation pipeline" | Product fact | site-wide | **VERIFIED**: engine `primerforge/engine/steps/` = 24 steps (AGENTS ground truth) | RETAIN | Product |
| CLM-019 | "22-step" / "22 validation steps" variants | Product fact (wrong) | 9 hits / 8 files (see SEO-01) | Contradicts CLM-018 | RESOLVED 2026-10-02 (working tree) | Frontend |
| CLM-020 | "DPDP-compliant" (as achieved state) | Legal/regulatory | To sweep with TRUST-05 | Compliance not evidenced; DPDP obligations ≠ certified status | PENDING-SCIENTIFIC-REVIEW + Legal (TRUST-05) | Legal |
| CLM-021 | "99.5% accuracy" (TaqMan probe assays) | Scientific | `frontend/glossary/taqman-probe.html` | No citation given on page | PENDING-SCIENTIFIC-REVIEW (add citation or remove number) | Scientific QA |
| CLM-022 | Blog/comparison "10,000+" occurrences | Context-dependent | 16 hits in blog/ + comparison pages | Sampled: comparison pages = MAFFT technical capability (legit); blog hits pending context check | TRIAGE in TRUST-03 sweep (keep technical contexts, remove adoption contexts) | Editorial |
| CLM-023 | `ratingCount`/review claims in any new schema | Schema | — | Allowed only if `ratingValue`/`ratingCount` match live `/api/reviews/public` | RULE: rules-lint blocks any `aggregateRating` unless listed here as RESOLVED-with-evidence | Frontend |

## Process

1. New public claim (numeric/adoption/scientific/security/privacy) → add a row here **before** publishing.
2. `scripts/rules_lint.py` enforces the machine-checkable subset (CLM-001/002/019 schema+term rules).
3. `REMOVE` rows must be deleted in the same change that touches the containing template.
4. Evidence supplied by the owner gets attached (link/exports path) and status flips to `RETAIN` with review date.

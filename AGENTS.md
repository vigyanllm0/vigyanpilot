# AGENTS.md — Agent Handoff & Tracking

**Session:** Phase 5 (ORACLE FAQ Generation) — Completed Jul 2026  
**Next Sprint:** User review → git commit/push

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

## Key Commands
- Python bulk-replace scripts for 200+ file operations
- `import os, glob` loop with `string.replace()` for safe batch editing
- No git push until user approval

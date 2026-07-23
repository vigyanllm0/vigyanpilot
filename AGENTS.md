# AGENTS.md — Agent Handoff & Tracking

**Session:** PA-08, PA-09, PA-11, PA-15, SEC-01–15, Phase 2 content — Completed Jul 2026  
**Next Sprint:** EC2 CMS backend, Directory submissions, Product Hunt launch

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

## Key Commands
- Python bulk-replace scripts for 200+ file operations
- `import os, glob` loop with `string.replace()` for safe batch editing
- No git push until user approval

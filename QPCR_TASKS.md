# qPCR Data Analyzer — Task Breakdown (OpenCode Execution)

**Master Plan:** `QPCR_MASTER_PLAN.md` (frozen spec)
**Repo:** `/Users/macbookpro/.local/share/opencode/worktree/b6b7e5/quick-lagoon`

---

## Phase A — Foundation (Batch A)
*Modules: Data model, 3 parsers, fixtures, Python mirror, debug page*

| Task ID | Title | Specialist | Status | Blockers | Notes |
|---------|-------|------------|--------|----------|-------|
| A1 | Create repo layout: `frontend/qpcr/`, `tests/fixtures/qpcr/`, `docs/` | Coder | ✅ done | — | Created |
| A2 | Define canonical `Run` / `Analysis` data model in `qpcr-engine.js` | Coder | ✅ done | A1 | Zero-DOM, zero-deps |
| A3 | Implement RDML 1.2 parser (XML) → canonical model | Coder | ✅ done | A2 | Bio-Rad CFX export format |
| A4 | Implement Bio-Rad CFX CSV parser → canonical model | Coder | ✅ done | A2 | CFX Maestro "Export → CSV" |
| A5 | Implement Generic Template parser (TSV/CSV) → canonical model | Coder | ✅ done | A2 | Downloadable template with per-vendor instructions |
| A6 | Create 3 golden parse fixtures (1 per format) in `tests/fixtures/qpcr/` | Coder | ✅ done | A3–A5 | RDML, CFX CSV, template TSV |
| A7 | Create edge-case fixtures | Coder | ✅ done | A6 | edge_cases.tsv + corrupted handling verified |
| A8 | Implement Python mirror `tests/qpcr_mirror.py` | Coder | ✅ done | A2 | 16 tests pass |
| A9 | Mirror equality tests | Coder | ✅ done | A6, A8 | 16/16 pass |
| A10 | Create debug page `frontend/qpcr/debug.html` | Coder | ✅ done | A2–A5 | Dev-only, working |

## Batch A Status: ✅ GATE PASSED (18/18 tests, 5/5 ACs, JS+Python mirror equal, perf 72ms/384 wells)
## Batch B Status: 🔄 PARTIAL (charts lib + amplification view done; melt/zoom/perf TODO)
## Batch B Status: 🔄 PARTIAL (charts lib + amplification view done; melt/zoom/perf TODO)
## Batch C Status: 🔄 PARTIAL (standard curve + expression + QC done; math validation TODO)
## Batch D Status: 🔄 PARTIAL (table + 96/384 plate done; view-state/URL/share/strip/rotor TODO)
## Batch E Status: 🔄 PARTIAL (PNG/CSV export + methodology doc done; PDF/methods/SEO/perf TODO)
- All 3 formats parse identically in JS + Python
- 16/16 mirror equality tests pass
- Debug page functional
- Engine: canonical model, 3 parsers, analysis pipeline, QC flags, Savitzky-Golay derivative

## Batch B — Core Charts (PARTIAL)
| B1 | Build `qpcr-charts.js` — Canvas line/scatter/bar | Coder | ✅ done | A1 | <60KB, zero deps |
| B2 | Amplification view: cycles × fluorescence, channel tabs | Coder | ✅ done | B1 | In qpcr-analyzer.html |
| B3 | Amplification interactions: linear/log Y, baseline, zoom | Coder | ⏳ todo | B2 | Y-mode toggle done; brush-zoom TODO |
| B4 | Melt view: −dF/dT vs T, Savitzky-Golay, Tm peaks | Coder | ⏳ todo | B1 | Needs melt data in fixtures + UI |
| B5 | Performance: 384-well × 5-channel <200ms | Coder | ⏳ todo | B2, B4 | Needs stress fixture |
| B6 | "View as table" toggle beside every chart | Coder | ⏳ todo | B2, B4 | |

## Batch C — Analysis (PARTIAL)
| C1 | Standard curve: Cq vs log₁₀(quantity) | Coder | ✅ done | A2 | In engine + analyzer |
| C2 | Unknown quantification: Q = 10^((Cq−b)/m) | Coder | ✅ done | C1 | In engine |
| C3 | Expression: Livak + Pfaffl | Coder | ✅ done | A2 | In engine + analyzer |
| C4 | Multi-reference target support | Coder | ✅ done | C3 | In engine |
| C5 | QC flags system | Coder | ✅ done | A2 | In engine + analyzer |
| C6 | Math validation vs published examples | Coder | ⏳ todo | C1, C3 | Needs published datasets |
| C7 | Missing standards/control → explanatory message | Coder | ⏳ todo | C1, C3 | |

## Batch D — Custom Views (PARTIAL)
| D1 | Full data table | Coder | ✅ done | A2 | In analyzer |
| D2 | ViewState JSON schema | Coder | ⏳ todo | D1 | |
| D3 | My Views: save/load localStorage | Coder | ⏳ todo | D2 | |
| D4 | URL hash encoding | Coder | ⏳ todo | D2 | |
| D5 | Plate views: 96, 384, strip, rotor | Coder | ✅ partial | B1 | 96+384 done; strip/rotor TODO |
| D6 | Bidirectional sync | Coder | ⏳ todo | B2, D1, D5 | |
| D7 | Round-trip tests | Coder | ⏳ todo | D3, D4 | |

## Batch E — Output & Chrome (PARTIAL)
| E1 | PNG export per view | Coder | ✅ done | B1 | In charts lib |
| E2 | CSV export of current table view | Coder | ✅ done | D1 | In analyzer |
| E3 | Multi-page PDF report | Coder | ⏳ todo | C1, C3, E1, E2 | |
| E4 | MIQE-aligned methods sentence | Coder | ⏳ todo | C1, C3, C5 | |
| E5 | Page chrome: slug, title, FAQ, schemas, sitemap | Coder | ⏳ todo | — | |
| E6 | rules_lint clean | Coder | ⏳ todo | E5 | |
| E7 | Headless tests 9/9 | Coder | ⏳ todo | All | |
| E8 | Perf: page weight <800KB, PSI ≥90 | Coder | ⏳ todo | All | |
| E9 | QPCR_METHODOLOGY.md | Coder | ✅ done | C1, C3, C5 | Created |

**Batch A Gate:** All fixtures parse identically in JS + Python; corrupted files give helpful errors; debug page works.

---

## Phase B — Core Charts (Batch B)
*Modules: Chart lib, amplification + melt views*

| Task ID | Title | Specialist | Status | Blockers | Notes |
|---------|-------|------------|--------|----------|-------|
| B1 | Build `qpcr-charts.js` — Canvas line/scatter/bar, color-blind palette, series toggle, zoom, PNG export | Coder | ⏳ todo | A1 | <60KB raw; no deps |
| B2 | Amplification view: cycles × fluorescence, channel tabs (FAM/HEX/ROX/CY5), legend grouped by sample/target | Coder | ⏳ todo | B1 | Click legend/well → toggle; shift-click range |
| B3 | Amplification interactions: linear/log Y, raw vs baseline-subtracted, brush-zoom cycles | Coder | ⏳ todo | B2 | Threshold-Cq verification overlay (labeled) |
| B4 | Melt view: −dF/dT vs T, Savitzky-Golay (window 7) derivative, Tm peaks labeled | Coder | ⏳ todo | B1 | Multi-peak → specificity flag |
| B5 | Performance: 384-well × 5-channel stress fixture renders <200ms interaction | Coder | ⏳ todo | B2, B4 | Visible-only + LTTB downsampling |
| B6 | "View as table" toggle beside every chart | Coder | ⏳ todo | B2, B4 | Syncs with M6 table |

**Batch B Gate:** Stress fixture interaction <200ms; 384-well usable; color + line-style differentiation; color-blind safe.

---

## Phase C — Analysis (Batch C)
*Modules: Standard curve, expression (both methods), QC flags*

| Task ID | Title | Specialist | Status | Blockers | Notes |
|---------|-------|------------|--------|----------|-------|
| C1 | Standard curve: Cq vs log₁₀(quantity), regression, efficiency %, slope, intercept, R² | Coder | ⏳ todo | A2, A8 | Auto-detect standards by content type |
| C2 | Unknown quantification: Q = 10^((Cq−b)/m) | Coder | ⏳ todo | C1 | |
| C3 | Expression: Livak (2^(-ΔΔCq)) + Pfaffl (efficiency-corrected), user-selectable, default Pfaffl when E exists | Coder | ⏳ todo | A2, A8 | Replicates: mean ± SD, SD propagation |
| C4 | Multi-reference target support | Coder | ⏳ todo | C3 | |
| C5 | QC flags system: NTC amp, replicate SD>0.5, E outside 90–110%, R²<0.99, melt multi-peak, late Cq>35, no amp | Coder | ⏳ todo | A2, C1, B4 | Configurable thresholds; tooltip + troubleshooting link |
| C6 | Math validation: fixtures vs published example datasets (Livak, Pfaffl, efficiency, Tm) | Coder | ⏳ todo | C1, C3, C5 | Python mirror validates too |
| C7 | Missing standards/control → explanatory message, not silent failure | Coder | ⏳ todo | C1, C3 | |

**Batch C Gate:** Math validated against published examples; both methods work; QC flags documented in `QPCR_METHODOLOGY.md`.

---

## Phase D — Custom Views (Batch D)
*Modules: Table, view-state, My Views, URL share, plate/strip/rotor*

| Task ID | Title | Specialist | Status | Blockers | Notes |
|---------|-------|------------|--------|----------|-------|
| D1 | Full data table: Well, Sample, Target, Channel, Content, Cq, Cq SD, Tm, Quantity, Status | Coder | ⏳ todo | A2 | Column picker, multi-filter, sort, group-by, search |
| D2 | ViewState JSON schema + (de)serialization | Coder | ⏳ todo | D1 | Table + charts + plate + analysis prefs |
| D3 | My Views: save/load presets to localStorage (v1) | Coder | ⏳ todo | D2 | Retention hook |
| D4 | URL hash encoding: settings travel, data never does | Coder | ⏳ todo | D2 | Privacy-safe sharing |
| D5 | Plate views: 96 (8×12), 384 (16×24), 8-strip, 12-strip, rotor (36) | Coder | ⏳ todo | B1, D1 | Color by Cq/sample/target/status; click-drag selection syncs to charts/table |
| D6 | Bidirectional sync: plate ↔ curves ↔ table selection | Coder | ⏳ todo | B2, D1, D5 | The "Maestro feel" integration |
| D7 | Round-trip tests: save → load → URL hash → fresh parse = identical view | Coder | ⏳ todo | D3, D4 | WYSIWYG exports |

**Batch D Gate:** Every view preference round-trips; URL hash restores exact view; exports reflect filtered/sorted view.

---

## Phase E — Output & Chrome (Batch E)
*Modules: Exports, methods generator, SEO, full suite, PSI*

| Task ID | Title | Specialist | Status | Blockers | Notes |
|---------|-------|------------|--------|----------|-------|
| E1 | PNG export per view (canvas) | Coder | ⏳ todo | B1 | |
| E2 | CSV export of current table view (filtered/sorted) | Coder | ⏳ todo | D1 | |
| E3 | Multi-page PDF report: run summary → curves → std curve → expression → table → methods block | Coder | ⏳ todo | C1, C3, E1, E2 | Reuse pharma report generator pattern |
| E4 | MIQE-aligned methods sentence generator (reflects ACTUAL settings) | Coder | ⏳ todo | C1, C3, C5 | Copy-ready, auto-populated |
| E5 | Page chrome: `/qpcr-analyzer` slug, title, FAQ (6 GSC queries), schemas, internal links, sitemap, IndexNow | Coder | ⏳ todo | — | Tool-page pattern (baked partials, auth overlay, navy chrome) |
| E6 | `rules_lint` clean (0 err) | Coder | ⏳ todo | E5 | |
| E7 | Headless tests: fixture upload → all views render → toggle/filter/export → 0 console errors (desktop+mobile) | Coder | ⏳ todo | All prior | 9/9 probes |
| E8 | Perf: page weight <800KB, PSI ≥90 | Coder | ⏳ todo | All prior | |
| E9 | `QPCR_METHODOLOGY.md` — every formula, threshold, source documented | Coder | ⏳ todo | C1, C3, C5 | Founder reviews methods wording |

**Batch E Gate:** All ACs green; founder demo; methods wording review; release → IndexNow + Request Indexing.

---

## Non-Goals (Explicit — Do Not Implement)
- Binary vendor formats (.pcrd/.eds/.ixo) → v1.5 via CSV templates
- Cq re-calling → v2 only with published methodology
- geNorm/reference validation, inter-run calibration → v2 ("qbase+ free")
- Server processing of user data → NEVER
- New chart libraries → custom canvas only

---

## Risk Register
| Risk | Mitigation |
|------|------------|
| Scientific responsibility (results in theses) | Instrument-reported Cq only; every formula in `QPCR_METHODOLOGY.md`; founder reviews methods |
| Format drift | Fixtures + verify export menus on current vendor versions during Batch A |
| Large-file performance | Visible-only rendering, LTTB downsampling, progress UI, perf gate |
| Scope creep | This doc frozen; additions = explicit approval + re-freeze |

---

## Execution Order
```
A1 → A2 → (A3, A4, A5 parallel) → A6 → A7 → A8 → A9 → A10  [Batch A Gate]
→ (B1 → B2 → B3) + (B4 parallel) → B5 → B6                 [Batch B Gate]
→ C1 → C2 → (C3, C4 parallel) → C5 → C6 → C7               [Batch C Gate]
→ D1 → D2 → (D3, D4 parallel) → D5 → D6 → D7               [Batch D Gate]
→ (E1, E2, E3 parallel) → E4 → E5 → E6 → E7 → E8 → E9      [Batch E Gate]
```

**Parallel branches** marked with `+` can run concurrently by the same agent.
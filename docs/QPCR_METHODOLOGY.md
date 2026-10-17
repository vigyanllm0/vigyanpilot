# qPCR Data Analyzer — Methodology

**Version:** 1.0.0
**Scope:** Research use only. Not for clinical diagnostic decisions.

## 1. Data Model

The canonical `Run` model is defined in `frontend/qpcr/qpcr-engine.js`. All parsers produce this model. The Python mirror (`tests/qpcr_mirror.py`) produces identical output.

### Channel Canonicalization

Vendor dye names are mapped to 5 canonical channels:

| Canonical | Aliases |
|-----------|---------|
| FAM | SYBR, SYBR Green, EVA Green, LC Green, Green |
| HEX | VIC, TET, JOE, CAL Gold 540 |
| ROX | Texas Red, TAMRA, CAL Orange 560 |
| CY5 | Quasar 670 |
| CY5.5 | Quasar 705 |

**Source:** Bio-Rad CFX, Applied Biosystems, Roche LightCycler documentation.

## 2. Parsers

### RDML 1.2
- Format: XML. Parsed via regex (no DOMParser dependency).
- Wells identified by `<react>` elements with `<position>`.
- Amplification data: space/comma/semicolon-separated floats in `<amplificationData>`.

### Bio-Rad CFX CSV
- Format: CSV with header row containing "Well" + "Fluor/Target".
- Amplification columns: headers matching `Cycle N` or numeric.
- Cq, Cq SD, Tm extracted by column name matching.

### Generic Template (TSV/CSV)
- Format: Tab or comma-delimited.
- Required columns: Well, Sample, Target, Channel.
- Optional: Content, Cq, CqSD, Tm, Amplification (semicolon-separated).

## 3. Analysis Methods

### Standard Curve
- **Model:** Linear regression of Cq vs log₁₀(quantity)
- **Slope (m), intercept (b), R²** computed via ordinary least squares.
- **Efficiency:** E% = (10^(-1/m) - 1) × 100
- **Acceptable range:** 90–110% (MIQE guideline)
- **Unknown quantification:** Q = 10^((Cq - b) / m)

**Source:** MIQE guidelines (Bustin et al., 2009, Clin Chem 55:611-622).

### Expression Analysis

#### Livak Method (2^-ΔΔCq)
- ΔCq = Cq(target) - mean Cq(reference targets)
- ΔΔCq = ΔCq(sample) - ΔCq(control)
- Fold change = 2^(-ΔΔCq)
- **Source:** Livak & Schmittgen, 2001, Methods 25:402-408.

#### Pfaffl Method (efficiency-corrected)
- ratio = E_target^(ΔCq_target) / E_ref^(ΔCq_ref)
- Where E = efficiency factor (E% / 100 + 1)
- Default when standard curve efficiencies are available.

**Source:** Pfaffl, 2001, Nucleic Acids Res 29:e45.

#### Replicate Statistics
- Mean ± SD per sample×target
- SD propagation: SD_ΔCq = √(SD_target² + SD_ref²)
- Fold error bars: 2^(-ΔΔCq ∓ SD)

### Melt Curve Derivative
- **Method:** Savitzky-Golay smoothing (window 7) over central difference
- **Output:** -dF/dT vs temperature
- **Tm detection:** Local maxima above 10% of maximum derivative
- **Multi-peak:** >1 peak → specificity flag (SYBR runs)

### QC Flags

| Flag | Condition | Severity |
|------|-----------|----------|
| NTC_AMP | Cq detected in NTC | strong (<35), weak (≥35) |
| LATE_CQ | Cq > 35 (configurable) | info |
| NO_AMP | No amplification / Cq = null | info |
| MULTI_PEAK | >1 melt peak | warning |
| HIGH_REPLICATE_SD | Replicate SD > 0.5 (configurable) | warning |
| EFFICIENCY_OUT_OF_RANGE | E% outside 90–110% | warning |
| LOW_R2 | R² < 0.99 | warning |

## 4. Thresholds (Configurable)

| Parameter | Default | Source |
|-----------|---------|--------|
| NTC Cq cutoff | 35 | MIQE / common practice |
| Replicate SD max | 0.5 | MIQE |
| Efficiency min | 90% | MIQE |
| Efficiency max | 110% | MIQE |
| R² min | 0.99 | MIQE |
| Late Cq cutoff | 35 | Common practice |

## 5. Scientific Stance (v1)

- **v1 analyzes instrument-reported Cq only.** No re-calling without published methodology.
- Cq values are never recomputed. The threshold-Cq overlay in the amplification view is labeled "verification" and never replaces reported Cq.
- Every formula and threshold is documented here with its source.
- Methods output sentence reflects the ACTUAL settings used, never generic text.

## 6. Performance Targets

| Metric | Target |
|--------|--------|
| Parse 10MB RDML | <3s |
| 96 wells × 5 channels interaction | <200ms |
| 384-well run | Usable (visible-only + LTTB downsampling) |
| Page weight | <800KB |
| PageSpeed Insights | ≥90 |

## 7. Non-Goals (v1)

- Binary vendor formats (.pcrd, .eds, .ixo) → v1.5 via CSV templates
- Cq re-calling → v2 (only with published methodology, LinRegPCR-style)
- geNorm/reference validation → v2
- Server processing of user data → NEVER
- New chart libraries → custom canvas only
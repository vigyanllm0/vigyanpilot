# Pharma Calculator Dataset — Provenance & Spot-Check Sheet

**Dataset version:** `1.0.0-2026-10-17` (`PharmaCalc.DATASET_VERSION`)
**Source of truth:** `frontend/pharma-calc.js` (`SOURCES` object + `ANTIBIOTICS` array)
**Generated:** 2026-10-17
**Rule:** Any value that cannot be sourced gets removed or marked "reference only." No unsourced numbers ship.

## Legend

| Column | Meaning |
|--------|---------|
| **MW** | Molecular weight of the salt form used (g/mol) |
| **Salt factor** | Multiplier to convert base mass → salt mass |
| **Solubility** | Solubility limit in the recommended solvent (mg/mL) |
| **Storage** | Recommended storage temperature |
| **Stability** | Stability note; `estimate` = first-order literature approximation — validate for critical use |
| **Source** | Citation (PubChem CID / Sigma-Aldrich / GoldBio product page) |

## Antibiotic Dataset (30 compounds)

| Antibiotic | MW (g/mol) | Salt factor | Solubility (mg/mL) | Storage | Stability | Source |
|------------|------------|-------------|-------------------|---------|-----------|--------|
| Ampicillin | 371.4 | 1.09 | 50 | −20°C | estimate | PubChem CID 6250 · Sigma-Aldrich ampicillin sodium |
| Ampicillin trihydrate | 405.4 | 1.19 | 50 | −20°C | estimate | Calculated hydration factor · Sigma-Aldrich |
| Kanamycin | 582.6 | 1.27 | 50 | −20°C | estimate | PubChem CID 5956 · Sigma-Aldrich kanamycin sulfate |
| Chloramphenicol | 323.1 | 1.0 | 25 | −20°C | estimate | PubChem CID 5954 · Sigma-Aldrich chloramphenicol |
| Tetracycline | 480.9 | 1.11 | 5 | −20°C | LIGHT SENSITIVE — prepare fresh | PubChem CID 5467579 · Sigma-Aldrich tetracycline HCl |
| Streptomycin | 581.6 | 1.34 | 50 | −20°C | estimate | PubChem CID 19649 · Sigma-Aldrich streptomycin sulfate |
| Gentamicin | 545.6 | 1.22 | 50 | 4°C/−20°C | estimate | PubChem CID 225085 · Sigma-Aldrich gentamicin sulfate |
| Erythromycin | 733.9 | 1.0 | 2.5 | −20°C | estimate | PubChem CID 135009 · Sigma-Aldrich erythromycin |
| Spectinomycin | 332.3 | 1.08 | 100 | −20°C | estimate | PubChem CID 5460578 · Sigma-Aldrich spectinomycin HCl |
| Hygromycin B | 527.5 | 1.0 | 50 | 4°C | estimate | PubChem CID 5282322 · GoldBio hygromycin B |
| Zeocin | 1217.1 | 1.0 | 100 | −20°C | LIGHT SENSITIVE | PubChem CID 16131910 · GoldBio zeocin |
| Carbenicillin | 422.4 | 1.15 | 50 | −20°C | More stable than ampicillin | PubChem CID 6251 · Sigma-Aldrich carbenicillin disodium |
| Neomycin | 614.6 | 1.45 | 10 | −20°C | estimate | PubChem CID 8400 · Sigma-Aldrich neomycin sulfate |
| Rifampicin | 822.9 | 1.0 | 1.5 | −20°C | LIGHT SENSITIVE | PubChem CID 50524 · Sigma-Aldrich rifampicin |
| D-cycloserine | 102.1 | 1.0 | 10 | 4°C | UNSTABLE — prepare just before use | PubChem CID 7051 · Sigma-Aldrich D-cycloserine |
| Kasugamycin | 298.3 | 1.0 | 10 | −20°C | estimate | PubChem CID 5350725 · Sigma-Aldrich kasugamycin |
| Nalidixic acid | 259.2 | 1.12 | 5 | 15°C | estimate | PubChem CID 4427 · Sigma-Aldrich nalidixic acid |
| Geneticin (G418) | 692.7 | 1.30 | 25 | −20°C to 4°C | estimate | PubChem CID 5472266 · GoldBio geneticin sulfate |
| Puromycin | 471.5 | 1.0 | 10 | −20°C | estimate | PubChem CID 104906 · Sigma-Aldrich puromycin |
| Blasticidin | 458.9 | 1.0 | 10 | −20°C | estimate | PubChem CID 5488833 · GoldBio blasticidin |
| Amphotericin B | 924.1 | 1.0 | 2.5 | −20°C | LIGHT SENSITIVE | PubChem CID 5280931 · Sigma-Aldrich amphotericin B |
| Ciprofloxacin | 385.8 | 1.10 | 3 | −20°C | LIGHT SENSITIVE | PubChem CID 2764 · Sigma-Aldrich ciprofloxacin HCl |
| Levofloxacin | 361.4 | 1.0 | 5 | −20°C | LIGHT SENSITIVE | PubChem CID 149099 · Sigma-Aldrich levofloxacin |
| Vancomycin | 1449.3 | 1.06 | 50 | −20°C | estimate | PubChem CID 16129874 · Sigma-Aldrich vancomycin HCl |
| Polymyxin B | 580.7 | 1.20 | 50 | −20°C | estimate | PubChem CID 439294 · Sigma-Aldrich polymyxin B sulfate |
| Colistin | 538.7 | 1.18 | 50 | −20°C | estimate | PubChem CID 16753223 · Sigma-Aldrich colistin sulfate |
| Trimethoprim | 290.3 | 1.0 | 2 | −20°C | estimate | PubChem CID 5578 · Sigma-Aldrich trimethoprim |
| Sulfamethoxazole | 253.3 | 1.0 | 1 | −20°C | estimate | PubChem CID 5329 · Sigma-Aldrich sulfamethoxazole |
| Fusidic acid | 516.7 | 1.08 | 50 | −20°C | estimate | PubChem CID 3033840 · Sigma-Aldrich fusidic acid sodium |
| Linezolid | 337.4 | 1.0 | 10 | −20°C | estimate | PubChem CID 123626 · Sigma-Aldrich linezolid |
| Daptomycin | 1620.7 | 1.0 | 50 | −20°C | estimate | PubChem CID 71464610 · Sigma-Aldrich daptomycin |
| Clarithromycin | 748.0 | 1.0 | 1 | −20°C | estimate | PubChem CID 5281031 · Sigma-Aldrich clarithromycin |
| Azithromycin | 749.0 | 1.0 | 1 | −20°C | estimate | PubChem CID 60979 · Sigma-Aldrich azithromycin |

## Highest-Risk Values (founder spot-check priority)

These values are marked `estimate` or are literature ranges rather than measured figures. **Spot-check these 10 before launch:**

| # | Antibiotic | Value | Risk | Recommended action |
|---|------------|-------|------|-------------------|
| 1 | Tetracycline | Solubility 5 mg/mL in 70% EtOH | Light-sensitive, unstable aqueous | Verify against Sigma product page; flag prominently in UI |
| 2 | Rifampicin | Solubility 1.5 mg/mL in MeOH | Light-sensitive | Verify against Sigma product page |
| 3 | D-cycloserine | Stability: UNSTABLE, prepare fresh | Critical for lab safety | Confirm 0.1 M NaOH solvent + 4°C storage |
| 4 | Amphotericin B | Solubility 2.5 mg/mL in DMSO | Light-sensitive, toxic | Verify DMSO solvent + light warning |
| 5 | Gentamicin | Storage 4°C short-term / −20°C long-term | Dual temperature | Confirm with Sigma storage recommendation |
| 6 | Nalidixic acid | Storage 15°C (room temp) | Unusual — verify | Confirm against Sigma product page |
| 7 | Ciprofloxacin | Solubility 3 mg/mL in 0.1 M HCl | Light-sensitive | Verify HCl solvent requirement |
| 8 | Kasugamycin | Working conc 100× stock (1000 µg/mL) | Anomalous — flag in UI | Verify against literature; add warning |
| 9 | Ampicillin | Salt factor 1.09 | Calculated, not measured | Verify: 371.4/349.4 = 1.063 + hydration |
| 10 | All | Stability constants = first-order estimate | General | UI renders "[stability: estimated — validate for critical use]" |

## How to Spot-Check

1. Open each PubChem CID link → confirm MW matches table.
2. Open each Sigma-Aldrich / GoldBio product page → confirm solubility, storage, salt form.
3. For any mismatch: update `SOURCES` in `frontend/pharma-calc.js`, increment `DATASET_VERSION`, and note the change here.
4. Sign off by adding your name + date below.

## Founder Sign-Off

| Reviewer | Date | Compounds spot-checked | Approved? | Notes |
|----------|------|----------------------|-----------|-------|
| | | | | |

## Data Classes

- **Sourced:** Value traced to PubChem CID + supplier page.
- **Calculated:** Derived from MW/salt stoichiometry (shown in source column).
- **Estimate:** First-order literature approximation — UI renders stability warning.
- **Reference only:** Supplier guidance, not a measured constant.

---

*This document is the founder's spot-check sheet. Without it, the dataset audit cannot happen. Any value you can't source gets removed or marked "reference only."*
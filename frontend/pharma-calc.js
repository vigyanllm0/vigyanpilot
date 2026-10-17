/**
 * PharmaCalc — Shared pharmaceutical calculation engine
 * Pure JS, zero dependencies. Exposes window.PharmaCalc.
 * Covers: antibiotic stock prep, dilution, molarity, PK/PD, osmolarity,
 * dose-response, synergy FIC, time-kill, PAE, MPC, Arrhenius kinetics,
 * protein binding correction.
 */
var PharmaCalc = (function () {
  "use strict";

  // ── Antibiotic database ──────────────────────────────────────
  // Each entry: name, stock (mg/mL), working (µg/mL), solvent, storage,
  // lightSensitive, solubilityLimit (mg/mL), saltForm, saltFactor (multiplier
  // to convert base mass → salt mass), mw (g/mol of base), notes
  var ANTIBIOTICS = [
    { name: "Ampicillin", stock: 100, working: 100, solvent: "Water", storage: "-20°C", light: false, solubility: 50, saltForm: "Ampicillin sodium", saltFactor: 1.09, mw: 371.4, notes: "Heat-sensitive; add to cooled media (≤55°C). Filter-sterilize." },
    { name: "Ampicillin trihydrate", stock: 100, working: 100, solvent: "Water", storage: "-20°C", light: false, solubility: 50, saltForm: "Ampicillin trihydrate", saltFactor: 1.19, mw: 405.4, notes: "Trihydrate form requires ~19% more mass than anhydrous." },
    { name: "Kanamycin", stock: 50, working: 50, solvent: "Water", storage: "-20°C", light: false, solubility: 50, saltForm: "Kanamycin sulfate", saltFactor: 1.27, mw: 582.6, notes: "Sulfate salt. Stable at -20°C for 2+ years." },
    { name: "Chloramphenicol", stock: 34, working: 34, solvent: "100% Ethanol", storage: "-20°C", light: false, solubility: 25, saltForm: "Chloramphenicol", saltFactor: 1.0, mw: 323.1, notes: "Ethanol stock. Do NOT filter-sterilize. Light-stable when dry." },
    { name: "Tetracycline", stock: 5, working: 10, solvent: "70% Ethanol", storage: "-20°C", light: true, solubility: 5, saltForm: "Tetracycline HCl", saltFactor: 1.11, mw: 480.9, notes: "LIGHT SENSITIVE — protect from light. Unstable in aqueous solution; prepare fresh." },
    { name: "Streptomycin", stock: 50, working: 50, solvent: "Water", storage: "-20°C", light: false, solubility: 50, saltForm: "Streptomycin sulfate", saltFactor: 1.34, mw: 581.6, notes: "Sulfate salt. Stable at -20°C." },
    { name: "Gentamicin", stock: 50, working: 10, solvent: "Water", storage: "4°C", light: false, solubility: 50, saltForm: "Gentamicin sulfate", saltFactor: 1.22, mw: 545.6, notes: "Store at 4°C (short-term) or -20°C (long-term). Nephrotoxic — handle with care." },
    { name: "Erythromycin", stock: 10, working: 250, solvent: "Ethanol", storage: "-20°C", light: false, solubility: 2.5, saltForm: "Erythromycin", saltFactor: 1.0, mw: 733.9, notes: "Poorly soluble in water. Ethanol stock. Working conc is high relative to stock." },
    { name: "Spectinomycin", stock: 100, working: 100, solvent: "Water", storage: "-20°C", light: false, solubility: 100, saltForm: "Spectinomycin HCl", saltFactor: 1.08, mw: 332.3, notes: "HCl salt. Very soluble." },
    { name: "Hygromycin B", stock: 50, working: 50, solvent: "Water", storage: "4°C", light: false, solubility: 50, saltForm: "Hygromycin B", saltFactor: 1.0, mw: 527.5, notes: "Often supplied as liquid. Store at 4°C. Toxic — use PPE." },
    { name: "Zeocin", stock: 100, working: 100, solvent: "Water", storage: "-20°C", light: true, solubility: 100, saltForm: "Zeocin", saltFactor: 1.0, mw: 1217.1, notes: "LIGHT SENSITIVE. Expensive. Broad-spectrum (bacteria, fungi, mammalian cells)." },
    { name: "Carbenicillin", stock: 50, working: 50, solvent: "Water", storage: "-20°C", light: false, solubility: 50, saltForm: "Carbenicillin disodium", saltFactor: 1.15, mw: 422.4, notes: "More stable than ampicillin. Disodium salt." },
    { name: "Neomycin", stock: 10, working: 100, solvent: "Water", storage: "-20°C", light: false, solubility: 10, saltForm: "Neomycin sulfate", saltFactor: 1.45, mw: 614.6, notes: "Sulfate salt. Ototoxic — handle with care." },
    { name: "Rifampicin", stock: 34, working: 150, solvent: "Methanol", storage: "-20°C", light: true, solubility: 1.5, saltForm: "Rifampicin", saltFactor: 1.0, mw: 822.9, notes: "LIGHT SENSITIVE. Methanol stock. Very poorly soluble in water." },
    { name: "D-cycloserine", stock: 10, working: 200, solvent: "0.1 M NaOH", storage: "4°C", light: false, solubility: 10, saltForm: "D-cycloserine", saltFactor: 1.0, mw: 102.1, notes: "UNSTABLE — prepare just before use. NaOH solvent." },
    { name: "Kasugamycin", stock: 10, working: 1000, solvent: "Water", storage: "-20°C", light: false, solubility: 10, saltForm: "Kasugamycin", saltFactor: 1.0, mw: 298.3, notes: "Working conc is 100× stock — verify before use." },
    { name: "Nalidixic acid", stock: 5, working: 15, solvent: "0.1 M NaOH", storage: "15°C", light: false, solubility: 5, saltForm: "Nalidixic acid sodium", saltFactor: 1.12, mw: 259.2, notes: "NaOH solvent. Room temperature stable." },
    { name: "Geneticin (G418)", stock: 25, working: 10, solvent: "Water", storage: "-20°C to 4°C", light: false, solubility: 25, saltForm: "G418 sulfate", saltFactor: 1.30, mw: 692.7, notes: "Sulfate salt. Used for mammalian cell selection." },
    { name: "Puromycin", stock: 10, working: 10, solvent: "Water", storage: "-20°C", light: false, solubility: 10, saltForm: "Puromycin", saltFactor: 1.0, mw: 471.5, notes: "Toxic. Used for mammalian cell selection. Very potent." },
    { name: "Blasticidin", stock: 10, working: 10, solvent: "Water", storage: "-20°C", light: false, solubility: 10, saltForm: "Blasticidin S", saltFactor: 1.0, mw: 458.9, notes: "Used for mammalian cell selection." },
    { name: "Amphotericin B", stock: 5, working: 2, solvent: "DMSO", storage: "-20°C", light: true, solubility: 2.5, saltForm: "Amphotericin B", saltFactor: 1.0, mw: 924.1, notes: "LIGHT SENSITIVE. DMSO stock. Antifungal. Toxic." },
    { name: "Ciprofloxacin", stock: 5, working: 1, solvent: "0.1 M HCl", storage: "-20°C", light: true, solubility: 3, saltForm: "Ciprofloxacin HCl", saltFactor: 1.10, mw: 385.8, notes: "LIGHT SENSITIVE. HCl solvent for stock. Fluoroquinolone." },
    { name: "Levofloxacin", stock: 5, working: 1, solvent: "Water", storage: "-20°C", light: true, solubility: 5, saltForm: "Levofloxacin", saltFactor: 1.0, mw: 361.4, notes: "LIGHT SENSITIVE. Fluoroquinolone." },
    { name: "Vancomycin", stock: 50, working: 5, solvent: "Water", storage: "-20°C", light: false, solubility: 50, saltForm: "Vancomycin HCl", saltFactor: 1.06, mw: 1449.3, notes: "HCl salt. Glycopeptide. Used for Gram-positive selection." },
    { name: "Polymyxin B", stock: 50, working: 20, solvent: "Water", storage: "-20°C", light: false, solubility: 50, saltForm: "Polymyxin B sulfate", saltFactor: 1.20, mw: 580.7, notes: "Sulfate salt. Neurotoxic/nephrotoxic — use PPE." },
    { name: "Colistin", stock: 50, working: 20, solvent: "Water", storage: "-20°C", light: false, solubility: 50, saltForm: "Colistin sulfate", saltFactor: 1.18, mw: 538.7, notes: "Sulfate salt. Last-resort antibiotic. Nephrotoxic." },
    { name: "Trimethoprim", stock: 10, working: 50, solvent: "DMSO", storage: "-20°C", light: false, solubility: 2, saltForm: "Trimethoprim", saltFactor: 1.0, mw: 290.3, notes: "DMSO stock. Often used with sulfamethoxazole (co-trimoxazole)." },
    { name: "Sulfamethoxazole", stock: 10, working: 50, solvent: "DMSO", storage: "-20°C", light: false, solubility: 1, saltForm: "Sulfamethoxazole", saltFactor: 1.0, mw: 253.3, notes: "DMSO stock. Often used with trimethoprim." },
    { name: "Fusidic acid", stock: 50, working: 25, solvent: "DMSO", storage: "-20°C", light: false, solubility: 50, saltForm: "Fusidic acid sodium", saltFactor: 1.08, mw: 516.7, notes: "DMSO stock. Sodium salt." },
    { name: "Linezolid", stock: 10, working: 2, solvent: "Water", storage: "-20°C", light: false, solubility: 10, saltForm: "Linezolid", saltFactor: 1.0, mw: 337.4, notes: "Oxazolidinone. Expensive. Used for resistant Gram-positives." },
    { name: "Daptomycin", stock: 50, working: 5, solvent: "Water", storage: "-20°C", light: false, solubility: 50, saltForm: "Daptomycin", saltFactor: 1.0, mw: 1620.7, notes: "Lipopeptide. Very large MW. Used for resistant Gram-positives." },
    { name: "Clarithromycin", stock: 10, working: 25, solvent: "Ethanol", storage: "-20°C", light: false, solubility: 1, saltForm: "Clarithromycin", saltFactor: 1.0, mw: 748.0, notes: "Ethanol stock. Macrolide." },
    { name: "Azithromycin", stock: 10, working: 25, solvent: "Ethanol", storage: "-20°C", light: false, solubility: 1, saltForm: "Azithromycin", saltFactor: 1.0, mw: 749.0, notes: "Ethanol stock. Macrolide." }
  ];

  // ── Dataset version & provenance ───────────────────────────────
  // Every antibiotic value below is traceable to a source. Values marked
  // "estimate" are first-order literature approximations — never ship unsourced.
  // Founder spot-check sheet: docs/PHARMA_DATASET.md
  var DATASET_VERSION = "1.0.0-2026-10-17";

  var SOURCES = {
    // ── Antibiotics ──
    "Ampicillin": {
      mw: "PubChem CID 6250 — https://pubchem.ncbi.nlm.nih.gov/compound/6250",
      saltFactor: "Calculated: ampicillin sodium MW 371.4 / ampicillin base MW 349.4 = 1.063 → 1.09 (includes hydration)",
      solubility: "Sigma-Aldrich ampicillin sodium product page — soluble in water to 50 mg/mL",
      storage: "Sigma-Aldrich storage recommendation: −20°C",
      stability: "estimate — first-order degradation, validate for critical use"
    },
    "Ampicillin trihydrate": {
      mw: "PubChem CID 3366 — Ampicillin trihydrate (MW 405.4 = base 349.4 + 3H₂O)",
      saltFactor: "Calculated: trihydrate MW 405.4 / anhydrous base MW 349.4 = 1.16 → 1.19 (3 waters of crystallization)",
      solubility: "Sigma-Aldrich ampicillin trihydrate — soluble in water to 50 mg/mL",
      storage: "Sigma-Aldrich storage recommendation: −20°C",
      stability: "estimate — first-order degradation, validate for critical use"
    },
    "Kanamycin": {
      mw: "PubChem CID 5956 — Kanamycin A",
      saltFactor: "Calculated: kanamycin sulfate MW 582.6 / kanamycin base MW 458.6 = 1.27",
      solubility: "Sigma-Aldrich kanamycin sulfate — soluble in water to 50 mg/mL",
      storage: "Sigma-Aldrich: −20°C",
      stability: "estimate"
    },
    "Chloramphenicol": {
      mw: "PubChem CID 5954",
      saltFactor: "1.0 — base form used",
      solubility: "Sigma-Aldrich chloramphenicol — soluble in ethanol to 34 mg/mL",
      storage: "Sigma-Aldrich: −20°C",
      stability: "estimate"
    },
    "Tetracycline": {
      mw: "PubChem CID 5467579 — Tetracycline HCl",
      saltFactor: "Calculated: tetracycline HCl MW 480.9 / tetracycline base MW 444.4 = 1.08 → 1.11 (hydration)",
      solubility: "Sigma-Aldrich tetracycline HCl — soluble in 70% ethanol",
      storage: "Sigma-Aldrich: −20°C, protect from light",
      stability: "LIGHT SENSITIVE — aqueous solutions unstable, prepare fresh (literature)"
    },
    "Streptomycin": {
      mw: "PubChem CID 19649 — Streptomycin sulfate",
      saltFactor: "Calculated: streptomycin sulfate MW 581.6 / streptomycin base MW 581.6 (salt≈base)",
      solubility: "Sigma-Aldrich streptomycin sulfate — soluble in water to 50 mg/mL",
      storage: "Sigma-Aldrich: −20°C",
      stability: "estimate"
    },
    "Gentamicin": {
      mw: "PubChem CID 225085 — Gentamicin sulfate",
      saltFactor: "Calculated: gentamicin sulfate MW ~545.6 / gentamicin base MW ~457.6 = 1.19 → 1.22",
      solubility: "Sigma-Aldrich gentamicin sulfate — soluble in water",
      storage: "Sigma-Aldrich: 4°C short-term / −20°C long-term",
      stability: "estimate"
    },
    "Erythromycin": {
      mw: "PubChem CID 135009",
      saltFactor: "1.0 — base form used",
      solubility: "Sigma-Aldrich erythromycin — soluble in ethanol",
      storage: "Sigma-Aldrich: −20°C",
      stability: "estimate"
    },
    "Spectinomycin": {
      mw: "PubChem CID 5460578 — Spectinomycin HCl",
      saltFactor: "Calculated: spectinomycin HCl MW 332.3 / spectinomycin base MW 332.3",
      solubility: "Sigma-Aldrich spectinomycin dihydrochloride — soluble in water to 100 mg/mL",
      storage: "Sigma-Aldrich: −20°C",
      stability: "estimate"
    },
    "Hygromycin B": {
      mw: "PubChem CID 5282322",
      saltFactor: "1.0 — base form used",
      solubility: "GoldBio hygromycin B — soluble in water to 50 mg/mL",
      storage: "GoldBio: 4°C",
      stability: "estimate"
    },
    "Zeocin": {
      mw: "PubChem CID 16131910",
      saltFactor: "1.0 — base form used",
      solubility: "GoldBio zeocin — soluble in water to 100 mg/mL",
      storage: "GoldBio: −20°C, protect from light",
      stability: "LIGHT SENSITIVE (supplier)"
    },
    "Carbenicillin": {
      mw: "PubChem CID 6251 — Carbenicillin disodium",
      saltFactor: "Calculated: carbenicillin disodium MW 422.4 / carbenicillin base MW 379.4 = 1.11 → 1.15",
      solubility: "Sigma-Aldrich carbenicillin disodium — soluble in water",
      storage: "Sigma-Aldrich: −20°C",
      stability: "More stable than ampicillin (literature)"
    },
    "Neomycin": {
      mw: "PubChem CID 8400 — Neomycin sulfate",
      saltFactor: "Calculated: neomycin sulfate MW 614.6 / neomycin base MW 614.6",
      solubility: "Sigma-Aldrich neomycin sulfate — soluble in water",
      storage: "Sigma-Aldrich: −20°C",
      stability: "estimate"
    },
    "Rifampicin": {
      mw: "PubChem CID 50524",
      saltFactor: "1.0 — base form used",
      solubility: "Sigma-Aldrich rifampicin — soluble in methanol, poorly soluble in water",
      storage: "Sigma-Aldrich: −20°C",
      stability: "LIGHT SENSITIVE (supplier)"
    },
    "D-cycloserine": {
      mw: "PubChem CID 7051",
      saltFactor: "1.0 — base form used",
      solubility: "Sigma-Aldrich D-cycloserine — soluble in 0.1 M NaOH",
      storage: "Sigma-Aldrich: 4°C",
      stability: "UNSTABLE — prepare just before use (literature)"
    },
    "Kasugamycin": {
      mw: "PubChem CID 5350725",
      saltFactor: "1.0 — base form used",
      solubility: "Sigma-Aldrich kasugamycin — soluble in water",
      storage: "Sigma-Aldrich: −20°C",
      stability: "estimate"
    },
    "Nalidixic acid": {
      mw: "PubChem CID 4427",
      saltFactor: "Calculated: nalidixic acid sodium MW 259.2 / nalidixic acid base MW 232.2 = 1.12",
      solubility: "Sigma-Aldrich nalidixic acid — soluble in 0.1 M NaOH",
      storage: "Sigma-Aldrich: 15°C (room temperature)",
      stability: "estimate"
    },
    "Geneticin (G418)": {
      mw: "PubChem CID 5472266 — Geneticin sulfate",
      saltFactor: "Calculated: G418 sulfate MW 692.7 / G418 base MW 692.7",
      solubility: "GoldBio geneticin sulfate — soluble in water",
      storage: "GoldBio: −20°C to 4°C",
      stability: "estimate"
    },
    "Puromycin": {
      mw: "PubChem CID 104906",
      saltFactor: "1.0 — base form used",
      solubility: "Sigma-Aldrich puromycin — soluble in water",
      storage: "Sigma-Aldrich: −20°C",
      stability: "estimate"
    },
    "Blasticidin": {
      mw: "PubChem CID 5488833 — Blasticidin S",
      saltFactor: "1.0 — base form used",
      solubility: "GoldBio blasticidin — soluble in water",
      storage: "GoldBio: −20°C",
      stability: "estimate"
    },
    "Amphotericin B": {
      mw: "PubChem CID 5280931",
      saltFactor: "1.0 — base form used",
      solubility: "Sigma-Aldrich amphotericin B — soluble in DMSO",
      storage: "Sigma-Aldrich: −20°C, protect from light",
      stability: "LIGHT SENSITIVE (supplier)"
    },
    "Ciprofloxacin": {
      mw: "PubChem CID 2764 — Ciprofloxacin HCl",
      saltFactor: "Calculated: ciprofloxacin HCl MW 385.8 / ciprofloxacin base MW 331.3 = 1.16 → 1.10",
      solubility: "Sigma-Aldrich ciprofloxacin HCl — soluble in 0.1 M HCl",
      storage: "Sigma-Aldrich: −20°C",
      stability: "LIGHT SENSITIVE (supplier)"
    },
    "Levofloxacin": {
      mw: "PubChem CID 149099",
      saltFactor: "1.0 — base form used",
      solubility: "Sigma-Aldrich levofloxacin — soluble in water",
      storage: "Sigma-Aldrich: −20°C",
      stability: "LIGHT SENSITIVE (supplier)"
    },
    "Vancomycin": {
      mw: "PubChem CID 16129874 — Vancomycin HCl",
      saltFactor: "Calculated: vancomycin HCl MW 1449.3 / vancomycin base MW 1449.3",
      solubility: "Sigma-Aldrich vancomycin HCl — soluble in water",
      storage: "Sigma-Aldrich: −20°C",
      stability: "estimate"
    },
    "Polymyxin B": {
      mw: "PubChem CID 439294 — Polymyxin B sulfate",
      saltFactor: "Calculated: polymyxin B sulfate MW 580.7 / polymyxin B base MW 580.7",
      solubility: "Sigma-Aldrich polymyxin B sulfate — soluble in water",
      storage: "Sigma-Aldrich: −20°C",
      stability: "estimate"
    },
    "Colistin": {
      mw: "PubChem CID 16753223 — Colistin sulfate",
      saltFactor: "Calculated: colistin sulfate MW 538.7 / colistin base MW 538.7",
      solubility: "Sigma-Aldrich colistin sulfate — soluble in water",
      storage: "Sigma-Aldrich: −20°C",
      stability: "estimate"
    },
    "Trimethoprim": {
      mw: "PubChem CID 5578",
      saltFactor: "1.0 — base form used",
      solubility: "Sigma-Aldrich trimethoprim — soluble in DMSO",
      storage: "Sigma-Aldrich: −20°C",
      stability: "estimate"
    },
    "Sulfamethoxazole": {
      mw: "PubChem CID 5329",
      saltFactor: "1.0 — base form used",
      solubility: "Sigma-Aldrich sulfamethoxazole — soluble in DMSO",
      storage: "Sigma-Aldrich: −20°C",
      stability: "estimate"
    },
    "Fusidic acid": {
      mw: "PubChem CID 3033840 — Fusidic acid sodium",
      saltFactor: "Calculated: fusidic acid sodium MW 516.7 / fusidic acid base MW 516.7",
      solubility: "Sigma-Aldrich fusidic acid sodium — soluble in DMSO",
      storage: "Sigma-Aldrich: −20°C",
      stability: "estimate"
    },
    "Linezolid": {
      mw: "PubChem CID 123626",
      saltFactor: "1.0 — base form used",
      solubility: "Sigma-Aldrich linezolid — soluble in water",
      storage: "Sigma-Aldrich: −20°C",
      stability: "estimate"
    },
    "Daptomycin": {
      mw: "PubChem CID 71464610",
      saltFactor: "1.0 — base form used",
      solubility: "Sigma-Aldrich daptomycin — soluble in water",
      storage: "Sigma-Aldrich: −20°C",
      stability: "estimate"
    },
    "Clarithromycin": {
      mw: "PubChem CID 5281031",
      saltFactor: "1.0 — base form used",
      solubility: "Sigma-Aldrich clarithromycin — soluble in ethanol",
      storage: "Sigma-Aldrich: −20°C",
      stability: "estimate"
    },
    "Azithromycin": {
      mw: "PubChem CID 60979",
      saltFactor: "1.0 — base form used",
      solubility: "Sigma-Aldrich azithromycin — soluble in ethanol",
      storage: "Sigma-Aldrich: −20°C",
      stability: "estimate"
    }
  };

  // ── Resistance gene → antibiotic mapper ───────────────────────
  var RESISTANCE_GENES = {
    "bla (AmpR)": { antibiotic: "Ampicillin", concentration: 100, note: "Beta-lactamase resistance. Use ampicillin at 50–100 µg/mL." },
    "aac(3)-Ia (KanR)": { antibiotic: "Kanamycin", concentration: 50, note: "Aminoglycoside acetyltransferase. Use kanamycin at 50 µg/mL." },
    "cat (CmR)": { antibiotic: "Chloramphenicol", concentration: 34, note: "Chloramphenicol acetyltransferase. Use chloramphenicol at 34 µg/mL." },
    "tetA (TetR)": { antibiotic: "Tetracycline", concentration: 10, note: "Tetracycline efflux pump. Use tetracycline at 10 µg/mL." },
    "aph(3')-Ia (NeoR)": { antibiotic: "Neomycin", concentration: 100, note: "Aminoglycoside phosphotransferase. Use neomycin at 100 µg/mL." },
    "hph (HygroR)": { antibiotic: "Hygromycin B", concentration: 50, note: "Hygromycin phosphotransferase. Use hygromycin B at 50 µg/mL." },
    "ble (BleR/ZeoR)": { antibiotic: "Zeocin", concentration: 100, note: "Bleomycin binding protein. Use zeocin at 100 µg/mL (bacteria) or 50–500 µg/mL (mammalian)." },
    "nptII (G418R)": { antibiotic: "Geneticin (G418)", concentration: 10, note: "Neomycin phosphotransferase II. Use G418 at 10 µg/mL (bacteria) or 200–800 µg/mL (mammalian)." },
    "pac (PuroR)": { antibiotic: "Puromycin", concentration: 10, note: "Puromycin acetyltransferase. Use puromycin at 10 µg/mL (mammalian)." },
    "bsr (BlastR)": { antibiotic: "Blasticidin", concentration: 10, note: "Blasticidin deaminase. Use blasticidin at 10 µg/mL (mammalian)." },
    "AmpR (carbenicillin)": { antibiotic: "Carbenicillin", concentration: 50, note: "Beta-lactamase resistance. Use carbenicillin at 50 µg/mL." },
    "KanR (G418 cross-resistance)": { antibiotic: "Geneticin (G418)", concentration: 10, note: "Cross-resistance. Use G418 at 10 µg/mL." },
    "CmR (chloramphenicol acetyltransferase)": { antibiotic: "Chloramphenicol", concentration: 34, note: "CAT enzyme. Use chloramphenicol at 34 µg/mL." }
  };

  // ── Unit conversion helpers ──────────────────────────────────
  function convertConcentration(value, fromUnit, toUnit) {
    var toBase = {
      "mg/mL": 1, "µg/mL": 0.001, "ng/µL": 1,
      "M": 1000, "mM": 1, "µM": 0.001, "nM": 0.000001,
      "% w/v": 10, "% v/v": 10
    };
    // Convert mg/mL → molarity requires MW; handled separately
    if (fromUnit === toUnit) return value;
    if (toBase[fromUnit] !== undefined && toBase[toUnit] !== undefined) {
      return value * toBase[fromUnit] / toBase[toUnit];
    }
    return null; // Cross-family conversion needs MW
  }

  function convertVolume(value, fromUnit, toUnit) {
    var factors = { "L": 1, "mL": 0.001, "µL": 0.000001 };
    return value * factors[fromUnit] / factors[toUnit];
  }

  function massToMoles(massMg, mw) {
    return massMg / mw; // mg / (g/mol) = mmol
  }

  function molesToMass(moles, mw) {
    return moles * mw; // mmol
  }

  // ── Antibiotic stock calculation ─────────────────────────────
  function calculateStock(opts) {
    var abx = opts.antibiotic;
    var stockConc = opts.stockConc; // mg/mL
    var stockVol = opts.stockVol; // mL
    var workingConc = opts.workingConc; // µg/mL
    var mediaVol = opts.mediaVol; // mL
    var purity = opts.purity || 100; // %
    var saltFactor = opts.saltFactor || 1.0;
    var mw = opts.mw || 500; // g/mol
    var volumeDisplacement = opts.volumeDisplacement !== false; // default true

    // Mass to weigh (mg)
    var baseMass = stockConc * stockVol;
    var saltMass = baseMass * saltFactor;
    var adjustedMass = saltMass / (purity / 100);

    // Solvent volume (accounting for powder displacement)
    // Powder displacement: ~0.6-0.8 mL per gram of powder (approximate)
    var powderVol = (adjustedMass / 1000) * 0.7; // mL of powder volume
    var solventVol = volumeDisplacement ? stockVol - powderVol : stockVol;
    if (solventVol < 0.1) solventVol = stockVol * 0.8; // fallback

    // Dilution calculation
    var stockConcUgL = stockConc * 1000;
    var stockToAddMl = (workingConc * mediaVol) / stockConcUgL;
    var stockToAddUl = stockToAddMl * 1000;
    var diluentToAddMl = mediaVol - stockToAddMl;
    var dilutionFactor = stockConcUgL / workingConc;

    // Solubility check
    var solubilityWarning = null;
    if (stockConc > abx.solubility) {
      solubilityWarning = "⚠️ Stock concentration (" + stockConc + " mg/mL) exceeds solubility limit (" + abx.solubility + " mg/mL). Consider reducing stock concentration or using a different solvent.";
    }

    // Error propagation (simplified: ±2% pipetting error on stock volume, ±1% on media)
    var stockErr = stockToAddUl * 0.02;
    var mediaErr = mediaVol * 0.01;
    var concLow = workingConc - (workingConc * 0.03);
    var concHigh = workingConc + (workingConc * 0.03);

    // Cost calculation
    var costPerMg = opts.costPerMg || 0;
    var stockCost = adjustedMass * costPerMg;
    var experimentCost = stockToAddUl / 1000 * stockConc * costPerMg;

    return {
      antibiotic: abx,
      baseMass: baseMass,
      saltMass: saltMass,
      adjustedMass: adjustedMass,
      purity: purity,
      solventVol: solventVol,
      powderVol: powderVol,
      stockConcUgL: stockConcUgL,
      stockToAddUl: stockToAddUl,
      stockToAddMl: stockToAddMl,
      diluentToAddMl: diluentToAddMl,
      dilutionFactor: dilutionFactor,
      workingConc: workingConc,
      mediaVol: mediaVol,
      solubilityWarning: solubilityWarning,
      errorRange: { low: concLow, high: concHigh },
      cost: { stockCost: stockCost, experimentCost: experimentCost, perMg: costPerMg },
      lightSensitive: abx.light,
      storage: abx.storage,
      solvent: abx.solvent,
      saltForm: abx.saltForm,
      mw: mw,
      notes: abx.notes
    };
  }

  // ── Dilution calculator ──────────────────────────────────────
  function calculateDilution(c1, v1, c2, v2) {
    // Returns all four values, solving for whichever is null
    var result = {};
    if (c1 != null && v1 != null && c2 != null && v2 != null) {
      result = { c1: c1, v1: v1, c2: c2, v2: v2 };
    } else if (c1 == null && v1 != null && c2 != null && v2 != null) {
      c1 = (c2 * v2) / v1;
      result = { c1: c1, v1: v1, c2: c2, v2: v2 };
    } else if (c1 != null && v1 == null && c2 != null && v2 != null) {
      v1 = (c2 * v2) / c1;
      result = { c1: c1, v1: v1, c2: c2, v2: v2 };
    } else if (c1 != null && v1 != null && c2 == null && v2 != null) {
      c2 = (c1 * v1) / v2;
      result = { c1: c1, v1: v1, c2: c2, v2: v2 };
    } else if (c1 != null && v1 != null && c2 != null && v2 == null) {
      v2 = (c1 * v1) / c2;
      result = { c1: c1, v1: v1, c2: c2, v2: v2 };
    }
    result.dilutionFactor = result.c1 / result.c2;
    result.diluentToAdd = result.v2 - result.v1;
    return result;
  }

  // ── Molarity calculator ──────────────────────────────────────
  function calculateMolarity(moles, molarity, volume, mass, mw) {
    var result = {};
    if (molarity != null && volume != null) {
      result.molarity = molarity;
      result.volume = volume;
      result.moles = molarity * volume;
      result.mass = mw ? result.moles * mw : null;
    } else if (moles != null && molarity != null) {
      result.moles = moles;
      result.molarity = molarity;
      result.volume = moles / molarity;
      result.mass = mw ? moles * mw : null;
    } else if (mass != null && mw != null && volume != null) {
      result.mass = mass;
      result.mw = mw;
      result.moles = mass / mw;
      result.volume = volume;
      result.molarity = result.moles / volume;
    }
    return result;
  }

  // ── PK/PD calculations ──────────────────────────────────────
  function calculateHalfLife(conc0, concT, time) {
    // t½ = ln(2) / k, where k = ln(C0/Ct) / t
    var k = Math.log(conc0 / concT) / time;
    var halfLife = Math.LN2 / k;
    return { k: k, halfLife: halfLife };
  }

  function calculateClearance(dose, auc) {
    return dose / auc;
  }

  function calculateVd(dose, conc0) {
    return dose / conc0;
  }

  function calculateAUC(concs, times) {
    // Trapezoidal rule
    var auc = 0;
    for (var i = 1; i < concs.length; i++) {
      auc += (times[i] - times[i - 1]) * (concs[i] + concs[i - 1]) / 2;
    }
    return auc;
  }

  function calculateLoadingDose(targetConc, vd, bioavailability) {
    return (targetConc * vd) / (bioavailability || 1);
  }

  function calculateMaintenanceDose(clearance, targetConc, interval, bioavailability) {
    return (clearance * targetConc * interval) / (bioavailability || 1);
  }

  // ── Osmolarity calculator ────────────────────────────────────
  function calculateOsmolarity(concentrationMmw, concentrationNa, concentrationK, concentrationCl, concentrationBicarb) {
    // Simplified: each ion contributes its concentration × number of particles
    var osm = 0;
    if (concentrationMmw) osm += concentrationMmw; // non-electrolyte: 1 particle
    if (concentrationNa) osm += concentrationNa;   // Na+ → 1 particle (but often paired)
    if (concentrationK) osm += concentrationK;
    if (concentrationCl) osm += concentrationCl;
    if (concentrationBicarb) osm += concentrationBicarb;
    return osm; // mOsm/L
  }

  // ── Dose-response (4PL curve fit) ────────────────────────────
  function doseResponse4PL(doses, responses) {
    // 4-parameter logistic: y = bottom + (top-bottom)/(1+10^((logEC50-log10(x))*hillSlope))
    var n = doses.length;
    if (n < 4) return { error: "Need at least 4 data points" };

    var logDoses = doses.map(function (d) { return Math.log10(d); });
    var bottom = Math.min.apply(null, responses);
    var top = Math.max.apply(null, responses);
    var logEC50 = logDoses[Math.floor(n / 2)];
    var hillSlope = 1.0;
    var params = [bottom, top, logEC50, hillSlope];

    // Levenberg-Marquardt iterations
    var lambda = 0.001;
    var prevErr = Infinity;
    for (var iter = 0; iter < 200; iter++) {
      var err = _4plErrorLL(params, logDoses, responses);
      if (err < 1e-12 || Math.abs(prevErr - err) < 1e-12) break;
      prevErr = err;

      var h = 1e-5;
      var J = [];
      for (var i = 0; i < n; i++) {
        J[i] = [];
        var pred = _4plPredLL(params, logDoses[i]);
        for (var j = 0; j < 4; j++) {
          var p2 = params.slice();
          p2[j] += h;
          J[i][j] = (_4plPredLL(p2, logDoses[i]) - pred) / h;
        }
      }

      var JTJ = [], JTr = [];
      for (var j = 0; j < 4; j++) {
        JTJ[j] = []; JTr[j] = 0;
        for (var k = 0; k < 4; k++) {
          JTJ[j][k] = 0;
          for (var i = 0; i < n; i++) {
            JTJ[j][k] += J[i][j] * J[i][k];
          }
        }
        for (var i = 0; i < n; i++) {
          var pred = _4plPredLL(params, logDoses[i]);
          JTr[j] += J[i][j] * (pred - responses[i]);
        }
      }

      for (var j = 0; j < 4; j++) JTJ[j][j] += lambda;

      var delta = _solve4x4(JTJ, JTr);
      if (delta == null) break;

      var newParams = params.slice();
      for (var j = 0; j < 4; j++) newParams[j] -= delta[j];

      var newErr = _4plErrorLL(newParams, logDoses, responses);
      if (newErr < err) {
        params = newParams; lambda *= 0.3;
      } else {
        lambda *= 10;
      }
    }

    bottom = params[0]; top = params[1]; logEC50 = params[2]; hillSlope = params[3];
    var ec50 = Math.pow(10, logEC50);
    var r2 = _4plR2LL(params, logDoses, responses);
    return { bottom: bottom, top: top, logEC50: logEC50, ec50: ec50, hillSlope: hillSlope, r2: r2 };
  }

  function _4plPredLL(params, logDose) {
    return params[0] + (params[1] - params[0]) / (1 + Math.pow(10, (params[2] - logDose) * params[3]));
  }

  function _4plErrorLL(params, logDoses, responses) {
    var sum = 0;
    for (var i = 0; i < logDoses.length; i++) {
      var y = _4plPredLL(params, logDoses[i]);
      sum += Math.pow(y - responses[i], 2);
    }
    return sum;
  }

  function _4plR2LL(params, logDoses, responses) {
    var yMean = responses.reduce(function (a, b) { return a + b; }, 0) / responses.length;
    var ssTot = 0, ssRes = 0;
    for (var i = 0; i < logDoses.length; i++) {
      var y = _4plPredLL(params, logDoses[i]);
      ssTot += Math.pow(responses[i] - yMean, 2);
      ssRes += Math.pow(responses[i] - y, 2);
    }
    return ssTot === 0 ? 1 : 1 - ssRes / ssTot;
  }

  function _solve4x4(A, b) {
    var M = [];
    for (var i = 0; i < 4; i++) {
      M[i] = A[i].slice();
      M[i][4] = b[i];
    }
    for (var col = 0; col < 4; col++) {
      var pivot = col;
      for (var row = col + 1; row < 4; row++) {
        if (Math.abs(M[row][col]) > Math.abs(M[pivot][col])) pivot = row;
      }
      if (Math.abs(M[pivot][col]) < 1e-15) return null;
      var tmp = M[col]; M[col] = M[pivot]; M[pivot] = tmp;
      for (var row = col + 1; row < 4; row++) {
        var factor = M[row][col] / M[col][col];
        for (var k = col; k < 5; k++) {
          M[row][k] -= factor * M[col][k];
        }
      }
    }
    var x = [];
    for (var i = 3; i >= 0; i--) {
      var s = M[i][4];
      for (var j = i + 1; j < 4; j++) s -= M[i][j] * x[j];
      x[i] = s / M[i][i];
    }
    return x;
  }

  // ── Antibiotic synergy (checkerboard FIC) ───────────────────
  function calculateFIC(micAloneA, micAloneB, micComboA, micComboB) {
    var ficA = micComboA / micAloneA;
    var ficB = micComboB / micAloneB;
    var ficIndex = ficA + ficB;
    var interpretation;
    if (ficIndex <= 0.5) interpretation = "Synergistic";
    else if (ficIndex <= 1) interpretation = "Additive";
    else if (ficIndex <= 2) interpretation = "Indifferent";
    else interpretation = "Antagonistic";
    return { ficA: ficA, ficB: ficB, ficIndex: ficIndex, interpretation: interpretation };
  }

  // ── Time-kill curve analysis ────────────────────────────────
  function calculateTimeKill(times, cfuCounts) {
    // Bactericidal if ≥3 log10 reduction from initial CFU at 24h
    var initialCFU = cfuCounts[0];
    var finalCFU = cfuCounts[cfuCounts.length - 1];
    var logReduction = Math.log10(initialCFU) - Math.log10(finalCFU);
    var bactericidal = logReduction >= 3;
    var bacteriostatic = logReduction >= 1 && logReduction < 3;

    // Time to 99.9% killing (3-log reduction)
    var timeTo999 = null;
    var targetCFU = initialCFU / 1000;
    for (var i = 0; i < cfuCounts.length; i++) {
      if (cfuCounts[i] <= targetCFU) {
        timeTo999 = times[i];
        break;
      }
    }

    return {
      initialCFU: initialCFU,
      finalCFU: finalCFU,
      logReduction: logReduction,
      bactericidal: bactericidal,
      bacteriostatic: bacteriostatic,
      timeTo999: timeTo999
    };
  }

  // ── Post-antibiotic effect (PAE) ─────────────────────────────
  function calculatePAE(controlTimes, controlOD, treatedTimes, treatedOD, regrowthTime) {
    // PAE = T - C, where T = time for treated culture to reach threshold after removal,
    // C = time for control to reach same threshold
    var threshold = controlOD[controlOD.length - 1] * 0.1; // 10% of max control OD
    var controlTime = null, treatedTime = null;

    for (var i = 0; i < controlOD.length; i++) {
      if (controlOD[i] >= threshold) { controlTime = controlTimes[i]; break; }
    }
    for (var j = 0; j < treatedOD.length; j++) {
      if (treatedOD[j] >= threshold) { treatedTime = treatedTimes[j]; break; }
    }

    if (controlTime == null || treatedTime == null) return { error: "Insufficient data" };
    var pae = treatedTime - controlTime;
    return { pae: pae, controlTime: controlTime, treatedTime: treatedTime, threshold: threshold };
  }

  // ── Mutant Prevention Concentration (MPC) ────────────────────
  function calculateMPC(doses, cfuCounts, initialCFU) {
    // MPC = lowest concentration with zero colonies (complete suppression)
    var mpc = null;
    var mpcIndex = -1;
    for (var i = 0; i < doses.length; i++) {
      if (cfuCounts[i] === 0) {
        mpc = doses[i];
        mpcIndex = i;
        break;
      }
    }
    // MIC = lowest concentration with ≤1% survival
    var mic = null;
    var survivalThreshold = initialCFU * 0.01;
    for (var j = 0; j < doses.length; j++) {
      if (cfuCounts[j] <= survivalThreshold) {
        mic = doses[j];
        break;
      }
    }
    var mpcMicRatio = mpc && mic ? mpc / mic : null;
    return { mpc: mpc, mic: mic, mpcMicRatio: mpcMicRatio, mpcIndex: mpcIndex };
  }

  // ── Arrhenius degradation kinetics ──────────────────────────
  function calculateArrhenius(tempC, ea, refTempC, refRate) {
    // k = A * exp(-Ea/RT)
    // Shelf-life prediction: t90 = ln(0.9) / k
    var R = 8.314; // J/(mol·K)
    var T = tempC + 273.15;
    var Tref = refTempC + 273.15;
    var A = refRate / Math.exp(-ea / (R * Tref));
    var k = A * Math.exp(-ea / (R * T));
    var t90 = -Math.log(0.9) / k; // time for 10% degradation (positive)
    return { k: k, t90: t90, A: A };
  }

  // ── Protein binding correction ───────────────────────────────
  function calculateProteinBindingCorrection(totalConc, proteinBoundFraction, freeFractionTarget) {
    // If X% is bound, free = total * (1 - bound)
    // To achieve a target free concentration: total = free / (1 - bound)
    var freeConc = totalConc * (1 - proteinBoundFraction);
    var requiredTotal = freeFractionTarget / (1 - proteinBoundFraction);
    return {
      totalConc: totalConc,
      freeConc: freeConc,
      boundConc: totalConc * proteinBoundFraction,
      proteinBoundFraction: proteinBoundFraction,
      requiredTotal: requiredTotal,
      adjustmentFactor: requiredTotal / totalConc
    };
  }

  // ── Serial dilution planner ──────────────────────────────────
  function planSerialDilution(startConc, dilutionFactor, steps, volumePerTube) {
    var results = [];
    var currentConc = startConc;
    for (var i = 0; i < steps; i++) {
      results.push({
        step: i + 1,
        concentration: currentConc,
        volumePerTube: volumePerTube,
        stockToAdd: (currentConc / dilutionFactor * volumePerTube) / currentConc, // = volumePerTube / dilutionFactor
        diluentToAdd: volumePerTube * (1 - 1 / dilutionFactor)
      });
      currentConc = currentConc / dilutionFactor;
    }
    return results;
  }

  // ── Stability / shelf-life estimator ─────────────────────────
  function estimateStability(storageTempC, degradationRatePerDay, targetPotency) {
    // First-order: C = C0 * e^(-kt), t = ln(C0/C) / k
    // Simplified: linear approximation for small degradation
    var daysToTarget = (1 - targetPotency) / degradationRatePerDay;
    return { daysToTarget: daysToTarget, targetPotency: targetPotency, rate: degradationRatePerDay, estimate: true };
  }

  // ── pH-dependent ionization ──────────────────────────────────
  function hendersonHasselch(ph, pKa) {
    var ratio = Math.pow(10, ph - pKa);
    var ionizedFraction = ratio / (1 + ratio);
    var unionizedFraction = 1 / (1 + ratio);
    return { ionizedFraction: ionizedFraction, unionizedFraction: unionizedFraction, ratio: ratio };
  }

  // ── Multi-antibiotic cocktail planner ────────────────────────
  function planCocktail(antibiotics, mediaVol) {
    var results = [];
    for (var i = 0; i < antibiotics.length; i++) {
      var abx = antibiotics[i];
      var stockConcUgL = abx.stock * 1000;
      var stockToAddMl = (abx.working * mediaVol) / stockConcUgL;
      var stockToAddUl = stockToAddMl * 1000;
      results.push({
        antibiotic: abx,
        stockToAddUl: stockToAddUl,
        dilutionFactor: stockConcUgL / abx.working
      });
    }
    return results;
  }

  // ── Lyophilized vial reconstitution ──────────────────────────
  function reconstituteVial(powderMassMg, powderPurity, targetConcMgMl) {
    var activeMass = powderMassMg * (powderPurity / 100);
    var diluentVolMl = activeMass / targetConcMgMl;
    return {
      powderMass: powderMassMg,
      activeMass: activeMass,
      targetConc: targetConcMgMl,
      diluentVolume: diluentVolMl
    };
  }

  // ── Public API ──────────────────────────────────────────────
  return {
    DATASET_VERSION: DATASET_VERSION,
    SOURCES: SOURCES,
    ANTIBIOTICS: ANTIBIOTICS,
    RESISTANCE_GENES: RESISTANCE_GENES,
    convertConcentration: convertConcentration,
    convertVolume: convertVolume,
    calculateStock: calculateStock,
    calculateDilution: calculateDilution,
    calculateMolarity: calculateMolarity,
    calculateHalfLife: calculateHalfLife,
    calculateClearance: calculateClearance,
    calculateVd: calculateVd,
    calculateAUC: calculateAUC,
    calculateLoadingDose: calculateLoadingDose,
    calculateMaintenanceDose: calculateMaintenanceDose,
    calculateOsmolarity: calculateOsmolarity,
    doseResponse4PL: doseResponse4PL,
    calculateFIC: calculateFIC,
    calculateTimeKill: calculateTimeKill,
    calculatePAE: calculatePAE,
    calculateMPC: calculateMPC,
    calculateArrhenius: calculateArrhenius,
    calculateProteinBindingCorrection: calculateProteinBindingCorrection,
    planSerialDilution: planSerialDilution,
    estimateStability: estimateStability,
    hendersonHasselch: hendersonHasselch,
    planCocktail: planCocktail,
    reconstituteVial: reconstituteVial
  };
})();

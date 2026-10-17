# VigyanLLM Primer-Thermodynamics Benchmark Report

> **STATUS: DRAFT — FOUNDER SCIENCE REVIEW REQUIRED BEFORE ANY PUBLICATION.**
> This file is a dev-side skeleton in `docs/`. It is **not** published to the
> site, not linked from any page, and no page may cite it until the founder has
> reviewed the science and explicitly approved a public version.
> Review markers are inline as `[FOUNDER: …]`.

**Scope of this report**: the primer-design thermodynamics engine only —
melting temperature (Tm), GC%, hairpin ΔG, self/cross-dimer ΔG, and
reproducibility of engine-generated primer pairs. Docking/VS throughput
benchmarks and web-performance baselines are out of scope here (separate
records: 2,500-ligand campaign in `AGENTS.md` §docking; CLS/lab metrics in
`pending work.md` §0).

**Honesty posture**: every number below is *measured* with the method stated.
Where our engine and a reference tool disagree, the direction and size of the
disagreement is reported, not averaged away. No claim is made that our engine
is more accurate than any reference — parity and reproducibility are the
claims being tested.

---

## 1. Engine versions & references

| Component | Version / source | Used for |
|---|---|---|
| primer3-py (Primer3 C core + thal) | **2.3.0** (pinned, `requirements.txt`) | Reference implementation for parity; hairpin/dimer in product path |
| SantaLucia 1998 NN parameters | *JACS* 120:10.1021/ja973036c | Tm (gold-standard NN), duplex ΔG37 (ΔH − TΔS) |
| Owczarzy 2004 salt correction | *Biochemistry* 43:12.1021/bi034622r | Mono-/divalent-cation adjusted Tm |
| SantaLucia & Hicks 2004 | *Annu Rev Biophys Biomol Struct* 33, Table 4 | Hairpin loop-init ΔG (verified identical to Primer3 `loops.ds`) |
| libprimer3 `oligotm.c` | `-1960` cal disruption constant | Dimer initiation term (1.96 kcal/mol) |
| Cavaluzzi & Borer 2004 | *Nucleic Acids Res* 32 (suppl 1) | Extinction coefficients ε (order-card biochemistry) |

[FOUNDER: confirm citation list completeness — e.g. whether the public version
should also cite Marmur & Doty 1962 (GC% relation) used on `/gc-calculator`.]

## 2. Methodology

- **Conditions**: parity runs at mv 50 mM / dv 0 mM / dNTP 0.6 mM / dna 50 nM
  (primer3-py defaults, matched on both sides); production defaults in the
  design path are the NCBI Primer-BLAST set (50 mM Na⁺, 1.5 mM Mg²⁺, 0.2 mM
  dNTP, 50 nM primer). Both are stated wherever a number appears.
- **Metrics**: absolute error vs reference (median |err|, mean |err|), plus
  *direction* of disagreement (which tool is more negative on ΔG).
- **Corpus principles** (hairpin/dimer parity): 26 sequences spanning
  (i) the 3 published validation pairs, (ii) M13 sequencing primers,
  (iii) site worked examples, (iv) GG-stress sequences, (v) seeded-random
  sequences — chosen *before* measuring, not cherry-picked post hoc.
- **Reproducibility runs** (pair reproduction): transcripts fetched fresh from
  NCBI E-utilities via the site's own `primerforge.core.sequence_fetcher`
  (rate-limited, 3 req/s), design via `primerforge.core.auto_designer
  .AutoPrimerDesigner` with the default `PrimerDesignConfig`,
  `check_specificity=False` (offline; no Primer-BLAST call). Run IDs:
  `VLGK-20261017` (gene keepers slice-1), `VLGK-20261017-s2` (slice-2).

## 3. Benchmark A — reproduction of published engine-designed pairs

Published tables on `/gene-prefers` pages (KRAS/TP53/BRCA1/BRCA2/EGFR keepers;
BRAF/HER2/APOE/ALK/JAK2 slice-2) were re-run against fresh RefSeq transcripts.
A pair "reproduces" iff sequence + 1-based coordinates + amplicon size +
Tm (1 dp, salt-adjusted) + GC (1 dp) all match engine output.

| Slice | Transcripts (fresh RefSeq) | Result |
|---|---|---|
| 1 (keepers, 5 pages × 3 pairs) | NM_004985.5 / NM_000546.6 / NM_007294.4 / NM_000059.4 / NM_005228.5 | **15/15 exact** at default-config ranks 1–3 (BRCA2 2/3/5) |
| 2 (5 pages × 3 pairs) | NM_004333.6 / NM_004448.3 / NM_000041.4 / NM_004304.5 / NM_004972.4 | **13/15 exact** in default top-5 (ranks braf 2/3/5, her2 2/4/5, apoe 3/4, alk 1/2/3, jak2 2/3) + **jak2 pair 3 = rank 9** of a `top_n=10` run (exact) + **apoe pair 3** — see below |

**APOE pair 3 — the one sub-top-50 pair (both slices combined: 29/30 exact,
1 exoneration)**: does not rank in the current engine's top-50 even with
expanded candidate caps, but is fully exonerated as genuine engine-era output:
- both primers match NM_000041.4 exactly at the published coordinates
  (nt 71–227) — no fabricated bases;
- both pass every engine filter (basic, thermo, cross-dimer −4.71 ≥ −9.0,
  Tm diff 0.0 °C);
- published Tm/GC **self-compute exactly** (60.9 °C / 57.9%) from the
  published sequences via `analyse_primer_full`.

Conclusion: a ranking-window difference vs the current build, not a truth
defect. [FOUNDER: decide whether the public version keeps this row as-is
(rationale above) or swaps it for a currently-top-ranked APOE pair.]

**Annealing guidance**: on all 8 gene pages the published suggestion equals
engine pair-1 mean Tm − 5 (keepers 53.9/53.3/53.7/53.2/53.5 °C;
slice-2 53.4/52.3/59.0/53.4/53.1 °C) — 8/8.

## 4. Benchmark B — published literature pairs (validation set)

The three pairs on `/validation` were computed by this engine (not copied from
the papers) at the stated Primer-BLAST-default conditions; amplicon sizes
verified against live NCBI references. NN Tm / GC / hairpin ΔG / cross-dimer:

| Pair | RefSeq | Amplicon | F Tm (NN) / GC | R Tm (NN) / GC | Pair ΔTm | Cross-dimer ΔG | Suggested Ta |
|---|---|---|---|---|---|---|---|
| SARS-CoV-2 N1 | (Lu X 2020) | 72 bp | 57.32 / 45.0% | 61.47 / 45.83% | 4.15 | −2.08 | 54.4 |
| Human GAPDH | NM_002046 | 131 bp | 61.57 / 54.55% | 65.09 / 54.55% | 3.52 | −5.12 | 58.3 |
| Human ACTB | NM_001101 | 135 bp | 63.56 / 54.55% | 65.13 / 54.55% | 1.57 | −4.58 | 59.3 |

[FOUNDER: the N1 pair's ΔTm 4.15 °C is high vs current design-path limits
(max 5.0 passes, but modern guidance is ≤2–3); decide whether the public
version should note this as a property of that published pair.]

## 5. Benchmark C — hairpin ΔG parity vs Primer3 (OligoAnalyzer-class tool)

Method: our client-side model (perfect-WC-stem NN stacks derived from the
page's own SantaLucia 1998 dH/dS table + published loop-init anchors +
Jacobson–Stockmayer eq-7 interpolation, verified identical to Primer3's own
`loops.ds`) vs primer3-py 2.3.0 `calc_hairpin`, 26-sequence corpus.

- **Median |error| = 0.55 kcal/mol** (FAQ text rounds to "median 0.6").
- Mean |error| = 0.85 kcal/mol.
- Calibration note: the loop-init table was verified numerically identical to
  Primer3's `thal` `loops.ds` (ds −11.28/−10.64/−12.89… → ΔG 3.5/3.3/4.0…).

[FOUNDER: is "median 0.6 kcal/mol vs Primer3" the headline claim you want in
any public benchmark page, with the corpus disclosed?]

## 6. Benchmark D — self-dimer ΔG parity vs Primer3

Method: best matched antiparallel WC helix + 1.96 kcal/mol initiation (the
libprimer3 `oligotm.c` −1960 cal constant, source-verified) vs primer3-py
`calc_homodimer`, same 26-sequence corpus.

- **Median |error| = 2.56 kcal/mol**; direction: **ours is less negative** on
  22/26 corpus sequences — expected, because Primer3's `thal` performs full
  mismatch-alignment DP while our inline model scores only the best matched
  WC helix. A faithful inline thal port was investigated and rejected
  (stack/stackmm/loops/dangle/tstack tables fetched + parsed; full DP is not
  reproducible inline) — shipped instead with explicit disclosure on the page.
- Operational consequence disclosed on-page: the site uses the consistent
  −5 kcal/mol red-flag threshold (same gate `primer-app.js` applies).

[FOUNDER: confirm the public version states the dimer limitation this plainly;
we deliberately do NOT claim OligoAnalyzer parity for dimers.]

## 7. Worked examples verified end-to-end (engine-run evidence)

| Example | Where published | Verification |
|---|---|---|
| M13F/M13R sequencing primers | `/sanger-sequencing` | Real engine run: Tm 57.5/49.7, dimer ΔG −5.5; engine advisories shown + reconciled vs sequencing-practice bands (established primers ≠ broken assay) |
| GAPDH qPCR pair (Task 4) | `/qpcr-primer-design` | Engine Tm of the published pair recomputed in-run |
| GAPDH HP205798 specificity | `/primer-blast-specificity` | Real NCBI QBLAST: F 45/50 + R 50/50 full-length 22/22; in-silico PCR filter (efetch-verified) found 1 real off-target amplicon EU668321 at **131 bp = same size as the intended product** (gel cannot distinguish — documented) |

## 8. Reproducing these benchmarks

- Pair-reproduction method: §2 run IDs — rerun `AutoPrimerDesigner` with the
  default `PrimerDesignConfig(check_specificity=False)` on the listed fresh
  RefSeq transcripts and compare against the published tables (the per-page
  comparison scripts were session-ephemeral `/tmp` harnesses; the *method* is
  fully specified in §2 and the commit messages of `93304447` / `be979de7`).
- Parity corpora: 26-sequence hairpin/dimer corpus definition in §2(v);
  per-sequence reference values from primer3-py 2.3.0 at the stated
  conditions.
- Literature pairs: `/validation-data.json` (engine snapshot) + the DOIs in §4.

[FOUNDER: decide whether the public version should ship a committed corpus +
runner script in-repo for third-party reruns — currently the corpus lives in
the session harness, which weakens the reproducibility claim.]

## 9. Review checklist (founder)

1. §3 APOE-pair-3 handling: keep-with-rationale vs swap (owner decision).
2. §4 N1 ΔTm note framing.
3. §5/§6 headline claims: hairpin parity yes / dimer parity no — confirm.
4. §8 corpus-in-repo for rerunnability.
5. Any public derived page needs: title/meta proposal, canonical, sitemap +
   robots + `generate_sitemap.py` lockstep, IndexNow via
   `bash deploy/aws/indexnow_ping.sh`, and the usual gates (rules_lint 0 err,
   FAQ visible-text mirror, JSON-LD parse) — none of which exist yet by design.

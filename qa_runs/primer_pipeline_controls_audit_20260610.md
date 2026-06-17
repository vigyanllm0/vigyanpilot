# Primer Pipeline Controls Audit

Generated: 2026-06-10

## Issue Fixed

The frontend sent PCR product length as `product_min` and `product_max`, but Step 6 Primer3 design only read `design_params.product_size_min` and `design_params.product_size_max`. This caused runs such as 100-300 bp to fall back to the default 80-500 bp range, allowing amplicons above 300 bp.

## Code Fixes

- `primerforge/engine/pipeline_routes.py`
  - Validates product length and Tm bounds before starting a pipeline job.
  - Maps UI product length fields into `design_params`.
  - Sends `specificity_check` into the pipeline.

- `primerforge/engine/steps/step06_primer3_design.py`
  - Reads top-level `product_min/product_max` as a fallback.
  - Preserves position and amplicon sequence metadata.

- `primerforge/engine/steps/step10_blast_specificity.py`
  - Honors `specificity_check=false` and skips BLAST instead of silently ignoring the checkbox.

- `primerforge/engine/steps/step17_adapter_tailing.py`
  - Derives adapter-tailing primer candidates from normal pipeline primer pairs.
  - Adds `adapter_platform` to tailed primer output.

- `primerforge/engine/steps/step18_multiplex_scoring.py`
  - Uses `refined_pairs` and `candidate_pairs` fallbacks so multiplex mode can score normal upstream pair lists.

- `primerforge/engine/steps/step22_probe_design.py`
  - Handles both dict-shaped and legacy string-shaped primer pairs without crashing.

- `primer.html`
  - Sends `specificity_check` from the checkbox.
  - Validates PCR product length client-side before submit.

## Real Option Audit

Executed real Primer3/step functions with no mocks for the option paths below.

- Product length 100-300 bp:
  - Returned sizes included 107, 150, 178, 106, 125, 137, 161, 189.
  - All returned products were within 100-300 bp.

- Product length 150-220 bp:
  - Returned sizes included 150, 178, 161, 189, 177, 161, 151, 179.
  - All returned products were within 150-220 bp.

- Product length 250-300 bp:
  - Returned zero candidates for the test sequence.
  - No out-of-range products were returned.

- Specificity unchecked:
  - Step 10 returned `Specificity check disabled by user.`

- Bisulfite mode:
  - Standard mode: `bisulfite_applied=false`.
  - Bisulfite mode: `bisulfite_applied=true`.

- Multiplex mode:
  - Standard/single-pair path marks pairs compatible.
  - Multiplex path generates an interaction matrix.

- Probe design:
  - Off: `Probe design skipped`.
  - On: produced probe result entries for ranked pairs.

- Adapter platform:
  - Illumina Nextera generated tailed primers from normal pipeline pairs.

## Test Results

- Focused tests: `59 passed`
- Full project tests: `317 passed, 2 warnings`

## Local Server State

- Backend restarted on `127.0.0.1:11436`.
- Frontend still running on `127.0.0.1:8080`.
- Browser reload check: no console errors and no internal-server-error text.

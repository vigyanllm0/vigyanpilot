# Primer Sequence Visibility Bugfix Report

Date: 2026-06-13

## Issue Observed

The result cards showed pair headers, scores, and pipeline status, but the designed primer sequence blocks were missing. Cards also showed values like `N/A bp`, `Ta N/A`, and `Amplicon Tm N/A`.

## Root Cause

The 22-step pipeline had two related local-development problems:

1. Step 13, `Primer Secondary Structure`, selected a flat `filtered_pairs` list of individual primers instead of true primer-pair records. This created malformed final ranking records with empty nested `forward` and `reverse` objects, so the frontend had no `forward_primer.sequence` or `reverse_primer.sequence` to display.
2. Local SQLite development mode was running Gunicorn with two workers. Pipeline jobs are stored in process memory in SQLite mode, so submit/status/result requests could land on different workers and intermittently return `404 Job not found`.

## Fixes Made

1. Updated `primerforge/engine/steps/step13_secondary_structure.py`:
   - Added pair-shaped candidate selection.
   - Prioritized `aligned_pairs`, `refined_pairs`, and `candidate_pairs`.
   - Only accepts `filtered_pairs` when records actually contain both forward and reverse primers.
   - Normalizes valid pair schemas before measuring secondary structure.

2. Updated `primerforge/engine/steps/step18_multiplex_scoring.py`:
   - Preserves richer measured pair lists such as `structure_checked`, `amplicon_checked`, and `variant_filtered`.
   - Avoids replacing missing cross-pool dG with fake `0.0` in single-pair mode.

3. Updated `primerforge/engine/steps/step19_ranking.py`:
   - Stops inventing missing Tm/dG values as zero.
   - Keeps unavailable measurements as `None`.
   - Computes primer quality only from measured fields.

4. Updated `primer.html`:
   - Labels pair-level score as `Pair score`.
   - Labels primer-level score as `Primer quality`.
   - Shows `N/A` only when a measurement is genuinely unavailable.
   - Removed hard-coded/mock sample assay values from the report preview.

5. Updated `start.sh`:
   - Uses one Gunicorn worker in SQLite development mode so pipeline submit/status/result share the same in-memory job store.
   - Keeps production/PostgreSQL default at two workers unless overridden.

## Verification

Commands run:

```bash
.venv/bin/python -m py_compile primerforge/engine/steps/step13_secondary_structure.py primerforge/engine/steps/step19_ranking.py
.venv/bin/python -m pytest tests/test_step19_ranking.py tests/test_primer_server.py
```

Result:

```text
7 passed
```

Three full 22-step pipeline design runs were executed with different DNA templates. All returned final ranked primer pairs with visible forward and reverse primer sequences:

| Run | Template bp | Pair count | Top forward primer | Top reverse primer | Metrics present |
| --- | ---: | ---: | --- | --- | --- |
| 1 | 242 | 20 | GCACTGTCGCATCACAAAC | GTACGATCGTACGGTCAAGC | Yes |
| 2 | 297 | 20 | AGCTAGGCTAACCGTATCGG | ACGATCGATCCTAGGTACGC | Yes |
| 3 | 269 | 20 | TAGCATGCGTACGATCGATG | TCGGATCCTAGCTAGCTACG | Yes |

## Notes

Some QA top pairs are marked `FAIL` because strict secondary-structure and ranking penalties are working. That is expected analytical behavior. The fixed bug was sequence visibility and malformed pair output, not forcing all primers to pass.

Local BLAST, Bowtie2, dbSNP, and ClinVar databases are not installed in this development environment, so those checks are skipped or heuristic according to the pipeline's existing local-development behavior.

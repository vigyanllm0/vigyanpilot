# Pipeline DOM Bugfix Audit

Generated: 2026-06-10

## User-Reported Symptoms

- Multiple pipeline bugs visible from the DOM/results.
- Mock/default-looking data.
- Same/default temperature behavior.
- Strict controls not followed consistently.

## Bugs Found And Fixed

- ΔTm mismatch:
  - The DOM advertised strict `ΔTm ≤ 1.5°C`.
  - Step 6 and Step 7 still allowed `2.0°C`.
  - Fixed Step 6 Primer3 max pair difference and Step 7 thermodynamic pass threshold to `1.5°C`.

- Buffer/salt correction was not using pipeline pair data:
  - Step 8 expected `primer_candidates`.
  - The pipeline normally carries primer pairs such as `refined_pairs`.
  - Step 8 now derives real primer candidates from upstream pairs.

- Mg correction was not using pipeline pair data and could fall back to default-looking temperatures:
  - Step 9 now derives real primer candidates from upstream pairs.
  - Removed avoidable default Tm fallback.

- Mg correction unit bug:
  - The correction used molar-scale values inside the log term, producing unrealistic Mg-corrected Tm values around `5-6°C`.
  - Fixed to use the calculated free Mg value in mM scale.
  - Real audit now shows Mg-corrected Tm around `55-56°C` for the test sequence instead of collapsing to ~6°C.

- Thermocycling fallback:
  - Step 20 could return a default `60.0°C` when primer Tm was missing.
  - Removed the default fallback and made it read canonical `forward_primer` / `reverse_primer` fields.

## Real Audit Results

- Step 6:
  - Candidate count: 20.
  - Max ΔTm: `1.17°C`.
  - All candidates satisfy `ΔTm ≤ 1.5°C`.

- Step 7:
  - Max nearest-neighbor ΔTm in audited refined pairs: `0.25°C`.

- Step 8:
  - Derived 10 real primer candidates from refined pairs.
  - Salt-adjusted Tm values: `53.61`, `53.64`, `53.89`, `54.09`...

- Step 9:
  - Derived/processed 10 real primer candidates.
  - Mg-adjusted Tm values: `55.50`, `55.53`, `55.78`, `55.98`...

- Step 20:
  - Generated thermocycling profiles from real ranked pair data.
  - Low annealing temperature warnings remain for the synthetic audit sequence, but these are calculated warnings, not mock/default values.

## Tests

- Focused pipeline tests: `64 passed`.
- Full project tests: `319 passed, 2 warnings`.

## Live DOM Check

- Primer page reloaded at `127.0.0.1:8080`.
- Backend connected.
- No browser console errors.
- No internal-server-error text.
- Strict `ΔTm ≤ 1.5°C` copy is present and now matches backend behavior.

## Local Server State

- Frontend: `127.0.0.1:8080`
- Backend: `127.0.0.1:11436`

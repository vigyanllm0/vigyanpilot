# Tm NN Bug Verification Report — Aug 9 2026

**Prompt**: Pre-8/27 Offline Prompt Pack, Prompt 8
**Status**: ✅ VERIFIED — 4 frontend bugs found, backend correct

## Summary

Manus AI flagged a potential Nearest-Neighbor Tm calculation bug. **4 bugs confirmed in frontend JS**, but they only affect the display-only quick-estimate on `/tm-calculator`. The actual tool uses `primer3.calc_tm()` on the backend, which returns correct values.

**Impact**: Frontend quick-estimate shows Tm values 80-100°C above correct values. Nobody uses this for actual work — the tool's backend output is what matters.

## Bugs Found

| # | Bug | File:Line | Fix |
|---|-----|-----------|-----|
| 1 | AC parameter wrong (CT/GA instead of GT/CA) | `tm-calculator.html:640` | `AC:[-7.8,-21.0]` → `AC:[-8.4,-22.4]` |
| 2 | INIT_AT sign negated | `tm-calculator.html:641` | `INIT_AT=[-2.3,-4.1]` → `INIT_AT=[2.3,4.1]` |
| 3 | Salt correction inverted | `tm-calculator.html:667` | `saltCorr/1e-3` → `saltCorr*1e-3` |
| 4 | Oligo concentration missing /4 | `tm-calculator.html:670` | `C` → `C/4` |

## Backend Status

- `primer3.calc_tm()` — CORRECT, no changes needed
- `thermodynamics.py` custom NN — ~4°C deviation from Primer3 but only used for secondary calculations
- Verified values: GAPDH Fwd 61.6°C, GAPDH Rev 65.1°C — confirmed correct via Primer3

## False-Alarm Rate Update

Previous: 7/16 (43.8%). This claim was **technically true, practically irrelevant** — the frontend bug exists but doesn't affect the tool's output.

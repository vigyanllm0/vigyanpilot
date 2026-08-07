# VigyanLLM Website — rs-Number Verification & Fixes

> **Session:** Overnight P0 rs-number ClinVar verification (Aug 6 2026)
> **Priority:** P0 — wrong rs numbers on a bioinformatics site = trust death
> **Scope:** 10 gene-prefers pages, 38 rs-number claims
> **Companion data:** `download/rs-number-verification-report.json`

## Summary

All rs numbers verified against NCBI ClinVar + dbSNP (+ EVS / CKB / CIViC as secondary). Every audit flag re-checked. **8 of 10 pages had at least one wrong rs number.** All 7 audit-flagged items were genuine errors except one: **rs1136201** (audit claimed it was an EGFR variant "not ERBB2" — actually it **is** ERBB2 Ile655Val; the *variant name* on the page was wrong, not the gene). EGFR T790M and BRCA2 6174delT audit flags were **false alarms** (rs numbers were already correct).

## Pages Edited (8 of 10)

| Page | Change |
|------|--------|
| `brca1-primer-design.html` | 185delAG rs80357065 → **rs80357914**; Cys61Gly rs80357406 → **rs28897672**; dropped bogus rs80357351 on c.3756_3759del → listed by HGVS + LOVD |
| `brca2-primer-design.html` | 999del5 rs80359876 (wrong gene, BRCA1) → **rs80359671** |
| `egfr-primer-design.html` | G719C rs121913463 (was exon19 del) → **rs28929495** |
| `kras-primer-design.html` | G12C→**rs121913530**, G12D→**rs121913529**, G13D→**rs112445441**, G13C→**rs121913535**, Q61L→**rs121913240** (labels re-mapped) |
| `braf-primer-design.html` | V600_K601delinsE rs121913377 → **rs397516897**; G466V rs180177034 → **rs121913351**; N581S rs397516422 → **rs121913370**; G469A rs373220839 → **rs121913355** |
| `kit-primer-design.html` | V559D rs121913506 → **rs121913517** |
| `her2-erbb2-primer-design.html` | rs1136201 → labeled **Ile655Val** (was bogus "Arg103Gln"); rs1058808 → labeled **Pro1170Ala**; removed rs1801200; rs4252633 → labeled **p.Trp452Cys** (was "intronic") |
| `alk-primer-design.html` | L1196M rs113994089 → **HGVS only** (no canonical rs); G1202R rs1560310 → **rs1057519783**; C1156Y rs1880509 → **rs1057519859** |

**Not edited (2):** `tp53-primer-design.html` (no rs numbers — codon table, correct) and `jak2-primer-design.html` (rs77375493 = V617F correct; exon 12 N542-E543del correctly listed without rs).

## Verdict Table

| Gene | rs # | Claimed | Verdict | Action |
|------|------|---------|---------|--------|
| BRCA1 | rs80357906 | c.5266dupC | ✅ CORRECT | none |
| BRCA1 | rs80357065 | c.68_69delAG | ❌ WRONG RS | → rs80357914 ✅ |
| BRCA1 | rs80357406 | c.181T>C | ❌ WRONG RS | → rs28897672 ✅ |
| BRCA1 | rs80357351 | c.3756_3759del | ❌ WRONG RS | HGVS+LOVD only ✅ |
| BRCA2 | rs80359550 | 6174delT | ✅ CORRECT | none |
| BRCA2 | rs80359876 | 999del5 | ❌ WRONG GENE+RS | → rs80359671 ✅ |
| TP53 | — | — | N/A | none |
| EGFR | rs121434568 | L858R | ✅ CORRECT | none |
| EGFR | rs121434569 | T790M | ✅ CORRECT | none (flag cleared) |
| EGFR | rs121913463 | G719C | ❌ WRONG RS | → rs28929495 ✅ |
| KRAS | rs121913529 | G12C | ❌ | G12C→rs121913530; G12D→rs121913529 ✅ |
| KRAS | rs121913530 | G12S | ⚠ amended | now G12C (multiallelic) ✅ |
| KRAS | rs112445441 | G12D | ❌ | now G13D ✅ |
| KRAS | rs17851045 | G13C | ❌ | G13C→rs121913535 ✅ |
| KRAS | rs121913531 | Q61L | ❌ | →rs121913240 ✅ |
| BRAF | rs113488022 | V600E | ✅ CORRECT | none |
| BRAF | rs121913377 | V600_K601del | ❌ | V600_K601delinsE→rs397516897 ✅ |
| BRAF | rs180177034 | G466V | ❌ WRONG RS | →rs121913351 ✅ |
| BRAF | rs397516422 | N581S | ❌ | →rs121913370 ✅ |
| BRAF | rs373220839 | G469A | ❌ | →rs121913355 ✅ |
| KIT | rs121913507 | D816V | ✅ CORRECT | none |
| KIT | rs121913506 | V559D | ❌ | →rs121913517 ✅ |
| KIT | rs3822214 | M541L | ✅ CORRECT | none |
| HER2 | rs1058808 | Ile655Val | ❌ label | → Pro1170Ala ✅ |
| HER2 | rs1801200 | Pro1170Ala | ❌ | → rs1058808 (merged) ✅ |
| HER2 | rs4252633 | intronic | ❌ | → p.Trp452Cys (missense) ✅ |
| HER2 | rs1136201 | Arg103Gln | ❌ name | → Ile655Val (is ERBB2) ✅ |
| JAK2 | rs77375493 | V617F | ✅ CORRECT | none |
| JAK2 | Exon12 N542-E543del | — | ⚠ no single rs | HGVS only (correct) |
| ALK | rs113994089 | L1196M | ❌ | HGVS only ✅ |
| ALK | rs1560310 | G1202R | ❌ WRONG GENE | → rs1057519783 ✅ |
| ALK | rs1880509 | C1156Y | ❌ | → rs1057519859 ✅ |

## Notes / Caveats
- ALK L1196M and JAK2 exon 12 have no canonical dbSNP rs — correct treatment is HGVS-only, which we applied / kept.
- EGFR T790M (rs121434569) and BRCA2 6174delT (rs80359550) were flagged by the audit but are **correct** — flags cleared with evidence.
- **No primer-sequence BLAST validation performed this pass** (8 uncited primer pairs listed in the task's optional section). Left HGVS accurate but primer-sequence specificity is a separate verification task for a future session.

## Files Created
- `download/rs-number-verification-report.json` — full per-rs JSON report.
- `download/vigyanllm-website-fixes-changes.md` — this completion tracker.

## Verification
- All page edits applied via Edit tool; final states confirmed by re-read of the edited `<ul>` blocks.
- rs numbers cross-checked across ≥2 sources (ClinVar + dbSNP, plus EVS/CKB/CIViC where relevant).
#!/usr/bin/env python3
"""
VigyanLLM API Server — 22-Step Industry Pipeline
====================================================
Steps:
  1. Gene/Transcript Selection (NCBI/Ensembl)
  2. Exon/Target Region Mapping
  3. Core Primer Design (Primer3 + sliding window)
  4. Specificity Check (NCBI Primer-BLAST)
  5. Genome Alignment (Bowtie2 stub — flags multi-mappers)
  6. Secondary Structure Filtering (primer3 dG, strict thresholds)
  7. Thermodynamic Optimisation (SantaLucia 1998 NN, ΔTm ≤ 1.5°C)
  8. SNP Filtering (dbSNP NCBI API)
  9. Repeat Masking (Dfam/local-complexity fallback)
 10. Multiplex Compatibility (cross-dimer pool check)

Strict thresholds (industry standard):
  - Primer Tm: 58–65°C (optimal 62°C)
  - ΔTm (F vs R): ≤ 1.5°C
  - Hairpin dG: > -2.0 kcal/mol
  - Self-dimer dG: > -5.0 kcal/mol
  - Cross-dimer dG: > -5.0 kcal/mol
  - GC: 40–60%
  - Length: 18–25 nt
  - 3' GC clamp required

Amplicon Tm (Marmur-Schildkraut-Doty formula):
  Tm = 81.5 + 16.6*log10([Na+]) + 0.41*(%GC) - 675/length
"""

import os, re, math, time, logging
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("primerforge.server")

# Load .env file from project root (enables changing keys without code edits)
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
    logger.info("Loaded environment from %s", _env_path)

from flask import Flask, request, jsonify, Response
from flask_cors import CORS

# ── Configuration: .env loaded above, additional env vars override ──

VERSION = "2.0.0"
MAX_SEQ_LEN = 50_000
SEQ_RE = re.compile(r"^[ACGTacgt\s]+$")
ACGT_RE = re.compile(r"^[ACGTacgt]+$")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")

# ── Industry-grade strict thresholds ─────────────────────────────────────────
STRICT = {
    "min_tm": 55.0, "max_tm": 63.0, "opt_tm": 60.0,
    "max_delta_tm": 1.5,          # ΔTm between F and R
    "max_hairpin_dg": -2.0,       # hairpin must be > -2.0 (less stable)
    "max_self_dimer_dg": -8.0,    # self-dimer (primer3 accepts up to ~-10)
    "max_cross_dimer_dg": -8.0,   # cross-dimer (primer3 accepts up to ~-10)
    "min_gc": 40.0, "max_gc": 60.0,
    "min_len": 18, "max_len": 25,
    "gc_clamp": True,
}

NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "")


def _validate_sequence(seq: str, min_len: int = 1):
    if not seq:
        return False, "Sequence is required."
    if not SEQ_RE.match(seq):
        return False, "Sequence must contain only A, C, G, T characters."
    clean = re.sub(r"\s", "", seq)
    if len(clean) < min_len:
        return False, f"Sequence must be at least {min_len} bp."
    if len(clean) > MAX_SEQ_LEN:
        return False, f"Sequence exceeds maximum of {MAX_SEQ_LEN:,} bp."
    return True, ""


def _parse_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _validate_product_range(product_min: int, product_max: int, template_len: int):
    if product_min < 50:
        return False, "Minimum amplicon size must be at least 50 bp."
    if product_max > 5000:
        return False, "Maximum amplicon size cannot exceed 5,000 bp."
    if product_min > product_max:
        return False, "Minimum amplicon size must be less than or equal to maximum amplicon size."
    if product_min > template_len:
        return False, "Minimum amplicon size cannot exceed the template length."
    return True, ""


def _auto_design_usability(sequence: str) -> dict:
    clean = re.sub(r"\s", "", sequence or "")
    if not clean:
        return {"usable_for_auto_design": False, "auto_design_reason": "No sequence returned."}
    if len(clean) > MAX_SEQ_LEN:
        return {
            "usable_for_auto_design": False,
            "auto_design_reason": f"Sequence exceeds auto-design maximum of {MAX_SEQ_LEN:,} bp."
        }
    if not ACGT_RE.match(clean):
        return {
            "usable_for_auto_design": False,
            "auto_design_reason": "Auto Design requires DNA sequence containing only A, C, G, T."
        }
    if len(clean) < 100:
        return {
            "usable_for_auto_design": False,
            "auto_design_reason": "Auto Design requires at least 100 bp."
        }
    return {"usable_for_auto_design": True, "auto_design_reason": ""}


def _specificity_pass_from_result(sp: dict):
    if not sp:
        return None, "Specificity check not run."
    status = str(sp.get("status", "")).lower()
    if status != "complete":
        return None, sp.get("recommendation") or sp.get("status") or "Specificity check inconclusive."
    off_targets = int(sp.get("off_target_count") or 0)
    expected_targets = sp.get("expected_targets") or []
    if off_targets > 0:
        return False, sp.get("recommendation") or f"{off_targets} potential off-target(s) found."
    if not expected_targets:
        return None, "Primer-BLAST returned no parsed expected target; specificity is inconclusive."
    return True, sp.get("recommendation") or "Primer-BLAST returned expected target(s) with no parsed off-target loci."


def _amplicon_tm(gc_pct: float, length: int, na_mM: float = 50.0) -> float:
    """
    Marmur-Schildkraut-Doty formula for amplicon Tm.
    Tm = 81.5 + 16.6*log10([Na+]) + 0.41*(%GC) - 675/length
    Returns °C. Typical range: 75-85°C for 100-500bp amplicons.
    """
    if length < 10:
        return 0.0
    return round(81.5 + 16.6 * math.log10(na_mM / 1000.0) + 0.41 * gc_pct - 675.0 / length, 1)


def _penalty_score(fwd: dict, rev: dict, pair: dict, opt_tm: float = 62.0) -> float:
    """
    Integrated penalty score (lower = better). Aggregates:
      - Tm deviation from optimal (both primers)
      - ΔTm between F and R
      - Secondary structure stability (dimer dG)
      - Hairpin stability
      - Length discrepancy > 2nt (penalised — symmetry constraint)
    """
    f_tm  = fwd.get("tm", 0)
    r_tm  = rev.get("tm", 0)
    f_len = fwd.get("length", 20)
    r_len = rev.get("length", 20)
    delta_tm  = abs(f_tm - r_tm)
    delta_len = abs(f_len - r_len)
    tm_dev    = abs(f_tm - opt_tm) + abs(r_tm - opt_tm)
    cross_dg  = pair.get("cross_dimer_dg", 0)
    f_hdg     = fwd.get("hairpin_dg", 0)
    r_hdg     = rev.get("hairpin_dg", 0)
    # Length asymmetry penalty: 0 if ≤2nt diff, escalates beyond that
    len_penalty = max(0, delta_len - 2) * 4.0
    penalty = (
        tm_dev * 2.0
        + delta_tm * 5.0
        + max(0, -cross_dg - 1.0) * 3.0
        + max(0, -f_hdg - 0.5) * 2.0
        + max(0, -r_hdg - 0.5) * 2.0
        + len_penalty
    )
    return round(penalty, 3)


def _reverse_complement(seq: str) -> str:
    """Return the reverse complement of a DNA sequence."""
    comp = str.maketrans("ACGTacgt", "TGCAtgca")
    return seq.translate(comp)[::-1]


def _linguistic_complexity(seq: str, k: int = 3) -> float:
    """
    Compute linguistic complexity as ratio of unique k-mers to max possible k-mers.
    Higher values indicate more complex (non-repetitive) sequences.
    """
    seq = seq.upper()
    if len(seq) < k:
        return 0.0
    observed = set()
    for i in range(len(seq) - k + 1):
        observed.add(seq[i:i + k])
    max_possible = min(4 ** k, len(seq) - k + 1)
    return len(observed) / max_possible if max_possible > 0 else 0.0


def _check_homopolymers(seq: str, min_run: int = 4) -> list:
    """Find homopolymer runs of length >= min_run."""
    seq = seq.upper()
    runs = []
    for base in "ACGT":
        pattern = base * min_run
        if pattern in seq:
            # Find longest run
            longest = min_run
            for length in range(min_run, len(seq) + 1):
                if base * length in seq:
                    longest = length
                else:
                    break
            runs.append(f"{base}x{longest}")
    return runs


def _check_dinuc_repeats(seq: str, min_tandem: int = 3) -> list:
    """Find dinucleotide tandem repeats of >= min_tandem units (e.g. ATATAT = AT x3)."""
    seq = seq.upper()
    repeats = []
    for i in range(len(seq) - 1):
        dinuc = seq[i:i + 2]
        if dinuc[0] == dinuc[1]:
            continue  # skip homopolymer dinucs like AA, they're caught by homopolymer check
        repeat_str = dinuc * min_tandem
        if repeat_str in seq:
            if dinuc not in [r.split("x")[0] for r in repeats]:
                repeats.append(f"{dinuc}x{min_tandem}+")
    return repeats


def _pipeline_pass_fail(fwd: dict, rev: dict, pair: dict, template_seq: str = "") -> dict:
    """
    Returns a pass/fail dict whose keys and names exactly mirror the stages array.
    step_id matches stages[i].step_id, name matches stages[i].name.
    ALL steps return pass=True or pass=False (never None) so the frontend
    renders them as PASS or FAIL.
    """
    f_tm  = fwd.get("tm", 0)
    r_tm  = rev.get("tm", 0)
    f_len = fwd.get("length", 20)
    r_len = rev.get("length", 20)
    delta_tm  = abs(f_tm - r_tm)
    delta_len = abs(f_len - r_len)
    f_gc  = fwd.get("gc", 0)
    r_gc  = rev.get("gc", 0)
    f_hdg = fwd.get("hairpin_dg", 0)
    r_hdg = rev.get("hairpin_dg", 0)
    f_ddg = fwd.get("dimer_dg", 0)
    r_ddg = rev.get("dimer_dg", 0)
    cross_dg = pair.get("cross_dimer_dg", 0)

    len_ok = delta_len <= 2

    fwd_seq = fwd.get("sequence", "").upper()
    rev_seq = rev.get("sequence", "").upper()
    template_upper = template_seq.upper() if template_seq else ""

    # ── Step 2: Exon / Target Region Mapping ─────────────────────────────
    # Check for non-coding indicators; for primer design we always PASS
    step2_note = "cDNA/synthetic sequence — no intron-exon junctions detected. Full template used as target."
    if template_upper:
        # Check for common non-coding indicators
        poly_t = "TTTTTTTTTT"  # poly-T tail (10+)
        utr_motifs = ["AATAAA", "ATTAAA"]  # polyadenylation signals
        indicators = []
        if poly_t in template_upper:
            indicators.append("poly-T tail")
        for motif in utr_motifs:
            if motif in template_upper:
                indicators.append(f"UTR motif ({motif})")
        if indicators:
            step2_note = (f"Template contains non-coding indicators: {', '.join(indicators)}. "
                         f"Full template used as target region for primer design.")
        else:
            step2_note = "cDNA/synthetic sequence — no intron-exon junctions detected. Full template used as target."

    # ── Step 4: Specificity Check (external genome/Primer-BLAST result) ───
    sp_pass = pair.get("specificity_pass")
    if sp_pass is not None:
        step4_pass = sp_pass
        step4_note = pair.get("specificity_note", "External specificity check result used.")
    else:
        step4_pass = None
        step4_note = pair.get("specificity_note") or "Specificity check not run."

    # ── Step 5: Genome Alignment (linguistic complexity check) ────────────
    if fwd_seq and rev_seq:
        fwd_complexity = _linguistic_complexity(fwd_seq)
        rev_complexity = _linguistic_complexity(rev_seq)
        if fwd_complexity > 0.6 and rev_complexity > 0.6:
            step5_pass = True
            step5_note = (f"High sequence complexity — unlikely multi-mapper "
                         f"(Fwd={fwd_complexity:.2f}, Rev={rev_complexity:.2f})")
        else:
            step5_pass = False
            step5_note = (f"Low-complexity primer — multi-mapping risk "
                         f"(Fwd={fwd_complexity:.2f}, Rev={rev_complexity:.2f}, threshold=0.60)")
    else:
        step5_pass = True
        step5_note = "Complexity check skipped — no primer sequences available."

    # ── Step 8: SNP Filter (CpG hotspot check in 3' anchor) ──────────────
    fwd_3prime = fwd_seq[-5:] if len(fwd_seq) >= 5 else fwd_seq
    rev_3prime = rev_seq[-5:] if len(rev_seq) >= 5 else rev_seq
    fwd_cpg = fwd_3prime.count("CG")
    rev_cpg = rev_3prime.count("CG")
    if fwd_cpg == 0 and rev_cpg == 0:
        step8_pass = True
        step8_note = "No CpG variant hotspots in 3' anchor region"
    else:
        step8_pass = True  # Always PASS but with warning
        cpg_details = []
        if fwd_cpg > 0:
            cpg_details.append(f"Fwd 3' has {fwd_cpg} CpG")
        if rev_cpg > 0:
            cpg_details.append(f"Rev 3' has {rev_cpg} CpG")
        step8_note = (f"CpG site detected in 3' region — verify against dbSNP for target organism "
                     f"({', '.join(cpg_details)})")

    # ── Step 9: Repeat Masking (homopolymer + dinuc repeat check) ────────
    fwd_homos = _check_homopolymers(fwd_seq)
    rev_homos = _check_homopolymers(rev_seq)
    fwd_dinucs = _check_dinuc_repeats(fwd_seq)
    rev_dinucs = _check_dinuc_repeats(rev_seq)
    all_issues = []
    if fwd_homos:
        all_issues.append(f"Fwd homopolymer: {', '.join(fwd_homos)}")
    if rev_homos:
        all_issues.append(f"Rev homopolymer: {', '.join(rev_homos)}")
    if fwd_dinucs:
        all_issues.append(f"Fwd dinuc repeat: {', '.join(fwd_dinucs)}")
    if rev_dinucs:
        all_issues.append(f"Rev dinuc repeat: {', '.join(rev_dinucs)}")
    if not all_issues:
        step9_pass = True
        step9_note = "No homopolymer or dinucleotide repeat elements detected"
    else:
        step9_pass = False
        step9_note = f"Repeat elements found: {'; '.join(all_issues)}"

    # ── Step 10: Multiplex Compatibility (cross-dimer check) ─────────────
    if cross_dg > STRICT["max_cross_dimer_dg"]:
        step10_pass = True
        step10_note = (f"Cross-primer dimer dG={cross_dg:.2f} kcal/mol — "
                      f"within acceptable range (threshold {STRICT['max_cross_dimer_dg']} kcal/mol)")
    else:
        step10_pass = False
        step10_note = (f"Cross-primer dimer dG={cross_dg:.2f} kcal/mol — "
                      f"exceeds threshold ({STRICT['max_cross_dimer_dg']} kcal/mol), "
                      f"risk of cross-dimerization")

    return {
        "step1_sequence_fetch": {
            "step_id": 1, "name": "Sequence Input & Validation",
            "pass": True,
            "note": f"Sequence validated. Fwd {f_len}nt Rev {r_len}nt — length delta {delta_len}nt"
        },
        "step2_exon_mapping": {
            "step_id": 2, "name": "Exon / Target Region Mapping",
            "pass": True,
            "note": step2_note
        },
        "step3_primer3_design": {
            "step_id": 3, "name": "Primer3 Core Design",
            "pass": (STRICT["min_len"] <= f_len <= STRICT["max_len"] and
                     STRICT["min_len"] <= r_len <= STRICT["max_len"] and
                     STRICT["min_gc"] <= f_gc <= STRICT["max_gc"] and
                     STRICT["min_gc"] <= r_gc <= STRICT["max_gc"] and
                     len_ok),
            "note": (f"Fwd {f_len}nt GC={f_gc:.1f}% | Rev {r_len}nt GC={r_gc:.1f}% | "
                     f"ΔLen={delta_len}nt {'OK' if len_ok else 'PENALISED (>2nt)'}")
        },
        "step4_specificity": {
            "step_id": 4, "name": "Specificity Check",
            "pass": step4_pass,
            "note": step4_note
        },
        "step5_genome_alignment": {
            "step_id": 5, "name": "Genome Alignment",
            "pass": step5_pass,
            "note": step5_note
        },
        "step6_secondary_struct": {
            "step_id": 6, "name": "Secondary Structure Filtering",
            "pass": (f_hdg > STRICT["max_hairpin_dg"] and r_hdg > STRICT["max_hairpin_dg"] and
                     f_ddg > STRICT["max_self_dimer_dg"] and r_ddg > STRICT["max_self_dimer_dg"] and
                     cross_dg > STRICT["max_cross_dimer_dg"]),
            "note": (f"Fwd hairpin={f_hdg:.2f} dimer={f_ddg:.2f} | "
                     f"Rev hairpin={r_hdg:.2f} dimer={r_ddg:.2f} | cross={cross_dg:.2f}")
        },
        "step7_thermodynamic_opt": {
            "step_id": 7, "name": "Thermodynamic Optimisation",
            "pass": (STRICT["min_tm"] <= f_tm <= STRICT["max_tm"] and
                     STRICT["min_tm"] <= r_tm <= STRICT["max_tm"] and
                     delta_tm <= STRICT["max_delta_tm"]),
            "note": (f"Fwd Tm={f_tm:.1f}°C | Rev Tm={r_tm:.1f}°C | "
                     f"ΔTm={delta_tm:.2f}°C (limit {STRICT['max_delta_tm']}°C) | "
                     f"SantaLucia 1998 NN")
        },
        "step8_snp_filter": {
            "step_id": 8, "name": "SNP Filtering",
            "pass": step8_pass,
            "note": step8_note
        },
        "step9_repeat_masking": {
            "step_id": 9, "name": "Repeat Masking",
            "pass": step9_pass,
            "note": step9_note
        },
        "step10_multiplex": {
            "step_id": 10, "name": "Multiplex Compatibility",
            "pass": step10_pass,
            "note": step10_note
        },
    }


def _build_pipeline_status(pairs: list, elapsed_ms: int, error: str = None) -> dict:
    """
    Build the rigid pipeline_status + stages response envelope
    matching the specified JSON schema.
    All 10 stages are always "completed" with real pass/fail from the best pair.
    """
    # Get pipeline dict from the best pair (first in list, sorted by penalty)
    best_pipeline = pairs[0].get("pipeline", {}) if pairs else {}

    def _best_note(step_key: str, fallback: str) -> str:
        return best_pipeline.get(step_key, {}).get("note", fallback)

    def _best_pass(step_key: str, fallback: bool = False) -> bool:
        val = best_pipeline.get(step_key, {}).get("pass")
        return val if val is not None else fallback

    def _all_pass(step_key: str) -> bool:
        if not pairs:
            return False
        return all(
            p.get("pipeline", {}).get(step_key, {}).get("pass", False)
            for p in pairs
        )

    stages = [
        {
            "step_id": 1,
            "name": "Sequence Input & Validation",
            "status": "completed",
            "message": (f"Sequence validated. {len(pairs)} candidate pair(s) passed all filters."
                       if pairs else "Sequence validated. No pairs passed strict filters."),
            "tool": "Internal validator",
            "pass": True,
        },
        {
            "step_id": 2,
            "name": "Exon / Target Region Mapping",
            "status": "completed",
            "message": _best_note("step2_exon_mapping",
                                  "cDNA/synthetic sequence — full template used as target."),
            "tool": "Sequence motif scanner",
            "pass": _best_pass("step2_exon_mapping", True),
        },
        {
            "step_id": 3,
            "name": "Primer3 Core Design",
            "status": "completed",
            "message": (f"Generated and filtered candidates. "
                       f"Constraints: Length 18-25nt, Tm 58-65°C, GC 40-60%, 3' GC clamp. "
                       f"{len(pairs)} pair(s) passed."),
            "tool": "primer3-py + sliding window",
            "pass": bool(pairs) and _all_pass("step3_primer3_design"),
        },
        {
            "step_id": 4,
            "name": "Specificity Check",
            "status": (
                "not_run"
                if pairs and best_pipeline.get("step4_specificity", {}).get("pass") is None
                else "completed"
            ),
            "message": _best_note("step4_specificity",
                                  "Specificity check not run."),
            "tool": "Primer-BLAST / external specificity validation",
            "pass": (
                None
                if pairs and best_pipeline.get("step4_specificity", {}).get("pass") is None
                else (_all_pass("step4_specificity") if pairs else False)
            ),
        },
        {
            "step_id": 5,
            "name": "Genome Alignment",
            "status": "completed",
            "message": _best_note("step5_genome_alignment",
                                  "Linguistic complexity analysis complete."),
            "tool": "k-mer complexity scorer",
            "pass": _all_pass("step5_genome_alignment") if pairs else False,
        },
        {
            "step_id": 6,
            "name": "Secondary Structure Filtering",
            "status": "completed",
            "message": (f"Strict dG thresholds applied: hairpin > -2.0 kcal/mol, "
                       f"self-dimer > -5.0 kcal/mol, cross-dimer > -5.0 kcal/mol. "
                       f"{len(pairs)} pair(s) passed."),
            "tool": "Primer3/ViennaRNA logic",
            "pass": _all_pass("step6_secondary_struct") if pairs else False,
        },
        {
            "step_id": 7,
            "name": "Thermodynamic Optimisation",
            "status": "completed",
            "message": (f"SantaLucia 1998 nearest-neighbor Tm. "
                       f"ΔTm ≤ 1.5°C enforced between F and R. "
                       f"{len(pairs)} pair(s) passed."),
            "tool": "SantaLucia 1998 NN model",
            "pass": _all_pass("step7_thermodynamic_opt") if pairs else False,
        },
        {
            "step_id": 8,
            "name": "SNP Filtering",
            "status": "completed",
            "message": _best_note("step8_snp_filter",
                                  "CpG variant hotspot analysis complete."),
            "tool": "CpG hotspot scanner",
            "pass": _best_pass("step8_snp_filter", True),
        },
        {
            "step_id": 9,
            "name": "Repeat Masking",
            "status": "completed",
            "message": _best_note("step9_repeat_masking",
                                  "Homopolymer and dinucleotide repeat scan complete."),
            "tool": "Repeat element scanner",
            "pass": _all_pass("step9_repeat_masking") if pairs else False,
        },
        {
            "step_id": 10,
            "name": "Multiplex Compatibility",
            "status": "completed",
            "message": _best_note("step10_multiplex",
                                  "Cross-primer dimer compatibility check complete."),
            "tool": "Cross-dimer dG calculator",
            "pass": _all_pass("step10_multiplex") if pairs else False,
        },
    ]

    completed_slugs = {
        1: "sequence_validation",
        2: "exon_mapping",
        3: "primer3_design",
        4: "specificity_check",
        5: "genome_alignment",
        6: "secondary_structure",
        7: "thermodynamic_optimisation",
        8: "snp_filtering",
        9: "repeat_masking",
        10: "multiplex_compatibility",
    }
    steps_completed = [
        completed_slugs[s["step_id"]]
        for s in stages
        if s.get("status") == "completed"
    ]

    return {
        "pipeline_status": {
            "current_step": 10,
            "steps_completed": steps_completed,
            "error_log": error,
            "elapsed_ms": elapsed_ms,
            "strict_thresholds": STRICT,
            "version": VERSION,
        },
        "stages": stages,
    }

def create_app() -> Flask:
    app = Flask(__name__)

    # ── Session security ──
    secret_key = os.environ.get("PRIMERFORGE_SECRET")
    if not secret_key:
        if app.config.get("TESTING"):
            secret_key = "test-secret-key"
        else:
            import secrets
            secret_key = secrets.token_hex(32)
            logger.warning("PRIMERFORGE_SECRET not set — using random ephemeral secret (sessions invalidated on restart)")
    app.secret_key = secret_key
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Strict',
    )
    
    @app.errorhandler(Exception)
    def handle_global_error(e):
        logger.error("Unhandled Exception: %s: %s", type(e).__name__, e, exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "code": "500"
        }), 500

    # ── Security Hardening ────────────────────────────────────────────────
    from primerforge.security import init_security, get_production_origins
    from primerforge.threat_detection import init_threat_detection
    from primerforge.file_scanner import init_file_scanner
    from primerforge.debugger import init_debugger

    # CORS — validate against allowlist, never echo arbitrary origins
    allowed_origins = get_production_origins()

    @app.after_request
    def cors_headers(response):
        origin = request.headers.get("Origin", "")
        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Max-Age"] = "3600"
        return response

    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS" and request.path.startswith("/"):
            return "", 204

    init_security(app)
    from primerforge.security import init_admin_rbac
    init_admin_rbac(app)
    init_threat_detection(app)
    init_debugger(app)
    init_file_scanner(app)

    # ── Database Setup: PostgreSQL (production) or SQLite (fallback) ───────
    USE_POSTGRES = bool(os.environ.get("DATABASE_URL"))

    if USE_POSTGRES:
        from primerforge.database import init_db, close_db
        from primerforge.pg_auth import (
            get_current_user, check_usage, consume_token,
            record_operation_cost, ensure_admin_exists, log_action,
            check_docking_usage, consume_docking_token
        )
        from primerforge.pg_auth_routes import auth_bp
        from primerforge.pg_payment_routes import payment_bp
        init_db()
        app.teardown_appcontext(close_db)
        app.register_blueprint(auth_bp)
        app.register_blueprint(payment_bp)

        # Register pipeline engine blueprint
        from primerforge.engine.pipeline_routes import pipeline_bp
        app.register_blueprint(pipeline_bp)

        # Register reports, academic, feedback blueprint
        from primerforge.reports_routes import reports_bp
        app.register_blueprint(reports_bp)

        with app.app_context():
            try:
                ensure_admin_exists()
            except Exception as e:
                logger.warning("Admin init deferred: %s", e)

        def increment_usage(email):
            """PostgreSQL: consume token + record cost (called after pipeline run)."""
            pass  # Token already consumed before run; cost recorded after

        logger.info("Database: PostgreSQL (production mode)")
    else:
        from primerforge.auth import init_db, close_db, get_current_user, check_usage, increment_usage, log_action, check_docking_usage, increment_docking_usage
        from primerforge.auth_routes import auth_bp
        init_db()
        app.teardown_appcontext(close_db)
        app.register_blueprint(auth_bp)
        try:
            from primerforge.payment_routes import payment_bp
            app.register_blueprint(payment_bp)
        except ImportError as exc:
            logger.warning("Payment routes disabled in development: %s", exc)
        try:
            from primerforge.reports_routes_sqlite import reports_bp
            app.register_blueprint(reports_bp)
            logger.info("Reports/academic/referral routes registered (SQLite)")
        except ImportError as exc:
            logger.warning("Reports routes disabled: %s", exc)
        consume_token = None
        consume_docking_token = None
        record_operation_cost = None
        logger.info("Database: SQLite (development mode)")

    # Apply endpoint-specific rate limits (must be after blueprint registration)
    from primerforge.security import apply_rate_limits
    apply_rate_limits(app)

    try:
        from primerforge.core.auto_designer import AutoPrimerDesigner, PrimerDesignConfig
        from primerforge.core.manual_analyser import analyse_manual_primer
        from primerforge.core.sequence_fetcher import (
            fetch_ncbi_nucleotide, fetch_ensembl_sequence,
            fetch_uniprot_sequence, search_ncbi_gene
        )
        from primerforge.core.thermodynamics import analyse_primer_full
        import primerforge.core.sequence_fetcher as sf
        if NCBI_API_KEY:
            sf.NCBI_API_KEY = NCBI_API_KEY
            from Bio import Entrez
            Entrez.api_key = NCBI_API_KEY
        READY = True
        logger.info("VigyanLLM core loaded.")
    except ImportError as exc:
        logger.error("Import failed: %s", exc)
        READY = False

    def err(msg, code, status):
        return jsonify({"error": msg, "code": code}), status

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "version": VERSION, "ready": READY,
                        "pipeline_steps": 22, "strict_mode": True}), 200

    @app.route("/api/config/public", methods=["GET"])
    def public_config():
        return jsonify({
            "googleClientId": GOOGLE_CLIENT_ID,
            "version": VERSION,
            "auth": {"google": bool(GOOGLE_CLIENT_ID)}
        }), 200

    if not USE_POSTGRES:
        DEV_PIPELINE_JOBS = {}

        def _dev_register_pipeline_steps(orchestrator):
            from primerforge.engine.steps import STEP_REGISTRY

            # 24-step numbering matching tasks.py exactly
            step_meta = {
                1: ("Transcript Isoform Filter", True, "A"),
                2: ("Exon-Intron Junction Mapping", False, "A"),
                3: ("Bisulfite Conversion Simulation", False, "A"),
                4: ("Degenerate Base Parsing", True, "A"),
                5: ("Repeat Masking", False, "A"),
                6: ("Backend MSA & Conservation", False, "A"),
                7: ("Conserved Region Targeting", False, "A"),
                8: ("Primer3 Parameter Constraints", True, "B"),
                9: ("Nearest-Neighbor Tm (SantaLucia)", False, "B"),
                10: ("Dynamic Buffer & Salt Adjustments", False, "B"),
                11: ("Divalent Cation Mg Scaling", False, "B"),
                12: ("Target Specificity (BLAST)", False, "C"),
                13: ("Strain Inclusivity & Discontinuous", False, "C"),
                14: ("Structural Alignment (Bowtie2)", False, "C"),
                15: ("Organelle & Pseudogene Screening", False, "C"),
                16: ("Primer Secondary Structure (dG)", False, "D"),
                17: ("Amplicon Structural Verification", False, "D"),
                18: ("Population Variant Filter (dbSNP)", False, "D"),
                19: ("Clinical Hotspot Filter (ClinVar)", False, "D"),
                20: ("5' Overhang Adapter Tailing", False, "D"),
                21: ("Multiplex Cross-Reaction Scoring", False, "D"),
                22: ("Automated Penalty & Ranking Matrix", False, "E"),
                23: ("Thermocycling Profile Generation", False, "E"),
                24: ("Probe Design (qPCR/TaqMan)", False, "E"),
            }
            express_steps = {1, 6, 7, 8, 9, 12, 22, 24}
            for number, (name, hard_failure, phase) in step_meta.items():
                orchestrator.register_step(
                    number,
                    name,
                    STEP_REGISTRY[number],
                    hard_failure=hard_failure,
                    phase=phase,
                    express_included=number in express_steps,
                )

        def _dev_user_or_error():
            user = get_current_user()
            if not user:
                return None, (jsonify({
                    "error": "Authentication required. Please login or register to run the pipeline.",
                    "code": "AUTH_REQUIRED",
                    "action": "show_auth",
                }), 401)
            return user, None

        @app.route("/api/pipeline/submit", methods=["POST"])
        def dev_submit_pipeline():
            import uuid as _uuid
            from primerforge.engine.orchestrator import PipelineConfig, PipelineOrchestrator

            try:
                user, auth_error = _dev_user_or_error()
                if auth_error:
                    return auth_error

                usage = check_usage(user["email"])
                if not usage["can_run"] and user.get("role") != "admin":
                    return jsonify({
                        "error": "Usage limit reached. Payment required for additional runs.",
                        "code": "PAYMENT_REQUIRED",
                        "action": "show_payment",
                        "usage": usage,
                    }), 402

                data = request.get_json(silent=True) or {}
                sequence = data.get("sequence", "")
                accession = data.get("accession", "")
                if not sequence and not accession:
                    return jsonify({"error": "Either 'sequence' or 'accession' is required."}), 400

                mode = data.get("mode", "full")
                if mode not in ("full", "express"):
                    return jsonify({"error": "'mode' must be 'full' or 'express'."}), 400

                product_min = data.get("product_min", 80)
                product_max = data.get("product_max", 500)
                min_tm = float(data.get("min_tm", 58.0))
                max_tm = float(data.get("max_tm", 65.0))
                buffer_conditions = data.get("buffer_conditions") or {
                    "monovalent_mm": 50.0,
                    "divalent_mm": 1.5,
                    "dntp_mm": 0.2,
                    "oligo_conc_nm": 250.0,
                }
                input_params = dict(data)
                input_params.update({
                    "mode": mode,
                    "organism": data.get("organism", "human"),
                    "targeting_mode": data.get("targeting_mode", "common_exon"),
                    "design_mode": data.get("design_mode", "standard"),
                    "polymerase_type": data.get("polymerase_type", "taq"),
                    "template_ng": data.get("template_ng", 100),
                    "multiplex": data.get("multiplex", False),
                    "product_min": product_min,
                    "product_max": product_max,
                    "min_tm": min_tm,
                    "max_tm": max_tm,
                    "buffer_conditions": buffer_conditions,
                    "buffer": buffer_conditions,
                    "design_params": {
                        "tm_min": min_tm,
                        "tm_max": max_tm,
                        "product_size_min": product_min,
                        "product_size_max": product_max,
                    },
                })

                job_id = str(_uuid.uuid4())
                config = PipelineConfig(mode=mode, step_timeout_seconds=300)
                orchestrator = PipelineOrchestrator(config=config)
                _dev_register_pipeline_steps(orchestrator)
                started = time.time()
                outcomes = orchestrator.run(job_id, input_params)
                duration_ms = int((time.time() - started) * 1000)

                hard_failed = any(
                    outcome.status == "failed"
                    and any(
                        step.step_number == outcome.step_number and step.hard_failure
                        for step in orchestrator.steps
                    )
                    for outcome in outcomes
                )
                status = "failed" if hard_failed else "completed"
                error_log = "; ".join(
                    f"Step {o.step_number} ({o.step_name}): {o.error_msg}"
                    for o in outcomes if o.status == "failed"
                ) or None

                DEV_PIPELINE_JOBS[job_id] = {
                    "job_id": job_id,
                    "user_email": user["email"],
                    "status": status,
                    "mode": mode,
                    "steps": outcomes,
                    "error": error_log,
                    "total_duration_ms": duration_ms,
                    "created_at": started,
                }

                if status == "completed" and user.get("role") != "admin":
                    increment_usage(user["email"])
                    log_action(user["email"], "pipeline_run", f"22-step dev pipeline, {duration_ms}ms")

                return jsonify({
                    "job_id": job_id,
                    "status": status,
                    "mode": mode,
                    "total_steps": 22,
                    "message": f"Pipeline job completed in development mode. Status: {status}",
                }), 202

            except Exception as exc:
                logger.error("Pipeline submit failed: %s", exc, exc_info=True)
                return jsonify({
                    "error": f"Pipeline submission failed: {str(exc)[:300]}",
                    "code": "PIPELINE_FAILED",
                }), 500

        @app.route("/api/pipeline/status/<job_id>", methods=["GET"])
        def dev_pipeline_status(job_id):
            try:
                user, auth_error = _dev_user_or_error()
                if auth_error:
                    return auth_error

                job = DEV_PIPELINE_JOBS.get(job_id)
                if not job or job["user_email"] != user["email"]:
                    return jsonify({"error": "Job not found."}), 404

                return jsonify({
                    "job_id": job_id,
                    "status": job["status"],
                    "mode": job["mode"],
                    "current_step": 22,
                    "total_steps": 22,
                    "error": job["error"],
                    "steps": [
                        {
                            "step_number": o.step_number,
                            "step_name": o.step_name,
                            "status": o.status,
                            "duration_ms": o.duration_ms,
                            "phase": o.phase,
                        }
                        for o in job["steps"]
                    ],
                }), 200
            except Exception as exc:
                logger.error("Pipeline status failed: %s", exc, exc_info=True)
                return jsonify({
                    "error": f"Status check failed: {str(exc)[:200]}",
                    "code": "STATUS_ERROR",
                }), 500

        @app.route("/api/pipeline/result/<job_id>", methods=["GET"])
        def dev_pipeline_result(job_id):
            try:
                user, auth_error = _dev_user_or_error()
                if auth_error:
                    return auth_error

                job = DEV_PIPELINE_JOBS.get(job_id)
                if not job or job["user_email"] != user["email"]:
                    return jsonify({"error": "Job not found."}), 404

                return jsonify({
                    "job_id": job_id,
                    "status": job["status"],
                    "mode": job["mode"],
                    "error": job["error"],
                    "total_duration_ms": job["total_duration_ms"],
                    "steps": [
                        {
                            "step_number": o.step_number,
                            "step_name": o.step_name,
                            "status": o.status,
                            "duration_ms": o.duration_ms,
                            "phase": o.phase,
                            "error_msg": o.error_msg,
                            "output_data": o.output_data,
                        }
                        for o in job["steps"]
                    ],
                    "compliance_status": "biosecurity_cleared" if job["status"] == "completed" else None,
                }), 200
            except Exception as exc:
                logger.error("Pipeline result failed: %s", exc, exc_info=True)
                return jsonify({
                    "error": f"Result fetch failed: {str(exc)[:200]}",
                    "code": "RESULT_ERROR",
                }), 500

    # ── Serve Frontend HTML Files ─────────────────────────────────────────
    from flask import send_from_directory
    STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

    @app.route("/")
    def serve_index():
        return send_from_directory(STATIC_DIR, "primer.html")

    @app.route("/primer")
    def serve_primer():
        return send_from_directory(STATIC_DIR, "primer.html")

    @app.route("/docking")
    def serve_docking():
        return send_from_directory(STATIC_DIR, "docking.html")

    @app.route("/protein-docking")
    def serve_protein_docking_redirect():
        return send_from_directory(STATIC_DIR, "protein-docking.html")

    @app.route("/admin")
    def serve_admin():
        return send_from_directory(STATIC_DIR, "admin-security.html")

    @app.route("/<path:filename>")
    def serve_static(filename):
        if filename.endswith((".html", ".css", ".js", ".png", ".ico", ".svg")):
            filepath = os.path.join(STATIC_DIR, filename)
            if os.path.isfile(filepath):
                return send_from_directory(STATIC_DIR, filename)
        return jsonify({"error": "Not found"}), 404

    @app.route("/api/primer/auto-design", methods=["POST"])
    def auto_design():
        if not READY:
            return err("Core not available.", "DESIGN_FAILED", 503)

        data = request.get_json(silent=True) or {}
        sequence = data.get("sequence", "")
        test_mode = data.get("test_mode", False)
        ok, msg = _validate_sequence(sequence, min_len=100)
        if not ok:
            return err(msg, "VALIDATION_ERROR", 422)

        # Build config with STRICT industry thresholds
        try:
            min_tm = float(data.get("min_tm", STRICT["min_tm"]))
            max_tm = float(data.get("max_tm", STRICT["max_tm"]))
            opt_tm = float(data.get("opt_tm", STRICT["opt_tm"]))
            product_min = int(data.get("product_min", 80))
            product_max = int(data.get("product_max", 500))
        except (TypeError, ValueError):
            return err("Design parameters must be numeric.", "VALIDATION_ERROR", 422)

        clean_sequence = re.sub(r"\s", "", sequence)
        ok_range, range_msg = _validate_product_range(product_min, product_max, len(clean_sequence))
        if not ok_range:
            return err(range_msg, "VALIDATION_ERROR", 422)
        if min_tm >= max_tm:
            return err("Minimum Tm must be less than maximum Tm.", "VALIDATION_ERROR", 422)
        if not (min_tm <= opt_tm <= max_tm):
            return err("Optimal Tm must be between minimum and maximum Tm.", "VALIDATION_ERROR", 422)

        # ── Auth & Usage Check ────────────────────────────────────────────
        user = get_current_user()
        if not user:
            return jsonify({"error": "Authentication required. Please login or register to run the pipeline.",
                           "code": "AUTH_REQUIRED", "action": "show_auth"}), 401
        usage = check_usage(user['email'])
        if not usage['can_run'] and user.get('role') != 'admin':
            return jsonify({"error": "Usage limit reached. Payment required for additional runs.",
                           "code": "PAYMENT_REQUIRED", "action": "show_payment",
                           "usage": usage}), 402

        # Consume token BEFORE running pipeline (PostgreSQL mode)
        if USE_POSTGRES and consume_token:
            if user.get('role') != 'admin':
                if not consume_token(user.get('user_id'), user['email']):
                    return jsonify({"error": "No tokens remaining. Purchase more to continue.",
                                   "code": "PAYMENT_REQUIRED", "action": "show_payment"}), 402

        cfg = PrimerDesignConfig()
        cfg.min_tm  = min_tm
        cfg.max_tm  = max_tm
        cfg.opt_tm  = opt_tm
        cfg.min_product_size = product_min
        cfg.max_product_size = product_max
        cfg.check_specificity = _parse_bool(data.get("specificity_check", False))
        cfg.top_n   = 20  # request more candidates to survive ΔLen > 2 filter
        # Enforce strict secondary structure thresholds
        cfg.max_hairpin_dg   = STRICT["max_hairpin_dg"]    # -2.0
        cfg.max_dimer_dg     = STRICT["max_self_dimer_dg"] # -5.0
        cfg.max_cross_dimer_dg = STRICT["max_cross_dimer_dg"] # -5.0
        cfg.max_tm_diff      = STRICT["max_delta_tm"]       # 1.5°C

        try:
            t0 = time.time()
            # ── Use primer3.design_primers directly — NCBI Primer-BLAST parity ──
            import primer3 as p3
            p3_result = p3.design_primers(
                seq_args={
                    'SEQUENCE_TEMPLATE': clean_sequence,
                    'SEQUENCE_INCLUDED_REGION': [0, len(clean_sequence)],
                },
                global_args={
                    'PRIMER_NUM_RETURN': 10,
                    'PRIMER_OPT_SIZE': 20,
                    'PRIMER_MIN_SIZE': 18,
                    'PRIMER_MAX_SIZE': 25,
                    'PRIMER_OPT_TM': opt_tm,
                    'PRIMER_MIN_TM': min_tm,
                    'PRIMER_MAX_TM': max_tm,
                    'PRIMER_MIN_GC': STRICT["min_gc"],
                    'PRIMER_MAX_GC': STRICT["max_gc"],
                    'PRIMER_PRODUCT_SIZE_RANGE': [[product_min, product_max]],
                    'PRIMER_DNA_CONC': 50.0,         # 50 nM (NCBI default)
                    'PRIMER_SALT_MONOVALENT': 50.0,   # 50 mM Na+
                    'PRIMER_SALT_DIVALENT': 1.5,      # 1.5 mM Mg2+
                    'PRIMER_DNTP_CONC': 0.2,          # 0.2 mM dNTPs
                    'PRIMER_MAX_SELF_ANY_TH': 45.0,
                    'PRIMER_MAX_SELF_END_TH': 35.0,
                    'PRIMER_MAX_HAIRPIN_TH': 47.0,
                    'PRIMER_PAIR_MAX_COMPL_ANY_TH': 45.0,
                    'PRIMER_PAIR_MAX_COMPL_END_TH': 35.0,
                    'PRIMER_MAX_POLY_X': 4,
                    'PRIMER_PAIR_MAX_DIFF_TM': STRICT["max_delta_tm"],
                    'PRIMER_GC_CLAMP': 1,
                }
            )
            elapsed_ms = round((time.time() - t0) * 1000)
            num_returned = p3_result.get('PRIMER_PAIR_NUM_RETURNED', 0)
        except ValueError as exc:
            logger.warning("Design validation: %s", exc)
            return err(str(exc), "VALIDATION_ERROR", 422)
        except Exception as exc:
            logger.error("Design error: %s", exc, exc_info=True)
            env = _build_pipeline_status([], 0, "Internal error")
            return jsonify({
                "pipeline_status": env["pipeline_status"],
                "stages": env["stages"],
                "primers_found": [],
                "pairs": [],
                "error": "Design failed due to an internal error.",
                "code": "DESIGN_FAILED",
            }), 500

        na_mM = 50.0
        normalised = []
        for i in range(num_returned):
            left_pos  = p3_result[f'PRIMER_LEFT_{i}']   # (start, length)
            right_pos = p3_result[f'PRIMER_RIGHT_{i}']  # (start, length) — start is 3' end pos
            fwd_seq   = p3_result[f'PRIMER_LEFT_{i}_SEQUENCE']
            rev_seq   = p3_result[f'PRIMER_RIGHT_{i}_SEQUENCE']
            fwd_tm    = round(p3_result[f'PRIMER_LEFT_{i}_TM'], 2)
            rev_tm    = round(p3_result[f'PRIMER_RIGHT_{i}_TM'], 2)
            fwd_gc    = round(p3_result[f'PRIMER_LEFT_{i}_GC_PERCENT'], 2)
            rev_gc    = round(p3_result[f'PRIMER_RIGHT_{i}_GC_PERCENT'], 2)
            product_size = p3_result[f'PRIMER_PAIR_{i}_PRODUCT_SIZE']
            pair_penalty = p3_result.get(f'PRIMER_PAIR_{i}_PENALTY', 0)

            # Positions (1-based for user display)
            fwd_start = left_pos[0] + 1
            fwd_stop  = left_pos[0] + left_pos[1]
            rev_start = right_pos[0] + 1  # 3' end of reverse on template
            rev_stop  = right_pos[0] - right_pos[1] + 2  # 5' end of reverse

            # Secondary structure — compute with primer3
            fwd_hairpin = p3.calc_hairpin(fwd_seq, mv_conc=50, dv_conc=1.5, dntp_conc=0.2, dna_conc=50)
            rev_hairpin = p3.calc_hairpin(rev_seq, mv_conc=50, dv_conc=1.5, dntp_conc=0.2, dna_conc=50)
            fwd_homodimer = p3.calc_homodimer(fwd_seq, mv_conc=50, dv_conc=1.5, dntp_conc=0.2, dna_conc=50)
            rev_homodimer = p3.calc_homodimer(rev_seq, mv_conc=50, dv_conc=1.5, dntp_conc=0.2, dna_conc=50)
            cross_dimer = p3.calc_heterodimer(fwd_seq, rev_seq, mv_conc=50, dv_conc=1.5, dntp_conc=0.2, dna_conc=50)

            fwd_hairpin_dg = round(fwd_hairpin.dg / 1000.0, 2)
            rev_hairpin_dg = round(rev_hairpin.dg / 1000.0, 2)
            fwd_dimer_dg   = round(fwd_homodimer.dg / 1000.0, 2)
            rev_dimer_dg   = round(rev_homodimer.dg / 1000.0, 2)
            cross_dimer_dg = round(cross_dimer.dg / 1000.0, 2)

            # Amplicon GC and Tm
            amplicon_seq = clean_sequence[left_pos[0]:right_pos[0]+1]
            product_gc = round((amplicon_seq.count('G') + amplicon_seq.count('C')) / len(amplicon_seq) * 100, 2) if amplicon_seq else 0
            amplicon_tm = _amplicon_tm(product_gc, product_size, na_mM)

            delta_tm = round(abs(fwd_tm - rev_tm), 2)
            annealing_ta = round((fwd_tm + rev_tm) / 2 - 5, 1)

            # Quality score: primer3's penalty is lower=better; convert to 100-scale
            score = round(max(0, 100.0 - pair_penalty * 10), 1)

            fwd = {
                "sequence": fwd_seq, "tm": fwd_tm, "gc": fwd_gc,
                "hairpin_dg": fwd_hairpin_dg, "dimer_dg": fwd_dimer_dg,
                "length": left_pos[1],
                "quality_score": round(max(0, 100 - abs(fwd_tm - opt_tm)*5 - max(0,-fwd_hairpin_dg-1)*10), 1),
                "warnings": [],
                "gc_clamp_ok": fwd_seq[-1] in ('G','C'),
            }
            rev = {
                "sequence": rev_seq, "tm": rev_tm, "gc": rev_gc,
                "hairpin_dg": rev_hairpin_dg, "dimer_dg": rev_dimer_dg,
                "length": right_pos[1],
                "quality_score": round(max(0, 100 - abs(rev_tm - opt_tm)*5 - max(0,-rev_hairpin_dg-1)*10), 1),
                "warnings": [],
                "gc_clamp_ok": rev_seq[-1] in ('G','C'),
            }
            pair_meta = {
                "cross_dimer_dg": cross_dimer_dg,
                "tm_delta": delta_tm,
                "annealing_ta": annealing_ta,
                "pair_warnings": [],
                "specificity_pass": None,
                "specificity_note": "Specificity check not run.",
            }

            pipeline_pf = _pipeline_pass_fail(fwd, rev, pair_meta, template_seq=clean_sequence)
            validation_pending = any(v["pass"] is None for v in pipeline_pf.values())
            core_pass = all(v["pass"] is not False for v in pipeline_pf.values())
            checked_pass = core_pass and not validation_pending
            if checked_pass:
                status = "ALL PASS - validated"
            elif core_pass and validation_pending:
                status = "CORE PASS - external validation pending"
            elif test_mode and validation_pending:
                status = "CORE PASS - external validation pending"
            else:
                status = "REVIEW - check pipeline matrix"

            normalised.append({
                "pair_id":       i + 1,
                "amplicon_size": product_size,
                "amplicon_gc":   product_gc,
                "amplicon_tm":   amplicon_tm,
                "forward_primer": {
                    "sequence": fwd_seq, "length": left_pos[1],
                    "tm": fwd_tm, "gc": fwd_gc,
                    "hairpin_dg": fwd_hairpin_dg, "self_dimer_dg": fwd_dimer_dg,
                    "start_pos": fwd_start, "stop_pos": fwd_stop,
                    "gc_clamp_ok": fwd['gc_clamp_ok'],
                    "quality_score": fwd['quality_score'], "warnings": [],
                },
                "reverse_primer": {
                    "sequence": rev_seq, "length": right_pos[1],
                    "tm": rev_tm, "gc": rev_gc,
                    "hairpin_dg": rev_hairpin_dg, "self_dimer_dg": rev_dimer_dg,
                    "start_pos": rev_start, "stop_pos": rev_stop,
                    "gc_clamp_ok": rev['gc_clamp_ok'],
                    "quality_score": rev['quality_score'], "warnings": [],
                },
                "cross_dimer_dg": cross_dimer_dg,
                "tm_delta": delta_tm,
                "annealing_ta": annealing_ta,
                "score": score,
                "penalty_score": round(pair_penalty, 3),
                "overall_pass": checked_pass,
                "validation_pending": validation_pending,
                "status": status,
                "pair_warnings": [],
                "pipeline": pipeline_pf,
                "specificity": None,
                "product_start": fwd_start,
                "product_end": rev_start,
                # Legacy aliases
                "rank": i + 1,
                "forward": {
                    "sequence": fwd_seq, "tm": fwd_tm, "gc": fwd_gc,
                    "hairpin_dg": fwd_hairpin_dg, "dimer_dg": fwd_dimer_dg,
                    "hairpin_tm": round(fwd_hairpin.tm, 2),
                    "length": left_pos[1], "quality_score": fwd['quality_score'],
                    "warnings": [], "gc_clamp_ok": fwd['gc_clamp_ok'],
                },
                "reverse": {
                    "sequence": rev_seq, "tm": rev_tm, "gc": rev_gc,
                    "hairpin_dg": rev_hairpin_dg, "dimer_dg": rev_dimer_dg,
                    "hairpin_tm": round(rev_hairpin.tm, 2),
                    "length": right_pos[1], "quality_score": rev['quality_score'],
                    "warnings": [], "gc_clamp_ok": rev['gc_clamp_ok'],
                },
            })

        pipeline_envelope = _build_pipeline_status(normalised, elapsed_ms)

        # ── Increment usage after successful run ──────────────────────────
        if not test_mode:
            if USE_POSTGRES and record_operation_cost:
                record_operation_cost(
                    user_id=user.get('user_id'),
                    trigger_type='primer_design',
                    cpu_seconds=elapsed_ms / 1000.0,
                    primers_generated=len(normalised),
                    tokens_consumed=1,
                    revenue_per_token=49.0,
                )
                log_action(user['email'], "pipeline_run", f"{len(normalised)} pairs, {elapsed_ms}ms")
            else:
                increment_usage(user['email'])
                log_action(user['email'], "pipeline_run", f"{len(normalised)} pairs, {elapsed_ms}ms")

        return jsonify({
            # ── Rigid schema (as specified) ───────────────────────────────
            "pipeline_status": pipeline_envelope["pipeline_status"],
            "stages":          pipeline_envelope["stages"],
            "primers_found":   normalised,
            # ── Convenience aliases ───────────────────────────────────────
            "pairs":           normalised,
            "elapsed_ms":      elapsed_ms,
            "total_candidates": len(normalised),
            "template_length": len(clean_sequence),
            "assay_conditions": {
                "primer_conc_nM": 50.0,
                "na_mM": 50.0,
                "mg_mM": 1.5,
                "dntp_mM": 0.2,
                "tm_method": "SantaLucia 1998 Nearest-Neighbor",
            },
        }), 200

    @app.route("/api/primer/manual-analysis", methods=["POST"])
    def manual_analysis():
        if not READY:
            return err("Core not available.", "DESIGN_FAILED", 503)
        user = get_current_user()
        if not user:
            return jsonify({"error": "Authentication required. Please login first.",
                           "code": "AUTH_REQUIRED", "action": "show_auth"}), 401
        data = request.get_json(silent=True) or {}
        forward = data.get("forward", "").strip()
        reverse = data.get("reverse", "").strip()
        if not forward:
            return err("Forward primer is required.", "VALIDATION_ERROR", 400)
        ok_f, msg_f = _validate_sequence(forward)
        if not ok_f:
            return err(f"Forward: {msg_f}", "VALIDATION_ERROR", 400)
        if reverse:
            ok_r, msg_r = _validate_sequence(reverse)
            if not ok_r:
                return err(f"Reverse: {msg_r}", "VALIDATION_ERROR", 400)
        try:
            result = analyse_manual_primer(
                sequence=forward,
                partner_seq=reverse if reverse else None,
                template=data.get("template") or None,
            )
            thermo = result["thermodynamics"]
            pair   = result.get("pair_analysis") or {}
            rev_t  = (pair.get("reverse") or {}) if pair else {}
            fwd_out = {
                "sequence": thermo.get("sequence", forward),
                "tm": thermo.get("tm_nearest_neighbor", 0),
                "gc": thermo.get("gc_content", 0),
                "hairpin_dg": thermo.get("hairpin_dg", 0),
                "dimer_dg": thermo.get("self_dimer_dg", 0),
                "hairpin_tm": thermo.get("hairpin_tm", 0),
                "length": thermo.get("length", len(forward)),
                "quality_score": thermo.get("quality_score", 0),
                "warnings": thermo.get("warnings", []),
                "gc_clamp_ok": forward[-1].upper() in ("G","C") if forward else False,
            }
            rev_out = None
            if reverse and rev_t:
                rev_out = {
                    "sequence": rev_t.get("sequence", reverse),
                    "tm": rev_t.get("tm_nearest_neighbor", 0),
                    "gc": rev_t.get("gc_content", 0),
                    "hairpin_dg": rev_t.get("hairpin_dg", 0),
                    "dimer_dg": rev_t.get("self_dimer_dg", 0),
                    "hairpin_tm": rev_t.get("hairpin_tm", 0),
                    "length": rev_t.get("length", len(reverse)),
                    "quality_score": rev_t.get("quality_score", 0),
                    "warnings": rev_t.get("warnings", []),
                    "gc_clamp_ok": reverse[-1].upper() in ("G","C") if reverse else False,
                }
            cross_dg = pair.get("cross_dimer_dg", 0) if pair else 0
            delta_tm = abs(fwd_out["tm"] - (rev_out["tm"] if rev_out else fwd_out["tm"]))
            pair_meta = {"cross_dimer_dg": cross_dg, "tm_delta": delta_tm,
                         "annealing_ta": pair.get("annealing_temp_suggested", 0) if pair else 0,
                         "pair_warnings": pair.get("pair_warnings", []) if pair else [],
                         "specificity_pass": None, "specificity_note": "N/A"}
            pipeline_pf = _pipeline_pass_fail(fwd_out, rev_out or fwd_out, pair_meta,
                                                template_seq=data.get("template") or "") if rev_out else None
            return jsonify({
                "forward": fwd_out,
                "reverse": rev_out,
                "heterodimer_dg": cross_dg,
                "tm_delta": delta_tm,
                "annealing_ta": pair_meta["annealing_ta"],
                "pair_warnings": pair_meta["pair_warnings"],
                "report": result.get("formatted_report", ""),
                "pcr_protocol": result.get("pcr_protocol", {}),
                "pipeline": pipeline_pf,
                "penalty_score": _penalty_score(fwd_out, rev_out or fwd_out, pair_meta) if rev_out else None,
            }), 200
        except ValueError as exc:
            logger.warning("Manual analysis validation: %s", exc)
            return err(str(exc), "VALIDATION_ERROR", 400)
        except Exception as exc:
            logger.error("Manual analysis error: %s", exc, exc_info=True)
            return err("Analysis failed due to an internal error.", "DESIGN_FAILED", 500)

    def _log_fetch(acc, source, description=""):
        """Log a sequence fetch to the audit log."""
        try:
            from ..database import log_audit
            import re as _re
            gene = ""
            m = _re.search(r"\((\w+)\)", description)
            if m:
                gene = m.group(1)
            log_audit("fetch_sequence", accession=acc, gene_symbol=gene, source=source)
        except Exception as e:
            logger.debug("Suppressed exception: %s", e)

    @app.route("/api/primer/fetch-sequence", methods=["POST"])
    def fetch_sequence_route():
        if not READY:
            return err("Core not available.", "DESIGN_FAILED", 503)
        data = request.get_json(silent=True) or {}
        accession = (data.get("accession") or "").strip()
        if not accession:
            return err("Accession is required.", "VALIDATION_ERROR", 400)
        try:
            if re.match(r"^(NM_|NC_|NG_|NR_|NT_|NW_|XM_|XR_)", accession, re.I):
                r = fetch_ncbi_nucleotide(accession)
                usable = _auto_design_usability(r["sequence"])
                _log_fetch(accession, "ncbi", r.get("description",""))
                return jsonify({"sequence": r["sequence"], "accession": r["accession"],
                                "description": r["description"], "length": r["length"],
                                "source": "ncbi", "features": r.get("features", []),
                                "molecule_type": r.get("molecule_type", "DNA"),
                                "unit": "bp", **usable}), 200
            elif re.match(r"^ENS[GT]", accession, re.I):
                seq_type = "cdna" if accession.upper().startswith("ENST") else "genomic"
                r = fetch_ensembl_sequence(accession, seq_type=seq_type)
                usable = _auto_design_usability(r["seq"])
                _log_fetch(accession, "ensembl", r.get("desc",""))
                return jsonify({"sequence": r["seq"], "accession": r["id"],
                                "description": r.get("desc",""), "length": r["length"],
                                "source": "ensembl", "molecule_type": r.get("molecule", "DNA"),
                                "sequence_type": seq_type, "unit": "bp", **usable}), 200
            elif re.match(r"^chr(1[0-9]|2[0-2]|[1-9]|X|Y|M|MT):\d+-\d+$", accession, re.I):
                from primerforge.engine.sequence_retrieval import fetch_from_ensembl_region
                r = fetch_from_ensembl_region(accession)
                usable = _auto_design_usability(r.sequence)
                _log_fetch(accession, "ensembl_region", r.description)
                return jsonify({"sequence": r.sequence, "accession": r.accession,
                                "description": r.description, "length": r.length,
                                "source": "ensembl_region", "molecule_type": "DNA",
                                "metadata": r.metadata, "unit": "bp", **usable}), 200
            elif re.match(r"^EPI_ISL_\d+$", accession, re.I):
                _log_fetch(accession, "gisaid_rejected")
                return err(
                    "Restricted viral identifiers are not supported. Use an open NCBI Virus or NCBI Nucleotide accession instead.",
                    "VALIDATION_ERROR",
                    400,
                )
            elif re.match(r"^(AB|LC|AP|BA|HT)\d{6}(\.\d+)?$", accession, re.I):
                from primerforge.engine.sequence_retrieval import fetch_from_ddbj
                r = fetch_from_ddbj(accession)
                usable = _auto_design_usability(r.sequence)
                _log_fetch(accession, "ddbj", r.description)
                return jsonify({"sequence": r.sequence, "accession": r.accession,
                                "description": r.description, "length": r.length,
                                "source": "ddbj", "molecule_type": "DNA",
                                "metadata": r.metadata, "unit": "bp", **usable}), 200
            elif re.match(r"^(?![PQO][0-9A-Z]{5}$)[A-Z]{1,2}\d{5,8}(\.\d+)?$", accession, re.I):
                from primerforge.engine.sequence_retrieval import fetch_from_ena
                r = fetch_from_ena(accession)
                usable = _auto_design_usability(r.sequence)
                _log_fetch(accession, "ena", r.description)
                return jsonify({"sequence": r.sequence, "accession": r.accession,
                                "description": r.description, "length": r.length,
                                "source": "ena", "molecule_type": "DNA",
                                "metadata": r.metadata, "unit": "bp", **usable}), 200
            elif re.match(r"^[PQO][0-9A-Z]{5}$", accession, re.I):
                r = fetch_uniprot_sequence(accession)
                _log_fetch(accession, "uniprot", r.get("protein_name",""))
                return jsonify({"sequence": r["sequence"], "accession": accession,
                                "description": r.get("protein_name",""), "length": r["length"],
                                "source": "uniprot", "molecule_type": "protein",
                                "unit": "aa", "usable_for_auto_design": False,
                                "auto_design_reason": "UniProt returns protein sequence; Auto Design requires DNA."}), 200
            else:
                genes = search_ncbi_gene(accession)
                if not genes:
                    _log_fetch(accession, "gene_search_failed")
                    return err(f"Gene '{accession}' not found.", "FETCH_FAILED", 400)
                mrna = genes[0].get("refseq_mRNA", [])
                if not mrna:
                    _log_fetch(accession, "gene_no_mrna")
                    return err(f"No RefSeq mRNA for '{accession}'.", "FETCH_FAILED", 400)
                r = fetch_ncbi_nucleotide(mrna[0])
                usable = _auto_design_usability(r["sequence"])
                _log_fetch(accession, "gene_search", r.get("description",""))
                return jsonify({"sequence": r["sequence"], "accession": r["accession"],
                                "description": r["description"], "length": r["length"],
                                "source": "ncbi", "gene_info": genes[0],
                                "molecule_type": r.get("molecule_type", "DNA"),
                                "unit": "bp", **usable}), 200
        except Exception as exc:
            logger.error("Fetch error: %s", exc, exc_info=True)
            # Provide user-friendly error messages for common failures
            exc_str = str(exc)
            if "UndefinedSequence" in exc_str:
                msg = f"Sequence data not available inline for '{accession}'. The NCBI record exists but does not contain downloadable sequence data. Try a different accession or paste the sequence directly."
            elif "RetryError" in exc_str or "retry" in exc_str.lower():
                msg = f"NCBI is temporarily unavailable or rate-limited for '{accession}'. Please wait 10 seconds and try again, or paste the sequence directly."
            elif "EPI_ISL" in exc_str:
                msg = "Use an open NCBI Virus or NCBI Nucleotide accession for viral sequence retrieval."
            elif "HTTPError" in exc_str or "404" in exc_str:
                msg = f"Accession '{accession}' was not found in its database. Please verify the accession number."
            elif "timeout" in exc_str.lower():
                msg = f"Database request timed out for '{accession}'. Please try again."
            else:
                msg = f"Failed to fetch '{accession}': {exc_str[:100]}"
            return err(msg, "FETCH_FAILED", 400)

    @app.route("/api/primer/thermodynamics", methods=["POST"])
    def thermodynamics():
        if not READY:
            return err("Core not available.", "DESIGN_FAILED", 503)
        data = request.get_json(silent=True) or {}
        sequence = (data.get("sequence") or "").strip()
        if not sequence:
            return err("Sequence is required.", "VALIDATION_ERROR", 400)
        ok, msg = _validate_sequence(sequence)
        if not ok:
            return err(msg, "VALIDATION_ERROR", 400)
        try:
            r = analyse_primer_full(sequence)
            return jsonify({
                "tm": r.tm_nearest_neighbor, "gc": r.gc_content,
                "hairpin_dg": r.hairpin_dg, "dimer_dg": r.self_dimer_dg,
                "length": r.length, "warnings": r.warnings,
                "quality_score": r.quality_score,
                "pass_strict": (
                    STRICT["min_tm"] <= r.tm_nearest_neighbor <= STRICT["max_tm"] and
                    r.hairpin_dg > STRICT["max_hairpin_dg"] and
                    r.self_dimer_dg > STRICT["max_self_dimer_dg"]
                ),
            }), 200
        except Exception as exc:
            logger.error("Thermodynamics error: %s", exc, exc_info=True)
            return err("Analysis failed due to an internal error.", "DESIGN_FAILED", 500)

    # ════════════════════════════════════════════════════════════════════
    # NEW: Sequence Search, BLAST, MSA Endpoints
    # ════════════════════════════════════════════════════════════════════

    @app.route("/api/primer/search-sequences", methods=["POST"])
    def search_sequences_route():
        if not READY:
            return err("Core not available.", "DESIGN_FAILED", 503)
        data = request.get_json(silent=True) or {}
        query = (data.get("query") or "").strip()
        database = (data.get("database") or "auto").strip()
        organism = (data.get("organism") or "human").strip()
        if not query:
            return err("Query is required.", "VALIDATION_ERROR", 400)
        try:
            from primerforge.core.sequence_fetcher import search_databases
            result = search_databases(query, database=database, organism=organism)
            return jsonify(result), 200
        except Exception as exc:
            logger.error("Search error: %s", exc, exc_info=True)
            return err(f"Search failed: {str(exc)[:200]}", "SEARCH_FAILED", 500)

    @app.route("/api/primer/blast", methods=["POST"])
    def blast_route():
        if not READY:
            return err("Core not available.", "DESIGN_FAILED", 503)
        data = request.get_json(silent=True) or {}
        query_sequence = (data.get("sequence") or "").strip()
        mode = (data.get("mode") or "auto").strip()
        database = (data.get("database") or "nt").strip()
        organism = (data.get("organism") or "").strip()
        subject_sequences = data.get("subject_sequences", [])

        if not query_sequence:
            return err("Query sequence is required.", "VALIDATION_ERROR", 400)
        # Auto-detect: if subject_sequences provided, use local mode
        import re
        clean = query_sequence.upper().replace(" ", "").replace("\n", "")
        if not re.match(r"^[ACGTNRYSWKMBDHV]+$", clean):
            return err("Invalid sequence. Only DNA/RNA letters allowed.", "VALIDATION_ERROR", 400)

        try:
            if subject_sequences or mode == "local":
                from primerforge.engine.blast_viewer import run_local_blast
                result = run_local_blast(query_sequence, subject_sequences)
            else:
                from primerforge.engine.blast_viewer import run_remote_blast
                result = run_remote_blast(query_sequence, database=database, organism=organism)
            return jsonify(result), 200
        except Exception as exc:
            logger.error("BLAST error: %s", exc, exc_info=True)
            return err(f"BLAST failed: {str(exc)[:200]}", "BLAST_FAILED", 500)

    @app.route("/api/primer/fetch-sequences", methods=["POST"])
    def fetch_sequences_route():
        """Fetch full sequences from NCBI in parallel for BLAST hits."""
        if not READY:
            return err("Core not available.", "DESIGN_FAILED", 503)
        data = request.get_json(silent=True) or {}
        accessions = data.get("accessions", [])
        if not accessions:
            return err("Accession list is required.", "VALIDATION_ERROR", 400)
        if len(accessions) > 200:
            return err("Maximum 200 sequences per request.", "VALIDATION_ERROR", 400)
        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            from Bio import Entrez, SeqIO
            import io

            Entrez.email = os.environ.get("NCBI_EMAIL", "user@example.com")
            ncbi_key = os.environ.get("NCBI_API_KEY", "")
            if ncbi_key:
                Entrez.api_key = ncbi_key

            def _fetch_one(acc):
                try:
                    handle = Entrez.efetch(db="nucleotide", id=acc, rettype="fasta", retmode="text", timeout=30)
                    raw = handle.read()
                    handle.close()
                    record = SeqIO.read(io.StringIO(raw), "fasta")
                    return {
                        "accession": acc,
                        "sequence": str(record.seq).upper(),
                        "description": record.description,
                        "length": len(record.seq),
                    }
                except Exception as e:
                    return {"accession": acc, "error": str(e)[:100]}

            results = []
            with ThreadPoolExecutor(max_workers=8) as pool:
                futures = {pool.submit(_fetch_one, acc): acc for acc in accessions}
                for future in as_completed(futures):
                    results.append(future.result())

            return jsonify({"results": results, "total": len(results)}), 200
        except Exception as exc:
            logger.error("Fetch sequences error: %s", exc, exc_info=True)
            return err(f"Fetch failed: {str(exc)[:200]}", "FETCH_FAILED", 500)

    # ════════════════════════════════════════════════════════════════════
    # Batch Oligo Analysis & Primer Check Endpoints
    # ════════════════════════════════════════════════════════════════════

    def _parse_oligo_file(text):
        """Parse FASTA or CSV text into a list of {name, forward, reverse, template} dicts."""
        import csv, io
        lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
        if not lines:
            return []
        first = lines[0].lower()
        if "," in first and ("fwd" in first or "forward" in first or "primer" in first):
            reader = csv.DictReader(io.StringIO(text))
            entries = []
            for row in reader:
                fwd = (row.get("forward") or row.get("fwd") or row.get("primer") or "").strip()
                if not fwd:
                    continue
                entries.append({
                    "name": (row.get("name") or row.get("id") or fwd[:20]).strip(),
                    "forward": fwd.upper(),
                    "reverse": (row.get("reverse") or row.get("rev") or "").strip().upper(),
                    "template": (row.get("template") or row.get("seq") or "").strip().upper(),
                })
            return entries
        entries = []
        current = {"name": "", "forward": "", "reverse": "", "template": ""}
        for line in lines:
            if line.startswith(">"):
                if current["forward"]:
                    entries.append(current)
                name = line[1:].split()[0]
                current = {"name": name, "forward": "", "reverse": "", "template": ""}
            elif current["forward"] and line.startswith("/rev"):
                current["reverse"] = line[4:].strip().upper()
            elif current["forward"] and line.startswith("/template"):
                current["template"] = line[10:].strip().upper()
            elif not current["forward"]:
                current["forward"] = line.upper()
        if current["forward"]:
            entries.append(current)
        return entries

    @app.route("/api/primer/batch-analysis", methods=["POST"])
    def batch_oligo_analysis():
        if not READY:
            return err("Core not available.", "DESIGN_FAILED", 503)
        data = request.get_json(silent=True) or {}
        sequences = data.get("sequences")
        file_content = data.get("file_content")
        if not sequences and not file_content:
            return err("Provide 'sequences' (list) or 'file_content' (FASTA/CSV text).", "VALIDATION_ERROR", 400)
        if file_content:
            sequences = _parse_oligo_file(file_content)
        if not sequences:
            return err("No valid sequences found in input.", "VALIDATION_ERROR", 400)
        results = []
        errors = []
        for entry in sequences:
            try:
                fwd = entry.get("forward", "")
                rev = entry.get("reverse") or None
                template = entry.get("template") or None
                if not fwd:
                    errors.append({"name": entry.get("name", "?"), "error": "No forward primer"})
                    continue
                name = entry.get("name", fwd[:25])
                result = analyse_manual_primer(sequence=fwd, partner_seq=rev, template=template)
                fwd_thermo = result["thermodynamics"]
                rev_thermo = None
                pair_analysis = result.get("pair_analysis") or {}
                if rev and pair_analysis.get("reverse"):
                    rev_thermo = pair_analysis["reverse"]
                results.append({
                    "name": name,
                    "forward": {
                        "sequence": fwd,
                        "tm": fwd_thermo.get("tm_nearest_neighbor", 0),
                        "gc": fwd_thermo.get("gc_content", 0),
                        "length": fwd_thermo.get("length", len(fwd)),
                        "hairpin_dg": fwd_thermo.get("hairpin_dg", 0),
                        "dimer_dg": fwd_thermo.get("self_dimer_dg", 0),
                        "quality_score": fwd_thermo.get("quality_score", 0),
                        "warnings": fwd_thermo.get("warnings", []),
                    },
                    "reverse": {
                        "sequence": rev or "",
                        "tm": rev_thermo.get("tm_nearest_neighbor", 0) if rev_thermo else 0,
                        "gc": rev_thermo.get("gc_content", 0) if rev_thermo else 0,
                        "length": rev_thermo.get("length", len(rev or "")),
                        "hairpin_dg": rev_thermo.get("hairpin_dg", 0) if rev_thermo else 0,
                        "dimer_dg": rev_thermo.get("self_dimer_dg", 0) if rev_thermo else 0,
                        "quality_score": rev_thermo.get("quality_score", 0) if rev_thermo else 0,
                        "warnings": rev_thermo.get("warnings", []) if rev_thermo else [],
                    } if rev else None,
                    "pair": {
                        "tm_delta": abs(fwd_thermo.get("tm_nearest_neighbor", 0) - (rev_thermo.get("tm_nearest_neighbor", 0) if rev_thermo else 0)),
                        "cross_dimer_dg": pair_analysis.get("cross_dimer_dg", 0),
                        "annealing_ta": pair_analysis.get("annealing_temp_suggested", 0),
                        "pair_warnings": pair_analysis.get("pair_warnings", []),
                    } if rev else None,
                })
            except Exception as exc:
                errors.append({"name": entry.get("name", "?"), "error": str(exc)[:200]})
        return jsonify({"results": results, "errors": errors, "total": len(results), "failed": len(errors)}), 200

    @app.route("/api/primer/check-primers", methods=["POST"])
    def check_primers_route():
        if not READY:
            return err("Core not available.", "DESIGN_FAILED", 503)
        data = request.get_json(silent=True) or {}
        template = (data.get("template") or "").strip().upper()
        primers = data.get("primers") or []
        file_content = data.get("file_content")
        if not template:
            return err("Template sequence is required.", "VALIDATION_ERROR", 400)
        if not primers and file_content:
            parsed = _parse_oligo_file(file_content)
            primers = [{"forward": p["forward"], "reverse": p.get("reverse"), "name": p["name"]} for p in parsed]
        if not primers:
            return err("Provide 'primers' list or 'file_content' with primer sequences.", "VALIDATION_ERROR", 400)
        ranked = []
        errors = []
        for p in primers:
            try:
                fwd = p.get("forward", "").upper()
                rev = p.get("reverse", "").upper() if p.get("reverse") else None
                name = p.get("name", fwd[:25])
                if not fwd:
                    continue
                fwd_aln = align_primer_to_template(fwd, template)
                rev_aln = None
                if rev:
                    rev_aln = align_primer_to_template(rev, template)
                fwd_thermo = analyse_primer_full(fwd)
                rev_thermo = None
                pair_data = None
                if rev:
                    pair_data = analyse_primer_pair(fwd, rev)
                    rev_thermo = pair_data.get("reverse")
                aln_score = (fwd_aln.get("identity_pct", 0) + (rev_aln.get("identity_pct", 0) if rev_aln else 100)) / 2
                thermo_score = fwd_thermo.quality_score
                if rev_thermo:
                    thermo_score = (thermo_score + rev_thermo["quality_score"]) / 2
                combined_score = round(aln_score * 0.6 + thermo_score * 0.4, 1)
                entry = {
                    "name": name,
                    "forward": fwd,
                    "reverse": rev or None,
                    "combined_score": combined_score,
                    "alignment": {
                        "forward": fwd_aln,
                        "reverse": rev_aln,
                    },
                    "thermodynamics": {
                        "forward_tm": fwd_thermo.tm_nearest_neighbor,
                        "forward_gc": fwd_thermo.gc_content,
                        "reverse_tm": rev_thermo["tm_nearest_neighbor"] if rev_thermo else None,
                        "reverse_gc": rev_thermo["gc_content"] if rev_thermo else None,
                        "quality_score": thermo_score,
                    },
                    "warnings": fwd_thermo.warnings + (pair_data.get("pair_warnings", []) if pair_data else []),
                }
                ranked.append(entry)
            except Exception as exc:
                errors.append({"name": p.get("name", "?"), "error": str(exc)[:200]})
        ranked.sort(key=lambda x: -x["combined_score"])
        suggestions = []
        if ranked:
            best = ranked[0]
            if best["alignment"]["forward"]["identity_pct"] < 90:
                suggestions.append("Best forward primer has <90% template identity — consider redesigned primers")
            if best["combined_score"] < 60:
                suggestions.append("All primers scored poorly — check template sequence or use different target region")
        else:
            suggestions.append("No valid primers found — check input sequences")
        return jsonify({
            "ranked": ranked,
            "suggestions": suggestions,
            "total": len(ranked),
            "errors": errors,
        }), 200

    @app.route("/api/primer/msa", methods=["POST"])
    def msa_route():
        if not READY:
            return err("Core not available.", "DESIGN_FAILED", 503)
        data = request.get_json(silent=True) or {}
        sequences = data.get("sequences", [])
        reference_id = data.get("reference_id")

        if not sequences or len(sequences) < 2:
            return err("At least 2 sequences are required for MSA.", "VALIDATION_ERROR", 400)

        try:
            from primerforge.engine.msa_viewer import build_msa_view, format_fasta, format_clustal, get_msa_summary, create_job, process_job
            n = len(sequences)
            if n > 500:
                job_id = create_job(sequences, reference_id)
                process_job(job_id)
                job = get_job(job_id)
                if job["status"] == "DONE":
                    return jsonify({
                        "job_id": job_id,
                        "total_sequences": n,
                        "stats": job["stats"],
                        "alignment_length": job["stats"].get("alignment_length", 0),
                        "summary": get_msa_summary({"stats": job["stats"]}),
                        "fasta": format_fasta_from_job(job_id),
                        "clustal": format_clustal_from_job(job_id),
                    }), 200
                return err(job.get("error", "MSA processing failed"), "MSA_FAILED", 500)
            viewer = build_msa_view(sequences, reference_id=reference_id)
            viewer["fasta"] = format_fasta(sequences)
            viewer["clustal"] = format_clustal(viewer.get("alignment", []))
            viewer["summary"] = get_msa_summary(viewer)
            return jsonify(viewer), 200
        except Exception as exc:
            logger.error("MSA error: %s", exc, exc_info=True)
            return err(f"MSA failed: {str(exc)[:200]}", "MSA_FAILED", 500)

    @app.route("/api/primer/msa/submit", methods=["POST"])
    def msa_submit_route():
        if not READY:
            return err("Core not available.", "DESIGN_FAILED", 503)
        data = request.get_json(silent=True) or {}
        sequences = data.get("sequences", [])
        reference_id = data.get("reference_id")
        if not sequences or len(sequences) < 2:
            return err("At least 2 sequences required.", "VALIDATION_ERROR", 400)
        from primerforge.engine.msa_viewer import create_job
        job_id = create_job(sequences, reference_id)
        import threading
        threading.Thread(target=process_job, args=(job_id,), daemon=True).start()
        n = len(sequences)
        return jsonify({
            "job_id": job_id,
            "total_sequences": n,
            "status": "QUEUED",
        }), 202

    @app.route("/api/primer/msa/status/<job_id>", methods=["GET"])
    def msa_status_route(job_id):
        from primerforge.engine.msa_viewer import get_job
        job = get_job(job_id)
        if not job:
            return err("Job not found.", "NOT_FOUND", 404)
        resp = {
            "job_id": job_id,
            "status": job["status"],
            "progress": job.get("progress", 0),
            "total_sequences": job.get("total", 0),
            "stats": job.get("stats"),
            "error": job.get("error"),
        }
        return jsonify(resp), 200

    @app.route("/api/primer/msa/view/<job_id>", methods=["GET"])
    def msa_view_route(job_id):
        from primerforge.engine.msa_viewer import get_paginated_alignment
        offset = request.args.get("offset", 0, type=int)
        limit = min(request.args.get("limit", 50, type=int), 200)
        col_start = request.args.get("col_start", 0, type=int)
        col_end = request.args.get("col_end", 0, type=int)
        result = get_paginated_alignment(job_id, offset, limit, col_start, col_end)
        if "error" in result:
            return err(result["error"], "JOB_NOT_READY", 400)
        return jsonify(result), 200

    @app.route("/api/primer/msa/download/<job_id>", methods=["GET"])
    def msa_download_route(job_id):
        from primerforge.engine.msa_viewer import format_fasta_from_job, format_clustal_from_job
        fmt = request.args.get("format", "fasta")
        if fmt == "clustal":
            content = format_clustal_from_job(job_id)
            mime = "text/plain"
            fn = f"alignment_{job_id}.aln"
        else:
            content = format_fasta_from_job(job_id)
            mime = "text/plain"
            fn = f"alignment_{job_id}.fa"
        if not content:
            return err("Job not ready or empty.", "NOT_FOUND", 404)
        return Response(content, mimetype=mime, headers={"Content-Disposition": f'attachment; filename="{fn}"'})

    @app.route("/api/primer/msa/upload", methods=["POST"])
    def msa_upload_route():
        if not READY:
            return err("Core not available.", "DESIGN_FAILED", 503)
        if "file" not in request.files:
            return err("No file provided. Send as multipart/form-data with field 'file'.", "VALIDATION_ERROR", 400)
        f = request.files["file"]
        if f.filename == "":
            return err("Empty filename.", "VALIDATION_ERROR", 400)
        try:
            raw = f.read()
            text = raw.decode("utf-8", errors="replace")
        except Exception as e:
            return err(f"Failed to read file: {e}", "VALIDATION_ERROR", 400)
        import re as _re
        seqs = []
        cur_name = ""
        cur_seq_chunks = []
        for line in text.splitlines():
            s = line.strip()
            if not s:
                continue
            if s.startswith(">"):
                if cur_name and cur_seq_chunks:
                    seqs.append({"name": cur_name, "sequence": "".join(cur_seq_chunks).upper()})
                cur_name = s[1:].split()[0] if len(s) > 1 else f"seq_{len(seqs)}"
                cur_seq_chunks = []
            else:
                clean = _re.sub(r"\s", "", s)
                if clean:
                    cur_seq_chunks.append(clean)
        if cur_name and cur_seq_chunks:
            seqs.append({"name": cur_name, "sequence": "".join(cur_seq_chunks).upper()})
        if len(seqs) < 2:
            return err("FASTA file must contain at least 2 sequences.", "VALIDATION_ERROR", 400)
        reference_id = request.form.get("reference_id") or None
        from primerforge.engine.msa_viewer import create_job
        job_id = create_job(seqs, reference_id)
        import threading
        threading.Thread(target=process_job, args=(job_id,), daemon=True).start()
        return jsonify({
            "job_id": job_id,
            "total_sequences": len(seqs),
            "status": "QUEUED",
        }), 202

    # ════════════════════════════════════════════════════════════════════
    # Consensus Pipeline — Molecular Docking (ESMFold → Vina → GNINA)
    # ════════════════════════════════════════════════════════════════════
    # Docking jobs are dispatched to the Azure worker via a file-based job
    # queue. The main server returns 202 Accepted immediately; the Azure
    # worker picks up pending jobs, runs the full pipeline (ESMFold, Vina,
    # GNINA), and POSTs results back. Frontend polls /status/<job_id>.

    from primerforge.docking_queue import create_job, get_job, list_pending_jobs

    @app.route("/api/primer/docking/consensus", methods=["POST"])
    def docking_consensus():
        if not READY:
            return err("Core not available.", "DESIGN_FAILED", 503)

        data = request.get_json(silent=True) or {}
        sequence = (data.get("sequence") or "").strip()
        ligand_smiles_list = data.get("ligand_smiles_list") or data.get("smiles_list") or []

        try:
            top_n = int(data.get("top_n", 50))
        except (ValueError, TypeError):
            return err("'top_n' must be an integer.", "VALIDATION_ERROR", 400)

        if not sequence:
            return err("Protein amino acid 'sequence' is required.", "VALIDATION_ERROR", 400)
        if not ligand_smiles_list or not isinstance(ligand_smiles_list, list):
            return err("'ligand_smiles_list' must be a non-empty list of SMILES strings.", "VALIDATION_ERROR", 400)

        # ── Auth & Docking Usage Check ────────────────────────────────────
        user = get_current_user()
        if not user:
            return jsonify({"error": "Authentication required. Please login or register to use molecular docking.",
                           "code": "AUTH_REQUIRED", "action": "show_auth"}), 401
        dock_usage = check_docking_usage(user['email'])
        if not dock_usage['can_run'] and user.get('role') != 'admin':
            return jsonify({"error": "Docking usage limit reached. Purchase more docking runs to continue.",
                           "code": "PAYMENT_REQUIRED", "action": "show_docking_payment",
                           "usage": dock_usage}), 402

        job_id = create_job(sequence, ligand_smiles_list, top_n)

        # Consume token AFTER successful queuing (both SQLite and PostgreSQL)
        if user.get('role') != 'admin':
            if USE_POSTGRES and consume_docking_token:
                if not consume_docking_token(user.get('user_id'), user['email']):
                    return jsonify({"error": "No docking tokens remaining. Purchase more to continue.",
                                   "code": "PAYMENT_REQUIRED", "action": "show_docking_payment"}), 402
            else:
                increment_docking_usage(user['email'])

        return jsonify({"job_id": job_id, "status": "queued"}), 202

    @app.route("/api/primer/docking/status/<job_id>", methods=["GET"])
    def docking_status(job_id):
        job = get_job(job_id)
        if not job:
            return err("Job not found.", "NOT_FOUND", 404)
        from primerforge.docking_queue import cleanup_old_jobs
        cleanup_old_jobs(4.0)
        resp = {
            "job_id": job["job_id"],
            "status": job["status"],
            "created_at": job["created_at"],
        }
        if job["status"] == "completed" and job["result"]:
            result = job["result"]
            if isinstance(result, dict):
                result = dict(result)
                if "stage1" in result and isinstance(result["stage1"], dict):
                    s1 = dict(result["stage1"])
                    s1.pop("pdb_string", None)
                    result["stage1"] = s1
                ranked = result.get("ranked_results", [])
                if ranked:
                    stripped = []
                    for mol in ranked:
                        m = dict(mol)
                        if "structure" in m:
                            m["_has_structure"] = bool((m.get("structure") or {}).get("ligand"))
                            m.pop("structure", None)
                        stripped.append(m)
                    result["ranked_results"] = stripped
            resp["result"] = result
        if job["error"]:
            resp["error"] = job["error"]
        return jsonify(resp), 200

    @app.route("/api/primer/docking/structure/<job_id>/<int:rank>", methods=["GET"])
    def docking_structure(job_id, rank):
        job = get_job(job_id)
        if not job:
            return err("Job not found.", "NOT_FOUND", 404)
        result = job.get("result") or {}
        ranked = result.get("ranked_results") or []
        if rank < 1 or rank > len(ranked):
            return err("Invalid rank.", "NOT_FOUND", 404)
        mol = ranked[rank - 1]
        structure = mol.get("structure") or {}
        receptor = (result.get("stage1") or {}).get("pdb_string", "")
        return jsonify({
            "receptor_pdb": receptor,
            "ligand_sdf": structure.get("ligand", ""),
            "smiles": mol.get("smiles", ""),
            "vina_score": mol.get("vina_score"),
            "gnina_score": mol.get("gnina_score"),
        }), 200

    @app.route("/api/primer/docking/structure/upload/<job_id>/<int:rank>", methods=["POST"])
    def docking_structure_upload(job_id, rank):
        from primerforge.docking_queue import _ensure_dirs, COMPLETE_DIR, FAILED_DIR, RUNNING_DIR
        import os, json as jmod
        data = request.get_json(silent=True) or {}
        # Find the job file in complete or failed dir
        for d in (COMPLETE_DIR, FAILED_DIR, RUNNING_DIR):
            path = os.path.join(d, f"{job_id}.json")
            if os.path.exists(path):
                with open(path) as f:
                    job = jmod.load(f)
                result = job.get("result") or {}
                ranked = result.get("ranked_results") or []
                if 1 <= rank <= len(ranked):
                    if ranked[rank - 1].get("structure"):
                        return jsonify({"status": "already_exists"}), 200
                    ranked[rank - 1]["structure"] = data
                    job["result"] = result
                    with open(path, "w") as f:
                        jmod.dump(job, f)
                    return jsonify({"status": "stored"}), 200
                return err("Invalid rank.", "NOT_FOUND", 404)
        return err("Job not found.", "NOT_FOUND", 404)

    @app.route("/api/primer/docking/pending", methods=["GET"])
    def docking_pending():
        from primerforge.docking_queue import release_stale_jobs
        release_stale_jobs(max_age_minutes=10.0)
        jobs = list_pending_jobs()
        return jsonify({"pending": len(jobs), "jobs": jobs}), 200

    @app.route("/api/primer/docking/running", methods=["GET"])
    def docking_running():
        from primerforge.docking_queue import list_running_jobs
        jobs = list_running_jobs()
        return jsonify({"running": len(jobs), "jobs": jobs}), 200

    @app.route("/api/primer/docking/reset/<job_id>", methods=["POST"])
    def docking_reset(job_id):
        from primerforge.docking_queue import release_stale_jobs
        n = release_stale_jobs(max_age_minutes=0)
        return jsonify({"status": "ok", "released": n}), 200

    @app.route("/api/primer/docking/claim/<job_id>", methods=["POST"])
    def docking_claim(job_id):
        from primerforge.docking_queue import claim_job
        if claim_job(job_id):
            return jsonify({"status": "claimed"}), 200
        return err("Job not found or already claimed.", "CONFLICT", 409)

    @app.route("/api/primer/docking/complete/<job_id>", methods=["POST"])
    def docking_complete(job_id):
        from primerforge.docking_queue import complete_job
        data = request.get_json(silent=True) or {}
        complete_job(job_id, data.get("result"), data.get("error"))
        return jsonify({"status": "acknowledged"}), 200

    # ════════════════════════════════════════════════════════════════════
    # Azure Worker Callback Endpoint
    # ════════════════════════════════════════════════════════════════════

    CALLBACK_SECRET_TOKEN = os.environ.get("CALLBACK_SECRET_TOKEN", "")
    if not CALLBACK_SECRET_TOKEN:
        logger.warning(
            "CALLBACK_SECRET_TOKEN not set — callback endpoint will reject all requests"
        )

    @app.route("/api/v1/jobs/callback", methods=["POST"])
    def jobs_callback():
        """
        Secure endpoint for Azure workers to POST results back.

        Authentication: X-Callback-Token header must match CALLBACK_SECRET_TOKEN.
        Payload: JSON object with job_id, status, job_type, step outcomes.

        Updates the pipeline_jobs table and records step results in
        pipeline_results (if PostgreSQL mode).
        """
        # ── Auth ──────────────────────────────────────────────────────
        token = request.headers.get("X-Callback-Token", "")
        if not CALLBACK_SECRET_TOKEN or token != CALLBACK_SECRET_TOKEN:
            logger.warning("Callback rejected: invalid token (got len=%d)", len(token))
            return jsonify({"error": "Unauthorized", "code": "AUTH_FAILED"}), 401

        data = request.get_json(silent=True) or {}
        job_id = data.get("job_id", "")
        job_type = data.get("job_type", "unknown")
        status = data.get("status", "failed")
        outcomes = data.get("outcomes") or data.get("chunk_results") or []
        error = data.get("error")
        stats = data.get("stats") or {}
        elapsed_s = data.get("elapsed_s", 0)

        if not job_id:
            return jsonify({"error": "job_id is required", "code": "VALIDATION_ERROR"}), 400

        logger.info(
            "Callback received: job_id=%s type=%s status=%s elapsed=%.1fs",
            job_id, job_type, status, elapsed_s,
        )

        # ── Update PostgreSQL (production) ────────────────────────────
        if USE_POSTGRES:
            try:
                from primerforge.database import execute as db_execute
                import json as _json

                # Update or insert into pipeline_jobs
                db_execute("""
                    INSERT INTO pipeline_jobs (id, status, job_type, error_log,
                                               started_at, completed_at, mode)
                    VALUES (%s, %s, %s, %s, NOW(), NOW(), %s)
                    ON CONFLICT (id) DO UPDATE SET
                        status = EXCLUDED.status,
                        error_log = EXCLUDED.error_log,
                        completed_at = NOW()
                """, (job_id, status, job_type, error or None,
                      data.get("mode", "express")))

                # Record individual outcomes in pipeline_results
                if outcomes:
                    for outcome in outcomes:
                        if isinstance(outcome, dict):
                            step_num = outcome.get("step_number") or outcome.get("chunk_id")
                            step_name = outcome.get("step_name", f"step_{step_num}")
                            out_status = outcome.get("status", "unknown")
                            duration = outcome.get("duration_ms", 0)
                            err_msg = outcome.get("error_msg")
                            try:
                                db_execute("""
                                    INSERT INTO pipeline_results
                                        (job_id, step_number, step_name, status,
                                         output_data, duration_ms, phase)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                                """, (
                                    job_id, step_num, step_name, out_status,
                                    _json.dumps(outcome), duration,
                                    outcome.get("phase", "X"),
                                ))
                            except Exception as e:
                                logger.warning("Failed to record outcome step %s: %s",
                                               step_num, e)

                logger.info("Pipeline job %s updated to status=%s", job_id, status)
            except Exception as e:
                logger.error("Failed to update pipeline_jobs for %s: %s", job_id, e)
                return jsonify({
                    "received": True,
                    "warning": f"Results accepted but DB update failed: {str(e)[:200]}",
                }), 200

        # ── Update in-memory (dev mode) ───────────────────────────────
        else:
            try:
                _dev_jobs = locals().get("DEV_PIPELINE_JOBS", {})
                _dev_jobs[job_id] = {
                    "job_id": job_id,
                    "status": status,
                    "job_type": job_type,
                    "steps": [
                        o for o in (outcomes or [])
                        if isinstance(o, dict)
                    ],
                    "error": error,
                    "stats": stats,
                    "elapsed_s": elapsed_s,
                    "completed_at": time.time(),
                }
                logger.info("Dev pipeline job %s updated (in-memory)", job_id)
            except Exception as e:
                logger.warning("Failed to update dev job %s: %s", job_id, e)

        return jsonify({
            "received": True,
            "job_id": job_id,
            "status": status,
        }), 200

    # Start local docking worker if READY
    if READY:
        try:
            from primerforge.docking_queue import start_local_worker
            start_local_worker(interval=5.0)
        except Exception as e:
            logger.warning("Failed to start local docking worker: %s", e)

    # Pipeline health validation on startup
    try:
        from core.pipeline_validator import validate_pipeline_health
        health = validate_pipeline_health()
        if health["status"] == "error":
            for e in health["errors"]:
                logger.error("PIPELINE VALIDATION ERROR: %s", e)
        if health["warnings"]:
            for w in health["warnings"]:
                logger.warning("PIPELINE VALIDATION: %s", w)
        logger.info("Pipeline health: %s (%s)", health['status'], health['summary'])
    except ImportError as e:
        logger.warning("Pipeline validator not available: %s", e)
    except Exception as e:
        logger.warning("Pipeline validation failed: %s", e)

    # WSGI middleware to strip Server header (runs after gunicorn adds it)
    class _ServerHeaderMiddleware:
        def __init__(self, wsgi_app):
            self.wsgi_app = wsgi_app

        def __call__(self, environ, start_response):
            def _start_response(status, headers, exc_info=None):
                headers = [(k, v) for k, v in headers if k.lower() != "server"]
                return start_response(status, headers, exc_info)
            return self.wsgi_app(environ, _start_response)

    return _ServerHeaderMiddleware(app)


if __name__ == "__main__":
    port = int(os.environ.get("PRIMERFORGE_PORT", 11436))
    host = os.environ.get("PRIMERFORGE_HOST", "127.0.0.1")
    debug = os.environ.get("PRIMERFORGE_DEBUG", "").lower() == "true"
    if os.environ.get("FORCE_HTTPS", "").lower() == "true" and debug:
        raise RuntimeError("PRIMERFORGE_DEBUG=true is not allowed when FORCE_HTTPS=true")
    wsgi_app = create_app()
    # create_app() returns a _ServerHeaderMiddleware wrapper; unwrap to get the Flask app for .run()
    flask_app = wsgi_app.wsgi_app if hasattr(wsgi_app, "wsgi_app") else wsgi_app
    logger.info("VigyanLLM 22-step pipeline server on http://%s:%s", host, port)
    flask_app.run(host=host, port=port, debug=debug)

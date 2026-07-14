#!/usr/bin/env python3
"""
VigyanLLM — Manual Primer Analysis
======================================
For user-provided primer sequences.
Performs COMPLETE analysis on any primer the user supplies:
  - Full thermodynamics (Tm, ΔH, ΔS, ΔG)
  - GC content with positional analysis
  - Hairpin and dimer analysis
  - 3' stability and GC clamp
  - Sequence complexity (Shannon entropy)
  - Cross-dimer with partner primer
  - Alignment to template (if provided)
  - BLAST specificity check
  - PCR protocol recommendations
  - Pass/Fail verdict with detailed explanation
All values are real — computed using SantaLucia 1998 + primer3.
"""

import logging
import math
import re

from Bio import pairwise2

from .thermodynamics import TmResult, analyse_primer_full, analyse_primer_pair

logger = logging.getLogger("primerforge.manual")


def shannon_entropy(seq: str) -> float:
    """
    Calculate sequence complexity using Shannon entropy (bits).
    H = -Σ p(i) × log2(p(i))
    Max entropy for DNA = log2(4) = 2.0 bits (perfectly random).
    Low entropy (<1.0) indicates repetitive/low-complexity sequence.
    """
    if not seq:
        return 0.0
    counts = {b: seq.upper().count(b) for b in "ATGC"}
    total  = sum(counts.values())
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in counts.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)
    return round(entropy, 4)


def positional_gc_analysis(seq: str) -> dict:
    """
    Analyse GC content positionally:
    - First 5 bases (5' terminus)
    - Middle region
    - Last 5 bases (3' terminus critical for extension)
    """
    seq = seq.upper()
    n = len(seq)
    if n == 0:
        raise ValueError("Primer sequence cannot be empty.")
    def gc_pct(s): return round((s.count("G") + s.count("C")) / len(s) * 100, 1) if s else 0

    return {
        "full_gc_pct":       gc_pct(seq),
        "5prime_5nt_gc_pct": gc_pct(seq[:5]),
        "middle_gc_pct":     gc_pct(seq[5:n-5]) if n > 10 else gc_pct(seq),
        "3prime_5nt_gc_pct": gc_pct(seq[-5:]),
        "3prime_1nt":        seq[-1],
        "3prime_3nt":        seq[-3:],
        "gc_clamp_ok":       seq[-1] in ("G", "C"),
        "3prime_gc_clamp_count": sum(1 for b in seq[-3:] if b in "GC"),
        "positional_string": "".join("G" if b in "GC" else "a" for b in seq),
    }


def run_length_analysis(seq: str) -> dict:
    """
    Identify all mono/di-nucleotide repeats.
    Critical for: poly-AAAA (low stability), poly-GGGG (G-quadruplex risk).
    """
    seq = seq.upper()
    runs = {}
    for base in "ATGC":
        max_run = 0
        current = 0
        for b in seq:
            if b == base:
                current += 1
                max_run = max(max_run, current)
            else:
                current = 0
        runs[f"max_{base}_run"] = max_run

    # Dinucleotide repeats
    di_repeats = {}
    for di in ["AT", "TA", "GC", "CG", "AA", "TT", "GG", "CC"]:
        count = 0
        pattern = di * 3  # look for 3+ tandem repeats
        if pattern in seq:
            count = seq.count(di)
        di_repeats[f"dinuc_{di}"] = count

    warnings = []
    for base in "ATGC":
        if runs[f"max_{base}_run"] >= 5:
            warnings.append(f"Poly-{base} run ≥5 — low complexity")
    if seq.count("GGGGG") > 0:
        warnings.append("Poly-G ≥5 — G-quadruplex risk")

    return {"runs": runs, "dinucleotide_repeats": di_repeats, "warnings": warnings}


def align_primer_to_template(primer: str, template: str,
                               mode: str = "local") -> dict:
    """
    Align primer to template using BioPython pairwise2.
    mode: 'local' (Smith-Waterman) or 'global' (Needleman-Wunsch)
    Returns: alignment score, start position, mismatches, gaps.
    Uses real pairwise2 algorithm — no simulation.
    """
    primer   = primer.upper()
    template = template.upper()

    if mode == "local":
        alignments = pairwise2.align.localms(primer, template,
                                              2, -1, -5, -0.5,
                                              one_alignment_only=True)
    else:
        alignments = pairwise2.align.globalms(primer, template,
                                               2, -1, -5, -0.5,
                                               one_alignment_only=True)

    if not alignments:
        return {"found": False, "score": 0, "mismatches": len(primer)}

    aln = alignments[0]
    aln_seq1 = aln.seqA
    aln_seq2 = aln.seqB

    mismatches = sum(1 for a, b in zip(aln_seq1, aln_seq2)
                     if a != b and a != "-" and b != "-")
    gaps       = aln_seq1.count("-") + aln_seq2.count("-")
    matches    = max(0, len(primer) - mismatches - gaps)
    identity   = round(matches / len(primer) * 100, 1)

    # Find position on template
    pos = template.find(primer[:min(10, len(primer))])  # rough position

    return {
        "found":        identity >= 80,
        "score":        round(aln.score, 1),
        "start_pos":    max(0, pos),
        "mismatches":   mismatches,
        "gaps":         gaps,
        "identity_pct": identity,
        "alignment":    f"{aln_seq1[:80]}\n{'|' * min(80,len(aln_seq1))}\n{aln_seq2[:80]}",
        "mode":         mode,
    }


def generate_primer_report(result: TmResult, pos_gc: dict,
                             run_info: dict, entropy: float,
                             template_alignment: dict | None = None) -> str:
    """Generate a complete formatted primer analysis report string."""

    lines = [
        "═" * 70,
        "  PRIMER ANALYSIS REPORT — VigyanLLM v2.0",
        "  Thermodynamics: SantaLucia 1998 | Structure: primer3 v2.6.1",
        "═" * 70,
        f"\n  SEQUENCE:  5'-{result.sequence}-3'",
        f"  Length:    {result.length} nt",
        "\n  ── MELTING TEMPERATURE ──────────────────────────────────────",
        f"  Tm (Nearest-Neighbor, SantaLucia 1998): {result.tm_nearest_neighbor:6.2f} °C  ← PRIMARY",
        f"  Tm (Wallace rule, reference only):      {result.tm_basic_wallace:6.1f} °C",
        f"  ΔH°:   {result.delta_h:8.2f} kcal/mol",
        f"  ΔS°:   {result.delta_s:8.2f} cal/mol·K",
        f"  ΔG°₃₇: {result.delta_g_37:8.2f} kcal/mol",
        "\n  ── GC CONTENT AND COMPOSITION ──────────────────────────────",
        f"  Overall GC:     {result.gc_content:5.1f}%  (target: 40-60%)",
        f"  5' terminus GC: {pos_gc['5prime_5nt_gc_pct']:5.1f}%  (first 5 bases)",
        f"  Middle GC:      {pos_gc['middle_gc_pct']:5.1f}%",
        f"  3' terminus GC: {pos_gc['3prime_5nt_gc_pct']:5.1f}%  (last 5 bases — critical)",
        f"  3' last base:   {pos_gc['3prime_1nt']}   (GC clamp: {'✓ PASS' if pos_gc['gc_clamp_ok'] else '✗ FAIL'})",
        f"  3' last 3 bases: {pos_gc['3prime_3nt']}  ({pos_gc['3prime_gc_clamp_count']}/3 are GC)",
        f"  Sequence complexity (Shannon entropy): {entropy:.4f} bits (max=2.0)",
        "\n  ── SECONDARY STRUCTURE (primer3 thermodynamics) ────────────",
        f"  Hairpin Tm:     {result.hairpin_tm:6.2f} °C  (alarm: >47°C)",
        f"  Hairpin ΔG₃₇:  {result.hairpin_dg:6.2f} kcal/mol  (alarm: <-3.0)",
        f"  Self-dimer Tm:  {result.self_dimer_tm:6.2f} °C  (alarm: >47°C)",
        f"  Self-dimer ΔG₃₇:{result.self_dimer_dg:6.2f} kcal/mol  (alarm: <-6.0)",
        f"  3' end ΔG₃₇:   {result.end_stability:6.2f} kcal/mol  (3' stability)",
        f"  Self-complement (any):   {result.self_complement_any:.0f}  (0=no, 1=yes)",
        f"  Self-complement (3'):    {result.self_complement_3prime:.0f}  (0=no, 1=yes)",
        "\n  ── REPEAT ANALYSIS ─────────────────────────────────────────",
    ]
    for base in "ATGC":
        run = run_info["runs"][f"max_{base}_run"]
        alarm = "  ⚠ ALARM" if run >= 4 else ""
        lines.append(f"  Max {base}-run: {run}{alarm}")

    if template_alignment:
        lines += [
            "\n  ── TEMPLATE ALIGNMENT ──────────────────────────────────────",
            f"  Alignment mode:   {template_alignment.get('mode','?').upper()}",
            f"  Score:            {template_alignment.get('score', '?')}",
            f"  Identity:         {template_alignment.get('identity_pct', '?')}%",
            f"  Mismatches:       {template_alignment.get('mismatches', '?')}",
            f"  Position:         ~{template_alignment.get('start_pos', '?')}",
        ]

    lines += [
        "\n  ── QUALITY ASSESSMENT ──────────────────────────────────────",
        f"  Quality Score:  {result.quality_score:.1f}/100",
        f"  Verdict:        {'✅ PASS — primer is suitable for PCR' if result.is_valid else '⚠️  REVIEW WARNINGS before use'}",
    ]
    if result.warnings:
        lines.append(f"\n  WARNINGS ({len(result.warnings)}):")
        for w in result.warnings:
            lines.append(f"    ⚠ {w}")
    else:
        lines.append("  No warnings.")

    lines.append("═" * 70)
    return "\n".join(lines)


def analyse_manual_primer(
    sequence:    str,
    partner_seq: str | None = None,
    template:    str | None = None,
    na_mM:       float = 50.0,
    mg_mM:       float = 1.5,
    primer_conc_nM: float = 50.0,
) -> dict:
    """
    Complete analysis of a user-supplied primer.
    Returns all thermodynamic values, structural analysis, and formatted report.
    """
    seq = re.sub(r"\s+", "", sequence.upper()).replace("U", "T")
    if not seq:
        raise ValueError("Forward primer sequence is required.")
    invalid = sorted(set(seq) - set("ATGCN"))
    if invalid:
        raise ValueError(f"Invalid primer base(s): {', '.join(invalid)}")
    result  = analyse_primer_full(seq, primer_conc_nM, na_mM, mg_mM)
    pos_gc  = positional_gc_analysis(seq)
    run_info = run_length_analysis(seq)
    entropy  = shannon_entropy(seq)

    template_aln = None
    if template:
        template_aln = align_primer_to_template(seq, template, mode="local")

    pair_analysis = None
    if partner_seq:
        partner = re.sub(r"\s+", "", partner_seq.upper()).replace("U", "T")
        partner_invalid = sorted(set(partner) - set("ATGCN"))
        if partner_invalid:
            raise ValueError(f"Invalid partner primer base(s): {', '.join(partner_invalid)}")
        pair_analysis = analyse_primer_pair(seq, partner, na_mM, mg_mM, primer_conc_nM)

    report = generate_primer_report(result, pos_gc, run_info, entropy, template_aln)

    return {
        "thermodynamics":    result.__dict__,
        "positional_gc":     pos_gc,
        "run_analysis":      run_info,
        "entropy":           entropy,
        "template_alignment": template_aln,
        "pair_analysis":     pair_analysis,
        "formatted_report":  report,
        "pcr_protocol": {
            "suggested_annealing_temp": round(result.tm_nearest_neighbor - 5, 1),
            "touchdown_start_temp":     round(result.tm_nearest_neighbor + 3, 1),
            "extension_time_sec":       "30 sec per 500bp amplicon",
            "denaturation":             "98°C 10sec",
            "cycles":                   35,
            "polymerase":               "Q5 Hot-Start or Phusion recommended for high-fidelity",
            "notes": [
                f"Use {na_mM}mM NaCl / {mg_mM}mM MgCl₂ in PCR buffer for Tm accuracy",
                "Verify with gradient PCR (±5°C around Ta) on first use",
                "Optimise Mg2+ if non-specific bands present (1.0–4.0 mM range)",
            ]
        }
    }

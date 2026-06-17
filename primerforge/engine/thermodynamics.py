#!/usr/bin/env python3
"""
VigyanLLM Thermodynamic Engine — SantaLucia 1998 Nearest-Neighbor Model
========================================================================
Production-grade implementation of:
- Nearest-Neighbor Tm calculation (unified oligo params)
- Monovalent salt correction (Owczarzy 2004)
- Divalent Mg²+ correction (von Ahsen 2001)
- Hairpin ΔG prediction
- Self-dimer ΔG prediction
- Cross-dimer (heterodimer) ΔG prediction

Reference: SantaLucia J Jr. (1998) Proc Natl Acad Sci USA 95:1460-1465
"""

import math
from dataclasses import dataclass
from typing import Tuple, Optional

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

R = 1.987  # Gas constant in cal/(K·mol)

# ═══════════════════════════════════════════════════════════════════════════
# NEAREST-NEIGHBOR PARAMETERS (SantaLucia 1998, Unified)
# ΔH in kcal/mol, ΔS in cal/(mol·K)
# ═══════════════════════════════════════════════════════════════════════════

# 10 unique Watson-Crick dinucleotide pairs (5'→3' / 3'→5')
NN_PARAMS = {
    "AA": (-7.9, -22.2),   # AA/TT
    "TT": (-7.9, -22.2),   # TT/AA (same as AA/TT)
    "AT": (-7.2, -20.4),   # AT/TA
    "TA": (-7.2, -21.3),   # TA/AT
    "CA": (-8.5, -22.7),   # CA/GT
    "TG": (-8.5, -22.7),   # TG/AC (complement of CA/GT)
    "GT": (-8.4, -22.4),   # GT/CA
    "AC": (-8.4, -22.4),   # AC/TG (complement of GT/CA)
    "CT": (-7.8, -21.0),   # CT/GA
    "AG": (-7.8, -21.0),   # AG/TC (complement of CT/GA)
    "GA": (-8.2, -22.2),   # GA/CT
    "TC": (-8.2, -22.2),   # TC/AG (complement of GA/CT)
    "CG": (-10.6, -27.2),  # CG/GC
    "GC": (-9.8, -24.4),   # GC/CG
    "GG": (-8.0, -19.9),   # GG/CC
    "CC": (-8.0, -19.9),   # CC/GG (same as GG/CC)
}

# Initiation parameters
INIT_GC = (0.1, -2.8)     # 5' G or C terminal: ΔH=0.1, ΔS=-2.8
INIT_AT = (2.3, 4.1)      # 5' A or T terminal: ΔH=2.3, ΔS=4.1

# Self-complementary correction
SYMMETRY_CORRECTION_S = -1.4  # cal/(mol·K) added to ΔS for self-complementary sequences


# ═══════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ThermoResult:
    """Result of thermodynamic calculation."""
    tm: float                   # Melting temperature (°C)
    tm_salt_adjusted: float     # Salt-adjusted Tm (°C)
    tm_mg_adjusted: float       # Mg²+-adjusted Tm (°C)
    delta_h: float              # Total ΔH (kcal/mol)
    delta_s: float              # Total ΔS (cal/(mol·K))
    delta_g_37: float           # ΔG at 37°C (kcal/mol)
    gc_percent: float           # GC content (%)
    length: int                 # Primer length


@dataclass
class StructureResult:
    """Result of secondary structure prediction."""
    delta_g: float              # ΔG of most stable structure (kcal/mol)
    structure_type: str         # 'hairpin', 'self_dimer', 'cross_dimer'
    is_stable: bool             # True if structure forms at annealing temp
    details: str                # Human-readable description


@dataclass
class BufferConditions:
    """PCR buffer composition for thermodynamic calculations."""
    monovalent_mm: float = 50.0    # [Na+] + [K+] in mM
    divalent_mm: float = 1.5       # [Mg²+] in mM
    dntp_mm: float = 0.2           # [dNTPs] in mM (chelates Mg²+)
    oligo_conc_nm: float = 250.0   # Total oligonucleotide concentration in nM


# ═══════════════════════════════════════════════════════════════════════════
# CORE CALCULATIONS
# ═══════════════════════════════════════════════════════════════════════════

def compute_nn_params(sequence: str) -> Tuple[float, float]:
    """
    Compute total ΔH and ΔS for a DNA sequence using nearest-neighbor model.
    
    Args:
        sequence: DNA sequence (5' to 3'), uppercase ACGT only
    
    Returns:
        (total_dH in kcal/mol, total_dS in cal/(mol·K))
    """
    seq = sequence.upper().strip()
    if len(seq) < 2:
        raise ValueError("Sequence must be at least 2 nucleotides")

    total_h = 0.0
    total_s = 0.0

    # Sum nearest-neighbor parameters
    for i in range(len(seq) - 1):
        dinuc = seq[i:i+2]
        if dinuc in NN_PARAMS:
            dh, ds = NN_PARAMS[dinuc]
            total_h += dh
            total_s += ds
        else:
            # Handle ambiguous bases by using average
            total_h += -8.0  # Average ΔH
            total_s += -22.0  # Average ΔS

    # Initiation parameters (terminal base pairs)
    if seq[0] in ('G', 'C'):
        total_h += INIT_GC[0]
        total_s += INIT_GC[1]
    else:
        total_h += INIT_AT[0]
        total_s += INIT_AT[1]

    if seq[-1] in ('G', 'C'):
        total_h += INIT_GC[0]
        total_s += INIT_GC[1]
    else:
        total_h += INIT_AT[0]
        total_s += INIT_AT[1]

    return total_h, total_s


def calculate_tm(sequence: str, buffer: BufferConditions = None) -> ThermoResult:
    """
    Calculate melting temperature using full SantaLucia NN model.
    
    Tm = ΔH° / (ΔS°_salt + R·ln(Ct/4)) - 273.15
    
    Args:
        sequence: Primer sequence (5'→3')
        buffer: PCR buffer conditions (defaults to standard)
    
    Returns:
        ThermoResult with all thermodynamic parameters
    """
    if buffer is None:
        buffer = BufferConditions()

    seq = sequence.upper().strip()
    n = len(seq)

    if n < 8:
        raise ValueError("Primer must be at least 8 nucleotides for reliable Tm")

    # Compute raw NN parameters
    delta_h, delta_s = compute_nn_params(seq)

    # Convert concentrations to Molar
    ct = buffer.oligo_conc_nm * 1e-9  # nM → M
    monovalent_m = buffer.monovalent_mm * 1e-3  # mM → M
    mg_m = buffer.divalent_mm * 1e-3  # mM → M
    dntp_m = buffer.dntp_mm * 1e-3  # mM → M

    # Free Mg²+ (dNTPs chelate Mg²+ 1:1)
    free_mg = max(0.0, mg_m - dntp_m)

    # ── Salt Correction (Owczarzy 2004) ───────────────────────────────────
    # ΔS°_salt = ΔS°_1M + 0.368·(N-1)·ln([Mon+])
    if monovalent_m > 0:
        delta_s_salt = delta_s + 0.368 * (n - 1) * math.log(monovalent_m)
    else:
        delta_s_salt = delta_s

    # ── Basic Tm (1M NaCl equivalent) ─────────────────────────────────────
    # Tm = ΔH / (ΔS + R·ln(Ct/4)) - 273.15
    denominator = delta_s_salt + R * math.log(ct / 4.0)
    if denominator == 0:
        tm_basic = 0.0
    else:
        tm_basic = (delta_h * 1000.0) / denominator - 273.15
        # Note: ΔH is in kcal/mol, need to convert to cal/mol for consistency with ΔS

    # Correct: ΔH in kcal/mol × 1000 = cal/mol to match ΔS units
    tm_salt = tm_basic

    # ── Mg²+ Correction (von Ahsen 2001) ─────────────────────────────────
    # Tm(Mg²+) = Tm(salt) + 7.21·ln([Mg²+])
    if free_mg > 0:
        tm_mg = tm_salt + 7.21 * math.log(free_mg)
    else:
        tm_mg = tm_salt

    # ── ΔG at 37°C ───────────────────────────────────────────────────────
    # ΔG = ΔH - T·ΔS (T in Kelvin = 310.15K for 37°C)
    delta_g_37 = delta_h - (310.15 * delta_s / 1000.0)

    # GC content
    gc_count = seq.count('G') + seq.count('C')
    gc_percent = (gc_count / n) * 100.0

    return ThermoResult(
        tm=round(tm_basic, 2),
        tm_salt_adjusted=round(tm_salt, 2),
        tm_mg_adjusted=round(tm_mg, 2),
        delta_h=round(delta_h, 2),
        delta_s=round(delta_s, 2),
        delta_g_37=round(delta_g_37, 2),
        gc_percent=round(gc_percent, 1),
        length=n,
    )


# ═══════════════════════════════════════════════════════════════════════════
# SECONDARY STRUCTURE PREDICTIONS
# ═══════════════════════════════════════════════════════════════════════════

def _complement(base: str) -> str:
    """Return Watson-Crick complement of a base."""
    comp = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G'}
    return comp.get(base.upper(), 'N')


def _reverse_complement(seq: str) -> str:
    """Return reverse complement of a DNA sequence."""
    return ''.join(_complement(b) for b in reversed(seq.upper()))


def predict_hairpin(sequence: str, buffer: BufferConditions = None) -> StructureResult:
    """
    Predict most stable hairpin structure by scanning all possible loop positions.
    A hairpin forms when a single strand folds back on itself.
    
    Minimum loop size: 3 nucleotides
    """
    seq = sequence.upper()
    n = len(seq)
    min_dg = 0.0
    best_detail = "No stable hairpin"

    # Scan all possible loop positions
    for loop_start in range(3, n - 6):  # Need at least 3bp stem on each side
        for loop_end in range(loop_start + 3, min(loop_start + 10, n - 3)):
            # Check if bases on either side of loop can pair
            stem_5 = seq[:loop_start]
            stem_3 = seq[loop_end:]
            
            # Find maximum stem length
            stem_len = min(len(stem_5), len(stem_3))
            pairs = 0
            dg = 0.0
            
            for i in range(stem_len):
                b5 = stem_5[-(i+1)]
                b3 = stem_3[i]
                if _complement(b5) == b3:
                    pairs += 1
                    # Approximate ΔG per base pair
                    dinuc = b5 + _complement(b5)
                    if dinuc in NN_PARAMS:
                        dh, ds = NN_PARAMS[dinuc]
                        dg += dh - (310.15 * ds / 1000.0)
                else:
                    break

            # Loop penalty (Turner 2004 approximation)
            loop_size = loop_end - loop_start
            loop_penalty = 1.75 * math.log(loop_size / 3.0) + 3.5 if loop_size > 3 else 3.5
            total_dg = dg + loop_penalty / 1000.0

            if total_dg < min_dg and pairs >= 3:
                min_dg = total_dg
                best_detail = f"Stem: {pairs}bp, Loop: {loop_size}nt, ΔG={total_dg:.2f} kcal/mol"

    return StructureResult(
        delta_g=round(min_dg, 2),
        structure_type="hairpin",
        is_stable=min_dg < -2.0,
        details=best_detail,
    )


def predict_self_dimer(sequence: str) -> StructureResult:
    """
    Predict self-dimer stability (bimolecular — two copies of same strand).
    Scans all possible alignments for complementary base pairing.
    """
    seq = sequence.upper()
    rc = _reverse_complement(seq)
    n = len(seq)
    min_dg = 0.0
    best_detail = "No stable self-dimer"

    # Slide one copy against the other
    for offset in range(-(n-3), n-2):
        dg = 0.0
        pairs = 0

        for i in range(n):
            j = i + offset
            if 0 <= j < n:
                if seq[i] == _complement(seq[j]):
                    pairs += 1
                    dinuc = seq[i] + seq[min(i+1, n-1)]
                    if dinuc in NN_PARAMS:
                        dh, ds = NN_PARAMS[dinuc]
                        dg += (dh - 310.15 * ds / 1000.0) * 0.5  # Approximate

        if pairs >= 4 and dg < min_dg:
            min_dg = dg
            best_detail = f"{pairs} complementary bases at offset {offset}, ΔG={dg:.2f}"

    return StructureResult(
        delta_g=round(min_dg, 2),
        structure_type="self_dimer",
        is_stable=min_dg < -5.0,
        details=best_detail,
    )


def predict_cross_dimer(seq1: str, seq2: str) -> StructureResult:
    """
    Predict heterodimer stability between two different primer sequences.
    Critical for multiplex PCR — cross-dimers waste primers.
    """
    s1 = seq1.upper()
    s2 = _reverse_complement(seq2.upper())
    n1, n2 = len(s1), len(s2)
    min_dg = 0.0
    best_detail = "No stable cross-dimer"

    for offset in range(-(n2-3), n1-2):
        dg = 0.0
        pairs = 0

        for i in range(n1):
            j = i - offset
            if 0 <= j < n2:
                if s1[i] == _complement(s2[j]) if j < len(seq2) else False:
                    pairs += 1
                    dinuc = s1[i] + s1[min(i+1, n1-1)]
                    if dinuc in NN_PARAMS:
                        dh, ds = NN_PARAMS[dinuc]
                        dg += (dh - 310.15 * ds / 1000.0) * 0.5

        if pairs >= 4 and dg < min_dg:
            min_dg = dg
            best_detail = f"{pairs} cross-pairs at offset {offset}, ΔG={dg:.2f}"

    return StructureResult(
        delta_g=round(min_dg, 2),
        structure_type="cross_dimer",
        is_stable=min_dg < -5.0,
        details=best_detail,
    )


def predict_amplicon_folding(sequence: str, temperature_c: float = 72.0) -> StructureResult:
    """
    Predict if amplicon forms stable structures at extension temperature.
    Uses simplified energy model — checks for internal palindromes and hairpins.
    If ΔG at extension temp is very negative, Taq polymerase may stall.
    """
    seq = sequence.upper()
    n = len(seq)
    
    if n < 20:
        return StructureResult(delta_g=0.0, structure_type="amplicon_fold",
                              is_stable=False, details="Amplicon too short for stable folding")

    # Scan for internal hairpins in the amplicon at extension temperature
    temp_k = temperature_c + 273.15
    min_dg = 0.0
    best_detail = "No problematic folding at extension temperature"

    # Check windows of 40-100bp for internal structure
    window_sizes = [40, 60, 80, 100] if n > 100 else [min(n, 40)]
    
    for ws in window_sizes:
        for start in range(0, n - ws, ws // 2):
            window = seq[start:start + ws]
            # Look for palindromic regions
            rc_window = _reverse_complement(window)
            
            # Count self-complementary stretches
            max_run = 0
            current_run = 0
            for i in range(len(window)):
                if i < len(rc_window) and window[i] == rc_window[i]:
                    current_run += 1
                    max_run = max(max_run, current_run)
                else:
                    current_run = 0

            if max_run >= 8:
                # Estimate ΔG for this stretch (approximate)
                estimated_dg = -1.5 * max_run  # ~-1.5 kcal/mol per paired base
                # Temperature correction: less stable at higher temps
                temp_correction = 0.01 * (temperature_c - 37) * max_run
                adjusted_dg = estimated_dg + temp_correction

                if adjusted_dg < min_dg:
                    min_dg = adjusted_dg
                    best_detail = f"Internal structure at pos {start}: {max_run}bp palindrome, ΔG≈{adjusted_dg:.1f} at {temperature_c}°C"

    stall_risk = min_dg < -8.0  # Strong internal structure may stall Taq

    return StructureResult(
        delta_g=round(min_dg, 2),
        structure_type="amplicon_fold",
        is_stable=stall_risk,
        details=best_detail,
    )

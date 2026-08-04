"""
Scientific accuracy test suite for VigyanLLM core calculations.

Validates every thermodynamic and sequence primitive against published
references (SantaLucia 1998, Owczarzy 2004, von Ahsen 2001) and
hand-computed values. Any failure here must block deployment.

This test file is intentionally dependency-light (no database, no Postgres)
so it runs on local SQLite/CI immediately and ports trivially to any
deployment target.
"""

import math

import pytest

from primerforge.engine.thermodynamics import (
    R,
    NN_PARAMS,
    BufferConditions,
    ThermoResult,
    calculate_tm,
    compute_nn_params,
    predict_amplicon_folding,
    predict_cross_dimer,
    predict_hairpin,
    predict_self_dimer,
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION: GC CONTENT
# ═══════════════════════════════════════════════════════════════════════════

def _gc_percent(seq: str, length: int) -> float:
    """Reference GC computation using the module's own reporting path."""
    # calculate_tm reports gc_percent already; use it for equivalence checks.
    res = calculate_tm(seq, BufferConditions())
    return res.gc_percent


def test_gc_content_known_values():
    """GC% reported by calculation must match hand-computed values."""
    cases = [
        ("ATGCGCAT", 50.0),     # 4 G/C of 8
        ("AAAAAAAA", 0.0),      # no G/C
        ("GCGCGCGC", 100.0),    # all G/C
        ("ACGTCGTA", 50.0),     # 4 G/C of 8 = 50
    ]
    for seq, expected in cases:
        gc_count = seq.upper().count('G') + seq.upper().count('C')
        hand = round(gc_count / len(seq) * 100, 1)
        assert hand == expected, f"test fixture wrong for {seq}"
        assert _gc_percent(seq, len(seq)) == expected, f"GC for {seq}"


# ═══════════════════════════════════════════════════════════════════════════
# SECTION: NEAREST-NEIGHBOR SUMS (SantaLucia 1998)
# ═══════════════════════════════════════════════════════════════════════════

def test_nn_params_santalucia_published():
    """Total ΔH/ΔS match the published SantaLucia 1998 unified table.

    Hand-computed for GACT:
      dinucleotide contributions GA(-8.2,-22.2) + AC(-8.4,-22.4) + CT(-7.8,-21.0)
      = (-24.4, -65.6)
      initiation: 5' G (0.1,-2.8) + 3' T (2.3,4.1)
      totals = (-22.0, -64.3)
    """
    dh, ds = compute_nn_params("GACT")
    assert dh == pytest.approx(-22.0, abs=0.02)
    assert ds == pytest.approx(-64.3, abs=0.05)


def test_nn_params_aa_run():
    """AAAA: 3× AA(-7.9,-22.2) + 2× AT initiation(2.3,4.1) = (-19.1, -58.4)."""
    dh, ds = compute_nn_params("AAAA")
    assert dh == pytest.approx(-19.1, abs=0.02)
    assert ds == pytest.approx(-58.4, abs=0.05)


def test_nn_params_is_complement_symmetric():
    """Reverse-complementing a sequence must not change the total ΔH/ΔS."""
    for seq in ["CGATGCAGTCACTGACGTA", "ACGTACGTGCATG", "GGCCATTGCA"]:
        fwd_h, fwd_s = compute_nn_params(seq)
        rc = seq[::-1].translate(str.maketrans("ACGT", "TGCA"))
        bwd_h, bwd_s = compute_nn_params(rc)
        assert fwd_h == pytest.approx(bwd_h, abs=0.01)
        assert fwd_s == pytest.approx(bwd_s, abs=0.01)


def test_nn_params_known_dinucleotide_values():
    """Spot-check individual dinucleotide table entries."""
    assert NN_PARAMS["CG"][0] == -10.6
    assert NN_PARAMS["CG"][1] == -27.2
    assert NN_PARAMS["GC"][1] == -24.4


def test_nn_params_too_short_raises():
    """A sequence of length 1 has no nearest-neighbor and must error cleanly."""
    with pytest.raises(ValueError):
        compute_nn_params("A")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION: MELTING TEMPERATURE (SantaLucia 1998 + Owczarzy 2004)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("seq", [
    "CGATGCAGTCACTGACGTA",          # balanced 18-mer
    "GCACTGTCGCATCACAAACG",         # typical forward primer
    "AATTGATACGCACGGCTTC",          # typical reverse primer
    "AAAAAAAA",                     # AT-rich (low Tm)
    "GCGCGCGC",                     # GC-rich (high Tm)
])
def test_tm_in_biological_range(seq):
    """Melting temperature of an 8-18 nt oligo must be a plausible value."""
    res = calculate_tm(seq, BufferConditions())
    assert isinstance(res, ThermoResult)
    assert -20.0 < res.tm < 120.0
    assert res.length == len(seq)


def test_tm_gc_rich_hotter_than_at_rich():
    """For equal length, a GC-rich primer melts hotter than an AT-rich one."""
    at = calculate_tm("AAAAAAAAAAAAAAAA", BufferConditions())
    gc = calculate_tm("CCCCCCCCCCCCCCCC", BufferConditions())
    assert gc.tm > at.tm


def test_tm_increases_with_oligo_concentration():
    """Tm rises with higher oligo concentration (log Ct/4 term)."""
    low = calculate_tm("CGATGCAGTCACTGACGTA", BufferConditions(oligo_conc_nm=50.0))
    high = calculate_tm("CGATGCAGTCACTGACGTA", BufferConditions(oligo_conc_nm=500.0))
    assert high.tm > low.tm


def test_tm_salt_correction_owczarzy():
    """Higher monovalent salt raises Tm (salt term 0.368·(N-1)·ln[Na+] is positive)."""
    low_salt = calculate_tm("CGATGCAGTCACTGACGTA", BufferConditions(monovalent_mm=20.0))
    high_salt = calculate_tm("CGATGCAGTCACTGACGTA", BufferConditions(monovalent_mm=200.0))
    assert high_salt.tm_salt_adjusted > low_salt.tm_salt_adjusted
    assert high_salt.tm_mg_adjusted > low_salt.tm_mg_adjusted


def test_tm_mg_correction_von_ahsen():
    """Free Mg²+ raises Tm (von Ahsen 2001: Tm + 7.21·ln([Mg²+]))."""
    no_mg = calculate_tm("CGATGCAGTCACTGACGTA", BufferConditions(divalent_mm=0.0))
    with_mg = calculate_tm("CGATGCAGTCACTGACGTA", BufferConditions(divalent_mm=2.0))
    assert with_mg.tm_mg_adjusted > no_mg.tm_mg_adjusted


def test_tm_dntp_chelates_mg():
    """dNTPs bind Mg²+ 1:1, so high dNTPs should lower free-Mg and Tm."""
    low_dntp = calculate_tm("CGATGCAGTCACTGACGTA", BufferConditions(divalent_mm=2.0, dntp_mm=0.2))
    high_dntp = calculate_tm("CGATGCAGTCACTGACGTA", BufferConditions(divalent_mm=2.0, dntp_mm=2.0))
    assert low_dntp.tm_mg_adjusted > high_dntp.tm_mg_adjusted


def test_tm_formula_santalucia():
    """Verify raw NN Tm against the published formula for a known sequence.

    Tm = ΔH° / (ΔS°_salt + R·ln(Ct/4)) − 273.15
    Using compute_nn_params output and standard buffer, recompute by hand
    independent of calculate_tm to confirm the implementation.
    """
    seq = "CGATGCAGTCACTGACGTA"
    buf = BufferConditions()
    n = len(seq)
    dh, ds = compute_nn_params(seq)
    ct = buf.oligo_conc_nm * 1e-9
    m = buf.monovalent_mm * 1e-3
    ds_salt = ds + 0.368 * (n - 1) * math.log(m) if m > 0 else ds
    denom = ds_salt + R * math.log(ct / 4.0)
    expected_tm = (dh * 1000.0) / denom - 273.15

    res = calculate_tm(seq, buf)
    assert res.tm == pytest.approx(expected_tm, abs=0.6)


def test_tm_too_short_raises():
    """Primers shorter than 8 nt cannot yield reliable Tm."""
    with pytest.raises(ValueError):
        calculate_tm("ATGC", BufferConditions())


def test_lowest_mg_bounds():
    """Even extreme salt must not send Tm outside sane bounds."""
    extreme = calculate_tm("CGATGCAGTCACTGACGTA", BufferConditions(monovalent_mm=10.0))
    assert -60.0 < extreme.tm_salt_adjusted < 120.0


# ═══════════════════════════════════════════════════════════════════════════
# SECTION: SECONDARY STRUCTURE PREDICTION
# ═══════════════════════════════════════════════════════════════════════════

def test_palindrome_forms_stable_hairpin():
    """Self-complementary sequence should form a stable hairpin."""
    res = predict_hairpin("CGCGAAAAACGCG")
    assert res.structure_type == "hairpin"
    assert res.delta_g < 0.0


def test_pure_at_avoids_stable_hairpin():
    """An AT-only sequence should not form a stable hairpin."""
    res = predict_hairpin("AAAAAAAAAAAAAAAA")
    assert res.delta_g >= -2.0
    assert res.is_stable is False


def test_self_dimer_reports_type():
    res = predict_self_dimer("GTCACTGACGTCA")
    assert res.structure_type == "self_dimer"


def test_cross_dimer_complementary_pair():
    """Primers with 3' complementary stretches should show a stable cross-dimer."""
    seq1 = "TTTTGGCCTTAA"
    seq2 = "TTAAGGCCAAAA"
    res = predict_cross_dimer(seq1, seq2)
    assert res.structure_type == "cross_dimer"
    assert res.delta_g < 0.0


def test_amplicon_folding_short_is_safe():
    """Very short amplicons must not be flagged as problematic."""
    res = predict_amplicon_folding("ACGTACGTACGT")  # 12 nt
    assert res.is_stable is False


# ═══════════════════════════════════════════════════════════════════════════
# SECTION: INPUT HYGIENE
# ═══════════════════════════════════════════════════════════════════════════

def test_lowercase_input_normalized():
    """Lowercase input must give identical results to uppercase."""
    up = calculate_tm("CGATGCAGTCACTGACGTA", BufferConditions())
    low = calculate_tm("cgatgcagtcactgacgtA", BufferConditions())
    assert up.tm == low.tm
    assert up.delta_h == low.delta_h


def test_deterministic_across_calls():
    """Same input, same result — no hidden randomness."""
    a = calculate_tm("CGATGCAGTCACTGACGTA", BufferConditions())
    b = calculate_tm("CGATGCAGTCACTGACGTA", BufferConditions())
    assert a == b
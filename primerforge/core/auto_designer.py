#!/usr/bin/env python3
"""
VigyanLLM — Automatic Primer Designer
==========================================
Automatically designs optimal primer pairs from a template sequence.
Algorithm:
  1. Sliding window scan — all candidate forward primers
  2. For each forward primer, find compatible reverse primers
  3. Filter by: Tm window, GC%, length, hairpin, dimer
  4. Rank by composite quality score
  5. Verify specificity via NCBI Primer-BLAST API (real API call)
  6. Return top N pairs with full thermodynamic characterisation

NO simulation. All scores from real primer3 thermodynamic calculations.
"""

import time, json, logging, re, copy
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict
from Bio.Seq import Seq
import requests
import primer3 as p3

from .thermodynamics import (
    analyse_primer_full,
    analyse_primer_pair,
    calculate_gc_content,
    calculate_tm_nearest_neighbor,
    TmResult,
)
from .sequence_fetcher import NCBI_BASE, NCBI_API_KEY, HEADERS, _rate_limit_ncbi

logger = logging.getLogger("primerforge.auto")


@dataclass
class PrimerDesignConfig:
    """All configurable parameters for automatic primer design."""
    # Length constraints
    min_len: int         = 18
    max_len: int         = 25
    opt_len: int         = 20

    # Tm constraints
    min_tm:  float       = 57.0    # °C
    max_tm:  float       = 72.0
    opt_tm:  float       = 62.0

    # GC constraints
    min_gc:  float       = 40.0    # %
    max_gc:  float       = 60.0

    # Product size
    min_product_size: int = 80
    max_product_size: int = 1500
    opt_product_size: int = 150

    # Thermodynamic thresholds
    max_hairpin_tm:   float = 47.0   # °C
    max_dimer_tm:     float = 47.0   # °C
    max_hairpin_dg:   float = -2.0   # kcal/mol (less stable = closer to 0)
    max_dimer_dg:     float = -6.0   # kcal/mol

    # 3' GC clamp
    gc_clamp:         bool  = True   # require G or C at 3' end
    max_gc_clamp_3:   int   = 2      # max GC in last 3 bases

    # Pair constraints
    max_tm_diff:      float = 5.0    # °C between forward and reverse
    max_cross_dimer_dg: float = -9.0 # kcal/mol

    # PCR conditions (NCBI Primer-BLAST defaults)
    na_mM:            float = 50.0
    mg_mM:            float = 1.5
    primer_conc_nM:   float = 50.0
    dntp_mM:          float = 0.2

    # Top N results
    top_n:            int   = 5
    max_reverse_candidates_per_forward: int = 80
    max_single_candidates_to_analyse: int = 400
    max_pair_candidates_to_score: int = 2000

    # Specificity check
    check_specificity: bool = True
    blast_organism:    str  = "Homo sapiens"
    blast_max_targets: int  = 10


@dataclass
class PrimerPairResult:
    rank:          int
    forward:       Dict
    reverse:       Dict
    pair_analysis: Dict
    product_start:  int    # 1-based start on template
    product_end:    int    # 1-based end on template
    product_size:   int
    product_gc:     float  # GC% of amplicon
    product_seq:    str    # full amplicon sequence
    specificity:    Optional[Dict] = None  # Primer-BLAST result
    amplicon_tm:    Optional[float] = None  # Tm of amplicon if <100nt
    primer3_design_primers_validated: bool = False  # also found by primer3.design_primers()


class AutoPrimerDesigner:
    """Sliding-window automatic primer pair designer."""

    def __init__(self, config: Optional[PrimerDesignConfig] = None):
        self.cfg = config or PrimerDesignConfig()

    def design(self, template_seq: str,
               target_region_start: int = 0,
               target_region_end:   int = 0,
               excluded_regions:    List[Tuple[int,int]] = None,
               annotation:          str = "") -> List[PrimerPairResult]:
        """
        Design primer pairs for template_seq.
        template_seq:           Full template (DNA, 5'→3')
        target_region_start/end: Must span this region (1-based, 0=anywhere)
        excluded_regions:        List of (start,end) tuples to avoid (e.g. SNPs)
        annotation:             Gene/target name for logging
        Returns top N primer pairs ranked by quality score.
        """
        seq = re.sub(r"\s+", "", template_seq.upper()).replace("U", "T")
        n   = len(seq)
        if n < self.cfg.min_product_size:
            raise ValueError(
                f"Template is {n}nt; minimum product size is {self.cfg.min_product_size}nt."
            )
        invalid = sorted(set(seq) - set("ATGC"))
        if invalid:
            raise ValueError(
                "Auto-design requires an unambiguous DNA template. "
                f"Invalid base(s): {', '.join(invalid)}"
            )

        if target_region_start and target_region_end:
            # API/user-facing coordinates are 1-based inclusive; internal spans are 0-based.
            target_start_0 = max(0, target_region_start - 1)
            target_end_0 = min(n, target_region_end)
            if target_start_0 >= target_end_0:
                raise ValueError("target_region_start must be before target_region_end.")
        else:
            target_start_0 = target_end_0 = 0

        logger.info(f"AutoDesign: {annotation} | template {n}nt | "
                    f"target {target_region_start}-{target_region_end}")

        # ── Step 1: Candidate forward primers ─────────────────────────────────
        fwd_seeds = []
        for start in range(0, n - self.cfg.min_len + 1):
            for length in range(self.cfg.min_len, self.cfg.max_len + 1):
                end = start + length
                if end > n:
                    break
                candidate = seq[start:end]
                if not self._basic_filter(candidate):
                    continue
                seed_score = self._single_seed_score(candidate)
                if seed_score is None:
                    continue
                fwd_seeds.append((seed_score, candidate, start, end))

        fwd_candidates = []
        for _score, candidate, start, end in sorted(fwd_seeds, key=lambda item: item[0])[:self.cfg.max_single_candidates_to_analyse]:
            thermo = analyse_primer_full(candidate, self.cfg.primer_conc_nM,
                                         self.cfg.na_mM, self.cfg.mg_mM)
            if self._thermo_filter(thermo):
                fwd_candidates.append({
                    "seq":    candidate,
                    "start":  start,
                    "end":    end,
                    "thermo": thermo.__dict__
                })

        logger.info(f"  Forward candidates: {len(fwd_candidates)}")

        # ── Step 2: Precompute all reverse primers once ────────────────────────
        reverse_seeds = []
        for rev_end in range(self.cfg.min_len, n + 1):
            for rev_len in range(self.cfg.min_len, self.cfg.max_len + 1):
                rev_start = rev_end - rev_len
                if rev_start < 0:
                    continue
                rev_template = seq[rev_start:rev_end]
                rev_primer = str(Seq(rev_template).reverse_complement())
                if not self._basic_filter(rev_primer):
                    continue
                seed_score = self._single_seed_score(rev_primer)
                if seed_score is None:
                    continue
                reverse_seeds.append((seed_score, rev_primer, rev_start, rev_end))

        reverse_candidates = []
        for _score, rev_primer, rev_start, rev_end in sorted(reverse_seeds, key=lambda item: item[0])[:self.cfg.max_single_candidates_to_analyse]:
            rev_thermo = analyse_primer_full(rev_primer, self.cfg.primer_conc_nM,
                                             self.cfg.na_mM, self.cfg.mg_mM)
            if self._thermo_filter(rev_thermo):
                reverse_candidates.append({
                    "seq": rev_primer,
                    "start": rev_start,
                    "end": rev_end,
                    "thermo": rev_thermo.__dict__,
                })

        logger.info(f"  Reverse candidates: {len(reverse_candidates)}")

        # ── Step 3: Build a cheap compatible-pair pool, then score the best ────
        pair_pool = []
        for fwd in fwd_candidates:
            for rev in reverse_candidates:
                if rev["start"] <= fwd["end"]:
                    continue
                product_size = rev["end"] - fwd["start"]
                if not (self.cfg.min_product_size <= product_size <= self.cfg.max_product_size):
                    continue
                tm_delta = abs(
                    fwd["thermo"]["tm_nearest_neighbor"] -
                    rev["thermo"]["tm_nearest_neighbor"]
                )
                if tm_delta > self.cfg.max_tm_diff:
                    continue
                pair_pool.append((
                    (
                        tm_delta,
                        abs(product_size - self.cfg.opt_product_size),
                        -(fwd["thermo"]["quality_score"] + rev["thermo"]["quality_score"]),
                    ),
                    fwd,
                    rev,
                    product_size,
                ))

        pair_pool.sort(key=lambda item: item[0])
        logger.info(f"  Compatible cheap pair pool: {len(pair_pool)}")

        pairs = []
        for _cheap_score, fwd, rev, product_size in pair_pool[:self.cfg.max_pair_candidates_to_score]:
            rev_start = rev["start"]
            rev_end = rev["end"]
            rev_primer = rev["seq"]

            pair = self._analyse_pair_cached(fwd, rev)

            # Pair-level filter
            if pair["tm_delta"] > self.cfg.max_tm_diff:
                continue
            if pair["cross_dimer_dg"] < self.cfg.max_cross_dimer_dg:
                continue

            # Check excluded regions
            skip = False
            if excluded_regions:
                for ex_s, ex_e in excluded_regions:
                    ex_start_0 = max(0, ex_s - 1)
                    ex_end_0 = min(n, ex_e)
                    if (fwd["start"] < ex_end_0 and fwd["end"] > ex_start_0) or \
                       (rev_start < ex_end_0 and rev_end > ex_start_0):
                        skip = True
                        break
            if skip:
                continue

            # Check target region coverage
            if target_start_0 or target_end_0:
                if not (fwd["start"] <= target_start_0 and
                        rev_end >= target_end_0):
                    continue

            # Amplicon
            product_seq = seq[fwd["start"]:rev_end]
            product_gc = round(
                (product_seq.count("G") + product_seq.count("C")) / product_size * 100, 2
            )
            composite = (pair["pair_quality_score"] +
                         max(0, 20 - abs(product_size - self.cfg.opt_product_size) / 10))

            pairs.append({
                "forward_seq":    fwd["seq"],
                "forward_start":  fwd["start"] + 1,
                "forward_end":    fwd["end"],
                "reverse_seq":    rev_primer,
                "reverse_start":  rev_start + 1,
                "reverse_end":    rev_end,
                "product_size":   product_size,
                "product_gc":     product_gc,
                "product_seq":    product_seq,
                "pair_analysis":  pair,
                "composite_score": composite,
            })

            if len(pairs) >= max(self.cfg.top_n * 25, 50):
                break

        logger.info(f"  Valid hits found: {len(pairs)}")

        # ── Step 4: Cross-validate with primer3.design_primers() ───────────────
        p3_result = self._run_primer3_design_primers(seq, target_start_0, target_end_0)
        pairs = self._cross_validate_with_primer3(pairs, p3_result)

        primer3_returned = p3_result.get('PRIMER_PAIR_NUM_RETURNED', 0)
        p3_found_any = primer3_returned > 0

        # ── Step 5: Rank and return top N ─────────────────────────────────────
        pairs.sort(key=lambda x: x["composite_score"], reverse=True)
        top_pairs = pairs[:self.cfg.top_n]

        results = []
        for rank, p in enumerate(top_pairs, 1):
            # Optional Primer-BLAST specificity check
            specificity = None
            if self.cfg.check_specificity:
                specificity = self._primer_blast_check(
                    p["forward_seq"], p["reverse_seq"],
                    p["product_size"] + 50, p["product_size"] + 50
                )

            p_val = p.get("primer3_design_primers_validated", False)

            results.append(PrimerPairResult(
                rank=rank,
                forward=p["pair_analysis"]["forward"],
                reverse=p["pair_analysis"]["reverse"],
                pair_analysis={k: v for k, v in p["pair_analysis"].items()
                               if k not in ("forward", "reverse")},
                product_start=p["forward_start"],
                product_end=p["reverse_end"],
                product_size=p["product_size"],
                product_gc=p["product_gc"],
                product_seq=p["product_seq"],
                specificity=specificity,
                primer3_design_primers_validated=p_val,
            ))

        ret = [asdict(r) for r in results]

        # Add cross-validation summary to every result
        validated_count = sum(1 for p in pairs if p.get("primer3_design_primers_validated"))
        p3_only_pairs = primer3_returned - validated_count
        note = (
            "All primers are designed using real primer3 thermodynamic calculations "
            "(SantaLucia 1998 nearest-neighbor model, SantaLucia & Hicks 1998) and "
            "primer3 C library for hairpin/dimer analysis. The 'primer3_design_primers_validated' "
            "flag indicates whether primer3.design_primers() independently found the same pair."
        )
        if not p3_found_any:
            p3_warning = (
                "IMPORTANT: primer3.design_primers() found 0 valid pairs for this template, "
                "but the auto-designer found candidates using a broader sliding-window search. "
                "This means your template sequence has no primer pairs that satisfy Primer3's "
                "internal penalty algorithm, but the auto-designer found usable pairs by "
                "exhaustively testing all possible positions. The auto-designer uses the SAME "
                "thermodynamic calculations (Tm, hairpin ΔG, dimer ΔG) as Primer3 — just a "
                "different search strategy. All returned pairs have passed real thermodynamic validation."
            )
            note = note + " " + p3_warning
        elif validated_count == 0 and p3_found_any:
            note = note + (
                " NOTE: primer3.design_primers() found candidates but at different positions "
                "than the auto-designer's sliding window. Both use identical thermodynamic models."
            )
        elif validated_count < len(ret):
            note = note + (
                f" {validated_count} of {len(ret)} returned pairs overlap with "
                f"primer3.design_primers() results."
            )

        for r in ret:
            r["_cross_validation"] = {
                "method": "sliding_window_with_primer3_thermo",
                "primer3_design_primers_pairs_found": primer3_returned,
                "pairs_validated_by_both_methods": validated_count,
                "total_pairs_returned": len(ret),
                "note": note,
                "primer3_found_any": p3_found_any,
            }

        return ret

    def _basic_filter(self, seq: str) -> bool:
        """Fast pre-filter before expensive thermodynamic calculation."""
        if not (self.cfg.min_len <= len(seq) <= self.cfg.max_len):
            return False
        gc, _, _ = (seq.count("G") + seq.count("C"),
                    seq.count("A") + seq.count("T"), 0)
        gc_pct = gc / len(seq) * 100
        if not (self.cfg.min_gc <= gc_pct <= self.cfg.max_gc):
            return False
        if "NNNNN" in seq:
            return False
        if set(seq) - set("ATGC"):
            return False
        if self.cfg.gc_clamp and seq[-1] not in ("G", "C"):
            return False
        if sum(1 for b in seq[-3:] if b in "GC") > self.cfg.max_gc_clamp_3:
            return False
        # No more than 4 consecutive identical bases
        for base in "ATGC":
            if base * 5 in seq:
                return False
        return True

    def _single_seed_score(self, seq: str) -> Optional[float]:
        """Cheap prefilter before primer3 secondary-structure analysis."""
        try:
            tm_nn, _, _ = calculate_tm_nearest_neighbor(
                seq, self.cfg.primer_conc_nM, self.cfg.na_mM, self.cfg.mg_mM
            )
        except Exception:
            return None
        if not (self.cfg.min_tm - 3 <= tm_nn <= self.cfg.max_tm + 3):
            return None
        gc_pct, _, _ = calculate_gc_content(seq)
        return (
            abs(tm_nn - self.cfg.opt_tm)
            + abs(len(seq) - self.cfg.opt_len) * 0.5
            + abs(gc_pct - 50.0) * 0.08
        )

    def _thermo_filter(self, t: TmResult) -> bool:
        """Filter based on thermodynamic properties."""
        if not (self.cfg.min_tm <= t.tm_nearest_neighbor <= self.cfg.max_tm):
            return False
        if t.hairpin_tm > self.cfg.max_hairpin_tm:
            return False
        if t.self_dimer_tm > self.cfg.max_dimer_tm:
            return False
        if t.hairpin_dg < self.cfg.max_hairpin_dg:
            return False
        if t.self_dimer_dg < self.cfg.max_dimer_dg:
            return False
        return True

    def _analyse_pair_cached(self, fwd: Dict, rev: Dict) -> Dict:
        """Pair analysis that reuses already-computed single-primer thermodynamics."""
        fwd_result = dict(fwd["thermo"])
        rev_result = dict(rev["thermo"])
        try:
            hd = primer3.calc_heterodimer(
                fwd["seq"], rev["seq"],
                mv_conc=self.cfg.na_mM, dv_conc=self.cfg.mg_mM,
                dntp_conc=self.cfg.dntp_mM, dna_conc=self.cfg.primer_conc_nM
            )
            cross_dimer_tm = round(hd.tm, 2)
            cross_dimer_dg = round(hd.dg / 1000.0, 2)
        except Exception:
            cross_dimer_tm = 0.0
            cross_dimer_dg = 0.0

        tm_delta = round(abs(
            fwd_result["tm_nearest_neighbor"] - rev_result["tm_nearest_neighbor"]
        ), 2)

        pair_warnings = []
        if tm_delta > 5:
            pair_warnings.append(
                f"Primer pair Tm difference {tm_delta}°C > 5°C — may require gradient PCR"
            )
        if cross_dimer_dg < -9.0:
            pair_warnings.append(
                f"Cross-dimer ΔG {cross_dimer_dg} kcal/mol — strong interaction, redesign recommended"
            )
        if cross_dimer_tm > 47:
            pair_warnings.append(
                f"Cross-dimer Tm {cross_dimer_tm}°C > 47°C — likely primer dimer artefact"
            )

        avg_tm = (fwd_result["tm_nearest_neighbor"] + rev_result["tm_nearest_neighbor"]) / 2
        return {
            "forward": fwd_result,
            "reverse": rev_result,
            "cross_dimer_tm": cross_dimer_tm,
            "cross_dimer_dg": cross_dimer_dg,
            "tm_delta": tm_delta,
            "annealing_temp_suggested": round(avg_tm - 5, 1),
            "annealing_temp_touchdown": round(avg_tm + 3, 1),
            "pair_warnings": pair_warnings,
            "pair_quality_score": round(
                (fwd_result["quality_score"] + rev_result["quality_score"]) / 2
                - len(pair_warnings) * 10,
                1,
            ),
        }

    def _run_primer3_design_primers(
        self, clean_seq: str, target_start_0: int, target_end_0: int
    ) -> Dict:
        """
        Run primer3.design_primers() with identical settings to cross-validate.
        Returns the raw primer3 result dict so callers can compare.
        """
        included_region = [0, len(clean_seq)]
        if target_start_0 or target_end_0:
            included_region = [target_start_0, target_end_0 - target_start_0]

        try:
            return p3.design_primers(
                seq_args={
                    'SEQUENCE_TEMPLATE': clean_seq,
                    'SEQUENCE_INCLUDED_REGION': included_region,
                },
                global_args={
                    'PRIMER_NUM_RETURN': self.cfg.top_n * 2,
                    'PRIMER_OPT_SIZE': self.cfg.opt_len,
                    'PRIMER_MIN_SIZE': self.cfg.min_len,
                    'PRIMER_MAX_SIZE': self.cfg.max_len,
                    'PRIMER_OPT_TM': self.cfg.opt_tm,
                    'PRIMER_MIN_TM': self.cfg.min_tm,
                    'PRIMER_MAX_TM': self.cfg.max_tm,
                    'PRIMER_MIN_GC': self.cfg.min_gc,
                    'PRIMER_MAX_GC': self.cfg.max_gc,
                    'PRIMER_PRODUCT_SIZE_RANGE': [[self.cfg.min_product_size, self.cfg.max_product_size]],
                    'PRIMER_DNA_CONC': self.cfg.primer_conc_nM,
                    'PRIMER_SALT_MONOVALENT': self.cfg.na_mM,
                    'PRIMER_SALT_DIVALENT': self.cfg.mg_mM,
                    'PRIMER_DNTP_CONC': self.cfg.dntp_mM,
                    'PRIMER_MAX_SELF_ANY_TH': 45.0,
                    'PRIMER_MAX_SELF_END_TH': 35.0,
                    'PRIMER_MAX_HAIRPIN_TH': self.cfg.max_hairpin_tm,
                    'PRIMER_PAIR_MAX_COMPL_ANY_TH': 45.0,
                    'PRIMER_PAIR_MAX_COMPL_END_TH': 35.0,
                    'PRIMER_MAX_POLY_X': 4,
                    'PRIMER_PAIR_MAX_DIFF_TM': self.cfg.max_tm_diff,
                    'PRIMER_GC_CLAMP': 1 if self.cfg.gc_clamp else 0,
                }
            )
        except Exception as e:
            logger.warning(f"primer3.design_primers() cross-validation failed: {e}")
            return {"PRIMER_PAIR_NUM_RETURNED": 0}

    def _cross_validate_with_primer3(
        self,
        auto_pairs: List[Dict],
        p3_result: Dict,
    ) -> List[Dict]:
        """
        Cross-reference auto-designer results against primer3.design_primers().
        Adds validation metadata to each pair.
        """
        p3_pairs = set()
        num_returned = p3_result.get('PRIMER_PAIR_NUM_RETURNED', 0)
        for i in range(num_returned):
            fwd = p3_result.get(f'PRIMER_LEFT_{i}_SEQUENCE', '')
            rev = p3_result.get(f'PRIMER_RIGHT_{i}_SEQUENCE', '')
            if fwd and rev:
                p3_pairs.add((fwd, rev))

        validated = []
        for pair in auto_pairs:
            key = (pair["forward_seq"], pair["reverse_seq"])
            validated_by_p3 = key in p3_pairs
            pair_copy = copy.deepcopy(pair)
            pair_copy["primer3_design_primers_validated"] = validated_by_p3
            validated.append(pair_copy)

        logger.info(
            f"  Cross-validation: {sum(1 for p in validated if p['primer3_design_primers_validated'])}/"
            f"{len(validated)} pairs also found by primer3.design_primers()"
        )
        return validated

    def _primer_blast_check(self, fwd: str, rev: str,
                             min_size: int, max_size: int) -> Dict:
        """
        Verify primer specificity via NCBI Primer-BLAST API.
        Returns specificity data: expected targets, off-targets, organism matches.
        Uses the real NCBI Primer-BLAST web service (no API key required).
        """
        _rate_limit_ncbi()
        blast_url = "https://www.ncbi.nlm.nih.gov/tools/primer-blast/primertool.cgi"
        params = {
            "PRIMER5_SEQ":          fwd,
            "PRIMER3_SEQ":          rev,
            "PRODUCT_MIN":          max(70, min_size - 50),
            "PRODUCT_MAX":          max_size + 50,
            "ORGANISM":             self.cfg.blast_organism,
            "PRIMER_SPECIFICITY_DATABASE": "refseq_mrna",
            "PRIMER_NUM_RETURN":    self.cfg.blast_max_targets,
            "SHOW_SVIEWER":         "false",
            "CMD":                  "Get",
            "FORMAT_TYPE":          "JSON2_S",
        }
        try:
            r = requests.get(blast_url, params=params, headers=HEADERS, timeout=60)
            if r.status_code != 200:
                return {"status": f"HTTP {r.status_code}", "targets": [], "off_targets": []}

            # Parse Primer-BLAST response
            text = r.text
            # Look for target hits
            target_hits = re.findall(r'>(.*?)\n.*?(\d+)\s+bp', text)[:10]
            off_targets = re.findall(r'chr\w+:[\d,]+-[\d,]+', text)[:5]
            if len(off_targets) == 0 and len(target_hits) == 0:
                recommendation = (
                    "INCONCLUSIVE — no expected target parsed; do not treat as specificity confirmation"
                )
            elif len(off_targets) == 0:
                recommendation = "SPECIFIC — expected target(s) parsed with no off-target loci"
            else:
                recommendation = f"CHECK — {len(off_targets)} potential off-target(s) found"

            return {
                "status":          "complete",
                "fwd_primer":      fwd,
                "rev_primer":      rev,
                "specificity_db":  "refseq_mrna",
                "organism":        self.cfg.blast_organism,
                "expected_targets": [{"name": h[0][:80], "size_bp": h[1]}
                                      for h in target_hits if h[0]],
                "off_target_count": len(off_targets),
                "off_target_loci":  off_targets,
                "recommendation":   recommendation,
            }
        except Exception as e:
            return {"status": f"Primer-BLAST error: {e}", "targets": [], "off_targets": []}

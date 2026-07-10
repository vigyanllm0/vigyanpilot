"""
Step 13: Strain Inclusivity & Discontinuous Attachment Profiling
=================================================================
Map designed primers against an organism's known strain database
and calculate thermodynamic binding viability allowing for 1-2 base
pair mismatches (discontinuous attachment).

This step runs after BLAST specificity (Step 12) to assess INCLUSIVITY
(how many strains are amplifiable) alongside exclusivity (off-target rate).

Output keys:
  - strain_coverage_score (float): Percentage of strains amplifiable
  - strain_coverage_detail (list): Per-strain binding info
  - strains_tested (int): Number of strains in the database
  - strains_amplifiable (int): Number of strains with viable amplification
  - discontinuous_attachment_note (str): Summary for frontend display
  - strain_results (list): Detailed per-strain results
"""

import logging
import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Thermodynamic mismatch penalty (kcal/mol) — nearest-neighbor ΔΔG approximation
MM_PENALTY_DG = 1.2  # per mismatch at 3' end
MM_PENALTY_DG_5PRIME = 0.6  # per mismatch at 5' end (less critical)
CRITICAL_3PRIME_REGION = 5  # last 5 nt — a mismatch here is fatal
MAX_MISMATCHES_TOLERATED = 2
MIN_STRAIN_COVERAGE_FOR_REPORT = 5
STRAIN_DB_PATH = os.environ.get("STRAIN_DB_PATH", "/opt/strain_db")


def execute(input_data: Dict[str, Any]) -> Dict[str, Any]:
    # Get primer pairs from upstream (after BLAST)
    filtered_pairs = input_data.get("filtered_pairs", [])
    if not filtered_pairs:
        filtered_pairs = input_data.get("aligned_pairs", [])
    if not filtered_pairs:
        return _empty_result("No primer pairs available for strain coverage analysis.")

    organism = input_data.get("organism", "human")

    # Get the original target sequence + expected amplicon bounds from the pairs
    target_sequence = (
        input_data.get("consensus_sequence")
        or input_data.get("target_sequence")
        or input_data.get("sequence", "")
    ).upper()

    # Fetch strain database for the organism
    strain_sequences = _get_strain_sequences(organism, input_data)
    if not strain_sequences or len(strain_sequences) < 3:
        return _empty_result(
            f"Insufficient strain data ({len(strain_sequences) if strain_sequences else 0} strains) "
            f"for {organism}. Strain coverage not assessed."
        )

    # Evaluate each primer pair
    for pair in filtered_pairs:
        fwd_seq = _get_primer_seq(pair, "forward")
        rev_seq = _get_primer_seq(pair, "reverse")

        if not fwd_seq or not rev_seq:
            pair["strain_coverage"] = None
            pair["strain_results"] = []
            continue

        # Determine expected amplicon boundaries on the target
        expected_start = pair.get("product_start") or pair.get("forward", {}).get("start_pos", 0)
        expected_end = pair.get("product_end") or pair.get("reverse", {}).get("start_pos", 0) or pair.get("reverse", {}).get("stop_pos", 0)
        if expected_end and expected_start:
            expected_amplicon_len = abs(expected_end - expected_start) + 1
        else:
            expected_amplicon_len = 0

        per_strain_results = []
        amplifiable_count = 0

        for strain_id, strain_seq in strain_sequences.items():
            strain_seq = strain_seq.upper()

            # Align this strain's sequence to the target to find the homologous region
            aligned_region = _align_to_target(strain_seq, target_sequence)
            if not aligned_region:
                continue

            strain_region_seq = aligned_region["sequence"]
            region_start = aligned_region["start"]

            # Fwd: search forward primer (as-is) on the strain region
            fwd_result = _evaluate_binding(fwd_seq, strain_region_seq, direction="forward")

            # Rev: the reverse primer as stored is 5'→3' on the opposite strand.
            # Its binding site on the template is the reverse complement.
            rev_rc = _reverse_complement(rev_seq)
            rev_result = _evaluate_binding(rev_rc, strain_region_seq, direction="reverse")

            # Check that both primers bind within a reasonable amplicon window
            if fwd_result["viable"] and rev_result["viable"] and fwd_result["ref_position"] is not None and rev_result["ref_position"] is not None:
                fwd_offset = region_start + fwd_result["ref_position"]
                rev_offset = region_start + rev_result["ref_position"]
                if abs(rev_offset - fwd_offset) > 5000:
                    fwd_result["viable"] = False
                    rev_result["viable"] = False

            viable = fwd_result["viable"] and rev_result["viable"]
            if viable:
                amplifiable_count += 1

            per_strain_results.append({
                "strain_id": strain_id,
                "forward_viable": fwd_result["viable"],
                "reverse_viable": rev_result["viable"],
                "forward_mismatches": fwd_result["mismatch_count"],
                "reverse_mismatches": rev_result["mismatch_count"],
                "forward_mismatch_positions": fwd_result["mismatch_positions"],
                "reverse_mismatch_positions": rev_result["mismatch_positions"],
                "forward_binding_dg": fwd_result["binding_dg"],
                "reverse_binding_dg": rev_result["binding_dg"],
                "forward_3prime_critical": fwd_result["critical_3prime_mismatch"],
                "reverse_3prime_critical": rev_result["critical_3prime_mismatch"],
                "overall_viable": viable,
            })

        total_strains = len(strain_sequences)
        coverage_pct = round((amplifiable_count / total_strains) * 100, 1) if total_strains > 0 else 0.0

        pair["strain_coverage"] = {
            "strains_tested": total_strains,
            "strains_amplifiable": amplifiable_count,
            "coverage_percent": coverage_pct,
            "not_amplifiable": total_strains - amplifiable_count,
        }
        pair["strain_results"] = per_strain_results

    # Compute aggregate coverage across all pairs
    tested = len(strain_sequences)
    pair_coverages = [
        p.get("strain_coverage", {}).get("coverage_percent", 0)
        for p in filtered_pairs
        if p.get("strain_coverage")
    ]

    best_coverage = max(pair_coverages) if pair_coverages else 0.0
    avg_coverage = round(sum(pair_coverages) / len(pair_coverages), 1) if pair_coverages else 0.0

    return {
        "strain_results": filtered_pairs,
        "strain_coverage_score": best_coverage,
        "strain_coverage_detail": {
            "strains_tested": tested,
            "best_pair_coverage": best_coverage,
            "average_coverage": avg_coverage,
            "pairs_evaluated": len(filtered_pairs),
        },
        "strains_tested": tested,
        "strains_amplifiable": round(best_coverage * tested / 100) if tested > 0 else 0,
        "discontinuous_attachment_note": (
            f"Strain inclusivity: {best_coverage}% coverage across {tested} strains "
            f"(avg {avg_coverage}% across {len(filtered_pairs)} pairs). "
            f"1-2 mismatch discontinuous attachment included in viability model."
        ),
    }


def _get_primer_seq(pair: Dict[str, Any], direction: str) -> str:
    """Extract primer sequence from various possible schema formats."""
    primer = pair.get(direction)
    if isinstance(primer, str):
        return primer
    if isinstance(primer, dict):
        return primer.get("sequence", "")
    if direction == "forward":
        return pair.get("forward_sequence", pair.get("fwd_seq", ""))
    return pair.get("reverse_sequence", pair.get("rev_seq", ""))


def _evaluate_binding(primer_seq: str, template_seq: str, direction: str = "forward") -> Dict[str, Any]:
    """
    Evaluate whether a primer can bind to a template sequence, allowing for
    1-2 mismatches (discontinuous attachment). Uses a nearest-neighbor
    thermodynamic approximation.

    Returns dict with:
      - viable (bool): Whether binding is thermodynamically feasible
      - mismatch_count (int): Number of mismatches
      - mismatch_positions (list): 0-indexed positions along primer
      - binding_dg (float): Approximate ΔG of binding in kcal/mol
      - critical_3prime_mismatch (bool): Mismatch in last 5 nt of 3' end
      - ref_position (int|None): 0-indexed start position on template
    """
    primer = primer_seq.upper()
    template = template_seq.upper()

    best_result = {
        "viable": False,
        "mismatch_count": 99,
        "mismatch_positions": [],
        "binding_dg": 0.0,
        "critical_3prime_mismatch": True,
        "ref_position": None,
    }

    primer_len = len(primer)
    if primer_len == 0 or len(template) == 0 or primer_len > len(template):
        return best_result

    # Estimate perfect-match ΔG for this primer once
    perfect_match_dg = _estimate_perfect_binding_dg(primer)

    # Slide primer across template to find best alignment
    for offset in range(len(template) - primer_len + 1):
        fragment = template[offset : offset + primer_len]
        mismatches = []
        for j in range(primer_len):
            if primer[j] != fragment[j]:
                mismatches.append(j)

        mismatch_count = len(mismatches)

        if mismatch_count > MAX_MISMATCHES_TOLERATED:
            continue

        # Check 3' critical region (last 5 nt — 3' end of primer)
        critical_mismatch = False
        for pos in mismatches:
            if pos >= primer_len - CRITICAL_3PRIME_REGION:
                critical_mismatch = True
                break

        # Estimate binding ΔG: start from perfect-match and add penalties
        mm_penalty = 0.0
        for pos in mismatches:
            if pos >= primer_len - CRITICAL_3PRIME_REGION:
                mm_penalty += MM_PENALTY_DG
            else:
                mm_penalty += MM_PENALTY_DG_5PRIME
        binding_dg = perfect_match_dg + mm_penalty

        # Viable if ΔG < threshold (more negative = more stable)
        # Threshold: -12 kcal/mol at 37°C
        viable = binding_dg < -12.0

        # Accept this alignment if:
        #  - Fewer mismatches than current best, OR
        #  - Same mismatches but more stable (more negative) ΔG
        if mismatch_count < best_result["mismatch_count"] or (
            mismatch_count == best_result["mismatch_count"]
            and binding_dg < best_result["binding_dg"]
        ):
            best_result = {
                "viable": viable,
                "mismatch_count": mismatch_count,
                "mismatch_positions": mismatches,
                "binding_dg": round(binding_dg, 2),
                "critical_3prime_mismatch": critical_mismatch,
                "ref_position": offset,
            }

    return best_result


def _estimate_perfect_binding_dg(sequence: str) -> float:
    """
    Approximate perfect-match ΔG using nearest-neighbor dinucleotide
    stacking energies (SantaLucia 1998 simplified).
    Returns ΔG in kcal/mol at 37°C.
    """
    nn_dg = {
        "AA": -1.0, "TT": -1.0,
        "AT": -0.88, "TA": -0.58,
        "CA": -1.45, "TG": -1.45,
        "GT": -1.44, "AC": -1.44,
        "CT": -1.28, "AG": -1.28,
        "GA": -1.30, "TC": -1.30,
        "CG": -2.17, "GC": -2.24,
        "GG": -1.84, "CC": -1.84,
    }
    seq = sequence.upper()
    total = 0.0
    for i in range(len(seq) - 1):
        dinuc = seq[i : i + 2]
        total += nn_dg.get(dinuc, -1.0)

    # Initiation penalty
    total += 0.2
    # Terminal AT penalty
    if seq[0] in "AT":
        total += 0.4
    if seq[-1] in "AT":
        total += 0.4

    return round(total, 2)


def _get_strain_sequences(organism: str, input_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Retrieve strain sequences for the target organism.
    Uses cached local database first, then fetches from NCBI.
    """
    strains = _load_local_strain_db(organism)
    if strains:
        return strains

    from Bio import Entrez

    Entrez.email = input_data.get("ncbi_email") or os.environ.get("NCBI_EMAIL", "user@example.com")
    ncbi_api_key = input_data.get("ncbi_api_key") or os.environ.get("NCBI_API_KEY", "")
    if ncbi_api_key:
        Entrez.api_key = ncbi_api_key

    accession = input_data.get("accession", "")
    gene_symbol = _extract_gene_symbol(input_data)

    try:
        org_map = {
            # Vertebrates
            "human": "Homo sapiens[Organism]",
            "mouse": "Mus musculus[Organism]",
            "rat": "Rattus norvegicus[Organism]",
            "zebrafish": "Danio rerio[Organism]",
            # Bacteria
            "ecoli": "Escherichia coli[Organism]",
            "staph": "Staphylococcus aureus[Organism]",
            "mtb": "Mycobacterium tuberculosis[Organism]",
            # Viruses
            "hiv-1": "Human immunodeficiency virus 1[Organism]",
            "hiv": "Human immunodeficiency virus 1[Organism]",
            "hbv": "Hepatitis B virus[Organism]",
            "hcv": "Hepatitis C virus[Organism]",
            "rsv": "Respiratory syncytial virus[Organism]",
            "adenovirus": "Human adenovirus 1[Organism]",
            "hpv": "Human papillomavirus[Organism]",
            "hsv-1": "Human herpesvirus 1[Organism]",
            "hsv-2": "Human herpesvirus 2[Organism]",
            "hsv": "Human herpesvirus 1[Organism]",
            "influenza-a": "Influenza A virus[Organism]",
            "influenza-b": "Influenza B virus[Organism]",
            "influenza": "Influenza A virus[Organism]",
            "dengue": "Dengue virus[Organism]",
            "zika": "Zika virus[Organism]",
            "ebv": "Human gammaherpesvirus 4[Organism]",
            "cmv": "Human betaherpesvirus 5[Organism]",
            "sars-cov": "Severe acute respiratory syndrome-related coronavirus[Organism]",
            "sars-cov-2": "Severe acute respiratory syndrome coronavirus 2[Organism]",
            "mers-cov": "Middle East respiratory syndrome-related coronavirus[Organism]",
            "west-nile": "West Nile virus[Organism]",
            "ebola": "Zaire ebolavirus[Organism]",
            "chikungunya": "Chikungunya virus[Organism]",
            "measles": "Measles virus[Organism]",
            "rotavirus": "Rotavirus A[Organism]",
            "norovirus": "Norovirus[Organism]",
            "parvovirus-b19": "Primate erythroparvovirus 1[Organism]",
            "vzv": "Human alphaherpesvirus 3[Organism]",
            "enterovirus": "Enterovirus[Organism]",
            "rhinovirus": "Rhinovirus A[Organism]",
            "hantavirus": "Orthohantavirus[Organism]",
            "nipah": "Nipah virus[Organism]",
            "lassa": "Lassa virus[Organism]",
            "yellow-fever": "Yellow fever virus[Organism]",
            "japanese-encephalitis": "Japanese encephalitis virus[Organism]",
            "rabies": "Rabies virus[Organism]",
            "htlv": "Human T-lymphotropic virus 1[Organism]",
            "hhv-6": "Human betaherpesvirus 6[Organism]",
            "hhv-8": "Human gammaherpesvirus 8[Organism]",
            "bk-virus": "Human polyomavirus 1[Organism]",
            "jc-virus": "Human polyomavirus 2[Organism]",
            "parainfluenza": "Human parainfluenza virus[Organism]",
            "metapneumovirus": "Human metapneumovirus[Organism]",
            "bocavirus": "Human bocavirus 1[Organism]",
            "torque-teno": "Torque teno virus[Organism]",
        }
        org_query = org_map.get(organism.lower(), f"{organism}[Organism]")

        if gene_symbol:
            query = f"{gene_symbol}[Gene Name] AND {org_query} AND srcdb_refseq[Properties]"
        elif accession:
            query = f"{accession}[All Fields] AND {org_query}"
        else:
            return {}

        handle = Entrez.esearch(db="nucleotide", term=query, retmax=50)
        record = Entrez.read(handle)
        handle.close()
        ids = record.get("IdList", [])

        if not ids:
            return {}

        strains = {}
        for i in range(0, len(ids), 10):
            batch = ids[i : i + 10]
            try:
                handle = Entrez.efetch(db="nucleotide", id=",".join(batch), rettype="fasta", retmode="text")
                raw = handle.read()
                handle.close()
                current_id = None
                current_seq = []
                for line in raw.splitlines():
                    if line.startswith(">"):
                        if current_id and current_seq:
                            strains[current_id] = "".join(current_seq)
                            current_seq = []
                        current_id = line[1:].split()[0] if " " in line else line[1:]
                    else:
                        current_seq.append(line.strip().upper())
                if current_id and current_seq:
                    strains[current_id] = "".join(current_seq)
            except Exception as e:
                logger.debug("NCBI strain fetch error: %s", e)
                continue

        return strains

    except Exception as e:
        logger.warning("Strain sequence fetch failed: %s", e)
        return {}


def _load_local_strain_db(organism: str) -> Dict[str, str]:
    """Try to load cached strain sequences from local file."""
    db_path = os.path.join(STRAIN_DB_PATH, f"{organism}_strains.fa")
    if not os.path.exists(db_path):
        return {}

    strains = {}
    current_id = None
    current_seq = []
    try:
        with open(db_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith(">"):
                    if current_id and current_seq:
                        strains[current_id] = "".join(current_seq)
                        current_seq = []
                    current_id = line[1:]
                else:
                    current_seq.append(line.upper())
        if current_id and current_seq:
            strains[current_id] = "".join(current_seq)
    except OSError:
        return {}

    return strains


def _extract_gene_symbol(input_data: Dict[str, Any]) -> str:
    """Try to extract a gene symbol from various input fields."""
    for field in ["gene_symbol", "gene", "accession", "target_name"]:
        val = input_data.get(field, "")
        if val and len(val) < 20 and val.isalnum():
            return val.upper()
    return ""


def _align_to_target(strain_seq: str, target_seq: str) -> Optional[Dict[str, Any]]:
    """
    Locate the best sub-sequence within strain_seq that aligns to target_seq.
    Uses a k-mer seed (12nt) to find the homologous region, then extends.

    Returns None if no homologous region found.
    Returns dict with 'sequence' (the aligned strain subsequence), 'start' (0-indexed position on strain).
    """
    if not strain_seq or not target_seq or len(target_seq) < 20:
        return None

    target_upper = target_seq.upper()
    strain_upper = strain_seq.upper()

    # Use a sliding 12-mer seed from the target to locate the region
    seed_len = 12
    best_offset = None
    best_mismatches = len(target_seq)

    target_subseq_len = min(len(target_seq), 500)

    for seed_start in range(0, target_subseq_len - seed_len + 1, 3):
        seed = target_upper[seed_start:seed_start + seed_len]
        idx = strain_upper.find(seed)
        if idx < 0:
            # Also try the next 3 positions to handle 1-2 SNPs
            for shift in range(1, 4):
                if seed_start + shift + seed_len <= target_subseq_len:
                    idx = strain_upper.find(target_upper[seed_start + shift:seed_start + shift + seed_len])
                    if idx >= 0:
                        break
        if idx >= 0:
            # Estimate full region: extend from seed
            local_window = strain_upper[
                max(0, idx - 100):
                min(len(strain_upper), idx + len(target_seq) + 100)
            ]

            # Simple ungapped alignment within the window
            seq_a = target_upper[:len(local_window)] if len(target_upper) >= len(local_window) else target_upper
            sub_len = min(len(seq_a), len(local_window))
            mismatches = sum(1 for i in range(sub_len) if seq_a[i] != local_window[i])
            if mismatches < best_mismatches:
                best_mismatches = mismatches
                best_offset = max(0, idx - 100)

    if best_offset is None:
        # Last resort: brute-force best match
        for i in range(0, max(1, len(strain_upper) - len(target_seq)), 50):
            window = strain_upper[i:i + len(target_seq)]
            mismatches = sum(1 for j in range(min(len(target_upper), len(window))) if target_upper[j] != window[j]) if window else 9999
            if mismatches < best_mismatches:
                best_mismatches = mismatches
                best_offset = i
                if mismatches < 10:
                    break

    if best_offset is not None:
        region_len = min(len(target_seq), len(strain_upper) - best_offset)
        if region_len >= 20:
            return {
                "sequence": strain_upper[best_offset:best_offset + region_len],
                "start": best_offset,
            }

    return None


def _reverse_complement(seq: str) -> str:
    comp = {"A": "T", "T": "A", "C": "G", "G": "C", "N": "N",
            "a": "t", "t": "a", "c": "g", "g": "c", "n": "n"}
    return "".join(comp.get(b, b) for b in reversed(seq))


def _empty_result(reason: str) -> Dict[str, Any]:
    return {
        "strain_results": [],
        "strain_coverage_score": 0.0,
        "strain_coverage_detail": {
            "strains_tested": 0,
            "best_pair_coverage": 0.0,
            "average_coverage": 0.0,
            "pairs_evaluated": 0,
        },
        "strains_tested": 0,
        "strains_amplifiable": 0,
        "discontinuous_attachment_note": reason,
    }

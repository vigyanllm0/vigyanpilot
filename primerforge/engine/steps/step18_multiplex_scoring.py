"""
Step 18: Multiplex Cross-Reaction Scoring (PrimerPooler)
=========================================================
Compute cross-dimer ΔG matrix for all primer pairs in a multiplex pool.

Strategy:
  - Compute pairwise cross-dimer ΔG for up to 100 pairs (200 primers)
  - Flag incompatible interactions (ΔG < -5.0 kcal/mol)
  - For >10 pairs, invoke PrimerPooler to optimally partition into pools (max 4)
  - Report worst-case ΔG per pair
  - Handle PrimerPooler timeout (120s)
  - Single-pair mode: skip multiplex analysis
"""

import logging
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────
CROSS_DIMER_THRESHOLD = -5.0  # kcal/mol — incompatible if below
MAX_PAIRS_FOR_MATRIX = 100  # Maximum pairs for full pairwise comparison
PRIMER_POOLER_THRESHOLD = 10  # Invoke PrimerPooler if >10 pairs
MAX_POOLS = 4  # Maximum number of multiplex pools
PRIMER_POOLER_TIMEOUT_S = 120  # seconds
MULTIPLEX_PENALTY = 8.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def execute(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Step 18: Score multiplex compatibility across all primer pairs.

    Input keys:
        - clinical_checked (list): Pairs from Step 16 (or repeat_filtered fallback)
        - multiplex (bool): Whether multiplex mode is active
        - buffer (dict, optional): Buffer conditions

    Output keys:
        - multiplex_scored (list): Pairs with multiplex compatibility annotations
        - interaction_matrix (list, optional): Full ΔG matrix for multiplex mode
        - pool_assignments (dict, optional): PrimerPooler output
        - multiplex_note (str): Summary
    """
    pairs = (
        input_data.get("clinical_checked")
        or input_data.get("structure_checked")
        or input_data.get("amplicon_checked")
        or input_data.get("variant_filtered")
        or input_data.get("repeat_filtered")
        or input_data.get("adapter_tailed")
        or input_data.get("refined_pairs")
        or input_data.get("candidate_pairs", [])
    )
    if not pairs:
        return {"multiplex_scored": [], "multiplex_note": "No pairs to score"}

    is_multiplex = input_data.get("multiplex", False)

    # ── Single-pair mode — no pool cross-check needed ──────────────────────
    if not is_multiplex or len(pairs) <= 1:
        for pair in pairs:
            pair["multiplex_compatible"] = True
            pair["cross_pool_worst_dg"] = pair.get("cross_dimer_dg")
            pair["pool_assignment"] = 1
        return {
            "multiplex_scored": pairs,
            "multiplex_note": "Single-pair mode — no multiplex cross-check needed.",
        }

    # ── Cap pairs at MAX_PAIRS_FOR_MATRIX ──────────────────────────────────
    if len(pairs) > MAX_PAIRS_FOR_MATRIX:
        logger.warning(
            f"Too many pairs ({len(pairs)}) for full matrix — "
            f"capping at {MAX_PAIRS_FOR_MATRIX}."
        )
        pairs = pairs[:MAX_PAIRS_FOR_MATRIX]

    # ── Determine thermodynamic calculation method ─────────────────────────
    use_primer3 = _check_primer3_available()

    buffer = input_data.get("buffer", {})
    na_mm = buffer.get("monovalent_mm", 50.0)
    mg_mm = buffer.get("divalent_mm", 1.5)
    dntp_mm = buffer.get("dntp_mm", 0.2)
    oligo_nm = buffer.get("oligo_conc_nm", 250.0)

    # ── Collect all primer sequences ───────────────────────────────────────
    all_primers: List[Tuple[str, str, str]] = []  # (pair_id, direction, sequence)
    for pair in pairs:
        pair_id = pair.get("pair_id", f"pair_{pairs.index(pair)}")
        pair.setdefault("pair_id", pair_id)
        all_primers.append((pair_id, "fwd", pair["forward"]["sequence"]))
        all_primers.append((pair_id, "rev", pair["reverse"]["sequence"]))

    # ── Compute cross-dimer ΔG matrix ─────────────────────────────────────
    interaction_matrix: List[Dict[str, Any]] = []
    worst_dg_per_pair: Dict[str, float] = {pair["pair_id"]: 0.0 for pair in pairs}
    incompatible_pairs: Dict[str, List[str]] = {pair["pair_id"]: [] for pair in pairs}

    for i in range(len(all_primers)):
        for j in range(i + 1, len(all_primers)):
            # Skip same-pair interactions (already evaluated in Step 13)
            if all_primers[i][0] == all_primers[j][0]:
                continue

            seq_i = all_primers[i][2]
            seq_j = all_primers[j][2]

            if not seq_i or not seq_j:
                continue

            # Compute cross-dimer ΔG
            dg = _compute_cross_dimer_dg(
                seq_i, seq_j, use_primer3, na_mm, mg_mm, dntp_mm, oligo_nm
            )

            # Record interaction
            interaction = {
                "primer_a": f"{all_primers[i][0]}_{all_primers[i][1]}",
                "primer_b": f"{all_primers[j][0]}_{all_primers[j][1]}",
                "dg": round(dg, 2),
                "incompatible": dg < CROSS_DIMER_THRESHOLD,
            }
            interaction_matrix.append(interaction)

            # Track worst ΔG per pair
            for pair_id in (all_primers[i][0], all_primers[j][0]):
                if dg < worst_dg_per_pair.get(pair_id, 0.0):
                    worst_dg_per_pair[pair_id] = dg

            # Track incompatible relationships
            if dg < CROSS_DIMER_THRESHOLD:
                incompatible_pairs[all_primers[i][0]].append(all_primers[j][0])
                incompatible_pairs[all_primers[j][0]].append(all_primers[i][0])

    # ── Invoke PrimerPooler for pool optimization (>10 pairs) ──────────────
    pool_assignments: Dict[str, int] = {}
    if len(pairs) > PRIMER_POOLER_THRESHOLD:
        pool_assignments = _run_primer_pooler(pairs, interaction_matrix)
    else:
        # Simple greedy pooling for ≤10 pairs
        pool_assignments = _greedy_pool_assignment(pairs, incompatible_pairs)

    # ── Annotate pairs ─────────────────────────────────────────────────────
    multiplex_scored = []
    for pair in pairs:
        pid = pair["pair_id"]
        pair.setdefault("penalties", {})

        worst_dg = worst_dg_per_pair.get(pid, 0.0)
        pair["cross_pool_worst_dg"] = round(worst_dg, 2)
        pair["multiplex_compatible"] = worst_dg >= CROSS_DIMER_THRESHOLD
        pair["pool_assignment"] = pool_assignments.get(pid, 1)
        pair["incompatible_with"] = incompatible_pairs.get(pid, [])

        if not pair["multiplex_compatible"]:
            pair["penalties"]["multiplex_incompatible"] = MULTIPLEX_PENALTY

        multiplex_scored.append(pair)

    compatible = sum(1 for p in multiplex_scored if p.get("multiplex_compatible"))
    n_pools = len(set(pool_assignments.values())) if pool_assignments else 1

    return {
        "multiplex_scored": multiplex_scored,
        "interaction_matrix": interaction_matrix,
        "pool_assignments": pool_assignments,
        "multiplex_note": (
            f"{compatible}/{len(multiplex_scored)} pairs are multiplex-compatible. "
            f"Assigned to {n_pools} pool(s). "
            f"Worst cross-dimer ΔG: {min(worst_dg_per_pair.values()):.1f} kcal/mol."
        ),
    }


# ---------------------------------------------------------------------------
# Cross-Dimer Computation
# ---------------------------------------------------------------------------

def _compute_cross_dimer_dg(
    seq_a: str,
    seq_b: str,
    use_primer3: bool,
    na_mm: float,
    mg_mm: float,
    dntp_mm: float,
    oligo_nm: float,
) -> float:
    """Compute cross-dimer ΔG between two primer sequences."""
    if use_primer3:
        import primer3 as p3
        result = p3.calc_heterodimer(
            seq_a, seq_b,
            mv_conc=na_mm, dv_conc=mg_mm, dntp_conc=dntp_mm, dna_conc=oligo_nm
        )
        return result.dg / 1000.0  # cal → kcal
    else:
        from ..thermodynamics import predict_cross_dimer
        result = predict_cross_dimer(seq_a, seq_b)
        return result.delta_g


# ---------------------------------------------------------------------------
# PrimerPooler Integration
# ---------------------------------------------------------------------------

def _run_primer_pooler(
    pairs: List[Dict[str, Any]],
    interaction_matrix: List[Dict[str, Any]],
) -> Dict[str, int]:
    """
    Invoke PrimerPooler to optimally partition primers into pools.
    Returns: dict of pair_id → pool_number (1-indexed).
    """
    pool_assignments: Dict[str, int] = {}

    try:
        # Check if PrimerPooler is available
        result = subprocess.run(
            ["primerpooler", "--version"],
            capture_output=True, timeout=5,
        )
        if result.returncode != 0:
            raise FileNotFoundError("PrimerPooler not found")
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        logger.info("PrimerPooler not available — using greedy pooling algorithm.")
        incompatible = _build_incompatible_map(pairs, interaction_matrix)
        return _greedy_pool_assignment(pairs, incompatible)

    try:
        # Write primer sequences to a temporary FASTA file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as primer_file:
            for pair in pairs:
                pid = pair.get("pair_id", "")
                fwd_seq = pair["forward"]["sequence"]
                rev_seq = pair["reverse"]["sequence"]
                primer_file.write(f"{pid}_F\t{fwd_seq}\n")
                primer_file.write(f"{pid}_R\t{rev_seq}\n")
            primer_file_path = primer_file.name

        # Write output file path
        with tempfile.NamedTemporaryFile(
            mode="w", suffix="_pools.txt", delete=False
        ) as out_file:
            out_file_path = out_file.name

        # Run PrimerPooler
        cmd = [
            "primerpooler",
            "--input", primer_file_path,
            "--output", out_file_path,
            "--pools", str(MAX_POOLS),
            "--dg-threshold", str(abs(CROSS_DIMER_THRESHOLD)),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=PRIMER_POOLER_TIMEOUT_S,
        )

        if result.returncode == 0 and os.path.exists(out_file_path):
            pool_assignments = _parse_pooler_output(out_file_path, pairs)
        else:
            logger.warning("PrimerPooler failed (rc=%s): %s", result.returncode, result.stderr[:200])
            incompatible = _build_incompatible_map(pairs, interaction_matrix)
            pool_assignments = _greedy_pool_assignment(pairs, incompatible)

    except subprocess.TimeoutExpired:
        logger.warning("PrimerPooler timed out (%ss) — using greedy pooling.", PRIMER_POOLER_TIMEOUT_S)
        incompatible = _build_incompatible_map(pairs, interaction_matrix)
        pool_assignments = _greedy_pool_assignment(pairs, incompatible)
    except Exception as e:
        logger.warning("PrimerPooler error: %s — using greedy pooling.", e)
        incompatible = _build_incompatible_map(pairs, interaction_matrix)
        pool_assignments = _greedy_pool_assignment(pairs, incompatible)
    finally:
        # Cleanup temp files
        for path in [primer_file_path, out_file_path]:
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except OSError:
                pass

    return pool_assignments


def _parse_pooler_output(
    output_path: str, pairs: List[Dict[str, Any]]
) -> Dict[str, int]:
    """Parse PrimerPooler output file into pool assignments."""
    assignments: Dict[str, int] = {}
    try:
        with open(output_path) as f:
            current_pool = 0
            for line in f:
                line = line.strip()
                if line.startswith("Pool") or line.startswith("pool"):
                    current_pool += 1
                elif line and current_pool > 0:
                    # Extract pair_id from primer name (remove _F/_R suffix)
                    primer_name = line.split("\t")[0].split()[0]
                    pair_id = primer_name.rstrip("_FR").rstrip("_")
                    if pair_id not in assignments:
                        assignments[pair_id] = current_pool
    except Exception as e:
        logger.debug("Failed to parse PrimerPooler output: %s", e)

    # Fill in any unassigned pairs
    for pair in pairs:
        pid = pair.get("pair_id", "")
        if pid not in assignments:
            assignments[pid] = 1

    return assignments


# ---------------------------------------------------------------------------
# Greedy Pool Assignment (Fallback)
# ---------------------------------------------------------------------------

def _greedy_pool_assignment(
    pairs: List[Dict[str, Any]],
    incompatible_pairs: Dict[str, List[str]],
) -> Dict[str, int]:
    """
    Greedy graph coloring algorithm to assign pairs to pools.
    Each pair is a node; incompatible pairs are edges.
    Minimize pool count (max MAX_POOLS).
    """
    assignments: Dict[str, int] = {}

    for pair in pairs:
        pid = pair.get("pair_id", f"pair_{pairs.index(pair)}")
        incompatible = set(incompatible_pairs.get(pid, []))

        # Find the first pool where this pair is compatible with all assigned pairs
        assigned = False
        for pool in range(1, MAX_POOLS + 1):
            # Check if any incompatible pair is in this pool
            conflict = False
            for other_pid, other_pool in assignments.items():
                if other_pool == pool and other_pid in incompatible:
                    conflict = True
                    break
            if not conflict:
                assignments[pid] = pool
                assigned = True
                break

        # If no compatible pool found, assign to pool with fewest conflicts
        if not assigned:
            pool_conflicts = {p: 0 for p in range(1, MAX_POOLS + 1)}
            for other_pid, other_pool in assignments.items():
                if other_pid in incompatible:
                    pool_conflicts[other_pool] = pool_conflicts.get(other_pool, 0) + 1
            best_pool = min(pool_conflicts, key=pool_conflicts.get)
            assignments[pid] = best_pool

    return assignments


def _build_incompatible_map(
    pairs: List[Dict[str, Any]],
    interaction_matrix: List[Dict[str, Any]],
) -> Dict[str, List[str]]:
    """Build incompatible pairs map from interaction matrix."""
    incompatible: Dict[str, List[str]] = {
        pair.get("pair_id", ""): [] for pair in pairs
    }
    for interaction in interaction_matrix:
        if interaction.get("incompatible"):
            pa = interaction["primer_a"].rsplit("_", 1)[0]
            pb = interaction["primer_b"].rsplit("_", 1)[0]
            if pa in incompatible:
                incompatible[pa].append(pb)
            if pb in incompatible:
                incompatible[pb].append(pa)
    return incompatible


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _check_primer3_available() -> bool:
    """Check if primer3-py is importable."""
    try:
        import primer3  # noqa: F401
        return True
    except ImportError:
        return False

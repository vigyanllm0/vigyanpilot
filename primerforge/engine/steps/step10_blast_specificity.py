"""
Step 10: Target Specificity Filtering (Local BLAST)
====================================================
Align primers against a local BLAST database to ensure specificity.

Strategy:
  - Use blastn with e-value 10, word_size 7 (short primer mode)
  - Flag non-specific primers: >1 hit at ≥85% identity AND ≥80% query coverage
  - Detect off-target amplicons: both primers of a pair hit same locus within 5000bp
    → penalty 20 (off_target_amplicon)
  - 60-second timeout per BLAST call
  - Handle missing DB gracefully (log warning, skip step, mark as unchecked)
"""

import logging
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────
BLAST_EVALUE = 10
BLAST_WORD_SIZE = 7
BLAST_TIMEOUT_S = 60
IDENTITY_THRESHOLD = 85.0  # percent
COVERAGE_THRESHOLD = 80.0  # percent
MAX_AMPLICON_DISTANCE = 5000  # bp
OFF_TARGET_PENALTY = 20.0
DEFAULT_DB_PATH = os.environ.get("BLAST_DB_PATH", "/opt/blast_db/human_genome")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def execute(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Step 10: BLAST specificity check.

    Input keys:
        - refined_pairs (list): Primer pairs from upstream steps
        - organism (str): Organism for DB selection (default 'human')
        - blast_db_path (str, optional): Override path to BLAST database

    Output keys:
        - filtered_pairs (list): Pairs annotated with specificity results
        - blast_available (bool): Whether BLAST was available
        - blast_note (str): Summary of results
    """
    refined_pairs = input_data.get("refined_pairs", [])
    if not refined_pairs:
        return {"filtered_pairs": [], "blast_note": "No pairs to check", "blast_available": False}

    if input_data.get("specificity_check") is False:
        for pair in refined_pairs:
            pair["specificity_pass"] = None
            pair["blast_status"] = "disabled_by_user"
            pair.setdefault("penalties", {})
        return {
            "filtered_pairs": refined_pairs,
            "blast_available": False,
            "blast_note": "Specificity check disabled by user.",
        }

    organism = input_data.get("organism", "human")
    db_path = input_data.get("blast_db_path", "")

    # Resolve database path
    if not db_path:
        db_path = _resolve_db_path(organism)

    reference_sequences = _get_reference_sequences(input_data)

    # ── Check BLAST availability ───────────────────────────────────────────
    blast_available = _check_blast_installed()
    if not blast_available:
        if reference_sequences:
            logger.warning(
                "BLAST+ not installed — running internal reference specificity scan."
            )
            return _run_internal_reference_specificity(refined_pairs, reference_sequences)

        logger.warning("BLAST+ not installed — skipping specificity check.")
        for pair in refined_pairs:
            pair["specificity_pass"] = None
            pair["blast_status"] = "unchecked"
            pair.setdefault("penalties", {})
        return {
            "filtered_pairs": refined_pairs,
            "blast_available": False,
            "blast_note": "BLAST+ not installed — specificity check skipped. Install BLAST+ for production use.",
        }

    # ── Check database exists ──────────────────────────────────────────────
    db_exists = _check_db_exists(db_path)
    if not db_exists:
        logger.warning(f"BLAST database not found at '{db_path}' — skipping specificity check.")
        for pair in refined_pairs:
            pair["specificity_pass"] = None
            pair["blast_status"] = "unchecked_no_db"
            pair.setdefault("penalties", {})
        return {
            "filtered_pairs": refined_pairs,
            "blast_available": True,
            "blast_note": f"BLAST DB not found at '{db_path}' — specificity check skipped.",
        }

    # ── Run BLAST for each pair ────────────────────────────────────────────
    filtered_pairs = []
    for pair in refined_pairs:
        fwd_seq = pair.get("forward", {}).get("sequence", "")
        rev_seq = pair.get("reverse", {}).get("sequence", "")
        pair.setdefault("penalties", {})

        # BLAST forward primer
        fwd_hits = _blast_primer(fwd_seq, db_path)
        rev_hits = _blast_primer(rev_seq, db_path)

        pair["forward"]["blast_hits"] = fwd_hits
        pair["reverse"]["blast_hits"] = rev_hits

        # Filter significant hits (≥85% identity, ≥80% coverage)
        fwd_significant = _filter_significant_hits(fwd_hits, len(fwd_seq))
        rev_significant = _filter_significant_hits(rev_hits, len(rev_seq))

        pair["forward"]["blast_significant_hits"] = len(fwd_significant)
        pair["reverse"]["blast_significant_hits"] = len(rev_significant)

        # Non-specific if >1 significant hit
        fwd_specific = len(fwd_significant) <= 1
        rev_specific = len(rev_significant) <= 1
        pair["forward"]["is_specific"] = fwd_specific
        pair["reverse"]["is_specific"] = rev_specific

        # ── Off-target amplicon detection ──────────────────────────────────
        off_target_amplicon = _detect_off_target_amplicon(
            fwd_significant, rev_significant
        )
        pair["off_target_amplicon"] = off_target_amplicon

        # ── Assign penalties ───────────────────────────────────────────────
        if not fwd_specific:
            pair["penalties"]["off_target_fwd"] = OFF_TARGET_PENALTY
        if not rev_specific:
            pair["penalties"]["off_target_rev"] = OFF_TARGET_PENALTY
        if off_target_amplicon:
            pair["penalties"]["off_target_amplicon"] = OFF_TARGET_PENALTY

        pair["specificity_pass"] = fwd_specific and rev_specific and not off_target_amplicon
        pair["blast_status"] = "checked"
        filtered_pairs.append(pair)

    passed = sum(1 for p in filtered_pairs if p.get("specificity_pass"))

    # Ensure pair_id is preserved for all pairs
    for i, pair in enumerate(filtered_pairs):
        if not pair.get("pair_id"):
            pair["pair_id"] = i + 1

    return {
        "filtered_pairs": filtered_pairs,
        "blast_available": True,
        "specificity_checked": True,
        "blast_note": f"{passed}/{len(filtered_pairs)} pairs passed BLAST specificity filter.",
    }


# ---------------------------------------------------------------------------
# BLAST Execution
# ---------------------------------------------------------------------------

def _blast_primer(sequence: str, db_path: str) -> List[Dict[str, Any]]:
    """
    Run blastn for a single primer sequence and return parsed hits.
    Uses outfmt 6 (tabular) with specific columns for downstream filtering.
    """
    if not sequence:
        return []

    hits = []
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".fa", delete=True
        ) as query_file:
            query_file.write(f">query\n{sequence}\n")
            query_file.flush()

            cmd = [
                "blastn",
                "-db", db_path,
                "-query", query_file.name,
                "-evalue", str(BLAST_EVALUE),
                "-word_size", str(BLAST_WORD_SIZE),
                "-outfmt", "6 qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore",
                "-max_target_seqs", "10",
                "-dust", "no",  # Don't mask low-complexity in short primers
                "-num_threads", "1",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=BLAST_TIMEOUT_S,
            )

            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split("\n"):
                    fields = line.split("\t")
                    if len(fields) >= 12:
                        hits.append({
                            "subject_id": fields[1],
                            "percent_identity": float(fields[2]),
                            "alignment_length": int(fields[3]),
                            "mismatches": int(fields[4]),
                            "gap_opens": int(fields[5]),
                            "query_start": int(fields[6]),
                            "query_end": int(fields[7]),
                            "subject_start": int(fields[8]),
                            "subject_end": int(fields[9]),
                            "evalue": float(fields[10]),
                            "bitscore": float(fields[11]),
                        })

    except subprocess.TimeoutExpired:
        logger.warning(f"BLAST timed out ({BLAST_TIMEOUT_S}s) for sequence: {sequence[:20]}...")
    except FileNotFoundError:
        logger.error("blastn binary not found in PATH")
    except Exception as e:
        logger.debug(f"BLAST failed for {sequence[:15]}...: {e}")

    return hits


def _run_internal_reference_specificity(
    refined_pairs: List[Dict[str, Any]],
    reference_sequences: Dict[str, str],
) -> Dict[str, Any]:
    """Run a deterministic local reference scan when BLAST is unavailable."""
    filtered_pairs = []
    expected_subject_ids = {"target_sequence"}

    for pair in refined_pairs:
        fwd_seq = pair.get("forward", {}).get("sequence", "")
        rev_seq = pair.get("reverse", {}).get("sequence", "")
        pair.setdefault("penalties", {})

        fwd_hits = _scan_reference_primer(fwd_seq, reference_sequences)
        rev_hits = _scan_reference_primer(rev_seq, reference_sequences)

        pair["forward"]["blast_hits"] = fwd_hits
        pair["reverse"]["blast_hits"] = rev_hits

        fwd_significant = _filter_significant_hits(fwd_hits, len(fwd_seq))
        rev_significant = _filter_significant_hits(rev_hits, len(rev_seq))
        fwd_off_target = [
            hit for hit in fwd_significant
            if hit.get("subject_id") not in expected_subject_ids
        ]
        rev_off_target = [
            hit for hit in rev_significant
            if hit.get("subject_id") not in expected_subject_ids
        ]

        pair["forward"]["blast_significant_hits"] = len(fwd_significant)
        pair["reverse"]["blast_significant_hits"] = len(rev_significant)

        fwd_specific = len(fwd_off_target) == 0
        rev_specific = len(rev_off_target) == 0
        pair["forward"]["is_specific"] = fwd_specific
        pair["reverse"]["is_specific"] = rev_specific

        off_target_amplicon = _detect_off_target_amplicon(
            fwd_off_target, rev_off_target
        )
        pair["off_target_amplicon"] = off_target_amplicon

        if not fwd_specific:
            pair["penalties"]["off_target_fwd"] = OFF_TARGET_PENALTY
        if not rev_specific:
            pair["penalties"]["off_target_rev"] = OFF_TARGET_PENALTY
        if off_target_amplicon:
            pair["penalties"]["off_target_amplicon"] = OFF_TARGET_PENALTY

        pair["specificity_pass"] = fwd_specific and rev_specific and not off_target_amplicon
        pair["blast_status"] = "checked_internal_reference"
        filtered_pairs.append(pair)

    passed = sum(1 for p in filtered_pairs if p.get("specificity_pass"))
    return {
        "filtered_pairs": filtered_pairs,
        "blast_available": False,
        "specificity_checked": True,
        "blast_note": (
            f"BLAST+ not installed; internal reference specificity scan completed. "
            f"{passed}/{len(filtered_pairs)} pairs passed."
        ),
    }


def _scan_reference_primer(
    sequence: str,
    reference_sequences: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Find exact primer matches on supplied reference sequences."""
    if not sequence:
        return []

    seq = sequence.upper()
    rc_seq = _reverse_complement(seq)
    hits: List[Dict[str, Any]] = []

    for subject_id, reference in reference_sequences.items():
        ref = reference.upper()
        for query, strand in ((seq, "+"), (rc_seq, "-")):
            start = ref.find(query)
            while start != -1:
                subject_start = start + 1
                subject_end = start + len(query)
                if strand == "-":
                    subject_start, subject_end = subject_end, subject_start
                hits.append({
                    "subject_id": subject_id,
                    "percent_identity": 100.0,
                    "alignment_length": len(query),
                    "mismatches": 0,
                    "gap_opens": 0,
                    "query_start": 1,
                    "query_end": len(query),
                    "subject_start": subject_start,
                    "subject_end": subject_end,
                    "evalue": 0.0,
                    "bitscore": float(len(query) * 2),
                    "strand": strand,
                })
                start = ref.find(query, start + 1)

    return hits


# ---------------------------------------------------------------------------
# Hit Filtering
# ---------------------------------------------------------------------------

def _filter_significant_hits(
    hits: List[Dict[str, Any]], query_length: int
) -> List[Dict[str, Any]]:
    """
    Filter BLAST hits by identity (≥85%) and coverage (≥80% of query).
    """
    if not hits or query_length == 0:
        return []

    significant = []
    for hit in hits:
        identity = hit.get("percent_identity", 0)
        alignment_len = hit.get("alignment_length", 0)
        coverage = (alignment_len / query_length) * 100.0

        if identity >= IDENTITY_THRESHOLD and coverage >= COVERAGE_THRESHOLD:
            hit["query_coverage"] = round(coverage, 1)
            significant.append(hit)

    return significant


def _detect_off_target_amplicon(
    fwd_hits: List[Dict[str, Any]], rev_hits: List[Dict[str, Any]]
) -> bool:
    """
    Detect off-target amplicon: both primers have significant hits on the same
    chromosome/contig within MAX_AMPLICON_DISTANCE bp of each other.
    """
    if not fwd_hits or not rev_hits:
        return False
    if len(fwd_hits) == 1 and len(rev_hits) == 1:
        return False

    # Build a map of subject_id → positions for forward hits
    fwd_loci: Dict[str, List[int]] = {}
    for hit in fwd_hits:
        sid = hit["subject_id"]
        pos = min(hit["subject_start"], hit["subject_end"])
        if sid not in fwd_loci:
            fwd_loci[sid] = []
        fwd_loci[sid].append(pos)

    # Check if any reverse hit is on the same subject within distance
    for hit in rev_hits:
        sid = hit["subject_id"]
        rev_pos = min(hit["subject_start"], hit["subject_end"])
        if sid in fwd_loci:
            for fwd_pos in fwd_loci[sid]:
                distance = abs(rev_pos - fwd_pos)
                if distance <= MAX_AMPLICON_DISTANCE:
                    return True

    return False


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _check_blast_installed() -> bool:
    """Check if blastn is available in PATH."""
    try:
        result = subprocess.run(
            ["blastn", "-version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _check_db_exists(db_path: str) -> bool:
    """Check if a BLAST database exists (look for .nsq, .nhr, .nin files)."""
    for ext in [".nsq", ".nhr", ".nin", ".nal"]:
        if os.path.exists(db_path + ext):
            return True
    # Also check if path is a directory with db files
    if os.path.isdir(db_path):
        return True
    return False


def _resolve_db_path(organism: str) -> str:
    """Resolve BLAST database path based on organism."""
    db_base = os.environ.get("BLAST_DB_BASE", "/opt/blast_db")
    organism_map = {
        "human": "human_genome",
        "mouse": "mouse_genome",
        "rat": "rat_genome",
        "zebrafish": "zebrafish_genome",
        "fly": "drosophila_genome",
        "worm": "celegans_genome",
        "yeast": "scerevisiae_genome",
        "ecoli": "ecoli_genome",
        "arabidopsis": "athaliana_genome",
        "pig": "sus_scrofa_genome",
        "dog": "canis_familiaris_genome",
        "chicken": "ggallus_genome",
        "cow": "btaurus_genome",
        "xenopus": "xtropicalis_genome",
    }
    db_name = organism_map.get(organism.lower(), f"{organism.lower()}_genome")
    return os.path.join(db_base, db_name)


def _get_reference_sequences(input_data: Dict[str, Any]) -> Dict[str, str]:
    """Normalize optional in-memory/local references for internal checks."""
    raw_refs = (
        input_data.get("reference_sequences")
        or input_data.get("specificity_references")
        or input_data.get("local_reference_sequences")
    )
    refs: Dict[str, str] = {}

    if isinstance(raw_refs, dict):
        refs = {str(k): str(v) for k, v in raw_refs.items() if v}
    elif isinstance(raw_refs, list):
        for i, item in enumerate(raw_refs):
            if isinstance(item, dict):
                name = str(item.get("id") or item.get("name") or f"ref_{i+1}")
                seq = item.get("sequence", "")
                if seq:
                    refs[name] = str(seq)
            elif item:
                refs[f"ref_{i+1}"] = str(item)

    target = input_data.get("target_sequence") or input_data.get("consensus_sequence")
    if target and "target_sequence" not in refs:
        refs["target_sequence"] = str(target)

    return refs


def _reverse_complement(sequence: str) -> str:
    table = str.maketrans("ACGTNacgtn", "TGCANtgcan")
    return sequence.translate(table)[::-1]

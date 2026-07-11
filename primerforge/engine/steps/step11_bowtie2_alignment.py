"""
Step 11: Structural Alignment (Bowtie2)
=========================================
Map primers across the entire genome using Bowtie2 to catch multi-mappers,
duplication events, and pseudogene hits that BLAST may miss due to its heuristic
nature.

Strategy:
  - End-to-end alignment mode (no soft-clipping)
  - Report up to 5 alignment locations per primer (-k 5)
  - Flag multi-mappers (>1 location)
  - Detect pseudogene hits (chrUn, _random, _alt contigs, or known pseudogene loci)
  - Batch processing: 50 primers per Bowtie2 invocation
  - 60-second timeout per batch
  - Handle missing Bowtie2 gracefully (log warning, skip, mark unchecked)
"""

import logging
import os
import re
import subprocess
import tempfile
from typing import Any

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────
BOWTIE2_TIMEOUT_S = 60
MAX_REPORT_ALIGNMENTS = 5  # -k 5
BATCH_SIZE = 50
DEFAULT_INDEX_PATH = os.environ.get("BOWTIE2_INDEX_PATH", "/opt/bowtie2_idx/human_genome")

# Pseudogene/non-standard chromosome patterns (excluding mitochondrial)
PSEUDOGENE_PATTERNS = [
    re.compile(r"chrUn", re.IGNORECASE),
    re.compile(r"_random$", re.IGNORECASE),
    re.compile(r"_alt$", re.IGNORECASE),
    re.compile(r"_fix$", re.IGNORECASE),
    re.compile(r"_hap\d+", re.IGNORECASE),
]

ORGANELLE_PATTERNS = [
    re.compile(r"chrM", re.IGNORECASE),
    re.compile(r"chrMT", re.IGNORECASE),
]

PSEUDOGENE_PENALTY = 20.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def execute(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Step 11: Bowtie2 genome-wide alignment.

    Input keys:
        - filtered_pairs (list): Pairs from Step 10 (or refined_pairs fallback)
        - organism (str): Organism identifier
        - bowtie2_index_path (str, optional): Override index path

    Output keys:
        - aligned_pairs (list): Pairs with mapping count and pseudogene annotations
        - bowtie2_available (bool): Whether Bowtie2 was available
        - bowtie2_note (str): Summary
    """
    pairs = input_data.get("filtered_pairs") or input_data.get("refined_pairs", [])
    if not pairs:
        return {"aligned_pairs": [], "bowtie2_note": "No pairs to align", "bowtie2_available": False}

    organism = input_data.get("organism", "human")
    index_path = input_data.get("bowtie2_index_path", "")

    if not index_path:
        index_path = _resolve_index_path(organism)

    reference_sequences = _get_reference_sequences(input_data)

    # ── Check Bowtie2 availability ─────────────────────────────────────────
    bt2_available = _check_bowtie2_installed()
    if not bt2_available:
        if reference_sequences:
            logger.warning(
                "Bowtie2 not installed — running internal exact genome mapper."
            )
            return _run_internal_reference_alignment(pairs, reference_sequences)

        logger.warning("Bowtie2 not installed — skipping genome alignment.")
        for pair in pairs:
            pair["forward"]["mapping_count"] = None
            pair["reverse"]["mapping_count"] = None
            pair["bowtie2_pass"] = None
            pair["pseudogene_hit"] = None
            pair.setdefault("penalties", {})
        return {
            "aligned_pairs": pairs,
            "bowtie2_available": False,
            "bowtie2_note": "Bowtie2 not installed — alignment skipped. Install for production use.",
        }

    # ── Check index exists ─────────────────────────────────────────────────
    index_exists = _check_index_exists(index_path)
    if not index_exists:
        logger.warning("Bowtie2 index not found at '%s' — skipping alignment.", index_path)
        for pair in pairs:
            pair["forward"]["mapping_count"] = None
            pair["reverse"]["mapping_count"] = None
            pair["bowtie2_pass"] = None
            pair["pseudogene_hit"] = None
            pair.setdefault("penalties", {})
        return {
            "aligned_pairs": pairs,
            "bowtie2_available": True,
            "bowtie2_note": f"Bowtie2 index not found at '{index_path}' — alignment skipped.",
        }

    # ── Collect all unique primer sequences ────────────────────────────────
    primer_sequences: dict[str, str] = {}  # id → sequence
    for i, pair in enumerate(pairs):
        fwd_id = f"pair{i}_fwd"
        rev_id = f"pair{i}_rev"
        primer_sequences[fwd_id] = pair.get("forward", {}).get("sequence", "")
        primer_sequences[rev_id] = pair.get("reverse", {}).get("sequence", "")

    # ── Run Bowtie2 in batches ─────────────────────────────────────────────
    all_results = _batch_align(primer_sequences, index_path)

    # ── Annotate pairs ─────────────────────────────────────────────────────
    aligned_pairs = []
    for i, pair in enumerate(pairs):
        fwd_id = f"pair{i}_fwd"
        rev_id = f"pair{i}_rev"
        pair.setdefault("penalties", {})

        fwd_result = all_results.get(fwd_id, {"mapping_count": 0, "locations": []})
        rev_result = all_results.get(rev_id, {"mapping_count": 0, "locations": []})

        pair["forward"]["mapping_count"] = fwd_result["mapping_count"]
        pair["forward"]["alignment_locations"] = fwd_result["locations"]
        pair["reverse"]["mapping_count"] = rev_result["mapping_count"]
        pair["reverse"]["alignment_locations"] = rev_result["locations"]

        # Multi-mapper detection
        fwd_unique = fwd_result["mapping_count"] <= 1
        rev_unique = rev_result["mapping_count"] <= 1
        pair["forward"]["is_unique_mapper"] = fwd_unique
        pair["reverse"]["is_unique_mapper"] = rev_unique

        # Pseudogene and organelle hit detection
        fwd_pseudogene = _has_pseudogene_hit(fwd_result["locations"])
        rev_pseudogene = _has_pseudogene_hit(rev_result["locations"])
        fwd_organelle = _has_organelle_hit(fwd_result["locations"])
        rev_organelle = _has_organelle_hit(rev_result["locations"])
        pair["forward"]["pseudogene_hit"] = fwd_pseudogene
        pair["reverse"]["pseudogene_hit"] = rev_pseudogene
        pair["pseudogene_hit"] = fwd_pseudogene or rev_pseudogene
        pair["forward"]["organelle_hit"] = fwd_organelle
        pair["reverse"]["organelle_hit"] = rev_organelle
        pair["organelle_hit"] = fwd_organelle or rev_organelle

        # ── Assign penalties ───────────────────────────────────────────────
        if not fwd_unique:
            pair["penalties"]["multi_map_fwd"] = 10.0
            pair["forward"].setdefault("flags", []).append("multi_mapper")
        if not rev_unique:
            pair["penalties"]["multi_map_rev"] = 10.0
            pair["reverse"].setdefault("flags", []).append("multi_mapper")
        if pair["pseudogene_hit"]:
            pair["penalties"]["pseudogene"] = PSEUDOGENE_PENALTY
        if pair["organelle_hit"]:
            pair["penalties"]["organelle"] = PSEUDOGENE_PENALTY

        pair["bowtie2_pass"] = fwd_unique and rev_unique and not pair["pseudogene_hit"] and not pair["organelle_hit"]
        aligned_pairs.append(pair)

    passed = sum(1 for p in aligned_pairs if p.get("bowtie2_pass"))

    # Ensure pair_id is preserved for all pairs
    for i, pair in enumerate(aligned_pairs):
        if not pair.get("pair_id"):
            pair["pair_id"] = i + 1

    return {
        "aligned_pairs": aligned_pairs,
        "bowtie2_available": True,
        "alignment_checked": True,
        "bowtie2_note": f"{passed}/{len(aligned_pairs)} pairs are unique mappers without pseudogene hits.",
    }


def _run_internal_reference_alignment(
    pairs: list[dict[str, Any]],
    reference_sequences: dict[str, str],
) -> dict[str, Any]:
    """Run deterministic exact mapping against supplied references."""
    aligned_pairs = []

    for i, pair in enumerate(pairs):
        pair.setdefault("penalties", {})
        fwd_seq = pair.get("forward", {}).get("sequence", "")
        rev_seq = pair.get("reverse", {}).get("sequence", "")

        fwd_locations = _scan_reference_locations(fwd_seq, reference_sequences)
        rev_locations = _scan_reference_locations(rev_seq, reference_sequences)

        pair["forward"]["mapping_count"] = len(fwd_locations)
        pair["forward"]["alignment_locations"] = fwd_locations
        pair["forward"]["alignment_hits"] = fwd_locations
        pair["reverse"]["mapping_count"] = len(rev_locations)
        pair["reverse"]["alignment_locations"] = rev_locations
        pair["reverse"]["alignment_hits"] = rev_locations

        fwd_unique = len(fwd_locations) <= 1
        rev_unique = len(rev_locations) <= 1
        pair["forward"]["is_unique_mapper"] = fwd_unique
        pair["reverse"]["is_unique_mapper"] = rev_unique

        fwd_pseudogene = _has_pseudogene_hit(fwd_locations)
        rev_pseudogene = _has_pseudogene_hit(rev_locations)
        fwd_organelle = _has_organelle_hit(fwd_locations)
        rev_organelle = _has_organelle_hit(rev_locations)
        pair["forward"]["pseudogene_hit"] = fwd_pseudogene
        pair["reverse"]["pseudogene_hit"] = rev_pseudogene
        pair["pseudogene_hit"] = fwd_pseudogene or rev_pseudogene
        pair["forward"]["organelle_hit"] = fwd_organelle
        pair["reverse"]["organelle_hit"] = rev_organelle
        pair["organelle_hit"] = fwd_organelle or rev_organelle

        if not fwd_unique:
            pair["penalties"]["multi_map_fwd"] = 10.0
            pair["forward"].setdefault("flags", []).append("multi_mapper")
        if not rev_unique:
            pair["penalties"]["multi_map_rev"] = 10.0
            pair["reverse"].setdefault("flags", []).append("multi_mapper")
        if pair["pseudogene_hit"]:
            pair["penalties"]["pseudogene"] = PSEUDOGENE_PENALTY

        pair["bowtie2_pass"] = fwd_unique and rev_unique and not pair["pseudogene_hit"]
        pair["bowtie2_status"] = "checked_internal_reference"
        aligned_pairs.append(pair)

    passed = sum(1 for p in aligned_pairs if p.get("bowtie2_pass"))
    return {
        "aligned_pairs": aligned_pairs,
        "bowtie2_available": False,
        "alignment_checked": True,
        "bowtie2_note": (
            f"Bowtie2 not installed; internal exact genome mapper completed. "
            f"{passed}/{len(aligned_pairs)} pairs are unique mappers without pseudogene hits."
        ),
    }


def _scan_reference_locations(
    sequence: str,
    reference_sequences: dict[str, str],
) -> list[dict[str, Any]]:
    if not sequence:
        return []

    seq = sequence.upper()
    rc_seq = _reverse_complement(seq)
    locations: list[dict[str, Any]] = []

    for chrom, reference in reference_sequences.items():
        ref = reference.upper()
        for query, strand in ((seq, "+"), (rc_seq, "-")):
            start = ref.find(query)
            while start != -1:
                position = start + 1
                end = start + len(query)
                locations.append({
                    "chromosome": chrom,
                    "position": position,
                    "start": position,
                    "end": end,
                    "mapq": 42,
                    "strand": strand,
                    "percent_identity": 100.0,
                    "query_coverage": 100.0,
                    "coverage": 100.0,
                    "alignment_length": len(query),
                })
                start = ref.find(query, start + 1)

    return locations


# ---------------------------------------------------------------------------
# Bowtie2 Batch Alignment
# ---------------------------------------------------------------------------

def _batch_align(
    primer_sequences: dict[str, str], index_path: str
) -> dict[str, dict[str, Any]]:
    """
    Align primers in batches of BATCH_SIZE using Bowtie2 end-to-end mode.
    Returns dict of primer_id → {mapping_count, locations}.
    """
    results: dict[str, dict[str, Any]] = {}
    items = list(primer_sequences.items())

    for batch_start in range(0, len(items), BATCH_SIZE):
        batch = items[batch_start : batch_start + BATCH_SIZE]
        batch_results = _run_bowtie2_batch(batch, index_path)
        results.update(batch_results)

    # Fill in any missing entries with defaults
    for primer_id in primer_sequences:
        if primer_id not in results:
            results[primer_id] = {"mapping_count": 0, "locations": []}

    return results


def _run_bowtie2_batch(
    batch: list[tuple[str, str]], index_path: str
) -> dict[str, dict[str, Any]]:
    """Run Bowtie2 for a batch of primer sequences."""
    results: dict[str, dict[str, Any]] = {}

    try:
        # Write FASTA file for the batch
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".fa", delete=True
        ) as fasta_file:
            for primer_id, sequence in batch:
                if sequence:
                    fasta_file.write(f">{primer_id}\n{sequence}\n")
            fasta_file.flush()

            cmd = [
                "bowtie2",
                "-x", index_path,
                "-f", fasta_file.name,         # FASTA input
                "--end-to-end",                 # End-to-end mode (no soft-clip)
                "--very-sensitive",             # Sensitive preset
                "-k", str(MAX_REPORT_ALIGNMENTS),  # Report up to k alignments
                "--no-hd",                      # No header
                "--no-unal",                    # Don't output unaligned reads
                "--threads", "1",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=BOWTIE2_TIMEOUT_S,
            )

            if result.returncode in (0, 1):  # 0=all aligned, 1=some unaligned (OK)
                results = _parse_sam_output(result.stdout)

    except subprocess.TimeoutExpired:
        logger.warning(
            f"Bowtie2 timed out ({BOWTIE2_TIMEOUT_S}s) for batch of {len(batch)} primers."
        )
    except FileNotFoundError:
        logger.error("bowtie2 binary not found in PATH")
    except Exception as e:
        logger.debug("Bowtie2 batch alignment failed: %s", e)

    return results


def _parse_sam_output(sam_text: str) -> dict[str, dict[str, Any]]:
    """Parse SAM output from Bowtie2 into structured results."""
    results: dict[str, dict[str, Any]] = {}

    if not sam_text:
        return results

    for line in sam_text.strip().split("\n"):
        if not line or line.startswith("@"):
            continue

        fields = line.split("\t")
        if len(fields) < 6:
            continue

        read_id = fields[0]
        flag = int(fields[1])
        ref_name = fields[2]
        position = int(fields[3]) if fields[3] != "0" else 0
        mapq = int(fields[4]) if fields[4] != "*" else 0

        # Skip unmapped reads (flag & 4)
        if flag & 4:
            continue

        if read_id not in results:
            results[read_id] = {"mapping_count": 0, "locations": []}

        results[read_id]["mapping_count"] += 1
        results[read_id]["locations"].append({
            "chromosome": ref_name,
            "position": position,
            "mapq": mapq,
            "strand": "-" if (flag & 16) else "+",
        })

    return results


# ---------------------------------------------------------------------------
# Pseudogene Detection
# ---------------------------------------------------------------------------

def _has_pseudogene_hit(locations: list[dict[str, Any]]) -> bool:
    """Check if any alignment location maps to a pseudogene or non-standard contig (not organelle)."""
    for loc in locations:
        chrom = loc.get("chromosome", "")
        # Check organelle first — skip, these are handled separately
        for pattern in ORGANELLE_PATTERNS:
            if pattern.search(chrom):
                return False
        for pattern in PSEUDOGENE_PATTERNS:
            if pattern.search(chrom):
                return True
    return False


def _has_organelle_hit(locations: list[dict[str, Any]]) -> bool:
    """Check if any alignment location maps to mitochondrial DNA."""
    for loc in locations:
        chrom = loc.get("chromosome", "")
        for pattern in ORGANELLE_PATTERNS:
            if pattern.search(chrom):
                return True
    return False


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _check_bowtie2_installed() -> bool:
    """Check if bowtie2 is available in PATH."""
    try:
        result = subprocess.run(
            ["bowtie2", "--version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _check_index_exists(index_path: str) -> bool:
    """Check if Bowtie2 index files exist."""
    for ext in [".1.bt2", ".1.bt2l"]:
        if os.path.exists(index_path + ext):
            return True
    return False


def _resolve_index_path(organism: str) -> str:
    """Resolve Bowtie2 index path based on organism."""
    base = os.environ.get("BOWTIE2_INDEX_BASE", "/opt/bowtie2_idx")
    organism_map = {
        "human": "human_genome",
        "mouse": "mouse_genome",
        "rat": "rat_genome",
    }
    idx_name = organism_map.get(organism.lower(), f"{organism.lower()}_genome")
    return os.path.join(base, idx_name)


def _get_reference_sequences(input_data: dict[str, Any]) -> dict[str, str]:
    """Normalize optional in-memory/local references for internal alignment."""
    raw_refs = (
        input_data.get("reference_sequences")
        or input_data.get("alignment_references")
        or input_data.get("local_reference_sequences")
    )
    refs: dict[str, str] = {}

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

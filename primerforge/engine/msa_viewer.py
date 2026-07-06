#!/usr/bin/env python3
"""
VigyanLLP MSA Viewer
=====================
Formats multiple sequence alignments for interactive viewing.
Supports color-coded display, conservation bars, and export.
"""

import os
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

MSA_COLORS = {
    "match": "#4CAF50",       # Green — identical to consensus
    "mismatch": "#F44336",    # Red — different from consensus
    "gap": "#FFEB3B",         # Yellow — gap
    "ambiguous": "#9E9E9E",  # Gray — N/X/any ambiguous
    "consensus": "#2196F3",   # Blue — consensus character
}

AMBIGUOUS_BASES = set("NX")


def build_msa_view(
    sequences: List[Dict],
    reference_id: Optional[str] = None,
) -> Dict:
    """
    Build a color-coded MSA view from a list of sequences.
    sequences: [{"id": str, "name": str, "sequence": str, ...}]
    reference_id: optional ID to use as reference (first sequence if not set)
    Returns: {alignment: [...], conservation: [...], stats: {...}}
    """
    if not sequences:
        return {"alignment": [], "conservation": [], "stats": {}}

    seq_ids = []
    seq_names = []
    seq_seqs = []
    for s in sequences:
        seq_ids.append(s.get("id", ""))
        seq_names.append(s.get("name", "") or s.get("accession", "") or s.get("id", ""))
        seq_seqs.append(s.get("sequence", "").upper())

    if not seq_seqs or all(len(s) == 0 for s in seq_seqs):
        return {"alignment": [], "conservation": [], "stats": {}}

    # Align sequences via MAFFT if available, otherwise pad to same length
    aligned = _align_sequences(seq_seqs)
    if not aligned:
        return {"alignment": [], "conservation": [], "stats": {}}

    # Build alignment rows with color coding
    alignment_rows = []
    for idx, seq in enumerate(aligned):
        pos_pairs = []
        for col_idx in range(len(seq)):
            char = seq[col_idx]
            css_class = _get_char_class(char)
            pos_pairs.append({
                "char": char,
                "css_class": css_class,
                "col": col_idx,
            })
        alignment_rows.append({
            "id": seq_ids[idx] if idx < len(seq_ids) else "",
            "name": seq_names[idx] if idx < len(seq_names) else f"seq_{idx}",
            "index": idx,
            "positions": pos_pairs,
            "sequence": seq,
            "length": len(seq),
        })

    # Build conservation row
    conservation = _build_conservation(aligned)

    # Compute stats
    stats = _compute_stats(aligned, seq_names)

    # Determine reference
    ref_idx = 0
    if reference_id:
        for idx, sid in enumerate(seq_ids):
            if sid == reference_id:
                ref_idx = idx
                break

    return {
        "alignment": alignment_rows,
        "conservation": conservation,
        "reference": {
            "id": seq_ids[ref_idx] if ref_idx < len(seq_ids) else "",
            "name": seq_names[ref_idx] if ref_idx < len(seq_names) else "",
            "index": ref_idx,
        },
        "stats": stats,
        "total_sequences": len(sequences),
        "alignment_length": len(aligned[0]) if aligned else 0,
    }


def _align_sequences(sequences: List[str]) -> List[str]:
    """
    Align sequences using MAFFT if available, else Biopython pairwise.
    """
    # Try MAFFT first
    env_aligned = _align_with_mafft(sequences)
    if env_aligned:
        return env_aligned

    # Fall back to simple pairwise alignment
    return _align_simple(sequences)


def _align_with_mafft(sequences: List[str]) -> Optional[List[str]]:
    """Run MAFFT alignment if installed."""
    import subprocess
    import tempfile

    try:
        # Check if MAFFT is available
        subprocess.run(["mafft", "--version"], capture_output=True, timeout=10)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".fa", delete=False) as f:
            for i, seq in enumerate(sequences):
                f.write(f">seq_{i}\n{seq}\n")
            f.flush()
            temp_path = f.name

        result = subprocess.run(
            ["mafft", "--auto", "--anysymbol", temp_path],
            capture_output=True, text=True, timeout=120,
        )
        os.unlink(temp_path)

        if result.returncode != 0:
            return None

        aligned = []
        current = ""
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith(">"):
                if current:
                    aligned.append(current.upper())
                current = ""
            elif line:
                current += line
        if current:
            aligned.append(current.upper())

        return aligned if len(aligned) == len(sequences) else None
    except Exception as e:
        logger.debug(f"MAFFT alignment failed: {e}")
        return None


def _align_simple(sequences: List[str]) -> List[str]:
    """Simple padding alignment when no external tool is available."""
    if not sequences:
        return []
    max_len = max(len(s) for s in sequences)
    aligned = []
    for seq in sequences:
        aligned.append(seq.upper().ljust(max_len, "-"))
    return aligned


def _get_char_class(char: str) -> str:
    """Determine CSS class for a character in MSA."""
    if char == "-":
        return "msa-gap"
    if char in AMBIGUOUS_BASES:
        return "msa-ambiguous"
    return "msa-char"  # Will be colored by comparison to reference


def _build_conservation(aligned: List[str]) -> List[Dict]:
    """Build conservation row showing per-column conservation."""
    if not aligned or not aligned[0]:
        return []

    conservation = []
    for col in range(len(aligned[0])):
        col_chars = [seq[col] for seq in aligned]
        non_gap = [c for c in col_chars if c != "-"]
        if not non_gap:
            conservation.append({"char": "-", "pct": 0.0, "count": 0, "total": len(aligned)})
            continue

        from collections import Counter
        counts = Counter(non_gap)
        most_common_char, most_common_count = counts.most_common(1)[0]
        pct = round(most_common_count / len(aligned) * 100, 1)

        conservation.append({
            "char": most_common_char,
            "pct": pct,
            "count": most_common_count,
            "total": len(aligned),
            "consensus": most_common_count >= len(aligned) * 0.5,
        })

    return conservation


def _compute_stats(aligned: List[str], names: List[str]) -> Dict:
    """Compute alignment statistics."""
    if not aligned or not aligned[0]:
        return {}

    n_seqs = len(aligned)
    alen = len(aligned[0])

    # Count gaps per sequence
    gap_counts = [seq.count("-") for seq in aligned]

    # Count conserved columns (all same non-gap char)
    conserved = 0
    for col in range(alen):
        chars = set(seq[col] for seq in aligned)
        non_gap = {c for c in chars if c != "-"}
        if len(non_gap) == 1:
            conserved += 1

    # Count gap-only columns
    gap_only = sum(1 for col in range(alen) if all(seq[col] == "-" for seq in aligned))

    return {
        "n_sequences": n_seqs,
        "alignment_length": alen,
        "conserved_columns": conserved,
        "conserved_pct": round(conserved / alen * 100, 2) if alen > 0 else 0,
        "gap_only_columns": gap_only,
        "mean_gaps_per_seq": round(sum(gap_counts) / n_seqs, 1) if n_seqs > 0 else 0,
        "identities": round(conserved / alen * 100, 1) if alen > 0 else 0,
    }


def format_fasta(sequences: List[Dict]) -> str:
    """Export sequences in FASTA format."""
    lines = []
    for s in sequences:
        sid = s.get("id") or s.get("accession") or s.get("name") or "seq"
        seq = s.get("sequence") or s.get("seq") or ""
        lines.append(f">{sid}")
        lines.append(seq)
    return "\n".join(lines)


def format_clustal(alignment_rows: List[Dict]) -> str:
    """Export alignment in CLUSTAL format."""
    if not alignment_rows:
        return ""
    lines = ["CLUSTAL W formatted alignment\n"]
    block_size = 60
    alen = alignment_rows[0]["length"] if alignment_rows else 0

    for start in range(0, alen, block_size):
        for row in alignment_rows:
            name = row["name"][:20].ljust(20)
            block_seq = row["sequence"][start:start + block_size]
            lines.append(f"{name} {block_seq}")
        lines.append("")
    return "\n".join(lines)


def get_msa_summary(msa_view: Dict) -> str:
    """Generate a text summary of the MSA for API response."""
    stats = msa_view.get("stats", {})
    if not stats:
        return "No alignment data available."
    return (
        f"Aligned {stats.get('n_sequences', 0)} sequences, "
        f"length {stats.get('alignment_length', 0)} columns, "
        f"{stats.get('conserved_pct', 0)}% conserved, "
        f"{stats.get('identities', 0)}% identity"
    )

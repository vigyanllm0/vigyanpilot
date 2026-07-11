#!/usr/bin/env python3
"""
VigyanLLM MSA Viewer — Large-scale MSA (100–100,000 sequences)
===============================================================
Supports paginated views, job-based async processing, FASTA/Clustal export.

Job state is persisted in Redis (instead of local memory) so it survives
Gunicorn worker restarts and can be shared across workers.
"""

import json
import logging
import os
import subprocess
import tempfile
import time
import uuid
from collections import Counter

logger = logging.getLogger(__name__)

MSA_COLORS = {
    "match": "#4CAF50",
    "mismatch": "#F44336",
    "gap": "#FFEB3B",
    "ambiguous": "#9E9E9E",
    "consensus": "#2196F3",
}
AMBIGUOUS_BASES = set("NX")

# ── Redis backend ─────────────────────────────────────────────────────────

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
_DEFAULT_TTL = int(os.environ.get("MSA_JOB_TTL", "3600"))  # 1 hour

_redis = None


def _get_redis():
    global _redis
    if _redis is None:
        import redis as _redis_mod
        _redis = _redis_mod.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=5,
        )
        logger.info("MSA viewer connected to Redis at %s", REDIS_URL)
    return _redis


def _job_key(job_id: str) -> str:
    return f"msa:job:{job_id}"


def _save_job(job_id: str, data: dict, ttl: int = _DEFAULT_TTL):
    """Persist a job dict to Redis with a TTL."""
    r = _get_redis()
    r.setex(_job_key(job_id), ttl, json.dumps(data, default=str))


def _load_job(job_id: str) -> dict | None:
    """Load a job dict from Redis, or None if missing/expired."""
    r = _get_redis()
    raw = r.get(_job_key(job_id))
    if raw is None:
        return None
    return json.loads(raw)


def _delete_job(job_id: str):
    """Remove a job from Redis."""
    r = _get_redis()
    r.delete(_job_key(job_id))

# ── Job lifecycle ──────────────────────────────────────────────

def create_job(sequences: list[dict], reference_id: str | None = None) -> str:
    job_id = uuid.uuid4().hex[:12]
    job_data = {
        "status": "QUEUED",
        "progress": 0,
        "sequences": sequences,
        "reference_id": reference_id,
        "alignment": None,
        "conservation": None,
        "stats": None,
        "total": len(sequences),
        "created": time.time(),
        "error": None,
    }
    _save_job(job_id, job_data)
    logger.info("MSA job %s created (%d sequences, TTL=%ds)", job_id, len(sequences), _DEFAULT_TTL)
    return job_id


def get_job(job_id: str) -> dict | None:
    return _load_job(job_id)


def process_job(job_id: str):
    job = _load_job(job_id)
    if not job:
        return
    try:
        job["status"] = "PROCESSING"
        job["progress"] = 5
        _save_job(job_id, job)

        seqs = job["sequences"]
        ref_id = job["reference_id"]

        n = len(seqs)
        job["progress"] = 10
        _save_job(job_id, job)

        if n == 0:
            job["status"] = "DONE"
            job["alignment"] = []
            job["conservation"] = []
            job["stats"] = {}
            _save_job(job_id, job)
            return

        seq_ids = [s.get("id", "") for s in seqs]
        seq_names = [s.get("name", "") or s.get("accession", "") or s.get("id", "") for s in seqs]
        seq_seqs = [s.get("sequence", "").upper() for s in seqs]
        max_raw = max((len(s) for s in seq_seqs), default=0)

        job["progress"] = 15
        _save_job(job_id, job)

        # ── Choose alignment strategy based on size ──
        if n <= 500:
            aligned = _align_mafft(seq_seqs, auto=True)
        elif n <= 5000:
            aligned = _align_mafft(seq_seqs, auto=False, fast=True)
        elif n <= 50000:
            aligned = _align_kmer_profile(seq_seqs)
        else:
            aligned = _align_fast_padding(seq_seqs)

        job["progress"] = 40
        _save_job(job_id, job)

        if not aligned or len(aligned) != n:
            aligned = _align_fast_padding(seq_seqs)

        alen = len(aligned[0]) if aligned else 0
        job["progress"] = 50
        _save_job(job_id, job)

        # ── Build full alignment ──
        full_alignment = []
        for idx, seq in enumerate(aligned):
            full_alignment.append({
                "id": seq_ids[idx] if idx < len(seq_ids) else "",
                "name": seq_names[idx] if idx < len(seq_names) else f"seq_{idx}",
                "index": idx,
                "sequence": seq,
                "length": len(seq),
            })
        job["alignment"] = full_alignment
        job["progress"] = 60
        _save_job(job_id, job)

        # ── Conservation (sampled for very large sets) ──
        if n <= 5000:
            cons = _build_conservation(aligned)
        else:
            cons = _build_conservation_sampled(aligned, sample_size=min(n, 5000))
        job["conservation"] = cons
        job["progress"] = 80
        _save_job(job_id, job)

        # ── Stats ──
        stats = _compute_stats(aligned, seq_names, cons)
        job["stats"] = stats
        job["progress"] = 100
        job["status"] = "DONE"
        _save_job(job_id, job)
        logger.info("MSA job %s completed (%d sequences, %d columns)", job_id, n, alen)

    except Exception as e:
        logger.error("MSA job %s failed: %s", job_id, e, exc_info=True)
        job["status"] = "ERROR"
        job["error"] = str(e)[:300]
        _save_job(job_id, job)

# ── Alignment strategies ───────────────────────────────────────

def _align_mafft(sequences: list[str], auto: bool = True, fast: bool = False) -> list[str] | None:
    """Align with MAFFT binary; fall back to pure-Python progressive alignment."""
    try:
        subprocess.run(["mafft", "--version"], capture_output=True, timeout=10)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return _align_python(sequences)
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".fa", delete=False) as f:
            for i, seq in enumerate(sequences):
                f.write(f">seq_{i}\n{seq}\n")
            f.flush()
            tpath = f.name

        cmd = ["mafft", "--anysymbol"]
        if auto:
            cmd.append("--auto")
        if fast:
            cmd.extend(["--retree", "1", "--maxiterate", "0"])
        cmd.append(tpath)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        os.unlink(tpath)
        if result.returncode != 0:
            return _align_python(sequences)

        aligned, cur = [], ""
        for line in result.stdout.splitlines():
            s = line.strip()
            if s.startswith(">"):
                if cur:
                    aligned.append(cur.upper())
                cur = ""
            elif s:
                cur += s
        if cur:
            aligned.append(cur.upper())
        if len(aligned) == len(sequences):
            return aligned
        return _align_python(sequences)
    except Exception as e:
        logger.debug("MAFFT alignment failed: %s", e)
        return _align_python(sequences)


def _align_python(sequences: list[str]) -> list[str] | None:
    """Reference-based pairwise progressive alignment (pure Python).
    
    Picks the longest sequence as reference and aligns all others
    to it via Needleman-Wunsch (or Biopython PairwiseAligner if available).
    Falls back to fast-padding for sets >100 sequences.
    """
    n = len(sequences)
    if n == 0:
        return []
    if n == 1:
        return [sequences[0]]
    if n > 100:
        return _align_fast_padding(sequences)

    try:
        from Bio import Align
        _use_bio = True
    except ImportError:
        _use_bio = False

    # Pick reference = longest sequence
    ref_idx = max(range(n), key=lambda i: len(sequences[i]))
    ref_seq = sequences[ref_idx]

    # Align every sequence (including the reference) to the reference
    aligned = [None] * n
    for i in range(n):
        if i == ref_idx:
            aligned[i] = ref_seq
        else:
            ali = _pairwise_gaps(sequences[i], ref_seq, _use_bio)
            aligned[i] = ali

    # All sequences now have gaps inserted -> pad to same length
    max_len = max(len(s) for s in aligned)
    return [s.ljust(max_len, "-") for s in aligned]


def _pairwise_gaps(query: str, target: str, use_bio: bool) -> str:
    """Align query to target and insert gaps into query where target has insertions."""
    if use_bio:
        from Bio import Align
        aligner = Align.PairwiseAligner()
        aligner.mode = "global"
        aligner.match_score = 2
        aligner.mismatch_score = -1
        aligner.gap_score = -2
        aligner.extend_gap_score = -0.5
        ali = aligner.align(query, target)
        idx = ali[0].indices[0]
        return "".join(query[i] if i >= 0 else "-" for i in idx)

    m, n = len(query), len(target)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = -2 * i
    for j in range(n + 1):
        dp[0][j] = -2 * j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            match = dp[i - 1][j - 1] + (2 if query[i - 1] == target[j - 1] else -1)
            delete = dp[i - 1][j] - 2
            insert = dp[i][j - 1] - 2
            dp[i][j] = max(match, delete, insert)

    i, j = m, n
    res = []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + (2 if query[i - 1] == target[j - 1] else -1):
            res.append(query[i - 1])
            i -= 1
            j -= 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] - 2:
            res.append(query[i - 1])
            i -= 1
        else:
            res.append("-")
            j -= 1
    return "".join(reversed(res))

def _align_kmer_profile(sequences: list[str]) -> list[str]:
    """K-mer based profile alignment for medium-large sets."""
    if not sequences:
        return []
    from collections import defaultdict
    n = len(sequences)
    if n == 1:
        return [sequences[0]]

    max_len = max(len(s) for s in sequences)
    min_len = min(len(s) for s in sequences)

    if max_len <= 200:
        return _align_fast_padding(sequences)

    reference = _pick_reference(sequences)
    ref_kmers = set()
    for i in range(len(reference) - 3):
        ref_kmers.add(reference[i:i+4])

    profiles = []
    for seq in sequences:
        shared = sum(1 for i in range(len(seq) - 3) if seq[i:i+4] in ref_kmers)
        total = max(len(seq) - 3, 1)
        profiles.append(shared / total)
    median_prof = sorted(profiles)[n // 2]

    clusters = defaultdict(list)
    for idx, prof in enumerate(profiles):
        key = "core" if prof >= median_prof * 0.5 else "divergent"
        clusters[key].append(idx)

    aligned_results = []
    aligned_count = 0
    for cluster_key in ("core", "divergent"):
        indices = clusters[cluster_key]
        if not indices:
            continue
        cluster_seqs = [sequences[i] for i in indices]
        cluster_aligned = _align_mafft(cluster_seqs, auto=False, fast=True)
        if not cluster_aligned:
            cluster_aligned = _align_fast_padding(cluster_seqs)
        aligned_results.extend(cluster_aligned)
        aligned_count += len(cluster_aligned)

    if aligned_count != n:
        return _align_fast_padding(sequences)
    return _align_to_max_length(aligned_results)

def _align_fast_padding(sequences: list[str]) -> list[str]:
    if not sequences:
        return []
    max_len = max(len(s) for s in sequences)
    return [s.upper().ljust(max_len, "-") for s in sequences]

def _pick_reference(sequences: list[str]) -> str:
    median_len = sorted(len(s) for s in sequences)[len(sequences) // 2]
    candidates = [s for s in sequences if abs(len(s) - median_len) < median_len * 0.1]
    return candidates[0] if candidates else sequences[0]

def _align_to_max_length(sequences: list[str]) -> list[str]:
    max_len = max(len(s) for s in sequences)
    return [s.ljust(max_len, "-") for s in sequences]

# ── Conservation ───────────────────────────────────────────────

def _build_conservation(aligned: list[str]) -> list[dict]:
    if not aligned or not aligned[0]:
        return []
    n = len(aligned)
    cols = len(aligned[0])
    conservation = []
    for col in range(cols):
        non_gap = [seq[col] for seq in aligned if seq[col] != "-"]
        if not non_gap:
            conservation.append({"char": "-", "pct": 0.0, "count": 0, "total": n})
            continue
        counts = Counter(non_gap)
        mc_char, mc_count = counts.most_common(1)[0]
        pct = round(mc_count / n * 100, 1)
        conservation.append({
            "char": mc_char, "pct": pct, "count": mc_count, "total": n,
            "consensus": mc_count >= n * 0.5,
        })
    return conservation

def _build_conservation_sampled(aligned: list[str], sample_size: int = 5000) -> list[dict]:
    n = len(aligned)
    if not aligned or not aligned[0]:
        return []
    cols = len(aligned[0])
    step = max(1, n // sample_size)
    sampled_indices = list(range(0, n, step))[:sample_size]
    conservation = []
    for col in range(cols):
        non_gap = [aligned[i][col] for i in sampled_indices if aligned[i][col] != "-"]
        if not non_gap:
            conservation.append({"char": "-", "pct": 0.0, "count": 0, "total": n})
            continue
        counts = Counter(non_gap)
        mc_char, mc_count = counts.most_common(1)[0]
        pct = round(mc_count / len(sampled_indices) * 100, 1)
        conservation.append({
            "char": mc_char, "pct": pct, "count": mc_count, "total": n,
            "consensus": mc_count >= len(sampled_indices) * 0.5,
        })
    return conservation

# ── Stats ──────────────────────────────────────────────────────

def _compute_stats(aligned: list[str], names: list[str], conservation: list[dict] = None) -> dict:
    if not aligned or not aligned[0]:
        return {}
    n = len(aligned)
    alen = len(aligned[0])
    gap_counts = [seq.count("-") for seq in aligned]
    conserved = sum(1 for c in (conservation or []) if c.get("pct", 0) == 100.0)
    gap_only = sum(1 for col in range(alen) if all(seq[col] == "-" for seq in aligned))
    return {
        "n_sequences": n,
        "alignment_length": alen,
        "conserved_columns": conserved,
        "conserved_pct": round(conserved / alen * 100, 2) if alen > 0 else 0,
        "gap_only_columns": gap_only,
        "mean_gaps_per_seq": round(sum(gap_counts) / n, 1) if n > 0 else 0,
        "identities": round(conserved / alen * 100, 1) if alen > 0 else 0,
        "max_gaps": max(gap_counts) if gap_counts else 0,
        "min_gaps": min(gap_counts) if gap_counts else 0,
    }

# ── Paginated view ────────────────────────────────────────────

def get_paginated_alignment(job_id: str, offset: int = 0, limit: int = 50,
                            col_start: int = 0, col_end: int = 0) -> dict:
    job = _load_job(job_id)
    if not job:
        return {"error": "Job not found", "status": "NOT_FOUND"}
    if job["status"] != "DONE":
        return {"error": "Job not ready", "status": job["status"]}
    full = job.get("alignment", [])
    total = len(full)
    col_end = col_end or (full[0]["length"] if full else 0)
    page = full[offset:offset + limit]
    rows = []
    for row in page:
        seq = row["sequence"][col_start:col_end]
        positions = [_get_char_class(c) for c in seq]
        rows.append({
            "id": row["id"], "name": row["name"], "index": row["index"],
            "sequence": seq, "length": len(seq),
            "positions": [{"char": seq[i], "css_class": positions[i], "col": i} for i in range(len(seq))],
        })
    cons = job.get("conservation", [])
    cons_page = cons[col_start:col_end] if cons else []
    return {
        "alignment": rows,
        "conservation": cons_page,
        "stats": job.get("stats"),
        "total_sequences": total,
        "offset": offset, "limit": limit,
        "col_start": col_start, "col_end": col_end,
    }

def _get_char_class(char: str) -> str:
    if char == "-":
        return "msa-gap"
    if char in AMBIGUOUS_BASES:
        return "msa-ambiguous"
    return "msa-char"

# ── Legacy API (backward compat, small alignments) ────────────

def build_msa_view(sequences: list[dict], reference_id: str | None = None) -> dict:
    if not sequences:
        return {"alignment": [], "conservation": [], "stats": {}}
    seq_seqs = [s.get("sequence", "").upper() for s in sequences]
    if not seq_seqs or all(len(s) == 0 for s in seq_seqs):
        return {"alignment": [], "conservation": [], "stats": {}}
    aligned = _align_mafft(seq_seqs, auto=True)
    if not aligned:
        aligned = _align_fast_padding(seq_seqs)
    alignment_rows = []
    for idx, seq in enumerate(aligned):
        pos = [{"char": seq[c], "css_class": _get_char_class(seq[c]), "col": c} for c in range(len(seq))]
        alignment_rows.append({
            "id": sequences[idx].get("id", ""),
            "name": sequences[idx].get("name", "") or f"seq_{idx}",
            "index": idx, "positions": pos, "sequence": seq, "length": len(seq),
        })
    cons = _build_conservation(aligned)
    stats = _compute_stats(aligned, [s.get("name","") for s in sequences], cons)
    return {
        "alignment": alignment_rows, "conservation": cons, "reference": {"index": 0},
        "stats": stats, "total_sequences": len(sequences), "alignment_length": len(aligned[0]) if aligned else 0,
    }

# ── Export ─────────────────────────────────────────────────────

def format_fasta(sequences: list[dict]) -> str:
    lines = []
    for s in sequences:
        sid = s.get("id") or s.get("accession") or s.get("name") or "seq"
        seq = s.get("sequence") or s.get("seq") or ""
        lines.append(f">{sid}")
        lines.append(seq)
    return "\n".join(lines)

def format_clustal(alignment_rows: list[dict]) -> str:
    if not alignment_rows:
        return ""
    lines = ["CLUSTAL W formatted alignment\n"]
    block_size = 60
    alen = alignment_rows[0]["length"] if alignment_rows else 0
    for start in range(0, alen, block_size):
        for row in alignment_rows:
            name = row["name"][:20].ljust(20)
            lines.append(f"{name} {row['sequence'][start:start + block_size]}")
        lines.append("")
    return "\n".join(lines)

def format_clustal_from_job(job_id: str) -> str:
    job = _load_job(job_id)
    if not job or job["status"] != "DONE":
        return ""
    return format_clustal(job["alignment"])

def format_fasta_from_job(job_id: str) -> str:
    job = _load_job(job_id)
    if not job:
        return ""
    lines = []
    for row in (job.get("alignment") or []):
        lines.append(f">{row['name']}")
        lines.append(row["sequence"])
    return "\n".join(lines)

def get_msa_summary(msa_view: dict) -> str:
    stats = msa_view.get("stats", {})
    if not stats:
        return "No alignment data available."
    return (
        f"Aligned {stats.get('n_sequences', 0)} sequences, "
        f"length {stats.get('alignment_length', 0)} columns, "
        f"{stats.get('conserved_pct', 0)}% conserved, "
        f"{stats.get('identities', 0)}% identity"
    )

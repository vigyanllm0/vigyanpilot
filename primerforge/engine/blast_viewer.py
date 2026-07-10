#!/usr/bin/env python3
"""
VigyanLLM BLAST Viewer
======================
Structures BLAST results into a uniform table format.
No local BLAST binary needed — uses NCBI API or exact matching.
"""

import os, re, logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

BLAST_FIELDS = [
    "query_id", "subject_id", "identity_pct", "alignment_length",
    "mismatches", "gap_opens", "query_start", "query_end",
    "subject_start", "subject_end", "e_value", "bit_score",
    "query_cover", "subject_description", "subject_species",
    "source", "source_url", "subject_sequence",
]

BLAST_HEADERS = {
    "query_id": "Query",
    "subject_id": "Subject Accession",
    "identity_pct": "Identity %",
    "alignment_length": "Align Len",
    "mismatches": "Mismatches",
    "gap_opens": "Gaps",
    "e_value": "E-value",
    "bit_score": "Bit Score",
    "query_cover": "Query Cover %",
    "subject_description": "Description",
    "subject_species": "Species",
    "source": "Source",
    "source_url": "Source URL",
}


def run_remote_blast(
    query_sequence: str,
    database: str = "nt",
    organism: str = "",
    max_hits: int = 50,
) -> Dict:
    """
    Run BLAST via NCBI Remote API.
    database: nt, nr, refseq_rna, refseq_protein
    organism: optional organism filter (e.g., "Homo sapiens")
    Returns: {results: [...], total: N, params: {...}}
    """
    import requests

    query_sequence = query_sequence.strip().upper()
    # Determine program based on sequence content
    is_protein = len(re.findall(r"[^ACGTN]", query_sequence)) > len(query_sequence) * 0.2
    program = "blastp" if is_protein else "blastn"
    db = database if not is_protein else "nr"

    results = []
    error_detail = None
    try:
        # Step 1: Submit BLAST job
        submit_url = "https://blast.ncbi.nlm.nih.gov/Blast.cgi"
        ncbi_api_key = os.environ.get("NCBI_API_KEY", "")
        params = {
            "CMD": "Put",
            "PROGRAM": program,
            "DATABASE": db,
            "QUERY": f">{program}_query\n{query_sequence}",
            "FORMAT_TYPE": "JSON2",
            "HITLIST_SIZE": str(max_hits),
        }
        if ncbi_api_key:
            params["API_KEY"] = ncbi_api_key
        if organism:
            params["EQ_QUERY"] = f"{organism}[ORGN]"

        r = requests.post(submit_url, data=params, timeout=30)
        r.raise_for_status()

        # Extract RID from response
        rid = None
        for line in r.text.splitlines():
            m = re.search(r"RID\s*=\s*(\S+)", line)
            if m:
                rid = m.group(1)
                break

        if not rid:
            error_detail = "Could not get RID from NCBI"
            return {"results": [], "total": 0, "params": {"program": program, "database": db, "error": error_detail}}

        # Step 2: Poll for results
        import time
        rtoe = None
        for line in r.text.splitlines():
            m = re.search(r"RTOE\s*=\s*(\d+)", line)
            if m:
                rtoe = int(m.group(1))
                break

        wait_time = rtoe if rtoe else 15
        time.sleep(min(wait_time, 30))

        status_url = "https://blast.ncbi.nlm.nih.gov/Blast.cgi"
        for attempt in range(30):
            poll_params = {
                "CMD": "Get",
                "FORMAT_TYPE": "JSON2",
                "RID": rid,
            }
            if ncbi_api_key:
                poll_params["API_KEY"] = ncbi_api_key
            status_resp = requests.get(status_url, params=poll_params, timeout=30)
            status_resp.raise_for_status()
            data = status_resp.json()

            status = data.get("BlastOutput2", {}).get("report", {}).get("results", {}).get("search", {}).get("message", "")
            if "No hits" in status:
                return {"results": [], "total": 0, "params": {"program": program, "database": db}}
            if "There are no more hits" in status or data.get("BlastOutput2", {}).get("report", {}).get("results", {}).get("search", {}).get("hits"):
                break
            time.sleep(5)
        else:
            error_detail = "BLAST polling timed out"
            return {"results": [], "total": 0, "params": {"program": program, "database": db, "error": error_detail}}

        # Step 3: Parse JSON results
        report = data.get("BlastOutput2", {}).get("report", {})
        search = report.get("results", {}).get("search", {})
        hits = search.get("hits", [])

        for hit in hits[:max_hits]:
            hsps_list = hit.get("hsps", [{}])
            for hsp in hsps_list:
                identity_pct = round(float(hsp.get("identity", 0)) / max(float(hsp.get("align_len", 1)), 1) * 100, 2) if hsp.get("align_len") else 0.0
                query_cover = round(float(hsp.get("align_len", 0)) / max(len(query_sequence), 1) * 100, 2) if len(query_sequence) > 0 else 0.0

                result = {
                    "query_id": f">{program}_query",
                    "subject_id": hit.get("id", ""),
                    "subject_description": hit.get("description", [{}])[0].get("title", "") if hit.get("description") else "",
                    "subject_species": _extract_species(hit.get("description", [{}])[0].get("title", "") if hit.get("description") else ""),
                    "identity_pct": identity_pct,
                    "alignment_length": hsp.get("align_len", 0),
                    "mismatches": hsp.get("mismatch", 0),
                    "gap_opens": hsp.get("gaps", 0),
                    "query_start": hsp.get("query_from", 0),
                    "query_end": hsp.get("query_to", 0),
                    "subject_start": hsp.get("hit_from", 0),
                    "subject_end": hsp.get("hit_to", 0),
                    "e_value": _format_evalue(hsp.get("evalue", 0)),
                    "bit_score": round(hsp.get("bit_score", 0), 1),
                    "query_cover": query_cover,
                    "source": "NCBI BLAST",
                    "source_url": f"https://blast.ncbi.nlm.nih.gov/Blast.cgi?CMD=Get&RID={rid}",
                    "subject_sequence": hsp.get("midline", ""),
                }
                results.append(result)

    except Exception as e:
        error_detail = str(e)[:200]
        logger.warning("Remote BLAST failed: %s", error_detail)

    return {
        "results": results,
        "total": len(results),
        "params": {"program": program, "database": db, "organism": organism, "error": error_detail},
    }


def run_local_blast(
    query_sequence: str,
    subject_sequences: List[Dict],
) -> Dict:
    """
    Simple exact/ungapped alignment against provided sequences.
    No local BLAST binary required.
    """
    results = []
    query = query_sequence.strip().upper()

    for subj in subject_sequences:
        seq = subj.get("sequence", "").upper()
        if not seq:
            continue
        # Sliding window exact match
        best_pct = 0
        best_len = 0
        best_start = 0
        best_end = 0
        for i in range(len(seq) - len(query) + 1):
            match = sum(1 for a, b in zip(query, seq[i:i+len(query)]) if a == b)
            pct = match / len(query) * 100
            if pct > best_pct:
                best_pct = pct
                best_len = len(query)
                best_start = i
                best_end = i + len(query)

        if best_pct > 0:
            mismatches = best_len - int(best_len * best_pct / 100)
            results.append({
                "query_id": "query",
                "subject_id": subj.get("accession", ""),
                "subject_description": subj.get("description", ""),
                "subject_species": subj.get("organism", ""),
                "identity_pct": round(best_pct, 2),
                "alignment_length": best_len,
                "mismatches": mismatches,
                "gap_opens": 0,
                "query_start": 0,
                "query_end": best_len,
                "subject_start": best_start,
                "subject_end": best_end,
                "e_value": _estimate_evalue(best_pct, best_len, len(seq)),
                "bit_score": round(best_pct * best_len / 100, 1),
                "query_cover": round(best_len / len(query) * 100, 2),
                "source": subj.get("source", "local"),
                "source_url": subj.get("source_url", ""),
                "subject_sequence": seq[best_start:best_end],
            })

    results.sort(key=lambda x: x["identity_pct"], reverse=True)
    return {
        "results": results,
        "total": len(results),
        "params": {"mode": "local_exact"},
    }


def _fallback_exact_match(query: str, organism: str = "") -> List[Dict]:
    """Fallback when BLAST remote fails — returns empty list."""
    return []


def _extract_species(description: str) -> str:
    """Extract species name from NCBI hit description."""
    m = re.search(r"\[(\w+\s+\w+)\]", description)
    return m.group(1) if m else ""


def _format_evalue(e: float) -> str:
    """Format E-value in human-readable form."""
    if e == 0:
        return "0.0"
    if e < 0.0001:
        return f"{e:.2e}"
    return f"{e:.4f}"


def _estimate_evalue(pct: float, align_len: int, db_len: int) -> str:
    """Rough E-value estimate for exact matching."""
    if pct < 50:
        return ">1.0"
    raw = 1.0 * db_len / max(align_len, 1) * (1 - pct / 100)
    return _format_evalue(raw)


def format_results_table(results: List[Dict]) -> List[List]:
    """Convert BLAST results to table rows for frontend."""
    rows = []
    for r in results:
        rows.append([
            r.get("subject_id", ""),
            r.get("subject_species", ""),
            r.get("identity_pct", 0),
            r.get("alignment_length", 0),
            r.get("e_value", ""),
            r.get("bit_score", 0),
            r.get("query_cover", 0),
            r.get("subject_description", ""),
            r.get("source", ""),
            r.get("source_url", ""),
        ])
    return rows

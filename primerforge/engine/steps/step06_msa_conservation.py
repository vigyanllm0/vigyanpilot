"""
Step 6: Backend Multiple Sequence Alignment (MSA)
===================================================
Fetch variant/strain sequences for the target organism, run MSA to
compute per-base conservation scores, and identify conserved regions.

Strategy:
  - Fetch additional sequences from NCBI for the target gene/organism
  - Run MUSCLE (preferred) or MAFFT for MSA, with BioPython fallback
  - Compute per-base conservation (% agreement) across the alignment
  - Identify contiguous regions with >95% conservation
  - Pass conserved region mask + full alignment to Step 7

Output keys:
  - msa_alignment (list): Aligned sequences as strings
  - conservation_scores (list): Per-base conservation percentages
  - conserved_regions (list): [start, end] 0-indexed intervals at >95%
  - msa_note (str): Summary
  - strain_count (int): Number of strains aligned
  - msa_status (str): "complete" | "fallback_no_strains" | "fallback_error"
"""

import logging
import os
import subprocess
import tempfile
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

MSA_TIMEOUT_S = 120
CONSERVATION_THRESHOLD = 0.95
MIN_STRAIN_SEQUENCES = 3
MAX_STRAIN_SEQUENCES = 50
TARGET_ORGANISM_NCBI_MAP = {
    # ── Model organisms / vertebrates ──
    "human": "Homo sapiens",
    "mouse": "Mus musculus",
    "rat": "Rattus norvegicus",
    "zebrafish": "Danio rerio",
    "fly": "Drosophila melanogaster",
    "worm": "Caenorhabditis elegans",
    "yeast": "Saccharomyces cerevisiae",
    "ecoli": "Escherichia coli",
    "arabidopsis": "Arabidopsis thaliana",
    "pig": "Sus scrofa",
    "dog": "Canis lupus familiaris",
    "chicken": "Gallus gallus",
    "cow": "Bos taurus",
    "xenopus": "Xenopus tropicalis",
    # ── Bacteria ──
    "staph": "Staphylococcus aureus",
    "mtb": "Mycobacterium tuberculosis",
    # ── Viruses ──
    "hiv-1": "Human immunodeficiency virus 1",
    "hiv": "Human immunodeficiency virus 1",
    "hbv": "Hepatitis B virus",
    "hcv": "Hepatitis C virus",
    "rsv": "Respiratory syncytial virus",
    "adenovirus": "Human adenovirus 1",
    "hpv": "Human papillomavirus",
    "hsv-1": "Human herpesvirus 1",
    "hsv-2": "Human herpesvirus 2",
    "hsv": "Human herpesvirus 1",
    "influenza-a": "Influenza A virus",
    "influenza-b": "Influenza B virus",
    "influenza": "Influenza A virus",
    "dengue": "Dengue virus",
    "zika": "Zika virus",
    "ebv": "Human gammaherpesvirus 4",
    "cmv": "Human betaherpesvirus 5",
    "sars-cov": "Severe acute respiratory syndrome-related coronavirus",
    "sars-cov-2": "Severe acute respiratory syndrome coronavirus 2",
    "mers-cov": "Middle East respiratory syndrome-related coronavirus",
    "west-nile": "West Nile virus",
    "ebola": "Zaire ebolavirus",
    "chikungunya": "Chikungunya virus",
    "measles": "Measles virus",
    "rotavirus": "Rotavirus A",
    "norovirus": "Norovirus",
    "parvovirus-b19": "Primate erythroparvovirus 1",
    "vzv": "Human alphaherpesvirus 3",
    "enterovirus": "Enterovirus",
    "rhinovirus": "Rhinovirus A",
    "hantavirus": "Orthohantavirus",
    "nipah": "Nipah virus",
    "lassa": "Lassa virus",
    "yellow-fever": "Yellow fever virus",
    "japanese-encephalitis": "Japanese encephalitis virus",
    "rabies": "Rabies virus",
    "htlv": "Human T-lymphotropic virus 1",
    "hhv-6": "Human betaherpesvirus 6",
    "hhv-8": "Human gammaherpesvirus 8",
    "bk-virus": "Human polyomavirus 1",
    "jc-virus": "Human polyomavirus 2",
    "parainfluenza": "Human parainfluenza virus",
    "metapneumovirus": "Human metapneumovirus",
    "bocavirus": "Human bocavirus 1",
    "torque-teno": "Torque teno virus",
}


def execute(input_data: Dict[str, Any]) -> Dict[str, Any]:
    sequence = input_data.get("consensus_sequence") or input_data.get("target_sequence") or input_data.get("sequence", "")
    if not sequence:
        return _fallback("No target sequence for MSA.", input_data)

    sequence = sequence.upper()
    sequence = re.sub(r"[^ACGT]", "N", sequence)
    if len(sequence) < 100:
        return _fallback("Sequence too short for meaningful MSA.", input_data)

    organism = input_data.get("organism", "human")
    gene_symbol = input_data.get("accession", "")

    # Fetch strain sequences from NCBI
    strain_seqs = _fetch_strain_sequences(sequence, organism, gene_symbol, input_data)
    if len(strain_seqs) < MIN_STRAIN_SEQUENCES:
        return _fallback(
            f"Only {len(strain_seqs)} strain(s) available (< {MIN_STRAIN_SEQUENCES} minimum). "
            "Cannot compute reliable conservation.",
            input_data, strain_seqs,
        )

    # Run MSA
    msa_result = _run_msa(sequence, strain_seqs)
    if "error" in msa_result:
        return _fallback(msa_result["error"], input_data, strain_seqs)

    aligned = msa_result["aligned"]
    reference_aligned = msa_result["reference"]

    # Compute per-base conservation scores
    scores = _compute_conservation_scores(aligned, reference_aligned)

    # Identify >95% conserved regions
    conserved = _find_conserved_regions(scores, CONSERVATION_THRESHOLD, min_length=20)

    return {
        "msa_alignment": aligned,
        "conservation_scores": scores,
        "conserved_regions": conserved,
        "msa_note": (
            f"MSA complete: {len(aligned)} sequences aligned, "
            f"{len(conserved)} conserved region(s) >95% found."
        ),
        "strain_count": len(aligned),
        "msa_status": "complete",
    }


def _run_msa(reference: str, strain_seqs: List[str]) -> Dict[str, Any]:
    try:
        return _run_muscle_msa(reference, strain_seqs)
    except Exception as e:
        logger.warning(f"MUSCLE MSA failed: {e}")
        try:
            return _run_biopython_msa(reference, strain_seqs)
        except Exception as e2:
            return {"error": f"MSA failed: {e2}"}


def _run_muscle_msa(reference: str, strain_seqs: List[str]) -> Dict[str, Any]:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".fa", delete=False) as f:
        f.write(f">reference\n{reference}\n")
        for i, seq in enumerate(strain_seqs):
            clean = re.sub(r"[^ACGT]", "N", seq.upper())
            f.write(f">strain_{i+1}\n{clean}\n")
        fasta_path = f.name

    output_path = fasta_path + ".afa"
    try:
        # Detect MUSCLE version and use appropriate flags
        try:
            ver_result = subprocess.run(["muscle", "-version"], capture_output=True, text=True, timeout=10)
            version_output = (ver_result.stdout + ver_result.stderr).lower()
            is_v5 = "5." in version_output or "muscle5" in version_output
        except (FileNotFoundError, subprocess.TimeoutExpired):
            is_v5 = False

        if is_v5:
            cmd = ["muscle", "-align", fasta_path, "-output", output_path]
        else:
            cmd = ["muscle", "-align", fasta_path, "-output", output_path]
        subprocess.run(cmd, capture_output=True, text=True, timeout=MSA_TIMEOUT_S, check=True)

        aligned = []
        current_id = None
        current_seq = []
        with open(output_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith(">"):
                    if current_id and current_seq:
                        aligned.append("".join(current_seq))
                    current_id = line[1:]
                    current_seq = []
                else:
                    current_seq.append(line)
            if current_id and current_seq:
                aligned.append("".join(current_seq))

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise RuntimeError(f"MUSCLE execution failed: {e}")
    finally:
        for path in [fasta_path, output_path]:
            try:
                os.unlink(path)
            except OSError:
                pass

    if not aligned:
        raise RuntimeError("MUSCLE produced no output.")

    # First sequence should be the reference (we wrote it first, MUSCLE preserves order)
    return {"aligned": aligned, "reference": aligned[0] if aligned else reference}


def _run_biopython_msa(reference: str, strain_seqs: List[str]) -> Dict[str, Any]:
    """
    Fallback MSA using Biopython pairwise alignment when MUSCLE is unavailable.
    Aligns each strain to the reference independently using global pairwise
    alignment, then returns the reference + all aligned strain sequences.
    This is an approximation — true MSA requires MUSCLE/MAFFT.
    """
    from Bio import Align

    aligner = Align.PairwiseAligner()
    aligner.mode = "global"
    aligner.match_score = 2
    aligner.mismatch_score = -1
    aligner.gap_score = -2

    aligned = [reference]
    for seq in strain_seqs:
        clean_seq = re.sub(r"[^ACGT]", "N", seq.upper())
        aln = aligner.align(reference, clean_seq)
        best = next(aln)

        aligned_query = _pairwise_aln_to_string(best, reference, clean_seq)
        if aligned_query:
            aligned.append(aligned_query)
        else:
            aligned.append(clean_seq)

    return {"aligned": aligned, "reference": reference}


def _pairwise_aln_to_string(alignment, ref_seq: str, qry_seq: str) -> str:
    """
    Reconstruct the aligned query string from a Biopython PairwiseAlignment,
    inserting gaps where the reference has gaps relative to the query.

    alignment.aligned is a numpy array of shape (2, N, 2):
      aligned[0] = blocks on reference,  aligned[1] = blocks on query.
    Each block is [start, end) in 0-based coordinates.
    """
    ref_len = len(ref_seq)
    result = ["-"] * ref_len

    ref_blocks = alignment.aligned[0]
    qry_blocks = alignment.aligned[1]

    for (r_start, r_end), (q_start, q_end) in zip(ref_blocks, qry_blocks):
        r_start = int(r_start)
        r_end = int(r_end)
        q_start = int(q_start)
        q_end = int(q_end)
        aligned_len = min(r_end - r_start, q_end - q_start)
        for k in range(aligned_len):
            if r_start + k < ref_len:
                result[r_start + k] = qry_seq[q_start + k]

    return "".join(result)


def _compute_conservation_scores(aligned: List[str], reference: str) -> List[float]:
    if not aligned or len(aligned) < 2:
        return [1.0] * len(reference)

    # Exclude the reference (first sequence) from conservation counting
    strain_sequences = aligned[1:] if len(aligned) > 1 else []
    n_strains = len(strain_sequences)
    if n_strains == 0:
        return [1.0] * len(reference)

    ref_len = len(reference)
    scores = []
    for pos in range(ref_len):
        ref_base = reference[pos].upper() if pos < len(reference) else "N"
        if ref_base not in "ACGT":
            scores.append(0.0)
            continue
        match_count = 0
        total_valid = 0
        for seq in strain_sequences:
            if pos >= len(seq):
                continue
            base = seq[pos].upper()
            if base == "-":
                continue
            total_valid += 1
            if base == ref_base:
                match_count += 1
        if total_valid > 0:
            scores.append(match_count / total_valid)
        else:
            scores.append(0.0)

    return scores


def _find_conserved_regions(scores: List[float], threshold: float, min_length: int = 20) -> List[Dict[str, Any]]:
    regions = []
    in_region = False
    start = 0

    for i, score in enumerate(scores):
        if score >= threshold and not in_region:
            start = i
            in_region = True
        elif score < threshold and in_region:
            if i - start >= min_length:
                avg = sum(scores[start:i]) / (i - start) if i > start else 0
                regions.append({
                    "start": start,
                    "end": i - 1,
                    "length": i - start,
                    "avg_conservation": round(avg, 4),
                })
            in_region = False

    if in_region and len(scores) - start >= min_length:
        avg = sum(scores[start:]) / (len(scores) - start)
        regions.append({
            "start": start,
            "end": len(scores) - 1,
            "length": len(scores) - start,
            "avg_conservation": round(avg, 4),
        })

    return regions


def _fetch_strain_sequences(
    reference: str, organism: str, accession: str, input_data: Dict[str, Any]
) -> List[str]:
    from Bio import Entrez

    Entrez.email = input_data.get("ncbi_email") or os.environ.get("NCBI_EMAIL", "user@example.com")
    ncbi_api_key = input_data.get("ncbi_api_key") or os.environ.get("NCBI_API_KEY", "")
    if ncbi_api_key:
        Entrez.api_key = ncbi_api_key

    sequences = []
    try:
        if accession:
            ids = _search_related_accessions(accession, organism, ncbi_api_key, Entrez.email)
        else:
            ids = []

        if not ids:
            # Fallback: search by organism for representative RefSeq sequences
            ids = _search_refseq_by_organism(organism, ncbi_api_key, Entrez.email)

        sequences = _fetch_sequences_by_ids(ids, max_count=MAX_STRAIN_SEQUENCES)
    except Exception as e:
        logger.warning(f"NCBI strain fetch failed: {e}")

    return sequences


def _search_refseq_by_organism(organism: str, api_key: str = "", email: str = "") -> List[str]:
    """Search for RefSeq nucleotide records for a given organism."""
    from Bio import Entrez
    try:
        Entrez.email = email or os.environ.get("NCBI_EMAIL", "user@example.com")
        org_name = TARGET_ORGANISM_NCBI_MAP.get(organism.lower(), organism)
        if api_key:
            Entrez.api_key = api_key
        query = f"{org_name}[Organism] AND srcdb_refseq[Properties] AND biomol mrna[Properties]"
        handle = Entrez.esearch(db="nucleotide", term=query, retmax=MAX_STRAIN_SEQUENCES)
        record = Entrez.read(handle)
        handle.close()
        return record.get("IdList", [])
    except Exception as e:
        logger.debug(f"Organism-based RefSeq search failed: {e}")
        return []


def _search_related_accessions(accession: str, organism: str, api_key: str = "", email: str = "") -> List[str]:
    """
    Find related strain sequences for a given accession from ANY database.
    Works with NCBI GenBank, RefSeq, DDBJ, ENA/EMBL (all INSDC members via NCBI Entrez),
    and Ensembl (via REST API lookup).
    """
    from Bio import Entrez

    Entrez.email = email or os.environ.get("NCBI_EMAIL", "user@example.com")
    ncbi_api_key = api_key or os.environ.get("NCBI_API_KEY", "")
    if ncbi_api_key:
        Entrez.api_key = ncbi_api_key

    org_name = TARGET_ORGANISM_NCBI_MAP.get(organism.lower(), organism)

    try:
        # Strategy 1: Try direct NCBI esearch with the accession string
        # NCBI's unified database covers all INSDC members (GenBank, DDBJ, ENA)
        # This handles: NCBI RefSeq (NM_, XM_, ...), DDBJ (LC, AB, ...), ENA (X, Z, ...)
        if re.match(r"^(NM_|XM_|NR_|XR_|NG_|NC_|NT_|NW_|AB|LC|AP|BA|HT|[A-Z]{2}\d{6})", accession, re.I):
            return _find_related_by_accession(accession, org_name, email)

        # Strategy 2: Ensembl ID — try to map to NCBI via Ensembl REST API
        if re.match(r"^ENS[A-Z]*[GTEP]\d{11}", accession, re.I):
            return _find_related_ensembl(accession, org_name, email)

        # Strategy 3: Treat as gene symbol
        query = f"{accession}[Gene Name] AND {org_name}[Organism] AND srcdb_refseq[Properties] AND biomol mrna[Properties]"
        handle = Entrez.esearch(db="nucleotide", term=query, retmax=MAX_STRAIN_SEQUENCES)
        record = Entrez.read(handle)
        handle.close()
        return record.get("IdList", [])

    except Exception as e:
        logger.debug(f"Related accession search failed for '{accession}': {e}")
        return _search_refseq_by_organism(organism, api_key, email)


def _find_related_by_accession(accession: str, organism: str, email: str) -> List[str]:
    """
    Given a nucleotide accession from any INSDC database (NCBI, DDBJ, ENA),
    find related RefSeq sequences for the same gene via NCBI Entrez.
    """
    from Bio import Entrez

    Entrez.email = email or os.environ.get("NCBI_EMAIL", "user@example.com")

    try:
        # Step 1: Look up the accession in NCBI nucleotide database
        # NCBI Entrez handles INSDC accessions from all members (GenBank, DDBJ, ENA)
        handle = Entrez.esummary(db="nucleotide", id=accession)
        summary = Entrez.read(handle)
        handle.close()

        gene_symbol = ""
        organism_from_record = ""
        if summary:
            title = summary[0].get("Title", "")
            # Title format: "Homo sapiens tumor protein p53 (TP53), transcript variant 1, mRNA"
            m = re.search(r"\((\w+)\)", title)
            if m:
                gene_symbol = m.group(1)
            # Extract organism from title prefix
            org_m = re.match(r"^([A-Z][a-z]+(?: [a-z]+)*)", title)
            if org_m:
                organism_from_record = org_m.group(1)

        # Use organism from record if available, otherwise fall back to input
        search_organism = organism_from_record or organism

        # Step 2: If we have a gene symbol, search for related RefSeq sequences
        if gene_symbol:
            query = f"{gene_symbol}[Gene Name] AND {search_organism}[Organism] AND srcdb_refseq[Properties] AND biomol mrna[Properties]"
            handle = Entrez.esearch(db="nucleotide", term=query, retmax=MAX_STRAIN_SEQUENCES)
            record = Entrez.read(handle)
            handle.close()
            ids = record.get("IdList", [])
            if len(ids) >= 1:
                return ids

        # Step 3: Fallback — search broader (include non-RefSeq) for same accession prefix
        base_acc = accession.split(".")[0]
        query = f"{base_acc}[ACCN]"
        handle = Entrez.esearch(db="nucleotide", term=query, retmax=MAX_STRAIN_SEQUENCES)
        record = Entrez.read(handle)
        handle.close()
        ids = record.get("IdList", [])
        if ids:
            return ids

        # Step 4: Last resort — organism-based RefSeq search
        return _search_refseq_by_organism(search_organism, "", email)

    except Exception as e:
        logger.debug(f"Related seq by accession failed for '{accession}': {e}")
        return _search_refseq_by_organism(organism, "", email)


def _find_related_ensembl(accession: str, organism: str, email: str) -> List[str]:
    """
    Given an Ensembl stable ID, find related strain sequences.
    Maps Ensembl transcript/gene ID to NCBI via the Ensembl REST API,
    then finds related RefSeq sequences.
    """
    import urllib.request
    import json as _json

    try:
        # Step 1: Query Ensembl REST API for the stable ID to get gene info
        ensembl_id = accession.split(".")[0]
        url = f"https://rest.ensembl.org/lookup/id/{ensembl_id}?content-type=application/json"
        req = urllib.request.Request(url, headers={"User-Agent": "VigyanLLM/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = _json.loads(resp.read().decode())

        gene_id = data.get("gene_id") or data.get("id", "")
        species = data.get("species", organism)
        display_name = data.get("display_name", "")

        # Step 2: If we have a gene or display name, try to find cross-references
        if gene_id:
            xref_url = f"https://rest.ensembl.org/xrefs/id/{gene_id}?content-type=application/json"
            xreq = urllib.request.Request(xref_url, headers={"User-Agent": "VigyanLLM/1.0"})
            with urllib.request.urlopen(xreq, timeout=15) as xresp:
                xrefs = _json.loads(xresp.read().decode())

            # Look for NCBI Gene or RefSeq cross-references
            ncbi_gene_id = ""
            for xref in xrefs:
                db = xref.get("dbname", "")
                if db == "NCBI_gene":
                    ncbi_gene_id = xref.get("primary_id", "")
                    break
                if "RefSeq" in db and xref.get("primary_id", "").startswith(("NM_", "XM_")):
                    # Direct RefSeq match — use it as the accession
                    refseq_acc = xref.get("primary_id", "")
                    from Bio import Entrez
                    Entrez.email = email or os.environ.get("NCBI_EMAIL", "user@example.com")
                    return _find_related_by_accession(refseq_acc, species, email)

            # Step 3: If we found an NCBI gene ID, search for RefSeq transcripts
            if ncbi_gene_id:
                from Bio import Entrez
                Entrez.email = email or os.environ.get("NCBI_EMAIL", "user@example.com")
                query = f"{ncbi_gene_id}[Gene ID] AND srcdb_refseq[Properties] AND biomol mrna[Properties]"
                handle = Entrez.esearch(db="nucleotide", term=query, retmax=MAX_STRAIN_SEQUENCES)
                record = Entrez.read(handle)
                handle.close()
                ids = record.get("IdList", [])
                if ids:
                    return ids

        # Step 4: Try gene symbol from display name
        m = re.search(r"\((\w+)\)", display_name)
        if m:
            gene_symbol = m.group(1)
            from Bio import Entrez
            Entrez.email = email or os.environ.get("NCBI_EMAIL", "user@example.com")
            query = f"{gene_symbol}[Gene Name] AND {species}[Organism] AND srcdb_refseq[Properties] AND biomol mrna[Properties]"
            handle = Entrez.esearch(db="nucleotide", term=query, retmax=MAX_STRAIN_SEQUENCES)
            record = Entrez.read(handle)
            handle.close()
            ids = record.get("IdList", [])
            if ids:
                return ids

    except Exception as e:
        logger.debug(f"Ensembl lookup failed for '{accession}': {e}")

    # Step 5: Fall back to organism-based RefSeq search
    return _search_refseq_by_organism(organism, "", email)


def _fetch_sequences_by_ids(ids: List[str], max_count: int = MAX_STRAIN_SEQUENCES) -> List[str]:
    if not ids:
        return []

    from Bio import Entrez

    Entrez.email = os.environ.get("NCBI_EMAIL", "user@example.com")
    sequences = []
    batch_size = 10
    for i in range(0, min(len(ids), max_count), batch_size):
        batch = ids[i : i + batch_size]
        try:
            handle = Entrez.efetch(db="nucleotide", id=",".join(batch), rettype="fasta", retmode="text")
            raw = handle.read()
            handle.close()
            seqs = _parse_fasta(raw)
            sequences.extend(seqs)
        except Exception as e:
            logger.debug(f"NCBI fetch batch failed: {e}")
            continue

    return sequences


def _parse_fasta(raw: str) -> List[str]:
    sequences = []
    current = []
    for line in raw.splitlines():
        if line.startswith(">"):
            if current:
                sequences.append("".join(current))
                current = []
        else:
            current.append(line.strip().upper())
    if current:
        sequences.append("".join(current))
    return sequences


def _fallback(
    reason: str,
    input_data: Dict[str, Any],
    strain_seqs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    sequence = input_data.get("consensus_sequence") or input_data.get("target_sequence") or input_data.get("sequence", "")
    logger.info(f"MSA fallback: {reason}")

    result = {
        "msa_alignment": [],
        "conservation_scores": [0.0] * len(sequence) if sequence else [],
        "conserved_regions": [],
        "msa_note": reason,
        "strain_count": len(strain_seqs) if strain_seqs else 0,
        "msa_status": "fallback_no_strains" if not strain_seqs else "fallback_error",
    }

    if sequence:
        result["conserved_regions"] = []
        result["conservation_scores"] = [0.0] * len(sequence)

    return result

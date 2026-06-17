#!/usr/bin/env python3
"""
VigyanLLM Sequence Fetcher
==============================
Fetches real sequences from live databases.
Sources: NCBI Nucleotide, NCBI Gene, Ensembl REST, UniProt.
ALL sequences are fetched in real-time — no cached or simulated data.
Rate limiting: NCBI max 3 req/sec without key, 10/sec with key.
"""

import os, time, logging, re
from typing import Optional, Dict, Tuple, List

import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from Bio import Entrez, SeqIO, SeqRecord
from Bio.Seq import Seq
import io

logger = logging.getLogger("primerforge.fetch")

NCBI_BASE     = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
ENSEMBL_BASE  = "https://rest.ensembl.org"
UNIPROT_BASE  = "https://rest.uniprot.org/uniprotkb"

# Set your NCBI email and API key (required for Entrez)
Entrez.email   = "vigyanllm@example.com"
NCBI_API_KEY   = os.environ.get("NCBI_API_KEY", "")
if NCBI_API_KEY:
    Entrez.api_key = NCBI_API_KEY
    logger.info("NCBI API key loaded from environment — rate limit: 10 req/sec")
else:
    logger.info("No NCBI API key — rate limit: 3 req/sec")

HEADERS = {"User-Agent": "VigyanLLM-PrimerMSA/1.0 (https://vigyanllm.ai; vigyanllm@example.com)"}


def _rate_limit_ncbi():
    """Enforce NCBI rate limit."""
    time.sleep(0.4 if NCBI_API_KEY else 0.35)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_ncbi_nucleotide(accession: str, seq_start: int = 0,
                           seq_stop: int = 0) -> Dict:
    """
    Fetch a nucleotide sequence from NCBI by accession number.
    Supports: NM_, NR_, NP_, NC_, NG_, XM_, XR_ accessions.
    seq_start/stop: 1-based coordinates (0 = full sequence)
    Returns full SeqRecord metadata including gene annotations.
    """
    _rate_limit_ncbi()
    params = {
        "db": "nucleotide", "id": accession,
        "rettype": "genbank", "retmode": "text"
    }
    if seq_start and seq_stop:
        params["seq_start"] = seq_start
        params["seq_stop"]  = seq_stop
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY

    r = requests.get(f"{NCBI_BASE}efetch.fcgi", params=params,
                     headers=HEADERS, timeout=30)
    r.raise_for_status()

    handle = io.StringIO(r.text)
    records = list(SeqIO.parse(handle, "genbank"))
    if not records:
        raise ValueError(f"No sequence returned for accession: {accession}")

    rec = records[0]

    # Handle UndefinedSequenceError in newer BioPython versions
    try:
        seq_str = str(rec.seq)
        if not seq_str or seq_str == "None" or set(seq_str) == {"N"}:
            raise ValueError("Sequence is empty or undefined")
    except Exception:
        # Fallback: fetch as FASTA which always contains the sequence
        _rate_limit_ncbi()
        fasta_params = {
            "db": "nucleotide", "id": accession,
            "rettype": "fasta", "retmode": "text"
        }
        if NCBI_API_KEY:
            fasta_params["api_key"] = NCBI_API_KEY
        r2 = requests.get(f"{NCBI_BASE}efetch.fcgi", params=fasta_params,
                          headers=HEADERS, timeout=30)
        r2.raise_for_status()
        fasta_lines = r2.text.strip().split("\n")
        if len(fasta_lines) < 2:
            raise ValueError(f"No sequence data available for accession: {accession}")
        seq_str = "".join(line.strip() for line in fasta_lines[1:] if not line.startswith(">"))

    # Extract gene annotations from features
    features = []
    for feat in rec.features:
        if feat.type in ("gene", "CDS", "exon", "UTR", "primer_bind"):
            loc = feat.location
            features.append({
                "type":       feat.type,
                "start":      int(loc.start),
                "end":        int(loc.end),
                "strand":     loc.strand,
                "qualifiers": {k: v[0] if isinstance(v, list) and v else v
                               for k, v in feat.qualifiers.items()
                               if k in ["gene", "product", "note", "db_xref", "protein_id"]}
            })

    return {
        "accession":   accession,
        "id":          rec.id,
        "name":        rec.name,
        "description": rec.description,
        "organism":    rec.annotations.get("organism", "Unknown"),
        "taxonomy":    rec.annotations.get("taxonomy", []),
        "sequence":    seq_str,
        "length":      len(seq_str),
        "gc_content":  round((seq_str.count("G") + seq_str.count("C")) / len(seq_str) * 100, 2),
        "features":    features,
        "molecule_type": rec.annotations.get("molecule_type", "DNA"),
        "data_file_division": rec.annotations.get("data_file_division", ""),
        "source":      "NCBI Nucleotide",
    }


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_ncbi_fasta(accession_or_id: str, db: str = "nucleotide") -> str:
    """Fetch raw FASTA from NCBI. db: nucleotide | protein | gene"""
    _rate_limit_ncbi()
    params = {"db": db, "id": accession_or_id, "rettype": "fasta", "retmode": "text"}
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    r = requests.get(f"{NCBI_BASE}efetch.fcgi", params=params,
                     headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def search_ncbi_gene(gene_name: str, organism: str = "human") -> List[Dict]:
    """
    Search NCBI Gene database and return gene summaries.
    Returns list of genes with ID, symbol, description, RefSeq accessions.
    """
    _rate_limit_ncbi()
    query  = f"{gene_name}[gene] AND {organism}[orgn] AND alive[prop]"
    params = {"db": "gene", "term": query, "retmax": 10, "retmode": "json"}
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY

    r = requests.get(f"{NCBI_BASE}esearch.fcgi", params=params,
                     headers=HEADERS, timeout=20)
    r.raise_for_status()
    ids = r.json().get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []

    # Fetch summaries
    _rate_limit_ncbi()
    params2 = {"db": "gene", "id": ",".join(ids[:5]),
               "retmode": "json", "rettype": "gene_table"}
    if NCBI_API_KEY:
        params2["api_key"] = NCBI_API_KEY
    r2 = requests.get(f"{NCBI_BASE}esummary.fcgi", params=params2,
                      headers=HEADERS, timeout=20)
    r2.raise_for_status()

    genes = []
    result = r2.json().get("result", {})
    for gid in ids[:5]:
        g = result.get(gid, {})
        # Fetch RefSeq accessions via elink
        refseq_accessions = fetch_gene_refseq_accessions(gid)
        genes.append({
            "gene_id":     gid,
            "symbol":      g.get("name", ""),
            "name":        g.get("description", ""),
            "organism":    g.get("organism", {}).get("scientificname", organism),
            "chromosome":  g.get("chromosome", ""),
            "map_location": g.get("maplocation", ""),
            "summary":     g.get("summary", "")[:300],
            "refseq_mRNA": refseq_accessions.get("mRNA", []),
            "refseq_prot": refseq_accessions.get("protein", []),
        })
    return genes


def fetch_gene_refseq_accessions(gene_id: str) -> Dict:
    """Fetch RefSeq mRNA and protein accessions linked to a Gene ID."""
    _rate_limit_ncbi()
    try:
        params = {"dbfrom": "gene", "db": "nuccore", "id": gene_id,
                  "linkname": "gene_nuccore_refseqrna", "retmode": "json"}
        if NCBI_API_KEY:
            params["api_key"] = NCBI_API_KEY
        r = requests.get(f"{NCBI_BASE}elink.fcgi", params=params,
                         headers=HEADERS, timeout=15)
        r.raise_for_status()
        linksets = r.json().get("linksets", [])
        ids = []
        for ls in linksets:
            for ld in ls.get("linksetdbs", []):
                ids.extend(ld.get("links", []))
        # Get accession strings
        if ids:
            _rate_limit_ncbi()
            params2 = {"db": "nuccore", "id": ",".join(ids[:5]),
                       "rettype": "acc", "retmode": "text"}
            if NCBI_API_KEY:
                params2["api_key"] = NCBI_API_KEY
            r2 = requests.get(f"{NCBI_BASE}efetch.fcgi", params=params2,
                              headers=HEADERS, timeout=15)
            mRNA_accessions = [a.strip() for a in r2.text.split("\n") if a.strip()]
            return {"mRNA": mRNA_accessions[:3], "protein": []}
    except Exception as e:
        logger.debug("NCBI protein fetch failed: %s", e)
    return {"mRNA": [], "protein": []}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_ensembl_sequence(ensembl_id: str, seq_type: str = "genomic",
                            expand_5prime: int = 0, expand_3prime: int = 0) -> Dict:
    """
    Fetch sequence from Ensembl REST API.
    ensembl_id: ENSG (gene), ENST (transcript), ENSP (protein), ENSE (exon)
    seq_type: genomic | cds | cdna | protein | utr3 | utr5
    Returns real sequence + metadata.
    """
    url = f"{ENSEMBL_BASE}/sequence/id/{ensembl_id}"
    params = {
        "content-type": "application/json",
        "type":          seq_type,
        "expand_5prime": expand_5prime,
        "expand_3prime": expand_3prime,
    }
    r = requests.get(url, params=params, headers={**HEADERS,
                     "Content-Type": "application/json"}, timeout=20)
    r.raise_for_status()
    data = r.json()

    return {
        "id":          data.get("id", ensembl_id),
        "desc":        data.get("desc", ""),
        "seq":         data.get("seq", ""),
        "length":      len(data.get("seq", "")),
        "molecule":    data.get("molecule", ""),
        "species":     data.get("species", ""),
        "assembly":    data.get("assembly_name", ""),
        "source":      "Ensembl REST",
        "seq_type":    seq_type,
    }


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_ensembl_gene_info(gene_symbol: str, species: str = "human") -> Dict:
    """Fetch gene coordinates, transcripts, and exons from Ensembl."""
    # Map species to Ensembl name
    species_map = {"human": "homo_sapiens", "mouse": "mus_musculus",
                   "rat": "rattus_norvegicus", "zebrafish": "danio_rerio"}
    ens_species = species_map.get(species.lower(), species.lower())

    url = f"{ENSEMBL_BASE}/lookup/symbol/{ens_species}/{gene_symbol}"
    r = requests.get(url, headers={**HEADERS, "Content-Type": "application/json"},
                     params={"content-type": "application/json", "expand": 1},
                     timeout=20)
    r.raise_for_status()
    data = r.json()

    transcripts = []
    for t in data.get("Transcript", []):
        exons = [{"id": e.get("id"), "start": e.get("start"),
                  "end": e.get("end"), "rank": e.get("rank")}
                 for e in t.get("Exon", [])]
        transcripts.append({
            "id":           t.get("id"),
            "name":         t.get("display_name", ""),
            "biotype":      t.get("biotype", ""),
            "is_canonical": t.get("is_canonical", 0),
            "length":       t.get("length", 0),
            "exon_count":   len(exons),
            "exons":        exons,
            "translation_id": t.get("Translation", {}).get("id", ""),
        })

    return {
        "gene_id":     data.get("id", ""),
        "symbol":      gene_symbol,
        "display_name": data.get("display_name", gene_symbol),
        "species":     species,
        "chromosome":  data.get("seq_region_name", ""),
        "start":       data.get("start", 0),
        "end":         data.get("end", 0),
        "strand":      data.get("strand", 1),
        "biotype":     data.get("biotype", ""),
        "description": data.get("description", ""),
        "transcripts": transcripts,
        "canonical_transcript": next(
            (t["id"] for t in transcripts if t.get("is_canonical")), ""),
        "source":      "Ensembl REST",
    }


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_uniprot_sequence(uniprot_id: str) -> Dict:
    """Fetch protein sequence and metadata from UniProt."""
    r_fasta = requests.get(f"{UNIPROT_BASE}/{uniprot_id}.fasta",
                           headers=HEADERS, timeout=20)
    r_fasta.raise_for_status()
    fasta_lines = r_fasta.text.strip().split("\n")
    header  = fasta_lines[0] if fasta_lines else ""
    seq_str = "".join(fasta_lines[1:])

    # Fetch JSON metadata
    r_json = requests.get(f"{UNIPROT_BASE}/{uniprot_id}",
                          headers={**HEADERS, "Accept": "application/json"},
                          timeout=20)
    r_json.raise_for_status()
    meta = r_json.json()

    gene_names = [gn.get("geneName", {}).get("value", "")
                  for gn in meta.get("genes", []) if gn.get("geneName")]

    return {
        "uniprot_id":  uniprot_id,
        "entry_name":  meta.get("uniProtkbId", ""),
        "gene_names":  gene_names,
        "organism":    meta.get("organism", {}).get("scientificName", ""),
        "protein_name": meta.get("proteinDescription", {}).get(
                            "recommendedName", {}).get("fullName", {}).get("value", ""),
        "sequence":    seq_str,
        "length":      len(seq_str),
        "reviewed":    meta.get("entryType", "") == "UniProtKB reviewed (Swiss-Prot)",
        "function":    next((c.get("texts", [{}])[0].get("value", "")
                             for c in meta.get("comments", [])
                             if c.get("commentType") == "FUNCTION"), ""),
        "source":      "UniProt",
    }

#!/usr/bin/env python3
"""
VigyanLLM Sequence Fetcher
==============================
Fetches real sequences from live databases.
Sources: NCBI Nucleotide, NCBI Gene, Ensembl REST, UniProt.
ALL sequences are fetched in real-time — no cached or simulated data.
Rate limiting: NCBI max 3 req/sec without key, 10/sec with key.
"""

import io
import logging
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
# `as_completed` raises the futures module's TimeoutError, which is the builtin
# on 3.11+ but a distinct class on older Pythons — import it so both are caught.
from concurrent.futures import TimeoutError as FuturesTimeoutError

import requests
from Bio import Entrez, SeqIO
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger("primerforge.fetch")

NCBI_BASE     = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
ENSEMBL_BASE  = "https://rest.ensembl.org"
UNIPROT_BASE  = "https://rest.uniprot.org/uniprotkb"
ENA_BASE      = "https://www.ebi.ac.uk/ena/portal/api"
ENA_BROWSER_API = "https://www.ebi.ac.uk/ena/browser/api"

# Hard wall-clock budget for one search request. Must stay comfortably below
# BOTH the browser's 30s AbortController timeout (frontend/search.html) and
# CloudFront's ~60s origin-response timeout — otherwise the caller sees a
# timeout/504 while the backend is still working. Overridable for tests.
SEARCH_BUDGET_S = float(os.environ.get("SEARCH_BUDGET_S", "20"))

# Sequence mode runs a remote BLAST, which NCBI queues and answers asynchronously
# (it returns an RTOE and the result arrives seconds later). That is inherently
# slower than a metadata lookup, so it gets its own ceiling — still below the
# browser's sequence-mode abort and well under CloudFront's ~60s origin-response
# timeout, which is what turned an over-long search into a user-facing 504.
SEARCH_SEQUENCE_BUDGET_S = float(os.environ.get("SEARCH_SEQUENCE_BUDGET_S", "40"))

# How long a cached search result stays valid. Gene-symbol lookups are highly
# repeatable, and this keeps a burst of identical queries from re-fanning-out
# to every upstream database.
SEARCH_CACHE_TTL_S = float(os.environ.get("SEARCH_CACHE_TTL_S", "900"))

# Set your NCBI email and API key (required for Entrez)
Entrez.email   = os.environ.get("NCBI_EMAIL", "user@example.com")
NCBI_API_KEY   = os.environ.get("NCBI_API_KEY", "")
if NCBI_API_KEY:
    Entrez.api_key = NCBI_API_KEY
    logger.info("NCBI API key loaded from environment — rate limit: 10 req/sec")
else:
    logger.info("No NCBI API key — rate limit: 3 req/sec")

HEADERS = {"User-Agent": "VigyanLLM-PrimerMSA/1.0 (https://vigyanllm.in; contact@vigyanllm.in)"}

# Uniform result schema for all fetchers
SOURCE_URLS = {
    "ncbi": "https://www.ncbi.nlm.nih.gov/nuccore/{id}",
    "ncbi_gene": "https://www.ncbi.nlm.nih.gov/gene/{id}",
    "ensembl": "https://{host}.ensembl.org/id/{id}",
    "uniprot": "https://www.uniprot.org/uniprotkb/{id}",
    "ddbj": "https://www.ddbj.nig.ac.jp/{id}",
    "ena": "https://www.ebi.ac.uk/ena/browser/view/{id}",
}

UNIFORM_SCHEMA = {
    "id": "",
    "accession": "",
    "name": "",
    "description": "",
    "organism": "",
    "sequence": "",
    "length": 0,
    "gc_content": 0.0,
    "source": "",
    "source_url": "",
    "molecule_type": "DNA",
    "features": [],
}


def _make_result(data: dict, source: str, source_id: str = None) -> dict:
    """Wrap a fetcher result into the uniform schema with source URL."""
    result = dict(UNIFORM_SCHEMA)
    result["id"] = data.get("accession") or data.get("id") or source_id or ""
    result["accession"] = data.get("accession") or result["id"]
    result["name"] = data.get("name") or data.get("entry_name") or ""
    result["description"] = data.get("description") or data.get("desc") or data.get("protein_name") or ""
    result["organism"] = data.get("organism") or data.get("species") or ""
    result["sequence"] = data.get("sequence") or data.get("seq") or ""
    result["length"] = data.get("length") or len(result["sequence"])
    if result["sequence"]:
        s = result["sequence"].upper()
        result["gc_content"] = round((s.count("G") + s.count("C")) / len(s) * 100, 2) if len(s) > 0 else 0.0
    result["source"] = source
    result["molecule_type"] = data.get("molecule_type") or data.get("molecule") or "DNA"
    result["features"] = data.get("features", [])

    # Generate source URL
    url_template = SOURCE_URLS.get(source, "")
    if url_template:
        identifier = source_id or result["id"]
        if source == "ensembl":
            species = (data.get("species") or "homo_sapiens").lower().replace(" ", "_")
            result["source_url"] = url_template.format(host=species, id=identifier)
        else:
            result["source_url"] = url_template.format(id=identifier)
    return result


_NCBI_LOCK = threading.Lock()
_NCBI_NEXT_SLOT = [0.0]
# NCBI allows 10 req/s with an API key, 3 req/s without. A shared wall-clock
# slot keeps the limit true across parallel workers — a per-call sleep does not.
_NCBI_MIN_INTERVAL = 0.1 if NCBI_API_KEY else 0.34


def _rate_limit_ncbi():
    """Thread-safe NCBI rate limit: 10 req/sec with key, 3 req/sec without."""
    with _NCBI_LOCK:
        now = time.monotonic()
        wait = _NCBI_NEXT_SLOT[0] - now
        if wait > 0:
            time.sleep(wait)
        _NCBI_NEXT_SLOT[0] = time.monotonic() + _NCBI_MIN_INTERVAL


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_ncbi_nucleotide(accession: str, seq_start: int = 0,
                           seq_stop: int = 0) -> dict:
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
def search_ncbi_gene(gene_name: str, organism: str = "human",
                     include_refseq: bool = False) -> list[dict]:
    """
    Search NCBI Gene and return gene summaries (esearch + esummary = 2 calls).

    include_refseq additionally resolves RefSeq accessions for each gene, which
    costs 2 extra HTTP calls per gene. It is opt-in: the search UI does not
    render those fields, but /api/primer/fetch-sequence depends on them.
    """
    _rate_limit_ncbi()
    query  = f"{gene_name}[gene] AND {organism}[orgn] AND alive[prop]"
    params = {"db": "gene", "term": query, "retmax": 10, "retmode": "json"}
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY

    r = requests.get(f"{NCBI_BASE}esearch.fcgi", params=params,
                     headers=HEADERS, timeout=15)
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
                      headers=HEADERS, timeout=15)
    r2.raise_for_status()

    genes = []
    result = r2.json().get("result", {})
    for gid in ids[:5]:
        g = result.get(gid, {})
        # esummary returns `organism` as a plain scientific-name string; older
        # versions returned a dict. Handle both — calling .get() on the string
        # raised AttributeError and failed every NCBI Gene search.
        org = g.get("organism") or ""
        if isinstance(org, dict):
            org = org.get("scientificname", "") or ""
        refseq_accessions = (fetch_gene_refseq_accessions(gid)
                             if include_refseq else {"mRNA": [], "protein": []})
        genes.append({
            # Uniform result schema. The results table reads accession/id/
            # description/length/sequence/source_url — a gene record carried
            # none of them, so NCBI Gene rows rendered with a blank ID column
            # and no Source link. Existing keys are preserved: the fetch-sequence
            # route reads refseq_mRNA and returns the whole dict as gene_info.
            "id":           gid,
            "accession":    gid,
            "gene_id":      gid,
            "symbol":       g.get("name", ""),
            "name":         g.get("description", "") or g.get("name", ""),
            "description":  g.get("description", ""),
            "organism":     org or organism,
            "length":       0,
            "sequence":     "",
            "source":       "ncbi_gene",
            "source_url":   SOURCE_URLS["ncbi_gene"].format(id=gid),
            "chromosome":   g.get("chromosome", ""),
            "map_location": g.get("maplocation", ""),
            "summary":      (g.get("summary") or "")[:300],
            "refseq_mRNA":  refseq_accessions.get("mRNA", []),
            "refseq_prot":  refseq_accessions.get("protein", []),
        })
    return genes


def fetch_gene_refseq_accessions(gene_id: str) -> dict:
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
                            expand_5prime: int = 0, expand_3prime: int = 0) -> dict:
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


def _ensembl_gene_payload(data: dict, gene_symbol: str, species: str) -> dict:
    """Map an Ensembl lookup response into the gene-info payload."""
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


def _ensembl_symbol_lookup(gene_symbol: str, ens_species: str, timeout: float = 8.0):
    """Single-attempt Ensembl symbol lookup, used by the search sweep.

    Deliberately not fetch_ensembl_gene_info(): that one retries three times
    with exponential backoff on top of a 20s timeout — right for an explicit
    fetch, but it could hold an entire parallel search past its own deadline.
    Returns None on any miss or error so the sweep can report it and move on.
    """
    url = f"{ENSEMBL_BASE}/lookup/symbol/{ens_species}/{gene_symbol}"
    try:
        r = requests.get(url, headers={**HEADERS, "Content-Type": "application/json"},
                         params={"content-type": "application/json", "expand": 1},
                         timeout=timeout)
        if r.status_code in (400, 404):
            return None
        r.raise_for_status()
        return _ensembl_gene_payload(r.json(), gene_symbol, ens_species)
    except Exception as e:
        logger.debug("Ensembl symbol lookup failed: %s", e)
        return None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_ensembl_gene_info(gene_symbol: str, species: str = "human") -> dict:
    """Fetch gene coordinates, transcripts, and exons from Ensembl.

    Patient by design (3 attempts, 20s timeout) — this backs an explicit fetch.
    The search sweep uses _ensembl_symbol_lookup instead.
    """
    # Map species to Ensembl name
    species_map = {"human": "homo_sapiens", "mouse": "mus_musculus",
                   "rat": "rattus_norvegicus", "zebrafish": "danio_rerio"}
    ens_species = species_map.get(species.lower(), species.lower())

    url = f"{ENSEMBL_BASE}/lookup/symbol/{ens_species}/{gene_symbol}"
    r = requests.get(url, headers={**HEADERS, "Content-Type": "application/json"},
                     params={"content-type": "application/json", "expand": 1},
                     timeout=20)
    r.raise_for_status()
    return _ensembl_gene_payload(r.json(), gene_symbol, species)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_uniprot_sequence(uniprot_id: str) -> dict:
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


# ════════════════════════════════════════════════════════════════
# Batched sequence back-fill
# ════════════════════════════════════════════════════════════════
# Search summaries (esummary / lookup) are metadata only, but the result table's
# "Send to Primer Design / BLAST / MSA" buttons read `sequence` from each row.
# Rather than downloading every hit individually (the original code's cost), we
# back-fill them in ONE batched call. All of these fail soft: a hit keeps an
# empty sequence rather than failing the whole search.

def _fetch_fasta_batch(db: str, accessions: list, timeout: int = 8) -> dict:
    """Fetch FASTA for many accessions in a single efetch call.

    Returns {accession: sequence}, indexed with and without the version suffix.
    """
    accs = [a for a in accessions if a][:25]
    if not accs:
        return {}
    _rate_limit_ncbi()
    params = {"db": db, "id": ",".join(accs), "rettype": "fasta", "retmode": "text"}
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    try:
        r = requests.get(f"{NCBI_BASE}efetch.fcgi", params=params,
                         headers=HEADERS, timeout=timeout)
        r.raise_for_status()
    except Exception as e:
        logger.debug("Batch FASTA fetch failed: %s", e)
        return {}
    out = {}
    try:
        for rec in SeqIO.parse(io.StringIO(r.text), "fasta"):
            seq = str(rec.seq)
            for key in (rec.id, rec.name, rec.id.split(".")[0]):
                if key and not out.get(key):
                    out[key] = seq
    except Exception as e:
        logger.debug("FASTA parse failed: %s", e)
    return out


def _attach_ncbi_sequences(results: list, db: str = "nuccore") -> None:
    """Populate `sequence` on NCBI hits using one batched efetch."""
    missing = [r for r in results if not r.get("sequence") and r.get("accession")]
    if not missing:
        return
    seqs = _fetch_fasta_batch(db, [r["accession"] for r in missing])
    if not seqs:
        return
    for r in missing:
        acc = r["accession"]
        r["sequence"] = seqs.get(acc) or seqs.get(acc.split(".")[0]) or ""


def _attach_ensembl_sequences(results: list) -> None:
    """Populate `sequence` on Ensembl transcript hits via one batched POST.

    Only transcript (ENST) rows are requested: a gene is a locus, not a
    molecule, and `type=cdna` is not defined for a gene id.
    """
    missing = [r for r in results
               if not r.get("sequence") and str(r.get("accession", "")).startswith("ENST")]
    if not missing:
        return
    ids = [r["accession"] for r in missing][:6]
    try:
        resp = requests.post(f"{ENSEMBL_BASE}/sequence/id",
                             params={"type": "cdna", "content-type": "application/json"},
                             headers={**HEADERS, "Content-Type": "application/json",
                                      "Accept": "application/json"},
                             json={"ids": ids}, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        logger.debug("Ensembl batch sequence fetch failed: %s", e)
        return
    if not isinstance(payload, list):
        return
    by_id = {d.get("id", ""): d.get("seq", "")
             for d in payload if isinstance(d, dict)}
    for r in missing:
        r["sequence"] = by_id.get(r["accession"], "")


def _is_uniprot_id(value: str) -> bool:
    """True when `value` has the shape of a UniProt accession.

    UniProt ids are 6 or 10 alphanumeric characters with no separator.
    RefSeq (NM_…), Ensembl (ENST…) and GenBank (AB000000) accessions fail
    that shape.

    This matters twice over: free-text searching a foreign accession returns
    unrelated proteins, and UniProt's `accession:` query filter rejects a
    malformed value with a 400 that discards the entire batched query — so a
    single non-UniProt id in a multi-row back-fill would blank every row.
    """
    return bool(value) and value.isalnum() and len(value) in (6, 10) and not value.isdigit()


def _attach_uniprot_sequences(results: list) -> None:
    """Populate `sequence` on UniProt hits via one batched POST.

    UniProt's search endpoint returns metadata only, so every row came back
    sequenceless and the page's "Send to Design / BLAST / MSA" buttons had
    nothing to export for those selections.
    """
    missing = [r for r in results if not r.get("sequence") and r.get("accession")]
    if not missing:
        return
    # UniProt's `accession:` filter 400s the whole query when any single value
    # is malformed, so validate first — non-UniProt rows simply stay
    # sequenceless instead of taking every other row down with them.
    accessions = [a for a in (r["accession"] for r in missing)
                  if _is_uniprot_id(a)][:25]
    if not accessions:
        return
    # One OR'd query rather than one request per row. The dedicated
    # /uniprotkb/accessions POST rejects this payload shape, while
    # /uniprotkb/search?fields=... returns the sequence directly.
    query = "(" + " OR ".join(f"accession:{a}" for a in accessions) + ")"
    try:
        resp = requests.get(f"{UNIPROT_BASE}/search",
                            params={"query": query, "fields": "accession,sequence",
                                    "format": "json", "size": 50},
                            headers=HEADERS, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        logger.debug("UniProt batch sequence fetch failed: %s", e)
        return
    by_acc = {}
    for entry in (payload.get("results") or []) if isinstance(payload, dict) else []:
        # _search_uniprot_by_name labels rows with primaryAccession, so keying
        # on the same value maps every row without a secondary-accession pass.
        acc = entry.get("primaryAccession", "")
        seq = (entry.get("sequence") or {}).get("value", "")
        if acc and seq:
            by_acc[acc] = seq
    for r in missing:
        r["sequence"] = by_acc.get(r["accession"], "")


def _attach_ena_sequences(results: list) -> None:
    """Populate `sequence` on ENA hits via one comma-separated FASTA request.

    ENA's portal search reports metadata only, which left its rows unexportable
    just like UniProt's.

    Guarded by size: ENA indexes whole genome assemblies as well as genes, and
    a single such record is hundreds of kilobases. Fetching those would blow the
    search's budget and payload for a row nobody can reasonably send to a primer
    design or MSA form, so only gene-scale records are back-filled.
    """
    missing = [r for r in results if not r.get("sequence") and r.get("accession")
               and (r.get("length") or 0) <= _ENA_SEQUENCE_MAX_BP]
    if not missing:
        return
    accessions = [r["accession"] for r in missing][:_ENA_SEQUENCE_MAX_ROWS]
    try:
        resp = requests.get(f"{ENA_BROWSER_API}/fasta/{','.join(accessions)}",
                            headers=HEADERS, timeout=12)
        if resp.status_code in (400, 404):
            return
        resp.raise_for_status()
    except Exception as e:
        logger.debug("ENA batch sequence fetch failed: %s", e)
        return

    # Multi-FASTA: parse header/sequence pairs rather than assume one record.
    # ENA headers are pipe-delimited — ">ENA|LT906637|LT906637.1 description" —
    # so keying on the whole first token never matches a row's accession.
    # Index each record under both its bare and its versioned form.
    by_acc, keys, buf = {}, [], []

    def _register():
        if not keys:
            return
        seq = "".join(buf)
        for k in keys:
            if k:
                by_acc[k] = seq

    for line in resp.text.splitlines():
        if line.startswith(">"):
            _register()
            hdr = line[1:].strip()
            if "|" in hdr:
                parts = hdr.split("|")
                bare = parts[1] if len(parts) > 1 else ""
                ver = parts[2].split()[0] if len(parts) > 2 else ""
            else:
                tokens = hdr.split()
                bare = tokens[0] if tokens else ""
                ver = ""
            keys = [bare, ver]
            buf = []
        elif line.strip():
            buf.append(line.strip())
    _register()

    for r in missing:
        r["sequence"] = (by_acc.get(r["accession"], "")
                         or by_acc.get(r["accession"].split(".")[0], ""))


# ════════════════════════════════════════════════════════════════
# Multi-Search Dispatcher
# ════════════════════════════════════════════════════════════════

DATABASE_REGISTRY = {
    "ncbi_nucleotide": {
        "label": "NCBI Nucleotide",
        "accepts": ["accession", "name"],
        "search": lambda q, org="": _search_ncbi_nucleotide_by_name(q, org),
        "fetch": lambda acc: fetch_ncbi_nucleotide(acc),
    },
    "ncbi_gene": {
        "label": "NCBI Gene",
        "accepts": ["name"],
        "search": lambda q, org="": search_ncbi_gene(q, org or "human"),
        "fetch": None,
    },
    "ensembl": {
        "label": "Ensembl",
        "accepts": ["accession", "name"],
        "search": lambda q, org="": _search_ensembl_by_name(q, org),
        "fetch": lambda acc: fetch_ensembl_sequence(acc),
    },
    "uniprot": {
        "label": "UniProt",
        "accepts": ["accession", "name"],
        "search": lambda q, org="": _search_uniprot_by_name(q),
        "fetch": lambda acc: fetch_uniprot_sequence(acc),
    },
    # DDBJ has no search API: getentry returns "not found" for every format and
    # every accession, and its /search routes 404. It was offered in the UI with
    # "search": None and silently returned nothing, so it is removed rather than
    # advertised. (DDBJ's flatfiles are exchanged through INSDC/ENA, so ENA
    # below surfaces those records under their own accessions.)
    "ena": {
        "label": "ENA",
        "accepts": ["accession", "name"],
        "search": lambda q, org="": _search_ena(q, org),
        "fetch": None,
    },
}


def _search_ncbi_nucleotide_by_name(query: str, organism: str = "") -> list[dict]:
    """
    Search NCBI Nucleotide by gene name/description.

    Uses esearch + esummary (2 calls total). The previous implementation pulled
    a full GenBank record for every one of the 20 hit IDs — up to 41 sequential
    HTTP requests for a single query — which is what pushed name searches past
    the browser timeout and CloudFront's 60s origin timeout.
    """
    _rate_limit_ncbi()
    q = query.strip()
    if detect_input_type(q) == "accession":
        # A bare accession resolves directly against NCBI. Wrapping it in
        # Title/Gene Name clauses matches nothing — RefSeq accessions never
        # appear in those fields — which sent every accession lookup away from
        # the one database that actually holds the record.
        search_query = q
    else:
        org_part = f" AND {organism}[Organism]" if organism else ""
        search_query = f"({q}[Title] OR {q}[Gene Name]){org_part} AND srcdb_refseq[Properties] AND biomol mrna[Properties]"
    params = {"db": "nucleotide", "term": search_query, "retmax": 20, "retmode": "json"}
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    try:
        r = requests.get(f"{NCBI_BASE}esearch.fcgi", params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        ids = r.json().get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        logger.debug("NCBI nucleotide search failed: %s", e)
        return []

    if not ids:
        return []

    # One batched summary call for all hits — no per-ID sequence download.
    _rate_limit_ncbi()
    s_params = {"db": "nucleotide", "id": ",".join(ids[:20]), "retmode": "json"}
    if NCBI_API_KEY:
        s_params["api_key"] = NCBI_API_KEY
    try:
        r2 = requests.get(f"{NCBI_BASE}esummary.fcgi", params=s_params,
                          headers=HEADERS, timeout=15)
        r2.raise_for_status()
        doc = r2.json().get("result", {})
    except Exception as e:
        logger.debug("NCBI nucleotide esummary failed: %s", e)
        return []

    results = []
    for uid in doc.get("uids", []):
        row = doc.get(uid, {})
        acc = row.get("accessionversion") or row.get("caption") or str(uid)
        mol = str(row.get("moltype") or "dna").upper()
        results.append(_make_result({
            "accession":   acc,
            "id":          acc,
            "name":        row.get("caption", ""),
            "description": row.get("title", ""),
            "organism":    row.get("organism", ""),
            "length":      row.get("slen", 0),
            "molecule":    "RNA" if mol == "rna" else "DNA",
        }, "ncbi", acc))
    # Back-fill sequences in one call so "Send to Design / MSA" receives real
    # FASTA instead of header-only records.
    _attach_ncbi_sequences(results, "nuccore")
    return results


def _search_ensembl_by_id(ensembl_id: str) -> list[dict]:
    """Resolve a single Ensembl identifier (ENSG/ENST/ENSP) via /lookup/id."""
    try:
        r = requests.get(f"{ENSEMBL_BASE}/lookup/id/{ensembl_id}",
                         params={"content-type": "application/json"},
                         headers=HEADERS, timeout=10)
        if r.status_code in (400, 404):
            return []
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.debug("Ensembl id lookup failed: %s", e)
        return []
    obj_type = data.get("object_type", "")
    results = [_make_result({
        "id":          data.get("id", ensembl_id),
        "accession":   data.get("id", ensembl_id),
        "name":        data.get("display_name", "") or data.get("id", ""),
        "description": data.get("description", ""),
        "species":     data.get("species", ""),
        "sequence":    "",
        "length":      data.get("end", 0) - data.get("start", 0),
        "molecule":    "protein" if obj_type == "Translation" else "DNA",
    }, "ensembl", ensembl_id)]
    return results


def _search_ensembl_by_name(query: str, organism: str = "human") -> list[dict]:
    """
    Look up a gene symbol in Ensembl, or resolve an Ensembl identifier.

    Non-Ensembl accessions (RefSeq NM_/XM_, UniProt, GenBank…) short-circuit
    here: the symbol endpoint answers 400 for them and the fetcher's retry
    decorator then burned ~6s per search on an answer we already knew.
    """
    q = query.strip()
    if re.match(r"^ENS[A-Z]{0,3}[GTPE]\d", q, re.I):
        return _search_ensembl_by_id(q)
    if detect_input_type(q) == "accession":
        return []

    species_map = {"human": "homo_sapiens", "mouse": "mus_musculus",
                   "rat": "rattus_norvegicus", "zebrafish": "danio_rerio",
                   "fly": "drosophila_melanogaster", "worm": "caenorhabditis_elegans"}
    ens_species = species_map.get(organism.lower(), organism.lower().replace(" ", "_"))

    info = _ensembl_symbol_lookup(query, ens_species)
    if not info or not info.get("gene_id"):
        return []

    results = []
    # Gene-level result
    results.append(_make_result({
        "id": info["gene_id"],
        "accession": info["gene_id"],
        "name": info["symbol"],
        "description": info["description"],
        "species": info["species"],
        "sequence": "",
        "length": info["end"] - info["start"],
        "molecule": "DNA",
    }, "ensembl", info["gene_id"]))

    # Transcript-level results from the same lookup — metadata only. The old
    # code fetched each transcript's full cDNA sequence here (up to 5 extra
    # HTTP calls per search). The sequence is back-filled in one batched POST
    # below instead.
    for t in info.get("transcripts", [])[:5]:
        results.append(_make_result({
            "id": t["id"],
            "accession": t["id"],
            "name": t["name"],
            "description": f"{info['symbol']} transcript {t['name']}",
            "species": info["species"],
            "sequence": "",
            "length": t["length"],
            "molecule": "DNA",
        }, "ensembl", t["id"]))
    _attach_ensembl_sequences(results)
    return results


def _search_uniprot_by_name(query: str) -> list[dict]:
    """Look up a protein by name, or fetch it exactly by UniProt accession."""
    q = query.strip()
    if detect_input_type(q) == "accession":
        # Free-text searching a RefSeq/Ensembl/GenBank accession returns
        # unrelated proteins instead of the nothing they should contribute
        # here — so only ids that actually look like UniProt are fetched.
        if not _is_uniprot_id(q):
            return []
        try:
            r = fetch_uniprot_sequence(q)
        except Exception as e:
            logger.debug("UniProt fetch for %s failed: %s", q, e)
            return []
        return [_make_result({
            "accession":   q,
            "name":        (r.get("gene_names") or [""])[0] or q,
            "entry_name":  r.get("entry_name", ""),
            "description": r.get("protein_name", ""),
            "organism":    r.get("organism", ""),
            "sequence":    r.get("sequence", ""),
            "length":      r.get("length", 0),
            "molecule":    "protein",
        }, "uniprot", q)]

    url = f"{UNIPROT_BASE}/search"
    params = {"query": query, "format": "json", "size": 20}
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
        results = []
        for entry in data.get("results", [])[:20]:
            accession = entry.get("primaryAccession", "")
            gene_names = [gn.get("geneName", {}).get("value", "")
                          for gn in entry.get("genes", []) if gn.get("geneName")]
            results.append(_make_result({
                "id": accession,
                "accession": accession,
                "name": gene_names[0] if gene_names else accession,
                "description": entry.get("proteinDescription", {}).get(
                    "recommendedName", {}).get("fullName", {}).get("value", ""),
                "organism": entry.get("organism", {}).get("scientificName", ""),
                "sequence": "",
                "length": entry.get("sequence", {}).get("length", 0),
                "molecule": "protein",
            }, "uniprot", accession))
        _attach_uniprot_sequences(results)
        return results
    except Exception as e:
        logger.debug("UniProt search failed: %s", e)
        return []


# RefSeq accessions are NCBI-only — they never resolve against ENA, so we skip
# the call instead of waiting on an empty reply.
_REFSEQ_PREFIXES = ("NM_", "XM_", "NR_", "XR_", "NG_", "NC_", "NT_", "NW_",
                    "NZ_", "NP_", "YP_", "WP_")
# ENA's index spans gene-scale records up to whole genome assemblies. Back-fill
# only the former: a 250 Mbp chromosome would dwarf the response and cannot be
# pasted into a primer-design or MSA form anyway.
_ENA_SEQUENCE_MAX_BP = 50_000
# Sized to a full search page (the portal query asks for limit=20) so that no
# row on the results table is left unexportable just because it sorted low.
_ENA_SEQUENCE_MAX_ROWS = 20


def _search_ena(query: str, organism: str = "") -> list[dict]:
    """
    Search the ENA Portal API — a single HTTP call.

    Handles both query shapes: free-text description match for gene names, and
    exact accession match for accessions (ENA carries GenBank/ENA/DDBJ records,
    not RefSeq, so RefSeq accessions are skipped up front).
    """
    q = query.strip()
    if detect_input_type(q) == "accession":
        if q.upper().startswith(_REFSEQ_PREFIXES):
            return []
        clause = f'accession="{q}"'
    else:
        clause = f'description="{q}"'
        if organism:
            clause += f' AND tax_name("{organism}")'

    params = {
        "result": "sequence",
        "query":  clause,
        "fields": "accession,description,scientific_name,base_count",
        "format": "json",
        "limit":  "20",
    }
    try:
        r = requests.get(f"{ENA_BASE}/search", params=params,
                         headers=HEADERS, timeout=15)
        r.raise_for_status()
        rows = r.json()
    except Exception as e:
        logger.debug("ENA search failed: %s", e)
        return []
    if not isinstance(rows, list):
        return []

    results = []
    for row in rows:
        acc = (row.get("accession") or "").strip()
        if not acc:
            continue
        try:
            length = int(row.get("base_count") or 0)
        except (TypeError, ValueError):
            length = 0
        results.append(_make_result({
            "accession":   acc,
            "id":          acc,
            "name":        acc,
            "description": row.get("description", ""),
            "organism":    row.get("scientific_name", ""),
            "length":      length,
            "molecule":    "DNA",
        }, "ena", acc))
    _attach_ena_sequences(results)
    return results


# IUPAC nucleotide (DNA + RNA — U included) and amino-acid alphabets.
_NT_RE = re.compile(r"^[ACGTURYSWKMBDHVN]+$")
_AA_RE = re.compile(r"^[ACDEFGHIKLMNPQRSTVWYBXZJUO*]+$")
# Letters present in the amino-acid alphabet but absent from nucleotide codes.
# Their presence is what separates a protein string from a DNA/RNA string.
_AA_ONLY = frozenset("EFILPQZXJO*")
# Both molecule types share this floor: it keeps short gene symbols (BRCA1,
# TP53) out of the sequence bucket, and is well under NCBI BLAST's minimum
# query length so a detected sequence can actually be searched.
_MIN_SEQUENCE_LEN = 20


def detect_input_type(text: str) -> str:
    """
    Detect whether input is a sequence, accession, or name.
    Returns: 'sequence' | 'accession' | 'name'

    DNA, RNA and protein strings all classify as 'sequence' — the third search
    mode handles all three (BLAST selects blastn vs blastp downstream).
    """
    clean = re.sub(r"\s+", "", text.strip()).upper()
    if len(clean) >= _MIN_SEQUENCE_LEN:
        # Nucleotide is tested first because every nucleotide letter is also a
        # valid amino-acid letter, so ordering decides. U makes RNA count — the
        # old ACGT-only pattern filed RNA as a gene name, and the missing
        # amino-acid pass filed every protein as a gene name too.
        if _NT_RE.fullmatch(clean):
            return "sequence"
        if _AA_RE.fullmatch(clean) and not _AA_ONLY.isdisjoint(clean):
            return "sequence"
    if re.match(r"^(NM_|XM_|NR_|XR_|NG_|NC_|NT_|NW_|NZ_|ENS[GTPE][0-9A-Z]{10}|[A-Z]{1,2}\d{5,}|[OPQ][0-9A-Z]{5}|EPI_ISL_\d+|[A-Z]{2}\d{6})", text.strip(), re.I):
        return "accession"
    return "name"


# ── Result cache ────────────────────────────────────────────────────────────

_search_cache: dict = {}
_search_cache_lock = threading.Lock()
_SEARCH_CACHE_MAX = 64


def _cache_get(key):
    with _search_cache_lock:
        hit = _search_cache.get(key)
        if hit is None:
            return None
        expires, value = hit
        if time.monotonic() >= expires:
            _search_cache.pop(key, None)
            return None
        return value


def _cache_put(key, value) -> None:
    with _search_cache_lock:
        if len(_search_cache) >= _SEARCH_CACHE_MAX:
            oldest = min(_search_cache, key=lambda k: _search_cache[k][0])
            _search_cache.pop(oldest, None)
        _search_cache[key] = (time.monotonic() + SEARCH_CACHE_TTL_S, value)


def _search_one_database(db_name: str, db_info: dict, query: str, organism: str) -> list:
    """Run one database's search and tag every hit with its source."""
    results = db_info["search"](query, organism) or []
    for r in results:
        r["database"] = db_name
        r["database_label"] = db_info["label"]
    return results


def _sequence_search(query: str, organism: str, database: str = "auto") -> dict:
    """
    Type 3 — homology search of a pasted DNA, RNA or protein sequence.

    Delegates to the shared remote-BLAST implementation, which already chooses
    blastn vs blastp from the query itself, then reshapes the hits into the
    uniform schema the result table renders. Hit sequences are back-filled in a
    single batched efetch so the downstream buttons receive real FASTA.
    """
    from primerforge.engine.blast_viewer import run_remote_blast

    seq = re.sub(r"\s+", "", query)
    # BLAST searches a nucleotide or protein index — not the metadata databases
    # the dropdown lists. run_remote_blast switches to a protein index on its own,
    # so "nt" is always the right starting point. Say so rather than appearing to
    # honour a database we did not actually search.
    # swissprot for protein: nr is large enough that a blastp run outlives this
    # request's budget and comes back empty, which reads as "search is broken".
    outcome = run_remote_blast(seq, organism=organism,
                               max_wait=SEARCH_SEQUENCE_BUDGET_S,
                               protein_database="swissprot")
    params = outcome.get("params") or {}
    is_protein = params.get("program") == "blastp"
    warnings = []
    if database not in ("auto", "_all", "ncbi_nucleotide", "ncbi_gene"):
        warnings.append(
            "Homology search runs against NCBI nt/swissprot — the selected "
            "database holds metadata only, so it was not searched."
        )
    if params.get("error"):
        warnings.append(f"BLAST: {params['error']}")

    hits = []
    for h in outcome.get("results", [])[:20]:
        acc = h.get("subject_id", "") or h.get("subject_description", "")
        hit = _make_result({
            "accession":   acc,
            "name":        (h.get("subject_description") or "")[:80],
            "description": h.get("subject_description", ""),
            "organism":    h.get("subject_species", ""),
            "length":      h.get("alignment_length", 0),
            "molecule":    "protein" if is_protein else "DNA",
        }, "ncbi", acc)
        # Homology hits carry alignment evidence the uniform schema has no slot
        # for; keep it alongside, and point "Open ↗" at this BLAST run.
        hit["evalue"] = h.get("e_value", "")
        hit["identity"] = h.get("identity_pct", 0)
        hit["alignment_length"] = h.get("alignment_length", 0)
        if h.get("source_url"):
            hit["source_url"] = h["source_url"]
        # Tag like every other path does. This branch returns before
        # _search_one_database can label the rows, and the table reads
        # r.database per hit — without it the Source column came out blank.
        hit["database"] = "blast"
        hit["database_label"] = "NCBI BLAST"
        hits.append(hit)

    if hits:
        _attach_ncbi_sequences(hits, "protein" if is_protein else "nuccore")

    if not hits:
        if is_protein and params.get("error"):
            # Protein homology against a comprehensive index is not a sub-minute
            # operation for anonymous callers. Measured: NCBI blastp never
            # returned within 2 minutes (blastn on the same wire: 10-20s), and
            # EBI's equivalent ncbiblast job was still RUNNING after 6 minutes.
            # CloudFront cuts this request off near 60s, so a protein search
            # that misses the window must say so — an empty table reads as
            # "your sequence matches nothing", which is a different claim.
            warnings.append(
                "Protein homology search did not finish inside this page's "
                "time limit. NCBI queues anonymous protein (BLASTP) searches "
                "well behind nucleotide ones, so they often need several "
                "minutes. DNA and RNA sequences work normally here; for "
                "protein, use the BLAST page (/blast), which allows up to "
                "2 minutes."
            )
        elif not warnings:
            warnings.append("BLAST found no homologous sequences for this query.")

    return {
        "results": hits[:50],
        "total": len(hits),
        "query": query,
        "query_type": "sequence",
        "database": "blast",
        "databases_searched": ["blast"],
        "warnings": warnings,
    }


def search_databases(query: str, database: str = "auto", organism: str = "human",
                     input_type: str = None, budget_s: float = None) -> dict:
    """
    Search one or all databases for the given query.

    query:      gene name, accession, or sequence text
    database:   a specific DB name, or "auto"/"_all" to search everything
    organism:   organism name used for NCBI/Ensembl/ENA filtering
    input_type: optional override for detect_input_type(). The browser knows
                which box the user typed into, so its choice wins over guessing.
    budget_s:   wall-clock ceiling for the fan-out (defaults to SEARCH_BUDGET_S)

    Returns: {results, total, query, query_type, database,
              databases_searched, warnings}
    """
    query_type = input_type or detect_input_type(query)

    # A pasted sequence is a homology question, not a metadata lookup — send it
    # to BLAST instead of sweeping every registry entry with the wrong tool.
    if query_type == "sequence":
        return _sequence_search(query, organism, database)

    cache_key = (query.strip().lower(), database, organism, query_type)
    cached = _cache_get(cache_key)
    if cached is not None:
        return dict(cached, results=list(cached["results"]))

    budget = SEARCH_BUDGET_S if budget_s is None else float(budget_s)
    if database in ("auto", "_all"):
        databases = list(DATABASE_REGISTRY.keys())
    else:
        databases = [database]

    errors = []
    runnable = []
    for db_name in databases:
        db_info = DATABASE_REGISTRY.get(db_name)
        if db_info is None:
            errors.append(f"{db_name}: unknown database")
            continue
        if query_type not in db_info.get("accepts", []):
            continue
        if not db_info.get("search"):
            errors.append(f"{db_info['label']}: search unavailable for this input")
            continue
        runnable.append((db_name, db_info))

    all_results = []
    searched = [name for name, _ in runnable]

    if runnable:
        # Fan out concurrently and hold the whole sweep to ONE deadline. The
        # original loop was serial and had no time limit at all, so a single
        # slow upstream — or the dozen round trips each fetcher used to make —
        # could push the request past the browser's 30s abort and then past
        # CloudFront's ~60s origin timeout, which surfaced as a 504.
        end = time.monotonic() + budget
        collected = {}
        executor = ThreadPoolExecutor(max_workers=min(4, len(runnable)),
                                      thread_name_prefix="seqsearch")
        futures = {executor.submit(_search_one_database, n, i, query, organism): n
                   for n, i in runnable}
        try:
            for fut in as_completed(futures, timeout=max(0.5, end - time.monotonic())):
                name = futures[fut]
                try:
                    collected[name] = fut.result()
                except Exception as e:
                    msg = str(e).strip() or type(e).__name__
                    errors.append(f"{name}: {type(e).__name__}: {msg[:140]}")
                    logger.warning("Search %s failed: %s", name, e)
        except FuturesTimeoutError:
            pass
        # Anything still pending has outlived the budget. Say so rather than
        # silently dropping a database; its own HTTP timeouts reap the thread.
        for fut, name in futures.items():
            if not fut.done() and not fut.cancelled():
                errors.append(f"{name}: skipped — exceeded {budget:.0f}s time budget")
        executor.shutdown(wait=False, cancel_futures=True)

        # Reassemble in registry order. Futures land in completion order, which
        # varies run to run — without this the table reshuffles itself between
        # two identical searches.
        for name in searched:
            all_results.extend(collected.get(name, []))

    payload = {
        "results": all_results[:50],
        "total": len(all_results),
        "query": query,
        "query_type": query_type,
        "database": database,
        "databases_searched": searched,
        "warnings": errors,
    }
    # Cache only clean, non-empty sweeps. Several fetchers return [] on an
    # upstream failure, so caching an empty answer would pin a transient outage
    # for the whole TTL and stop a healthy database from being retried.
    if not errors and all_results:
        _cache_put(cache_key, payload)
    return payload

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
    "ddbj": {
        "label": "DDBJ",
        "accepts": ["accession"],
        "search": None,
        "fetch": None,
    },
    "ena": {
        "label": "ENA",
        "accepts": ["accession"],
        "search": None,
        "fetch": None,
    },
}


def _search_ncbi_nucleotide_by_name(query: str, organism: str = "") -> List[Dict]:
    """Search NCBI Nucleotide database by gene name/description."""
    _rate_limit_ncbi()
    org_part = f" AND {organism}[Organism]" if organism else ""
    search_query = f"({query}[Title] OR {query}[Gene Name]){org_part} AND srcdb_refseq[Properties] AND biomol mrna[Properties]"
    params = {"db": "nucleotide", "term": search_query, "retmax": 20, "retmode": "json"}
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    try:
        r = requests.get(f"{NCBI_BASE}esearch.fcgi", params=params, headers=HEADERS, timeout=20)
        r.raise_for_status()
        ids = r.json().get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        logger.debug(f"NCBI nucleotide search failed: {e}")
        return []

    if not ids:
        return []

    # Fetch summaries for each hit
    results = []
    for gid in ids[:20]:
        try:
            data = fetch_ncbi_nucleotide(gid)
            results.append(_make_result(data, "ncbi", gid))
        except Exception as e:
            logger.debug(f"Failed to fetch {gid}: {e}")
            continue
    return results


def _search_ensembl_by_name(query: str, organism: str = "human") -> List[Dict]:
    """Search Ensembl by gene symbol."""
    species_map = {"human": "homo_sapiens", "mouse": "mus_musculus",
                   "rat": "rattus_norvegicus", "zebrafish": "danio_rerio",
                   "fly": "drosophila_melanogaster", "worm": "caenorhabditis_elegans"}
    ens_species = species_map.get(organism.lower(), organism.lower().replace(" ", "_"))
    try:
        info = fetch_ensembl_gene_info(query, species=ens_species)
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

        # Transcript-level results
        for t in info.get("transcripts", [])[:5]:
            try:
                seq_data = fetch_ensembl_sequence(t["id"], seq_type="cdna")
                results.append(_make_result({
                    "id": t["id"],
                    "accession": t["id"],
                    "name": t["name"],
                    "description": f"{info['symbol']} transcript {t['name']}",
                    "species": info["species"],
                    "sequence": seq_data["seq"],
                    "length": t["length"],
                    "molecule": "DNA",
                }, "ensembl", t["id"]))
            except Exception:
                continue
        return results
    except Exception as e:
        logger.debug(f"Ensembl search failed: {e}")
        return []


def _search_uniprot_by_name(query: str) -> List[Dict]:
    """Search UniProt by gene/protein name."""
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
        return results
    except Exception as e:
        logger.debug(f"UniProt search failed: {e}")
        return []


def detect_input_type(text: str) -> str:
    """
    Detect whether input is a sequence, accession, or name.
    Returns: 'sequence' | 'accession' | 'name'
    """
    clean = text.strip().upper().replace(" ", "").replace("\n", "").replace("\r", "")
    if re.match(r"^[ACGTNRYSWKMBDHVacgtnryswkmbdhv\s]+$", text.strip()):
        if len(clean) >= 20:
            return "sequence"
    if re.match(r"^(NM_|XM_|NR_|XR_|NG_|NC_|NT_|NW_|ENS[GTPE][0-9A-Z]{10}|[A-Z]{1,2}\d{5,}|[OPQ][0-9A-Z]{5}|EPI_ISL_\d+|[A-Z]{2}\d{6})", text.strip(), re.I):
        return "accession"
    return "name"


def search_databases(query: str, database: str = "auto", organism: str = "human") -> Dict:
    """
    Search one or all databases for the given query.
    query: gene name, accession, or sequence text
    database: specific DB name or "auto" to detect
    organism: organism name for NCBI filtering
    Returns: {results: [...], total: N, source: str, query_type: str}
    """
    query_type = detect_input_type(query)
    all_results = []

    if database == "auto" or database == "_all":
        databases = list(DATABASE_REGISTRY.keys())
    else:
        databases = [database]

    for db_name in databases:
        db_info = DATABASE_REGISTRY.get(db_name)
        if not db_info or query_type not in db_info.get("accepts", []):
            continue
        try:
            if db_info["search"]:
                results = db_info["search"](query, organism)
                for r in results:
                    r["database"] = db_name
                    r["database_label"] = db_info["label"]
                all_results.extend(results)
        except Exception as e:
            logger.debug(f"Search {db_name} failed: {e}")
            continue

    return {
        "results": all_results[:50],
        "total": len(all_results),
        "query": query,
        "query_type": query_type,
        "database": database,
        "databases_searched": databases,
    }

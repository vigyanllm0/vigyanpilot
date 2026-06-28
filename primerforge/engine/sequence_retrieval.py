"""
Sequence Retrieval Service
============================
Unified interface for fetching genomic sequences from multiple databases:
- NCBI (RefSeq / GenBank via Entrez)
- Ensembl / GENCODE (REST API)
- NCBI Virus (via NCBI Nucleotide records)
- ENA (EBI REST API)
- DDBJ (REST API)

Input parsing supports:
- NCBI accession patterns (NM_, NR_, XM_, XR_, NC_, NG_, NT_, NW_)
- Ensembl stable IDs (ENS + optional species prefix + G/T/E/P + 11 digits)
- Genomic coordinates (chr[N]:[start]-[end]) via Ensembl region sequence
- HGNC gene symbols (resolved via NCBI Gene database)

Pattern precedence: NCBI → Ensembl → coordinate → HGNC gene symbol.
Max 50 queries per request, 256 chars per query, whitespace trimmed.

Results are normalized to a common SequenceRecord dataclass.
"""

import os
import re
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

MAX_QUERIES_PER_REQUEST = 50
MAX_INPUT_LENGTH = 256

# Supported input formats (for error messages)
SUPPORTED_FORMATS = [
    "NCBI accession (NM_, NR_, XM_, XR_, NC_, NG_, NT_, NW_ followed by digits and optional .version)",
    "Ensembl stable ID (ENS + optional species prefix + G/T/E/P + 11 digits)",
    "DDBJ accession (AB, LC, AP, BA, HT followed by 6 digits)",
    "ENA/EMBL accession (2 uppercase letters followed by 6+ digits)",
    "UniProt ID (P/Q/O followed by 5 alphanumeric characters)",
    "Genomic coordinate (chr[1-22|X|Y|M|MT]:[start]-[end])",
    "HGNC gene symbol (1-40 alphanumeric characters and hyphens, e.g., BRCA1, TP53)",
]


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SequenceRecord:
    """Normalized sequence record from any source."""
    id: str
    source: str  # ncbi | ncbi_virus | ensembl | ensembl_region | ena | ddbj | ncbi_gene
    accession: str
    sequence: str
    description: str = ""
    length: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    exon_map: List[Dict[str, Any]] = field(default_factory=list)
    transcripts: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if self.length == 0 and self.sequence:
            self.length = len(self.sequence)


@dataclass
class InputParseResult:
    """Result of parsing and classifying a single input query."""
    query: str
    input_type: str  # ncbi_accession | ensembl_id | genomic_coordinate | gene_symbol | invalid
    source: str  # ncbi | ensembl | ensembl_region | ncbi_gene | invalid
    error: Optional[str] = None


@dataclass
class ValidationError:
    """Validation error for an input query."""
    query: str
    error: str
    supported_formats: List[str] = field(default_factory=lambda: list(SUPPORTED_FORMATS))


# ═══════════════════════════════════════════════════════════════════════════
# INPUT PATTERNS (ordered by precedence)
# ═══════════════════════════════════════════════════════════════════════════

# 1. NCBI accession: NM_, NR_, XM_, XR_, NC_, NG_, NT_, NW_ + digits + optional .version
_NCBI_PATTERN = re.compile(
    r"^(NM|NR|XM|XR|NC|NG|NT|NW)_\d+(\.\d+)?$",
    re.IGNORECASE
)

# 2. Ensembl stable ID: ENS + optional species prefix (uppercase letters) + feature type + 11 digits
_ENSEMBL_PATTERN = re.compile(
    r"^ENS[A-Z]*[GTEP]\d{11}(\.\d+)?$",
    re.IGNORECASE
)

# 3. Genomic coordinate: chr[N]:[start]-[end]
_COORDINATE_PATTERN = re.compile(
    r"^chr(1[0-9]|2[0-2]|[1-9]|X|Y|M|MT):(\d+)-(\d+)$",
    re.IGNORECASE
)

# 4. HGNC gene symbol: 1-40 alphanumeric characters + hyphens
_GENE_SYMBOL_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9\-]{0,39}$"
)

# ═══════════════════════════════════════════════════════════════════════════
# SOURCE-SPECIFIC FETCHERS
# ═══════════════════════════════════════════════════════════════════════════

def fetch_from_ncbi(accession: str, **kwargs) -> SequenceRecord:
    """
    Fetch sequence from NCBI RefSeq/GenBank via Entrez API.

    Args:
        accession: NCBI accession (e.g., NM_001301717.2, NC_000017.11)

    Returns:
        SequenceRecord with populated fields.
    """
    logger.info("Fetching from NCBI: %s", accession)

    try:
        from Bio import Entrez, SeqIO

        Entrez.email = os.environ.get("NCBI_EMAIL", "user@example.com")
        api_key = os.environ.get("NCBI_API_KEY", "")
        if api_key:
            Entrez.api_key = api_key

        handle = Entrez.efetch(db="nucleotide", id=accession, rettype="gb", retmode="text")
        record = SeqIO.read(handle, "genbank")
        handle.close()

        seq_str = str(record.seq)
        exon_map = []
        transcripts = []

        for feature in record.features:
            if feature.type == "exon":
                exon_map.append({
                    "start": int(feature.location.start),
                    "end": int(feature.location.end),
                    "strand": feature.location.strand,
                })
            elif feature.type == "mRNA":
                transcripts.append({
                    "start": int(feature.location.start),
                    "end": int(feature.location.end),
                })

        return SequenceRecord(
            id=accession,
            source="ncbi",
            accession=record.id,
            sequence=seq_str,
            description=record.description or "",
            length=len(seq_str),
            metadata={
                "molecule_type": record.annotations.get("molecule_type", "DNA"),
                "organism": record.annotations.get("organism", ""),
            },
            exon_map=exon_map,
            transcripts=transcripts,
        )
    except Exception as e:
        logger.error("NCBI fetch failed for %s: %s", accession, e)
        raise RuntimeError(f"NCBI fetch failed: {e}")


def fetch_from_ensembl(gene_id: str, **kwargs) -> SequenceRecord:
    """
    Fetch sequence and annotations from Ensembl/GENCODE REST API.

    Args:
        gene_id: Ensembl gene/transcript ID (e.g., ENSG00000141510, ENST00000269305)

    Returns:
        SequenceRecord with transcript and exon annotations.
    """
    logger.info("Fetching from Ensembl: %s", gene_id)
    import requests

    base_url = "https://rest.ensembl.org"

    try:
        # Fetch sequence
        seq_r = requests.get(
            f"{base_url}/sequence/id/{gene_id}",
            headers={"Content-Type": "application/json"},
            params={"type": "genomic"},
            timeout=15,
        )
        seq_r.raise_for_status()
        seq_data = seq_r.json()

        sequence = seq_data.get("seq", "")
        description = seq_data.get("desc", "")

        # Fetch exon info if it's a transcript
        exon_map = []
        transcripts = []
        if gene_id.upper().startswith("ENST"):
            exon_r = requests.get(
                f"{base_url}/overlap/id/{gene_id}",
                headers={"Content-Type": "application/json"},
                params={"feature": "exon"},
                timeout=15,
            )
            if exon_r.status_code == 200:
                for exon in exon_r.json():
                    exon_map.append({
                        "start": exon.get("start", 0),
                        "end": exon.get("end", 0),
                        "strand": exon.get("strand", 1),
                    })

        return SequenceRecord(
            id=gene_id,
            source="ensembl",
            accession=gene_id,
            sequence=sequence,
            description=description,
            length=len(sequence),
            metadata={
                "assembly": seq_data.get("assembly_name", ""),
                "molecule_type": seq_data.get("molecule", "dna"),
            },
            exon_map=exon_map,
            transcripts=transcripts,
        )
    except Exception as e:
        logger.error("Ensembl fetch failed for %s: %s", gene_id, e)
        raise RuntimeError(f"Ensembl fetch failed: {e}")


def fetch_from_ncbi_virus(accession: str, **kwargs) -> SequenceRecord:
    """
    Fetch an open viral accession through NCBI Nucleotide and mark it as NCBI Virus.

    Args:
        accession: NCBI viral accession (e.g., NC_045512.2)
    """
    record = fetch_from_ncbi(accession, **kwargs)
    record.source = "ncbi_virus"
    record.metadata["api"] = "ncbi_nucleotide"
    record.metadata["collection"] = "NCBI Virus"
    return record


def fetch_from_ensembl_region(query: str, **kwargs) -> SequenceRecord:
    """
    Fetch genomic coordinates from Ensembl's public region sequence endpoint.

    Args:
        query: Coordinate string (e.g., chr17:7668402-7687538)
    """
    logger.info("Fetching Ensembl region: %s", query)
    import requests

    try:
        clean_query = query.replace(",", "").strip()
        chrom, positions = clean_query.split(":")
        start_s, end_s = positions.split("-")
        chrom_name = chrom[3:] if chrom.lower().startswith("chr") else chrom
        if chrom_name.upper() == "M":
            chrom_name = "MT"
        start = int(start_s)
        end = int(end_s)
        species = kwargs.get("species", "human")
        assembly = kwargs.get("assembly", "GRCh38")

        region = f"{chrom_name}:{start}..{end}:1"
        url = f"https://rest.ensembl.org/sequence/region/{species}/{region}"
        r = requests.get(
            url,
            headers={"Content-Type": "application/json"},
            params={"coord_system_version": assembly},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()

        sequence = data.get("seq", "").upper()

        return SequenceRecord(
            id=query,
            source="ensembl_region",
            accession=query,
            sequence=sequence,
            description=data.get("desc", f"{assembly} {query}"),
            length=len(sequence),
            metadata={
                "api": "rest.ensembl.org",
                "assembly": assembly,
                "chrom": chrom,
                "start": start,
                "end": end,
                "species": species,
            },
        )
    except Exception as e:
        logger.error("Ensembl region fetch failed for %s: %s", query, e)
        raise RuntimeError(f"Ensembl region fetch failed: {e}")


def fetch_from_ena(accession: str, **kwargs) -> SequenceRecord:
    """
    Fetch sequence from ENA (European Nucleotide Archive) REST API.

    Args:
        accession: ENA accession (e.g., A00001, LR792597.1)
    """
    logger.info("Fetching from ENA: %s", accession)
    import requests

    try:
        url = f"https://www.ebi.ac.uk/ena/browser/api/fasta/{accession}"
        r = requests.get(url, timeout=15)
        r.raise_for_status()

        # Parse FASTA
        lines = r.text.strip().split("\n")
        description = lines[0][1:] if lines[0].startswith(">") else ""
        sequence = "".join(l.strip() for l in lines[1:] if not l.startswith(">")).upper()

        return SequenceRecord(
            id=accession,
            source="ena",
            accession=accession,
            sequence=sequence,
            description=description,
            length=len(sequence),
            metadata={"api": "ebi.ac.uk/ena"},
        )
    except Exception as e:
        logger.error("ENA fetch failed for %s: %s", accession, e)
        raise RuntimeError(f"ENA fetch failed: {e}")


def fetch_from_ddbj(accession: str, **kwargs) -> SequenceRecord:
    """
    Fetch sequence from DDBJ (DNA Data Bank of Japan) REST API.

    Args:
        accession: DDBJ accession (e.g., AB000001, LC000001)
    """
    logger.info("Fetching from DDBJ: %s", accession)
    import requests

    try:
        url = f"https://getentry.ddbj.nig.ac.jp/getentry/na/{accession}?format=fasta&filetype=text"
        r = requests.get(url, timeout=15)
        r.raise_for_status()

        lines = r.text.strip().split("\n")
        description = lines[0][1:] if lines[0].startswith(">") else ""
        sequence = "".join(l.strip() for l in lines[1:] if not l.startswith(">")).upper()

        return SequenceRecord(
            id=accession,
            source="ddbj",
            accession=accession,
            sequence=sequence,
            description=description,
            length=len(sequence),
            metadata={"api": "getentry.ddbj.nig.ac.jp"},
        )
    except Exception as e:
        logger.error("DDBJ fetch failed for %s: %s", accession, e)
        raise RuntimeError(f"DDBJ fetch failed: {e}")


def resolve_gene_symbol(symbol: str, **kwargs) -> SequenceRecord:
    """
    Resolve an HGNC gene symbol to a sequence via NCBI Gene database.

    Searches NCBI Gene for the symbol, retrieves the canonical RefSeq
    transcript accession, then fetches the sequence from NCBI Nucleotide.

    Args:
        symbol: HGNC gene symbol (e.g., BRCA1, TP53, EGFR)

    Returns:
        SequenceRecord from the resolved NCBI accession.

    Raises:
        RuntimeError: If the gene symbol cannot be resolved.
    """
    logger.info("Resolving gene symbol via NCBI Gene: %s", symbol)

    try:
        from Bio import Entrez

        Entrez.email = os.environ.get("NCBI_EMAIL", "user@example.com")
        api_key = os.environ.get("NCBI_API_KEY", "")
        if api_key:
            Entrez.api_key = api_key

        # Search NCBI Gene database for the symbol
        handle = Entrez.esearch(
            db="gene",
            term=f"{symbol}[Gene Name] AND Homo sapiens[Organism]",
            retmax=1,
        )
        search_results = Entrez.read(handle)
        handle.close()

        gene_ids = search_results.get("IdList", [])
        if not gene_ids:
            raise RuntimeError(
                f"Gene symbol '{symbol}' not found in NCBI Gene database"
            )

        gene_id = gene_ids[0]

        # Fetch gene record to find RefSeq transcript
        handle = Entrez.efetch(db="gene", id=gene_id, rettype="gene_table", retmode="text")
        gene_data = handle.read()
        handle.close()

        # Try to extract canonical RefSeq mRNA accession (NM_)
        refseq_match = re.search(r"(NM_\d+\.\d+)", gene_data)
        if not refseq_match:
            # Fallback: try any RefSeq accession
            refseq_match = re.search(r"((NM|NR|XM|XR)_\d+(\.\d+)?)", gene_data)

        if refseq_match:
            accession = refseq_match.group(1)
            logger.info("Resolved %s to accession %s", symbol, accession)
            record = fetch_from_ncbi(accession, **kwargs)
            record.metadata["resolved_from_symbol"] = symbol
            record.metadata["ncbi_gene_id"] = gene_id
            return record

        # If no RefSeq found, try to get genomic sequence via gene ID
        # Use Entrez elink to find associated nucleotide records
        handle = Entrez.elink(dbfrom="gene", db="nucleotide", id=gene_id)
        link_results = Entrez.read(handle)
        handle.close()

        nuc_ids = []
        for linkset in link_results:
            for link_db in linkset.get("LinkSetDb", []):
                for link in link_db.get("Link", []):
                    nuc_ids.append(link["Id"])

        if nuc_ids:
            # Fetch the first linked nucleotide record
            record = fetch_from_ncbi(nuc_ids[0], **kwargs)
            record.metadata["resolved_from_symbol"] = symbol
            record.metadata["ncbi_gene_id"] = gene_id
            return record

        raise RuntimeError(
            f"Gene symbol '{symbol}' found (Gene ID: {gene_id}) but no "
            f"associated RefSeq transcript could be identified"
        )
    except RuntimeError:
        raise
    except Exception as e:
        logger.error("Gene symbol resolution failed for %s: %s", symbol, e)
        raise RuntimeError(f"Gene symbol resolution failed for '{symbol}': {e}")


# ═══════════════════════════════════════════════════════════════════════════
# INPUT PARSING AND CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════

def classify_input(query: str) -> InputParseResult:
    """
    Classify a single input query string by pattern matching.

    Applies pattern precedence: NCBI accession → Ensembl stable ID →
    genomic coordinate → HGNC gene symbol.

    Args:
        query: Trimmed input string to classify.

    Returns:
        InputParseResult with input_type and source, or error details.
    """
    # 1. NCBI accession (highest precedence)
    if _NCBI_PATTERN.match(query):
        return InputParseResult(
            query=query,
            input_type="ncbi_accession",
            source="ncbi",
        )

    # 2. Ensembl stable ID
    if _ENSEMBL_PATTERN.match(query):
        return InputParseResult(
            query=query,
            input_type="ensembl_id",
            source="ensembl",
        )

    # 3. DDBJ accession (AB, LC, AP, BA, HT + 6 digits)
    if re.match(r"^(AB|LC|AP|BA|HT)\d{6}(\.\d+)?$", query, re.IGNORECASE):
        return InputParseResult(
            query=query,
            input_type="ddbj_accession",
            source="ddbj",
        )

    # 4. ENA/EMBL accession (2 uppercase letters + 6+ digits, excluding UniProt)
    if re.match(r"^[A-Z]{2}\d{6,}(\.\d+)?$", query, re.IGNORECASE) and \
       not re.match(r"^[PQO][0-9A-Z]{5}$", query):
        return InputParseResult(
            query=query,
            input_type="ena_accession",
            source="ena",
        )

    # 5. UniProt accession (P/Q/O + 5 digits)
    if re.match(r"^[PQO][0-9A-Z]{5}$", query):
        return InputParseResult(
            query=query,
            input_type="uniprot_id",
            source="uniprot",
        )

    # 6. Genomic coordinate
    coord_match = _COORDINATE_PATTERN.match(query)
    if coord_match:
        start = int(coord_match.group(2))
        end = int(coord_match.group(3))
        if start >= end:
            return InputParseResult(
                query=query,
                input_type="invalid",
                source="invalid",
                error=f"Invalid genomic coordinate: start ({start}) must be less than end ({end})",
            )
        return InputParseResult(
            query=query,
            input_type="genomic_coordinate",
            source="ensembl_region",
        )

    # 7. HGNC gene symbol (fallback)
    if _GENE_SYMBOL_PATTERN.match(query):
        return InputParseResult(
            query=query,
            input_type="gene_symbol",
            source="ncbi_gene",
        )

    # Unrecognized format
    return InputParseResult(
        query=query,
        input_type="invalid",
        source="invalid",
        error=(
            f"Unrecognized input format: '{query}'. "
            f"Supported formats: {', '.join(SUPPORTED_FORMATS)}"
        ),
    )


def validate_input(query: str) -> Tuple[str, Optional[str]]:
    """
    Validate and sanitize a single input query string.

    Returns:
        Tuple of (trimmed_query, error_message_or_None).
    """
    if not query or not isinstance(query, str):
        return "", "Input query must be a non-empty string"

    trimmed = query.strip()

    if not trimmed:
        return "", "Input query is empty after trimming whitespace"

    if len(trimmed) > MAX_INPUT_LENGTH:
        return trimmed, (
            f"Input query exceeds maximum length of {MAX_INPUT_LENGTH} characters "
            f"(got {len(trimmed)} characters)"
        )

    return trimmed, None


def validate_batch(queries: List[str]) -> Tuple[List[str], List[ValidationError]]:
    """
    Validate a batch of input queries.

    Enforces max 50 queries per request, trims whitespace, validates length.

    Args:
        queries: List of query strings.

    Returns:
        Tuple of (valid_trimmed_queries, validation_errors).
    """
    errors: List[ValidationError] = []

    if not queries:
        errors.append(ValidationError(
            query="",
            error="No queries provided. At least one query is required.",
        ))
        return [], errors

    if len(queries) > MAX_QUERIES_PER_REQUEST:
        errors.append(ValidationError(
            query="",
            error=(
                f"Too many queries: {len(queries)} provided, "
                f"maximum is {MAX_QUERIES_PER_REQUEST} per request"
            ),
        ))
        return [], errors

    valid_queries: List[str] = []
    for raw_query in queries:
        trimmed, error = validate_input(raw_query)
        if error:
            errors.append(ValidationError(query=raw_query or "", error=error))
        else:
            valid_queries.append(trimmed)

    return valid_queries, errors


def parse_queries(queries: List[str]) -> Tuple[List[InputParseResult], List[ValidationError]]:
    """
    Parse and classify a batch of input queries.

    Validates the batch, trims whitespace, enforces limits, and classifies
    each query by pattern precedence.

    Args:
        queries: List of raw query strings.

    Returns:
        Tuple of (parse_results_for_valid_queries, validation_errors).
    """
    valid_queries, errors = validate_batch(queries)

    results: List[InputParseResult] = []
    for query in valid_queries:
        result = classify_input(query)
        if result.input_type == "invalid":
            errors.append(ValidationError(
                query=query,
                error=result.error or f"Unrecognized format: '{query}'",
            ))
        else:
            results.append(result)

    return results, errors


# ═══════════════════════════════════════════════════════════════════════════
# UNIFIED FETCH INTERFACE
# ═══════════════════════════════════════════════════════════════════════════

# Legacy patterns for backward compatibility with detect_source()
_SOURCE_PATTERNS = [
    # NCBI RefSeq: NM_, NR_, XM_, XR_, NC_, NG_, NT_, NW_ + digits + optional .version
    (re.compile(r"^(NM|NR|XM|XR|NC|NG|NT|NW)_\d+(\.\d+)?$", re.IGNORECASE), "ncbi"),
    # Ensembl: ENS + optional species prefix + GTEP + 11 digits
    (re.compile(r"^ENS[A-Z]*[GTEP]\d{11}(\.\d+)?$", re.IGNORECASE), "ensembl"),
    # Ensembl region coordinate format: chr[1-22|X|Y|M|MT]:start-end
    (re.compile(r"^chr(1[0-9]|2[0-2]|[1-9]|X|Y|M|MT):(\d+)-(\d+)$", re.IGNORECASE), "ensembl_region"),
    # ENA accessions (typical patterns)
    (re.compile(r"^[A-Z]{2}\d{6,}", re.IGNORECASE), "ena"),
    # DDBJ — prefixes AB, LC, AP, etc.
    (re.compile(r"^(AB|LC|AP|BA|HT)\d{6}", re.IGNORECASE), "ddbj"),
]

_FETCHER_MAP = {
    "ncbi": fetch_from_ncbi,
    "ncbi_virus": fetch_from_ncbi_virus,
    "ensembl": fetch_from_ensembl,
    "ensembl_region": fetch_from_ensembl_region,
    "ena": fetch_from_ena,
    "ddbj": fetch_from_ddbj,
    "ncbi_gene": resolve_gene_symbol,
}


def detect_source(query: str) -> Optional[str]:
    """
    Auto-detect the database source from the query format.

    Uses the upgraded pattern precedence:
    NCBI accession → Ensembl → coordinate → gene symbol.

    Returns:
        Source name string or None if unrecognized.
    """
    trimmed = query.strip()

    # Check against ordered patterns first
    for pattern, source in _SOURCE_PATTERNS:
        if pattern.match(trimmed):
            return source

    # Fallback: check if it looks like a gene symbol
    if _GENE_SYMBOL_PATTERN.match(trimmed):
        return "ncbi_gene"

    return None


def fetch_sequence(query: str, source: str = "auto", **kwargs) -> SequenceRecord:
    """
    Unified sequence fetcher with auto-detection of source database.

    Args:
        query: Accession, gene ID, coordinate string, or gene symbol.
        source: One of 'ncbi', 'ncbi_virus', 'ensembl', 'ensembl_region',
                'ena', 'ddbj', 'ncbi_gene', or 'auto'.
                If 'auto', the source is inferred from the query format.

    Returns:
        SequenceRecord from the appropriate database.

    Raises:
        ValueError: If query validation fails, source is 'auto' and cannot
                    be detected, or if an unknown source is specified.
    """
    # Validate single input
    trimmed, error = validate_input(query)
    if error:
        raise ValueError(error)

    if source == "auto":
        detected = detect_source(trimmed)
        if detected is None:
            raise ValueError(
                f"Cannot auto-detect source for query '{trimmed}'. "
                f"Input does not match any recognized format. "
                f"Supported formats: {', '.join(SUPPORTED_FORMATS)}"
            )
        source = detected

    fetcher = _FETCHER_MAP.get(source)
    if fetcher is None:
        raise ValueError(
            f"Unknown source '{source}'. "
            f"Available sources: {list(_FETCHER_MAP.keys())}"
        )

    logger.info("fetch_sequence: query=%s, source=%s", trimmed, source)
    return fetcher(trimmed, **kwargs)


def fetch_sequences(queries: List[str], **kwargs) -> Tuple[List[SequenceRecord], List[ValidationError]]:
    """
    Fetch sequences for a batch of queries with validation and classification.

    Validates the batch (max 50 queries, 256 chars per query, whitespace trimming),
    classifies each query by pattern precedence, and fetches from the appropriate source.

    Args:
        queries: List of raw query strings.
        **kwargs: Additional keyword arguments passed to individual fetchers.

    Returns:
        Tuple of (successful_records, errors).
    """
    parse_results, errors = parse_queries(queries)

    records: List[SequenceRecord] = []
    for result in parse_results:
        fetcher = _FETCHER_MAP.get(result.source)
        if fetcher is None:
            errors.append(ValidationError(
                query=result.query,
                error=f"No fetcher available for source '{result.source}'",
            ))
            continue

        try:
            record = fetcher(result.query, **kwargs)
            records.append(record)
        except Exception as e:
            errors.append(ValidationError(
                query=result.query,
                error=f"Fetch failed from {result.source}: {str(e)}",
            ))

    return records, errors


# ═══════════════════════════════════════════════════════════════════════════
# ASYNC EXECUTION WITH RETRY AND TIMEOUT
# Requirements: 26.3, 26.4, 26.5
# ═══════════════════════════════════════════════════════════════════════════

import asyncio
import time as _time
from concurrent.futures import ThreadPoolExecutor

# Thread pool for running blocking fetchers in async context
_executor = ThreadPoolExecutor(max_workers=8)

# Default retry/timeout configuration
DEFAULT_TIMEOUT_S = 30
DEFAULT_MAX_RETRIES = 3
CACHE_TTL_DAYS = 7


async def fetch_sequence_async(
    query: str,
    source: str = "auto",
    timeout_s: int = DEFAULT_TIMEOUT_S,
    max_retries: int = DEFAULT_MAX_RETRIES,
    **kwargs,
) -> SequenceRecord:
    """
    Async wrapper around fetch_sequence with cache, retry, and per-source timeout.

    Checks sequence_cache (7-day TTL) before making external calls.
    On cache miss, fetches with exponential backoff retry (1s, 2s, 4s)
    and per-source timeout enforcement.

    Args:
        query: Accession, gene ID, coordinate string, or gene symbol.
        source: One of 'ncbi', 'ncbi_virus', 'ensembl', 'ensembl_region',
                'ena', 'ddbj', 'ncbi_gene', or 'auto'.
        timeout_s: Per-source timeout in seconds (default 30).
        max_retries: Maximum retry attempts (default 3).
        **kwargs: Additional arguments passed to the underlying fetcher.

    Returns:
        SequenceRecord from cache or the appropriate source database.

    Raises:
        RuntimeError: If all retries are exhausted or timeout exceeded.
        ValueError: If query validation fails.
    """
    from .sequence_cache import get_cached, store_cached

    # Validate and resolve source early
    trimmed, error = validate_input(query)
    if error:
        raise ValueError(error)

    if source == "auto":
        detected = detect_source(trimmed)
        if detected is None:
            raise ValueError(
                f"Cannot auto-detect source for query '{trimmed}'. "
                f"Input does not match any recognized format. "
                f"Supported formats: {', '.join(SUPPORTED_FORMATS)}"
            )
        source = detected

    # Check cache first (7-day TTL enforced by sequence_cache module)
    cached = get_cached(source, trimmed)
    if cached and cached.sequence:
        logger.info("fetch_sequence_async: cache HIT for %s/%s", source, trimmed)
        return cached

    # Cache miss — fetch with retry and timeout
    logger.info(
        "fetch_sequence_async: cache MISS for %s/%s — fetching with retries",
        source, trimmed,
    )

    last_exception: Optional[Exception] = None
    loop = asyncio.get_event_loop()

    for attempt in range(1, max_retries + 1):
        try:
            # Run blocking fetch_sequence in thread pool with timeout
            record = await asyncio.wait_for(
                loop.run_in_executor(
                    _executor,
                    lambda s=source, q=trimmed, kw=kwargs: fetch_sequence(q, s, **kw),
                ),
                timeout=timeout_s,
            )

            # Store successful result in cache
            if record and record.sequence:
                try:
                    store_cached(record)
                except Exception as cache_err:
                    logger.debug("Cache store failed after fetch: %s", cache_err)

            return record

        except asyncio.TimeoutError:
            last_exception = RuntimeError(
                f"Timeout ({timeout_s}s) exceeded fetching '{trimmed}' from {source} "
                f"(attempt {attempt}/{max_retries})"
            )
            logger.warning(
                "fetch_sequence_async: timeout on attempt %d/%d for %s/%s",
                attempt, max_retries, source, trimmed,
            )
        except Exception as e:
            last_exception = e
            logger.warning(
                "fetch_sequence_async: attempt %d/%d failed for %s/%s: %s",
                attempt, max_retries, source, trimmed, e,
            )

        # Exponential backoff: 1s, 2s, 4s (2^(attempt-1))
        if attempt < max_retries:
            backoff = 2 ** (attempt - 1)
            logger.debug("fetch_sequence_async: backing off %ds before retry", backoff)
            await asyncio.sleep(backoff)

    # All retries exhausted
    raise RuntimeError(
        f"All {max_retries} attempts failed for '{trimmed}' from {source}. "
        f"Last error: {last_exception}"
    )


async def fetch_sequences_async(
    queries: List[str],
    **kwargs,
) -> Tuple[List[SequenceRecord], List[ValidationError]]:
    """
    Batch async sequence fetcher with retry/timeout for each query.

    Validates the batch, then fetches all sequences concurrently using
    fetch_sequence_async. Supports the same kwargs as fetch_sequence_async
    (source, timeout_s, max_retries).

    Args:
        queries: List of raw query strings (max 50 per request).
        **kwargs: Passed to fetch_sequence_async (source, timeout_s, max_retries, etc.).

    Returns:
        Tuple of (successful_records, errors).
    """
    # Extract async-specific kwargs, pass the rest to the fetcher
    source = kwargs.pop("source", "auto")
    timeout_s = kwargs.pop("timeout_s", DEFAULT_TIMEOUT_S)
    max_retries = kwargs.pop("max_retries", DEFAULT_MAX_RETRIES)

    # Validate the batch
    valid_queries, errors = validate_batch(queries)

    if not valid_queries:
        return [], errors

    # Classify each query for source detection (unless source is explicit)
    tasks = []
    for query in valid_queries:
        query_source = source
        if query_source == "auto":
            detected = detect_source(query)
            if detected is None:
                errors.append(ValidationError(
                    query=query,
                    error=f"Cannot auto-detect source for '{query}'",
                ))
                continue
            query_source = detected

        tasks.append((query, query_source))

    # Fetch all concurrently
    records: List[SequenceRecord] = []

    async def _fetch_one(query: str, src: str) -> Optional[SequenceRecord]:
        try:
            return await fetch_sequence_async(
                query,
                source=src,
                timeout_s=timeout_s,
                max_retries=max_retries,
                **kwargs,
            )
        except Exception as e:
            errors.append(ValidationError(
                query=query,
                error=f"Async fetch failed from {src}: {str(e)}",
            ))
            return None

    # Run all fetch tasks concurrently
    results = await asyncio.gather(
        *[_fetch_one(q, s) for q, s in tasks],
        return_exceptions=False,
    )

    for result in results:
        if result is not None:
            records.append(result)

    return records, errors

"""
Step 15: Population Variant Filter (dbSNP)
============================================
Query a local dbSNP database for common variants overlapping primer binding sites.

Strategy:
  - Hard penalty 15 for SNPs with MAF ≥ 0.01 at the 3' last 5 nucleotides
    (critical for polymerase extension — mismatches here prevent amplification)
  - Annotate 5' and interior SNPs without penalty (informational only)
  - Handle missing dbSNP database gracefully (log warning, skip, mark unchecked)
  - Use pysam/tabix for indexed VCF queries when available
"""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────
CRITICAL_3PRIME_LENGTH = 5  # Last 5 bases at 3' end
MAF_THRESHOLD = 0.01  # Minor allele frequency threshold for penalty
SNP_3PRIME_PENALTY = 15.0  # Hard penalty for 3' critical SNP
DEFAULT_DBSNP_PATH = os.environ.get("DBSNP_VCF_PATH", "/opt/dbsnp/common_all.vcf.gz")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def execute(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Step 15: Filter primers overlapping common population variants.

    Input keys:
        - amplicon_checked (list): Pairs from Step 14
        - organism (str): Organism identifier (default 'human')
        - dbsnp_path (str, optional): Override path to dbSNP VCF

    Output keys:
        - variant_filtered (list): Pairs with SNP annotations
        - dbsnp_available (bool): Whether dbSNP was queryable
        - snp_note (str): Summary
    """
    pairs = input_data.get("amplicon_checked", [])
    if not pairs:
        return {"variant_filtered": [], "snp_note": "No pairs to filter", "dbsnp_available": False}

    organism = input_data.get("organism", "human")
    dbsnp_path = input_data.get("dbsnp_path", DEFAULT_DBSNP_PATH)

    # ── Check dbSNP availability ───────────────────────────────────────────
    dbsnp_available = _check_dbsnp_available(dbsnp_path)
    tabix_reader = None

    if dbsnp_available:
        tabix_reader = _open_tabix(dbsnp_path)
        if not tabix_reader:
            dbsnp_available = False

    if not dbsnp_available:
        logger.warning("dbSNP VCF not available — skipping full variant check, using heuristic.")
        # Fallback: heuristic check for CpG mutation hotspots at 3' end
        return _heuristic_snp_check(pairs)

    # ── Full dbSNP query for each primer ───────────────────────────────────
    variant_filtered = []
    for pair in pairs:
        pair.setdefault("penalties", {})

        fwd = pair.get("forward", {})
        rev = pair.get("reverse", {})

        # Query variants for each primer
        fwd_variants = _query_primer_variants(fwd, tabix_reader, organism)
        rev_variants = _query_primer_variants(rev, tabix_reader, organism)

        # Annotate forward primer
        fwd_3prime_snps = [v for v in fwd_variants if v["region"] == "3prime" and v["maf"] >= MAF_THRESHOLD]
        fwd_interior_snps = [v for v in fwd_variants if v["region"] == "interior"]
        fwd_5prime_snps = [v for v in fwd_variants if v["region"] == "5prime"]

        pair["forward"]["snp_3prime"] = fwd_3prime_snps
        pair["forward"]["snp_interior"] = fwd_interior_snps
        pair["forward"]["snp_5prime"] = fwd_5prime_snps
        pair["forward"]["snp_3prime_count"] = len(fwd_3prime_snps)

        # Annotate reverse primer
        rev_3prime_snps = [v for v in rev_variants if v["region"] == "3prime" and v["maf"] >= MAF_THRESHOLD]
        rev_interior_snps = [v for v in rev_variants if v["region"] == "interior"]
        rev_5prime_snps = [v for v in rev_variants if v["region"] == "5prime"]

        pair["reverse"]["snp_3prime"] = rev_3prime_snps
        pair["reverse"]["snp_interior"] = rev_interior_snps
        pair["reverse"]["snp_5prime"] = rev_5prime_snps
        pair["reverse"]["snp_3prime_count"] = len(rev_3prime_snps)

        # ── Apply penalties ────────────────────────────────────────────────
        if fwd_3prime_snps:
            pair["penalties"]["snp_3prime_fwd"] = SNP_3PRIME_PENALTY * len(fwd_3prime_snps)
            pair["forward"].setdefault("flags", []).append("snp_3prime_critical")
        if rev_3prime_snps:
            pair["penalties"]["snp_3prime_rev"] = SNP_3PRIME_PENALTY * len(rev_3prime_snps)
            pair["reverse"].setdefault("flags", []).append("snp_3prime_critical")

        # 5' and interior SNPs: annotate only, no penalty
        total_3prime = len(fwd_3prime_snps) + len(rev_3prime_snps)
        pair["snp_pass"] = total_3prime == 0
        pair["snp_total_variants"] = len(fwd_variants) + len(rev_variants)

        variant_filtered.append(pair)

    # Close tabix reader
    if tabix_reader:
        try:
            tabix_reader.close()
        except Exception as e:
            logger.debug("Error closing tabix reader: %s", e)

    passed = sum(1 for p in variant_filtered if p.get("snp_pass"))
    total_snps = sum(p.get("snp_total_variants", 0) for p in variant_filtered)

    # Ensure pair_id is preserved for all pairs
    for i, pair in enumerate(variant_filtered):
        if not pair.get("pair_id"):
            pair["pair_id"] = i + 1

    return {
        "variant_filtered": variant_filtered,
        "dbsnp_available": True,
        "snp_note": (
            f"{passed}/{len(variant_filtered)} pairs clear of critical 3' SNPs. "
            f"{total_snps} total variants annotated."
        ),
    }


# ---------------------------------------------------------------------------
# Variant Query
# ---------------------------------------------------------------------------

def _query_primer_variants(
    primer_data: Dict[str, Any],
    tabix_reader: Any,
    organism: str,
) -> List[Dict[str, Any]]:
    """
    Query dbSNP for variants overlapping a primer's genomic position.
    Classify each variant as 3prime, interior, or 5prime based on position.
    """
    variants = []

    chrom = primer_data.get("chromosome", primer_data.get("chrom", ""))
    start = primer_data.get("genomic_start", primer_data.get("start", 0))
    end = primer_data.get("genomic_end", primer_data.get("end", 0))
    direction = primer_data.get("direction", primer_data.get("strand", "forward"))
    seq_length = len(primer_data.get("sequence", ""))

    if not chrom or not start or not end or not tabix_reader:
        return variants

    try:
        # Query the VCF for variants in the primer region
        records = tabix_reader.fetch(chrom, max(0, start - 1), end)
        for record in records:
            # Parse variant info
            rsid = _extract_rsid(record)
            maf = _extract_maf(record)
            var_pos = _extract_position(record)

            # Determine region (relative to primer direction)
            region = _classify_variant_region(
                var_pos, start, end, seq_length, direction
            )

            variants.append({
                "rsid": rsid,
                "position": var_pos,
                "maf": maf,
                "region": region,
                "chrom": chrom,
            })

    except Exception as e:
        logger.debug("dbSNP query failed for %s:%d-%d: %s", chrom, start, end, e)

    return variants


def _classify_variant_region(
    var_pos: int,
    primer_start: int,
    primer_end: int,
    primer_length: int,
    direction: str,
) -> str:
    """
    Classify a variant as 3prime, 5prime, or interior relative to the primer.
    The 3' critical region is the last CRITICAL_3PRIME_LENGTH bases.
    """
    if not primer_length:
        primer_length = primer_end - primer_start

    if direction in ("forward", "+", "sense"):
        # Forward primer: 3' end is at the higher genomic coordinate
        three_prime_start = primer_end - CRITICAL_3PRIME_LENGTH
        five_prime_end = primer_start + CRITICAL_3PRIME_LENGTH
        if var_pos >= three_prime_start:
            return "3prime"
        elif var_pos <= five_prime_end:
            return "5prime"
        else:
            return "interior"
    else:
        # Reverse primer: 3' end is at the lower genomic coordinate
        three_prime_end = primer_start + CRITICAL_3PRIME_LENGTH
        five_prime_start = primer_end - CRITICAL_3PRIME_LENGTH
        if var_pos <= three_prime_end:
            return "3prime"
        elif var_pos >= five_prime_start:
            return "5prime"
        else:
            return "interior"


# ---------------------------------------------------------------------------
# VCF Parsing Helpers
# ---------------------------------------------------------------------------

def _extract_rsid(record) -> str:
    """Extract rsID from a VCF record (pysam or string format)."""
    if hasattr(record, "id"):
        return record.id or ""
    if isinstance(record, str):
        fields = record.split("\t")
        return fields[2] if len(fields) > 2 else ""
    return ""


def _extract_maf(record) -> float:
    """Extract MAF from a VCF record's INFO field."""
    # Try common MAF fields: CAF, AF, FREQ, TOPMED
    info = ""
    if hasattr(record, "info"):
        # pysam VariantRecord
        try:
            # Try CAF field (NCBI format: ref_freq,alt_freq)
            if "CAF" in record.info:
                caf = record.info["CAF"]
                if isinstance(caf, (list, tuple)) and len(caf) > 1:
                    alt_freqs = [float(f) for f in caf[1:] if f and f != "."]
                    return max(alt_freqs) if alt_freqs else 0.0
            # Try AF field
            if "AF" in record.info:
                af = record.info["AF"]
                if isinstance(af, (list, tuple)):
                    return max(float(f) for f in af if f)
                return float(af)
            # Try FREQ field
            if "FREQ" in record.info:
                freq = record.info["FREQ"]
                if isinstance(freq, str) and "|" in freq:
                    parts = freq.split("|")
                    if len(parts) > 1:
                        try:
                            return float(parts[1].split(",")[0])
                        except Exception as e: logger.debug("Suppressed exception: %s", e)
        except Exception as e: logger.debug("Suppressed exception: %s", e)
    elif isinstance(record, str):
        # Tab-delimited VCF line
        fields = record.split("\t")
        if len(fields) > 7:
            info = fields[7]
            # Parse INFO field for CAF or AF
            for item in info.split(";"):
                if item.startswith("CAF="):
                    try:
                        values = item[4:].split(",")
                        alt_freqs = [float(v) for v in values[1:] if v and v != "."]
                        return max(alt_freqs) if alt_freqs else 0.0
                    except ValueError:
                        pass
                elif item.startswith("AF="):
                    try:
                        return float(item[3:].split(",")[0])
                    except ValueError:
                        pass

    return 0.0


def _extract_position(record) -> int:
    """Extract genomic position from a VCF record."""
    if hasattr(record, "pos"):
        return record.pos
    if isinstance(record, str):
        fields = record.split("\t")
        if len(fields) > 1:
            try:
                return int(fields[1])
            except ValueError:
                pass
    return 0


# ---------------------------------------------------------------------------
# Tabix / Database Access
# ---------------------------------------------------------------------------

def _open_tabix(vcf_path: str):
    """Open a tabix-indexed VCF file. Returns reader or None."""
    has_index = os.path.exists(vcf_path + ".tbi") or os.path.exists(vcf_path + ".csi")
    try:
        if has_index:
            import pysam
            return pysam.TabixFile(vcf_path)
    except ImportError:
        logger.debug("pysam not available — trying manual tabix")
    except Exception as e:
        logger.debug("pysam TabixFile failed: %s", e)

    # Fallback: try subprocess tabix
    if has_index:
        try:
            import subprocess
            result = subprocess.run(
                ["tabix", "--version"], capture_output=True, timeout=5
            )
            if result.returncode == 0:
                return _TabixSubprocessReader(vcf_path)
        except Exception as e: logger.debug("Suppressed exception: %s", e)

    if os.path.exists(vcf_path):
        return _PlainVcfReader(vcf_path)

    return None


class _TabixSubprocessReader:
    """Fallback tabix reader using subprocess."""

    def __init__(self, vcf_path: str):
        self._path = vcf_path

    def fetch(self, chrom: str, start: int, end: int):
        """Fetch records from tabix-indexed VCF."""
        import subprocess
        try:
            region = f"{chrom}:{start+1}-{end}"
            result = subprocess.run(
                ["tabix", self._path, region],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split("\n")
        except Exception as e:
            logger.debug("Tabix subprocess failed: %s", e)
        return []

    def close(self):
        pass


class _PlainVcfReader:
    """Small local VCF reader used when tabix/pysam are unavailable."""

    def __init__(self, vcf_path: str):
        self._records = []
        with open(vcf_path, "r") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                fields = line.split("\t")
                if len(fields) < 8:
                    continue
                try:
                    pos = int(fields[1])
                except ValueError:
                    continue
                self._records.append((fields[0], pos, line))

    def fetch(self, chrom: str, start: int, end: int):
        # pysam uses 0-based half-open coordinates; VCF POS is 1-based.
        return [
            line for rec_chrom, pos, line in self._records
            if rec_chrom == chrom and start < pos <= end
        ]

    def close(self):
        pass


# ---------------------------------------------------------------------------
# Heuristic Fallback
# ---------------------------------------------------------------------------

def _heuristic_snp_check(pairs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Fallback when dbSNP is not available: check for CpG dinucleotides at the 3' end
    (CpG → TpG transitions are the most common human SNPs).
    """
    for pair in pairs:
        pair.setdefault("penalties", {})

        fwd_seq = pair.get("forward", {}).get("sequence", "")
        rev_seq = pair.get("reverse", {}).get("sequence", "")

        fwd_3prime = fwd_seq[-CRITICAL_3PRIME_LENGTH:].upper() if fwd_seq else ""
        rev_3prime = rev_seq[-CRITICAL_3PRIME_LENGTH:].upper() if rev_seq else ""

        fwd_cpg_count = fwd_3prime.count("CG")
        rev_cpg_count = rev_3prime.count("CG")

        pair["forward"]["snp_3prime_count"] = fwd_cpg_count
        pair["forward"]["snp_3prime"] = []
        pair["reverse"]["snp_3prime_count"] = rev_cpg_count
        pair["reverse"]["snp_3prime"] = []

        # CpG at 3' end is a proxy for likely SNP — apply reduced penalty
        if fwd_cpg_count > 0:
            pair["forward"].setdefault("flags", []).append("cpg_3prime_hotspot")
        if rev_cpg_count > 0:
            pair["reverse"].setdefault("flags", []).append("cpg_3prime_hotspot")

        pair["snp_pass"] = (fwd_cpg_count == 0 and rev_cpg_count == 0)
        pair["snp_total_variants"] = 0

    passed = sum(1 for p in pairs if p.get("snp_pass"))
    return {
        "variant_filtered": pairs,
        "dbsnp_available": False,
        "snp_note": (
            f"{passed}/{len(pairs)} clear of 3' CpG hotspots "
            "(full dbSNP check unavailable — install dbSNP VCF for production use)."
        ),
    }


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _check_dbsnp_available(dbsnp_path: str) -> bool:
    """Check if local dbSNP VCF is accessible and indexed."""
    if not os.path.exists(dbsnp_path):
        return False
    if os.path.isfile(dbsnp_path):
        return True
    # Check for tabix index (.tbi)
    tbi_path = dbsnp_path + ".tbi"
    csi_path = dbsnp_path + ".csi"
    return os.path.exists(tbi_path) or os.path.exists(csi_path)

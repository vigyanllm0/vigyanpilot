"""
Step 16: Clinical Hotspot Filter (ClinVar)
==========================================================
Cross-reference primer binding sites against clinically relevant ClinVar
Pathogenic / Likely pathogenic variants.

Flag "clinical_hotspot_overlap" with a soft penalty — primers binding to
hyper-mutated loci may yield false negatives in clinical assays.

Strategy:
  - Query local ClinVar VCF for Pathogenic/Likely pathogenic
  - Report variant ID, gene, and position for each overlap
  - Soft penalty (does not reject — annotates for user review)
  - Handle missing databases gracefully
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────
DEFAULT_CLINVAR_PATH = os.environ.get("CLINVAR_VCF_PATH", "/opt/clinvar/clinvar.vcf.gz")

CLINICAL_PENALTY = 10.0
CLINVAR_SIGNIFICANCE_FILTER = {"Pathogenic", "Likely_pathogenic", "Pathogenic/Likely_pathogenic"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def execute(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Step 16: Check primers against ClinVar clinical hotspots.

    Input keys:
        - variant_filtered (list): Pairs from Step 15
        - organism (str): Organism identifier
        - clinvar_path (str, optional): Override ClinVar VCF path

    Output keys:
        - clinical_checked (list): Pairs with clinical annotations
        - clinvar_available (bool): Whether ClinVar was queryable
        - clinical_note (str): Summary
    """
    pairs = input_data.get("variant_filtered", [])
    if not pairs:
        return {
            "clinical_checked": [],
            "clinical_note": "No pairs to check",
            "clinvar_available": False,
        }

    clinvar_path = input_data.get("clinvar_path", DEFAULT_CLINVAR_PATH)

    # ── Check database availability ────────────────────────────────────────
    clinvar_available = _check_vcf_available(clinvar_path)

    if not clinvar_available:
        logger.info("ClinVar not available locally — skipping clinical hotspot check.")
        for pair in pairs:
            pair["clinvar_overlaps"] = []
            pair["clinical_hotspot_overlap"] = False
            pair["clinical_pass"] = True
            pair.setdefault("penalties", {})
        return {
            "clinical_checked": pairs,
            "clinvar_available": False,
            "clinical_note": (
                "ClinVar not available — clinical hotspot check skipped. "
                "Install a local ClinVar VCF for clinical assay design."
            ),
        }

    # ── Open database readers ──────────────────────────────────────────────
    clinvar_reader = _open_vcf(clinvar_path)

    # ── Query each primer pair ─────────────────────────────────────────────
    clinical_checked = []
    hotspot_count = 0

    for pair in pairs:
        pair.setdefault("penalties", {})

        fwd = pair.get("forward", {})
        rev = pair.get("reverse", {})

        # ClinVar query
        fwd_clinvar = _query_clinvar(fwd, clinvar_reader) if clinvar_reader else []
        rev_clinvar = _query_clinvar(rev, clinvar_reader) if clinvar_reader else []

        all_clinvar = fwd_clinvar + rev_clinvar

        pair["clinvar_overlaps"] = all_clinvar
        pair["forward"]["clinvar_hits"] = len(fwd_clinvar)
        pair["reverse"]["clinvar_hits"] = len(rev_clinvar)

        # ── Flag clinical hotspot overlap ──────────────────────────────────
        has_overlap = len(all_clinvar) > 0
        pair["clinical_hotspot_overlap"] = has_overlap
        pair["clinical_pass"] = not has_overlap

        if has_overlap:
            hotspot_count += 1
            pair["penalties"]["clinical_hotspot"] = CLINICAL_PENALTY
            # Add details for reporting
            pair["clinical_details"] = _build_clinical_details(all_clinvar)

        clinical_checked.append(pair)

    # ── Close readers ──────────────────────────────────────────────────────
    _safe_close(clinvar_reader)

    passed = len(clinical_checked) - hotspot_count

    # Ensure pair_id is preserved for all pairs
    for i, pair in enumerate(clinical_checked):
        if not pair.get("pair_id"):
            pair["pair_id"] = i + 1

    return {
        "clinical_checked": clinical_checked,
        "clinvar_available": clinvar_available,
        "clinical_note": (
            f"{passed}/{len(clinical_checked)} pairs avoid clinical hotspots. "
            f"{hotspot_count} flagged with clinical_hotspot_overlap (soft penalty)."
        ),
    }


# ---------------------------------------------------------------------------
# ClinVar Query
# ---------------------------------------------------------------------------

def _query_clinvar(
    primer_data: dict[str, Any], reader: Any
) -> list[dict[str, Any]]:
    """
    Query ClinVar for Pathogenic/Likely pathogenic variants overlapping the primer.
    """
    chrom = primer_data.get("chromosome", primer_data.get("chrom", ""))
    start = primer_data.get("genomic_start", primer_data.get("start", 0))
    end = primer_data.get("genomic_end", primer_data.get("end", 0))

    if not chrom or not start or not end or not reader:
        return []

    variants = []
    try:
        records = _fetch_records(reader, chrom, start, end)
        for record in records:
            significance = _extract_clinical_significance(record)
            # Filter for pathogenic
            if significance and any(
                sig in CLINVAR_SIGNIFICANCE_FILTER
                for sig in significance.replace(" ", "_").split("/")
            ):
                variant_info = {
                    "source": "ClinVar",
                    "variant_id": _extract_id(record),
                    "position": _extract_pos(record),
                    "significance": significance,
                    "gene": _extract_gene(record),
                    "type": "pathogenic",
                }
                variants.append(variant_info)
    except Exception as e:
        logger.debug("ClinVar query failed for %s:%s-%s: %s", chrom, start, end, e)

    return variants


def _extract_clinical_significance(record) -> str:
    """Extract CLNSIG from ClinVar VCF record."""
    if hasattr(record, "info"):
        try:
            clnsig = record.info.get("CLNSIG", "")
            if isinstance(clnsig, (list, tuple)):
                return "/".join(str(s) for s in clnsig)
            return str(clnsig)
        except Exception as e: logger.debug("Suppressed exception: %s", e)
    elif isinstance(record, str):
        # Parse INFO field
        fields = record.split("\t")
        if len(fields) > 7:
            for item in fields[7].split(";"):
                if item.startswith("CLNSIG="):
                    return item[7:]
    return ""


# ---------------------------------------------------------------------------
# VCF Record Helpers
# ---------------------------------------------------------------------------

def _extract_id(record) -> str:
    """Extract variant ID from a VCF record."""
    if hasattr(record, "id"):
        return record.id or ""
    if isinstance(record, str):
        fields = record.split("\t")
        return fields[2] if len(fields) > 2 else ""
    return ""


def _extract_pos(record) -> int:
    """Extract position from a VCF record."""
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


def _extract_gene(record) -> str:
    """Extract gene name from a VCF record's INFO field."""
    if hasattr(record, "info"):
        try:
            gene = record.info.get("GENEINFO", record.info.get("GENE", ""))
            if isinstance(gene, str) and ":" in gene:
                return gene.split(":")[0]
            return str(gene) if gene else ""
        except Exception as e: logger.debug("Suppressed exception: %s", e)
    elif isinstance(record, str):
        fields = record.split("\t")
        if len(fields) > 7:
            for item in fields[7].split(";"):
                if item.startswith("GENEINFO="):
                    return item[9:].split(":")[0]
                elif item.startswith("GENE="):
                    return item[5:]
    return ""


def _fetch_records(reader, chrom: str, start: int, end: int) -> list:
    """Fetch records from a VCF reader (pysam or subprocess-based)."""
    try:
        return list(reader.fetch(chrom, max(0, start - 1), end))
    except Exception:
        # Try with/without 'chr' prefix
        alt_chrom = chrom.replace("chr", "") if chrom.startswith("chr") else f"chr{chrom}"
        try:
            return list(reader.fetch(alt_chrom, max(0, start - 1), end))
        except Exception:
            return []


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _build_clinical_details(clinvar_variants: list[dict]) -> list[dict[str, Any]]:
    """Build a combined clinical details report."""
    details = []
    for v in clinvar_variants:
        details.append({
            "source": "ClinVar",
            "variant_id": v.get("variant_id", ""),
            "gene": v.get("gene", ""),
            "position": v.get("position", 0),
            "significance": v.get("significance", ""),
        })
    return details


# ---------------------------------------------------------------------------
# Database Access Utilities
# ---------------------------------------------------------------------------

def _check_vcf_available(vcf_path: str) -> bool:
    """Check if a VCF file exists and is indexed."""
    if not os.path.exists(vcf_path):
        return False
    tbi_path = vcf_path + ".tbi"
    csi_path = vcf_path + ".csi"
    return os.path.exists(tbi_path) or os.path.exists(csi_path)


def _open_vcf(vcf_path: str):
    """Open an indexed VCF file. Returns reader or None."""
    try:
        import pysam
        return pysam.TabixFile(vcf_path)
    except ImportError:
        logger.debug("pysam not available — trying subprocess tabix fallback")
    except Exception as e:
        logger.debug("pysam open failed for %s: %s", vcf_path, e)

    # Subprocess fallback
    try:
        import subprocess
        result = subprocess.run(["tabix", "--version"], capture_output=True, timeout=5)
        if result.returncode == 0:
            return _TabixFallbackReader(vcf_path)
    except Exception as e: logger.debug("Suppressed exception: %s", e)

    return None


class _TabixFallbackReader:
    """Fallback VCF reader using tabix subprocess."""

    def __init__(self, vcf_path: str):
        self._path = vcf_path

    def fetch(self, chrom: str, start: int, end: int) -> list[str]:
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
            logger.debug("Tabix fetch failed: %s", e)
        return []

    def close(self):
        pass


def _safe_close(reader) -> None:
    """Safely close a reader."""
    if reader:
        try:
            reader.close()
        except Exception as e:
            logger.debug("Error closing reader: %s", e)

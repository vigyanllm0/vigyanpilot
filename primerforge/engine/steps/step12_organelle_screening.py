"""
Step 12: Organelle & Pseudogene Screening
==========================================
Screen primer alignment hits against mitochondrial DNA (chrM/MT) and
processed pseudogene coordinate databases to ensure amplification
products originate exclusively from the intended genomic locus.

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5
"""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from .base import PipelineStep

logger = logging.getLogger(__name__)

# Thresholds for hit significance
IDENTITY_THRESHOLD = 90.0  # ≥90% identity
COVERAGE_THRESHOLD = 80.0  # ≥80% query coverage

# Max distance between fwd and rev hits to flag as same-locus amplification
LOCUS_PROXIMITY_BP = 5000

# Penalty weight for organelle/pseudogene risk
PSEUDOGENE_ORGANELLE_PENALTY = 20.0

# Mitochondrial chromosome identifiers (various naming conventions)
MITOCHONDRIAL_CHROMS = {"chrM", "MT", "chrMT", "mitochondria", "NC_012920"}

# Default paths for reference databases
DEFAULT_PSEUDOGENE_DB_PATH = os.environ.get(
    "PSEUDOGENE_DB_PATH", "/opt/blast_db/pseudogene_coordinates.tsv"
)
DEFAULT_MITO_REF_PATH = os.environ.get(
    "MITO_REF_PATH", "/opt/blast_db/chrM_reference.fa"
)


class OrganelleScreeningStep(PipelineStep):
    """
    Screens primers against mitochondrial DNA and processed pseudogenes.

    Cross-references alignment hits from Step 11 (Bowtie2) against:
    1. Known processed pseudogene coordinate database
    2. Mitochondrial genome sequence (chrM/MT)

    Rejects primer pairs where both forward and reverse align to the same
    organelle or pseudogene locus within 5000bp of each other.
    """

    def __init__(
        self,
        pseudogene_db_path: Optional[str] = None,
        mito_ref_path: Optional[str] = None,
    ):
        super().__init__(name="Organelle & Pseudogene Screening", step_number=12)
        self.pseudogene_db_path = pseudogene_db_path or DEFAULT_PSEUDOGENE_DB_PATH
        self.mito_ref_path = mito_ref_path or DEFAULT_MITO_REF_PATH

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Screen primer alignment hits against organelle and pseudogene databases.

        Input keys:
            primer_candidates (list): Primer candidate pairs from upstream steps
            alignment_hits (list): Alignment hits from Step 11 (Bowtie2)

        Output keys:
            primer_candidates (list): Updated with organelle/pseudogene flags
            organelle_hits (list): Hits matching mitochondrial genome
            pseudogene_hits (list): Hits matching pseudogene coordinates
        """
        primer_candidates = input_data.get("primer_candidates", [])
        alignment_hits = input_data.get("alignment_hits", [])

        # Also check aligned_pairs from step11 format
        if not alignment_hits:
            alignment_hits = input_data.get("aligned_pairs", [])
        if not primer_candidates and input_data.get("aligned_pairs"):
            primer_candidates = input_data.get("aligned_pairs", [])

        if not primer_candidates and not alignment_hits:
            return {
                "primer_candidates": [],
                "organelle_hits": [],
                "pseudogene_hits": [],
                "organelle_screening_note": "No candidates or hits to screen",
            }

        # Check database availability
        pseudogene_db_available = self._check_pseudogene_db()
        mito_ref_available = self._check_mito_ref()

        if not pseudogene_db_available and not mito_ref_available:
            logger.warning(
                "VigyanLLM: Pseudogene DB and mitochondrial reference both "
                "unavailable — skipping organelle screening"
            )
            # Mark all candidates as unchecked per Requirement 12.5
            for candidate in primer_candidates:
                if "flags" not in candidate:
                    candidate["flags"] = []
                candidate["flags"].append("organelle_pseudogene_unchecked")
                if "annotations" not in candidate:
                    candidate["annotations"] = {}
                candidate["annotations"]["organelle_screening"] = "skipped_db_unavailable"

            return {
                "primer_candidates": primer_candidates,
                "aligned_pairs": primer_candidates,
                "organelle_hits": [],
                "pseudogene_hits": [],
                "organelle_screening_note": "organelle_pseudogene_unchecked",
                "screening_status": "organelle_pseudogene_unchecked",
            }

        # Screen alignment hits against mitochondrial genome
        organelle_hits = []
        if mito_ref_available:
            organelle_hits = self._check_mitochondrial(alignment_hits)

        # Screen alignment hits against pseudogene coordinates
        pseudogene_hits = []
        if pseudogene_db_available:
            pseudogene_hits = self._check_pseudogenes(alignment_hits)

        # Flag primer pairs where both fwd and rev align to same locus
        flagged_pairs = self._flag_same_locus_pairs(
            primer_candidates, organelle_hits, pseudogene_hits
        )

        screened_count = len(primer_candidates)
        flagged_count = sum(
            1 for c in primer_candidates
            if "organelle_pseudogene_risk" in c.get("flags", [])
        )

        return {
            "primer_candidates": primer_candidates,
            "aligned_pairs": primer_candidates,
            "organelle_hits": organelle_hits,
            "pseudogene_hits": pseudogene_hits,
            "organelle_screening_note": (
                f"{flagged_count}/{screened_count} candidates flagged for "
                f"organelle/pseudogene risk"
            ),
            "screening_status": "completed",
        }

    def _check_pseudogene_db(self) -> bool:
        """Check if the pseudogene coordinate database is accessible."""
        return os.path.exists(self.pseudogene_db_path)

    def _check_mito_ref(self) -> bool:
        """Check if the mitochondrial reference sequence is accessible."""
        return os.path.exists(self.mito_ref_path)

    def _check_mitochondrial(self, alignment_hits: List[Dict]) -> List[Dict]:
        """
        Cross-reference alignment hits against mitochondrial genome (chrM/MT).

        Filters hits with ≥90% identity and ≥80% coverage that map to
        mitochondrial chromosome identifiers.

        Returns:
            List of hits matching mitochondrial genome with locus details.
        """
        mito_hits = []

        for hit in alignment_hits:
            # Handle both flat hit dicts and nested pair structures
            hits_to_check = self._extract_hits_from_entry(hit)

            for h in hits_to_check:
                chrom = h.get("chromosome", h.get("chrom", h.get("reference", "")))
                identity = h.get("percent_identity", h.get("identity", 0.0))
                coverage = h.get("query_coverage", h.get("coverage", 0.0))

                if (
                    chrom in MITOCHONDRIAL_CHROMS
                    and identity >= IDENTITY_THRESHOLD
                    and coverage >= COVERAGE_THRESHOLD
                ):
                    mito_hit = {
                        "type": "mitochondrial",
                        "chromosome": chrom,
                        "start": h.get("start", h.get("position", 0)),
                        "end": h.get("end", h.get("position", 0) + h.get("alignment_length", 0)),
                        "percent_identity": identity,
                        "query_coverage": coverage,
                        "primer_id": h.get("primer_id", h.get("query_id", "")),
                        "direction": h.get("direction", "unknown"),
                        "locus": f"{chrom}:{h.get('start', 0)}-{h.get('end', 0)}",
                    }
                    mito_hits.append(mito_hit)

        return mito_hits

    def _check_pseudogenes(self, alignment_hits: List[Dict]) -> List[Dict]:
        """
        Cross-reference alignment hits against pseudogene coordinate database.

        Filters hits with ≥90% identity and ≥80% coverage that overlap
        known pseudogene coordinates.

        Returns:
            List of hits matching pseudogene regions with gene identifiers.
        """
        pseudogene_hits = []

        # Load pseudogene coordinates
        pseudogene_coords = self._load_pseudogene_coordinates()
        if not pseudogene_coords:
            logger.warning(
                "VigyanLLM: Pseudogene coordinate database is empty or unreadable"
            )
            return []

        for hit in alignment_hits:
            hits_to_check = self._extract_hits_from_entry(hit)

            for h in hits_to_check:
                identity = h.get("percent_identity", h.get("identity", 0.0))
                coverage = h.get("query_coverage", h.get("coverage", 0.0))

                if identity < IDENTITY_THRESHOLD or coverage < COVERAGE_THRESHOLD:
                    continue

                chrom = h.get("chromosome", h.get("chrom", h.get("reference", "")))
                start = h.get("start", h.get("position", 0))
                end = h.get("end", start + h.get("alignment_length", 0))

                # Check overlap with pseudogene coordinates
                matching_pseudogenes = self._find_pseudogene_overlap(
                    pseudogene_coords, chrom, start, end
                )

                for pg in matching_pseudogenes:
                    pg_hit = {
                        "type": "pseudogene",
                        "pseudogene_id": pg["gene_id"],
                        "pseudogene_name": pg["gene_name"],
                        "chromosome": chrom,
                        "start": start,
                        "end": end,
                        "percent_identity": identity,
                        "query_coverage": coverage,
                        "primer_id": h.get("primer_id", h.get("query_id", "")),
                        "direction": h.get("direction", "unknown"),
                        "locus": f"{chrom}:{start}-{end}",
                        "parent_gene": pg.get("parent_gene", ""),
                    }
                    pseudogene_hits.append(pg_hit)

        return pseudogene_hits

    def _flag_same_locus_pairs(
        self,
        primer_candidates: List[Dict],
        organelle_hits: List[Dict],
        pseudogene_hits: List[Dict],
    ) -> List[str]:
        """
        Reject primer pairs where both fwd and rev align to the same
        pseudogene or organelle locus within 5000bp.

        Modifies primer_candidates in-place by adding flags and penalties.

        Returns:
            List of pair IDs that were flagged.
        """
        all_hits = organelle_hits + pseudogene_hits
        flagged_pairs = []

        # Group hits by primer_id
        hits_by_primer: Dict[str, List[Dict]] = {}
        for h in all_hits:
            pid = h.get("primer_id", "")
            if pid not in hits_by_primer:
                hits_by_primer[pid] = []
            hits_by_primer[pid].append(h)

        for candidate in primer_candidates:
            if "flags" not in candidate:
                candidate["flags"] = []
            if "annotations" not in candidate:
                candidate["annotations"] = {}
            if "penalties" not in candidate:
                candidate["penalties"] = {}

            # Get IDs for forward and reverse primers
            pair_id = candidate.get("pair_id", candidate.get("id", ""))
            fwd_id = candidate.get("forward", {}).get("id", f"{pair_id}_fwd")
            rev_id = candidate.get("reverse", {}).get("id", f"{pair_id}_rev")

            # Also try flat structure (primer_id directly on candidate)
            fwd_hits = hits_by_primer.get(fwd_id, [])
            rev_hits = hits_by_primer.get(rev_id, [])

            # Check if both primers hit the same locus within LOCUS_PROXIMITY_BP
            flagged, locus_details = self._check_proximity(fwd_hits, rev_hits)

            if flagged:
                candidate["flags"].append("organelle_pseudogene_risk")
                candidate["penalties"]["pseudogene_organelle"] = PSEUDOGENE_ORGANELLE_PENALTY
                candidate["annotations"]["organelle_pseudogene_details"] = locus_details
                flagged_pairs.append(pair_id)

        return flagged_pairs

    def _check_proximity(
        self, fwd_hits: List[Dict], rev_hits: List[Dict]
    ) -> Tuple[bool, List[Dict]]:
        """
        Check if any forward hit and reverse hit map to the same chromosome
        within LOCUS_PROXIMITY_BP of each other.

        Returns:
            Tuple of (is_flagged, locus_detail_list).
        """
        locus_details = []

        for fwd in fwd_hits:
            for rev in rev_hits:
                fwd_chrom = fwd.get("chromosome", "")
                rev_chrom = rev.get("chromosome", "")

                if fwd_chrom != rev_chrom or not fwd_chrom:
                    continue

                fwd_start = fwd.get("start", 0)
                fwd_end = fwd.get("end", fwd_start)
                rev_start = rev.get("start", 0)
                rev_end = rev.get("end", rev_start)

                # Calculate distance between the two hits
                # Distance is the gap between the closest ends
                if fwd_end <= rev_start:
                    distance = rev_start - fwd_end
                elif rev_end <= fwd_start:
                    distance = fwd_start - rev_end
                else:
                    # Overlapping
                    distance = 0

                if distance <= LOCUS_PROXIMITY_BP:
                    hit_type = fwd.get("type", rev.get("type", "unknown"))
                    detail = {
                        "type": hit_type,
                        "chromosome": fwd_chrom,
                        "fwd_position": f"{fwd_start}-{fwd_end}",
                        "rev_position": f"{rev_start}-{rev_end}",
                        "distance_bp": distance,
                    }

                    # Add pseudogene or organelle-specific info
                    if hit_type == "pseudogene":
                        detail["pseudogene_id"] = fwd.get(
                            "pseudogene_id", rev.get("pseudogene_id", "")
                        )
                        detail["pseudogene_name"] = fwd.get(
                            "pseudogene_name", rev.get("pseudogene_name", "")
                        )
                        detail["parent_gene"] = fwd.get(
                            "parent_gene", rev.get("parent_gene", "")
                        )
                    elif hit_type == "mitochondrial":
                        detail["locus"] = f"{fwd_chrom}:{fwd_start}-{rev_end}"

                    locus_details.append(detail)

        return (len(locus_details) > 0, locus_details)

    def _extract_hits_from_entry(self, entry: Dict) -> List[Dict]:
        """
        Extract individual alignment hits from an entry which may be
        a flat hit dict or a nested pair structure from Step 11.
        """
        hits = []

        # If entry has 'hits' list (batch format)
        if "hits" in entry:
            for h in entry["hits"]:
                h.setdefault("primer_id", entry.get("primer_id", entry.get("id", "")))
                h.setdefault("direction", entry.get("direction", "unknown"))
                hits.append(h)
        # If entry has forward/reverse nested structure
        elif "forward" in entry and "reverse" in entry:
            fwd = entry.get("forward", {})
            rev = entry.get("reverse", {})
            for fwd_hit in fwd.get("alignment_hits", fwd.get("hits", [])):
                fwd_hit.setdefault("primer_id", fwd.get("id", entry.get("pair_id", "") + "_fwd"))
                fwd_hit.setdefault("direction", "forward")
                hits.append(fwd_hit)
            for fwd_hit in fwd.get("alignment_locations", []):
                fwd_hit.setdefault("primer_id", fwd.get("id", entry.get("pair_id", "") + "_fwd"))
                fwd_hit.setdefault("direction", "forward")
                hits.append(fwd_hit)
            for rev_hit in rev.get("alignment_hits", rev.get("hits", [])):
                rev_hit.setdefault("primer_id", rev.get("id", entry.get("pair_id", "") + "_rev"))
                rev_hit.setdefault("direction", "reverse")
                hits.append(rev_hit)
            for rev_hit in rev.get("alignment_locations", []):
                rev_hit.setdefault("primer_id", rev.get("id", entry.get("pair_id", "") + "_rev"))
                rev_hit.setdefault("direction", "reverse")
                hits.append(rev_hit)
        # Flat hit dict (single alignment record)
        elif "chromosome" in entry or "chrom" in entry or "reference" in entry:
            hits.append(entry)

        return hits

    def _load_pseudogene_coordinates(self) -> List[Dict]:
        """
        Load pseudogene coordinates from the database file.

        Expected TSV format:
            gene_id<TAB>gene_name<TAB>chromosome<TAB>start<TAB>end<TAB>parent_gene

        Returns:
            List of pseudogene coordinate records.
        """
        coords = []
        try:
            with open(self.pseudogene_db_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("\t")
                    if len(parts) >= 5:
                        coords.append({
                            "gene_id": parts[0],
                            "gene_name": parts[1],
                            "chromosome": parts[2],
                            "start": int(parts[3]),
                            "end": int(parts[4]),
                            "parent_gene": parts[5] if len(parts) > 5 else "",
                        })
        except (OSError, IOError) as e:
            logger.warning("VigyanLLM: Failed to load pseudogene DB: %s", e)
        return coords

    def _find_pseudogene_overlap(
        self,
        pseudogene_coords: List[Dict],
        chrom: str,
        start: int,
        end: int,
    ) -> List[Dict]:
        """
        Find pseudogene entries that overlap the given genomic interval.

        Returns:
            List of pseudogene records overlapping the region.
        """
        overlaps = []
        for pg in pseudogene_coords:
            if pg["chromosome"] != chrom:
                continue
            # Check for any overlap
            if start <= pg["end"] and end >= pg["start"]:
                overlaps.append(pg)
        return overlaps


def execute(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Module-level execute function for Step 12: Organelle & Pseudogene Screening.

    Instantiates OrganelleScreeningStep and runs execution.
    This function is registered with the pipeline orchestrator.

    Args:
        input_data: Dictionary containing primer_candidates and alignment_hits.

    Returns:
        Dictionary with screened primer_candidates, organelle_hits,
        and pseudogene_hits.
    """
    step = OrganelleScreeningStep(
        pseudogene_db_path=input_data.get("pseudogene_db_path"),
        mito_ref_path=input_data.get("mito_ref_path"),
    )
    return step.execute(input_data)

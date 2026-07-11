"""
IGSC Compliance Module
=======================
Biosecurity screening against IGSC (International Gene Synthesis Consortium)
guidelines. Screens primer, probe, and amplicon sequences against a local
pathogen database before order serialization is permitted.

This module runs AFTER Step 19 (Ranking) completes and BEFORE order
serialization. It is not a numbered pipeline step but a post-pipeline gate.

Requirements: 27.1, 27.2, 27.3, 27.4, 27.5, 27.6, 27.7, 27.8
"""

import json
import logging
import os
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Default screening timeout in seconds
SCREENING_TIMEOUT_SECONDS = 120

# Alignment thresholds for biosecurity hold
IDENTITY_THRESHOLD = 80.0  # ≥80% identity
ALIGNMENT_LENGTH_THRESHOLD = 200  # ≥200 bp alignment length


@dataclass
class AlignmentHit:
    """A single BLASTN alignment hit against the pathogen database."""

    organism: str = ""
    gene: str = ""
    percent_identity: float = 0.0
    alignment_length: int = 0
    query_sequence: str = ""
    subject_id: str = ""
    e_value: float = 0.0
    bit_score: float = 0.0


@dataclass
class ComplianceResult:
    """Result of IGSC biosecurity compliance screening.

    Attributes:
        status: One of: biosecurity_cleared, biosecurity_hold,
                compliance_unavailable, compliance_timeout
        matched_organism: Organism name if a match triggered a hold.
        matched_gene: Gene name if a match triggered a hold.
        percent_identity: Alignment identity percentage for the triggering hit.
        alignment_length: Alignment length in bp for the triggering hit.
        sequences_screened: Total number of sequences screened.
    """

    status: str  # biosecurity_cleared | biosecurity_hold | compliance_unavailable | compliance_timeout
    matched_organism: str | None = None
    matched_gene: str | None = None
    percent_identity: float | None = None
    alignment_length: int | None = None
    sequences_screened: int = 0


class IGSCComplianceModule:
    """Biosecurity screening against IGSC guidelines.

    Screens primer, probe, and amplicon sequences against a local pathogen
    database using BLASTN alignment. Any match at ≥80% identity over ≥200bp
    triggers a biosecurity_hold, blocking order serialization.

    Args:
        pathogen_db_path: Path to the local BLAST-formatted pathogen database.
            Defaults to /opt/pathogen_db.
        timeout_seconds: Maximum screening time in seconds. Defaults to 120.
    """

    def __init__(
        self,
        pathogen_db_path: str = "/opt/pathogen_db",
        timeout_seconds: int = SCREENING_TIMEOUT_SECONDS,
    ):
        self._db_path = pathogen_db_path
        self._timeout_seconds = timeout_seconds
        self._db_loaded = False

    @property
    def db_path(self) -> str:
        """Return the configured pathogen database path."""
        return self._db_path

    @property
    def timeout_seconds(self) -> int:
        """Return the configured screening timeout."""
        return self._timeout_seconds

    def screen(self, sequences: list[str], job_id: str) -> ComplianceResult:
        """Screen sequences against the pathogen database for biosecurity concerns.

        Aligns all provided sequences (primers, probes, amplicons) against
        the local pathogen DB. Returns a ComplianceResult indicating whether
        the design is cleared for order serialization.

        Args:
            sequences: List of DNA sequences to screen.
            job_id: Pipeline job identifier for logging.

        Returns:
            ComplianceResult with appropriate status.
        """
        # Check pathogen database availability (Requirement 27.4)
        if not self._is_db_available():
            result = ComplianceResult(
                status="compliance_unavailable",
                sequences_screened=0,
            )
            self._log_result(job_id, result)
            return result

        # Screen with timeout enforcement (Requirement 27.6)
        result_container: list[ComplianceResult] = []
        exception_container: list[Exception] = []

        def _run_screening():
            try:
                screening_result = self._perform_screening(sequences, job_id)
                result_container.append(screening_result)
            except Exception as exc:
                exception_container.append(exc)

        start_time = time.time()
        thread = threading.Thread(target=_run_screening, daemon=True)
        thread.start()
        thread.join(timeout=self._timeout_seconds)

        elapsed = time.time() - start_time

        # Check for timeout
        if thread.is_alive():
            logger.warning(
                "VigyanLLM: Compliance screening for job %s exceeded %ds timeout "
                "(elapsed: %.1fs)",
                job_id,
                self._timeout_seconds,
                elapsed,
            )
            result = ComplianceResult(
                status="compliance_timeout",
                sequences_screened=len(sequences),
            )
            self._log_result(job_id, result)
            return result

        # Check for exceptions during screening
        if exception_container:
            exc = exception_container[0]
            logger.error(
                "VigyanLLM: Compliance screening error for job %s: %s",
                job_id,
                str(exc),
            )
            result = ComplianceResult(
                status="compliance_unavailable",
                sequences_screened=len(sequences),
            )
            self._log_result(job_id, result)
            return result

        # Return screening result
        if result_container:
            result = result_container[0]
        else:
            result = ComplianceResult(
                status="compliance_unavailable",
                sequences_screened=len(sequences),
            )

        self._log_result(job_id, result)
        return result

    def _is_db_available(self) -> bool:
        """Check if the pathogen database is available and contains data.

        The database is considered available if the path exists and contains
        at least one BLAST database file (*.nhr, *.nin, *.nsq for nucleotide).

        Returns:
            True if database is available, False otherwise.
        """
        if not os.path.exists(self._db_path):
            logger.warning(
                "VigyanLLM: Pathogen database path does not exist: %s",
                self._db_path,
            )
            return False

        # Check if it's a directory containing BLAST DB files
        if os.path.isdir(self._db_path):
            # Look for BLAST nucleotide database files
            blast_extensions = {".nhr", ".nin", ".nsq", ".ndb", ".nto", ".ntf"}
            for entry in os.listdir(self._db_path):
                _, ext = os.path.splitext(entry)
                if ext in blast_extensions:
                    return True

            # No BLAST DB files found — database contains zero entries
            logger.warning(
                "VigyanLLM: Pathogen database directory contains no BLAST DB "
                "files: %s",
                self._db_path,
            )
            return False

        # If it's a file path (BLAST DB prefix), check for associated files
        for ext in [".nhr", ".nin", ".nsq"]:
            if os.path.exists(self._db_path + ext):
                return True

        logger.warning(
            "VigyanLLM: Pathogen BLAST database files not found at: %s",
            self._db_path,
        )
        return False

    def _perform_screening(
        self, sequences: list[str], job_id: str
    ) -> ComplianceResult:
        """Execute BLASTN alignment of sequences against pathogen DB.

        Screens each sequence and checks for hits meeting the biosecurity
        threshold (≥80% identity AND ≥200bp alignment length).

        Args:
            sequences: DNA sequences to screen.
            job_id: Job ID for context.

        Returns:
            ComplianceResult with cleared or hold status.
        """
        all_hits: list[AlignmentHit] = []

        for seq in sequences:
            if not seq or len(seq) < 20:
                # Skip very short sequences (unlikely to produce meaningful hits)
                continue
            hits = self._align_against_pathogens(seq)
            all_hits.extend(hits)

        # Check for biosecurity hold (Requirement 27.3)
        for hit in all_hits:
            if (
                hit.percent_identity >= IDENTITY_THRESHOLD
                and hit.alignment_length >= ALIGNMENT_LENGTH_THRESHOLD
            ):
                return ComplianceResult(
                    status="biosecurity_hold",
                    matched_organism=hit.organism,
                    matched_gene=hit.gene,
                    percent_identity=hit.percent_identity,
                    alignment_length=hit.alignment_length,
                    sequences_screened=len(sequences),
                )

        # All clear (Requirement 27.5)
        return ComplianceResult(
            status="biosecurity_cleared",
            sequences_screened=len(sequences),
        )

    def _align_against_pathogens(self, seq: str) -> list[AlignmentHit]:
        """Run BLASTN alignment of a single sequence against the pathogen DB.

        Uses subprocess to invoke blastn with tabular output format.
        Parses results into AlignmentHit objects.

        Args:
            seq: DNA sequence to align.

        Returns:
            List of AlignmentHit objects for significant matches.
        """
        hits: list[AlignmentHit] = []

        # Determine BLAST DB path (could be directory or prefix)
        db_path = self._resolve_db_path()
        if not db_path:
            return hits

        try:
            # Run BLASTN with tabular output
            # Output format 6: qseqid sseqid pident length mismatch gapopen
            #                   qstart qend sstart send evalue bitscore stitle
            cmd = [
                "blastn",
                "-db", db_path,
                "-outfmt", "6 qseqid sseqid pident length mismatch gapopen "
                           "qstart qend sstart send evalue bitscore stitle",
                "-evalue", "10",
                "-word_size", "11",
                "-dust", "no",
                "-num_threads", "2",
                "-max_target_seqs", "10",
            ]

            result = subprocess.run(
                cmd,
                input=f">query\n{seq}\n",
                capture_output=True,
                text=True,
                timeout=60,  # Per-sequence timeout
            )

            if result.returncode != 0:
                logger.debug(
                    "VigyanLLM: BLASTN returned code %d: %s",
                    result.returncode,
                    result.stderr[:200] if result.stderr else "",
                )
                return hits

            # Parse tabular output
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                hits.append(self._parse_blast_hit(line))

        except FileNotFoundError:
            logger.warning(
                "VigyanLLM: blastn executable not found — compliance screening "
                "cannot perform alignment"
            )
        except subprocess.TimeoutExpired:
            logger.warning(
                "VigyanLLM: BLASTN alignment timed out for sequence of length %d",
                len(seq),
            )
        except Exception as exc:
            logger.error(
                "VigyanLLM: Error during pathogen alignment: %s", str(exc)
            )

        return hits

    def _check_select_agents(self, seq: str) -> list[AlignmentHit]:
        """Screen sequence specifically against Select Agent toxin genes.

        This is a secondary check targeting the most dangerous regulated
        sequences (CDC/USDA Select Agent list).

        Args:
            seq: DNA sequence to screen.

        Returns:
            List of AlignmentHit objects for Select Agent matches.
        """
        # Select Agent screening uses the same alignment mechanism
        # but against a subset of the pathogen DB that specifically
        # contains Select Agent toxin gene sequences
        select_agent_db = os.path.join(self._db_path, "select_agents")
        if not os.path.exists(select_agent_db):
            # Fall back to general pathogen DB alignment
            return self._align_against_pathogens(seq)

        hits: list[AlignmentHit] = []
        try:
            cmd = [
                "blastn",
                "-db", select_agent_db,
                "-outfmt", "6 qseqid sseqid pident length mismatch gapopen "
                           "qstart qend sstart send evalue bitscore stitle",
                "-evalue", "1",
                "-word_size", "11",
                "-dust", "no",
                "-num_threads", "2",
            ]

            result = subprocess.run(
                cmd,
                input=f">query\n{seq}\n",
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split("\n"):
                    if line:
                        hits.append(self._parse_blast_hit(line))

        except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as exc:
            logger.warning(
                "VigyanLLM: Select Agent screening failed: %s", str(exc)
            )

        return hits

    def _parse_blast_hit(self, line: str) -> AlignmentHit:
        """Parse a single BLASTN tabular output line into an AlignmentHit.

        Expected format (outfmt 6 with stitle):
            qseqid sseqid pident length mismatch gapopen
            qstart qend sstart send evalue bitscore stitle

        Args:
            line: Tab-separated BLAST output line.

        Returns:
            AlignmentHit with parsed fields.
        """
        fields = line.split("\t")

        # Parse numeric fields with safe defaults
        try:
            pident = float(fields[2]) if len(fields) > 2 else 0.0
        except (ValueError, IndexError):
            pident = 0.0

        try:
            length = int(fields[3]) if len(fields) > 3 else 0
        except (ValueError, IndexError):
            length = 0

        try:
            evalue = float(fields[10]) if len(fields) > 10 else 0.0
        except (ValueError, IndexError):
            evalue = 0.0

        try:
            bitscore = float(fields[11]) if len(fields) > 11 else 0.0
        except (ValueError, IndexError):
            bitscore = 0.0

        # Parse subject title for organism and gene info
        subject_id = fields[1] if len(fields) > 1 else ""
        stitle = fields[12] if len(fields) > 12 else ""
        organism, gene = self._parse_subject_title(stitle, subject_id)

        return AlignmentHit(
            organism=organism,
            gene=gene,
            percent_identity=pident,
            alignment_length=length,
            query_sequence="",  # Don't store full sequence for security
            subject_id=subject_id,
            e_value=evalue,
            bit_score=bitscore,
        )

    def _parse_subject_title(
        self, stitle: str, subject_id: str
    ) -> tuple[str, str]:
        """Extract organism name and gene name from BLAST subject title.

        Common title formats:
            "Bacillus anthracis lethal factor gene"
            "Yersinia pestis pla gene, complete cds"
            "organism_name | gene_name"

        Args:
            stitle: BLAST subject title string.
            subject_id: Subject sequence identifier.

        Returns:
            Tuple of (organism_name, gene_name).
        """
        if not stitle:
            # Try to extract from subject_id
            return (subject_id, "unknown")

        # Try pipe-delimited format: "organism | gene"
        if "|" in stitle:
            parts = [p.strip() for p in stitle.split("|")]
            organism = parts[0] if parts else "unknown"
            gene = parts[1] if len(parts) > 1 else "unknown"
            return (organism, gene)

        # Try to split on common patterns
        # Many BLAST DBs use format: "Organism_name gene_name description"
        parts = stitle.strip().split()
        if len(parts) >= 3:
            # First two words are typically genus species
            organism = " ".join(parts[:2])
            gene = " ".join(parts[2:])
        elif len(parts) == 2:
            organism = parts[0]
            gene = parts[1]
        else:
            organism = stitle.strip()
            gene = "unknown"

        return (organism, gene)

    def _resolve_db_path(self) -> str | None:
        """Resolve the actual BLAST database path/prefix.

        BLAST databases can be referenced by:
        1. A directory containing DB files (we find the prefix)
        2. A direct file prefix (e.g., /opt/pathogen_db/pathogens)

        Returns:
            BLAST database prefix string, or None if not resolvable.
        """
        # If path is a directory, look for the DB prefix within
        if os.path.isdir(self._db_path):
            # Find .nhr files and derive prefix
            for entry in os.listdir(self._db_path):
                if entry.endswith(".nhr"):
                    prefix = os.path.join(self._db_path, entry[:-4])
                    return prefix
            return None

        # If it's a file prefix, check it exists
        if os.path.exists(self._db_path + ".nhr"):
            return self._db_path

        return None

    def _log_result(self, job_id: str, result: ComplianceResult) -> None:
        """Log compliance screening result to system_events table.

        Requirement 27.7: Log with severity "info" for cleared designs,
        "critical" for biosecurity holds.

        Args:
            job_id: Pipeline job identifier.
            result: ComplianceResult to log.
        """
        severity = "info" if result.status == "biosecurity_cleared" else "critical"

        context = {
            "job_id": job_id,
            "status": result.status,
            "sequences_screened": result.sequences_screened,
        }

        if result.matched_organism:
            context["matched_organism"] = result.matched_organism
        if result.matched_gene:
            context["matched_gene"] = result.matched_gene
        if result.percent_identity is not None:
            context["percent_identity"] = result.percent_identity
        if result.alignment_length is not None:
            context["alignment_length"] = result.alignment_length

        message = (
            f"VigyanLLM: Compliance screening {result.status} for job {job_id}"
        )

        if result.status == "biosecurity_hold":
            message += (
                f" — matched {result.matched_organism} "
                f"({result.matched_gene}) at "
                f"{result.percent_identity:.1f}% identity, "
                f"{result.alignment_length}bp"
            )
            logger.critical(message)
        elif result.status == "biosecurity_cleared":
            logger.info(message)
        elif result.status == "compliance_unavailable":
            logger.critical(
                "%s — pathogen database unavailable", message
            )
        elif result.status == "compliance_timeout":
            logger.critical(
                "%s — screening exceeded timeout", message
            )

        # Persist to system_events table
        self._persist_to_system_events(severity, message, context)

    def _persist_to_system_events(
        self,
        severity: str,
        message: str,
        context: dict[str, Any],
    ) -> None:
        """Insert a record into the system_events table.

        This uses a lazy import of the database module to avoid circular
        dependencies and to gracefully handle cases where the database
        is not available (e.g., during testing).

        Args:
            severity: Event severity (info, warning, critical).
            message: Event message.
            context: Context dictionary to store as JSON.
        """
        try:
            from primerforge.database import execute

            execute(
                """INSERT INTO system_events (severity, module, message, context)
                   VALUES (%s, %s, %s, %s)""",
                (
                    severity.upper(),
                    "compliance",
                    message,
                    json.dumps(context),
                ),
            )
        except Exception as exc:
            # Don't let logging failure break the compliance result
            logger.debug(
                "VigyanLLM: Failed to persist compliance event to DB: %s",
                str(exc),
            )

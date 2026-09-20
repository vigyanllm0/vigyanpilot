"""
VigyanLLM — Virtual Screening Engine

Batch processing for virtual screening campaigns:
1. Multi-ligand screening (100-10K compounds)
2. Parallel job management (file-based queue)
3. Progress tracking and streaming
4. Results aggregation and ranking
5. CSV/SDF export

Usage:
    from virtual_screener import VirtualScreeningCampaign
    campaign = VirtualScreeningCampaign(receptor_pdb, ligand_list)
    campaign.run()
"""

import csv
import io
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

MAX_CONCURRENT_JOBS = 4        # Parallel Vina instances
MAX_LIGANDS_PER_BATCH = 500    # Max ligands per campaign
BATCH_TIMEOUT = 300            # Seconds per ligand
PROGRESS_FILE_INTERVAL = 10    # Update progress file every N ligands

# Campaign status
STATUS_PENDING = 'pending'
STATUS_RUNNING = 'running'
STATUS_COMPLETE = 'complete'
STATUS_FAILED = 'failed'
STATUS_PARTIAL = 'partial'  # Some ligands failed


@dataclass
class LigandResult:
    """Result for a single ligand in the campaign."""
    ligand_id: str
    smiles: str
    status: str               # 'complete', 'failed', 'timeout'
    vina_score: float = 0.0
    gnina_score: float = 0.0
    consensus_score: float = 0.0
    ligand_efficiency: float = 0.0
    heavy_atom_count: int = 0
    error: str = ''
    processing_time: float = 0.0


@dataclass
class CampaignProgress:
    """Campaign progress tracking."""
    campaign_id: str
    status: str
    total_ligands: int
    completed: int
    failed: int
    running: int
    pending: int
    percent_complete: float
    elapsed_seconds: float
    eta_seconds: float
    top_hits: list            # Top 10 results


@dataclass
class ScreeningCampaign:
    """Complete virtual screening campaign."""
    campaign_id: str
    receptor_pdb: str
    ligands: list             # List of {id, smiles} dicts
    results: list             # List of LigandResult
    status: str
    created_at: float
    completed_at: float = 0.0
    progress_file: str = ''


class VirtualScreeningCampaign:
    """
    Manages a virtual screening campaign.
    """

    def __init__(self, receptor_pdb: str, ligands: list, campaign_id: str = None):
        """
        Args:
            receptor_pdb: Receptor structure in PDB format
            ligands: List of dicts with 'id' and 'smiles' keys
            campaign_id: Optional campaign identifier
        """
        if len(ligands) > MAX_LIGANDS_PER_BATCH:
            raise ValueError(f"Too many ligands ({len(ligands)}). Max: {MAX_LIGANDS_PER_BATCH}")

        self.campaign_id = campaign_id or f"VS_{int(time.time())}_{os.getpid()}"
        self.receptor_pdb = receptor_pdb
        self.ligands = ligands
        self.results = []
        self.status = STATUS_PENDING
        self.created_at = time.time()
        self.completed_at = 0.0

        # Progress file
        self.progress_dir = Path('/tmp/vigyanllm_screening')
        self.progress_dir.mkdir(parents=True, exist_ok=True)
        self.progress_file = self.progress_dir / f"{self.campaign_id}.json"

        logger.info("Created campaign %s with %d ligands", self.campaign_id, len(ligands))

    def _update_progress(self):
        """Write progress to file for streaming."""
        completed = sum(1 for r in self.results if r.status == 'complete')
        failed = sum(1 for r in self.results if r.status == 'failed')
        running = sum(1 for r in self.results if r.status == 'running')
        pending = len(self.ligands) - completed - failed - running

        elapsed = time.time() - self.created_at
        rate = completed / max(1, elapsed) * 3600  # ligands/hour
        remaining = pending + running
        eta = remaining / max(1, rate) * 3600 if rate > 0 else 0

        # Top hits
        successful = [r for r in self.results if r.status == 'complete']
        successful.sort(key=lambda r: r.consensus_score)
        top_hits = [
            {
                'ligand_id': r.ligand_id,
                'smiles': r.smiles,
                'consensus_score': r.consensus_score,
                'vina_score': r.vina_score,
                'ligand_efficiency': r.ligand_efficiency,
            }
            for r in successful[:10]
        ]

        progress = CampaignProgress(
            campaign_id=self.campaign_id,
            status=self.status,
            total_ligands=len(self.ligands),
            completed=completed,
            failed=failed,
            running=running,
            pending=pending,
            percent_complete=round(100 * (completed + failed) / max(1, len(self.ligands)), 1),
            elapsed_seconds=round(elapsed, 1),
            eta_seconds=round(eta, 1),
            top_hits=top_hits,
        )

        try:
            with open(self.progress_file, 'w') as f:
                json.dump({
                    'campaign_id': progress.campaign_id,
                    'status': progress.status,
                    'total': progress.total_ligands,
                    'completed': progress.completed,
                    'failed': progress.failed,
                    'running': progress.running,
                    'pending': progress.pending,
                    'percent': progress.percent_complete,
                    'elapsed': progress.elapsed_seconds,
                    'eta': progress.eta_seconds,
                    'top_hits': progress.top_hits,
                }, f)
        except Exception as e:
            logger.warning("Failed to write progress: %s", e)

    def _dock_single_ligand(self, ligand: dict) -> LigandResult:
        """Dock a single ligand (called in thread pool)."""
        ligand_id = ligand.get('id', 'unknown')
        smiles = ligand.get('smiles', '')

        start_time = time.time()

        try:
            # Import here to avoid circular imports
            from primerforge.pipelines.docking_engine import VinaEngine, GNINAEngine

            # Run Vina
            vina = VinaEngine()
            vina_result = vina.dock(
                receptor_pdb=self.receptor_pdb,
                ligand_smiles=smiles,
                center=[0, 0, 0],  # Would be set from pocket detection
                box_size=[20, 20, 20],
            )

            vina_score = vina_result.get('score', 0)

            # Run GNINA if available
            gnina_score = 0
            try:
                gnina = GNINAEngine()
                gnina_result = gnina.dock(
                    receptor_pdb=self.receptor_pdb,
                    ligand_smiles=smiles,
                )
                gnina_score = gnina_result.get('score', 0)
            except Exception:
                pass

            # Consensus score
            consensus = (vina_score + gnina_score) / 2 if gnina_score else vina_score

            # Ligand efficiency
            heavy_atoms = self._count_heavy_atoms(smiles)
            le = abs(consensus) / max(1, heavy_atoms)

            elapsed = time.time() - start_time

            return LigandResult(
                ligand_id=ligand_id,
                smiles=smiles,
                status='complete',
                vina_score=round(vina_score, 3),
                gnina_score=round(gnina_score, 3),
                consensus_score=round(consensus, 3),
                ligand_efficiency=round(le, 4),
                heavy_atom_count=heavy_atoms,
                processing_time=round(elapsed, 2),
            )

        except Exception as e:
            elapsed = time.time() - start_time
            return LigandResult(
                ligand_id=ligand_id,
                smiles=smiles,
                status='failed',
                error=str(e),
                processing_time=round(elapsed, 2),
            )

    def _count_heavy_atoms(self, smiles: str) -> int:
        """Count non-hydrogen atoms in SMILES."""
        count = 0
        i = 0
        while i < len(smiles):
            ch = smiles[i]
            if ch.isupper() and ch != 'H':
                count += 1
                if i + 1 < len(smiles) and smiles[i+1].islower():
                    i += 1
            i += 1
        return max(count, 5)

    def run(self, max_workers: int = MAX_CONCURRENT_JOBS) -> ScreeningCampaign:
        """
        Run the screening campaign.

        Args:
            max_workers: Number of parallel workers

        Returns:
            ScreeningCampaign with results
        """
        self.status = STATUS_RUNNING
        self._update_progress()

        logger.info("Starting campaign %s (%d ligands, %d workers)",
                    self.campaign_id, len(self.ligands), max_workers)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for i, ligand in enumerate(self.ligands):
                future = executor.submit(self._dock_single_ligand, ligand)
                futures[future] = i

            for future in as_completed(futures):
                try:
                    result = future.result(timeout=BATCH_TIMEOUT)
                    self.results.append(result)

                    if len(self.results) % PROGRESS_FILE_INTERVAL == 0:
                        self._update_progress()
                        logger.info("Campaign %s: %d/%d completed",
                                   self.campaign_id, len(self.results), len(self.ligands))

                except Exception as e:
                    idx = futures[future]
                    ligand = self.ligands[idx]
                    self.results.append(LigandResult(
                        ligand_id=ligand.get('id', 'unknown'),
                        smiles=ligand.get('smiles', ''),
                        status='failed',
                        error=str(e),
                    ))

        # Determine final status
        completed = sum(1 for r in self.results if r.status == 'complete')
        failed = sum(1 for r in self.results if r.status == 'failed')

        if completed == len(self.ligands):
            self.status = STATUS_COMPLETE
        elif completed > 0:
            self.status = STATUS_PARTIAL
        else:
            self.status = STATUS_FAILED

        self.completed_at = time.time()
        self._update_progress()

        elapsed = self.completed_at - self.created_at
        logger.info("Campaign %s complete: %d/%d succeeded in %.1fs",
                    self.campaign_id, completed, len(self.ligands), elapsed)

        return self.to_campaign()

    def to_campaign(self) -> ScreeningCampaign:
        """Convert to ScreeningCampaign dataclass."""
        return ScreeningCampaign(
            campaign_id=self.campaign_id,
            receptor_pdb=self.receptor_pdb,
            ligands=self.ligands,
            results=self.results,
            status=self.status,
            created_at=self.created_at,
            completed_at=self.completed_at,
            progress_file=str(self.progress_file),
        )

    def get_progress(self) -> dict:
        """Get current campaign progress."""
        try:
            if self.progress_file.exists():
                with open(self.progress_file) as f:
                    return json.load(f)
        except Exception:
            pass
        return {'status': self.status, 'completed': 0, 'total': len(self.ligands)}

    def export_csv(self) -> str:
        """Export results as CSV string."""
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            'ligand_id', 'smiles', 'status', 'consensus_score',
            'vina_score', 'gnina_score', 'ligand_efficiency',
            'heavy_atom_count', 'processing_time', 'error'
        ])

        # Sort by consensus score
        sorted_results = sorted(self.results, key=lambda r: r.consensus_score)

        for r in sorted_results:
            writer.writerow([
                r.ligand_id, r.smiles, r.status, r.consensus_score,
                r.vina_score, r.gnina_score, r.ligand_efficiency,
                r.heavy_atom_count, r.processing_time, r.error,
            ])

        return output.getvalue()

    def export_sdf(self) -> str:
        """Export top results as SDF (simplified — scores in properties)."""
        sdf_blocks = []

        successful = [r for r in self.results if r.status == 'complete']
        successful.sort(key=lambda r: r.consensus_score)

        for r in successful[:100]:  # Top 100
            block = f"""{r.ligand_id}
     VigyanLLM Virtual Screening
     Consensus: {r.consensus_score:.3f} kcal/mol

  0  0  0  0  0  0  0  0  0  0999 V2000
M  END
> <consensus_score>
{r.consensus_score:.3f}

> <vina_score>
{r.vina_score:.3f}

> <ligand_efficiency>
{r.ligand_efficiency:.4f}

> <ligand_id>
{r.ligand_id}

$$$$
"""
            sdf_blocks.append(block)

        return ''.join(sdf_blocks)


def campaign_to_dict(campaign: ScreeningCampaign) -> dict:
    """Convert campaign to JSON-serializable dict."""
    return {
        'campaign_id': campaign.campaign_id,
        'status': campaign.status,
        'total_ligands': len(campaign.ligands),
        'results': [
            {
                'ligand_id': r.ligand_id,
                'smiles': r.smiles,
                'status': r.status,
                'consensus_score': r.consensus_score,
                'vina_score': r.vina_score,
                'gnina_score': r.gnina_score,
                'ligand_efficiency': r.ligand_efficiency,
                'heavy_atom_count': r.heavy_atom_count,
                'processing_time': r.processing_time,
                'error': r.error,
            }
            for r in campaign.results
        ],
        'created_at': campaign.created_at,
        'completed_at': campaign.completed_at,
        'elapsed': round(campaign.completed_at - campaign.created_at, 1) if campaign.completed_at else 0,
        'summary': {
            'completed': sum(1 for r in campaign.results if r.status == 'complete'),
            'failed': sum(1 for r in campaign.results if r.status == 'failed'),
            'best_score': min((r.consensus_score for r in campaign.results if r.status == 'complete'), default=0),
            'mean_score': round(
                sum(r.consensus_score for r in campaign.results if r.status == 'complete') /
                max(1, sum(1 for r in campaign.results if r.status == 'complete')), 3
            ),
        },
    }

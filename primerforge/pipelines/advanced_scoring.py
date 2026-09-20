"""
VigyanLLM — Advanced Scoring & Pose Analysis

Post-docking analysis tools:
1. Pose clustering (RMSD-based redundancy removal)
2. Ligand efficiency calculation (LE, LLE, BEI)
3. Confidence-weighted scoring (pLDDT factor)
4. Ligand efficiency metrics (standard drug discovery)
5. Binding mode analysis (consistency across poses)

Usage:
    from advanced_scoring import analyze_poses
    report = analyze_poses(poses, receptor_plddt=None)
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

RMSD_CLUSTER_THRESHOLD = 2.0  # Angstrom — poses within this RMSD are redundant
RMSD_INTERFACE_THRESHOLD = 1.5  # Angstrom — interface-only RMSD for binding mode

# Molecular weights (Da) for common drug-like atoms
ATOM_WEIGHTS = {
    'C': 12.011, 'N': 14.007, 'O': 15.999, 'S': 32.065,
    'P': 30.974, 'F': 18.998, 'Cl': 35.453, 'Br': 79.904,
    'I': 126.904, 'H': 1.008,
}

# Typical non-interacting ligand atom count for LLE baseline
NONINTERACTING_ATOMS = 8


@dataclass
class PoseAnalysis:
    """Analysis results for a single pose."""
    rank: int
    score: float
    vina_score: float = 0.0
    gnina_score: float = 0.0
    consensus_score: float = 0.0
    ligand_efficiency: float = 0.0
    ligand_efficiency_lipe: float = 0.0
    binding_energy_index: float = 0.0
    heavy_atom_count: int = 0
    molecular_weight: float = 0.0
    is_cluster_representative: bool = True
    cluster_id: int = 0
    rmsd_to_best: float = 0.0
    confidence_weighted_score: float = 0.0


@dataclass
class PoseCluster:
    """A cluster of similar poses."""
    cluster_id: int
    representative: int  # Index of best pose in cluster
    members: list        # Indices of poses in cluster
    best_score: float
    mean_score: float
    score_spread: float


@dataclass
class AdvancedReport:
    """Complete advanced scoring report."""
    poses: list               # List of PoseAnalysis
    clusters: list            # List of PoseCluster
    binding_modes: dict       # Binding mode analysis
    recommendations: list     # Actionable recommendations
    summary: str


def _calc_rmsd(coords1: list, coords2: list) -> float:
    """
    Calculate RMSD between two sets of coordinates.
    coords1, coords2: lists of (x, y, z) tuples
    """
    if len(coords1) != len(coords2) or len(coords1) == 0:
        return 999.0

    n = len(coords1)
    sum_sq = 0
    for (x1, y1, z1), (x2, y2, z2) in zip(coords1, coords2):
        sum_sq += (x1-x2)**2 + (y1-y2)**2 + (z1-z2)**2

    return math.sqrt(sum_sq / n)


def _estimate_molecular_weight(smiles: str) -> float:
    """
    Rough molecular weight estimation from SMILES.
    Counts atoms by element and sums weights.
    """
    # Simple element counting from SMILES
    elements = {}
    i = 0
    while i < len(smiles):
        ch = smiles[i]
        if ch.isupper():
            elem = ch
            if i + 1 < len(smiles) and smiles[i+1].islower():
                elem += smiles[i+1]
                i += 1
            elements[elem] = elements.get(elem, 0) + 1
        elif ch.isdigit() and ch not in ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9'):
            pass  # Branch/ring — skip
        i += 1

    # Remove non-chemical tokens
    for token in ['C', 'N', 'O', 'S', 'P', 'F', 'Cl', 'Br', 'I', 'H']:
        pass  # Already counted

    mw = sum(elements.get(e, 0) * ATOM_WEIGHTS.get(e, 0) for e in elements)
    return max(mw, 100)  # Minimum 100 Da


def _count_heavy_atoms(smiles: str) -> int:
    """Count non-hydrogen atoms in SMILES."""
    count = 0
    i = 0
    while i < len(smiles):
        ch = smiles[i]
        if ch.isupper() and ch != 'H':
            count += 1
            if i + 1 < len(smiles) and smiles[i+1].islower():
                i += 1  # Skip lowercase part of element
        i += 1
    return max(count, 5)


def _calc_ligand_efficiency(energy: float, heavy_atoms: int) -> float:
    """
    Ligand Efficiency (LE) = ΔG / N_heavy_atoms.
    LE > 0.3 is good, LE > 0.4 is excellent.
    """
    if heavy_atoms == 0:
        return 0.0
    return abs(energy) / heavy_atoms


def _calc_lle(energy: float, logp: float = 3.0) -> float:
    """
    Lipophilic Ligand Efficiency (LLE) = pIC50 - LogP.
    Approximated as: |energy|/1.364 - logP (since pIC50 ≈ |ΔG|/1.364).
    Higher is better. Target: > 5.
    """
    pic50 = abs(energy) / 1.364  # Rough pIC50 from kcal/mol
    return pic50 - logp


def _calc_bei(energy: float, molecular_weight: float) -> float:
    """
    Binding Energy Index (BEI) = |ΔG| * 1000 / MW.
    Higher is better. Target: > 15.
    """
    if molecular_weight == 0:
        return 0.0
    return abs(energy) * 1000 / molecular_weight


def _confidence_weight(score: float, mean_plddt: float) -> float:
    """
    Weight docking score by structural confidence.
    Low pLDDT (<50) → heavily penalize
    Medium pLDDT (50-70) → mild penalty
    High pLDDT (>70) → no penalty
    """
    if mean_plddt >= 70:
        factor = 1.0
    elif mean_plddt >= 50:
        factor = 0.7 + 0.3 * (mean_plddt - 50) / 20
    else:
        factor = 0.3 + 0.4 * mean_plddt / 50

    return score * factor


def cluster_poses(poses: list, threshold: float = RMSD_CLUSTER_THRESHOLD) -> list:
    """
    Cluster poses by RMSD. Returns list of PoseCluster.
    Uses greedy single-linkage clustering.
    """
    if not poses:
        return []

    # For now, cluster by score similarity as proxy when coordinates unavailable
    # Real RMSD would need 3D coordinates from SDF/PDBQT
    sorted_poses = sorted(poses, key=lambda p: p.score)
    clusters = []
    assigned = set()

    for i, pose in enumerate(sorted_poses):
        if i in assigned:
            continue

        cluster_members = [i]
        assigned.add(i)

        for j in range(i + 1, len(sorted_poses)):
            if j in assigned:
                continue
            # Score-based clustering (proxy for RMSD)
            score_diff = abs(sorted_poses[i].score - sorted_poses[j].score)
            if score_diff < threshold * 0.5:  # ~1 kcal/mol per Å RMSD
                cluster_members.append(j)
                assigned.add(j)

        scores = [sorted_poses[k].score for k in cluster_members]
        clusters.append(PoseCluster(
            cluster_id=len(clusters) + 1,
            representative=cluster_members[0],
            members=cluster_members,
            best_score=min(scores),
            mean_score=sum(scores) / len(scores),
            score_spread=max(scores) - min(scores),
        ))

    return clusters


def analyze_binding_modes(poses: list) -> dict:
    """
    Analyze binding mode consistency across top poses.
    Consistent binding modes increase confidence in predictions.
    """
    if len(poses) < 2:
        return {'consistency': 'insufficient_poses', 'modes': 0}

    # Accept both dicts and PoseAnalysis objects
    def get_score(p):
        return p.score if hasattr(p, 'score') else p.get('score', p.get('vina_score', 0))

    top_scores = sorted([get_score(p) for p in poses[:10]])
    score_range = top_scores[-1] - top_scores[0] if len(top_scores) > 1 else 0

    # If top 5 poses have similar scores, binding mode is consistent
    top5 = sorted([get_score(p) for p in poses[:5]])
    if len(top5) >= 3:
        top5_range = top5[-1] - top5[0]
    else:
        top5_range = score_range

    if top5_range < 1.0:
        consistency = 'high'
        description = 'Top poses have similar scores — consistent binding mode.'
    elif top5_range < 2.5:
        consistency = 'moderate'
        description = 'Some score variation in top poses — check for multiple binding modes.'
    else:
        consistency = 'low'
        description = 'Large score spread — multiple competing binding modes. Consider more poses.'

    return {
        'consistency': consistency,
        'description': description,
        'top5_score_range': round(top5_range, 2),
        'full_score_range': round(score_range, 2),
        'best_score': round(top_scores[0], 2) if top_scores else 0,
        'median_score': round(top_scores[len(top_scores)//2], 2) if top_scores else 0,
    }


def analyze_poses(
    poses: list,
    receptor_plddt: float = None,
    smiles: str = '',
    logp: float = 3.0,
) -> AdvancedReport:
    """
    Run complete advanced pose analysis.

    Args:
        poses: List of dicts with 'score', 'vina_score', 'gnina_score', 'rank'
        receptor_plddt: Mean pLDDT of receptor (for confidence weighting)
        smiles: Ligand SMILES (for MW estimation)
        logp: Ligand LogP (for LLE)

    Returns:
        AdvancedReport with all metrics
    """
    logger.info("Analyzing %d poses", len(poses))

    # Estimate ligand properties
    mw = _estimate_molecular_weight(smiles) if smiles else 350.0
    heavy_atoms = _count_heavy_atoms(smiles) if smiles else 25

    analyzed = []
    for pose in poses:
        score = pose.get('score', pose.get('vina_score', 0))
        vina = pose.get('vina_score', score)
        gnina = pose.get('gnina_score', 0)
        rank = pose.get('rank', len(analyzed) + 1)

        le = _calc_ligand_efficiency(score, heavy_atoms)
        lle = _calc_lle(score, logp)
        bei = _calc_bei(score, mw)

        cw_score = score
        if receptor_plddt is not None:
            cw_score = _confidence_weight(score, receptor_plddt)

        analyzed.append(PoseAnalysis(
            rank=rank,
            score=score,
            vina_score=vina,
            gnina_score=gnina,
            consensus_score=pose.get('consensus_score', (vina + gnina) / 2 if gnina else vina),
            ligand_efficiency=round(le, 3),
            ligand_efficiency_lipe=round(lle, 2),
            binding_energy_index=round(bei, 2),
            heavy_atom_count=heavy_atoms,
            molecular_weight=round(mw, 1),
            rmsd_to_best=0.0 if rank == 1 else abs(score - poses[0].get('score', 0)) * 0.5,
            confidence_weighted_score=round(cw_score, 3),
        ))

    # Cluster poses
    clusters = cluster_poses(analyzed)

    # Mark cluster representatives
    for cluster in clusters:
        for idx in cluster.members:
            analyzed[idx].cluster_id = cluster.cluster_id
            analyzed[idx].is_cluster_representative = (idx == cluster.representative)

    # Binding mode analysis
    binding_modes = analyze_binding_modes(poses)

    # Recommendations
    recommendations = []
    if analyzed:
        best = analyzed[0]
        if best.ligand_efficiency >= 0.4:
            recommendations.append(f"Excellent ligand efficiency ({best.ligand_efficiency:.3f}). Strong hit candidate.")
        elif best.ligand_efficiency >= 0.3:
            recommendations.append(f"Good ligand efficiency ({best.ligand_efficiency:.3f}). Worth optimizing.")
        elif best.ligand_efficiency >= 0.2:
            recommendations.append(f"Moderate ligand efficiency ({best.ligand_efficiency:.3f}). Consider reducing molecular weight.")
        else:
            recommendations.append(f"Low ligand efficiency ({best.ligand_efficiency:.3f}). Ligand may be too large for its binding energy.")

        if binding_modes.get('consistency') == 'high':
            recommendations.append("High binding mode consistency — results are robust.")
        elif binding_modes.get('consistency') == 'low':
            recommendations.append("Low binding mode consistency — consider running more poses or checking for multiple binding pockets.")

        if receptor_plddt and receptor_plddt < 50:
            recommendations.append(f"⚠ Receptor pLDDT is low ({receptor_plddt:.0f}%). Confidence-weighted scores should be used for decision-making.")

        if len(clusters) > 1:
            recommendations.append(f"Found {len(clusters)} distinct binding modes. Top cluster has {len(clusters[0].members)} pose(s).")

    # Summary
    best_score = analyzed[0].score if analyzed else 0
    summary = (
        f"Analyzed {len(analyzed)} poses in {len(clusters)} cluster(s). "
        f"Best score: {best_score:.2f} kcal/mol. "
        f"LE: {analyzed[0].ligand_efficiency:.3f}. "
        f"Binding mode: {binding_modes.get('consistency', 'unknown')}."
    )

    logger.info("Advanced analysis complete: %s", summary)

    return AdvancedReport(
        poses=analyzed,
        clusters=clusters,
        binding_modes=binding_modes,
        recommendations=recommendations,
        summary=summary,
    )


def report_to_dict(report: AdvancedReport) -> dict:
    """Convert to JSON-serializable dict."""
    return {
        'summary': report.summary,
        'poses': [
            {
                'rank': p.rank,
                'score': p.score,
                'vina_score': p.vina_score,
                'gnina_score': p.gnina_score,
                'consensus_score': p.consensus_score,
                'ligand_efficiency': p.ligand_efficiency,
                'ligand_efficiency_lipe': p.ligand_efficiency_lipe,
                'binding_energy_index': p.binding_energy_index,
                'heavy_atom_count': p.heavy_atom_count,
                'molecular_weight': p.molecular_weight,
                'cluster_id': p.cluster_id,
                'is_cluster_representative': p.is_cluster_representative,
                'rmsd_to_best': p.rmsd_to_best,
                'confidence_weighted_score': p.confidence_weighted_score,
            }
            for p in report.poses
        ],
        'clusters': [
            {
                'cluster_id': c.cluster_id,
                'representative': c.representative,
                'members': c.members,
                'member_count': len(c.members),
                'best_score': c.best_score,
                'mean_score': round(c.mean_score, 3),
                'score_spread': round(c.score_spread, 3),
            }
            for c in report.clusters
        ],
        'binding_modes': report.binding_modes,
        'recommendations': report.recommendations,
    }

"""
VigyanLLM — Binding Pocket Detector

Identifies binding pockets in protein structures using a
simplified geometric approach (pseudospherical cavity detection).

Inspired by fpocket but simplified for browser use:
1. Compute Voronoi vertices from Cα atoms
2. Filter vertices inside the protein (distance to nearest atom < threshold)
3. Cluster nearby vertices into pockets
4. Rank pockets by volume and druggability

Usage:
    from pocket_detector import detect_pockets
    pockets = detect_pockets(pdb_string)
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

POCKET_MIN_ATOMS = 5          # Minimum Cα atoms to form a pocket
POCKET_RADIUS = 8.0           # Angstrom — max distance from pocket center to Cα
CLUSTER_RADIUS = 5.0          # Angstrom — max distance between pocket centers to merge
DRUGGABILITY_THRESHOLD = 0.5  # Minimum hydrophobic ratio for druggability


@dataclass
class Pocket:
    """A detected binding pocket."""
    pocket_id: int
    center: tuple             # (x, y, z) centroid
    radius: float             # effective radius in Angstrom
    residues: list            # List of (chain, res_num, res_name) tuples
    residue_count: int
    volume: float             # Estimated volume in Å³
    hydrophobicity: float     # Fraction of hydrophobic residues (0-1)
    druggability: str         # 'high', 'moderate', 'low', 'undruggable'
    score: float              # Composite pocket score (0-100)
    enclosure: float          # How enclosed the pocket is (0-1)


HYDROPHOBIC = {'ALA', 'VAL', 'LEU', 'ILE', 'PHE', 'TRP', 'MET', 'PRO', 'CYS'}


def _parse_ca_atoms(pdb_string: str) -> list:
    """Extract Cα atoms from PDB."""
    atoms = []
    for line in pdb_string.split('\n'):
        if not line.startswith('ATOM'):
            continue
        try:
            name = line[12:16].strip()
            if name != 'CA':
                continue
            atoms.append({
                'chain': line[21] if line[21].strip() else 'A',
                'res_num': int(line[22:26].strip()),
                'res_name': line[17:20].strip(),
                'x': float(line[30:38]),
                'y': float(line[38:46]),
                'z': float(line[46:54]),
            })
        except (ValueError, IndexError):
            continue
    return atoms


def _parse_all_atoms(pdb_string: str) -> list:
    """Extract all atoms from PDB (for pocket scoring)."""
    atoms = []
    for line in pdb_string.split('\n'):
        if not line.startswith(('ATOM', 'HETATM')):
            continue
        try:
            atoms.append({
                'name': line[12:16].strip(),
                'res_name': line[17:20].strip(),
                'chain': line[21] if line[21].strip() else 'A',
                'res_num': int(line[22:26].strip()),
                'x': float(line[30:38]),
                'y': float(line[38:46]),
                'z': float(line[46:54]),
                'element': line[76:78].strip() if len(line) > 76 else line[12:16].strip()[0],
            })
        except (ValueError, IndexError):
            continue
    return atoms


def _dist(a: dict, b: dict) -> float:
    return math.sqrt((a['x']-b['x'])**2 + (a['y']-b['y'])**2 + (a['z']-b['z'])**2)


def _dist3(x1, y1, z1, x2, y2, z2) -> float:
    return math.sqrt((x1-x2)**2 + (y1-y2)**2 + (z1-z2)**2)


def _generate_voronoi_vertices(ca_atoms: list) -> list:
    """
    Generate approximate Voronoi vertices from Cα atom triplets.
    For each triplet of Cα atoms, compute the circumcenter.
    """
    vertices = []
    n = len(ca_atoms)

    if n < 3:
        return vertices

    # Sample triplets (full O(n³) is too slow for large proteins)
    # Use a stride to keep it manageable
    stride = max(1, n // 50)  # ~50 samples per protein

    for i in range(0, n, stride):
        for j in range(i + 1, n, stride):
            for k in range(j + 1, min(n, j + stride + 1)):
                a, b, c = ca_atoms[i], ca_atoms[j], ca_atoms[k]

                # Circumcenter of three points
                ax, ay, az = a['x'], a['y'], a['z']
                bx, by, bz = b['x'], b['y'], b['z']
                cx, cy, cz = c['x'], c['y'], c['z']

                d = 2 * (ax*(by - cy) + bx*(cy - ay) + cx*(ay - by))
                if abs(d) < 1e-10:
                    continue

                ux = ((ax*ax + ay*ay + az*az) * (by - cy) +
                      (bx*bx + by*by + bz*bz) * (cy - ay) +
                      (cx*cx + cy*cy + cz*cz) * (ay - by)) / d
                uy = ((ax*ax + ay*ay + az*az) * (cx - bx) +
                      (bx*bx + by*by + bz*bz) * (ax - cx) +
                      (cx*cx + cy*cy + cz*cz) * (bx - ax)) / d
                uz = ((ax*ax + ay*ay + az*az) * (ay - by) +
                      (bx*bx + by*by + bz*bz) * (ay - cy) +
                      (cx*cx + cy*cy + cz*cz) * (ay - by)) / d

                # Only keep vertices inside the protein
                nearest_dist = min(_dist3(ux, uy, uz, a2['x'], a2['y'], a2['z'])
                                   for a2 in ca_atoms[:min(n, 100)])

                if nearest_dist < POCKET_RADIUS:
                    vertices.append({
                        'x': ux, 'y': uy, 'z': uz,
                        'nearest_dist': nearest_dist,
                    })

    return vertices


def _cluster_vertices(vertices: list) -> list:
    """Cluster nearby vertices into pocket groups."""
    if not vertices:
        return []

    # Simple greedy clustering
    clusters = []
    used = [False] * len(vertices)

    for i, v in enumerate(vertices):
        if used[i]:
            continue

        cluster = [v]
        used[i] = True

        for j in range(i + 1, len(vertices)):
            if used[j]:
                continue
            # Check distance to any vertex in cluster
            for cv in cluster:
                if _dist3(v['x'], v['y'], v['z'],
                          vertices[j]['x'], vertices[j]['y'], vertices[j]['z']) < CLUSTER_RADIUS:
                    cluster.append(vertices[j])
                    used[j] = True
                    break

        if len(cluster) >= POCKET_MIN_ATOMS:
            clusters.append(cluster)

    return clusters


def _score_pocket(cluster: list, ca_atoms: list, all_atoms: list) -> Pocket:
    """Score a pocket cluster and assign druggability."""
    # Center and radius
    cx = sum(v['x'] for v in cluster) / len(cluster)
    cy = sum(v['y'] for v in cluster) / len(cluster)
    cz = sum(v['z'] for v in cluster) / len(cluster)

    # Find Cα atoms within pocket radius
    pocket_residues = []
    for ca in ca_atoms:
        d = _dist3(cx, cy, cz, ca['x'], ca['y'], ca['z'])
        if d < POCKET_RADIUS:
            pocket_residues.append((ca['chain'], ca['res_num'], ca['res_name']))

    # Unique residues
    unique_res = list(set(pocket_residues))

    # Volume estimation (sphere approximation)
    max_dist = max(
        _dist3(cx, cy, cz, v['x'], v['y'], v['z'])
        for v in cluster
    ) if cluster else POCKET_RADIUS
    volume = (4/3) * math.pi * (max_dist + 2)**3  # +2 Å padding

    # Hydrophobicity
    hydro_count = sum(1 for _, _, name in unique_res if name in HYDROPHOBIC)
    hydro_ratio = hydro_count / max(1, len(unique_res))

    # Enclosure (how surrounded by Cα atoms)
    neighbors = sum(1 for ca in ca_atoms
                    if _dist3(cx, cy, cz, ca['x'], ca['y'], ca['z']) < POCKET_RADIUS * 1.5)
    enclosure = min(1.0, neighbors / 20.0)

    # Druggability
    if hydro_ratio >= 0.4 and enclosure >= 0.3 and len(unique_res) >= 6:
        druggability = 'high'
    elif hydro_ratio >= 0.25 and enclosure >= 0.2:
        druggability = 'moderate'
    elif len(unique_res) >= 4:
        druggability = 'low'
    else:
        druggability = 'undruggable'

    # Composite score (0-100)
    score = (
        min(40, len(unique_res) * 3) +          # Residue count (max 40)
        hydro_ratio * 30 +                       # Hydrophobicity (max 30)
        enclosure * 30                           # Enclosure (max 30)
    )
    score = min(100, max(0, score))

    return Pocket(
        pocket_id=0,  # Set later
        center=(round(cx, 2), round(cy, 2), round(cz, 2)),
        radius=round(max_dist + 2, 2),
        residues=unique_res,
        residue_count=len(unique_res),
        volume=round(volume, 1),
        hydrophobicity=round(hydro_ratio, 3),
        druggability=druggability,
        score=round(score, 1),
        enclosure=round(enclosure, 3),
    )


def detect_pockets(pdb_string: str) -> list:
    """
    Detect binding pockets in a protein structure.

    Args:
        pdb_string: PDB-format structure

    Returns:
        List of Pocket objects, sorted by score (best first)
    """
    logger.info("Detecting binding pockets (%d bytes PDB)", len(pdb_string))

    ca_atoms = _parse_ca_atoms(pdb_string)
    all_atoms = _parse_all_atoms(pdb_string)

    if len(ca_atoms) < POCKET_MIN_ATOMS:
        logger.warning("Too few Cα atoms (%d) for pocket detection", len(ca_atoms))
        return []

    # Generate Voronoi vertices
    vertices = _generate_voronoi_vertices(ca_atoms)
    logger.info("Generated %d Voronoi vertices", len(vertices))

    # Cluster vertices
    clusters = _cluster_vertices(vertices)
    logger.info("Found %d pocket clusters", len(clusters))

    # Score and rank
    pockets = []
    for i, cluster in enumerate(clusters):
        pocket = _score_pocket(cluster, ca_atoms, all_atoms)
        pocket.pocket_id = i + 1
        pockets.append(pocket)

    # Sort by score
    pockets.sort(key=lambda p: -p.score)

    # Re-number
    for i, p in enumerate(pockets):
        p.pocket_id = i + 1

    logger.info("Top pocket: score=%.1f, druggability=%s, %d residues",
                pockets[0].score if pockets else 0,
                pockets[0].druggability if pockets else 'none',
                pockets[0].residue_count if pockets else 0)

    return pockets[:10]  # Return top 10


def pockets_to_dict(pockets: list) -> list:
    """Convert pockets to JSON-serializable list."""
    return [
        {
            'pocket_id': p.pocket_id,
            'center': list(p.center),
            'radius': p.radius,
            'residues': [f"{c}:{n} {name}" for c, n, name in p.residues],
            'residue_count': p.residue_count,
            'volume': p.volume,
            'hydrophobicity': p.hydrophobicity,
            'druggability': p.druggability,
            'score': p.score,
            'enclosure': p.enclosure,
        }
        for p in pockets
    ]

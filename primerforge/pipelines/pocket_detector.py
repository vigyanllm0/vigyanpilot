"""
VigyanLLM — Binding Pocket Detector

Finds binding pockets with a voxel-grid cavity search:

1. Rasterise the protein heavy atoms into a 3D occupancy grid.
2. Mark the voxels a ligand-sized probe physically fits into.
3. Score each such voxel by enclosure — how many sample directions from it
   run into protein within 10 A. Open solvent scores near 0, a cleft scores
   high, an internal void scores near 1.
4. Keep the well-enclosed voxels, join them into connected patches, and merge
   fragments that belong to the same cleft.
5. Rank the patches by enclosure, cavity volume and lining-residue count.

The previous implementation sampled circumcentres of C-alpha triplets. Its
circumcentre formula was wrong, its triplet stride collapsed to adjacent
triplets on small proteins, and it demanded >= 5 vertices per cluster while
producing at most 3 — so it reported zero pockets for 1CRN, 1UBQ and any
other structure without a deep cavity. On ligand-bound structures it placed
its top pocket 11-20 A from the actual site.

numpy is a hard dependency of biopython, so it is always available here.
scipy is deliberately not used: it is not installed on the production box.

Usage:
    from pocket_detector import detect_pockets
    pockets = detect_pockets(pdb_string)
"""

import logging
import math
from collections import defaultdict, deque
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

# ── Constants (Å) ─────────────────────────────────────────────────────────────

R_ATOM = 1.8             # protein van der Waals shell used to build the grid
R_PROBE = 1.7            # ligand-sized probe radius
R_ENC = 10.0             # enclosure sampling radius
ENC_MIN = 0.55           # enclosure below this is treated as bulk solvent
MERGE_R = 6.0            # merge patches whose centroids come this close
LINING_CUT = 4.5         # protein atom within this of the patch lines the pocket
MAX_VOXELS = 2_000_000   # adaptive grid coarsens to stay under this
MIN_ATOMS = 30           # fewer protein atoms than this -> nothing to search
MIN_PATCH_VOXELS = 8     # ignore specks
MAX_POCKETS = 10
CELL = 5.0               # Å — atom bucket size for the lining search

HYDROPHOBIC = {'ALA', 'VAL', 'LEU', 'ILE', 'PHE', 'TRP', 'MET', 'PRO', 'CYS'}


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


# ── Parsing ───────────────────────────────────────────────────────────────────

def _parse_protein(pdb_string: str):
    """Heavy atoms of ATOM records, plus the residue table.

    HETATM is skipped on purpose. A pocket is the empty volume a ligand would
    fill, so the ligand's own atoms must not be counted as protein — otherwise
    a holo structure reports no cavity exactly where its ligand sits.
    """
    xyz, akey, res = [], [], {}
    for line in pdb_string.split('\n'):
        if not line.startswith('ATOM'):
            continue
        try:
            x, y, z = float(line[30:38]), float(line[38:46]), float(line[46:54])
        except ValueError:
            continue
        element = (line[76:78].strip() or line[12:16].strip()[0]).upper()
        if element == 'H':
            continue
        key = (line[21] or 'A', int(line[22:26]))
        xyz.append((x, y, z))
        akey.append(key)
        res.setdefault(key, line[17:20].strip())
    return np.asarray(xyz, dtype=float), akey, res


# ── Grid helpers ──────────────────────────────────────────────────────────────

def _mark(mask, shape, pts, radius, origin, grid):
    """Set voxels whose centre lies within `radius` of any point."""
    reach = int(math.ceil(radius / grid))
    idx = np.floor((pts - origin) / grid).astype(int)
    rr = radius * radius
    for a in range(pts.shape[0]):
        i0, j0, k0 = idx[a]
        i1 = max(0, i0 - reach); i2 = min(shape[0] - 1, i0 + reach)
        j1 = max(0, j0 - reach); j2 = min(shape[1] - 1, j0 + reach)
        k1 = max(0, k0 - reach); k2 = min(shape[2] - 1, k0 + reach)
        if i1 > i2 or j1 > j2 or k1 > k2:
            continue
        I, J, K = np.meshgrid(np.arange(i1, i2 + 1),
                              np.arange(j1, j2 + 1),
                              np.arange(k1, k2 + 1), indexing='ij')
        vc = origin + np.stack([I, J, K], axis=-1) * grid
        mask[I, J, K] |= ((vc - pts[a]) ** 2).sum(-1) <= rr
    return mask


def _dilate_box(mask, radius_vox):
    """Separable box dilation: O(N) per axis, unlike O(N·atoms) re-marking."""
    out = mask
    for axis in range(3):
        pad = [(0, 0)] * 3
        pad[axis] = (radius_vox, radius_vox)
        padded = np.pad(out, pad, constant_values=False)
        window = np.lib.stride_tricks.sliding_window_view(
            padded, 2 * radius_vox + 1, axis=axis)
        out = window.any(axis=-1)
    return out


def _sphere_dirs(n):
    """n quasi-uniform unit vectors (Fibonacci sphere)."""
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    theta = np.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(theta) * np.sin(phi),
                     np.sin(theta) * np.sin(phi),
                     np.cos(phi)], axis=1)


def _components(cand, shape):
    """Label 6-connected patches over the candidate voxels."""
    lab = -np.ones(shape, dtype=np.int32)
    lab[cand[:, 0], cand[:, 1], cand[:, 2]] = 0
    n_labels = 0
    for s in range(cand.shape[0]):
        ci, cj, ck = cand[s]
        if lab[ci, cj, ck] != 0:
            continue
        n_labels += 1
        lab[ci, cj, ck] = n_labels
        queue = deque([(int(ci), int(cj), int(ck))])
        while queue:
            a, b, c = queue.popleft()
            for da, db, dc in ((1, 0, 0), (-1, 0, 0), (0, 1, 0),
                               (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                na, nb, nc = a + da, b + db, c + dc
                if (0 <= na < shape[0] and 0 <= nb < shape[1]
                        and 0 <= nc < shape[2] and lab[na, nb, nc] == 0):
                    lab[na, nb, nc] = n_labels
                    queue.append((na, nb, nc))
    return lab


def _merge_groups(groups, centroids, radius):
    """Union patches whose centroids come within `radius` of one another.

    An enclosure threshold cuts holes through a cleft, which shatters one real
    pocket into several 3-patch slivers. Merging by proximity puts them back.
    """
    parent = {c: c for c in groups}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    keys = list(groups)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = keys[i], keys[j]
            if float(np.linalg.norm(centroids[a] - centroids[b])) <= radius:
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[rb] = ra

    merged = defaultdict(list)
    for c, members in groups.items():
        merged[find(c)].extend(members)
    return merged


def _lining(atoms, voxels_xyz):
    """Residues whose atoms sit within LINING_CUT of the patch, plus depth."""
    lo = voxels_xyz.min(axis=0) - LINING_CUT
    hi = voxels_xyz.max(axis=0) + LINING_CUT
    cell_lo = np.floor(lo / CELL).astype(int)
    cell_hi = np.floor(hi / CELL).astype(int)

    cells = defaultdict(list)
    for i, a in enumerate(atoms):
        cells[(int(a[0] // CELL), int(a[1] // CELL), int(a[2] // CELL))].append(i)

    keep = []
    for cx in range(cell_lo[0], cell_hi[0] + 1):
        for cy in range(cell_lo[1], cell_hi[1] + 1):
            for cz in range(cell_lo[2], cell_hi[2] + 1):
                keep.extend(cells.get((cx, cy, cz), ()))
    if not keep:
        return set(), 0.0

    sub = atoms[np.asarray(keep)]
    d = np.linalg.norm(voxels_xyz[:, None, :] - sub[None, :, :], axis=2)
    # d is (voxel, atom): atoms lining the patch run down axis 1,
    # how deep each voxel sits from any atom runs across axis 0.
    near = d.min(axis=0) <= LINING_CUT
    depth = float(d.min(axis=1).max()) if d.size else 0.0
    return set(np.asarray(keep)[near].tolist()), depth


# ── Detection ─────────────────────────────────────────────────────────────────

def detect_pockets(pdb_string: str, top: int = MAX_POCKETS) -> list:
    """
    Detect binding pockets in a protein structure.

    Args:
        pdb_string: PDB-format structure

    Returns:
        List of Pocket objects, sorted by score (best first)
    """
    logger.info("Detecting binding pockets (%d bytes PDB)", len(pdb_string))

    atoms, akey, residues = _parse_protein(pdb_string)
    if atoms.shape[0] < MIN_ATOMS:
        logger.warning("Too few protein atoms (%d) for pocket detection",
                       atoms.shape[0])
        return []

    lo = atoms.min(axis=0) - 4.0
    hi = atoms.max(axis=0) + 4.0
    # keep the grid affordable on large assemblies
    raw = float(np.prod(np.ceil(hi - lo)))
    grid = 1.0 if raw <= MAX_VOXELS else max(1.0, (raw / MAX_VOXELS) ** (1 / 3))
    shape = tuple(int(v) for v in np.ceil((hi - lo) / grid) + 1)

    protein = _mark(np.zeros(shape, bool), shape, atoms, R_ATOM, lo, grid)
    blocked = _mark(np.zeros(shape, bool), shape, atoms, R_ATOM + R_PROBE, lo, grid)
    near = _dilate_box(protein, int(math.ceil(R_ENC / grid)))

    cand = np.argwhere(~blocked & near & ~protein)
    if cand.shape[0] == 0:
        logger.info("No probe-fitting void found near the protein")
        return []
    logger.info("Grid %dx%dx%d (h=%.2f A), %d candidate probe positions",
                shape[0], shape[1], shape[2], grid, cand.shape[0])

    # ── enclosure: fraction of directions that strike protein within R_ENC ──
    dirs = _sphere_dirs(24)
    flat = protein.reshape(-1)
    steps = np.arange(1.0, R_ENC + 0.25, max(grid, 1.25))
    enc = np.zeros(cand.shape[0])
    for d in dirs:
        hit = np.zeros(cand.shape[0], dtype=bool)
        for s in steps:
            off = d * s
            ii = cand[:, 0] + int(round(off[0] / grid))
            jj = cand[:, 1] + int(round(off[1] / grid))
            kk = cand[:, 2] + int(round(off[2] / grid))
            ok = ((ii >= 0) & (ii < shape[0]) & (jj >= 0) & (jj < shape[1])
                  & (kk >= 0) & (kk < shape[2]))
            got = np.zeros(cand.shape[0], dtype=bool)
            got[ok] = flat[(ii[ok] * shape[1] + jj[ok]) * shape[2] + kk[ok]]
            hit |= got
        enc += hit
    enc /= len(dirs)

    keep = enc >= ENC_MIN
    cand, enc = cand[keep], enc[keep]
    if cand.shape[0] == 0:
        logger.info("All candidate positions are open to solvent")
        return []

    lab = _components(cand, shape)
    clabel = lab[cand[:, 0], cand[:, 1], cand[:, 2]]

    groups = defaultdict(list)
    for i in range(cand.shape[0]):
        groups[int(clabel[i])].append(i)
    centroids = {c: lo + cand[m].mean(axis=0) * grid for c, m in groups.items()}
    merged = _merge_groups(groups, centroids, MERGE_R)
    logger.info("Found %d pocket patch(es)", len(merged))

    pockets = []
    for members in merged.values():
        if len(members) < MIN_PATCH_VOXELS:
            continue
        vox = cand[np.asarray(members)]
        pts = lo + vox * grid
        centre = pts.mean(axis=0)
        # Report an actual pocket voxel nearest the centroid: the centroid of a
        # crescent-shaped patch can fall inside the protein, and the deepest
        # voxel can sit out on an arm of the crescent.
        reported = pts[int(np.linalg.norm(pts - centre, axis=1).argmin())]
        volume = float(pts.shape[0]) * (grid ** 3)

        atoms_near, depth = _lining(atoms, pts)
        lin_res = sorted({(akey[a], residues[akey[a]]) for a in atoms_near},
                         key=lambda t: t[0])
        n_res = len(lin_res)
        hydro = sum(1 for _, rn in lin_res if rn in HYDROPHOBIC)
        hfrac = hydro / max(1, n_res)
        mean_enc = float(enc[np.asarray(members)].mean())
        radius = float(np.linalg.norm(pts - centre, axis=1).max()) + grid

        pockets.append(Pocket(
            pocket_id=0,
            center=(round(float(reported[0]), 2), round(float(reported[1]), 2),
                    round(float(reported[2]), 2)),
            radius=round(radius, 2),
            residues=[(c, n, name) for (c, n), name in lin_res],
            residue_count=n_res,
            volume=round(volume, 1),
            hydrophobicity=round(hfrac, 3),
            druggability='low',
            score=0.0,
            enclosure=round(mean_enc, 3),
        ))
        pockets[-1].__dict__['_centre_xyz'] = centre
        pockets[-1].__dict__['_depth'] = depth

    if not pockets:
        return []

    # ── Rank ────────────────────────────────────────────────────────────────
    # Enclosure, a ligand-sized cavity, and how many residues line it.
    # Volume is scored against 250 Å³ (a typical small-molecule site) and
    # falls off for both hairline grooves and bulk solvent-filled cavities.
    for p in pockets:
        vol = max(p.volume, 1.0)
        vol_term = math.exp(-((math.log(vol) - math.log(250.0)) ** 2) / 2.2)
        p.score = round(min(100.0, 100.0 * (
            0.45 * p.enclosure +
            0.35 * vol_term +
            0.20 * min(1.0, p.residue_count / 30.0)
        )), 1)
        p.druggability = (
            'high' if p.score >= 70 else
            'moderate' if p.score >= 55 else
            'low' if p.score >= 40 else
            'undruggable'
        )

    pockets.sort(key=lambda p: -p.score)
    for i, p in enumerate(pockets[:top]):
        p.pocket_id = i + 1

    logger.info("Top pocket: score=%.1f, druggability=%s, %d residues",
                pockets[0].score, pockets[0].druggability, pockets[0].residue_count)

    return pockets[:top]


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

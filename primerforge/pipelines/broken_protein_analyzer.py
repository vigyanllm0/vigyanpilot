"""
VigyanLLM — Broken Protein Analysis Engine

Analyzes protein structures for defects before docking:
1. pLDDT confidence analysis (per-residue quality)
2. Missing residue detection (structural gaps)
3. Steric clash detection (atomic overlaps)
4. Ramachandran outlier detection (backbone geometry)
5. Unsatisfied H-bond analysis (buried polar groups)
6. Overall quality score (composite metric)

Usage:
    from broken_protein_analyzer import analyze_protein
    report = analyze_protein(pdb_string, plddt_scores=None)
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ── Amino acid properties ────────────────────────────────────────────────────

# Van der Waals radii (Angstrom) for clash detection
VDW_RADII = {
    'C': 1.7, 'N': 1.55, 'O': 1.52, 'S': 1.8, 'H': 1.2,
    'P': 1.8, 'F': 1.47, 'Cl': 1.75, 'Br': 1.85,
}

# Backbone atoms of the peptide link — a consecutive-residue pair where at
# least one atom is in this set is covalent 1-2/1-3/1-4 geometry (every path
# across the peptide bond runs through C(i) or N(i+1)), never a steric clash.
# HETATM names (OXT/OT1/OT2, common H names) included for uploaded PDBs.
_BACKBONE_ATOMS = {'N', 'CA', 'C', 'O', 'OXT', 'OT1', 'OT2',
                   'H', 'HA', 'HA2', 'HA3', '1H', '2H', '3H', 'HN'}

# Residue types
POLAR_RESIDUES = {'SER', 'THR', 'ASN', 'GLN', 'TYR', 'CYS', 'HIS'}
CHARGED_POS = {'LYS', 'ARG', 'HIS'}
CHARGED_NEG = {'ASP', 'GLU'}
HYDROPHOBIC_RESIDUES = {'ALA', 'VAL', 'LEU', 'ILE', 'PHE', 'TRP', 'MET', 'PRO'}
SMALL_RESIDUES = {'GLY', 'ALA', 'SER'}

# Ramachandran favored regions (phi, psi) — simplified
RAMACHANDRAN_FAVORED = [
    (-135, 135, 45),   # Beta sheet
    (-65, -40, 30),    # Alpha helix
    (-65, 120, 25),    # Left-handed helix
]

# Bond lengths for bond detection
BOND_LENGTHS = {
    ('N', 'CA'): 1.47, ('CA', 'C'): 1.52, ('C', 'N'): 1.33,
    ('C', 'O'): 1.24, ('CA', 'CB'): 1.54,
}


@dataclass
class Defect:
    """A single structural defect."""
    type: str           # 'clash', 'gap', 'ramachandran', 'hbond', 'plddt'
    severity: str       # 'critical', 'warning', 'info'
    residue: str        # e.g. 'A:42 ASN'
    description: str
    details: dict = field(default_factory=dict)


@dataclass
class AnalysisReport:
    """Complete broken protein analysis report."""
    quality_score: float          # 0-100 composite score
    quality_grade: str            # A/B/C/D/F
    plddt_analysis: dict
    missing_residues: list
    clashes: list
    ramachandran_outliers: list
    hbond_analysis: dict
    defects: list                 # All defects sorted by severity
    summary: str
    recommendation: str


def _parse_pdb(pdb_string: str) -> tuple[dict, list]:
    """Parse PDB string into atoms and residues.

    Multi-model files (NMR ensembles): only the FIRST model is read —
    otherwise atoms from later models would be merged into the same
    residues and every inter-model contact would report as a spurious
    steric clash.
    """
    atoms = []
    residues = {}
    current_res = None

    for line in pdb_string.split('\n'):
        if line.startswith('ENDMDL'):
            break  # first model only
        if not line.startswith(('ATOM', 'HETATM')):
            continue

        try:
            atom = {
                'serial': int(line[6:11].strip()),
                'name': line[12:16].strip(),
                'res_name': line[17:20].strip(),
                'chain': line[21] if line[21].strip() else 'A',
                'res_num': int(line[22:26].strip()),
                'x': float(line[30:38]),
                'y': float(line[38:46]),
                'z': float(line[46:54]),
                'element': line[76:78].strip() if len(line) > 76 else line[12:16].strip()[0],
                'alt': line[16],  # Alternate location indicator
            }
            # B-factor / temperature factor (PDB cols 61-66). Predicted
            # models (AlphaFold/ESMFold) write pLDDT here; experimental
            # structures write a displacement factor. 0.0 = "no data".
            # Parsed in its own try so a malformed column never drops the atom.
            try:
                atom['b_factor'] = float(line[60:66])
            except (ValueError, IndexError):
                atom['b_factor'] = 0.0
        except (ValueError, IndexError):
            continue

        # Skip alternate conformations (keep only first)
        if atom['alt'] not in (' ', 'A'):
            continue

        atoms.append(atom)
        res_key = (atom['chain'], atom['res_num'])
        if res_key not in residues:
            residues[res_key] = {
                'chain': atom['chain'],
                'num': atom['res_num'],
                'name': atom['res_name'],
                'atoms': [],
            }
        residues[res_key]['atoms'].append(atom)

    return residues, atoms


def _calc_distance(a1: dict, a2: dict) -> float:
    """Calculate Euclidean distance between two atoms."""
    return math.sqrt(
        (a1['x'] - a2['x'])**2 +
        (a1['y'] - a2['y'])**2 +
        (a1['z'] - a2['z'])**2
    )


def extract_per_residue_plddt(pdb_string: str) -> Optional[list]:
    """Per-residue mean B-factor read as pLDDT (predicted-model convention:
    AlphaFold/ESMFold write confidence into the B-factor column).

    Scale-aware: the ESMFold web API writes 0-1 fractions, local models
    write 0-100 — detect the scale and always return 0-100 percentages.

    Returns None when the file carries no B-factor data (column absent or
    all zeros) so callers never present fabricated confidence numbers.
    """
    residues, _ = _parse_pdb(pdb_string)
    sorted_res = sorted(residues.values(), key=lambda r: (r['chain'], r['num']))
    if not sorted_res:
        return None
    scores = []
    for res in sorted_res:
        b_vals = [a['b_factor'] for a in res['atoms'] if 'b_factor' in a]
        scores.append(sum(b_vals) / len(b_vals) if b_vals else 0.0)
    if max(scores) <= 0.001:
        return None                      # column present but all zeros = no data
    if max(scores) <= 1.5:               # 0-1 fraction scale → percent
        scores = [s * 100.0 for s in scores]
    return [round(s, 1) for s in scores]


def count_ca_residues(pdb_string: str) -> int:
    """Number of distinct residues carrying a backbone CA atom.

    Pre-validation gate for uploaded structures: a file without enough of
    these is not a protein and must be rejected before a run is booked.
    """
    seen = set()
    for line in pdb_string.splitlines():
        if line.startswith(('ATOM', 'HETATM')) and line[12:16].strip() == 'CA':
            seen.add((line[21:22] or 'A', line[22:26]))
    return len(seen)


def _confidence_tier(score: float) -> str:
    """pLDDT confidence tier for one residue (or a segment mean)."""
    if score >= 90:
        return 'high'
    if score >= 70:
        return 'medium'
    if score >= 50:
        return 'low'
    return 'very_low'


def analyze_plddt(pdb_string: str, plddt_scores: Optional[list] = None) -> dict:
    """
    Analyze pLDDT confidence scores per residue.

    If plddt_scores not provided, estimates from B-factor (conformational diversity).
    ESMFold pLDDT ranges: 0-100 (higher = more confident).
    """
    residues, _ = _parse_pdb(pdb_string)
    sorted_res = sorted(residues.values(), key=lambda r: (r['chain'], r['num']))

    if plddt_scores and len(plddt_scores) >= len(sorted_res):
        scores = plddt_scores[:len(sorted_res)]
    else:
        # Estimate from B-factors if the column carries data. The guard
        # (any b > 0) matters: an all-zero B column means "no data" —
        # without it every residue would estimate as a perfect 100.
        scores = []
        for res in sorted_res:
            b_factors = [a.get('b_factor', 0) for a in res['atoms'] if 'b_factor' in a]
            if b_factors and any(b > 0 for b in b_factors):
                avg_b = sum(b_factors) / len(b_factors)
                # Rough conversion: pLDDT ≈ 100 - (B-factor / 2)
                est_plddt = max(0, min(100, 100 - avg_b / 2))
                scores.append(est_plddt)
            else:
                scores.append(70)  # Default medium confidence (no data)

    # Classify residues by confidence
    high_conf = sum(1 for s in scores if s >= 90)
    medium_conf = sum(1 for s in scores if 70 <= s < 90)
    low_conf = sum(1 for s in scores if 50 <= s < 70)
    very_low = sum(1 for s in scores if s < 50)
    total = len(scores) if scores else 1

    mean_plddt = sum(scores) / total if scores else 0

    # Find low-confidence regions (contiguous stretches)
    low_regions = []
    current_region = None
    for i, (res, score) in enumerate(zip(sorted_res, scores)):
        if score < 70:
            if current_region is None:
                current_region = {'start': res['num'], 'end': res['num'], 'chain': res['chain'], 'scores': []}
            current_region['end'] = res['num']
            current_region['scores'].append(score)
        else:
            if current_region and len(current_region['scores']) >= 3:
                current_region['mean_plddt'] = sum(current_region['scores']) / len(current_region['scores'])
                low_regions.append(current_region)
            current_region = None
    if current_region and len(current_region.get('scores', [])) >= 3:
        current_region['mean_plddt'] = sum(current_region['scores']) / len(current_region['scores'])
        low_regions.append(current_region)

    # Full confidence-tier segmentation (which part of the protein is
    # trustworthy): contiguous same-tier runs. Runs shorter than 3 residues
    # merge into the previous run so a single noisy residue doesn't
    # fragment the table; the merged run is re-tiered from its new mean.
    segments = []
    for res, score in zip(sorted_res, scores):
        tier = _confidence_tier(score)
        if segments and segments[-1]['chain'] == res['chain'] and segments[-1]['tier'] == tier:
            segments[-1]['end'] = res['num']
            segments[-1]['scores'].append(score)
        else:
            segments.append({'chain': res['chain'], 'start': res['num'],
                             'end': res['num'], 'tier': tier, 'scores': [score]})
    merged = []
    for seg in segments:
        if merged and len(seg['scores']) < 3 and merged[-1]['chain'] == seg['chain']:
            merged[-1]['end'] = seg['end']
            merged[-1]['scores'].extend(seg['scores'])
        else:
            merged.append(seg)
    regions = []
    for seg in merged:
        mean = sum(seg['scores']) / len(seg['scores'])
        regions.append({
            'chain': seg['chain'],
            'start': seg['start'],
            'end': seg['end'],
            'count': len(seg['scores']),
            'tier': _confidence_tier(mean),
            'mean': round(mean, 1),
        })

    return {
        'mean_plddt': round(mean_plddt, 1),
        'high_confidence': high_conf,
        'medium_confidence': medium_conf,
        'low_confidence': low_conf,
        'very_low_confidence': very_low,
        'total_residues': total,
        'scores': scores,
        'regions': regions,
        'low_confidence_regions': low_regions,
        'defects': [
            Defect(
                type='plddt',
                severity='critical' if r['mean_plddt'] < 50 else 'warning',
                residue=f"{r['chain']}:{r['start']}-{r['end']}",
                description=f"Low-confidence region ({r['mean_plddt']:.0f}% mean pLDDT, {r['end']-r['start']+1} residues)",
                details={'region': r}
            )
            for r in low_regions
        ]
    }


def detect_missing_residues(pdb_string: str) -> list:
    """Detect gaps (missing residues) in the structure."""
    residues, _ = _parse_pdb(pdb_string)
    gaps = []

    # Group by chain
    chains = {}
    for res in residues.values():
        chain = res['chain']
        if chain not in chains:
            chains[chain] = []
        chains[chain].append(res['num'])

    for chain, nums in chains.items():
        nums = sorted(set(nums))
        if len(nums) < 2:
            continue
        for i in range(len(nums) - 1):
            gap_size = nums[i + 1] - nums[i] - 1
            if gap_size > 0:
                gaps.append({
                    'chain': chain,
                    'start': nums[i],
                    'end': nums[i + 1],
                    'missing_count': gap_size,
                    'description': f"Missing {gap_size} residue(s) between {chain}:{nums[i]} and {chain}:{nums[i+1]}",
                })

    return gaps


def detect_clashes(atoms: list, threshold: float = 0.5) -> list:
    """
    Detect steric clashes (atoms closer than threshold).
    Uses a simplified grid-based approach for efficiency.
    """
    clashes = []

    # Build spatial grid for efficiency
    grid = {}
    cell_size = 3.0  # Angstrom

    for atom in atoms:
        if atom['element'] not in VDW_RADII:
            continue
        key = (
            int(atom['x'] / cell_size),
            int(atom['y'] / cell_size),
            int(atom['z'] / cell_size)
        )
        if key not in grid:
            grid[key] = []
        grid[key].append(atom)

    # Check neighboring cells
    checked = set()
    for atom in atoms:
        if atom['element'] not in VDW_RADII:
            continue
        key = (
            int(atom['x'] / cell_size),
            int(atom['y'] / cell_size),
            int(atom['z'] / cell_size)
        )
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                for dz in range(-1, 2):
                    nkey = (key[0] + dx, key[1] + dy, key[2] + dz)
                    if nkey not in grid:
                        continue
                    for other in grid[nkey]:
                        if atom['serial'] >= other['serial']:
                            continue
                        pair_key = (atom['serial'], other['serial'])
                        if pair_key in checked:
                            continue
                        checked.add(pair_key)

                        dist = _calc_distance(atom, other)
                        # Skip COVALENT geometry, not just same-residue pairs:
                        #  1) same residue (all intra-residue bonded pairs)
                        #  2) consecutive residues where at least one atom is
                        #     backbone (N/CA/C/O) — every 1-2/1-3/1-4 pair
                        #     across the peptide link runs through C(i) or
                        #     N(i+1), so one partner is always backbone:
                        #     peptide C-N 1.20-1.39 A, O(i)...N(i+1) 2.27 A,
                        #     CA(i)...N(i+1) 2.42 A, C(i)...CA(i+1) 2.4-2.75 A,
                        #     PRO CD 1-3 neighbours ~2.4-2.8 A.  Sidechain-
                        #     sidechain contacts between consecutive residues
                        #     (rotamer clashes) stay detectable.
                        # Without (2) EVERY peptide bond trips the overlap
                        # test (C-N vdW sum 3.25 - 1.33 = 1.92 A overlap) and
                        # the top-50 cap turned a 159-aa model into a bogus
                        # "50 critical clashes", wrecking the quality grade.
                        # Real non-bonded anomalies (e.g. a 1.01 A side-chain
                        # overlap from a bad prediction) stay flagged: those
                        # pairs are > 1 residue apart.
                        if atom['chain'] == other['chain']:
                            if atom['res_num'] == other['res_num']:
                                continue
                            if (abs(atom['res_num'] - other['res_num']) == 1
                                    and (atom['name'] in _BACKBONE_ATOMS
                                         or other['name'] in _BACKBONE_ATOMS)):
                                continue
                        if (atom['name'] == 'SG' and other['name'] == 'SG'
                                and atom['element'] == 'S'
                                and other['element'] == 'S'):
                            continue

                        r1 = VDW_RADII.get(atom['element'], 1.5)
                        r2 = VDW_RADII.get(other['element'], 1.5)
                        overlap = (r1 + r2) - dist

                        if overlap > threshold:
                            clashes.append({
                                'atom1': f"{atom['chain']}:{atom['res_num']} {atom['res_name']} {atom['name']}",
                                'atom2': f"{other['chain']}:{other['res_num']} {other['res_name']} {other['name']}",
                                'distance': round(dist, 3),
                                'overlap': round(overlap, 3),
                                'severity': 'critical' if overlap > 1.0 else 'warning',
                            })

    # Sort by overlap severity
    clashes.sort(key=lambda c: -c['overlap'])
    return clashes[:50]  # Limit to top 50


def check_ramachandran(pdb_string: str) -> list:
    """
    Check backbone phi/psi angles against Ramachandran favored regions.
    Simplified: checks CA-C-N-CA dihedral geometry.
    """
    residues, _ = _parse_pdb(pdb_string)
    outliers = []

    sorted_res = sorted(residues.values(), key=lambda r: (r['chain'], r['num']))

    # Build atom lookup by residue
    def get_atom(res, name):
        for a in res['atoms']:
            if a['name'] == name:
                return a
        return None

    for i in range(1, len(sorted_res) - 1):
        prev = sorted_res[i - 1]
        curr = sorted_res[i]
        nxt = sorted_res[i + 1]

        if prev['chain'] != curr['chain'] or curr['chain'] != nxt['chain']:
            continue

        n = get_atom(curr, 'N')
        ca = get_atom(curr, 'CA')
        c = get_atom(curr, 'C')

        if not (n and ca and c):
            continue

        # Check N-CA bond length (should be ~1.47 A)
        n_ca_dist = _calc_distance(n, ca)
        if abs(n_ca_dist - 1.47) > 0.3:
            outliers.append({
                'residue': f"{curr['chain']}:{curr['num']} {curr['name']}",
                'type': 'bond_length',
                'value': round(n_ca_dist, 3),
                'expected': 1.47,
                'description': f"N-CA bond length {n_ca_dist:.3f} A (expected ~1.47 A)",
            })

        # Check CA-C bond length (should be ~1.52 A)
        ca_c_dist = _calc_distance(ca, c)
        if abs(ca_c_dist - 1.52) > 0.3:
            outliers.append({
                'residue': f"{curr['chain']}:{curr['num']} {curr['name']}",
                'type': 'bond_length',
                'value': round(ca_c_dist, 3),
                'expected': 1.52,
                'description': f"CA-C bond length {ca_c_dist:.3f} A (expected ~1.52 A)",
            })

        # Check N-CA-C angle (should be ~111 degrees)
        if n and ca and c:
            v1 = (n['x'] - ca['x'], n['y'] - ca['y'], n['z'] - ca['z'])
            v2 = (c['x'] - ca['x'], c['y'] - ca['y'], c['z'] - ca['z'])
            dot = sum(a*b for a, b in zip(v1, v2))
            m1 = math.sqrt(sum(a*a for a in v1))
            m2 = math.sqrt(sum(a*a for a in v2))
            if m1 > 0 and m2 > 0:
                angle = math.degrees(math.acos(max(-1, min(1, dot / (m1 * m2)))))
                if abs(angle - 111) > 25:
                    outliers.append({
                        'residue': f"{curr['chain']}:{curr['num']} {curr['name']}",
                        'type': 'angle',
                        'value': round(angle, 1),
                        'expected': 111,
                        'description': f"N-CA-C angle {angle:.1f} deg (expected ~111 deg)",
                    })

    return outliers


def analyze_hbonds(pdb_string: str) -> dict:
    """
    Analyze hydrogen bond satisfaction.
    Finds buried polar atoms without H-bond partners.
    """
    residues, atoms = _parse_pdb(pdb_string)
    hbond_donors = []
    hbond_acceptors = []
    buried_polar = []

    # Identify donors and acceptors
    for atom in atoms:
        res_name = atom['res_name']
        atom_name = atom['name']

        # Donors: NH, OH, SH groups
        if atom_name in ('N', 'NE', 'NH1', 'NH2', 'ND1', 'NE2', 'NZ', 'OG', 'OG1', 'OH', 'SG', 'NE2'):
            hbond_donors.append(atom)

        # Acceptors: O, N with lone pairs
        if atom_name in ('O', 'OD1', 'OD2', 'OE1', 'OE2', 'OG', 'OG1', 'OH', 'SD', 'ND1', 'NE2'):
            hbond_acceptors.append(atom)

    # Find unsatisfied donors/acceptors (no partner within 3.5 A)
    unsatisfied_donors = []
    unsatisfied_acceptors = []

    for donor in hbond_donors:
        has_partner = False
        for acceptor in hbond_acceptors:
            if donor['serial'] == acceptor['serial']:
                continue
            if donor['chain'] == acceptor['chain'] and abs(donor['res_num'] - acceptor['res_num']) <= 1:
                continue  # Skip intra-residue/neighbor
            dist = _calc_distance(donor, acceptor)
            if dist < 3.5:
                has_partner = True
                break
        if not has_partner:
            unsatisfied_donors.append(donor)

    for acceptor in hbond_acceptors:
        has_partner = False
        for donor in hbond_donors:
            if donor['serial'] == acceptor['serial']:
                continue
            if donor['chain'] == acceptor['chain'] and abs(donor['res_num'] - acceptor['res_num']) <= 1:
                continue
            dist = _calc_distance(donor, acceptor)
            if dist < 3.5:
                has_partner = True
                break
        if not has_partner:
            unsatisfied_acceptors.append(acceptor)

    return {
        'total_donors': len(hbond_donors),
        'total_acceptors': len(hbond_acceptors),
        'unsatisfied_donors': len(unsatisfied_donors),
        'unsatisfied_acceptors': len(unsatisfied_acceptors),
        'satisfaction_rate': round(
            100 * (1 - (len(unsatisfied_donors) + len(unsatisfied_acceptors)) /
                   max(1, len(hbond_donors) + len(hbond_acceptors))), 1
        ),
        'defects': [
            Defect(
                type='hbond',
                severity='warning',
                residue=f"{d['chain']}:{d['res_num']} {d['res_name']} {d['name']}",
                description=f"Unsatisfied H-bond donor {d['name']} in {d['res_name']}",
            )
            for d in unsatisfied_donors[:20]  # Limit
        ] + [
            Defect(
                type='hbond',
                severity='info',
                residue=f"{a['chain']}:{a['res_num']} {a['res_name']} {a['name']}",
                description=f"Unsatisfied H-bond acceptor {a['name']} in {a['res_name']}",
            )
            for a in unsatisfied_acceptors[:20]
        ]
    }


def compute_quality_score(
    plddt_analysis: dict,
    missing_residues: list,
    clashes: list,
    ramachandran_outliers: list,
    hbond_analysis: dict,
    n_atoms: Optional[int] = None,
) -> tuple[float, str]:
    """
    Compute composite quality score (0-100) and grade (A-F).

    Weights:
    - pLDDT confidence: 40%
    - Clash severity: 20%
    - Ramachandran: 20%
    - H-bond satisfaction: 10%
    - Missing residues: 10%
    """
    # pLDDT score (0-100)
    plddt_score = plddt_analysis.get('mean_plddt', 70)

    # Clash penalty (0-100): MolProbity-style severity-weighted clashscore —
    # critical clashes (overlap > 1.0 A) weigh 3x warnings, normalised per
    # 1000 atoms so small models aren't judged by raw counts. Rate 0-5/1000
    # = high-resolution quality (small penalty), linear to a full penalty at
    # 50/1000 (grossly broken model).
    # The old formula (5*count + 20*sum_top10_overlaps) saturated to the
    # full 20-point loss at ~6 moderate contacts — a cliff, not a curve:
    # a 159-aa model with 11 mild short contacts scored clash 0/100.
    if n_atoms is None:
        n_atoms = plddt_analysis.get('total_residues', 1) * 8  # ~8 heavy atoms/residue
    n_atoms = max(1, int(n_atoms) or 1)
    weighted = sum(3 if c.get('overlap', 0) > 1.0 else 1 for c in clashes)
    clash_rate = weighted / n_atoms * 1000.0  # weighted clashes per 1000 atoms
    clash_penalty = min(100.0, max(0.0, clash_rate / 50.0 * 100.0))

    # Ramachandran score
    total_res = plddt_analysis.get('total_residues', 1)
    ram_score = max(0, 100 - (len(ramachandran_outliers) / max(1, total_res) * 500))

    # H-bond satisfaction
    hbond_score = hbond_analysis.get('satisfaction_rate', 70)

    # Missing residue penalty
    missing_penalty = min(100, sum(g['missing_count'] for g in missing_residues) * 10)

    # Weighted composite
    quality = (
        plddt_score * 0.40 +
        (100 - clash_penalty) * 0.20 +
        ram_score * 0.20 +
        hbond_score * 0.10 +
        (100 - missing_penalty) * 0.10
    )
    quality = max(0, min(100, quality))

    # Grade
    if quality >= 90: grade = 'A'
    elif quality >= 75: grade = 'B'
    elif quality >= 60: grade = 'C'
    elif quality >= 40: grade = 'D'
    else: grade = 'F'

    return round(quality, 1), grade


def _docking_recommendation(quality: float, critical: int) -> str:
    """Human verdict for stage 1 — severity-aware at the top grade.

    Saying "Minor issues" beside a "N critical" defect count (severe steric
    overlaps, <50-pLDDT regions) reads dishonest to a careful scientist, so
    the suitable-but-critical case names the defects and points at repair.
    """
    if quality >= 75:
        if critical > 0:
            return (
                f"Structure is suitable for docking overall ({quality:g}/100), but "
                f"{critical} severe defect{'s' if critical != 1 else ''} flagged — "
                "review the defect list below (the Repair structure step fixes "
                "steric clashes) before relying on exact ranks."
            )
        return "Structure appears suitable for docking. Minor issues noted but unlikely to significantly impact results."
    if quality >= 50:
        return "Structure has moderate quality issues. Consider using an experimental PDB structure if available, or proceed with caution on the flagged regions."
    return "Structure has significant quality issues. Docking results on this structure should be treated with extreme caution. Consider using an experimental structure, a different prediction method, or selecting a shorter region around your binding site."


def analyze_protein(pdb_string: str, plddt_scores: Optional[list] = None) -> AnalysisReport:
    """
    Run complete broken protein analysis.

    Args:
        pdb_string: PDB-format structure
        plddt_scores: Optional per-residue pLDDT scores from ESMFold

    Returns:
        AnalysisReport with all findings
    """
    logger.info("Starting broken protein analysis (%d bytes PDB)", len(pdb_string))

    residues, atoms = _parse_pdb(pdb_string)

    # 1. pLDDT analysis
    plddt = analyze_plddt(pdb_string, plddt_scores)

    # 2. Missing residues
    missing = detect_missing_residues(pdb_string)

    # 3. Steric clashes
    clashes = detect_clashes(atoms)

    # 4. Ramachandran outliers
    ram_outliers = check_ramachandran(pdb_string)

    # 5. H-bond analysis
    hbond = analyze_hbonds(pdb_string)

    # 6. Quality score
    quality, grade = compute_quality_score(plddt, missing, clashes, ram_outliers, hbond,
                                           n_atoms=len(atoms))

    # 7. Aggregate defects
    all_defects = []
    all_defects.extend(plddt.get('defects', []))
    all_defects.extend(hbond.get('defects', []))
    for c in clashes:
        all_defects.append(Defect(
            type='clash',
            severity=c['severity'],
            residue=f"{c['atom1']} ↔ {c['atom2']}",
            description=f"Steric clash: {c['overlap']:.2f} A overlap ({c['distance']:.2f} A apart)",
            details=c,
        ))
    for r in ram_outliers:
        all_defects.append(Defect(
            type='ramachandran',
            severity='warning',
            residue=r['residue'],
            description=r['description'],
            details=r,
        ))

    # Sort by severity
    severity_order = {'critical': 0, 'warning': 1, 'info': 2}
    all_defects.sort(key=lambda d: severity_order.get(d.severity, 3))

    # Summary
    critical = sum(1 for d in all_defects if d.severity == 'critical')
    warnings = sum(1 for d in all_defects if d.severity == 'warning')
    total_res = plddt.get('total_residues', 0)

    recommendation = _docking_recommendation(quality, critical)

    summary = (
        f"Quality: {grade} ({quality}/100). "
        f"{total_res} residues analyzed. "
        f"{critical} critical, {warnings} warnings. "
        f"pLDDT: {plddt['mean_plddt']}% mean. "
        f"{len(missing)} gap(s), {len(clashes)} clash(es), "
        f"{len(ram_outliers)} Ramachandran outlier(s)."
    )

    logger.info("Analysis complete: %s", summary)

    return AnalysisReport(
        quality_score=quality,
        quality_grade=grade,
        plddt_analysis=plddt,
        missing_residues=missing,
        clashes=clashes,
        ramachandran_outliers=ram_outliers,
        hbond_analysis=hbond,
        defects=all_defects,
        summary=summary,
        recommendation=recommendation,
    )


def report_to_dict(report: AnalysisReport) -> dict:
    """Convert AnalysisReport to JSON-serializable dict."""
    return {
        'quality_score': report.quality_score,
        'quality_grade': report.quality_grade,
        'summary': report.summary,
        'recommendation': report.recommendation,
        'plddt': {
            'mean': report.plddt_analysis.get('mean_plddt', 0),
            'high_confidence': report.plddt_analysis.get('high_confidence', 0),
            'medium_confidence': report.plddt_analysis.get('medium_confidence', 0),
            'low_confidence': report.plddt_analysis.get('low_confidence', 0),
            'very_low_confidence': report.plddt_analysis.get('very_low_confidence', 0),
            'total_residues': report.plddt_analysis.get('total_residues', 0),
            'regions': report.plddt_analysis.get('regions', []),
        },
        'missing_residues': report.missing_residues,
        'clashes': [
            {k: v for k, v in c.items()} for c in report.clashes
        ],
        'ramachandran_outliers': report.ramachandran_outliers,
        'hbond_analysis': {
            'total_donors': report.hbond_analysis.get('total_donors', 0),
            'total_acceptors': report.hbond_analysis.get('total_acceptors', 0),
            'unsatisfied_donors': report.hbond_analysis.get('unsatisfied_donors', 0),
            'unsatisfied_acceptors': report.hbond_analysis.get('unsatisfied_acceptors', 0),
            'satisfaction_rate': report.hbond_analysis.get('satisfaction_rate', 0),
        },
        'defects': [
            {
                'type': d.type,
                'severity': d.severity,
                'residue': d.residue,
                'description': d.description,
            }
            for d in report.defects
        ],
        'defect_count': {
            'critical': sum(1 for d in report.defects if d.severity == 'critical'),
            'warning': sum(1 for d in report.defects if d.severity == 'warning'),
            'info': sum(1 for d in report.defects if d.severity == 'info'),
        },
    }

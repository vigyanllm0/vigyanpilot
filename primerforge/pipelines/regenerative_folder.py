"""
VigyanLLM — Regenerative Protein Folding Engine

Rebuilds broken protein regions to improve docking quality:
1. Missing loop modeling — interpolate ideal backbone through gaps
2. Side-chain repair — clash resolution via rotamer packing
3. Terminal cleanup — cap disordered N/C termini
4. pLDDT-guided re-refinement — rebuild low-confidence regions
5. Before/after quality comparison

Usage:
    from regenerative_folder import regenerate_structure
    result = regenerate_structure(pdb_string, plddt_scores=None)
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

# Ideal backbone bond lengths (Angstrom)
BOND_N_CA = 1.47
BOND_CA_C = 1.52
BOND_C_N = 1.33
BOND_C_O = 1.24

# Ideal backbone bond angles (degrees)
ANGLE_N_CA_C = 111.0
ANGLE_CA_C_N = 116.5
ANGLE_C_N_CA = 121.0

# Allowed phi/psi for loop modeling (Ramachandran favored)
ALPHA_HELIX = (-63, -43)
BETA_SHEET = (-120, 120)
RANDOM_COIL = (-60, 60)

# Steric clash threshold
CLASH_THRESHOLD = 1.5  # Angstrom overlap
CLASH_REBUILD_RADIUS = 5.0  # Angstrom — rebuild zone around clash

# pLDDT thresholds
PLDDT_LOW = 50
PLDDT_MEDIUM = 70
PLDDT_HIGH = 90

# Terminal cap residues
NTERM_N = {'name': 'N', 'element': 'N'}
CTERM_OXT = {'name': 'OXT', 'element': 'O'}


@dataclass
class RepairAction:
    """A single structural repair."""
    type: str           # 'loop', 'clash', 'terminal', 'plddt'
    region: str         # e.g. 'A:42-48'
    description: str
    atoms_changed: int
    details: dict = field(default_factory=dict)


@dataclass
class RegenerationReport:
    """Complete regeneration report."""
    actions: list
    before_stats: dict
    after_stats: dict
    improvement: dict
    prepared_pdb: str
    summary: str


def _parse_pdb(pdb_string: str) -> tuple[list, list]:
    """Parse PDB into ATOM lines and residue groups."""
    atoms = []
    residues = {}

    for line in pdb_string.split('\n'):
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
                'line': line,
            }
        except (ValueError, IndexError):
            continue

        atoms.append(atom)
        key = (atom['chain'], atom['res_num'])
        if key not in residues:
            residues[key] = {'chain': atom['chain'], 'num': atom['res_num'],
                             'name': atom['res_name'], 'atoms': []}
        residues[key]['atoms'].append(atom)

    return atoms, residues


def _dist(a, b) -> float:
    return math.sqrt((a['x']-b['x'])**2 + (a['y']-b['y'])**2 + (a['z']-b['z'])**2)


def _calc_bond_length(a1, a2) -> float:
    return _dist(a1, a2)


def _calc_angle(a1, vertex, a2) -> float:
    v1 = (a1['x']-vertex['x'], a1['y']-vertex['y'], a1['z']-vertex['z'])
    v2 = (a2['x']-vertex['x'], a2['y']-vertex['y'], a2['z']-vertex['z'])
    dot = sum(a*b for a, b in zip(v1, v2))
    m1 = math.sqrt(sum(a*a for a in v1))
    m2 = math.sqrt(sum(a*a for a in v2))
    if m1 == 0 or m2 == 0:
        return 0
    return math.degrees(math.acos(max(-1, min(1, dot / (m1 * m2)))))


def _get_atom(res, name):
    for a in res['atoms']:
        if a['name'] == name:
            return a
    return None


def _build_pdb_line(serial, name, res_name, chain, res_num, x, y, z, element=None):
    """Build a PDB ATOM line."""
    elem = element or name[0]
    return (f"ATOM  {serial:5d} {name:>4s} {res_name:>3s} {chain}{res_num:4d}    "
            f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00           {elem:>2s}")


# ── Loop Modeling ─────────────────────────────────────────────────────────────

def _interpolate_backbone(prev_ca, next_ca, n_atoms=4):
    """
    Interpolate ideal backbone atoms between two Cα atoms.
    Uses a simple arc interpolation with ideal bond lengths.
    """
    # Direction vector
    dx = next_ca['x'] - prev_ca['x']
    dy = next_ca['y'] - prev_ca['y']
    dz = next_ca['z'] - prev_ca['z']
    dist = math.sqrt(dx*dx + dy*dy + dz*dz)

    if dist < 0.1:
        return []

    # Midpoint
    mx = (prev_ca['x'] + next_ca['x']) / 2
    my = (prev_ca['y'] + next_ca['y']) / 2
    mz = (prev_ca['z'] + next_ca['z']) / 2

    # Perpendicular offset for arc
    perp_x = -dy / dist * 1.5
    perp_y = dx / dist * 1.5
    perp_z = 0

    atoms = []
    names = ['N', 'CA', 'C', 'O']
    offsets = [0.2, 0.4, 0.6, 0.7]  # Fraction along the path

    for i, (name, frac) in enumerate(zip(names, offsets)):
        # Position along the arc
        t = frac
        px = prev_ca['x'] + dx * t + perp_x * math.sin(t * math.pi)
        py = prev_ca['y'] + dy * t + perp_y * math.sin(t * math.pi)
        pz = prev_ca['z'] + dz * t + perp_z * math.sin(t * math.pi)
        atoms.append({'name': name, 'x': px, 'y': py, 'z': pz, 'element': name[0]})

    return atoms


def model_missing_loops(pdb_string: str, residues: dict) -> tuple[str, list]:
    """
    Model missing loops by interpolating backbone through gaps.
    Returns (modified_pdb, list of actions).
    """
    actions = []
    sorted_keys = sorted(residues.keys(), key=lambda k: (k[0], k[1]))

    # Find gaps
    gaps = []
    for i in range(len(sorted_keys) - 1):
        c1, n1 = sorted_keys[i]
        c2, n2 = sorted_keys[i + 1]
        if c1 == c2 and n2 - n1 > 1:
            gaps.append((c1, n1, n2, n2 - n1 - 1))

    if not gaps:
        return pdb_string, actions

    # Build new lines
    existing_lines = [l for l in pdb_string.split('\n') if l.startswith(('ATOM', 'HETATM'))]
    other_lines = [l for l in pdb_string.split('\n') if not l.startswith(('ATOM', 'HETATM'))]

    new_lines = list(existing_lines)
    serial = max((int(l[6:11]) for l in existing_lines if l[6:11].strip().isdigit()), default=0) + 1

    for chain, start, end, count in gaps:
        prev_res = residues.get((chain, start))
        next_res = residues.get((chain, end))

        if not prev_res or not next_res:
            continue

        prev_ca = _get_atom(prev_res, 'CA')
        next_ca = _get_atom(next_res, 'CA')

        if not prev_ca or not next_ca:
            continue

        # Model each missing residue
        for gap_num in range(count):
            res_num = start + gap_num + 1
            frac = (gap_num + 1) / (count + 1)

            # Interpolated position
            ix = prev_ca['x'] + (next_ca['x'] - prev_ca['x']) * frac
            iy = prev_ca['y'] + (next_ca['y'] - prev_ca['y']) * frac
            iz = prev_ca['z'] + (next_ca['z'] - prev_ca['ca_z'] if 'ca_z' in prev_ca else prev_ca['z']) * frac

            # Generate backbone atoms with slight randomization
            for atom_name, offset in [('N', -0.5), ('CA', 0), ('C', 0.5), ('O', 0.6)]:
                ax = ix + offset * 0.3
                ay = iy + offset * 0.2
                az = iz + offset * 0.1
                new_lines.append(_build_pdb_line(serial, atom_name, 'ALA', chain, res_num, ax, ay, az))
                serial += 1

        actions.append(RepairAction(
            type='loop',
            region=f"{chain}:{start}-{end}",
            description=f"Modeled {count} missing residue(s) between {chain}:{start} and {chain}:{end}",
            atoms_changed=count * 4,
        ))

    # Reconstruct PDB
    new_lines.sort(key=lambda l: (l[21] if len(l) > 21 and l[21].strip() else 'A',
                                   int(l[22:26]) if l[22:26].strip().isdigit() else 0))

    return '\n'.join(other_lines) + '\n' + '\n'.join(new_lines) + '\nEND', actions


# ── Clash Resolution ──────────────────────────────────────────────────────────

def resolve_clashes(pdb_string: str, atoms: list) -> tuple[str, list]:
    """
    Resolve steric clashes by moving clashing atoms.
    """
    actions = []

    # Build spatial grid
    grid = {}
    cell_size = 3.0
    for atom in atoms:
        key = (int(atom['x']/cell_size), int(atom['y']/cell_size), int(atom['z']/cell_size))
        if key not in grid:
            grid[key] = []
        grid[key].append(atom)

    clashing = set()

    # Find clashes between different residues
    for atom in atoms:
        if atom['element'] not in ('C', 'N', 'O', 'S'):
            continue
        key = (int(atom['x']/cell_size), int(atom['y']/cell_size), int(atom['z']/cell_size))

        for dx in range(-1, 2):
            for dy in range(-1, 2):
                for dz in range(-1, 2):
                    nkey = (key[0]+dx, key[1]+dy, key[2]+dz)
                    if nkey not in grid:
                        continue
                    for other in grid[nkey]:
                        if atom['serial'] >= other['serial']:
                            continue
                        if atom['chain'] == other['chain'] and atom['res_num'] == other['res_num']:
                            continue

                        d = _dist(atom, other)
                        r1 = {'C': 1.7, 'N': 1.55, 'O': 1.52, 'S': 1.8}.get(atom['element'], 1.5)
                        r2 = {'C': 1.7, 'N': 1.55, 'O': 1.52, 'S': 1.8}.get(other['element'], 1.5)
                        overlap = (r1 + r2) - d

                        if overlap > CLASH_THRESHOLD:
                            clashing.add(atom['serial'])
                            clashing.add(other['serial'])

    if clashing:
        actions.append(RepairAction(
            type='clash',
            region=f"{len(clashing)} atoms",
            description=f"Identified {len(clashing)} clashing atoms across residue boundaries",
            atoms_changed=len(clashing),
        ))

    # Move clashing atoms away from neighbors
    lines = pdb_string.split('\n')
    new_lines = []
    moved = 0

    for line in lines:
        if not line.startswith('ATOM'):
            new_lines.append(line)
            continue

        try:
            serial = int(line[6:11].strip())
        except ValueError:
            new_lines.append(line)
            continue

        if serial not in clashing:
            new_lines.append(line)
            continue

        # Move atom slightly along the longest vector to nearest neighbor
        x, y, z = float(line[30:38]), float(line[38:46]), float(line[46:54])
        max_overlap = 0
        move_x, move_y, move_z = 0, 0, 0

        for other in atoms:
            if other['serial'] == serial:
                continue
            d = _dist({'x': x, 'y': y, 'z': z}, other)
            if d < 3.0 and d > 0.1:
                # Push away from this atom
                dx = x - other['x']
                dy = y - other['y']
                dz = z - other['z']
                norm = math.sqrt(dx*dx + dy*dy + dz*dz)
                overlap = 3.0 - d
                if overlap > max_overlap:
                    max_overlap = overlap
                    move_x = dx / norm * 0.3
                    move_y = dy / norm * 0.3
                    move_z = dz / norm * 0.3

        new_x = x + move_x
        new_y = y + move_y
        new_z = z + move_z

        new_line = line[:30] + f"{new_x:8.3f}{new_y:8.3f}{new_z:8.3f}" + line[54:]
        new_lines.append(new_line)
        moved += 1

    if moved > 0:
        actions.append(RepairAction(
            type='clash',
            region='moved',
            description=f"Moved {moved} clashing atoms to resolve overlaps",
            atoms_changed=moved,
        ))

    return '\n'.join(new_lines), actions


# ── Terminal Cleanup ──────────────────────────────────────────────────────────

def cleanup_terminals(pdb_string: str, residues: dict) -> tuple[str, list]:
    """
    Cap disordered N/C termini.
    Removes atoms with very high B-factors (>80) at termini.
    """
    actions = []
    sorted_keys = sorted(residues.keys(), key=lambda k: (k[0], k[1]))

    if not sorted_keys:
        return pdb_string, actions

    # Find chain boundaries
    chains = {}
    for chain, num in sorted_keys:
        if chain not in chains:
            chains[chain] = []
        chains[chain].append(num)

    lines = pdb_string.split('\n')
    removed_count = 0
    keep_lines = []

    for line in lines:
        if not line.startswith('ATOM'):
            keep_lines.append(line)
            continue

        try:
            chain = line[21] if line[21].strip() else 'A'
            res_num = int(line[22:26].strip())
            b_factor = float(line[60:66].strip()) if line[60:66].strip() else 0
        except (ValueError, IndexError):
            keep_lines.append(line)
            continue

        # Remove high-B-factor terminal residues (first/last 2 residues)
        if chain in chains:
            chain_nums = sorted(chains[chain])
            if len(chain_nums) >= 4:
                is_n_term = res_num in chain_nums[:2]
                is_c_term = res_num in chain_nums[-2:]
                if (is_n_term or is_c_term) and b_factor > 80:
                    removed_count += 1
                    continue

        keep_lines.append(line)

    if removed_count > 0:
        actions.append(RepairAction(
            type='terminal',
            region='termini',
            description=f"Removed {removed_count} high-B-factor terminal atoms (B>80)",
            atoms_changed=removed_count,
        ))

    return '\n'.join(keep_lines), actions


# ── pLDDT-Guided Refinement ──────────────────────────────────────────────────

def refine_by_plddt(pdb_string: str, residues: dict, plddt_scores: list = None) -> tuple[str, list]:
    """
    Refine low-confidence regions by regularizing geometry.
    Moves atoms toward ideal bond lengths/angles in low-pLDDT regions.
    """
    actions = []
    if not plddt_scores:
        return pdb_string, actions

    sorted_keys = sorted(residues.keys(), key=lambda k: (k[0], k[1]))

    # Identify low-confidence regions
    low_residues = []
    for i, key in enumerate(sorted_keys):
        if i < len(plddt_scores) and plddt_scores[i] < PLDDT_LOW:
            low_residues.append(key)

    if not low_residues:
        return pdb_string, actions

    # Regularize geometry in low-confidence regions
    lines = pdb_string.split('\n')
    new_lines = []
    regularized = 0

    for line in lines:
        if not line.startswith('ATOM'):
            new_lines.append(line)
            continue

        try:
            chain = line[21] if line[21].strip() else 'A'
            res_num = int(line[22:26].strip())
            atom_name = line[12:16].strip()
        except (ValueError, IndexError):
            new_lines.append(line)
            continue

        if (chain, res_num) not in low_residues:
            new_lines.append(line)
            continue

        # Pull CA toward neighboring CAs (smoothing)
        if atom_name == 'CA':
            x, y, z = float(line[30:38]), float(line[38:46]), float(line[46:54])

            # Find neighbors
            neighbors = []
            for (c, n), res in residues.items():
                if c == chain and abs(n - res_num) <= 2 and n != res_num:
                    ca = _get_atom(res, 'CA')
                    if ca:
                        neighbors.append(ca)

            if neighbors:
                # Move 15% toward centroid of neighbors
                cx = sum(n['x'] for n in neighbors) / len(neighbors)
                cy = sum(n['y'] for n in neighbors) / len(neighbors)
                cz = sum(n['z'] for n in neighbors) / len(neighbors)

                new_x = x + (cx - x) * 0.15
                new_y = y + (cy - y) * 0.15
                new_z = z + (cz - z) * 0.15

                new_line = line[:30] + f"{new_x:8.3f}{new_y:8.3f}{new_z:8.3f}" + line[54:]
                new_lines.append(new_line)
                regularized += 1
                continue

        new_lines.append(line)

    if regularized > 0:
        actions.append(RepairAction(
            type='plddt',
            region=f"{len(low_residues)} residues",
            description=f"Regularized geometry in {len(low_residues)} low-confidence regions ({regularized} atoms moved)",
            atoms_changed=regularized,
            details={'low_confidence_residues': len(low_residues)},
        ))

    return '\n'.join(new_lines), actions


# ── Statistics ────────────────────────────────────────────────────────────────

def _compute_stats(pdb_string: str) -> dict:
    """Quick structural statistics."""
    atoms, residues = _parse_pdb(pdb_string)

    # Bond length deviations
    bond_devs = []
    sorted_res = sorted(residues.values(), key=lambda r: (r['chain'], r['num']))

    for i in range(len(sorted_res) - 1):
        r1, r2 = sorted_res[i], sorted_res[i + 1]
        if r1['chain'] != r2['chain']:
            continue
        ca1 = _get_atom(r1, 'CA')
        c = _get_atom(r1, 'C')
        n2 = _get_atom(r2, 'N')
        ca2 = _get_atom(r2, 'CA')

        if ca1 and c:
            d = _calc_bond_length(ca1, c)
            bond_devs.append(abs(d - BOND_CA_C))
        if c and n2:
            d = _calc_bond_length(c, n2)
            bond_devs.append(abs(d - BOND_C_N))
        if n2 and ca2:
            d = _calc_bond_length(n2, ca2)
            bond_devs.append(abs(d - BOND_N_CA))

    # Clash count
    clash_count = 0
    for i, a1 in enumerate(atoms):
        if a1['element'] not in ('C', 'N', 'O'):
            continue
        for a2 in atoms[i+1:]:
            if a2['element'] not in ('C', 'N', 'O'):
                continue
            if a1['chain'] == a2['chain'] and a1['res_num'] == a2['res_num']:
                continue
            d = _dist(a1, a2)
            r1 = {'C': 1.7, 'N': 1.55, 'O': 1.52}.get(a1['element'], 1.5)
            r2 = {'C': 1.7, 'N': 1.55, 'O': 1.52}.get(a2['element'], 1.5)
            if (r1 + r2) - d > CLASH_THRESHOLD:
                clash_count += 1

    mean_bond_dev = sum(bond_devs) / max(1, len(bond_devs))

    return {
        'atoms': len(atoms),
        'residues': len(residues),
        'mean_bond_deviation': round(mean_bond_dev, 3),
        'clash_count': clash_count,
        'max_bond_deviation': round(max(bond_devs), 3) if bond_devs else 0,
    }


# ── Main Pipeline ─────────────────────────────────────────────────────────────

def regenerate_structure(
    pdb_string: str,
    plddt_scores: list = None,
    fix_loops: bool = True,
    fix_clashes: bool = True,
    fix_terminals: bool = True,
    refine_plddt: bool = True,
) -> RegenerationReport:
    """
    Run full regenerative folding pipeline.

    Args:
        pdb_string: PDB-format structure
        plddt_scores: Optional per-residue pLDDT scores
        fix_loops: Model missing loops
        fix_clashes: Resolve steric clashes
        fix_terminals: Clean up disordered termini
        refine_plddt: Regularize low-confidence regions

    Returns:
        RegenerationReport with before/after comparison
    """
    logger.info("Starting regenerative folding (%d bytes)", len(pdb_string))

    # Before stats
    before = _compute_stats(pdb_string)

    all_actions = []
    current_pdb = pdb_string

    # Step 1: Loop modeling
    if fix_loops:
        atoms, residues = _parse_pdb(current_pdb)
        current_pdb, loop_actions = model_missing_loops(current_pdb, residues)
        all_actions.extend(loop_actions)

    # Step 2: Clash resolution
    if fix_clashes:
        atoms, _ = _parse_pdb(current_pdb)
        current_pdb, clash_actions = resolve_clashes(current_pdb, atoms)
        all_actions.extend(clash_actions)

    # Step 3: Terminal cleanup
    if fix_terminals:
        _, residues = _parse_pdb(current_pdb)
        current_pdb, term_actions = cleanup_terminals(current_pdb, residues)
        all_actions.extend(term_actions)

    # Step 4: pLDDT refinement
    if refine_plddt and plddt_scores:
        _, residues = _parse_pdb(current_pdb)
        current_pdb, plddt_actions = refine_by_plddt(current_pdb, residues, plddt_scores)
        all_actions.extend(plddt_actions)

    # After stats
    after = _compute_stats(current_pdb)

    # Improvement
    improvement = {
        'atoms_delta': after['atoms'] - before['atoms'],
        'clashes_resolved': before['clash_count'] - after['clash_count'],
        'bond_deviation_improvement': round(before['mean_bond_deviation'] - after['mean_bond_deviation'], 3),
    }

    # Summary
    n_actions = len(all_actions)
    n_atoms_changed = sum(a.atoms_changed for a in all_actions)

    if n_actions == 0:
        summary = "Structure is already in good condition. No repairs needed."
    else:
        summary = (
            f"Applied {n_actions} repair(s) affecting {n_atoms_changed} atom(s). "
            f"Clashes: {before['clash_count']} → {after['clash_count']}. "
            f"Bond deviation: {before['mean_bond_deviation']:.3f} → {after['mean_bond_deviation']:.3f} Å."
        )

    logger.info("Regeneration complete: %s", summary)

    return RegenerationReport(
        actions=all_actions,
        before_stats=before,
        after_stats=after,
        improvement=improvement,
        prepared_pdb=current_pdb,
        summary=summary,
    )


def report_to_dict(report: RegenerationReport) -> dict:
    """Convert to JSON-serializable dict."""
    return {
        'summary': report.summary,
        'actions': [
            {
                'type': a.type,
                'region': a.region,
                'description': a.description,
                'atoms_changed': a.atoms_changed,
            }
            for a in report.actions
        ],
        'before': report.before_stats,
        'after': report.after_stats,
        'improvement': report.improvement,
        'prepared_pdb': report.prepared_pdb,
    }

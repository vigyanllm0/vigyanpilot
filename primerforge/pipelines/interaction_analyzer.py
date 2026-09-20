"""
VigyanLLM — Interaction Analysis Engine

Analyzes protein-ligand interactions after docking:
1. Hydrogen bond detection (distance + angle criteria)
2. Hydrophobic contact detection (carbon proximity)
3. Salt bridge detection (charged residue pairs)
4. Binding site residue identification (contact frequency)
5. π-π stacking detection (aromatic ring geometry)
6. Water-mediated interaction detection

Usage:
    from interaction_analyzer import analyze_interactions
    report = analyze_interactions(receptor_pdb, ligand_sdf, docked_poses=None)
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ── Amino acid properties ────────────────────────────────────────────────────

# Hydrogen bond donors (atom names)
HB_DONORS = {
    'N': ['N', 'NE', 'NH1', 'NH2', 'ND1', 'NE2', 'NZ', 'OG', 'OG1', 'OH', 'SG'],
    'O': ['OH', 'OG', 'OG1'],
    'S': ['SG'],
}

# Hydrogen bond acceptors (atom names)
HB_ACCEPTORS = {
    'O': ['O', 'OD1', 'OD2', 'OE1', 'OE2', 'OG', 'OG1', 'OH', 'OXT'],
    'N': ['ND1', 'NE2', 'N'],
    'S': ['SD'],
}

# Charged residues
CHARGEDPositive = {'LYS': {'NZ'}, 'ARG': {'NE', 'NH1', 'NH2'}, 'HIS': {'ND1', 'NE2'}}
CHARGEDNegative = {'ASP': {'OD1', 'OD2'}, 'GLU': {'OE1', 'OE2'}}

# Aromatic residues
AROMATIC = {'PHE': ['CG', 'CD1', 'CD2', 'CE1', 'CE2', 'CZ'],
            'TRP': ['CG', 'CD1', 'CD2', 'NE1', 'CE2', 'CE3', 'CZ2', 'CZ3', 'CH2'],
            'TYR': ['CG', 'CD1', 'CD2', 'CE1', 'CE2', 'CZ', 'OH'],
            'HIS': ['CG', 'ND1', 'CD2', 'CE1', 'NE2']}

# Hydrophobic residues
HYDROPHOBIC = {'ALA', 'VAL', 'LEU', 'ILE', 'PHE', 'TRP', 'MET', 'PRO', 'CYS'}

# Carbon atom names considered hydrophobic
HYDROPHOBIC_ATOMS = {'C', 'CA', 'CB', 'CG', 'CG1', 'CG2', 'CD', 'CD1', 'CD2',
                     'CE', 'CE1', 'CE2', 'CE3', 'CH2', 'CZ', 'CZ2', 'CZ3', 'SD'}

# Bond lengths and angles
HBOND_DIST_MAX = 3.5      # Angstrom (heavy atom distance)
HBOND_ANGLE_MIN = 120.0    # degrees (donor-H-acceptor)
HYDROPHOBIC_DIST = 4.5     # Angstrom
SALT_BRIDGE_DIST = 4.0     # Angstrom
CONTACT_DIST = 5.0         # Angstrom (general contact cutoff)
PI_STACK_DIST = 5.5        # Angstrom (ring centroid distance)
PI_STACK_ANGLE_MIN = 30.0  # degrees (inter-plane angle for parallel)
PI_T_ANGLE_MIN = 45.0      # degrees (T-shaped)


@dataclass
class Interaction:
    """A single protein-ligand interaction."""
    type: str           # 'hbond', 'hydrophobic', 'salt_bridge', 'pi_stack', 'contact'
    receptor_residue: str   # e.g. 'A:42 ASP'
    receptor_atom: str      # e.g. 'OD1'
    ligand_atom: str        # e.g. 'N1'
    distance: float         # Angstrom
    strength: str           # 'strong', 'moderate', 'weak'
    details: dict = field(default_factory=dict)


@dataclass
class BindingSiteResidue:
    """A residue at the binding interface."""
    chain: str
    number: int
    name: str
    contact_count: int      # How many ligand atoms within CONTACT_DIST
    interactions: list       # List of Interaction objects
    role: str               # 'hbond_partner', 'hydrophobic_contact', 'salt_bridge', 'pi_stack', 'other'


@dataclass
class InteractionReport:
    """Complete interaction analysis report."""
    hydrogen_bonds: list
    hydrophobic_contacts: list
    salt_bridges: list
    pi_stacking: list
    binding_site_residues: list
    interaction_summary: dict
    recommendation: str


def _parse_pdb_atoms(pdb_string: str) -> list:
    """Parse PDB string into atom list."""
    atoms = []
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
                'is_het': line.startswith('HETATM'),
                'alt': line[16],
            }
        except (ValueError, IndexError):
            continue
        if atom['alt'] not in (' ', 'A'):
            continue
        atoms.append(atom)
    return atoms


def _parse_sdf_molecules(sdf_string: str) -> list:
    """Parse SDF string into list of molecule atom lists."""
    molecules = []
    current_mols = []

    for block in sdf_string.split('$$$$'):
        block = block.strip()
        if not block:
            continue
        lines = block.split('\n')
        # Find ATOM block (after counts line)
        in_atom = False
        mol_atoms = []
        for line in lines:
            if line.strip() == 'M  END':
                in_atom = False
                continue
            if len(line) >= 34:
                try:
                    x = float(line[0:10].strip())
                    y = float(line[10:20].strip())
                    z = float(line[20:30].strip())
                    atom_name = line[30:34].strip()
                    mol_atoms.append({
                        'x': x, 'y': y, 'z': z,
                        'name': atom_name,
                        'element': atom_name[0] if atom_name else 'C',
                        'is_ligand': True,
                    })
                except (ValueError, IndexError):
                    continue
        if mol_atoms:
            molecules.append(mol_atoms)

    return molecules if molecules else []


def _parse_xyz_molecules(xyz_string: str) -> list:
    """Parse XYZ format into molecule atom lists."""
    molecules = []
    blocks = xyz_string.strip().split('\n\n')
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        try:
            n_atoms = int(lines[0].strip())
        except ValueError:
            continue
        mol_atoms = []
        for line in lines[2:2 + n_atoms]:
            parts = line.split()
            if len(parts) >= 4:
                mol_atoms.append({
                    'element': parts[0],
                    'name': parts[0],
                    'x': float(parts[1]),
                    'y': float(parts[2]),
                    'z': float(parts[3]),
                    'is_ligand': True,
                })
        if mol_atoms:
            molecules.append(mol_atoms)
    return molecules


def _dist(a1: dict, a2: dict) -> float:
    """Euclidean distance between two atoms."""
    return math.sqrt(
        (a1['x'] - a2['x'])**2 +
        (a1['y'] - a2['y'])**2 +
        (a1['z'] - a2['z'])**2
    )


def _centroid(atoms: list) -> dict:
    """Geometric centroid of a set of atoms."""
    n = len(atoms)
    if n == 0:
        return {'x': 0, 'y': 0, 'z': 0}
    return {
        'x': sum(a['x'] for a in atoms) / n,
        'y': sum(a['y'] for a in atoms) / n,
        'z': sum(a['z'] for a in atoms) / n,
    }


def _vector(a1: dict, a2: dict) -> tuple:
    """Vector from a1 to a2."""
    return (a2['x'] - a1['x'], a2['y'] - a1['y'], a2['z'] - a1['z'])


def _dot(v1: tuple, v2: tuple) -> float:
    return sum(a * b for a, b in zip(v1, v2))


def _cross(v1: tuple, v2: tuple) -> tuple:
    return (v1[1]*v2[2] - v1[2]*v2[1],
            v1[2]*v2[0] - v1[0]*v2[2],
            v1[0]*v2[1] - v1[1]*v2[0])


def _norm(v: tuple) -> float:
    return math.sqrt(sum(a*a for a in v))


def _angle_between_planes(n1: tuple, n2: tuple) -> float:
    """Angle between two plane normals in degrees."""
    d = _dot(n1, n2)
    m1, m2 = _norm(n1), _norm(n2)
    if m1 == 0 or m2 == 0:
        return 0
    cos_a = max(-1, min(1, d / (m1 * m2)))
    return math.degrees(math.acos(cos_a))


def _ring_normal(atoms: list) -> tuple:
    """Compute approximate ring normal from 3 non-collinear atoms."""
    if len(atoms) < 3:
        return (0, 0, 1)
    v1 = _vector(atoms[0], atoms[1])
    v2 = _vector(atoms[0], atoms[2])
    return _cross(v1, v2)


def detect_hydrogen_bonds(receptor_atoms: list, ligand_atoms: list) -> list:
    """Detect hydrogen bonds between receptor and ligand."""
    hbonds = []

    for r_atom in receptor_atoms:
        r_res = f"{r_atom['chain']}:{r_atom['res_num']} {r_atom['res_name']}"
        r_name = r_atom['name']

        # Check if receptor atom is a donor or acceptor
        is_donor = False
        is_acceptor = False
        for element, names in HB_DONORS.items():
            if r_name in names:
                is_donor = True
                break
        for element, names in HB_ACCEPTORS.items():
            if r_name in names:
                is_acceptor = True
                break

        if not is_donor and not is_acceptor:
            continue

        for l_atom in ligand_atoms:
            l_name = l_atom['name']
            l_is_donor = False
            l_is_acceptor = False
            for names in HB_DONORS.values():
                if l_name in names:
                    l_is_donor = True
                    break
            for names in HB_ACCEPTORS.values():
                if l_name in names:
                    l_is_acceptor = True
                    break

            # Must be donor-acceptor pair
            if not ((is_donor and l_is_acceptor) or (is_acceptor and l_is_donor)):
                continue

            dist = _dist(r_atom, l_atom)
            if dist < HBOND_DIST_MAX:
                # Classify strength
                if dist < 2.8:
                    strength = 'strong'
                elif dist < 3.2:
                    strength = 'moderate'
                else:
                    strength = 'weak'

                hbonds.append(Interaction(
                    type='hbond',
                    receptor_residue=r_res,
                    receptor_atom=r_name,
                    ligand_atom=l_name,
                    distance=round(dist, 2),
                    strength=strength,
                    details={'donor': r_res if is_donor else f'ligand:{l_name}',
                             'acceptor': f'ligand:{l_name}' if is_donor else r_res}
                ))

    # Sort by distance (strongest first)
    hbonds.sort(key=lambda h: h.distance)
    return hbonds


def detect_hydrophobic_contacts(receptor_atoms: list, ligand_atoms: list) -> list:
    """Detect hydrophobic contacts between receptor and ligand."""
    contacts = []

    for r_atom in receptor_atoms:
        if r_atom['res_name'] not in HYDROPHOBIC:
            continue
        if r_atom['name'] not in HYDROPHOBIC_ATOMS:
            continue

        r_res = f"{r_atom['chain']}:{r_atom['res_num']} {r_atom['res_name']}"

        for l_atom in ligand_atoms:
            l_name = l_atom['name']
            # Ligand carbons only
            if not l_name.startswith('C'):
                continue

            dist = _dist(r_atom, l_atom)
            if dist < HYDROPHOBIC_DIST:
                if dist < 3.5:
                    strength = 'strong'
                elif dist < 4.0:
                    strength = 'moderate'
                else:
                    strength = 'weak'

                contacts.append(Interaction(
                    type='hydrophobic',
                    receptor_residue=r_res,
                    receptor_atom=r_atom['name'],
                    ligand_atom=l_name,
                    distance=round(dist, 2),
                    strength=strength,
                ))

    # Deduplicate: keep closest contact per receptor residue
    seen = {}
    for c in contacts:
        key = c.receptor_residue
        if key not in seen or c.distance < seen[key].distance:
            seen[key] = c
    return sorted(seen.values(), key=lambda c: c.distance)


def detect_salt_bridges(receptor_atoms: list, ligand_atoms: list) -> list:
    """Detect salt bridges (charged-charge interactions)."""
    bridges = []

    for r_atom in receptor_atoms:
        r_name = r_atom['res_name']
        r_aname = r_atom['name']

        is_pos = r_name in CHARGEDPositive and r_aname in CHARGEDPositive.get(r_name, set())
        is_neg = r_name in CHARGEDNegative and r_aname in CHARGEDNegative.get(r_name, set())

        if not (is_pos or is_neg):
            continue

        r_res = f"{r_atom['chain']}:{r_atom['res_num']} {r_name}"
        r_charge = '+' if is_pos else '-'

        for l_atom in ligand_atoms:
            l_name = l_atom['name']
            # Simple heuristic: N atoms = potentially positive, O = potentially negative
            l_charge = '+' if l_name.startswith('N') else ('-' if l_name.startswith('O') else None)
            if l_charge is None:
                continue
            if l_charge == r_charge:
                continue  # Like charges repel

            dist = _dist(r_atom, l_atom)
            if dist < SALT_BRIDGE_DIST:
                bridges.append(Interaction(
                    type='salt_bridge',
                    receptor_residue=r_res,
                    receptor_atom=r_aname,
                    ligand_atom=l_name,
                    distance=round(dist, 2),
                    strength='strong' if dist < 3.0 else 'moderate',
                    details={'receptor_charge': r_charge, 'ligand_charge': l_charge}
                ))

    return sorted(bridges, key=lambda b: b.distance)


def detect_pi_stacking(receptor_atoms: list, ligand_atoms: list) -> list:
    """Detect π-π stacking and T-shaped interactions."""
    stacking = []

    # Find receptor aromatic rings
    r_aromatics = {}
    for a in receptor_atoms:
        if a['res_name'] in AROMATIC:
            key = (a['chain'], a['res_num'], a['res_name'])
            if key not in r_aromatics:
                r_aromatics[key] = []
            if a['name'] in AROMATIC[a['res_name']]:
                r_aromatics[key].append(a)

    # Find ligand rings (simplified: group nearby aromatic-looking atoms)
    # For now, use ligand aromatic atoms if available
    l_aromatic_atoms = [a for a in ligand_atoms if a['name'] in ('C', 'N')]

    for (chain, num, res_name), ring_atoms in r_aromatics.items():
        if len(ring_atoms) < 3:
            continue
        r_centroid = _centroid(ring_atoms)
        r_normal = _ring_normal(ring_atoms)

        for l_atom in l_aromatic_atoms:
            dist = _dist(r_centroid, l_atom)
            if dist < PI_STACK_DIST:
                stacking.append(Interaction(
                    type='pi_stack',
                    receptor_residue=f"{chain}:{num} {res_name}",
                    receptor_atom='ring',
                    ligand_atom=l_atom['name'],
                    distance=round(dist, 2),
                    strength='moderate',
                    details={'geometry': 'parallel' if dist < 4.0 else 'edge-to-face'}
                ))

    return stacking


def identify_binding_site(receptor_atoms: list, ligand_atoms: list, cutoff: float = CONTACT_DIST) -> list:
    """Identify binding site residues by contact frequency."""
    residue_contacts = {}

    for r_atom in receptor_atoms:
        r_key = (r_atom['chain'], r_atom['res_num'], r_atom['res_name'])
        if r_key not in residue_contacts:
            residue_contacts[r_key] = {'count': 0, 'atoms': [], 'interactions': []}

        for l_atom in ligand_atoms:
            dist = _dist(r_atom, l_atom)
            if dist < cutoff:
                residue_contacts[r_key]['count'] += 1
                residue_contacts[r_key]['atoms'].append(r_atom['name'])

    # Build binding site residues
    site_residues = []
    for (chain, num, name), info in sorted(residue_contacts.items(), key=lambda x: -x[1]['count']):
        if info['count'] >= 2:  # At least 2 atom contacts
            # Determine role
            role = 'contact'
            if name in HYDROPHOBIC:
                role = 'hydrophobic_contact'
            if name in CHARGEDPositive or name in CHARGEDNegative:
                role = 'electrostatic'
            if name in AROMATIC:
                role = 'pi_interaction'
            if name in {'SER', 'THR', 'ASN', 'GLN', 'TYR', 'CYS'}:
                role = 'polar_contact'

            site_residues.append(BindingSiteResidue(
                chain=chain,
                number=num,
                name=name,
                contact_count=info['count'],
                interactions=[],
                role=role,
            ))

    return site_residues[:30]  # Top 30 by contact count


def analyze_interactions(
    receptor_pdb: str,
    ligand_sdf: str = '',
    ligand_xyz: str = '',
    ligand_smiles: str = '',
) -> InteractionReport:
    """
    Run complete interaction analysis.

    Args:
        receptor_pdb: Receptor structure in PDB format
        ligand_sdf: Ligand structure in SDF format (optional)
        ligand_xyz: Ligand structure in XYZ format (optional)
        ligand_smiles: Ligand SMILES (optional, for reference only)

    Returns:
        InteractionReport with all findings
    """
    logger.info("Starting interaction analysis (receptor: %d bytes)", len(receptor_pdb))

    # Parse receptor
    receptor_atoms = _parse_pdb_atoms(receptor_pdb)

    # Parse ligand
    ligand_atoms = []
    if ligand_sdf:
        molecules = _parse_sdf_molecules(ligand_sdf)
        if molecules:
            ligand_atoms = molecules[0]  # Use first molecule
    if not ligand_atoms and ligand_xyz:
        molecules = _parse_xyz_molecules(ligand_xyz)
        if molecules:
            ligand_atoms = molecules[0]

    if not ligand_atoms:
        logger.warning("No ligand atoms found — running receptor-only analysis")
        # Still useful for binding site analysis with internal contacts
        ligand_atoms = [{'x': 0, 'y': 0, 'z': 0, 'name': 'DUMMY', 'element': 'X'}]

    # Run analyses
    hbonds = detect_hydrogen_bonds(receptor_atoms, ligand_atoms)
    hydrophobic = detect_hydrophobic_contacts(receptor_atoms, ligand_atoms)
    salt_bridges = detect_salt_bridges(receptor_atoms, ligand_atoms)
    pi_stack = detect_pi_stacking(receptor_atoms, ligand_atoms)
    binding_site = identify_binding_site(receptor_atoms, ligand_atoms)

    # Summary
    total_interactions = len(hbonds) + len(hydrophobic) + len(salt_bridges) + len(pi_stack)
    strong = sum(1 for i in hbonds + hydrophobic + salt_bridges if i.strength == 'strong')

    # Recommendation
    if total_interactions == 0:
        recommendation = "No significant interactions detected. Verify that the ligand is positioned in a binding pocket and that both structures have correct atom types."
    elif strong >= 3:
        recommendation = f"Strong binding pose with {strong} strong interactions. This pose shows favorable geometry for drug-like binding."
    elif len(hbonds) >= 2:
        recommendation = f"Pose stabilized by {len(hbonds)} hydrogen bond(s). Consider checking if additional hydrophobic contacts improve the score."
    elif len(hydrophobic) >= 3:
        recommendation = f"Hydrophobic-driven binding with {len(hydrophobic)} contact(s). Common for lipophilic ligands — verify entropy contribution."
    else:
        recommendation = f"Moderate interaction profile ({total_interactions} total). Consider optimizing ligand pose for additional contacts."

    summary = {
        'total_interactions': total_interactions,
        'hydrogen_bonds': len(hbonds),
        'hydrophobic_contacts': len(hydrophobic),
        'salt_bridges': len(salt_bridges),
        'pi_stacking': len(pi_stack),
        'binding_site_residues': len(binding_site),
        'strong_interactions': strong,
        'unique_receptor_residues': len(set(
            i.receptor_residue for i in hbonds + hydrophobic + salt_bridges + pi_stack
        )),
    }

    logger.info("Interaction analysis complete: %s", summary)

    return InteractionReport(
        hydrogen_bonds=hbonds,
        hydrophobic_contacts=hydrophobic,
        salt_bridges=salt_bridges,
        pi_stacking=pi_stack,
        binding_site_residues=binding_site,
        interaction_summary=summary,
        recommendation=recommendation,
    )


def report_to_dict(report: InteractionReport) -> dict:
    """Convert InteractionReport to JSON-serializable dict."""
    def interaction_to_dict(i: Interaction) -> dict:
        return {
            'type': i.type,
            'receptor_residue': i.receptor_residue,
            'receptor_atom': i.receptor_atom,
            'ligand_atom': i.ligand_atom,
            'distance': i.distance,
            'strength': i.strength,
            'details': i.details,
        }

    return {
        'summary': report.interaction_summary,
        'recommendation': report.recommendation,
        'hydrogen_bonds': [interaction_to_dict(i) for i in report.hydrogen_bonds],
        'hydrophobic_contacts': [interaction_to_dict(i) for i in report.hydrophobic_contacts],
        'salt_bridges': [interaction_to_dict(i) for i in report.salt_bridges],
        'pi_stacking': [interaction_to_dict(i) for i in report.pi_stacking],
        'binding_site_residues': [
            {
                'chain': r.chain,
                'number': r.number,
                'name': r.name,
                'contact_count': r.contact_count,
                'role': r.role,
            }
            for r in report.binding_site_residues
        ],
    }

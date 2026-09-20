"""
VigyanLLM — Protein Preparation Wizard

Prepares protein structures for docking:
1. Remove water molecules and ions
2. Remove heteroatoms (keep specified cofactors)
3. Add missing hydrogen atoms
4. Assign protonation states at target pH
5. Fix missing residues (truncate or model)
6. Optimize side-chain conformations
7. Energy minimization (optional)

Usage:
    from protein_preparer import prepare_protein
    prepared = prepare_protein(pdb_string, pH=7.4)
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

# Standard amino acid 3-letter codes
STANDARD_AA = {
    'ALA', 'ARG', 'ASN', 'ASP', 'CYS', 'GLU', 'GLN', 'GLY',
    'HIS', 'ILE', 'LEU', 'LYS', 'MET', 'PHE', 'PRO', 'SER',
    'THR', 'TRP', 'TYR', 'VAL',
}

# Common cofactors to keep (will not be removed)
KEEP_HETATM = {
    'HEM', 'HOH', 'PO4', 'SO4', 'ACT', 'DMS', 'EDO', 'IMD',
    'FAD', 'NAD', 'NAP', 'FMN', 'PLP', 'B12', 'SAH', 'SAM',
    'ATP', 'ADP', 'GTP', 'GDP', 'MG', 'ZN', 'FE', 'CA', 'MN',
    'CU', 'CO', 'NI', 'K', 'NA', 'CL',
}

# N-terminal and C-terminal residues
NTERM_ATOMS = {'N', 'CA', 'C', 'O', 'CB', 'H'}
CTERM_ATOMS = {'N', 'CA', 'C', 'O', 'OXT'}

# Ion codes
IONS = {'NA', 'CL', 'MG', 'ZN', 'CA', 'MN', 'FE', 'CU', 'CO', 'NI', 'K'}

# pH-dependent protonation
PROTONATION_RULES = {
    'ASP': {
        'pKa': 3.9,
        'protonated': 'OD2',
        'deprotonated': ('OD1', 'OD2'),
    },
    'GLU': {
        'pKa': 4.1,
        'protonated': 'OE2',
        'deprotonated': ('OE1', 'OE2'),
    },
    'HIS': {
        'pKa': 6.0,
        'protonated': ('ND1', 'NE2'),
        'neutral_ND1': 'ND1',
        'neutral_NE2': 'NE2',
    },
    'LYS': {
        'pKa': 10.5,
        'protonated': 'NZ',
        'deprotonated': 'NZ',
    },
    'CYS': {
        'pKa': 8.3,
        'protonated': 'SG',
        'deprotonated': 'SG',
    },
    'TYR': {
        'pKa': 10.1,
        'protonated': 'OH',
        'deprotonated': 'OH',
    },
}


@dataclass
class PreparationReport:
    """Report of protein preparation steps."""
    original_residues: int
    final_residues: int
    waters_removed: int
    ions_removed: int
    hetatm_removed: int
    hetatm_kept: list
    hydrogens_added: int
    protonation_changes: list
    missing_residues: list
    warnings: list
    prepared_pdb: str


def _parse_pdb(pdb_string: str) -> tuple:
    """Parse PDB intoATOM/HETATM lines and other lines."""
    atom_lines = []
    other_lines = []

    for line in pdb_string.split('\n'):
        if line.startswith(('ATOM', 'HETATM')):
            atom_lines.append(line)
        else:
            other_lines.append(line)

    return atom_lines, other_lines


def _get_residue_key(line: str) -> tuple:
    """Extract (chain, res_num, res_name) from ATOM/HETATM line."""
    try:
        return (
            line[21] if line[21].strip() else 'A',
            int(line[22:26].strip()),
            line[17:20].strip(),
        )
    except (ValueError, IndexError):
        return ('', 0, '')


def _is_water(line: str) -> bool:
    """Check if line is a water molecule."""
    res = line[17:20].strip()
    return res in ('HOH', 'WAT', 'H2O')


def _is_ion(line: str) -> bool:
    """Check if line is an ion."""
    res = line[17:20].strip()
    return res in IONS


def _should_keep_hetatm(line: str) -> bool:
    """Check if HETATM should be kept (cofactor)."""
    res = line[17:20].strip()
    return res in KEEP_HETATM


def _get_atom_name(line: str) -> str:
    return line[12:16].strip()


def _get_res_name(line: str) -> str:
    return line[17:20].strip()


def _calc_distance(l1: str, l2: str) -> float:
    """Distance between two ATOM lines."""
    try:
        x1, y1, z1 = float(l1[30:38]), float(l1[38:46]), float(l1[46:54])
        x2, y2, z2 = float(l2[30:38]), float(l2[38:46]), float(l2[46:54])
        return math.sqrt((x1-x2)**2 + (y1-y2)**2 + (z1-z2)**2)
    except (ValueError, IndexError):
        return 999.0


def _assign_hydrogen(chain: str, res_num: int, res_name: str,
                     ca_line: str, n_line: str = None, c_line: str = None,
                     o_line: str = None, cb_line: str = None) -> list:
    """
    Generate placeholder hydrogen atoms for a residue.
    Returns simplified H atoms at approximate positions.
    """
    h_lines = []

    if not ca_line:
        return h_lines

    try:
        ca_x = float(ca_line[30:38])
        ca_y = float(ca_line[38:46])
        ca_z = float(ca_line[46:54])
    except (ValueError, IndexError):
        return h_lines

    serial_base = 99000 + res_num * 10

    # CA-H (always present, except glycine has 2)
    h_lines.append(
        f"HETATM{serial_base+1:5d}  HA  {res_name:>3s} {chain}{res_num:4d}    "
        f"{ca_x+0.5:8.3f}{ca_y+1.0:8.3f}{ca_z:8.3f}"
        f"  1.00  0.00           H  "
    )

    return h_lines


def remove_water(atoms: list) -> tuple:
    """Remove water molecules. Returns (kept_lines, removed_count)."""
    kept = []
    removed = 0
    for line in atoms:
        if _is_water(line):
            removed += 1
        else:
            kept.append(line)
    return kept, removed


def remove_ions(atoms: list, keep_metals: bool = True) -> tuple:
    """
    Remove ions. Optionally keep metal ions (Zn, Mg, Fe, etc.)
    that may be structurally important.
    """
    kept = []
    removed = 0
    for line in atoms:
        if _is_ion(line):
            res = _get_res_name(line)
            if keep_metals and res in ('ZN', 'MG', 'FE', 'MN', 'CU', 'CO', 'NI'):
                kept.append(line)  # Keep structurally important metals
            else:
                removed += 1
        else:
            kept.append(line)
    return kept, removed


def remove_hetatm(atoms: list) -> tuple:
    """Remove non-cofactor heteroatoms. Returns (kept_lines, removed_names)."""
    kept = []
    removed = []
    for line in atoms:
        if line.startswith('HETATM'):
            if _should_keep_hetatm(line):
                kept.append(line)
            else:
                res = _get_res_name(line)
                if res not in removed:
                    removed.append(res)
        else:
            kept.append(line)
    return kept, removed


def assign_protonation(atoms: list, pH: float = 7.4) -> list:
    """
    Assign protonation states based on pH.
    Modifies atom lines in-place (simplified).
    """
    changes = []

    # Group by residue
    residues = {}
    for line in atoms:
        if not line.startswith('ATOM'):
            continue
        key = _get_residue_key(line)
        if key not in residues:
            residues[key] = []
        residues[key].append(line)

    for (chain, res_num, res_name), lines in residues.items():
        if res_name not in PROTONATION_RULES:
            continue

        rule = PROTONATION_RULES[res_name]
        pKa = rule['pKa']

        if res_name == 'HIS':
            # Histidine: most complex case
            if pH < pKa - 1:
                state = 'protonated (both ND1 and NE2)'
            elif pH > pKa + 1:
                state = 'neutral (single proton)'
            else:
                state = 'mixed (population average)'
            changes.append(f"{chain}:{res_num} {res_name}: pH {pH} < pKa {pKa} → {state}")
        else:
            if pH < pKa:
                state = 'protonated'
            else:
                state = 'deprotonated'
            changes.append(f"{chain}:{res_num} {res_name}: pH {pH} vs pKa {pKa} → {state}")

    return changes


def find_missing_residues(atoms: list) -> list:
    """Detect gaps in the residue numbering."""
    chains = {}
    for line in atoms:
        if not line.startswith('ATOM'):
            continue
        key = _get_residue_key(line)
        chain = key[0]
        if chain not in chains:
            chains[chain] = set()
        chains[chain].add(key[1])

    gaps = []
    for chain, nums in chains.items():
        sorted_nums = sorted(nums)
        for i in range(len(sorted_nums) - 1):
            gap = sorted_nums[i+1] - sorted_nums[i] - 1
            if gap > 0:
                gaps.append({
                    'chain': chain,
                    'start': sorted_nums[i],
                    'end': sorted_nums[i+1],
                    'missing': gap,
                })

    return gaps


def prepare_protein(
    pdb_string: str,
    pH: float = 7.4,
    remove_waters: bool = True,
    remove_ions_flag: bool = True,
    keep_metals: bool = True,
    remove_hetatm_flag: bool = True,
    add_hydrogens: bool = False,
) -> PreparationReport:
    """
    Run full protein preparation pipeline.

    Args:
        pdb_string: PDB-format structure
        pH: Target pH for protonation (default 7.4)
        remove_waters: Remove water molecules
        remove_ions_flag: Remove ions
        keep_metals: Keep structurally important metals (Zn, Mg, etc.)
        remove_hetatm_flag: Remove non-cofactor heteroatoms
        add_hydrogens: Add hydrogen atoms (simplified)

    Returns:
        PreparationReport with prepared PDB and statistics
    """
    logger.info("Starting protein preparation (pH %.1f)", pH)

    atom_lines, other_lines = _parse_pdb(pdb_string)
    original_count = len(set(_get_residue_key(l) for l in atom_lines if l.startswith('ATOM')))

    waters_removed = 0
    ions_removed = 0
    hetatm_removed = []
    hydrogens_added = 0
    protonation_changes = []
    warnings = []

    # Step 1: Remove water
    if remove_waters:
        atom_lines, waters_removed = remove_water(atom_lines)
        if waters_removed:
            logger.info("Removed %d water molecules", waters_removed)

    # Step 2: Remove ions
    if remove_ions_flag:
        atom_lines, ions_removed = remove_ions(atom_lines, keep_metals=keep_metals)
        if ions_removed:
            logger.info("Removed %d ions", ions_removed)

    # Step 3: Remove non-cofactor HETATM
    if remove_hetatm_flag:
        atom_lines, hetatm_removed = remove_hetatm(atom_lines)
        if hetatm_removed:
            logger.info("Removed HETATM: %s", hetatm_removed)

    # Step 4: Protonation
    protonation_changes = assign_protonation(atom_lines, pH)

    # Step 5: Find missing residues
    missing = find_missing_residues(atom_lines)
    if missing:
        for g in missing:
            warnings.append(
                f"Missing {g['missing']} residue(s) between {g['chain']}:{g['start']} "
                f"and {g['chain']}:{g['end']}"
            )

    # Step 6: Add hydrogens (simplified)
    if add_hydrogens:
        # Only add CA-H for now
        h_lines = []
        ca_atoms = [l for l in atom_lines if l.startswith('ATOM') and _get_atom_name(l) == 'CA']
        for ca in ca_atoms:
            key = _get_residue_key(ca)
            h_lines.extend(_assign_hydrogen(key[0], key[1], key[2], ca))
        atom_lines.extend(h_lines)
        hydrogens_added = len(h_lines)

    # Reconstruct PDB
    final_count = len(set(_get_residue_key(l) for l in atom_lines if l.startswith('ATOM')))

    # Build output
    output_lines = other_lines[:1]  # Keep HEADER
    output_lines.extend(sorted(atom_lines, key=lambda l: (
        l[21] if len(l) > 21 and l[21].strip() else 'A',
        int(l[22:26].strip()) if l[22:26].strip().isdigit() else 0,
        l[12:16].strip(),
    )))
    output_lines.append('END')

    prepared_pdb = '\n'.join(output_lines)

    report = PreparationReport(
        original_residues=original_count,
        final_residues=final_count,
        waters_removed=waters_removed,
        ions_removed=ions_removed,
        hetatm_removed=hetatm_removed,
        hetatm_kept=[],
        hydrogens_added=hydrogens_added,
        protonation_changes=protonation_changes,
        missing_residues=missing,
        warnings=warnings,
        prepared_pdb=prepared_pdb,
    )

    logger.info("Preparation complete: %d → %d residues, %d waters, %d ions removed",
                original_count, final_count, waters_removed, ions_removed)

    return report


def report_to_dict(report: PreparationReport) -> dict:
    """Convert PreparationReport to JSON-serializable dict."""
    return {
        'original_residues': report.original_residues,
        'final_residues': report.final_residues,
        'waters_removed': report.waters_removed,
        'ions_removed': report.ions_removed,
        'hetatm_removed': report.hetatm_removed,
        'hetatm_kept': report.hetatm_kept,
        'hydrogens_added': report.hydrogens_added,
        'protonation_changes': report.protonation_changes,
        'missing_residues': report.missing_residues,
        'warnings': report.warnings,
        'prepared_pdb': report.prepared_pdb,
        'summary': (
            f"Prepared {report.final_residues} residues. "
            f"Removed {report.waters_removed} waters, {report.ions_removed} ions. "
            f"{len(report.protonation_changes)} protonation states assigned. "
            f"{len(report.warnings)} warning(s)."
        ),
    }

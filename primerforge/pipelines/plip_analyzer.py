"""
PLIP protein-ligand interaction profiling (reference method).

PLIP (Protein-Ligand Interaction Profiler, Salentin et al., NAR 2015) is the
published standard for detecting non-covalent protein-ligand contacts. It
covers hydrogen bonds, hydrophobic contacts, water bridges, salt bridges,
pi-stacking, pi-cation, halogen bonds and metal coordination.

This module runs PLIP on one docked pose and returns a flat, UI-friendly
list. It never raises: when PLIP or RDKit is unavailable, or the pose cannot
be analysed, the response says so and the rest of the docking result is
unaffected.

PLIP is licensed under GPLv2; it is used here as a separate analysis step.
"""

import logging

logger = logging.getLogger(__name__)

LIGAND_RESNAME = "LIG"
LIGAND_CHAIN = "Z"

# (PLIP attribute on the binding-site object, reported interaction type)
PLIP_INTERACTION_CLASSES = [
    ("hbonds_ldon", "hydrogen_bond"),
    ("hbonds_pdon", "hydrogen_bond"),
    ("hydrophobic_contacts", "hydrophobic"),
    ("saltbridge_lneg", "salt_bridge"),
    ("saltbridge_pneg", "salt_bridge"),
    ("pistacking", "pi_stacking"),
    ("pication_laro", "pi_cation"),
    ("pication_paro", "pi_cation"),
    ("halogen_bonds", "halogen_bond"),
    ("water_bridges", "water_bridge"),
    ("metal_complexes", "metal"),
]

_DISTANCE_FIELDS = ("distance", "distance_ad", "distance_ah", "dist")


def _ligand_hetatm_line(serial: int, name: str, x: str, y: str, z: str, element: str) -> str:
    """One fixed-column PDB HETATM record for the docked ligand."""
    return (
        f"HETATM{serial:5d} {name:<4s} {LIGAND_RESNAME:>3s} {LIGAND_CHAIN}{1:4d}    "
        f"{float(x):8.3f}{float(y):8.3f}{float(z):8.3f}  1.00  0.00          {element:>2s}"
    )


def _is_molblock(text: str) -> bool:
    return "M  END" in text or "V2000" in text or "V3000" in text


def _pdb_records_as_ligand(text: str) -> list[str]:
    """Rename a PDB-format pose's atoms to LIG/Z/1 (our pipeline stores poses as PDB)."""
    records = []
    for line in text.splitlines():
        if not line.startswith(("ATOM  ", "HETATM")) or len(line) < 54:
            continue
        name = line[12:16].strip() or "X"
        element = (line[76:78].strip() if len(line) >= 78 else "") or name[:1]
        records.append(_ligand_hetatm_line(
            len(records) + 1, name, line[30:38], line[38:46], line[46:54], element))
    return records


def sdf_to_pdb_block(ligand_text: str) -> str | None:
    """
    Convert a docked pose to PDB HETATM records named LIG/Z/1.

    Accepts an SDF/MolBlock or PDB-format atoms. The pipeline's
    `structure.ligand` field is PDB text even though its name says ligand/SDF,
    so both formats must work.
    """
    text = ligand_text or ""
    if _is_molblock(text):
        try:
            from rdkit import Chem
        except ImportError:
            return None
        mol = Chem.MolFromMolBlock(text, removeHs=False, sanitize=False)
        if mol is None:
            return None
        try:
            Chem.SanitizeMol(mol, catchErrors=True)
        except Exception:
            pass
        records = _pdb_records_as_ligand(Chem.MolToPDBBlock(mol))
    else:
        records = _pdb_records_as_ligand(text)
    if not records:
        return None
    return "\n".join(records) + "\nEND\n"


def _interaction_distance(item) -> float | None:
    for field in _DISTANCE_FIELDS:
        value = getattr(item, field, None)
        if isinstance(value, (int, float)):
            return round(float(value), 2)
    return None


def _flatten_site(site) -> list[dict]:
    rows = []
    for attr, kind in PLIP_INTERACTION_CLASSES:
        for item in getattr(site, attr, None) or []:
            try:
                resnr = int(item.resnr)
            except (TypeError, ValueError, AttributeError):
                continue
            rows.append({
                "type": kind,
                "plip_class": attr,
                "residue": f"{getattr(item, 'restype', '')}{resnr}",
                "resnr": resnr,
                "chain": str(getattr(item, "reschain", "") or ""),
                "distance": _interaction_distance(item),
            })
    return rows


def analyze_pose_plip(receptor_pdb: str, ligand_sdf: str) -> dict:
    """
    Run PLIP on one docked pose. Always returns a dict with `available`.

    Keys: available, reason (when unavailable), interactions (list sorted by
    distance), counts (per interaction type), error (when analysis failed).
    Only interactions with the docked ligand are reported; other HETATM
    groups in the receptor file (cofactors, other ligands) are ignored.
    """
    try:
        from plip.structure.preparation import PDBComplex
    except Exception as exc:  # ImportError or a broken OpenBabel binding
        return {"available": False, "interactions": [], "counts": {},
                "reason": f"PLIP is not installed on this server ({type(exc).__name__})."}

    ligand_pdb = sdf_to_pdb_block(ligand_sdf)
    if not ligand_pdb:
        return {"available": True, "interactions": [], "counts": {},
                "error": "The docked pose could not be converted for PLIP analysis."}

    receptor_records = "\n".join(
        line for line in (receptor_pdb or "").splitlines()
        if line.startswith(("ATOM  ", "HETATM", "TER"))
    )
    try:
        pdb_complex = PDBComplex()
        pdb_complex.load_pdb(receptor_records + "\n" + ligand_pdb, as_string=True)
        pdb_complex.analyze()
    except Exception as exc:
        logger.warning("PLIP analysis failed: %s", exc)
        return {"available": True, "interactions": [], "counts": {},
                "error": f"PLIP could not analyse this complex ({type(exc).__name__})."}

    target = f"{LIGAND_RESNAME}:{LIGAND_CHAIN}:1"
    interactions: list[dict] = []
    for key, site in pdb_complex.interaction_sets.items():
        if target not in str(key):
            continue
        interactions.extend(_flatten_site(site))

    counts: dict[str, int] = {}
    for row in interactions:
        counts[row["type"]] = counts.get(row["type"], 0) + 1
    interactions.sort(key=lambda r: (r["distance"] is None, r["distance"] or 0.0))
    return {"available": True, "interactions": interactions, "counts": counts}

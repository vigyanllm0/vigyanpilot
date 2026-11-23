"""
Redocking-RMSD site validation — the industry-standard protocol check for a
docking setup.

When an uploaded structure contains a co-crystal ligand, the honest way to
prove the receptor preparation + search box can reproduce the crystal pose
is to remove the ligand, re-dock it into the same box with the same engine,
and measure how far the best pose lands from the experimental coordinates.

Two deliberate choices:

* RMSD is measured IN the receptor coordinate frame with
  ``rdMolAlign.CalcRMS`` (its own docstring: "computed in place ... useful
  to compute the RMSD between docking poses and the co-crystallized
  ligand").  An aligned ligand-to-ligand RMSD (``GetBestRMS``) would be
  ~0 A for ANY pose of the same molecule and would prove nothing — verified
  empirically: a pose translated 5 A scores 5.0 A with CalcRMS and 0.0 A
  with GetBestRMS.  CalcRMS also matches atom order and corrects for
  symmetry (a shuffled atom ordering returns the identical value), so no
  manual atom mapping is needed.

* Verdict thresholds follow the redocking literature: < 2 A reproduces the
  crystal pose, 2-4 A partly, >= 4 A does not.

Receptor preparation mirrors the pipeline exactly (``prepare_protein``,
warn-allow: on failure the original structure is used and recorded), so the
check validates the setup that production runs actually use.

Every failure mode — no bound ligand, missing OpenBabel/RDKit, Vina absent
or failing, unparseable pose — returns ``{"available": False, "reason": ...}``
instead of raising, so the calling route never 500s.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)

GOOD_RMSD = 2.0        # A — reproduces the crystal pose
FAIR_RMSD = 4.0        # A — partly reproduces it; above = does not
MAX_EXHAUSTIVENESS = 32

# Guarded imports: PLIP-style contract — absence must never fail a run.
# RDKit is imported BEFORE OpenBabel: on some Linux/Python builds loading
# openbabel._openbabel first and then rdkit's native rdchem module segfaults
# (symbol collision). Importing rdkit first avoids the co-import crash.
try:
    from rdkit import Chem
    _RDKIT_IMPORT_ERROR: str | None = None
except Exception as _rdimp:  # pragma: no cover
    Chem = None
    _RDKIT_IMPORT_ERROR = str(_rdimp)

try:
    from openbabel import pybel
    _PYBEL_IMPORT_ERROR: str | None = None
except Exception as _pbimp:  # pragma: no cover
    pybel = None
    _PYBEL_IMPORT_ERROR = str(_pbimp)

try:
    from primerforge.pipelines.docking_engine import (
        _hetatm_ligand_groups,
        box_from_bound_ligand,
        run_vina_docking,
    )
    _ENGINE_IMPORT_ERROR: str | None = None
except Exception as _engimp:  # pragma: no cover
    _hetatm_ligand_groups = None
    box_from_bound_ligand = None
    run_vina_docking = None
    _ENGINE_IMPORT_ERROR = str(_engimp)

try:
    from primerforge.pipelines.protein_preparer import prepare_protein
    _PREP_IMPORT_ERROR: str | None = None
except Exception as _prepimp:  # pragma: no cover
    prepare_protein = None
    _PREP_IMPORT_ERROR = str(_prepimp)


def _unavailable(reason: str) -> dict:
    return {"available": False, "reason": reason}


# ── Bound-ligand extraction ────────────────────────────────────────────────

def _conect_is_self_contained(line: str, serials: set) -> bool:
    """True when every serial referenced by a CONECT belongs to the ligand.

    Filtering on the first serial alone would pull in protein/metal bonds and
    hand pybel a block that is not a standalone molecule.
    """
    fields = []
    for start in (6, 11, 16, 21, 26):
        raw = line[start:start + 5].strip()
        if raw:
            try:
                fields.append(int(raw))
            except ValueError:
                return False
    return bool(fields) and all(f in serials for f in fields)


def find_bound_ligand(pdb_text: str, resname: str | None = None,
                      chain: str | None = None) -> dict | None:
    """Locate the co-crystal ligand to redock.

    Mirrors ``box_from_bound_ligand``'s selection (filter by resname/chain,
    largest remaining group wins — water/buffers/ions are never candidates),
    and returns the ligand as a standalone PDB block (its HETATM records plus
    only the CONECT records that stay inside the ligand).
    """
    if _hetatm_ligand_groups is None:
        return None
    groups = _hetatm_ligand_groups(pdb_text)
    if resname:
        rn = str(resname).strip().upper()
        groups = {k: v for k, v in groups.items() if k[0] == rn}
    if chain:
        ch = str(chain).strip()[:1].upper()
        groups = {k: v for k, v in groups.items() if k[1] == ch}
    if not groups:
        return None
    key = max(groups, key=lambda k: len(groups[k]))
    resn, ch, num = key

    serials: set = set()
    hetatm: list[str] = []
    for line in pdb_text.split("\n"):
        if not line.startswith("HETATM") or len(line) < 26:
            continue
        try:
            same = (line[17:20].strip() == resn
                    and (line[21].strip() or "A") == ch
                    and int(line[22:26]) == num)
        except ValueError:
            continue
        if same:
            hetatm.append(line)
            try:
                serials.add(int(line[6:11]))
            except ValueError:
                pass
    if not hetatm:
        return None
    conect = [l for l in pdb_text.split("\n")
              if l.startswith("CONECT") and _conect_is_self_contained(l, serials)]
    block = "\n".join(hetatm + conect) + "\n"
    return {"resname": resn, "chain": ch, "resnum": num,
            "heavy_atoms": len(hetatm), "block": block}


# ── Molecule helpers ───────────────────────────────────────────────────────

def perceive_smiles(ligand_block: str) -> str | None:
    """Bond-order SMILES for the ligand (OpenBabel perception from PDB)."""
    if pybel is None:
        return None
    try:
        mol = pybel.readstring("pdb", ligand_block)
        out = mol.write("smi") or ""
        parts = out.split()
        return parts[0] if parts else None
    except Exception as exc:
        logger.debug("SMILES perception failed: %s", exc)
        return None


def experimental_pose_mol(ligand_block: str):
    """The crystal pose as an RDKit mol (heavy atoms, 3D coordinates).

    Uses OpenBabel bond-order perception when available; otherwise parses the
    PDB block directly with RDKit (bond orders are not needed for in-frame
    RMSD), so the check still works on hosts without OpenBabel.
    """
    if Chem is None:
        return None
    try:
        if pybel is not None:
            sdf = pybel.readstring("pdb", ligand_block).write("sdf")
            return Chem.MolFromMolBlock(sdf, removeHs=True)
        mol = Chem.MolFromPDBBlock(ligand_block, removeHs=True, sanitize=False)
        if mol is not None:
            try:
                Chem.SanitizeMol(mol)
            except Exception:
                pass  # keep unsanitized; atom matching may still work
        return mol
    except Exception as exc:
        logger.debug("Experimental pose parse failed: %s", exc)
        return None


def parse_pose_mol(text: str):
    """A docked pose (SDF molblock or first-model PDB text) as an RDKit mol.

    ``run_vina_docking`` returns an SDF when obabel converted the PDBQT and
    plain PDB text otherwise — both must work.
    """
    if not text or Chem is None:
        return None
    try:
        head = text.lstrip()[:6]
        if head.startswith(("ATOM", "HETATM")):
            mol = Chem.MolFromPDBBlock(text, removeHs=True, sanitize=False)
            if mol is not None:
                try:
                    Chem.SanitizeMol(mol)
                except Exception:
                    pass  # keep the unsanitized mol; matching may still work
            return mol
        return Chem.MolFromMolBlock(text, removeHs=True)
    except Exception as exc:
        logger.debug("Docked pose parse failed: %s", exc)
        return None


def pose_rmsd(docked_mol, experimental_mol) -> dict:
    """Symmetry-corrected, in-frame heavy-atom RMSD between the two poses.

    CalcRMS is used without an atom map: it matches atom order itself and
    applies symmetry correction (empirically verified — a shuffled atom
    ordering returns the identical value, and a translated pose returns the
    translation, i.e. no superposition is performed).
    """
    if Chem is None:
        return {"reason": f"RDKit unavailable: {_RDKIT_IMPORT_ERROR}"}
    # Imported here (function scope) like every other rdkit use in this repo.
    from rdkit.Chem import rdMolAlign
    if docked_mol is None or experimental_mol is None:
        return {"reason": "One of the two poses could not be parsed into a "
                          "molecule for RMSD comparison."}
    if docked_mol.GetNumAtoms() != experimental_mol.GetNumAtoms():
        return {"reason": (
            f"The re-docked ligand has {docked_mol.GetNumAtoms()} heavy atoms "
            f"but the crystal ligand has {experimental_mol.GetNumAtoms()} — "
            "the docking preparation changed the molecule, so RMSD is not "
            "comparable.")}
    try:
        rmsd = float(rdMolAlign.CalcRMS(docked_mol, experimental_mol))
    except Exception as exc:
        return {"reason": f"RMSD could not be computed (the two poses do not "
                          f"share a matching atom graph): {exc}"}
    if rmsd != rmsd:  # NaN
        return {"reason": "RMSD computation returned a non-finite value."}
    return {"rmsd": round(rmsd, 2)}


def _verdict(rmsd: float) -> tuple[str, str]:
    if rmsd < GOOD_RMSD:
        return ("good", "Reproduces the crystal pose")
    if rmsd < FAIR_RMSD:
        return ("fair", "Partly reproduces the crystal pose")
    return ("poor", "Does not reproduce the crystal pose")


# ── Main entry points ──────────────────────────────────────────────────────

async def validate_redocking(pdb_text: str, resname: str | None = None,
                             chain: str | None = None, box: dict | None = None,
                             exhaustiveness: int = 8) -> dict:
    """Redock the co-crystal ligand and report its RMSD vs the crystal pose.

    Never raises; always returns a dict with ``available``.
    """
    if _ENGINE_IMPORT_ERROR:
        return _unavailable(f"Docking engine unavailable: {_ENGINE_IMPORT_ERROR}")
    if pybel is None:
        return _unavailable(
            f"OpenBabel is unavailable on this server: {_PYBEL_IMPORT_ERROR}")
    if Chem is None:
        return _unavailable(f"RDKit is unavailable: {_RDKIT_IMPORT_ERROR}")

    lig = find_bound_ligand(pdb_text, resname=resname, chain=chain)
    if not lig:
        return _unavailable(
            "No bound ligand found in that structure — redocking validation "
            "needs a co-crystal ligand (water, buffers and ions don't count).")

    smiles = perceive_smiles(lig["block"])
    if not smiles:
        return _unavailable(
            "The bond structure of the co-crystal ligand could not be "
            "perceived from the PDB records, so it cannot be re-docked.")
    exp_mol = experimental_pose_mol(lig["block"])
    if exp_mol is None:
        return _unavailable(
            "The experimental pose of the co-crystal ligand could not be "
            "parsed for RMSD comparison.")

    # Receptor: the SAME preparation production runs use (waters/ions/
    # non-cofactor HETATM removed). Warn-allow, mirroring the pipeline's
    # _prepare_upload — a preparation failure falls back to the raw text
    # and is reported, never fatal.
    receptor_text = pdb_text
    receptor_prepared = False
    prep_error = None
    if prepare_protein is None:
        prep_error = f"preparer unavailable: {_PREP_IMPORT_ERROR}"
    else:
        try:
            report = prepare_protein(pdb_text)
            receptor_text = report.prepared_pdb or pdb_text
            receptor_prepared = bool(report.prepared_pdb)
        except Exception as exc:
            prep_error = str(exc)
            logger.warning("Redock receptor preparation failed (original "
                           "used): %s", exc)

    if box is None:
        box = box_from_bound_ligand(pdb_text, resname=lig["resname"],
                                    chain=lig["chain"])
    if not box or not box.get("center") or not box.get("size"):
        return _unavailable(
            "No search box could be derived for the co-crystal ligand.")

    try:
        exh = int(exhaustiveness)
    except (TypeError, ValueError):
        exh = 8
    exh = max(1, min(exh, MAX_EXHAUSTIVENESS))

    try:
        docked = await run_vina_docking(receptor_text, smiles,
                                        exhaustiveness=exh, box=box)
    except Exception as exc:
        msg = str(exc).strip()[:300] or "Vina failed."
        return _unavailable(f"Redocking failed: {msg}")

    docked_mol = parse_pose_mol(docked.get("structure", {}).get("ligand") or "")
    rmsd_info = pose_rmsd(docked_mol, exp_mol)
    if "rmsd" not in rmsd_info:
        return _unavailable(rmsd_info["reason"])

    rmsd = rmsd_info["rmsd"]
    verdict, label = _verdict(rmsd)
    result = {
        "available": True,
        "rmsd": rmsd,
        "verdict": verdict,
        "verdict_label": label,
        "ligand": {k: lig[k] for k in ("resname", "chain", "resnum",
                                       "heavy_atoms")},
        "smiles": smiles,
        "vina_score": docked.get("binding_affinity"),
        "box": box,
        "exhaustiveness": exh,
        "receptor_prepared": receptor_prepared,
        "note": (
            f"Re-docked {lig['resname']} {lig['chain']}:{lig['resnum']} with "
            f"the same receptor preparation and search box production runs "
            f"use (exhaustiveness {exh}). RMSD is measured in the receptor "
            f"frame — symmetry-corrected, no superposition. "
            f"Below {GOOD_RMSD:g} Å reproduces the crystal pose; "
            f"{GOOD_RMSD:g}–{FAIR_RMSD:g} Å partly; "
            f"{FAIR_RMSD:g} Å or above does not."),
    }
    if prep_error:
        result["preparation_note"] = (
            f"Receptor preparation did not run ({prep_error}); the original "
            "structure was used.")
    return result


def validate_redocking_sync(pdb_text: str, resname: str | None = None,
                            chain: str | None = None, box: dict | None = None,
                            exhaustiveness: int = 8) -> dict:
    """Blocking wrapper for Flask routes (they are sync; no loop is running).

    Defensive: if a loop IS somehow running on this thread, the coroutine is
    executed on a short-lived worker thread instead of raising.
    """
    coro = validate_redocking(pdb_text, resname=resname, chain=chain,
                              box=box, exhaustiveness=exhaustiveness)
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(asyncio.run, coro).result()

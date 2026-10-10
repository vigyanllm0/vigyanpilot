import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
import time
from typing import Any

logger = logging.getLogger(__name__)


def compute_box_center_from_pdb(pdb_string: str, default_size: float = 25.0) -> tuple[float, float, float, float, float, float]:
    """
    Whole-protein geometric-centroid search box from a PDB/PDBQT string
    (blind docking): centroid of all ATOM/HETATM heavy atoms + a box sized
    to the atom extent with 10 Å padding, clamped to [default_size, 30] Å
    per side so it stays inside Vina's volume limit (~27,000 Å³).
    Falls back to (0,0,0,30,30,30) if no coordinates parse.
    """
    xs, ys, zs = [], [], []
    for line in pdb_string.split("\n"):
        if line.startswith(("ATOM  ", "HETATM")):
            try:
                xs.append(float(line[30:38]))
                ys.append(float(line[38:46]))
                zs.append(float(line[46:54]))
            except (ValueError, IndexError):
                continue

    if not xs:
        return 0.0, 0.0, 0.0, 30.0, 30.0, 30.0

    cx, cy, cz = sum(xs) / len(xs), sum(ys) / len(ys), sum(zs) / len(zs)
    # Box is protein extent + 10 Å padding, clamped to 30 Å max
    extent_x = (max(xs) - min(xs)) + 10.0
    extent_y = (max(ys) - min(ys)) + 10.0
    extent_z = (max(zs) - min(zs)) + 10.0
    sx = max(default_size, min(extent_x, 30.0))
    sy = max(default_size, min(extent_y, 30.0))
    sz = max(default_size, min(extent_z, 30.0))
    return cx, cy, cz, sx, sy, sz


def _compute_box_center(pdb_path: str, default_size: float = 25.0) -> tuple[float, float, float, float, float, float]:
    """
    File-path wrapper around compute_box_center_from_pdb (kept for engine
    call sites that read the box from a written PDB/PDBQT file).
    """
    try:
        with open(pdb_path) as f:
            return compute_box_center_from_pdb(f.read(), default_size)
    except Exception as e:
        logger.debug("Suppressed exception: %s", e)
        return 0.0, 0.0, 0.0, 30.0, 30.0, 30.0


def box_from_residues(pdb_string: str, chain: str, start: int, end: int) -> dict | None:
    """
    Manual-override box spanning the atoms of residues `start`..`end` in
    `chain` (advanced-panel residue-range mode). Center = atom centroid of
    the selection; size = selection extent + 10 Å padding per side, clamped
    to [12, 30] Å (Vina volume limit). Returns None when no atom matches so
    the caller can fall back to automatic box selection.
    """
    xs, ys, zs = [], [], []
    chain = (chain or "").strip()[:1]
    for line in pdb_string.split("\n"):
        if not line.startswith(("ATOM  ", "HETATM")) or len(line) < 54:
            continue
        if chain and (line[21] if line[21].strip() else "A") != chain:
            continue
        try:
            resnum = int(line[22:26])
        except ValueError:
            continue
        if not (start <= resnum <= end):
            continue
        try:
            xs.append(float(line[30:38]))
            ys.append(float(line[38:46]))
            zs.append(float(line[46:54]))
        except (ValueError, IndexError):
            continue

    if not xs:
        return None

    cx, cy, cz = sum(xs) / len(xs), sum(ys) / len(ys), sum(zs) / len(zs)
    sx = max(12.0, min((max(xs) - min(xs)) + 10.0, 30.0))
    sy = max(12.0, min((max(ys) - min(ys)) + 10.0, 30.0))
    sz = max(12.0, min((max(zs) - min(zs)) + 10.0, 30.0))
    return {
        "center": [round(cx, 3), round(cy, 3), round(cz, 3)],
        "size": [round(sx, 1), round(sy, 1), round(sz, 1)],
        "source": "residue_range",
        "residues": {"chain": chain or "A", "start": int(start), "end": int(end)},
    }


def _mol_from_pdb(receptor_pdb: str):
    """Parse a (possibly imperfect) PDB block into an RDKit mol.

    Predicted structures (ESMFold/AlphaFold) and some uploaded PDBs contain
    pairs of atoms from *different* residues closer than a covalent bond
    (side-chain clashes in low-confidence loops, e.g. an Asp OD1 sitting
    1.5 A from a Ser OG). RDKit's proximity bonding then creates an
    impossible bond and sanitization raises, which used to abort the whole
    docking job. We re-parse without sanitization and drop ONLY such
    inter-residue non-backbone bonds (peptide C-N and disulfide SG-SG are
    kept). Dropping a bond does not move any atom, so Vina's geometry — and
    the coordinates the 3D viewer renders — stay exact.
    Returns an RDKit Mol, or None if the block is unparsable/unfixable.
    """
    from rdkit import Chem
    mol = Chem.MolFromPDBBlock(receptor_pdb, removeHs=False)
    if mol is not None:
        return mol
    mol = Chem.MolFromPDBBlock(receptor_pdb, removeHs=False, sanitize=False)
    if mol is None:
        return None
    rw = Chem.RWMol(mol)
    to_remove = []
    for bond in rw.GetBonds():
        a1, a2 = bond.GetBeginAtom(), bond.GetEndAtom()
        i1, i2 = a1.GetPDBResidueInfo(), a2.GetPDBResidueInfo()
        if i1 is None or i2 is None:
            continue
        same_res = (i1.GetChainId() == i2.GetChainId()
                    and i1.GetResidueNumber() == i2.GetResidueNumber()
                    and i1.GetResidueName() == i2.GetResidueName())
        if same_res:
            continue
        names = {i1.GetName().strip(), i2.GetName().strip()}
        if names == {"C", "N"} or names == {"SG", "SG"}:
            continue  # legitimate peptide bond / disulfide
        to_remove.append((a1.GetIdx(), a2.GetIdx()))
    for idx1, idx2 in to_remove:
        rw.RemoveBond(idx1, idx2)
    if to_remove:
        logger.warning("PDB parse: dropped %d spurious inter-residue clash bond(s) from proximity bonding",
                       len(to_remove))
    mol = rw.GetMol()
    try:
        Chem.SanitizeMol(mol)
    except Exception as e:
        logger.error("PDB parse: sanitize still failing after clash-bond cleanup: %s", e)
        return None
    return mol


def pdb_to_pdbqt(receptor_pdb: str, output_path: str) -> bool:
    """Convert receptor PDB to PDBQT format (once, cached for reuse)."""
    # Write PDB to temp file first, then convert with obabel
    _tmp_pdb = output_path.replace(".pdbqt", ".pdb")
    with open(_tmp_pdb, "w") as f:
        f.write(receptor_pdb)
    if shutil.which("obabel"):
        try:
            subprocess.run(["obabel", _tmp_pdb, "-O", output_path, "-xr"],
                           check=True, capture_output=True, timeout=60)
            return True
        except Exception as e:
            logger.debug("Suppressed exception: %s", e)
    from meeko import MoleculePreparation
    from rdkit import Chem
    mol = _mol_from_pdb(receptor_pdb)
    if mol:
        frags = Chem.GetMolFrags(mol, asMols=True)
        if frags:
            mol = max(frags, key=lambda m: m.GetNumAtoms())
        mol = Chem.AddHs(mol, addCoords=True)
        prep = MoleculePreparation()
        prep.prepare(mol)
        prep.write_pdbqt_file(output_path)
        allowed_tags = ("ATOM", "HETATM")
        with open(output_path) as f:
            content = f.read()
        with open(output_path, "w", newline="\n") as f:
            for line in content.splitlines():
                clean = line.strip()
                if clean and clean.startswith(allowed_tags):
                    f.write(clean + "\n")
        return True
    logger.error("Failed to convert receptor PDB to PDBQT")
    return False


async def run_vina_docking(receptor_pdb: str, ligand_smiles: str, exhaustiveness: int = 8, receptor_pdbqt_path: str = None, cpu: int = None, box: dict = None) -> dict[str, Any]:
    """
    Runs AutoDock Vina physics engine locally.

    If receptor_pdbqt_path is provided, skips receptor PDB→PDBQT conversion.
    cpu: threads for this Vina process (None = vina auto-detects all cores).
         The consensus pipeline passes cores//N when running N ligands in
         parallel so concurrent searches don't oversubscribe the box.
    box: optional explicit search box {"center": [x,y,z], "size": [sx,sy,sz],
         "source": ...} (pocket-detected / manual / residue-range from the
         pipeline). None = blind docking on the whole-protein centroid.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        receptor_pdb_path = os.path.join(temp_dir, "receptor.pdb")
        if receptor_pdbqt_path:
            local_receptor_pdbqt = receptor_pdbqt_path
        else:
            local_receptor_pdbqt = os.path.join(temp_dir, "receptor.pdbqt")
        ligand_smi_path = os.path.join(temp_dir, "ligand.smi")
        ligand_pdbqt_path = os.path.join(temp_dir, "ligand.pdbqt")
        out_pdbqt_path = os.path.join(temp_dir, "out.pdbqt")

        with open(receptor_pdb_path, "w") as f: f.write(receptor_pdb)
        with open(ligand_smi_path, "w") as f: f.write(ligand_smiles)

        if not receptor_pdbqt_path:
            pdb_to_pdbqt(receptor_pdb, local_receptor_pdbqt)

        # 3. Convert Ligand SMILES to 3D PDBQT
        if shutil.which("obabel"):
            try:
                subprocess.run(["obabel", ligand_smi_path, "-O", ligand_pdbqt_path, "--gen3d", "-p", "7.4"], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                from meeko import MoleculePreparation
                from rdkit import Chem
                from rdkit.Chem import AllChem
                mol = Chem.MolFromSmiles(ligand_smiles); mol = Chem.AddHs(mol); AllChem.EmbedMolecule(mol, AllChem.ETKDG())
                prep = MoleculePreparation(); prep.prepare(mol); prep.write_pdbqt_file(ligand_pdbqt_path)

                # Clean PDBQT for FLEXIBLE LIGAND (ROOT/BRANCH allowed)
                allowed_tags = ("ATOM", "HETATM", "TER", "REMARK", "ROOT", "ENDROOT", "BRANCH", "ENDBRANCH", "TORSDOF", "MODEL", "ENDMDL", "END")
                with open(ligand_pdbqt_path) as f: lines = f.readlines()
                with open(ligand_pdbqt_path, "w", newline="\n") as f:
                    for i, line in enumerate(lines):
                        clean_line = line.strip()
                        if not clean_line: continue
                        if clean_line.startswith(allowed_tags):
                            f.write(clean_line + "\n")
        else:
            from meeko import MoleculePreparation
            from rdkit import Chem
            from rdkit.Chem import AllChem
            mol = Chem.MolFromSmiles(ligand_smiles); mol = Chem.AddHs(mol); AllChem.EmbedMolecule(mol, AllChem.ETKDG())
            prep = MoleculePreparation(); prep.prepare(mol); prep.write_pdbqt_file(ligand_pdbqt_path)

            # Clean PDBQT for FLEXIBLE LIGAND
            allowed_tags = ("ATOM", "HETATM", "TER", "REMARK", "ROOT", "ENDROOT", "BRANCH", "ENDBRANCH", "TORSDOF", "MODEL", "ENDMDL", "END")
            with open(ligand_pdbqt_path) as f: lines = f.readlines()
            with open(ligand_pdbqt_path, "w", newline="\n") as f:
                for i, line in enumerate(lines):
                    clean_line = line.strip()
                    if not clean_line: continue
                    if clean_line.startswith(allowed_tags):
                        f.write(clean_line + "\n")

        # 4. Run Vina
        start_time = time.time()
        try:
            vina_bin = shutil.which("vina") or "vina"

            # Search box: an explicit box from the pipeline (pocket-detected,
            # manual override, or residue range) wins; otherwise fall back to
            # the whole-protein geometric centroid (blind docking).
            if box and box.get("center") and box.get("size"):
                cx, cy, cz = (float(v) for v in box["center"])
                sx, sy, sz = (float(v) for v in box["size"])
                box_out = dict(box)
                box_out["center"] = [round(cx, 3), round(cy, 3), round(cz, 3)]
                box_out["size"] = [round(sx, 1), round(sy, 1), round(sz, 1)]
            else:
                cx, cy, cz, sx, sy, sz = _compute_box_center(local_receptor_pdbqt)
                box_out = {
                    "center": [round(cx, 3), round(cy, 3), round(cz, 3)],
                    "size": [round(sx, 1), round(sy, 1), round(sz, 1)],
                    "source": "protein_centroid",
                }
            logger.info("Search box center: (%.2f, %.2f, %.2f), size: (%.1f, %.1f, %.1f) [source=%s]",
                        cx, cy, cz, sx, sy, sz, box_out.get("source", "?"))

            vina_cmd = [
                vina_bin, "--receptor", local_receptor_pdbqt, "--ligand", ligand_pdbqt_path,
                "--center_x", str(round(cx, 3)), "--center_y", str(round(cy, 3)), "--center_z", str(round(cz, 3)),
                "--size_x", str(round(sx, 1)), "--size_y", str(round(sy, 1)), "--size_z", str(round(sz, 1)),
                "--exhaustiveness", str(exhaustiveness), "--out", out_pdbqt_path
            ]
            if cpu:
                vina_cmd += ["--cpu", str(int(cpu))]

            # Redirect stdout/stderr to files instead of PIPE to avoid pipe-buffer
            # deadlock when multiple Vina processes run concurrently on low-core
            # machines (the progress-bar output fills the 64KB pipe buffer and Vina
            # blocks on write while the event loop is starved of CPU).
            vina_stdout = os.path.join(temp_dir, "vina_stdout.txt")
            vina_stderr = os.path.join(temp_dir, "vina_stderr.txt")
            with open(vina_stdout, "w") as out_f, open(vina_stderr, "w") as err_f:
                process = await asyncio.create_subprocess_exec(
                    *vina_cmd, stdout=out_f, stderr=err_f
                )
                try:
                    await asyncio.wait_for(process.wait(), timeout=600)
                except asyncio.TimeoutError:
                    process.kill()
                    raise Exception(f"Vina timeout after 600s: ligand {ligand_smiles[:40]}")

            if process.returncode != 0:
                with open(vina_stderr) as f:
                    err_msg = f.read().strip()
                with open(vina_stdout) as f:
                    out_msg = f.read().strip()
                logger.error("Vina failed with code %s: %s", process.returncode, err_msg or out_msg[:200])
                raise Exception(f"Vina failed: {err_msg or out_msg[:200]}")

            elapsed = time.time() - start_time

            # Parse scores from output PDBQT file (REMARK VINA RESULT lines).
            # The stdout table is also available in vina_stdout if needed.
            best_score = None
            poses_count = 0
            with open(out_pdbqt_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("REMARK VINA RESULT:"):
                        poses_count += 1
                        parts = line.split()
                        if len(parts) >= 4:
                            try:
                                score_val = float(parts[3])
                                if best_score is None or score_val < best_score:
                                    best_score = score_val
                            except ValueError:
                                pass

            if best_score is None:
                raise Exception("Failed to parse Vina score from output PDBQT.")

            with open(receptor_pdb_path) as f:
                receptor_data = f.read()

            # Convert Vina's PDBQT output to SDF for 3D viewer (3Dmol.js)
            # The frontend passes 'sdf' format to addModel().
            ligand_view = None
            if shutil.which("obabel"):
                sdf_path = os.path.join(temp_dir, "ligand_view.sdf")
                try:
                    subprocess.run(
                        ["obabel", out_pdbqt_path, "-O", sdf_path],
                        check=True, capture_output=True, timeout=30
                    )
                    with open(sdf_path) as f:
                        ligand_view = f.read()
                except Exception as e:
                    logger.debug("PDBQT-to-SDF conversion failed: %s", e)
            if not ligand_view:
                # Fallback: extract ATOM/HETATM from Vina's PDBQT as plain PDB.
                # Vina writes ONE MODEL per pose (model 1 = best) — take only
                # the first model. Concatenating every model's ATOM lines (what
                # this used to do) handed 3Dmol ~9 overlapping copies of the
                # ligand as a single structure → garbled render.
                try:
                    with open(out_pdbqt_path) as f:
                        raw = f.read()
                    clean = []
                    for line in raw.splitlines():
                        if line.startswith(("MODEL", "ENDMDL")) and clean:
                            break  # first model complete (model 1 = best pose)
                        if line.startswith(("ATOM", "HETATM")):
                            clean.append(line[:66])
                    if clean:
                        ligand_view = "\n".join(clean) + "\n"
                        logger.debug("Using stripped-PDB fallback for ligand viewer (best pose only)")
                except Exception as e:
                    logger.debug("PDB fallback failed: %s", e)
            if not ligand_view:
                with open(out_pdbqt_path) as f:
                    ligand_view = f.read()

            return {
                "binding_affinity": best_score,
                "poses": poses_count or 9,
                "computation_time": f"{elapsed:.1f}s",
                "confidence": max(0, min(100, int(50 + abs(best_score) * 5))),
                "status": "success",
                "message": f"Vina docking successful: {best_score} kcal/mol",
                "box": box_out,
                "structure": {
                    "ligand": ligand_view,
                    "receptor": receptor_data
                }
            }
        except Exception as e:
            logger.error("Vina Error: %s", str(e))
            raise e


def _parse_gnina_stdout(text: str) -> dict[str, Any]:
    """Parse GNINA's stdout results table.

    Verified empirically against the official CPU binary (v1.1, run 2026-10-08)
    and against gninasrc/main/main.cpp for both v1.1 and master — the table is:

        mode |  affinity  |  intramol  |    CNN     |   CNN
             | (kcal/mol) | (kcal/mol) | pose score | affinity
        -----+------------+------------+------------+----------
        1       -3.16       -0.58       0.8300      3.282

    i.e. exactly 5 whitespace-separated numbers per data row:
        [mode, vina_affinity, intramol_energy, CNNscore, CNNaffinity]

    CNNscore = pose confidence (0-1); CNNaffinity = predicted binding
    affinity in log mol/L units (the "real DL affinity"). Rows are printed
    in rank order (mode 1 = recommended pose).

    (The pre-2026-10-08 parser required >=6 fields, so it never matched a
    single row of this 5-column table and raised "Failed to parse GNINA
    output table"; it also would have mislabelled CNNscore as cnn_affinity.)

    Raises ValueError when the output contains no parseable table row.
    """
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 5 or not parts[0].isdigit() or int(parts[0]) < 1:
            continue  # banner/progress/header lines never start with a mode number
        try:
            vals = [float(p) for p in parts[1:5]]
        except ValueError:
            continue
        if any(v != v or v in (float("inf"), float("-inf")) for v in vals):
            continue
        rows.append({
            "mode": int(parts[0]),
            "affinity": vals[0],
            "intramol": vals[1],
            "cnn_score": vals[2],
            "cnn_affinity": vals[3],
        })
    if not rows:
        raise ValueError("no GNINA results table found in gnina stdout")
    return {
        "affinity": rows[0]["affinity"],
        "intramol": rows[0]["intramol"],
        "cnn_score": rows[0]["cnn_score"],
        "cnn_affinity": rows[0]["cnn_affinity"],
        "poses": len(rows),
        "table": rows,
    }


def _lift_address_space_limit() -> tuple[int, int] | None:
    """Raise RLIMIT_AS soft to the hard limit (returns the previous values).

    The standalone docking worker caps its OWN python at 600MB soft so
    runaway allocations raise a catchable MemoryError instead of SIGKILL.
    Children inherit that soft limit — GNINA's CNN (grids + net, ~1-3GB)
    would die under it. Hard is left unlimited by the worker, so an
    unprivileged raise is allowed; restoring in `finally` keeps the guard
    for everything else. No-op (returns None) when no cap is set.
    """
    try:
        import resource
        prev = resource.getrlimit(resource.RLIMIT_AS)
        if prev[0] != prev[1]:
            resource.setrlimit(resource.RLIMIT_AS, (prev[1], prev[1]))
        return prev
    except Exception:
        return None


def _restore_address_space_limit(prev: tuple[int, int] | None) -> None:
    if prev is None:
        return
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS, prev)
    except Exception:
        pass


def _resolve_gnina_bin() -> str:
    """Project-local binary wins (fresh checkout/CI), else PATH lookup."""
    project_bin = os.path.join(os.path.dirname(__file__), "bin")
    gnina_bin = os.path.join(project_bin, "gnina")
    return gnina_bin if os.path.exists(gnina_bin) else "gnina"


def binary_spawn_error(e: BaseException) -> bool:
    """True when GNINA itself can't run (missing / exec-format / permission),
    as opposed to a per-ligand docking failure."""
    if isinstance(e, (FileNotFoundError, PermissionError)):
        return True
    if isinstance(e, OSError) and getattr(e, "errno", None) in (8, 13, 2):
        return True
    msg = str(e).lower()
    return ("exec format error" in msg or "permission denied" in msg
            or "no such file or directory" in msg or "not found" in msg)


def human_binary_error(e: BaseException) -> str:
    """Actionable text for binary-level failures — the raw OSError string
    ('[Errno 8] Exec format error') meant nothing to a user."""
    raw = str(e)[:300]
    errno_ = getattr(e, "errno", None)
    if isinstance(e, PermissionError) or errno_ == 13:
        return f"{raw} — GNINA binary is present but not executable (needs chmod +x)."
    msg = raw.lower()
    if "exec format" in msg or errno_ == 8:
        return (f"{raw} — GNINA binary is built for a different OS/CPU "
                "(e.g. a Linux build on macOS). Expected when running on a "
                "personal computer; the server installs the Linux CPU build at deploy.")
    if (isinstance(e, FileNotFoundError) or errno_ == 2
            or "no such file" in msg):
        return (f"{raw} — GNINA binary is not installed on this host "
                "(the server installs it at deploy).")
    return raw


# One `gnina --version` probe per process — the exact contract the prod
# deploy gate uses. A binary that EXISTS but can't execute on this host
# (Linux build on macOS, missing interpreter, lost +x) must read as NOT
# available, so the pipeline degrades to Vina-only instead of attempting
# — and failing — once per ligand.
_GNINA_PROBE_CACHE: dict[str, Any] | None = None


def gnina_available(force: bool = False, timeout: float = 30.0) -> dict[str, Any]:
    """Probe the resolved GNINA binary with `--version`.

    Returns {'ok': bool, 'path': str, 'version': str|None, 'reason': str|None}.
    'reason' is always human text (never a bare errno). The Docker-based
    macOS wrapper (Linux binary in a container) also passes this probe —
    'ok' means GNINA will actually run here, not merely that a file exists.
    """
    global _GNINA_PROBE_CACHE
    if _GNINA_PROBE_CACHE is not None and not force:
        return _GNINA_PROBE_CACHE
    path = _resolve_gnina_bin()
    result: dict[str, Any] = {"ok": False, "path": path,
                              "version": None, "reason": None}
    if shutil.which(path) is None and not os.path.exists(path):
        result["reason"] = ("GNINA binary is not installed on this host "
                            "(the server installs the Linux CPU build at deploy).")
    else:
        try:
            proc = subprocess.run([path, "--version"], capture_output=True,
                                  text=True, timeout=timeout)
            out = ((proc.stdout or "") + (proc.stderr or "")).strip()
            if proc.returncode == 0 and out:
                result["ok"] = True
                result["version"] = out.splitlines()[0][:120]
            else:
                result["reason"] = (
                    f"GNINA --version probe failed (exit {proc.returncode}): "
                    f"{out[:300] or 'no output'}")
        except OSError as e:
            result["reason"] = human_binary_error(e)
        except subprocess.TimeoutExpired:
            result["reason"] = (
                f"GNINA --version timed out after {timeout:.0f}s — the binary "
                "is present but not usable on this host.")
    _GNINA_PROBE_CACHE = result
    logger.info("GNINA availability probe: ok=%s version=%s reason=%s",
                result["ok"], result["version"], result["reason"])
    return result


async def run_gnina_docking(receptor_pdb: str, ligand_smiles: str, exhaustiveness: int = 4, receptor_pdbqt_path: str = None, box: dict = None) -> dict[str, Any]:
    """
    Runs GNINA docking (CNN-based scoring).

    box: optional explicit search box (same contract as run_vina_docking) —
         the consensus pipeline passes the SAME box it screened with in
         stage 2 so CNN re-scoring refines poses in the identical volume.
    """
    import time
    with tempfile.TemporaryDirectory() as temp_dir:
        receptor_pdb_path = os.path.join(temp_dir, "receptor.pdb")
        ligand_smi_path = os.path.join(temp_dir, "ligand.smi")
        ligand_sdf_path = os.path.join(temp_dir, "ligand.sdf")
        out_sdf_path = os.path.join(temp_dir, "out.sdf")

        with open(receptor_pdb_path, "w") as f: f.write(receptor_pdb)
        with open(ligand_smi_path, "w") as f: f.write(ligand_smiles)

        if shutil.which("obabel"):
            try:
                subprocess.run(["obabel", ligand_smi_path, "-O", ligand_sdf_path, "--gen3d", "-p", "7.4"], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                from rdkit import Chem
                from rdkit.Chem import AllChem
                mol = Chem.MolFromSmiles(ligand_smiles); mol = Chem.AddHs(mol); AllChem.EmbedMolecule(mol, AllChem.ETKDG())
                writer = Chem.SDWriter(ligand_sdf_path); writer.write(mol); writer.close()
        else:
            from rdkit import Chem
            from rdkit.Chem import AllChem
            mol = Chem.MolFromSmiles(ligand_smiles); mol = Chem.AddHs(mol); AllChem.EmbedMolecule(mol, AllChem.ETKDG())
            writer = Chem.SDWriter(ligand_sdf_path); writer.write(mol); writer.close()

        start_time = time.time()
        try:
            gnina_bin = _resolve_gnina_bin()

            # Search box: same explicit-box contract as Vina (stage-3 must
            # refine inside the exact volume stage 2 screened).
            if box and box.get("center") and box.get("size"):
                cx, cy, cz = (float(v) for v in box["center"])
                sx, sy, sz = (float(v) for v in box["size"])
                box_out = dict(box)
                box_out["center"] = [round(cx, 3), round(cy, 3), round(cz, 3)]
                box_out["size"] = [round(sx, 1), round(sy, 1), round(sz, 1)]
            else:
                cx, cy, cz, sx, sy, sz = _compute_box_center(receptor_pdb_path)
                box_out = {
                    "center": [round(cx, 3), round(cy, 3), round(cz, 3)],
                    "size": [round(sx, 1), round(sy, 1), round(sz, 1)],
                    "source": "protein_centroid",
                }
            logger.info("GNINA search box: (%.2f, %.2f, %.2f), size: (%.1f, %.1f, %.1f) [source=%s]",
                        cx, cy, cz, sx, sy, sz, box_out.get("source", "?"))

            gnina_cmd = [
                gnina_bin, "--receptor", receptor_pdb_path, "--ligand", ligand_sdf_path,
                "--center_x", str(round(cx, 3)), "--center_y", str(round(cy, 3)), "--center_z", str(round(cz, 3)),
                "--size_x", str(round(sx, 1)), "--size_y", str(round(sy, 1)), "--size_z", str(round(sz, 1)),
                "--exhaustiveness", str(exhaustiveness),
                # IMPORTANT: --cnn_scoring takes a VALUE (boost value<> enum,
                # accepted tokens: none/rescore/refinement/... verified in
                # gnina v1.1 user_opts.cpp). The old bare `--cnn_scoring
                # --out <path>` made gnina parse `--out` as the enum value →
                # "Command line parse error" → exit 1 (empirically reproduced
                # on the official v1.1 binary 2026-10-08), so GNINA never ran
                # even with a working binary. `=rescore` is unambiguous.
                #
                # --cnn: single model instead of v1.1's default 3-model
                # ensemble — measured on the official binary (same receptor +
                # ligand, x86_64 emulation): ensemble rescore 246s vs single
                # model 37s (6.6x), while search-only at exh=4 is 12s. The
                # ensemble would blow the 900s job cap at K=10; the authors'
                # own startup warning recommends the single model on CPU.
                # crossdock_default2018 is v1.1's published CrossDocked2018
                # model (token accepted by this binary — verified live).
                "--cnn_scoring=rescore", "--cnn", "crossdock_default2018",
                "--out", out_sdf_path
            ]

            # Redirect stdout/stderr to files to avoid pipe-buffer deadlock
            gnina_stdout = os.path.join(temp_dir, "gnina_stdout.txt")
            gnina_stderr = os.path.join(temp_dir, "gnina_stderr.txt")
            with open(gnina_stdout, "w") as out_f, open(gnina_stderr, "w") as err_f:
                # Lift the worker's 600MB soft guard across the fork only —
                # the child inherits the lifted limit; our process restores
                # immediately after spawn (direct exec keeps FileNotFoundError/
                # ENOEXEC semantics that the binary fail-fast relies on).
                prev_limit = _lift_address_space_limit()
                try:
                    process = await asyncio.create_subprocess_exec(
                        *gnina_cmd, stdout=out_f, stderr=err_f
                    )
                finally:
                    _restore_address_space_limit(prev_limit)
                try:
                    await asyncio.wait_for(process.wait(), timeout=600)
                except asyncio.TimeoutError:
                    process.kill()
                    raise Exception(f"GNINA timeout after 600s: ligand {ligand_smiles[:40]}")

            if process.returncode != 0:
                with open(gnina_stderr) as f:
                    err_msg = f.read().strip()
                raise Exception(f"Gnina failed: {err_msg}")

            elapsed = time.time() - start_time
            with open(gnina_stdout) as f:
                parsed = _parse_gnina_stdout(f.read())

            with open(out_sdf_path) as f:
                ligand_data = f.read()

            cnn_score = parsed["cnn_score"]
            cnn_affinity = parsed["cnn_affinity"]
            return {
                "binding_affinity": parsed["affinity"],
                # Honest field names (2026-10-08): cnn_score = pose confidence
                # 0-1 (GNINA "CNNscore"); cnn_affinity = predicted affinity in
                # log mol/L (GNINA "CNNaffinity"). The legacy `cnn_affinity`
                # key used to carry CNNscore — nothing in the UI consumed it.
                "cnn_score": cnn_score,
                "cnn_affinity": cnn_affinity,
                "intramol_energy": parsed["intramol"],
                "poses": parsed["poses"],
                "pose_table": parsed["table"],
                "computation_time": f"{elapsed:.1f}s",
                "confidence": int(round(cnn_score * 100)) if 0.0 <= cnn_score <= 1.0 else None,
                "status": "success",
                "message": (f"GNINA docking complete. CNN pose score: {cnn_score:.3f}, "
                            f"CNN affinity: {cnn_affinity:.2f} (log mol/L)."),
                "box": box_out,
                "structure": {
                    "ligand": ligand_data,
                    "receptor": receptor_pdb
                }
            }

        except Exception as e:
            logger.error("Gnina Error: %s", str(e))
            raise e

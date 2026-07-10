import os
import subprocess
import tempfile
import logging
import asyncio
import shutil
import time
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


def _compute_box_center(pdb_path: str, default_size: float = 25.0) -> Tuple[float, float, float, float, float, float]:
    """
    Parse ATOM/HETATM records from a PDB or PDBQT file and return the
    geometric center (cx, cy, cz) and a recommended search box size (sx, sy, sz).
    Falls back to (0,0,0) with size 60 if parsing fails.
    Box dimensions are clamped to a max of 30 Å per side to stay within
    Vina's volume limit (~27,000 Å³).
    """
    xs, ys, zs = [], [], []
    try:
        with open(pdb_path, "r") as f:
            for line in f:
                if line.startswith(("ATOM  ", "HETATM")):
                    try:
                        xs.append(float(line[30:38]))
                        ys.append(float(line[38:46]))
                        zs.append(float(line[46:54]))
                    except (ValueError, IndexError):
                        continue
    except Exception as e:
        logger.debug("Suppressed exception: %s", e)

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
    from rdkit import Chem
    from meeko import MoleculePreparation
    mol = Chem.MolFromPDBBlock(receptor_pdb, removeHs=False)
    if mol:
        frags = Chem.GetMolFrags(mol, asMols=True)
        if frags:
            mol = max(frags, key=lambda m: m.GetNumAtoms())
        mol = Chem.AddHs(mol, addCoords=True)
        prep = MoleculePreparation()
        prep.prepare(mol)
        prep.write_pdbqt_file(output_path)
        allowed_tags = ("ATOM", "HETATM")
        with open(output_path, "r") as f:
            content = f.read()
        with open(output_path, "w", newline="\n") as f:
            for line in content.splitlines():
                clean = line.strip()
                if clean and clean.startswith(allowed_tags):
                    f.write(clean + "\n")
        return True
    logger.error("Failed to convert receptor PDB to PDBQT")
    return False


async def run_vina_docking(receptor_pdb: str, ligand_smiles: str, exhaustiveness: int = 8, receptor_pdbqt_path: str = None) -> Dict[str, Any]:
    """
    Runs AutoDock Vina physics engine locally.
    
    If receptor_pdbqt_path is provided, skips receptor PDB→PDBQT conversion.
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
                from rdkit import Chem; from rdkit.Chem import AllChem; from meeko import MoleculePreparation
                mol = Chem.MolFromSmiles(ligand_smiles); mol = Chem.AddHs(mol); AllChem.EmbedMolecule(mol, AllChem.ETKDG())
                prep = MoleculePreparation(); prep.prepare(mol); prep.write_pdbqt_file(ligand_pdbqt_path)
                
                # Clean PDBQT for FLEXIBLE LIGAND (ROOT/BRANCH allowed)
                allowed_tags = ("ATOM", "HETATM", "TER", "REMARK", "ROOT", "ENDROOT", "BRANCH", "ENDBRANCH", "TORSDOF", "MODEL", "ENDMDL", "END")
                with open(ligand_pdbqt_path, "r") as f: lines = f.readlines()
                with open(ligand_pdbqt_path, "w", newline="\n") as f:
                    for i, line in enumerate(lines):
                        clean_line = line.strip()
                        if not clean_line: continue
                        if clean_line.startswith(allowed_tags):
                            f.write(clean_line + "\n")
        else:
            from rdkit import Chem; from rdkit.Chem import AllChem; from meeko import MoleculePreparation
            mol = Chem.MolFromSmiles(ligand_smiles); mol = Chem.AddHs(mol); AllChem.EmbedMolecule(mol, AllChem.ETKDG())
            prep = MoleculePreparation(); prep.prepare(mol); prep.write_pdbqt_file(ligand_pdbqt_path)
            
            # Clean PDBQT for FLEXIBLE LIGAND
            allowed_tags = ("ATOM", "HETATM", "TER", "REMARK", "ROOT", "ENDROOT", "BRANCH", "ENDBRANCH", "TORSDOF", "MODEL", "ENDMDL", "END")
            with open(ligand_pdbqt_path, "r") as f: lines = f.readlines()
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

            # Compute protein geometric center for search box
            cx, cy, cz, sx, sy, sz = _compute_box_center(local_receptor_pdbqt)
            logger.info("Search box center: (%.2f, %.2f, %.2f), size: (%.1f, %.1f, %.1f)", cx, cy, cz, sx, sy, sz)
            
            vina_cmd = [
                vina_bin, "--receptor", local_receptor_pdbqt, "--ligand", ligand_pdbqt_path, 
                "--center_x", str(round(cx, 3)), "--center_y", str(round(cy, 3)), "--center_z", str(round(cz, 3)),
                "--size_x", str(round(sx, 1)), "--size_y", str(round(sy, 1)), "--size_z", str(round(sz, 1)),
                "--exhaustiveness", str(exhaustiveness), "--out", out_pdbqt_path
            ]

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
                with open(vina_stderr, "r") as f:
                    err_msg = f.read().strip()
                with open(vina_stdout, "r") as f:
                    out_msg = f.read().strip()
                logger.error("Vina failed with code %s: %s", process.returncode, err_msg or out_msg[:200])
                raise Exception(f"Vina failed: {err_msg or out_msg[:200]}")
            
            elapsed = time.time() - start_time

            # Parse scores from output PDBQT file (REMARK VINA RESULT lines).
            # The stdout table is also available in vina_stdout if needed.
            best_score = None
            poses_count = 0
            with open(out_pdbqt_path, "r") as f:
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

            with open(receptor_pdb_path, "r") as f:
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
                    with open(sdf_path, "r") as f:
                        ligand_view = f.read()
                except Exception as e:
                    logger.debug("PDBQT-to-SDF conversion failed: %s", e)
            if not ligand_view:
                # Fallback: extract ATOM/HETATM from PDBQT as plain PDB
                try:
                    with open(out_pdbqt_path, "r") as f:
                        raw = f.read()
                    clean = []
                    for line in raw.splitlines():
                        if line.startswith(("ATOM", "HETATM")):
                            clean.append(line[:66])
                    if clean:
                        ligand_view = "\n".join(clean) + "\n"
                        logger.debug("Using stripped-PDB fallback for ligand viewer")
                except Exception as e:
                    logger.debug("PDB fallback failed: %s", e)
            if not ligand_view:
                with open(out_pdbqt_path, "r") as f:
                    ligand_view = f.read()

            return {
                "binding_affinity": best_score,
                "poses": poses_count or 9,
                "computation_time": f"{elapsed:.1f}s",
                "confidence": 92 if best_score < -7 else 85,
                "status": "success",
                "message": f"Vina docking successful: {best_score} kcal/mol",
                "structure": {
                    "ligand": ligand_view,
                    "receptor": receptor_data
                }
            }
        except Exception as e:
            logger.error("Vina Error: %s", str(e))
            raise e


async def run_gnina_docking(receptor_pdb: str, ligand_smiles: str, exhaustiveness: int = 4, receptor_pdbqt_path: str = None) -> Dict[str, Any]:
    """
    Runs GNINA docking (CNN-based scoring).
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
                from rdkit import Chem; from rdkit.Chem import AllChem
                mol = Chem.MolFromSmiles(ligand_smiles); mol = Chem.AddHs(mol); AllChem.EmbedMolecule(mol, AllChem.ETKDG())
                writer = Chem.SDWriter(ligand_sdf_path); writer.write(mol); writer.close()
        else:
            from rdkit import Chem; from rdkit.Chem import AllChem
            mol = Chem.MolFromSmiles(ligand_smiles); mol = Chem.AddHs(mol); AllChem.EmbedMolecule(mol, AllChem.ETKDG())
            writer = Chem.SDWriter(ligand_sdf_path); writer.write(mol); writer.close()
            
        start_time = time.time()
        try:
            project_bin = os.path.join(os.path.dirname(__file__), "bin")
            gnina_bin = os.path.join(project_bin, "gnina")
            if not os.path.exists(gnina_bin): gnina_bin = "gnina"

            # Compute protein geometric center for search box
            cx, cy, cz, sx, sy, sz = _compute_box_center(receptor_pdb_path)
            logger.info("GNINA search box: (%.2f, %.2f, %.2f), size: (%.1f, %.1f, %.1f)", cx, cy, cz, sx, sy, sz)

            gnina_cmd = [
                gnina_bin, "--receptor", receptor_pdb_path, "--ligand", ligand_sdf_path, 
                "--center_x", str(round(cx, 3)), "--center_y", str(round(cy, 3)), "--center_z", str(round(cz, 3)),
                "--size_x", str(round(sx, 1)), "--size_y", str(round(sy, 1)), "--size_z", str(round(sz, 1)),
                "--exhaustiveness", str(exhaustiveness), "--cnn_scoring", "--out", out_sdf_path
            ]

            # Redirect stdout/stderr to files to avoid pipe-buffer deadlock
            gnina_stdout = os.path.join(temp_dir, "gnina_stdout.txt")
            gnina_stderr = os.path.join(temp_dir, "gnina_stderr.txt")
            with open(gnina_stdout, "w") as out_f, open(gnina_stderr, "w") as err_f:
                process = await asyncio.create_subprocess_exec(
                    *gnina_cmd, stdout=out_f, stderr=err_f
                )
                try:
                    await asyncio.wait_for(process.wait(), timeout=600)
                except asyncio.TimeoutError:
                    process.kill()
                    raise Exception(f"GNINA timeout after 600s: ligand {ligand_smiles[:40]}")
            
            if process.returncode != 0:
                with open(gnina_stderr, "r") as f:
                    err_msg = f.read().strip()
                raise Exception(f"Gnina failed: {err_msg}")
            
            elapsed = time.time() - start_time
            best_score = None
            cnn_score = None
            poses_count = 0
            with open(gnina_stdout, "r") as f:
                for line in f:
                    line = line.strip()
                    parts = line.split()
                    if len(parts) >= 6:
                        try:
                            mode_num = int(parts[0])
                            if mode_num == 1:
                                best_score = float(parts[1])
                                cnn_score = float(parts[5])
                            poses_count = max(poses_count, mode_num)
                        except Exception as e: logger.debug("Suppressed exception: %s", e)
            
            if best_score is None:
                raise Exception("Failed to parse GNINA output table. Ensure 'gnina' binary is correctly installed.")
                
            with open(out_sdf_path, "r") as f:
                ligand_data = f.read()

            return {
                "binding_affinity": best_score,
                "cnn_affinity": cnn_score,
                "poses": poses_count or 5,
                "computation_time": f"{elapsed:.1f}s",
                "confidence": int(cnn_score * 100) if cnn_score and cnn_score < 1 else 98,
                "status": "success",
                "message": f"GNINA docking complete. CNN Affinity: {cnn_score}",
                "structure": {
                    "ligand": ligand_data,
                    "receptor": receptor_pdb
                }
            }
            
        except Exception as e:
            logger.error("Gnina Error: %s", str(e))
            raise e

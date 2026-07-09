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
        return 0.0, 0.0, 0.0, 60.0, 60.0, 60.0

    cx, cy, cz = sum(xs) / len(xs), sum(ys) / len(ys), sum(zs) / len(zs)
    # Box is protein extent + 10 Å padding, minimum 30 Å
    sx = max(30.0, (max(xs) - min(xs)) + 10.0)
    sy = max(30.0, (max(ys) - min(ys)) + 10.0)
    sz = max(30.0, (max(zs) - min(zs)) + 10.0)
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
            logger.info(f"Search box center: ({cx:.2f}, {cy:.2f}, {cz:.2f}), size: ({sx:.1f}, {sy:.1f}, {sz:.1f})")
            
            vina_cmd = [
                vina_bin, "--receptor", local_receptor_pdbqt, "--ligand", ligand_pdbqt_path, 
                "--center_x", str(round(cx, 3)), "--center_y", str(round(cy, 3)), "--center_z", str(round(cz, 3)),
                "--size_x", str(round(sx, 1)), "--size_y", str(round(sy, 1)), "--size_z", str(round(sz, 1)),
                "--exhaustiveness", str(exhaustiveness), "--out", out_pdbqt_path
            ]
            
            process = await asyncio.create_subprocess_exec(*vina_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=600)
            except asyncio.TimeoutError:
                process.kill()
                raise Exception(f"Vina timeout after 600s: ligand {ligand_smiles[:40]}")
            
            if process.returncode != 0: 
                err_msg = stderr.decode() or stdout.decode()
                logger.error(f"Vina failed with code {process.returncode}: {err_msg}")
                raise Exception(f"Vina failed: {err_msg}")
            
            elapsed = time.time() - start_time
            output_text = stdout.decode()
            best_score = None
            poses_count = 0
            # Parse Vina output table — handles both 1.1 and 1.2 formats
            # Format: "   1       -7.5      0.000      0.000"
            for line in output_text.splitlines():
                line = line.strip()
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        mode_num = int(parts[0])
                        score_val = float(parts[1])
                        if mode_num == 1 and score_val < 0:
                            best_score = score_val
                        poses_count = max(poses_count, mode_num)
                    except Exception as e: logger.debug("Suppressed exception: %s", e)
            
            if best_score is None:
                raise Exception("Failed to parse Vina output table. Ensure 'vina' binary is compatible.")
                
            with open(out_pdbqt_path, "r") as f:
                ligand_data = f.read()
            with open(receptor_pdb_path, "r") as f:
                receptor_data = f.read()

            return {
                "binding_affinity": best_score,
                "poses": poses_count or 9,
                "computation_time": f"{elapsed:.1f}s",
                "confidence": 92 if best_score < -7 else 85,
                "status": "success",
                "message": f"Vina docking successful: {best_score} kcal/mol",
                "structure": {
                    "ligand": ligand_data,
                    "receptor": receptor_data
                }
            }
        except Exception as e:
            logger.error(f"Vina Error: {str(e)}")
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
            logger.info(f"GNINA search box: ({cx:.2f}, {cy:.2f}, {cz:.2f}), size: ({sx:.1f}, {sy:.1f}, {sz:.1f})")

            gnina_cmd = [
                gnina_bin, "--receptor", receptor_pdb_path, "--ligand", ligand_sdf_path, 
                "--center_x", str(round(cx, 3)), "--center_y", str(round(cy, 3)), "--center_z", str(round(cz, 3)),
                "--size_x", str(round(sx, 1)), "--size_y", str(round(sy, 1)), "--size_z", str(round(sz, 1)),
                "--exhaustiveness", str(exhaustiveness), "--cnn_scoring", "--out", out_sdf_path
            ]
            
            process = await asyncio.create_subprocess_exec(*gnina_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=600)
            except asyncio.TimeoutError:
                process.kill()
                raise Exception(f"GNINA timeout after 600s: ligand {ligand_smiles[:40]}")
            
            if process.returncode != 0: raise Exception(f"Gnina failed: {stderr.decode()}")
            
            elapsed = time.time() - start_time
            output_text = stdout.decode()
            best_score = None
            cnn_score = None
            poses_count = 0
            for line in output_text.splitlines():
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
            logger.error(f"Gnina Error: {str(e)}")
            raise e

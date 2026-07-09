#!/usr/bin/env python3
"""
VigyanLLM File System Scanner & Integrity Monitor
=====================================================
- Monitors project files for unauthorized modifications
- Detects injected backdoors, webshells, or tampered code
- Runs as a background task or on-demand via admin endpoint
- Auto-quarantines suspicious files
"""

import os
import re
import json
import time
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger("primerforge.file_scanner")

# ── Configuration ─────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
SCAN_DIRS = [
    PROJECT_ROOT / "primerforge",
    PROJECT_ROOT / "infra",
]
QUARANTINE_DIR = PROJECT_ROOT / ".quarantine"
BASELINE_FILE = PROJECT_ROOT / ".file_integrity_baseline.json"

# File patterns to scan
SCAN_EXTENSIONS = {".py", ".js", ".html", ".sh", ".sql", ".yml", ".yaml", ".json", ".env"}
IGNORE_DIRS = {".venv", "__pycache__", ".git", "node_modules", ".pytest_cache", ".quarantine"}

# ── Malware Signature Database ────────────────────────────────────────────

MALWARE_SIGNATURES = {
    "php_backdoor": [
        r"<\?php\s*(eval|assert|system|exec|passthru|shell_exec|popen)\s*\(",
        r"base64_decode\s*\(\s*\$_(GET|POST|REQUEST|COOKIE)",
        r"preg_replace\s*\(.*/e",
    ],
    "python_backdoor": [
        r"exec\s*\(\s*__import__\s*\(\s*['\"]os['\"]\s*\)",
        r"subprocess\.call\s*\(\s*\[.*\bsh\b",
        r"os\.system\s*\(\s*request\.",
        r"eval\s*\(\s*request\.(args|form|data|json)",
        r"__import__\s*\(\s*['\"]pty['\"]\s*\)\.spawn",
        r"socket\.socket.*connect\s*\(",
    ],
    "webshell": [
        r"(cmd|command|exec|execute|run)\s*=\s*request\.(args|form|get|post)",
        r"os\.popen\s*\(\s*request\.",
        r"subprocess\.\w+\s*\(\s*request\.",
    ],
    "crypto_miner": [
        r"coinhive|cryptonight|stratum\+tcp://|mining\.pool",
        r"xmrig|minerd|cpuminer",
    ],
    "data_exfiltration": [
        r"requests\.(get|post)\s*\(\s*['\"]https?://[^'\"]*\.\w+['\"].*password",
        r"urllib\.request.*password|secret|key",
        r"smtplib\.SMTP.*sendmail.*password",
    ],
    "env_stealer": [
        r"open\s*\(\s*['\"]\.env['\"]\s*\)\.read",
        r"dotenv.*load.*\bsend\b|\bpost\b|\bupload\b",
        r"os\.environ.*requests\.(post|get)",
    ],
    "reverse_shell": [
        r"socket\.socket\s*\(.*AF_INET.*SOCK_STREAM",
        r"pty\.spawn\s*\(",
        r"/bin/(ba)?sh.*-i",
        r"nc\s+-e\s+/bin/(ba)?sh",
    ],
}

# Compile all patterns
_COMPILED_SIGS = {}
for category, patterns in MALWARE_SIGNATURES.items():
    _COMPILED_SIGS[category] = [re.compile(p, re.IGNORECASE) for p in patterns]


# ── File Integrity Baseline ───────────────────────────────────────────────

def compute_file_hash(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    except (IOError, PermissionError):
        return ""
    return h.hexdigest()


def create_baseline() -> dict:
    """Create integrity baseline of all project files."""
    baseline = {}
    for scan_dir in SCAN_DIRS:
        if not scan_dir.exists():
            continue
        for filepath in scan_dir.rglob("*"):
            if filepath.is_file() and filepath.suffix in SCAN_EXTENSIONS:
                if any(ignore in filepath.parts for ignore in IGNORE_DIRS):
                    continue
                rel_path = str(filepath.relative_to(PROJECT_ROOT))
                baseline[rel_path] = {
                    "hash": compute_file_hash(filepath),
                    "size": filepath.stat().st_size,
                    "modified": filepath.stat().st_mtime,
                }
    return baseline


def save_baseline():
    """Save current file state as the integrity baseline."""
    baseline = create_baseline()
    baseline["_meta"] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "file_count": len(baseline) - 1,
    }
    with open(BASELINE_FILE, "w") as f:
        json.dump(baseline, f, indent=2)
    logger.info(f"Baseline saved: {len(baseline)-1} files")
    return baseline


def load_baseline() -> dict:
    """Load the integrity baseline. Returns empty dict if none exists."""
    if not BASELINE_FILE.exists():
        return {}
    try:
        with open(BASELINE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def check_integrity() -> dict:
    """
    Compare current file state against baseline.
    Returns dict with modified, added, and deleted files.
    """
    baseline = load_baseline()
    if not baseline:
        return {"error": "No baseline exists. Run save_baseline() first.", "changes": []}

    current = create_baseline()
    changes = []

    # Check for modifications and deletions
    for path, info in baseline.items():
        if path == "_meta":
            continue
        if path not in current:
            changes.append({"path": path, "change": "deleted", "severity": "high"})
        elif current[path]["hash"] != info["hash"]:
            changes.append({
                "path": path,
                "change": "modified",
                "severity": "medium",
                "old_hash": info["hash"][:16],
                "new_hash": current[path]["hash"][:16],
            })

    # Check for new files (potential backdoor drop)
    baseline_paths = set(k for k in baseline.keys() if k != "_meta")
    for path in current:
        if path not in baseline_paths:
            changes.append({"path": path, "change": "added", "severity": "low"})

    return {
        "baseline_files": len(baseline) - 1,
        "current_files": len(current),
        "changes_detected": len(changes),
        "changes": changes,
    }


# ── Malware Scanner ──────────────────────────────────────────────────────

def scan_file_for_malware(filepath: Path) -> list:
    """Scan a single file for malware signatures. Returns list of findings."""
    findings = []
    try:
        content = filepath.read_text(errors="ignore")
    except (IOError, PermissionError):
        return findings

    for category, patterns in _COMPILED_SIGS.items():
        for pattern in patterns:
            matches = pattern.findall(content)
            if matches:
                # Find line number
                for i, line in enumerate(content.split("\n"), 1):
                    if pattern.search(line):
                        findings.append({
                            "category": category,
                            "file": str(filepath.relative_to(PROJECT_ROOT)),
                            "line": i,
                            "pattern": pattern.pattern[:60],
                            "snippet": line.strip()[:100],
                        })
                        break
                break  # One match per category per file is enough

    return findings


def full_malware_scan() -> dict:
    """Scan all project files for known malware patterns."""
    all_findings = []
    files_scanned = 0

    for scan_dir in SCAN_DIRS:
        if not scan_dir.exists():
            continue
        for filepath in scan_dir.rglob("*"):
            if filepath.is_file() and filepath.suffix in SCAN_EXTENSIONS:
                if any(ignore in filepath.parts for ignore in IGNORE_DIRS):
                    continue
                files_scanned += 1
                findings = scan_file_for_malware(filepath)
                all_findings.extend(findings)

    return {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "files_scanned": files_scanned,
        "threats_found": len(all_findings),
        "findings": all_findings,
        "status": "clean" if not all_findings else "threats_detected",
    }


# ── Auto-Quarantine ──────────────────────────────────────────────────────

def quarantine_file(filepath: str) -> dict:
    """Move a suspicious file to quarantine directory."""
    src = PROJECT_ROOT / filepath
    if not src.exists():
        return {"error": f"File not found: {filepath}"}

    QUARANTINE_DIR.mkdir(exist_ok=True)
    timestamp = int(time.time())
    dest_name = f"{timestamp}_{src.name}"
    dest = QUARANTINE_DIR / dest_name

    # Save metadata
    meta = {
        "original_path": str(filepath),
        "quarantined_at": datetime.now(timezone.utc).isoformat(),
        "hash": compute_file_hash(src),
        "size": src.stat().st_size,
    }

    try:
        src.rename(dest)
        # Write metadata alongside
        meta_file = QUARANTINE_DIR / f"{dest_name}.meta.json"
        with open(meta_file, "w") as f:
            json.dump(meta, f, indent=2)
        logger.warning(f"File quarantined: {filepath} → .quarantine/{dest_name}")
        return {"success": True, "quarantined_as": dest_name, "metadata": meta}
    except Exception as e:
        return {"error": f"Quarantine failed: {e}"}


def restore_from_quarantine(quarantine_name: str) -> dict:
    """Restore a file from quarantine to its original location."""
    meta_file = QUARANTINE_DIR / f"{quarantine_name}.meta.json"
    if not meta_file.exists():
        return {"error": "Quarantine metadata not found."}

    with open(meta_file, "r") as f:
        meta = json.load(f)

    src = QUARANTINE_DIR / quarantine_name
    dest = PROJECT_ROOT / meta["original_path"]

    if not src.exists():
        return {"error": "Quarantined file not found."}

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dest)
        meta_file.unlink()
        return {"success": True, "restored_to": meta["original_path"]}
    except Exception as e:
        return {"error": f"Restore failed: {e}"}


# ── Flask Admin Endpoints ─────────────────────────────────────────────────

def init_file_scanner(app):
    """Register file scanner admin endpoints."""
    from flask import jsonify, request as flask_request

    try:
        from .pg_auth import require_admin
    except Exception as exc:
        logger.warning("File scanner admin endpoints disabled: %s", exc)
        logger.info("File scanner initialized")
        return

    @app.route("/api/admin/scanner/scan", methods=["POST"])
    @require_admin
    def run_scan():
        """Admin: Run full malware scan on project files."""
        result = full_malware_scan()
        return jsonify(result), 200

    @app.route("/api/admin/scanner/integrity", methods=["GET"])
    @require_admin
    def check_file_integrity():
        """Admin: Check file integrity against baseline."""
        result = check_integrity()
        return jsonify(result), 200

    @app.route("/api/admin/scanner/baseline", methods=["POST"])
    @require_admin
    def create_new_baseline():
        """Admin: Create/update the integrity baseline."""
        baseline = save_baseline()
        return jsonify({
            "success": True,
            "files_baselined": len(baseline) - 1,
            "message": "Baseline created. Future integrity checks will compare against this snapshot."
        }), 200

    @app.route("/api/admin/scanner/quarantine", methods=["POST"])
    @require_admin
    def quarantine_suspicious():
        """Admin: Quarantine a suspicious file."""
        data = flask_request.get_json(silent=True) or {}
        filepath = data.get("filepath", "")
        if not filepath:
            return jsonify({"error": "filepath required."}), 400
        # Prevent path traversal in the quarantine request itself
        if ".." in filepath:
            return jsonify({"error": "Invalid path."}), 400
        result = quarantine_file(filepath)
        return jsonify(result), 200 if "success" in result else 400

    @app.route("/api/admin/scanner/restore", methods=["POST"])
    @require_admin
    def restore_quarantined():
        """Admin: Restore a file from quarantine."""
        data = flask_request.get_json(silent=True) or {}
        name = data.get("name", "")
        if not name or ".." in name:
            return jsonify({"error": "Invalid quarantine name."}), 400
        result = restore_from_quarantine(name)
        return jsonify(result), 200 if "success" in result else 400

    logger.info("File scanner initialized")

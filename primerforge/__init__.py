# VigyanLLM package
from __future__ import annotations

import os
from pathlib import Path


def _prepend_local_tool_bins() -> None:
    root = Path(__file__).resolve().parent.parent
    candidates = [
        root / "tools" / "ncbi-blast-2.17.0+" / "bin",
    ]
    current = os.environ.get("PATH", "")
    parts = current.split(os.pathsep) if current else []
    for path in candidates:
        path_str = str(path)
        if path.is_dir() and path_str not in parts:
            parts.insert(0, path_str)
    os.environ["PATH"] = os.pathsep.join(parts)


_prepend_local_tool_bins()

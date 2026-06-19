"""WSGI entry point for production gunicorn server."""
import os, sys
from pathlib import Path

# Load .env manually (avoids python-dotenv edge cases in production)
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#"):
            continue
        if "=" in _line:
            _key, _val = _line.split("=", 1)
            os.environ.setdefault(_key.strip(), _val.strip())

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from primerforge.primer_server import create_app
app = create_app()

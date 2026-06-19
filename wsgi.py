"""WSGI entry point for production gunicorn server."""
import os, sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env BEFORE any app imports so env vars are available
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
    print(f"wsgi: loaded {_env_path}", flush=True)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from primerforge.primer_server import create_app
app = create_app()

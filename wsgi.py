"""WSGI entry point for production gunicorn server."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from primerforge.primer_server import create_app
app = create_app()

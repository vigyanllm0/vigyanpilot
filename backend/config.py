import os
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

# Use SQLite for local dev, PostgreSQL for production
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./cms.db")

# ── SSL / TLS for Azure PostgreSQL ────────────────────────────────────────
# If DB_SSL_MODE is set and not already in the URL, append it as a query param.
DB_SSL_MODE = os.environ.get("DB_SSL_MODE", "").strip().lower()
if DB_SSL_MODE and DATABASE_URL.startswith("postgresql"):
    parsed = urlparse(DATABASE_URL)
    qs = parse_qs(parsed.query)
    if "sslmode" not in qs:
        qs["sslmode"] = [DB_SSL_MODE]
        new_query = urlencode(qs, doseq=True)
        DATABASE_URL = urlunparse(parsed._replace(query=new_query))

DB_CONNECT_ARGS = {}
if DB_SSL_MODE == "require":
    ca_path = os.environ.get("DB_SSL_CA_PATH")
    if ca_path:
        DB_CONNECT_ARGS["sslrootcert"] = ca_path

_jwt_secret = os.environ.get("JWT_SECRET")
if not _jwt_secret:
    raise RuntimeError(
        "JWT_SECRET environment variable is required. "
        "Generate one with: python3 -c 'import secrets; print(secrets.token_hex(32))'"
    )
JWT_SECRET = _jwt_secret
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "frontend/uploads/cms")
MAX_UPLOAD_SIZE = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}
ALLOWED_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml"}

MAIN_API_URL = os.environ.get("MAIN_API_URL", "http://13.207.60.92:5000/api")

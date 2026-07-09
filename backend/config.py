import os

# Use SQLite for local dev, PostgreSQL for production
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./cms.db")
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

DATABASE_URL = "postgresql://localhost:5432/vigyanllm_cms"
JWT_SECRET = "vp-cms-secret-key-change-in-production-2025"
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24
UPLOAD_DIR = "frontend/uploads/cms"
MAX_UPLOAD_SIZE = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}
ALLOWED_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml"}

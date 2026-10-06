import logging
import os

from database import engine
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from models import Base
from pii_mask import install_pii_mask
from routes import auth, blocks, media, notifications, pages, public, review, settings, stats, upload, users

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
install_pii_mask()

app = FastAPI(title="VigyanLLM CMS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://vigyanllm.in",
        "https://www.vigyanllm.in",
        "http://localhost:8000",
        "http://localhost:3000",
        "http://localhost:8001",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8001",
        "http://localhost:11436",
        "http://127.0.0.1:11436",
        "http://13.207.60.92:8001",
        "http://13.207.60.92:5000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    _seed_admin()

def _seed_admin():
    """Create or rotate the CMS admin from environment configuration.

    CMS_ADMIN_EMAIL / CMS_ADMIN_PASSWORD are written to .env by CI from
    GitHub secrets (same pattern as PRIMERFORGE_ADMIN_*). No credential
    lives in code: when the stored hash does not verify against the
    configured password, the hash is re-derived — changing the secret
    rotates the credential and the old password stops working. Skips
    with a warning when unset so local tooling can still boot the app.
    """
    from auth import hash_password, verify_password
    from database import SessionLocal
    from models import AdminUser

    email = os.environ.get("CMS_ADMIN_EMAIL", "").strip()
    password = os.environ.get("CMS_ADMIN_PASSWORD", "")
    if not email or not password:
        logging.warning(
            "CMS admin seeding skipped: CMS_ADMIN_EMAIL / CMS_ADMIN_PASSWORD not set"
        )
        return

    def _pw_ok(stored):
        if not stored:
            return False
        try:
            return bool(verify_password(password, stored))
        except (ValueError, TypeError):
            return False  # malformed/legacy hash → treated as mismatch, re-derived

    db = SessionLocal()
    try:
        user = db.query(AdminUser).filter(AdminUser.email == email).first()
        if user is None:
            db.add(
                AdminUser(
                    email=email,
                    password_hash=hash_password(password),
                    display_name="CMS Admin",
                    role="admin",
                )
            )
            db.commit()
            logging.info("CMS admin seeded: %s", email)
        elif not _pw_ok(user.password_hash):
            user.password_hash = hash_password(password)
            user.role = "admin"
            db.commit()
            logging.info("CMS admin credential rotated from environment: %s", email)
        elif user.role != "admin":
            user.role = "admin"
            db.commit()
    finally:
        db.close()


@app.get("/health")
def health():
    """Liveness probe for deploy gates (service binds 127.0.0.1:8001 only)."""
    return {"status": "ok", "service": "vigyan-cms"}

app.include_router(auth.router)
app.include_router(pages.router)
app.include_router(review.queue_router)
app.include_router(review.router)
app.include_router(upload.router)
app.include_router(public.router)
app.include_router(notifications.router)
app.include_router(stats.router)
app.include_router(media.router)
app.include_router(settings.router)
app.include_router(blocks.router)
app.include_router(users.router)

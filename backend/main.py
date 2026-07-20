import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine
from models import Base
from routes import auth, pages, review, upload, public, notifications, stats
from pii_mask import install_pii_mask

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
    from sqlalchemy.orm import Session
    from database import SessionLocal
    from models import AdminUser
    from auth import hash_password
    db = SessionLocal()
    try:
        existing = db.query(AdminUser).filter(AdminUser.email == "admin@vigyanllm.in").first()
        if not existing:
            import secrets
            plain = secrets.token_urlsafe(16)
            hashed = hash_password(plain)
            user = AdminUser(
                email="admin@vigyanllm.in",
                password_hash=hashed,
                display_name="Admin",
                role="admin",
            )
            db.add(user)
            db.commit()
            print(f"INITIAL CMS ADMIN PASSWORD: {plain} — Save this now. It will not be shown again.")
        else:
            pass
    finally:
        db.close()

app.include_router(auth.router)
app.include_router(pages.router)
app.include_router(review.queue_router)
app.include_router(review.router)
app.include_router(upload.router)
app.include_router(public.router)
app.include_router(notifications.router)
app.include_router(stats.router)

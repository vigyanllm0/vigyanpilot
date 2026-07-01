from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import AdminUser
from schemas import LoginRequest, LoginResponse
from auth import hash_password, verify_password, create_token
from datetime import datetime, timezone

router = APIRouter(prefix="/api/v1/cms/auth", tags=["auth"])

@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(AdminUser).filter(AdminUser.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    token, exp = create_token(user.id, user.email, user.role)
    return LoginResponse(token=token, expires_at=exp)

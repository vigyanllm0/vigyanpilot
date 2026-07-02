from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import AdminUser
from schemas import LoginRequest, LoginResponse, UserInfo
from auth import hash_password, verify_password, create_token
from datetime import datetime, timezone
import urllib.request, json

router = APIRouter(prefix="/api/v1/cms/auth", tags=["auth"])

from config import MAIN_API_URL as MAIN_API

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    if req.token:
        return _exchange_token(req.token, db)
    if not req.email or not req.password:
        raise HTTPException(status_code=400, detail="Email and password required")
    user = db.query(AdminUser).filter(AdminUser.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    token, exp = create_token(user.id, user.email, user.role)
    return LoginResponse(
        token=token,
        expires_at=exp,
        user=UserInfo(id=user.id, email=user.email, display_name=user.display_name, role=user.role),
    )

def _exchange_token(pf_token: str, db: Session):
    try:
        r = urllib.request.urlopen(
            urllib.request.Request(
                MAIN_API + "/auth/me",
                headers={"Authorization": f"Bearer {pf_token}"},
            ),
            timeout=5,
        )
        data = json.loads(r.read())
        email = data.get("email") or data.get("user", {}).get("email", "")
        role = data.get("role") or data.get("user", {}).get("role", "user")
        display_name = data.get("display_name") or data.get("user", {}).get("display_name", email.split("@")[0])
        if not email:
            raise HTTPException(status_code=401, detail="Invalid web token")
        existing = db.query(AdminUser).filter(AdminUser.email == email).first()
        if existing:
            user = existing
        else:
            cms_role = "editor" if role == "user" else "admin"
            user = AdminUser(email=email, password_hash="", display_name=display_name, role=cms_role)
            db.add(user)
            db.flush()
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()
        token, exp = create_token(user.id, user.email, user.role)
        return LoginResponse(
            token=token,
            expires_at=exp,
            user=UserInfo(id=user.id, email=user.email, display_name=user.display_name, role=user.role),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not verify web token: {str(e)}")

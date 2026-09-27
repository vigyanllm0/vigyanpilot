import json
import urllib.request
from urllib.error import URLError

from auth import decode_token
from database import get_db
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from models import AdminUser
from sqlalchemy.orm import Session

from config import MAIN_API_URL as MAIN_API

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> AdminUser:
    payload = decode_token(credentials.credentials)
    if payload:
        user = db.query(AdminUser).filter(AdminUser.id == payload["sub"]).first()
        if user:
            return user

    web_user = _validate_pf_token(credentials.credentials, db)
    if web_user:
        return web_user

    raise HTTPException(status_code=401, detail="Invalid or expired token")

def require_admin(user: AdminUser = Depends(get_current_user)) -> AdminUser:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user

def _validate_pf_token(token: str, db: Session):
    try:
        req = urllib.request.Request(  # noqa: S310
            MAIN_API + "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req, timeout=5) as r:  # noqa: S310
            data = json.loads(r.read())
        email = data.get("email") or data.get("user", {}).get("email", "")
        role = data.get("role") or data.get("user", {}).get("role", "user")
        display_name = data.get("display_name") or data.get("user", {}).get("display_name", email.split("@")[0])
        if not email:
            return None
        existing = db.query(AdminUser).filter(AdminUser.email == email).first()
        if existing:
            return existing
        cms_role = "editor" if role == "user" else "admin"
        user = AdminUser(email=email, password_hash="", display_name=display_name, role=cms_role)
        db.add(user)
        db.commit()
        return user
    except (URLError, json.JSONDecodeError):
        return None

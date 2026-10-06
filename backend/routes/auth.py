import json
import time
import urllib.request
from datetime import datetime, timezone
from urllib.error import URLError

from auth import create_token, verify_password
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, Request
from models import AdminUser
from schemas import LoginRequest, LoginResponse, UserInfo
from sqlalchemy.orm import Session

from config import MAIN_API_URL as MAIN_API

router = APIRouter(prefix="/api/v1/cms/auth", tags=["auth"])

# ── Login throttling (in-memory; uvicorn runs a single worker) ───────────────
# This endpoint becomes publicly reachable behind CloudFront once /api/v1/cms/
# is opened, so online brute force must be made expensive: consecutive failures
# lock the targeted account for a sliding window, and a looser cap limits
# cross-account password spraying from a single source.
_LOGIN_FAIL_LIMIT = 5          # failures per account key
_LOGIN_FAIL_LIMIT_IP = 20      # failures per source-IP key (spray)
_LOGIN_FAIL_WINDOW_S = 900     # sliding window: 15 minutes
_LOGIN_FAIL_MAX_KEYS = 10000   # memory cap for the dict
_login_fails: dict[str, list[float]] = {}


def _client_ip(request: Request) -> str:
    # CloudFront puts the viewer IP into X-Forwarded-For and nginx then
    # appends the edge IP ($proxy_add_x_forwarded_for), so the FIRST entry is
    # the real client. Best effort only — the per-account key is the real
    # defense (the first entry can be spoofed by the client).
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    real = request.headers.get("x-real-ip", "")
    if real:
        return real.strip()
    return request.client.host if request.client else "unknown"


def _login_gate(keys: list[str], limits: list[int]) -> None:
    now = time.monotonic()
    for key, limit in zip(keys, limits, strict=True):
        hits = [t for t in _login_fails.get(key, ()) if now - t < _LOGIN_FAIL_WINDOW_S]
        if hits:
            _login_fails[key] = hits
        if len(hits) >= limit:
            raise HTTPException(
                status_code=429,
                detail="Too many failed attempts — try again later",
            )


def _login_fail(keys: list[str]) -> None:
    now = time.monotonic()
    for key in keys:
        hits = [t for t in _login_fails.get(key, ()) if now - t < _LOGIN_FAIL_WINDOW_S]
        hits.append(now)
        if len(_login_fails) >= _LOGIN_FAIL_MAX_KEYS and key not in _login_fails:
            _login_fails.clear()  # crude cap; acceptable for a single admin panel
        _login_fails[key] = hits


def _login_ok(keys: list[str]) -> None:
    for key in keys:
        _login_fails.pop(key, None)


def _pw_ok(plain: str, stored) -> bool:
    """Constant-shape password check: None/''/malformed hashes are a miss,
    never a 500 (bcrypt raises on non-bcrypt input)."""
    if not stored:
        return False
    try:
        return bool(verify_password(plain, stored))
    except (ValueError, TypeError):
        return False


@router.post("/login")
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    if req.token:
        return _exchange_token(req.token, db)
    if not req.email or not req.password:
        raise HTTPException(status_code=400, detail="Email and password required")
    email_key = "e:" + req.email.strip().lower()
    ip_key = "i:" + _client_ip(request)
    _login_gate([email_key, ip_key], [_LOGIN_FAIL_LIMIT, _LOGIN_FAIL_LIMIT_IP])
    user = db.query(AdminUser).filter(AdminUser.email == req.email).first()
    if not user or not _pw_ok(req.password, user.password_hash):
        _login_fail([email_key, ip_key])
        raise HTTPException(status_code=401, detail="Invalid credentials")
    _login_ok([email_key, ip_key])
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
        with urllib.request.urlopen(  # noqa: S310
            urllib.request.Request(  # noqa: S310
                MAIN_API + "/auth/me",
                headers={"Authorization": f"Bearer {pf_token}"},
            ),
            timeout=5,
        ) as r:
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
    except (URLError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=502, detail=f"Could not verify web token: {e!s}")

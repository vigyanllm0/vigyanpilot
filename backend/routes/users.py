from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import AdminUser
from schemas import UserCreate, UserListItem, UserListResponse
from deps import get_current_user, require_admin
from auth import hash_password
import logging

logger = logging.getLogger("vigyanllm.cms.users")

router = APIRouter(prefix="/api/v1/cms/users", tags=["cms-users"])


def _user_to_item(user: AdminUser) -> UserListItem:
    return UserListItem(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


@router.get("", response_model=UserListResponse)
def list_users(
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_admin),
):
    users = db.query(AdminUser).order_by(AdminUser.created_at.desc()).all()
    return UserListResponse(users=[_user_to_item(u) for u in users])


@router.post("", response_model=UserListItem, status_code=201)
def create_user(
    req: UserCreate,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_admin),
):
    existing = db.query(AdminUser).filter(AdminUser.email == req.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="A user with this email already exists")

    new_user = AdminUser(
        email=req.email,
        password_hash=hash_password(req.password),
        display_name=req.display_name,
        role=req.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return _user_to_item(new_user)


@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_admin),
):
    target = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    db.delete(target)
    db.commit()
    return {"success": True}

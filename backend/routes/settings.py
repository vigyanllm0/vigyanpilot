from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import AdminUser, CMSSetting
from schemas import SettingItem, SettingUpdate, SettingListResponse
from deps import get_current_user, require_admin
import json
import logging

logger = logging.getLogger("vigyanllm.cms.settings")

router = APIRouter(prefix="/api/v1/cms/settings", tags=["cms-settings"])

SENSITIVE_KEYS = {"custom_css", "custom_js", "ga4_id"}

PUBLIC_KEYS = {"site_name", "site_logo", "ga4_id", "social_links", "footer_text"}

DEFAULT_SETTINGS = {
    "site_name": {"value": "VigyanLLM", "type": "text"},
    "site_logo": {"value": "", "type": "image"},
    "ga4_id": {"value": "", "type": "text"},
    "social_links": {"value": "{}", "type": "json"},
    "footer_text": {"value": "© 2026 VigyanLLM. All rights reserved.", "type": "text"},
    "custom_css": {"value": "", "type": "text"},
    "custom_js": {"value": "", "type": "text"},
}


def _setting_to_item(setting: CMSSetting) -> SettingItem:
    value = setting.value
    if setting.type == "json" and value:
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            pass
    return SettingItem(
        id=setting.id,
        key=setting.key,
        value=value,
        type=setting.type,
        updated_at=setting.updated_at,
    )


@router.get("", response_model=SettingListResponse)
def list_settings(
    db: Session = Depends(get_db),
    user: AdminUser = Depends(get_current_user),
):
    q = db.query(CMSSetting)
    if user.role != "admin":
        q = q.filter(CMSSetting.key.notin_(SENSITIVE_KEYS))
    settings = q.all()
    return SettingListResponse(settings=[_setting_to_item(s) for s in settings])


@router.get("/public", response_model=SettingListResponse)
def public_settings(db: Session = Depends(get_db)):
    settings = db.query(CMSSetting).filter(CMSSetting.key.in_(PUBLIC_KEYS)).all()
    return SettingListResponse(settings=[_setting_to_item(s) for s in settings])


@router.put("/{key}", response_model=SettingItem)
def update_setting(
    key: str,
    req: SettingUpdate,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_admin),
):
    setting = db.query(CMSSetting).filter(CMSSetting.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    if req.value is not None:
        if setting.type == "json" and not isinstance(req.value, str):
            setting.value = json.dumps(req.value)
        else:
            setting.value = str(req.value) if req.value is not None else None
    if req.type is not None:
        setting.type = req.type
    db.commit()
    db.refresh(setting)
    return _setting_to_item(setting)


@router.post("/seed")
def seed_settings(
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_admin),
):
    created = []
    for key, cfg in DEFAULT_SETTINGS.items():
        existing = db.query(CMSSetting).filter(CMSSetting.key == key).first()
        if existing:
            continue
        setting = CMSSetting(key=key, value=cfg["value"], type=cfg["type"])
        db.add(setting)
        created.append(key)
    db.commit()
    return {"success": True, "created": created}

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database import get_db
from models import AdminUser, CMSNotification, CMSPage
from schemas import NotificationItem, AuthorInfo
from deps import get_current_user

router = APIRouter(prefix="/api/v1/cms", tags=["cms-notifications"])

@router.get("/notifications")
def list_notifications(
    unread: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: AdminUser = Depends(get_current_user),
):
    q = db.query(CMSNotification).filter(CMSNotification.user_id == user.id)
    if unread:
        q = q.filter(CMSNotification.is_read == False)
    total = q.count()
    notifs = q.order_by(desc(CMSNotification.created_at)).offset(offset).limit(limit).all()
    items = []
    for n in notifs:
        page_slug = None
        if n.page_id:
            page = db.query(CMSPage).filter(CMSPage.id == n.page_id).first()
            if page:
                page_slug = page.slug
        items.append(NotificationItem(
            id=n.id,
            type=n.type,
            message=n.message,
            page_slug=page_slug,
            is_read=n.is_read,
            created_at=n.created_at,
        ))
    return {"data": {"notifications": items, "total": total}}

@router.post("/notifications/{notif_id}/read")
def mark_notification_read(
    notif_id: str,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(get_current_user),
):
    notif = db.query(CMSNotification).filter(
        CMSNotification.id == notif_id,
        CMSNotification.user_id == user.id,
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.commit()
    return {"success": True}

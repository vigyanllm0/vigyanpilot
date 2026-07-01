from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database import get_db
from models import AdminUser, CMSPage, CMSPageRevision, CMSReviewNote, CMSNotification
from schemas import (
    ReviewQueueItem, ReviewQueueResponse, ReviewNoteItem, ReviewNoteCreate,
    RejectRequest, AuthorInfo, PageDetail,
)
from deps import get_current_user, require_admin
from datetime import datetime, timezone
from routes.pages import page_to_detail, _render_html

router = APIRouter(prefix="/api/v1/cms/pages", tags=["cms-review"])
queue_router = APIRouter(prefix="/api/v1/cms", tags=["cms-review"])

def _waiting_hours(submitted_at) -> float:
    if not submitted_at:
        return 0
    delta = datetime.now(timezone.utc) - submitted_at
    return round(delta.total_seconds() / 3600, 1)

@router.post("/{slug}/submit")
def submit_for_review(
    slug: str,
    body: dict = {},
    db: Session = Depends(get_db),
    user: AdminUser = Depends(get_current_user),
):
    page = db.query(CMSPage).filter(CMSPage.slug == slug).first()
    if not page:
        raise HTTPException(status_code=404, detail="PAGE_NOT_FOUND")
    if page.author_id != user.id:
        raise HTTPException(status_code=403, detail="Only the page author can submit")
    if page.status not in ("draft", "rejected"):
        raise HTTPException(status_code=409, detail="Page must be in 'draft' or 'rejected' status")

    page.status = "pending_review"
    page.submitted_at = datetime.now(timezone.utc)
    page.rejection_reason = None
    page.reviewer_id = None
    page.reviewed_at = None
    page.updated_at = datetime.now(timezone.utc)

    revision = CMSPageRevision(
        page_id=page.id,
        content_json=page.content_json,
        content_html=page.content_html,
        changed_by=user.id,
        change_note=body.get("change_note"),
        status_at_save="pending_review",
    )
    db.add(revision)

    change_note = body.get("change_note", "")
    if change_note:
        note = CMSReviewNote(
            page_id=page.id,
            author_id=user.id,
            note=change_note,
        )
        db.add(note)

    admins = db.query(AdminUser).filter(AdminUser.role == "admin").all()
    for admin_user in admins:
        notif = CMSNotification(
            user_id=admin_user.id,
            page_id=page.id,
            type="submitted_for_review",
            message=f'Page "{page.title}" submitted for review by {user.display_name or user.email}',
        )
        db.add(notif)

    db.commit()
    return {"data": page_to_detail(page, db)}

@router.post("/{slug}/approve")
def approve_page(
    slug: str,
    body: dict = {},
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_admin),
):
    page = db.query(CMSPage).filter(CMSPage.slug == slug).first()
    if not page:
        raise HTTPException(status_code=404, detail="PAGE_NOT_FOUND")
    if page.status != "pending_review":
        raise HTTPException(status_code=409, detail="Page must be in 'pending_review' status")

    page.content_html = _render_html(page.content_json)
    page.status = "published"
    page.reviewer_id = user.id
    page.reviewed_at = datetime.now(timezone.utc)
    page.published_at = datetime.now(timezone.utc)
    page.updated_at = datetime.now(timezone.utc)

    revision = CMSPageRevision(
        page_id=page.id,
        content_json=page.content_json,
        content_html=page.content_html,
        changed_by=user.id,
        change_note=body.get("change_note"),
        status_at_save="published",
    )
    db.add(revision)

    notif = CMSNotification(
        user_id=page.author_id,
        page_id=page.id,
        type="approved",
        message=f'Your page "{page.title}" has been approved and published.',
    )
    db.add(notif)

    db.commit()
    return {"data": page_to_detail(page, db)}

@router.post("/{slug}/reject")
def reject_page(
    slug: str,
    req: RejectRequest,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_admin),
):
    page = db.query(CMSPage).filter(CMSPage.slug == slug).first()
    if not page:
        raise HTTPException(status_code=404, detail="PAGE_NOT_FOUND")
    if page.status != "pending_review":
        raise HTTPException(status_code=409, detail="Page must be in 'pending_review' status")

    page.status = "rejected"
    page.reviewer_id = user.id
    page.reviewed_at = datetime.now(timezone.utc)
    page.rejection_reason = req.reason
    page.updated_at = datetime.now(timezone.utc)

    revision = CMSPageRevision(
        page_id=page.id,
        content_json=page.content_json,
        content_html=page.content_html,
        changed_by=user.id,
        change_note=req.change_note or f"Rejected: {req.reason[:240]}",
        status_at_save="rejected",
    )
    db.add(revision)

    note = CMSReviewNote(
        page_id=page.id,
        author_id=user.id,
        note=f"REJECTED: {req.reason}",
    )
    db.add(note)

    notif = CMSNotification(
        user_id=page.author_id,
        page_id=page.id,
        type="rejected",
        message=f'Your page "{page.title}" was rejected. Reason: {req.reason[:200]}',
    )
    db.add(notif)

    db.commit()
    return {"data": page_to_detail(page, db)}

@router.post("/{slug}/archive")
def archive_page(slug: str, db: Session = Depends(get_db), user: AdminUser = Depends(require_admin)):
    page = db.query(CMSPage).filter(CMSPage.slug == slug).first()
    if not page:
        raise HTTPException(status_code=404, detail="PAGE_NOT_FOUND")
    if page.status not in ("published", "draft"):
        raise HTTPException(status_code=409, detail="Only published or draft pages can be archived")
    page.status = "archived"
    page.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"data": page_to_detail(page, db)}

@router.post("/{slug}/restore")
def restore_page(slug: str, db: Session = Depends(get_db), user: AdminUser = Depends(require_admin)):
    page = db.query(CMSPage).filter(CMSPage.slug == slug).first()
    if not page:
        raise HTTPException(status_code=404, detail="PAGE_NOT_FOUND")
    if page.status != "archived":
        raise HTTPException(status_code=409, detail="Only archived pages can be restored")
    page.status = "draft"
    page.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"data": page_to_detail(page, db)}

@router.get("/{slug}/review-notes")
def list_review_notes(slug: str, db: Session = Depends(get_db), user: AdminUser = Depends(get_current_user)):
    page = db.query(CMSPage).filter(CMSPage.slug == slug).first()
    if not page:
        raise HTTPException(status_code=404, detail="PAGE_NOT_FOUND")
    if user.role == "editor" and page.author_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    notes = db.query(CMSReviewNote).filter(
        CMSReviewNote.page_id == page.id
    ).order_by(CMSReviewNote.created_at.asc()).all()
    items = []
    for n in notes:
        author = db.query(AdminUser).filter(AdminUser.id == n.author_id).first()
        items.append(ReviewNoteItem(
            id=n.id,
            note=n.note,
            author=AuthorInfo(display_name=author.display_name if author else None, email=author.email if author else ""),
            created_at=n.created_at,
        ))
    return {"data": {"notes": items}}

@router.post("/{slug}/review-notes", status_code=201)
def add_review_note(
    slug: str,
    req: ReviewNoteCreate,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(get_current_user),
):
    page = db.query(CMSPage).filter(CMSPage.slug == slug).first()
    if not page:
        raise HTTPException(status_code=404, detail="PAGE_NOT_FOUND")
    if user.role == "editor" and page.author_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    note = CMSReviewNote(
        page_id=page.id,
        author_id=user.id,
        note=req.note,
    )
    db.add(note)
    db.commit()
    return {"data": ReviewNoteItem(
        id=note.id,
        note=note.note,
        author=AuthorInfo(display_name=user.display_name, email=user.email),
        created_at=note.created_at,
    )}

@queue_router.get("/review-queue")
def review_queue(
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_admin),
):
    q = db.query(CMSPage).filter(CMSPage.status == "pending_review").order_by(CMSPage.submitted_at.asc().nullslast())
    total = q.count()
    pages = q.offset(offset).limit(limit).all()
    items = []
    for p in pages:
        author = db.query(AdminUser).filter(AdminUser.id == p.author_id).first()
        items.append(ReviewQueueItem(
            id=p.id,
            slug=p.slug,
            title=p.title,
            author=AuthorInfo(display_name=author.display_name if author else None, email=author.email if author else ""),
            submitted_at=p.submitted_at,
            waiting_hours=_waiting_hours(p.submitted_at),
            content_html=p.content_html,
        ))
    return {"data": ReviewQueueResponse(queue=items, total=total, limit=limit, offset=offset)}

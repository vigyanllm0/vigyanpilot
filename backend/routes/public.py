from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database import get_db
from models import AdminUser, CMSPage, CMSPageRevision
from schemas import AuthorInfo, PageDetail
from fastapi.responses import HTMLResponse
import os

router = APIRouter(prefix="/api/v1/pages", tags=["public"])

@router.get("")
def public_list_pages(
    content_type: str = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(CMSPage).filter(CMSPage.status == "published")
    if content_type:
        q = q.filter(CMSPage.content_type == content_type)
    total = q.count()
    pages = q.order_by(desc(CMSPage.published_at)).offset(offset).limit(limit).all()
    return {
        "data": {
            "pages": [{
                "slug": p.slug,
                "title": p.title,
                "description": p.description,
                "content_type": p.content_type,
                "published_at": p.published_at,
                "created_at": p.created_at,
            } for p in pages],
            "total": total,
        }
    }

@router.get("/{slug}")
def get_public_page(slug: str, db: Session = Depends(get_db)):
    page = db.query(CMSPage).filter(
        CMSPage.slug == slug,
        CMSPage.status == "published",
    ).first()
    if not page:
        raise HTTPException(status_code=404, detail="Not found")

    revision = db.query(CMSPageRevision).filter(
        CMSPageRevision.page_id == page.id,
        CMSPageRevision.status_at_save == "published",
    ).order_by(desc(CMSPageRevision.created_at)).first()

    content_html = revision.content_html if revision else page.content_html

    return {
        "data": {
            "slug": page.slug,
            "title": page.title,
            "description": page.description,
            "content_html": content_html or "",
            "hero_image": page.hero_image,
            "content_type": page.content_type,
            "published_at": page.published_at,
            "updated_at": page.updated_at,
        }
    }

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database import get_db
from models import AdminUser, CMSPage, CMSPageRevision
from schemas import AuthorInfo, PageDetail
from fastapi.responses import HTMLResponse
import os

router = APIRouter(prefix="/api/v1/pages", tags=["public"])

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
            "published_at": page.published_at,
            "updated_at": page.updated_at,
        }
    }

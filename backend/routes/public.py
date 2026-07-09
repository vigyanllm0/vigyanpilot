"""
VigyanLLM CMS Public Pages Route
===================================
Exposes published CMS pages to anonymous public clients.

Security hardening (SEC-08 FIX — Stored XSS):
  The previous implementation returned raw content_html from the database
  directly to the browser without any sanitization, enabling stored XSS if
  an admin account was compromised or a malicious revision was injected.

  FIX: All content_html is passed through bleach with a strict whitelist
  before being returned. Only safe presentational HTML tags and attributes
  are allowed. Script tags, event handlers, and unsafe protocols are stripped.

Bleach whitelist policy:
  Tags:   h1-h6, p, br, strong, em, u, s, ul, ol, li, blockquote, pre,
          code, a, img, table, thead, tbody, tr, th, td, figure, figcaption,
          div, span, hr, sup, sub
  Attrs:  href (a), src/alt/width/height (img), class/id (all), colspan/
          rowspan (table cells)
  Protocols: http, https, mailto (href only — no javascript:)
"""

import logging

import bleach
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from models import AdminUser, CMSPage, CMSPageRevision

logger = logging.getLogger("vigyanllm.cms.public")

router = APIRouter(prefix="/api/v1/pages", tags=["public"])

# ── Bleach whitelist (SEC-08 FIX) ────────────────────────────────────────
# Only safe presentational tags are permitted. All event handlers, <script>,
# <iframe>, <object>, <embed>, and unsafe attribute values are stripped.
_ALLOWED_TAGS = [
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "br", "hr",
    "strong", "em", "u", "s", "b", "i",
    "ul", "ol", "li",
    "blockquote", "pre", "code",
    "a",
    "img",
    "table", "thead", "tbody", "tfoot", "tr", "th", "td",
    "figure", "figcaption",
    "div", "span",
    "sup", "sub",
]

_ALLOWED_ATTRIBUTES = {
    "a":   ["href", "title", "target", "rel"],
    "img": ["src", "alt", "width", "height", "loading", "title"],
    "td":  ["colspan", "rowspan"],
    "th":  ["colspan", "rowspan", "scope"],
    "*":   ["class", "id"],   # Used for styling/anchors — no event handlers
}

# Only allow safe protocols in href/src
_ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def _sanitize_html(raw_html: str | None) -> str:
    """
    Sanitize HTML content using bleach with a strict whitelist.

    Strips all tags not in _ALLOWED_TAGS, all attributes not in
    _ALLOWED_ATTRIBUTES, and all protocols not in _ALLOWED_PROTOCOLS.
    JavaScript: and data: URIs are stripped from href/src.

    Args:
        raw_html: Raw HTML string from database (may be None).

    Returns:
        Sanitized HTML string safe for browser rendering, or "" if None.
    """
    if not raw_html:
        return ""
    try:
        return bleach.clean(
            raw_html,
            tags=_ALLOWED_TAGS,
            attributes=_ALLOWED_ATTRIBUTES,
            protocols=_ALLOWED_PROTOCOLS,
            strip=True,          # Remove disallowed tags rather than escaping
            strip_comments=True, # Remove HTML comments (can hide payloads)
        )
    except Exception as exc:
        logger.error("bleach sanitization failed: %s", exc)
        # Fail-closed: return empty string rather than unsanitized content
        return ""


@router.get("")
def public_list_pages(
    content_type: str = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    List published CMS pages (public, no auth required).

    Args:
        content_type: Optional filter (e.g. 'blog', 'docs').
        limit:        Max results per page (max 50).
        offset:       Pagination offset.

    Returns:
        JSON with pages list (slug, title, description, type, dates) and total count.
        Note: content_html is NOT included in list view for performance.
    """
    q = db.query(CMSPage).filter(CMSPage.status == "published")
    if content_type:
        q = q.filter(CMSPage.content_type == content_type)
    total = q.count()
    pages = q.order_by(desc(CMSPage.published_at)).offset(offset).limit(min(limit, 50)).all()
    return {
        "data": {
            "pages": [
                {
                    "slug": p.slug,
                    "title": p.title,
                    "description": p.description,
                    "content_type": p.content_type,
                    "published_at": p.published_at,
                    "created_at": p.created_at,
                }
                for p in pages
            ],
            "total": total,
        }
    }


@router.get("/{slug}")
def get_public_page(slug: str, db: Session = Depends(get_db)):
    """
    Get a single published CMS page by slug (public, no auth required).

    SEC-08 FIX: content_html is sanitized through bleach before returning
    to prevent stored XSS from compromised admin accounts or injected revisions.

    Args:
        slug: URL-safe page identifier.

    Returns:
        JSON with sanitized page content, hero image, and metadata.

    Raises:
        404: Page not found or not published.
    """
    page = db.query(CMSPage).filter(
        CMSPage.slug == slug,
        CMSPage.status == "published",
    ).first()
    if not page:
        raise HTTPException(status_code=404, detail="Not found")

    revision = (
        db.query(CMSPageRevision)
        .filter(
            CMSPageRevision.page_id == page.id,
            CMSPageRevision.status_at_save == "published",
        )
        .order_by(desc(CMSPageRevision.created_at))
        .first()
    )

    raw_html = revision.content_html if revision else page.content_html

    # SEC-08 FIX: Sanitize before returning — strips XSS payloads
    safe_html = _sanitize_html(raw_html)

    return {
        "data": {
            "slug": page.slug,
            "title": page.title,
            "description": page.description,
            "content_html": safe_html,
            "hero_image": page.hero_image,
            "content_type": page.content_type,
            "published_at": page.published_at,
            "updated_at": page.updated_at,
        }
    }

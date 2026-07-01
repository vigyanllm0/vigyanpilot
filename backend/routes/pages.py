from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from database import get_db
from models import AdminUser, CMSPage, CMSPageRevision
from schemas import PageCreate, PageUpdate, PageDetail, PageListItem, PageListResponse, PageCreateResponse, AuthorInfo, RevisionItem
from deps import get_current_user, require_admin
from datetime import datetime, timezone
from sqlalchemy import desc

router = APIRouter(prefix="/api/v1/cms/pages", tags=["cms-pages"])

def page_to_list_item(page: CMSPage) -> PageListItem:
    return PageListItem(
        id=page.id,
        slug=page.slug,
        title=page.title,
        description=page.description,
        content_type=page.content_type,
        status=page.status,
        author=AuthorInfo(display_name=page.author.display_name, email=page.author.email),
        published_at=page.published_at,
        updated_at=page.updated_at,
    )

def page_to_detail(page: CMSPage, db: Session) -> PageDetail:
    reviewer_info = None
    if page.reviewer:
        reviewer_info = AuthorInfo(display_name=page.reviewer.display_name, email=page.reviewer.email)
    return PageDetail(
        id=page.id,
        slug=page.slug,
        title=page.title,
        description=page.description,
        content_json=page.content_json,
        content_html=page.content_html,
        hero_image=page.hero_image,
        status=page.status,
        content_type=page.content_type,
        author=AuthorInfo(display_name=page.author.display_name, email=page.author.email),
        reviewer=reviewer_info,
        rejection_reason=page.rejection_reason,
        published_at=page.published_at,
        submitted_at=page.submitted_at,
        reviewed_at=page.reviewed_at,
        created_at=page.created_at,
        updated_at=page.updated_at,
    )

@router.get("")
def list_pages(
    status_filter: str = Query(None, alias="status"),
    content_type: str = Query(None, alias="content_type"),
    sort: str = Query("updated_at"),
    order: str = Query("desc"),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    author_id: str = Query(None),
    db: Session = Depends(get_db),
    user: AdminUser = Depends(get_current_user),
):
    q = db.query(CMSPage)
    if user.role == "editor":
        q = q.filter(CMSPage.author_id == user.id)
    if author_id and user.role == "admin":
        q = q.filter(CMSPage.author_id == author_id)
    if status_filter:
        q = q.filter(CMSPage.status == status_filter)
    if content_type:
        q = q.filter(CMSPage.content_type == content_type)
    total = q.count()
    sort_col = getattr(CMSPage, sort, CMSPage.updated_at)
    order_fn = desc if order == "desc" else lambda c: c.asc()
    pages = q.order_by(order_fn(sort_col)).offset(offset).limit(limit).all()
    return {"data": PageListResponse(
        pages=[page_to_list_item(p) for p in pages],
        total=total,
        limit=limit,
        offset=offset,
    )}

@router.post("", status_code=201)
def create_page(
    req: PageCreate,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(get_current_user),
):
    existing = db.query(CMSPage).filter(CMSPage.slug == req.slug).first()
    if existing:
        raise HTTPException(status_code=409, detail="A page with this slug already exists.")

    if req.status not in ("draft", "pending_review"):
        raise HTTPException(status_code=400, detail="Status must be 'draft' or 'pending_review'")
    if req.status == "pending_review" and user.role == "editor":
        raise HTTPException(status_code=403, detail="Editors cannot submit for review on create. Save as draft first.")

    content_json = req.content_json
    content_html = _render_html(content_json)

    page = CMSPage(
        slug=req.slug,
        title=req.title,
        description=req.description,
        content_json=content_json,
        content_html=content_html,
        hero_image=req.hero_image,
        content_type=req.content_type,
        status=req.status,
        author_id=user.id,
        submitted_at=datetime.now(timezone.utc) if req.status == "pending_review" else None,
    )
    db.add(page)
    db.flush()

    revision = CMSPageRevision(
        page_id=page.id,
        content_json=content_json,
        content_html=content_html,
        changed_by=user.id,
        change_note=req.change_note,
        status_at_save=page.status,
    )
    db.add(revision)

    if req.status == "pending_review":
        _create_notification(db, "submitted_for_review", page, user)

    db.commit()
    return {"data": PageCreateResponse(id=page.id, slug=page.slug, status=page.status)}

@router.get("/{slug}")
def get_page(slug: str, db: Session = Depends(get_db), user: AdminUser = Depends(get_current_user)):
    page = db.query(CMSPage).filter(CMSPage.slug == slug).first()
    if not page:
        raise HTTPException(status_code=404, detail="PAGE_NOT_FOUND")
    if user.role == "editor" and page.author_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return {"data": page_to_detail(page, db)}

@router.put("/{slug}")
def update_page(
    slug: str,
    req: PageUpdate,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(get_current_user),
):
    page = db.query(CMSPage).filter(CMSPage.slug == slug).first()
    if not page:
        raise HTTPException(status_code=404, detail="PAGE_NOT_FOUND")
    if user.role == "editor" and page.author_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if req.content_type:
        if req.content_type not in ("page", "blog"):
            raise HTTPException(status_code=400, detail="content_type must be 'page' or 'blog'")

    if req.status:
        if req.status not in ("draft", "pending_review"):
            raise HTTPException(status_code=400, detail="Invalid status via update. Use submit endpoint.")
        if req.status == "pending_review" and user.role == "editor":
            raise HTTPException(status_code=403, detail="Use submit endpoint instead")

    if req.title:
        page.title = req.title
    if req.description is not None:
        page.description = req.description
    if req.hero_image is not None:
        page.hero_image = req.hero_image
    if req.content_type:
        page.content_type = req.content_type

    old_status = page.status

    if page.status == "published" and req.content_json:
        page.status = "draft"

    if req.content_json:
        page.content_json = req.content_json
        page.content_html = _render_html(req.content_json)

    if req.status:
        page.status = req.status

    if page.status == "pending_review" and old_status != "pending_review":
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
        change_note=req.change_note,
        status_at_save=page.status,
    )
    db.add(revision)

    if page.status == "pending_review" and old_status != "pending_review":
        _create_notification(db, "submitted_for_review", page, user)

    db.commit()
    return {"data": page_to_detail(page, db)}

@router.delete("/{slug}")
def delete_page(slug: str, db: Session = Depends(get_db), user: AdminUser = Depends(require_admin)):
    page = db.query(CMSPage).filter(CMSPage.slug == slug).first()
    if not page:
        raise HTTPException(status_code=404, detail="PAGE_NOT_FOUND")
    page.status = "archived"
    page.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"data": page_to_detail(page, db)}

@router.get("/{slug}/revisions")
def list_revisions(slug: str, db: Session = Depends(get_db), user: AdminUser = Depends(get_current_user)):
    page = db.query(CMSPage).filter(CMSPage.slug == slug).first()
    if not page:
        raise HTTPException(status_code=404, detail="PAGE_NOT_FOUND")
    if user.role == "editor" and page.author_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    revisions = db.query(CMSPageRevision).filter(
        CMSPageRevision.page_id == page.id
    ).order_by(desc(CMSPageRevision.created_at)).all()
    items = []
    for r in revisions:
        changer = db.query(AdminUser).filter(AdminUser.id == r.changed_by).first()
        items.append(RevisionItem(
            id=r.id,
            change_note=r.change_note,
            changed_by=AuthorInfo(display_name=changer.display_name if changer else None, email=changer.email if changer else ""),
            status_at_save=r.status_at_save,
            created_at=r.created_at,
        ))
    return {"data": {"revisions": items}}

@router.post("/{slug}/revisions/{revision_id}/restore")
def restore_revision(
    slug: str,
    revision_id: str,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_admin),
):
    page = db.query(CMSPage).filter(CMSPage.slug == slug).first()
    if not page:
        raise HTTPException(status_code=404, detail="PAGE_NOT_FOUND")
    revision = db.query(CMSPageRevision).filter(CMSPageRevision.id == revision_id, CMSPageRevision.page_id == page.id).first()
    if not revision:
        raise HTTPException(status_code=404, detail="REVISION_NOT_FOUND")

    old_content = page.content_json
    page.content_json = revision.content_json
    page.content_html = revision.content_html
    page.updated_at = datetime.now(timezone.utc)

    new_revision = CMSPageRevision(
        page_id=page.id,
        content_json=page.content_json,
        content_html=page.content_html,
        changed_by=user.id,
        change_note=f"Restored from revision of {revision.created_at.strftime('%Y-%m-%d %H:%M')}",
        status_at_save=page.status,
    )
    db.add(new_revision)
    db.commit()
    return {"data": page_to_detail(page, db)}


def _render_html(content_json: dict) -> str:
    blocks = []
    for node in content_json.get("content", []):
        blocks.append(_render_node(node))
    return "".join(blocks)

def _render_node(node: dict) -> str:
    t = node.get("type", "")
    attrs = node.get("attrs", {}) or {}
    marks = node.get("marks", []) or []

    if t == "paragraph":
        inner = _render_children(node)
        return f"<p>{inner}</p>"
    elif t == "heading":
        level = attrs.get("level", 2)
        inner = _render_children(node)
        return f"<h{level}>{inner}</h{level}>"
    elif t == "bulletList":
        inner = "".join([_render_node(c) for c in node.get("content", [])])
        return f"<ul>{inner}</ul>"
    elif t == "orderedList":
        inner = "".join([_render_node(c) for c in node.get("content", [])])
        return f"<ol>{inner}</ol>"
    elif t == "listItem":
        inner = "".join([_render_node(c) for c in node.get("content", [])])
        return f"<li>{inner}</li>"
    elif t == "blockquote":
        inner = "".join([_render_node(c) for c in node.get("content", [])])
        return f"<blockquote>{inner}</blockquote>"
    elif t == "codeBlock":
        lang = attrs.get("language", "")
        lang_attr = f' class="language-{lang}"' if lang else ""
        inner = _render_children(node)
        return f"<pre><code{lang_attr}>{inner}</code></pre>"
    elif t == "horizontalRule":
        return "<hr>"
    elif t == "hardBreak":
        return "<br>"
    elif t == "image":
        src = attrs.get("src", "")
        alt = attrs.get("alt", "")
        caption = attrs.get("caption", "")
        img = f'<img src="{src}" alt="{alt}" loading="lazy">'
        if caption:
            return f'<figure>{img}<figcaption>{caption}</figcaption></figure>'
        return img
    elif t == "text":
        text = node.get("text", "")
        for m in marks:
            mt = m.get("type")
            if mt == "bold":
                text = f"<strong>{text}</strong>"
            elif mt == "italic":
                text = f"<em>{text}</em>"
            elif mt == "underline":
                text = f"<u>{text}</u>"
            elif mt == "strike":
                text = f"<s>{text}</s>"
            elif mt == "link":
                href = m.get("attrs", {}).get("href", "")
                text = f'<a href="{href}" target="_blank" rel="noopener">{text}</a>'
            elif mt == "code":
                text = f"<code>{text}</code>"
        return text
    return ""

def _render_children(node: dict) -> str:
    content = node.get("content", [])
    if isinstance(content, list):
        return "".join([_render_node(c) for c in content])
    if isinstance(content, str):
        return content
    return ""

def _create_notification(db, ntype: str, page: CMSPage, actor: AdminUser):
    from models import CMSNotification
    admins = db.query(AdminUser).filter(AdminUser.role == "admin").all()
    for admin_user in admins:
        if ntype == "submitted_for_review":
            msg = f'Page "{page.title}" submitted for review by {actor.display_name or actor.email}'
            notif = CMSNotification(
                user_id=admin_user.id,
                page_id=page.id,
                type="submitted_for_review",
                message=msg,
            )
            db.add(notif)

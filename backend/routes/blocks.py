from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models import AdminUser, CMSBlock
from schemas import BlockItem, BlockCreate, BlockUpdate, BlockListResponse, AuthorInfo
from deps import get_current_user, require_admin
from datetime import datetime, timezone
from sqlalchemy import desc
import logging

logger = logging.getLogger("vigyanllm.cms.blocks")

router = APIRouter(prefix="/api/v1/cms/blocks", tags=["cms-blocks"])


def _block_to_item(block: CMSBlock) -> BlockItem:
    creator_info = None
    if block.created_by:
        creator = block.__dict__.get("_creator")
        if creator:
            creator_info = AuthorInfo(display_name=creator.display_name, email=creator.email)
    return BlockItem(
        id=block.id,
        name=block.name,
        slug=block.slug,
        description=block.description,
        content_json=block.content_json,
        content_html=block.content_html,
        category=block.category or "custom",
        created_by=creator_info,
        updated_at=block.updated_at,
    )


@router.get("", response_model=BlockListResponse)
def list_blocks(
    category: str = Query(None),
    search: str = Query(None),
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_admin),
):
    q = db.query(CMSBlock)
    if category:
        q = q.filter(CMSBlock.category == category)
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            CMSBlock.name.ilike(pattern) | CMSBlock.description.ilike(pattern)
        )
    total = q.count()
    blocks = q.order_by(desc(CMSBlock.updated_at)).all()
    items = []
    for b in blocks:
        if b.created_by:
            creator = db.query(AdminUser).filter(AdminUser.id == b.created_by).first()
            b.__dict__["_creator"] = creator
        items.append(_block_to_item(b))
    return BlockListResponse(blocks=items, total=total)


@router.post("", response_model=BlockItem, status_code=201)
def create_block(
    req: BlockCreate,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_admin),
):
    existing = db.query(CMSBlock).filter(CMSBlock.slug == req.slug).first()
    if existing:
        raise HTTPException(status_code=409, detail="A block with this slug already exists")

    from routes.pages import _render_html
    content_html = _render_html(req.content_json)

    block = CMSBlock(
        name=req.name,
        slug=req.slug,
        description=req.description,
        content_json=req.content_json,
        content_html=content_html,
        category=req.category,
        created_by=user.id,
    )
    db.add(block)
    db.commit()
    db.refresh(block)
    if block.created_by:
        creator = db.query(AdminUser).filter(AdminUser.id == block.created_by).first()
        block.__dict__["_creator"] = creator
    return _block_to_item(block)


@router.get("/{slug}", response_model=BlockItem)
def get_block(
    slug: str,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_admin),
):
    block = db.query(CMSBlock).filter(CMSBlock.slug == slug).first()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    if block.created_by:
        creator = db.query(AdminUser).filter(AdminUser.id == block.created_by).first()
        block.__dict__["_creator"] = creator
    return _block_to_item(block)


@router.put("/{slug}", response_model=BlockItem)
def update_block(
    slug: str,
    req: BlockUpdate,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_admin),
):
    block = db.query(CMSBlock).filter(CMSBlock.slug == slug).first()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    if req.name is not None:
        block.name = req.name
    if req.description is not None:
        block.description = req.description
    if req.category is not None:
        block.category = req.category
    if req.content_json is not None:
        block.content_json = req.content_json
        from routes.pages import _render_html
        block.content_html = _render_html(req.content_json)

    block.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(block)
    if block.created_by:
        creator = db.query(AdminUser).filter(AdminUser.id == block.created_by).first()
        block.__dict__["_creator"] = creator
    return _block_to_item(block)


@router.delete("/{slug}")
def delete_block(
    slug: str,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(require_admin),
):
    block = db.query(CMSBlock).filter(CMSBlock.slug == slug).first()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    db.delete(block)
    db.commit()
    return {"success": True}

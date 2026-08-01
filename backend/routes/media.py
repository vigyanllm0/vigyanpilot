from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
from models import AdminUser, CMSMedia
from schemas import MediaItem, MediaUploadResponse, MediaListResponse, AuthorInfo
from deps import get_current_user
from config import UPLOAD_DIR
import os
import uuid
import struct
import datetime
import logging

logger = logging.getLogger("vigyanllm.cms.media")

router = APIRouter(prefix="/api/v1/cms", tags=["cms-media"])

ALLOWED_IMAGE_MIMES = {
    "image/png", "image/jpeg", "image/webp", "image/gif", "image/svg+xml",
}
ALLOWED_VIDEO_MIMES = {
    "video/mp4", "video/webm", "video/quicktime",
}
MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_VIDEO_SIZE = 20 * 1024 * 1024


class MediaUpdate(BaseModel):
    alt_text: Optional[str] = None
    caption: Optional[str] = None


def _check_image_magic_bytes(data: bytes) -> str | None:
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return "image/png"
    if data[:2] in (b'\xff\xd8',):
        return "image/jpeg"
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return "image/webp"
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return "image/gif"
    stripped = data[:256].lstrip()
    if stripped.startswith(b'<svg') or stripped.startswith(b'<?xml') or b'<svg' in data[:512]:
        return "image/svg+xml"
    return None


def _get_dimensions(data: bytes, mime: str) -> tuple[int, int]:
    try:
        from PIL import Image as PilImage
        import io
        with PilImage.open(io.BytesIO(data)) as img:
            return img.size
    except ImportError:
        pass
    try:
        if mime == "image/png":
            w = struct.unpack('>I', data[16:20])[0]
            h = struct.unpack('>I', data[20:24])[0]
            return w, h
        if mime == "image/jpeg":
            i = 0
            while i < len(data) - 1:
                if data[i] == 0xff and data[i + 1] == 0xc0:
                    h = struct.unpack('>H', data[i + 5:i + 7])[0]
                    w = struct.unpack('>H', data[i + 7:i + 9])[0]
                    return w, h
                i += 1
    except Exception:
        pass
    return 0, 0


def _media_to_item(media: CMSMedia) -> MediaItem:
    uploader_info = None
    if media.uploader:
        uploader_info = AuthorInfo(display_name=media.uploader.display_name, email=media.uploader.email)
    return MediaItem(
        id=media.id,
        filename=media.filename,
        original_name=media.original_name,
        url=media.url,
        mime_type=media.mime_type,
        media_type=media.media_type,
        size_bytes=media.size_bytes,
        width=media.width,
        height=media.height,
        alt_text=media.alt_text,
        caption=media.caption,
        uploaded_by=uploader_info,
        created_at=media.created_at,
    )


@router.post("/upload", response_model=MediaUploadResponse, status_code=201)
async def upload_media(
    file: UploadFile = File(...),
    alt_text: str = Form(None),
    caption: str = Form(None),
    db: Session = Depends(get_db),
    user: AdminUser = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    is_video = content_type in ALLOWED_VIDEO_MIMES

    data = await file.read()

    if is_video:
        if len(data) > MAX_VIDEO_SIZE:
            raise HTTPException(status_code=413, detail="Video exceeds 20 MB limit")
        mime = content_type
        media_type = "video"
        w, h = 0, 0
    else:
        if len(data) > MAX_IMAGE_SIZE:
            raise HTTPException(status_code=413, detail="File exceeds 5 MB limit")
        magic_mime = _check_image_magic_bytes(data)
        if not magic_mime:
            raise HTTPException(
                status_code=415,
                detail="Cannot determine file type from file content. Allowed: PNG, JPEG, WEBP, GIF, SVG",
            )
        if magic_mime not in ALLOWED_IMAGE_MIMES:
            raise HTTPException(status_code=415, detail=f"MIME type '{magic_mime}' not allowed")
        mime = magic_mime
        media_type = "image"
        w, h = _get_dimensions(data, mime)

    now = datetime.datetime.now()
    year = str(now.year)
    month = f"{now.month:02d}"
    upload_path = os.path.join(UPLOAD_DIR, year, month)
    os.makedirs(upload_path, exist_ok=True)

    ext = os.path.splitext(file.filename)[1].lower()
    stem = os.path.splitext(file.filename)[0]
    safe_stem = "".join(c for c in stem if c.isalnum() or c in "-_")
    random_prefix = uuid.uuid4().hex[:8]
    new_filename = f"{random_prefix}-{safe_stem}{ext}"
    full_path = os.path.join(upload_path, new_filename)

    with open(full_path, "wb") as f:
        f.write(data)

    url = f"/uploads/cms/{year}/{month}/{new_filename}"

    record = CMSMedia(
        filename=new_filename,
        original_name=file.filename,
        url=url,
        mime_type=mime,
        media_type=media_type,
        size_bytes=len(data),
        width=w,
        height=h,
        alt_text=alt_text,
        caption=caption,
        uploaded_by=user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info(
        "Uploaded %s (%s, %d bytes) by user %s",
        new_filename, mime, len(data), user.email,
    )

    return MediaUploadResponse(success=True, data=_media_to_item(record))


@router.get("/media", response_model=MediaListResponse)
def list_media(
    media_type: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: AdminUser = Depends(get_current_user),
):
    q = db.query(CMSMedia)
    if media_type:
        q = q.filter(CMSMedia.media_type == media_type)
    total = q.count()
    items = q.order_by(CMSMedia.created_at.desc()).offset(offset).limit(limit).all()
    return MediaListResponse(items=[_media_to_item(m) for m in items], total=total)


@router.get("/media/{media_id}", response_model=MediaItem)
def get_media(
    media_id: str,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(get_current_user),
):
    media = db.query(CMSMedia).filter(CMSMedia.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    return _media_to_item(media)


@router.put("/media/{media_id}", response_model=MediaItem)
def update_media(
    media_id: str,
    req: MediaUpdate,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(get_current_user),
):
    media = db.query(CMSMedia).filter(CMSMedia.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    if req.alt_text is not None:
        media.alt_text = req.alt_text
    if req.caption is not None:
        media.caption = req.caption
    db.commit()
    db.refresh(media)
    return _media_to_item(media)


@router.delete("/media/{media_id}")
def delete_media(
    media_id: str,
    db: Session = Depends(get_db),
    user: AdminUser = Depends(get_current_user),
):
    media = db.query(CMSMedia).filter(CMSMedia.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    file_path = os.path.join(UPLOAD_DIR, media.url.replace("/uploads/cms/", ""))
    if os.path.exists(file_path):
        os.remove(file_path)
    db.delete(media)
    db.commit()
    return {"success": True}

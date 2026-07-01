from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from database import get_db
from models import AdminUser
from deps import get_current_user
from config import UPLOAD_DIR, MAX_UPLOAD_SIZE, ALLOWED_EXTENSIONS
import os, uuid, struct, datetime

router = APIRouter(prefix="/api/v1/cms", tags=["cms-upload"])

def _check_magic_bytes(data: bytes) -> str | None:
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return "image/png"
    if data[:2] in (b'\xff\xd8',):
        return "image/jpeg"
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return "image/webp"
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return "image/gif"
    if data[:4] == b'<svg' or data[:5] == b'<?xml':
        return "image/svg+xml"
    return None

def _get_dimensions(data: bytes, mime: str) -> tuple[int, int]:
    try:
        if mime == "image/png":
            w = struct.unpack('>I', data[16:20])[0]
            h = struct.unpack('>I', data[20:24])[0]
            return w, h
        if mime == "image/jpeg":
            i = 0
            while i < len(data) - 1:
                if data[i] == 0xff and data[i+1] == 0xc0:
                    h = struct.unpack('>H', data[i+5:i+7])[0]
                    w = struct.unpack('>H', data[i+7:i+9])[0]
                    return w, h
                i += 1
    except:
        pass
    return 0, 0

@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    context: str = Form(None),
    db: Session = Depends(get_db),
    user: AdminUser = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Extension {ext} not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    data = await file.read()
    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 5MB limit")

    magic_mime = _check_magic_bytes(data)
    if not magic_mime:
        raise HTTPException(status_code=415, detail="Cannot determine file type from magic bytes")

    w, h = _get_dimensions(data, magic_mime)
    if max(w, h) > 4096:
        raise HTTPException(status_code=400, detail="Image dimensions exceed 4096px")

    now = datetime.datetime.now()
    year = str(now.year)
    month = f"{now.month:02d}"
    upload_path = os.path.join(UPLOAD_DIR, year, month)
    os.makedirs(upload_path, exist_ok=True)

    stem = os.path.splitext(file.filename)[0]
    safe_stem = "".join(c for c in stem if c.isalnum() or c in "-_")
    random_prefix = uuid.uuid4().hex[:8]
    new_filename = f"{random_prefix}-{safe_stem}{ext}"
    full_path = os.path.join(upload_path, new_filename)

    if magic_mime == "image/svg+xml":
        sanitized = data.replace(b"<script", b"<!-- script").replace(b"onload", b"onload-blocked")
        with open(full_path, "wb") as f:
            f.write(sanitized)
    else:
        with open(full_path, "wb") as f:
            f.write(data)

    url = f"/uploads/cms/{year}/{month}/{new_filename}"
    return {
        "success": True,
        "data": {
            "url": url,
            "filename": new_filename,
            "size_bytes": len(data),
            "mime_type": magic_mime,
            "dimensions": {"width": w, "height": h},
        },
    }

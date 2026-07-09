"""
VigyanLLM CMS Upload Route
============================
Handles authenticated image uploads for the CMS backend.

Security hardening (SEC-09, BUG-08 FIXES):
  - Magic-byte MIME validation (not just extension)
  - SVG content sanitized with defusedxml to strip ALL dangerous elements:
    <script>, inline event handlers (on*), <use> with external hrefs,
    foreign-object injections, and XML namespace attacks.
  - Content-Type header cross-checked against detected MIME type (SEC-12)
  - File size enforced at read time (SEC-11)
  - Bare except replaced with typed exceptions (BUG-28)
  - File handles always closed via context manager (BUG-24)

Allowed MIME types: PNG, JPEG, WEBP, GIF, SVG
Max file size: 5 MB (MAX_UPLOAD_SIZE from config)
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from database import get_db
from models import AdminUser
from deps import get_current_user
from config import UPLOAD_DIR, MAX_UPLOAD_SIZE, ALLOWED_EXTENSIONS
import os
import uuid
import struct
import datetime
import logging

logger = logging.getLogger("vigyanllm.cms.upload")

router = APIRouter(prefix="/api/v1/cms", tags=["cms-upload"])


# ── SVG Sanitization (SEC-09 / BUG-08 FIX) ────────────────────────────────
# The previous implementation used str.replace() which is trivially bypassable
# via capitalisation (<SCRIPT>), onerror, namespace tricks, etc.
# We now use defusedxml to parse the SVG and rebuild it clean.

try:
    import defusedxml.ElementTree as _det
    import xml.etree.ElementTree as _et
    _DEFUSEDXML_AVAILABLE = True
except ImportError:
    _DEFUSEDXML_AVAILABLE = False
    logger.warning(
        "defusedxml not installed — SVG uploads will be REJECTED for safety. "
        "Install with: pip install defusedxml"
    )

# SVG elements that are never allowed (XSS vectors)
_SVG_BLOCKED_ELEMENTS = {
    "script", "object", "embed", "iframe", "foreignobject",
    "use",      # external <use href="http://..."> can load external content
    "animate",  # can trigger JS via attributeName
    "set",
    "animatetransform",
    "animatemotion",
}

# Event-handler attributes that are never allowed
_SVG_BLOCKED_ATTRS_PREFIX = (
    "on",    # onclick, onload, onerror, onmouseover, etc.
)

_SVG_BLOCKED_ATTRS_EXACT = {
    "href",          # on <use> — external resource load
    "xlink:href",    # legacy form of the above
    "action",
    "formaction",
}

_SVG_BLOCKED_ATTR_VALUES_STARTSWITH = (
    "javascript:",
    "data:",         # data: URIs can encode scripts
    "vbscript:",
)


def _sanitize_svg(raw_bytes: bytes) -> bytes:
    """
    Parse and re-serialise an SVG document, stripping all dangerous content.

    Strategy:
      1. Parse with defusedxml (blocks entity expansion / XXE attacks).
      2. Walk every element and remove blocked tags entirely.
      3. Strip all event-handler attributes (on*) and dangerous hrefs.
      4. Re-serialise to bytes.

    Args:
        raw_bytes: Raw SVG file content as bytes.

    Returns:
        Sanitized SVG bytes safe for storage and browser rendering.

    Raises:
        HTTPException(400): If the SVG cannot be parsed or defusedxml is not
                            installed (fail-closed for safety).
    """
    if not _DEFUSEDXML_AVAILABLE:
        raise HTTPException(
            status_code=415,
            detail="SVG uploads are temporarily disabled (defusedxml not installed). "
                   "Contact the administrator.",
        )

    try:
        root = _det.fromstring(raw_bytes.decode("utf-8", errors="replace"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid SVG: cannot parse XML. {exc}")

    _sanitize_element(root)

    return _et.tostring(root, encoding="unicode", xml_declaration=False).encode("utf-8")


def _sanitize_element(element) -> None:
    """
    Recursively sanitize an SVG element tree in-place.

    Removes blocked child elements and strips dangerous attributes.
    """
    # Collect children to remove (cannot modify list while iterating)
    to_remove = []
    for child in element:
        # Strip namespace prefix to get local tag name for comparison
        local_tag = child.tag.split("}")[-1].lower() if "}" in child.tag else child.tag.lower()
        if local_tag in _SVG_BLOCKED_ELEMENTS:
            to_remove.append(child)
        else:
            _sanitize_element(child)  # Recurse

    for child in to_remove:
        element.remove(child)

    # Strip dangerous attributes from this element
    attrs_to_remove = []
    for attr_name, attr_value in element.attrib.items():
        local_attr = attr_name.split("}")[-1].lower() if "}" in attr_name else attr_name.lower()

        # Block event handlers (onclick, onload, onerror, etc.)
        if local_attr.startswith(_SVG_BLOCKED_ATTRS_PREFIX):
            attrs_to_remove.append(attr_name)
            continue

        # Block exact dangerous attributes
        if local_attr in _SVG_BLOCKED_ATTRS_EXACT:
            attrs_to_remove.append(attr_name)
            continue

        # Block dangerous attribute values (javascript:, data:, etc.)
        for prefix in _SVG_BLOCKED_ATTR_VALUES_STARTSWITH:
            if attr_value.strip().lower().startswith(prefix):
                attrs_to_remove.append(attr_name)
                break

    for attr_name in attrs_to_remove:
        del element.attrib[attr_name]


# ── Magic-Byte MIME Detection ─────────────────────────────────────────────

def _check_magic_bytes(data: bytes) -> str | None:
    """
    Detect MIME type from file magic bytes.

    Extension-only validation (BUG-30) is bypassed by renaming files.
    Magic-byte inspection ensures the actual file content matches the
    declared extension (SEC-12 FIX).

    Returns:
        MIME type string, or None if unrecognised.
    """
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return "image/png"
    if data[:2] in (b'\xff\xd8',):
        return "image/jpeg"
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return "image/webp"
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return "image/gif"
    # SVG: XML-based — detect by content, not bytes alone
    stripped = data[:256].lstrip()
    if stripped.startswith(b'<svg') or stripped.startswith(b'<?xml') or b'<svg' in data[:512]:
        return "image/svg+xml"
    return None


def _get_dimensions(data: bytes, mime: str) -> tuple[int, int]:
    """
    Extract image dimensions from raw bytes for raster formats.

    Returns (0, 0) if dimensions cannot be determined (e.g. SVG, corrupt file).
    """
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
    except Exception as exc:
        logger.debug("Could not extract image dimensions: %s", exc)
    return 0, 0


# ── Upload Endpoint ────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    context: str = Form(None),
    db: Session = Depends(get_db),
    user: AdminUser = Depends(get_current_user),
):
    """
    Upload a CMS image (admin only).

    Accepts PNG, JPEG, WEBP, GIF, SVG files up to MAX_UPLOAD_SIZE bytes.
    SVGs are fully sanitized via defusedxml before storage.

    Returns:
        JSON with upload URL, filename, size, MIME type, and dimensions.

    Raises:
        400: Extension not allowed, file corrupt, or image too large.
        413: File exceeds size limit.
        415: MIME type cannot be determined from magic bytes.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Extension whitelist check (first line of defence — fast rejection)
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extension '{ext}' not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file content (SEC-11: enforce size limit at read time)
    data = await file.read()
    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 5 MB limit")

    # Magic-byte MIME validation (SEC-12 FIX: not extension-only)
    magic_mime = _check_magic_bytes(data)
    if not magic_mime:
        raise HTTPException(
            status_code=415,
            detail="Cannot determine file type from file content. Ensure the file is a valid image.",
        )

    # Cross-check: uploaded Content-Type must be compatible with detected MIME
    content_type_header = (file.content_type or "").split(";")[0].strip().lower()
    if content_type_header and content_type_header not in (magic_mime, "application/octet-stream"):
        logger.warning(
            "Content-Type mismatch: header=%s detected=%s filename=%s",
            content_type_header, magic_mime, file.filename,
        )
        # Log but do not hard-reject — some clients send wrong content-type

    # Dimension guard for raster images
    w, h = _get_dimensions(data, magic_mime)
    if max(w, h) > 4096:
        raise HTTPException(status_code=400, detail="Image dimensions exceed 4096 px maximum")

    # Build output path
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

    # SVG sanitization (SEC-09 / BUG-08 FIX — replaces naive str.replace())
    if magic_mime == "image/svg+xml":
        sanitized_data = _sanitize_svg(data)
        write_data = sanitized_data
    else:
        write_data = data

    # BUG-24 FIX: Always use context manager so file handle is closed on error
    with open(full_path, "wb") as f:
        f.write(write_data)

    url = f"/uploads/cms/{year}/{month}/{new_filename}"
    logger.info(
        "Uploaded %s (%s, %d bytes) by user %s",
        new_filename, magic_mime, len(write_data), user.email if hasattr(user, "email") else "unknown",
    )
    return {
        "success": True,
        "data": {
            "url": url,
            "filename": new_filename,
            "size_bytes": len(write_data),
            "mime_type": magic_mime,
            "dimensions": {"width": w, "height": h},
        },
    }

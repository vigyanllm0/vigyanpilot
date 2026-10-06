"""
VigyanLLM CMS media storage
===========================
Single write-path for CMS uploads, used by routes/upload.py and routes/media.py.

Production (S3_BUCKET set):
    PutObject/DeleteObject against the frontend origin bucket
    (vigyanllm-frontend, ap-south-1) under `uploads/cms/...`. CloudFront's
    default origin IS that bucket, so the returned `/uploads/cms/...` URL
    resolves through the distribution with no invalidation — object names are
    uuid-prefixed (immutable), so they can be cached aggressively.
    Credentials come from the boto3 default chain (AWS_ACCESS_KEY_ID /
    AWS_SECRET_ACCESS_KEY in the service EnvironmentFile).

Development (S3_BUCKET unset):
    Local disk under config.UPLOAD_DIR (gitignored — never relied on in
    production; this is exactly the bug the S3 path fixes, since the repo
    never ships frontend/uploads/ to the origin bucket).

Failures are loud: a rejected PutObject raises StorageError (routes convert
it to HTTP 502) instead of silently returning a URL that 404s through the CDN.
Deletes are best-effort (an orphaned object is harmless; a hard error would
block media/DB cleanup).
"""

import datetime
import logging
import os

from config import UPLOAD_DIR

logger = logging.getLogger("vigyanllm.cms.storage")

S3_BUCKET = os.environ.get("S3_BUCKET", "").strip()
S3_PREFIX = "uploads/cms"  # public URL path == S3 key (URL has a leading "/")
S3_REGION = os.environ.get("S3_BUCKET_REGION", "").strip() or "ap-south-1"


class StorageError(RuntimeError):
    """Backing store rejected a write (routes surface this as 502)."""


def _client():
    try:
        import boto3
        from botocore.config import Config
        from botocore.exceptions import BotoCoreError, ClientError  # noqa: F401
    except ImportError as exc:  # pragma: no cover — requirements pin guarantees it
        raise StorageError(
            "boto3 is not installed — install backend/requirements.txt"
        ) from exc
    return boto3.client(
        "s3",
        region_name=S3_REGION,
        config=Config(retries={"max_attempts": 3, "mode": "standard"}),
    )


def store(year: str, month: str, filename: str, data: bytes, content_type: str) -> str:
    """
    Persist one media object and return its public URL.

    Args:
        year/month: path segments (YYYY, MM) — shared by S3 key and local path.
        filename: already-sanitized unique filename (uuid prefix + safe stem).
        data: final bytes to store (SVGs must be sanitized by the caller).
        content_type: MIME type — set as the S3 ContentType so the CDN
            serves images inline instead of as downloads.

    Returns:
        "/uploads/cms/YYYY/MM/filename"

    Raises:
        StorageError: store rejected the write (S3 error or local I/O error).
    """
    key = f"{S3_PREFIX}/{year}/{month}/{filename}"
    if S3_BUCKET:
        try:
            _client().put_object(
                Bucket=S3_BUCKET,
                Key=key,
                Body=data,
                ContentType=content_type or "application/octet-stream",
                CacheControl="public, max-age=31536000, immutable",
            )
        except Exception as exc:  # noqa: BLE001 — any boto3 failure → StorageError
            logger.error("S3 PutObject failed for s3://%s/%s: %s", S3_BUCKET, key, exc)
            raise StorageError(f"S3 PutObject failed for {key}") from exc
    else:
        path = os.path.join(UPLOAD_DIR, year, month)
        try:
            os.makedirs(path, exist_ok=True)
            with open(os.path.join(path, filename), "wb") as fh:
                fh.write(data)
        except OSError as exc:
            logger.error("Local store failed for %s: %s", key, exc)
            raise StorageError(f"local store failed for {key}") from exc
    return f"/{key}"


def remove(url: str) -> None:
    """
    Best-effort delete of a previously stored object/file.

    Ignores URLs outside `/uploads/cms/` (external or legacy references).
    """
    if not isinstance(url, str) or not url.startswith(f"/{S3_PREFIX}/"):
        return
    key = url.lstrip("/")  # "uploads/cms/YYYY/MM/filename"
    if S3_BUCKET:
        try:
            _client().delete_object(Bucket=S3_BUCKET, Key=key)
        except Exception as exc:  # noqa: BLE001 — orphan object beats blocked cleanup
            logger.error("S3 DeleteObject failed for s3://%s/%s: %s", S3_BUCKET, key, exc)
    else:
        rel = url.replace(f"/{S3_PREFIX}/", "", 1)
        path = os.path.join(UPLOAD_DIR, rel)
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError as exc:
            logger.error("Local remove failed for %s: %s", path, exc)


def now_path_segments() -> tuple[str, str]:
    """(YYYY, MM) for this instant — shared by both route handlers."""
    now = datetime.datetime.now()
    return str(now.year), f"{now.month:02d}"

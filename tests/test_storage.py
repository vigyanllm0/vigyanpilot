"""
Unit tests for backend/storage.py (CMS media storage).

Covers both modes of the write path:
  - production: S3 PutObject/DeleteObject against the CloudFront origin bucket
  - development: local-disk fallback when S3_BUCKET is unset

No network access: the boto3 client is replaced with a recording fake.
"""

import os
import sys

# backend/config.py requires JWT_SECRET at import time (storage imports config)
os.environ.setdefault("JWT_SECRET", "storage-unit-test-secret")
os.environ.pop("S3_BUCKET", None)

# backend modules import each other as top-level names (config, storage, ...)
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
)

import pytest  # noqa: E402

import storage  # noqa: E402


class _FakeS3:
    """Records the kwargs of each boto3 call it receives."""

    def __init__(self, fail: bool = False):
        self.calls: list[tuple[str, dict]] = []
        self.fail = fail

    def _record(self, op: str, kwargs: dict) -> None:
        self.calls.append((op, kwargs))
        if self.fail:
            raise RuntimeError("simulated s3 failure")

    def put_object(self, **kwargs):
        self._record("put_object", kwargs)

    def delete_object(self, **kwargs):
        self._record("delete_object", kwargs)


def _use_s3(monkeypatch, fake: _FakeS3, bucket: str = "vigyanllm-frontend"):
    monkeypatch.setattr(storage, "S3_BUCKET", bucket)
    monkeypatch.setattr(storage, "_client", lambda: fake)


# ── store(): S3 (production) ────────────────────────────────────────────────

def test_store_s3_returns_public_url_and_sets_object_metadata(monkeypatch):
    fake = _FakeS3()
    _use_s3(monkeypatch, fake)

    url = storage.store("2026", "10", "ab12-photo.png", b"\x89PNG...", "image/png")

    assert url == "/uploads/cms/2026/10/ab12-photo.png"
    (op, kwargs), = fake.calls  # exactly one call
    assert op == "put_object"
    assert kwargs["Bucket"] == "vigyanllm-frontend"
    # public URL path == S3 key (leading "/" removed)
    assert kwargs["Key"] == "uploads/cms/2026/10/ab12-photo.png"
    assert kwargs["Body"] == b"\x89PNG..."
    assert kwargs["ContentType"] == "image/png"  # served inline, not downloaded
    assert "immutable" in kwargs["CacheControl"]  # uuid-prefixed → safe to cache


def test_store_s3_failure_raises_storage_error(monkeypatch):
    """A rejected write must NOT return a URL that would 404 through the CDN."""
    _use_s3(monkeypatch, _FakeS3(fail=True))

    with pytest.raises(storage.StorageError):
        storage.store("2026", "10", "x.png", b"data", "image/png")


def test_store_missing_content_type_falls_back_to_octet_stream(monkeypatch):
    fake = _FakeS3()
    _use_s3(monkeypatch, fake)

    storage.store("2026", "10", "x.bin", b"data", "")

    _, kwargs = fake.calls[0]
    assert kwargs["ContentType"] == "application/octet-stream"


# ── store(): local disk (development fallback) ──────────────────────────────

def test_store_local_writes_file_and_returns_same_url_shape(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "S3_BUCKET", "")
    monkeypatch.setattr(storage, "UPLOAD_DIR", str(tmp_path))

    url = storage.store("2026", "10", "ab12-photo.png", b"PNGDATA", "image/png")

    assert url == "/uploads/cms/2026/10/ab12-photo.png"
    written = tmp_path / "2026" / "10" / "ab12-photo.png"
    assert written.read_bytes() == b"PNGDATA"  # path layout unchanged from before


# ── remove() ────────────────────────────────────────────────────────────────

def test_remove_s3_deletes_object_key(monkeypatch):
    fake = _FakeS3()
    _use_s3(monkeypatch, fake)

    storage.remove("/uploads/cms/2026/10/ab12-photo.png")

    (op, kwargs), = fake.calls
    assert op == "delete_object"
    assert kwargs["Bucket"] == "vigyanllm-frontend"
    assert kwargs["Key"] == "uploads/cms/2026/10/ab12-photo.png"


def test_remove_s3_failure_is_best_effort(monkeypatch):
    """DB cleanup must not be blocked by a storage hiccup (orphan beats 500)."""
    _use_s3(monkeypatch, _FakeS3(fail=True))

    storage.remove("/uploads/cms/2026/10/x.png")  # must not raise


def test_remove_ignores_external_and_invalid_urls(monkeypatch):
    fake = _FakeS3()
    _use_s3(monkeypatch, fake)

    storage.remove("https://example.com/not-ours.png")
    storage.remove("/assets/logo.png")
    storage.remove(None)

    assert fake.calls == []


def test_remove_local_deletes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "S3_BUCKET", "")
    monkeypatch.setattr(storage, "UPLOAD_DIR", str(tmp_path))
    target_dir = tmp_path / "2026" / "10"
    target_dir.mkdir(parents=True)
    target = target_dir / "x.png"
    target.write_bytes(b"1")

    storage.remove("/uploads/cms/2026/10/x.png")

    assert not target.exists()


def test_remove_local_ignores_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "S3_BUCKET", "")
    monkeypatch.setattr(storage, "UPLOAD_DIR", str(tmp_path))

    storage.remove("/uploads/cms/2026/10/nope.png")  # must not raise

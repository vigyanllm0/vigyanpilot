import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    email: str | None = None
    password: str | None = None
    token: str | None = None

class UserInfo(BaseModel):
    id: str
    email: str
    display_name: str | None = None
    role: str

class LoginResponse(BaseModel):
    token: str
    expires_at: str
    user: UserInfo | None = None

class AuthorInfo(BaseModel):
    display_name: str | None = None
    email: str

class PageListItem(BaseModel):
    id: str
    slug: str
    title: str
    description: str | None = None
    content_type: str = "page"
    status: str
    tags: str | None = None
    author: AuthorInfo
    published_at: datetime | None = None
    updated_at: datetime | None = None

class PageListResponse(BaseModel):
    pages: list[PageListItem]
    total: int
    limit: int
    offset: int

class PageDetail(BaseModel):
    id: str
    slug: str
    title: str
    description: str | None = None
    content_json: Any
    content_html: str | None = None
    hero_image: str | None = None
    meta_title: str | None = None
    tags: str | None = None
    publish_schedule_at: datetime | None = None
    status: str
    content_type: str = "page"
    author: AuthorInfo
    reviewer: AuthorInfo | None = None
    rejection_reason: str | None = None
    published_at: datetime | None = None
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class PageCreate(BaseModel):
    slug: str
    title: str
    description: str | None = None
    content_json: dict
    hero_image: str | None = None
    meta_title: str | None = None
    tags: str | None = None
    publish_schedule_at: datetime | None = None
    status: str = "draft"
    content_type: str = "page"
    change_note: str | None = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v):
        if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', v):
            raise ValueError("Slug must be URL-safe: lowercase letters, numbers, hyphens")
        if len(v) > 255:
            raise ValueError("Slug max 255 characters")
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        if len(v) < 1 or len(v) > 512:
            raise ValueError("Title must be 1-512 characters")
        return v

    @field_validator("content_json")
    @classmethod
    def validate_content_json(cls, v):
        if not isinstance(v, dict):
            raise ValueError("content_json must be a JSON object")
        if v.get("type") != "doc":
            raise ValueError("content_json must have type='doc'")
        if "content" not in v:
            raise ValueError("content_json must have a content array")
        return v

class PageUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    content_json: dict | None = None
    hero_image: str | None = None
    meta_title: str | None = None
    tags: str | None = None
    publish_schedule_at: datetime | None = None
    status: str | None = None
    content_type: str | None = None
    change_note: str | None = None

class PageCreateResponse(BaseModel):
    id: str
    slug: str
    status: str
    tags: str | None = None
    meta_title: str | None = None

class ReviewNoteCreate(BaseModel):
    note: str = Field(..., min_length=1, max_length=2048)

class ReviewNoteItem(BaseModel):
    id: str
    note: str
    author: AuthorInfo
    created_at: datetime | None = None

class RejectRequest(BaseModel):
    reason: str = Field(..., min_length=10, max_length=1024)
    change_note: str | None = None

class ReviewQueueItem(BaseModel):
    id: str
    slug: str
    title: str
    author: AuthorInfo
    submitted_at: datetime | None = None
    waiting_hours: float | None = None
    content_html: str | None = None

class ReviewQueueResponse(BaseModel):
    queue: list[ReviewQueueItem]
    total: int
    limit: int
    offset: int

class NotificationItem(BaseModel):
    id: str
    type: str
    message: str
    page_slug: str | None = None
    is_read: bool
    created_at: datetime | None = None

class RevisionItem(BaseModel):
    id: str
    change_note: str | None = None
    changed_by: AuthorInfo
    status_at_save: str
    created_at: datetime | None = None

class MediaItem(BaseModel):
    id: str
    filename: str
    original_name: str | None = None
    url: str
    mime_type: str
    media_type: str
    size_bytes: int
    width: int
    height: int
    alt_text: str | None = None
    caption: str | None = None
    uploaded_by: AuthorInfo | None = None
    created_at: datetime | None = None

class MediaUploadResponse(BaseModel):
    success: bool
    data: MediaItem

class MediaListResponse(BaseModel):
    items: list[MediaItem]
    total: int

class SettingItem(BaseModel):
    id: str
    key: str
    value: Any | None = None
    type: str
    updated_at: datetime | None = None

class SettingUpdate(BaseModel):
    value: Any | None = None
    type: str | None = None

class SettingListResponse(BaseModel):
    settings: list[SettingItem]

class BlockItem(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None = None
    content_json: Any
    content_html: str | None = None
    category: str
    created_by: AuthorInfo | None = None
    updated_at: datetime | None = None

class BlockCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None
    content_json: dict
    category: str = "custom"

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v):
        if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', v):
            raise ValueError("Slug must be URL-safe: lowercase letters, numbers, hyphens")
        if len(v) > 255:
            raise ValueError("Slug max 255 characters")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if len(v) < 1 or len(v) > 255:
            raise ValueError("Name must be 1-255 characters")
        return v

    @field_validator("content_json")
    @classmethod
    def validate_content_json(cls, v):
        if not isinstance(v, dict):
            raise ValueError("content_json must be a JSON object")
        if v.get("type") != "doc":
            raise ValueError("content_json must have type='doc'")
        if "content" not in v:
            raise ValueError("content_json must have a content array")
        return v

class BlockUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    content_json: dict | None = None
    category: str | None = None

class BlockListResponse(BaseModel):
    blocks: list[BlockItem]
    total: int

class UserCreate(BaseModel):
    email: str
    password: str
    display_name: str | None = None
    role: str = "editor"

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', v):
            raise ValueError("Invalid email address")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        # Delegate to the shared VigyanLLM password policy (12 characters,
        # character classes, common-password blocklist, sequence/repeat
        # guards) rather than a weaker local check — admin and editor accounts
        # must not be able to set a password the main app would reject.
        # Imported lazily so this module keeps no import-time dependency.
        from primerforge.security import validate_password as _policy
        ok, err = _policy(v)
        if not ok:
            raise ValueError(err)
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        allowed = {"admin", "editor", "viewer"}
        if v not in allowed:
            raise ValueError(f"Role must be one of: {', '.join(sorted(allowed))}")
        return v

class UserListItem(BaseModel):
    id: str
    email: str
    display_name: str | None = None
    role: str
    last_login_at: datetime | None = None
    created_at: datetime | None = None

class UserListResponse(BaseModel):
    users: list[UserListItem]

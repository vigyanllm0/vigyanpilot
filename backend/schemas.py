from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any
from datetime import datetime
import re

class LoginRequest(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None

class UserInfo(BaseModel):
    id: str
    email: str
    display_name: Optional[str] = None
    role: str

class LoginResponse(BaseModel):
    token: str
    expires_at: str
    user: Optional[UserInfo] = None

class AuthorInfo(BaseModel):
    display_name: Optional[str] = None
    email: str

class PageListItem(BaseModel):
    id: str
    slug: str
    title: str
    description: Optional[str] = None
    content_type: str = "page"
    status: str
    author: AuthorInfo
    published_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class PageListResponse(BaseModel):
    pages: list[PageListItem]
    total: int
    limit: int
    offset: int

class PageDetail(BaseModel):
    id: str
    slug: str
    title: str
    description: Optional[str] = None
    content_json: Any
    content_html: Optional[str] = None
    hero_image: Optional[str] = None
    status: str
    content_type: str = "page"
    author: AuthorInfo
    reviewer: Optional[AuthorInfo] = None
    rejection_reason: Optional[str] = None
    published_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class PageCreate(BaseModel):
    slug: str
    title: str
    description: Optional[str] = None
    content_json: dict
    hero_image: Optional[str] = None
    status: str = "draft"
    content_type: str = "page"
    change_note: Optional[str] = None

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
    title: Optional[str] = None
    description: Optional[str] = None
    content_json: Optional[dict] = None
    hero_image: Optional[str] = None
    status: Optional[str] = None
    content_type: Optional[str] = None
    change_note: Optional[str] = None

class PageCreateResponse(BaseModel):
    id: str
    slug: str
    status: str

class ReviewNoteCreate(BaseModel):
    note: str = Field(..., min_length=1, max_length=2048)

class ReviewNoteItem(BaseModel):
    id: str
    note: str
    author: AuthorInfo
    created_at: Optional[datetime] = None

class RejectRequest(BaseModel):
    reason: str = Field(..., min_length=10, max_length=1024)
    change_note: Optional[str] = None

class ReviewQueueItem(BaseModel):
    id: str
    slug: str
    title: str
    author: AuthorInfo
    submitted_at: Optional[datetime] = None
    waiting_hours: Optional[float] = None
    content_html: Optional[str] = None

class ReviewQueueResponse(BaseModel):
    queue: list[ReviewQueueItem]
    total: int
    limit: int
    offset: int

class NotificationItem(BaseModel):
    id: str
    type: str
    message: str
    page_slug: Optional[str] = None
    is_read: bool
    created_at: Optional[datetime] = None

class RevisionItem(BaseModel):
    id: str
    change_note: Optional[str] = None
    changed_by: AuthorInfo
    status_at_save: str
    created_at: Optional[datetime] = None

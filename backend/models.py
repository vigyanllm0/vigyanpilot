from sqlalchemy import create_engine, Column, String, Text, Boolean, DateTime, ForeignKey, UUID, Integer, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

def gen_uuid():
    return str(uuid.uuid4())

class AdminUser(Base):
    __tablename__ = "admin_users"
    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(255))
    role = Column(String(20), nullable=False, default="editor")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True))

    pages = relationship("CMSPage", back_populates="author", foreign_keys="CMSPage.author_id")
    reviewed_pages = relationship("CMSPage", back_populates="reviewer", foreign_keys="CMSPage.reviewer_id")

class CMSPage(Base):
    __tablename__ = "cms_pages"
    id = Column(String, primary_key=True, default=gen_uuid)
    slug = Column(String(255), unique=True, nullable=False)
    title = Column(String(512), nullable=False)
    description = Column(String(1024))
    content_json = Column(JSONB, nullable=False)
    content_html = Column(Text)
    hero_image = Column(String(512))
    status = Column(String(20), nullable=False, default="draft")
    author_id = Column(String, ForeignKey("admin_users.id"), nullable=False)
    reviewer_id = Column(String, ForeignKey("admin_users.id"))
    published_at = Column(DateTime(timezone=True))
    submitted_at = Column(DateTime(timezone=True))
    reviewed_at = Column(DateTime(timezone=True))
    rejection_reason = Column(String(1024))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    author = relationship("AdminUser", back_populates="pages", foreign_keys=[author_id])
    reviewer = relationship("AdminUser", back_populates="reviewed_pages", foreign_keys=[reviewer_id])
    revisions = relationship("CMSPageRevision", back_populates="page", cascade="all, delete-orphan")
    review_notes = relationship("CMSReviewNote", back_populates="page", cascade="all, delete-orphan")
    notifications = relationship("CMSNotification", back_populates="page", cascade="all, delete-orphan")

class CMSPageRevision(Base):
    __tablename__ = "cms_page_revisions"
    id = Column(String, primary_key=True, default=gen_uuid)
    page_id = Column(String, ForeignKey("cms_pages.id", ondelete="CASCADE"), nullable=False)
    content_json = Column(JSONB, nullable=False)
    content_html = Column(Text)
    changed_by = Column(String, ForeignKey("admin_users.id"), nullable=False)
    change_note = Column(String(255))
    status_at_save = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    page = relationship("CMSPage", back_populates="revisions")

class CMSReviewNote(Base):
    __tablename__ = "cms_review_notes"
    id = Column(String, primary_key=True, default=gen_uuid)
    page_id = Column(String, ForeignKey("cms_pages.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(String, ForeignKey("admin_users.id"), nullable=False)
    note = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    page = relationship("CMSPage", back_populates="review_notes")
    author = relationship("AdminUser")

class CMSNotification(Base):
    __tablename__ = "cms_notifications"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False)
    page_id = Column(String, ForeignKey("cms_pages.id", ondelete="SET NULL"))
    type = Column(String(30), nullable=False)
    message = Column(String(512), nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    page = relationship("CMSPage", back_populates="notifications")

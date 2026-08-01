from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import CMSPage, CMSPageView, AdminUser
from deps import get_current_user
from datetime import datetime, timezone, timedelta

router = APIRouter(tags=["stats"])

@router.get("/api/stats/public")
def public_stats():
    return {
        "designs_runs": 2847,
        "researchers": 1250,
        "validated_primers": 14230,
        "partner_organizations": 18,
    }

@router.get("/api/v1/cms/stats/dashboard")
def dashboard_stats(db: Session = Depends(get_db), user: AdminUser = Depends(get_current_user)):
    total_pages = db.query(func.count(CMSPage.id)).scalar() or 0
    published = db.query(func.count(CMSPage.id)).filter(CMSPage.status == "published").scalar() or 0
    drafts = db.query(func.count(CMSPage.id)).filter(CMSPage.status == "draft").scalar() or 0
    total_views = db.query(func.count(CMSPageView.id)).scalar() or 0
    authors = db.query(func.count(AdminUser.id)).scalar() or 0
    return {
        "total_pages": total_pages,
        "published": published,
        "drafts": drafts,
        "total_views": total_views,
        "authors": authors,
    }


@router.get("/api/v1/cms/stats/analytics")
def analytics_stats(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    user: AdminUser = Depends(get_current_user),
):
    """
    Advanced analytics for the CMS dashboard.

    Returns real per-page traffic data with numbers and timestamps:
      - totals: total / today / 7d / 30d views, unique pages viewed
      - timeline: views bucketed by day (for charts)
      - top_pages: per-page view counts + last-viewed timestamps
      - recent_views: the most recent individual view events with timestamps
      - sources: breakdown by day of week / hour (activity heat) if needed
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    # ── Totals ────────────────────────────────────────────────────────────
    total_views = db.query(func.count(CMSPageView.id)).scalar() or 0
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    views_today = (
        db.query(func.count(CMSPageView.id))
        .filter(CMSPageView.viewed_at >= today_start)
        .scalar() or 0
    )
    views_7d = (
        db.query(func.count(CMSPageView.id))
        .filter(CMSPageView.viewed_at >= now - timedelta(days=7))
        .scalar() or 0
    )
    views_30d = (
        db.query(func.count(CMSPageView.id))
        .filter(CMSPageView.viewed_at >= now - timedelta(days=30))
        .scalar() or 0
    )
    unique_pages = (
        db.query(func.count(func.distinct(CMSPageView.page_id)))
        .filter(CMSPageView.viewed_at >= cutoff)
        .scalar() or 0
    )

    # ── Timeline (per-day buckets for charts) ─────────────────────────────
    rows = (
        db.query(
            func.date(CMSPageView.viewed_at).label("day"),
            func.count(CMSPageView.id),
        )
        .filter(CMSPageView.viewed_at >= cutoff)
        .group_by(func.date(CMSPageView.viewed_at))
        .order_by(func.date(CMSPageView.viewed_at))
        .all()
    )
    views_by_day = {str(day): cnt for day, cnt in rows}

    timeline = []
    for offset in range(days - 1, -1, -1):
        day = (now - timedelta(days=offset)).date()
        timeline.append({
            "date": day.isoformat(),
            "views": views_by_day.get(day.isoformat(), 0),
        })

    # ── Top pages (per-page traffic with numbers + last viewed) ───────────
    top_rows = (
        db.query(
            CMSPageView.page_id,
            func.count(CMSPageView.id).label("cnt"),
            func.max(CMSPageView.viewed_at).label("last_viewed"),
        )
        .filter(CMSPageView.viewed_at >= cutoff)
        .group_by(CMSPageView.page_id)
        .order_by(func.count(CMSPageView.id).desc())
        .limit(15)
        .all()
    )
    pages_map = {
        p.id: p for p in db.query(CMSPage).filter(CMSPage.id.in_([r[0] for r in top_rows])).all()
    } if top_rows else {}
    top_pages = []
    for page_id, cnt, last_viewed in top_rows:
        p = pages_map.get(page_id)
        top_pages.append({
            "slug": p.slug if p else page_id,
            "title": p.title if p else "Unknown",
            "content_type": p.content_type if p else "page",
            "views": cnt,
            "last_viewed_at": last_viewed.isoformat() if last_viewed else None,
        })

    # ── Recent individual view events (with timestamps) ───────────────────
    recent_rows = (
        db.query(CMSPageView)
        .filter(CMSPageView.viewed_at >= cutoff)
        .order_by(CMSPageView.viewed_at.desc())
        .limit(20)
        .all()
    )
    recent_views = []
    for v in recent_rows:
        p = pages_map.get(v.page_id) if pages_map else None
        recent_views.append({
            "slug": p.slug if p else v.page_id,
            "title": p.title if p else None,
            "viewed_at": v.viewed_at.isoformat() if v.viewed_at else None,
            "ip": v.ip_address,
            "user_agent": v.user_agent,
        })

    return {
        "days": days,
        "totals": {
            "total_views": total_views,
            "views_today": views_today,
            "views_7d": views_7d,
            "views_30d": views_30d,
            "unique_pages_viewed": unique_pages,
        },
        "timeline": timeline,
        "top_pages": top_pages,
        "recent_views": recent_views,
        "generated_at": now.isoformat(),
    }

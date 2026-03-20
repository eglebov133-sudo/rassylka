from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Bid, Supplier, DistributionBatch, DistributionLog, BidStatus, BatchStatus, EmailStatus
from backend.schemas import DashboardStats, RecentBidItem

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    total_bids = (await db.execute(select(func.count(Bid.id)))).scalar() or 0

    active_mailings = (await db.execute(
        select(func.count(Bid.id)).where(Bid.status == BidStatus.DISTRIBUTING.value)
    )).scalar() or 0

    suppliers_notified = (await db.execute(
        select(func.count(func.distinct(DistributionLog.supplier_id)))
        .where(DistributionLog.email_status == EmailStatus.SENT.value)
    )).scalar() or 0

    total_suppliers = (await db.execute(
        select(func.count(Supplier.id)).where(Supplier.active == True)
    )).scalar() or 0

    total_sent = (await db.execute(
        select(func.count(DistributionLog.id))
        .where(DistributionLog.email_status == EmailStatus.SENT.value)
    )).scalar() or 0

    total_responded = (await db.execute(
        select(func.count(DistributionLog.id))
        .where(DistributionLog.email_status == EmailStatus.RESPONDED.value)
    )).scalar() or 0

    response_rate = (total_responded / total_sent * 100) if total_sent > 0 else 0.0

    return DashboardStats(
        total_bids=total_bids,
        active_mailings=active_mailings,
        suppliers_notified=suppliers_notified,
        total_suppliers=total_suppliers,
        response_rate=round(response_rate, 1),
    )


@router.get("/recent", response_model=list[RecentBidItem])
async def get_recent_bids(limit: int = 10, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Bid).order_by(Bid.parsed_at.desc()).limit(limit)
    )
    bids = result.scalars().all()

    items = []
    for bid in bids:
        # Get the latest batch for this bid
        batch_result = await db.execute(
            select(DistributionBatch)
            .where(DistributionBatch.bid_id == bid.id)
            .order_by(DistributionBatch.batch_number.desc())
            .limit(1)
        )
        latest_batch = batch_result.scalar_one_or_none()

        items.append(RecentBidItem(
            id=bid.id,
            source_id=bid.source_id,
            name=bid.name,
            spare_part_type=bid.spare_part_type,
            status=bid.status,
            parsed_at=bid.parsed_at,
            batch_status=latest_batch.status if latest_batch else None,
            batch_number=latest_batch.batch_number if latest_batch else 0,
        ))

    return items


@router.get("/analytics")
async def get_analytics(db: AsyncSession = Depends(get_db)):
    """Comprehensive analytics: weekly/monthly stats, top categories, top suppliers, daily chart, spam alert."""
    import datetime as dt
    now = dt.datetime.utcnow()
    week_ago = now - dt.timedelta(days=7)
    two_weeks_ago = now - dt.timedelta(days=14)
    month_ago = now - dt.timedelta(days=30)

    # ── Bids processed ──
    bids_week = (await db.execute(
        select(func.count(Bid.id)).where(Bid.parsed_at >= week_ago)
    )).scalar() or 0

    bids_month = (await db.execute(
        select(func.count(Bid.id)).where(Bid.parsed_at >= month_ago)
    )).scalar() or 0

    # ── Emails sent / clicked ──
    sent_total = (await db.execute(
        select(func.count(DistributionLog.id)).where(DistributionLog.email_status == EmailStatus.SENT.value)
    )).scalar() or 0

    clicked_total = (await db.execute(
        select(func.count(DistributionLog.id)).where(DistributionLog.clicked_at.isnot(None))
    )).scalar() or 0

    failed_total = (await db.execute(
        select(func.count(DistributionLog.id)).where(DistributionLog.email_status == EmailStatus.FAILED.value)
    )).scalar() or 0

    click_rate = round((clicked_total / sent_total * 100), 1) if sent_total > 0 else 0.0

    # ── This week vs previous week click rate (spam alert) ──
    sent_this_week = (await db.execute(
        select(func.count(DistributionLog.id)).where(
            and_(DistributionLog.sent_at >= week_ago, DistributionLog.email_status == EmailStatus.SENT.value)
        )
    )).scalar() or 0

    clicked_this_week = (await db.execute(
        select(func.count(DistributionLog.id)).where(
            and_(DistributionLog.clicked_at >= week_ago, DistributionLog.clicked_at.isnot(None))
        )
    )).scalar() or 0

    sent_prev_week = (await db.execute(
        select(func.count(DistributionLog.id)).where(
            and_(DistributionLog.sent_at >= two_weeks_ago, DistributionLog.sent_at < week_ago,
                 DistributionLog.email_status == EmailStatus.SENT.value)
        )
    )).scalar() or 0

    clicked_prev_week = (await db.execute(
        select(func.count(DistributionLog.id)).where(
            and_(DistributionLog.clicked_at >= two_weeks_ago, DistributionLog.clicked_at < week_ago,
                 DistributionLog.clicked_at.isnot(None))
        )
    )).scalar() or 0

    rate_this = (clicked_this_week / sent_this_week * 100) if sent_this_week > 0 else 0
    rate_prev = (clicked_prev_week / sent_prev_week * 100) if sent_prev_week > 0 else 0
    spam_alert = rate_prev > 0 and rate_this < rate_prev * 0.5

    # ── Top categories ──
    cat_result = await db.execute(
        select(Bid.spare_part_type, func.count(Bid.id).label("cnt"))
        .where(Bid.spare_part_type != "")
        .group_by(Bid.spare_part_type)
        .order_by(func.count(Bid.id).desc())
        .limit(5)
    )
    top_categories = [{"name": r[0] or "Без категории", "count": r[1]} for r in cat_result.fetchall()]

    # ── Top suppliers by clicks ──
    sup_result = await db.execute(
        select(Supplier.company_name, func.count(DistributionLog.id).label("clicks"))
        .join(DistributionLog, DistributionLog.supplier_id == Supplier.id)
        .where(DistributionLog.clicked_at.isnot(None))
        .group_by(Supplier.id)
        .order_by(func.count(DistributionLog.id).desc())
        .limit(5)
    )
    top_suppliers = [{"name": r[0], "clicks": r[1]} for r in sup_result.fetchall()]

    # ── Daily stats (last 14 days) ──
    daily_sent = await db.execute(
        select(func.date(DistributionLog.sent_at).label("day"), func.count(DistributionLog.id))
        .where(and_(DistributionLog.sent_at >= two_weeks_ago, DistributionLog.email_status == EmailStatus.SENT.value))
        .group_by(func.date(DistributionLog.sent_at))
        .order_by(func.date(DistributionLog.sent_at))
    )
    daily_clicked = await db.execute(
        select(func.date(DistributionLog.clicked_at).label("day"), func.count(DistributionLog.id))
        .where(and_(DistributionLog.clicked_at >= two_weeks_ago, DistributionLog.clicked_at.isnot(None)))
        .group_by(func.date(DistributionLog.clicked_at))
        .order_by(func.date(DistributionLog.clicked_at))
    )

    sent_by_day = {str(r[0]): r[1] for r in daily_sent.fetchall()}
    clicked_by_day = {str(r[0]): r[1] for r in daily_clicked.fetchall()}

    # Build 14-day array
    daily_chart = []
    for i in range(13, -1, -1):
        day = (now - dt.timedelta(days=i)).strftime("%Y-%m-%d")
        daily_chart.append({
            "date": day,
            "sent": sent_by_day.get(day, 0),
            "clicked": clicked_by_day.get(day, 0),
        })

    return {
        "bids_week": bids_week,
        "bids_month": bids_month,
        "sent_total": sent_total,
        "clicked_total": clicked_total,
        "failed_total": failed_total,
        "click_rate": click_rate,
        "spam_alert": spam_alert,
        "rate_this_week": round(rate_this, 1),
        "rate_prev_week": round(rate_prev, 1),
        "top_categories": top_categories,
        "top_suppliers": top_suppliers,
        "daily_chart": daily_chart,
    }


@router.get("/clicks")
async def get_click_report(
    page: int = 1,
    page_size: int = 50,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
):
    """Detailed click report — who clicked, on which bid, when."""
    import datetime as dt
    cutoff = dt.datetime.utcnow() - dt.timedelta(days=days)

    # Total clicks
    total_clicks = (await db.execute(
        select(func.count(DistributionLog.id))
        .where(and_(
            DistributionLog.clicked_at.isnot(None),
            DistributionLog.clicked_at >= cutoff,
        ))
    )).scalar() or 0

    # Unique suppliers who clicked
    unique_clickers = (await db.execute(
        select(func.count(func.distinct(DistributionLog.supplier_id)))
        .where(and_(
            DistributionLog.clicked_at.isnot(None),
            DistributionLog.clicked_at >= cutoff,
        ))
    )).scalar() or 0

    # Total sent in period
    total_sent = (await db.execute(
        select(func.count(DistributionLog.id))
        .where(and_(
            DistributionLog.sent_at.isnot(None),
            DistributionLog.sent_at >= cutoff,
        ))
    )).scalar() or 0

    click_rate = round((total_clicks / total_sent * 100), 1) if total_sent > 0 else 0.0

    # Detailed click entries
    click_result = await db.execute(
        select(DistributionLog, Supplier, Bid)
        .join(Supplier, Supplier.id == DistributionLog.supplier_id)
        .join(DistributionBatch, DistributionBatch.id == DistributionLog.batch_id)
        .join(Bid, Bid.id == DistributionBatch.bid_id)
        .where(and_(
            DistributionLog.clicked_at.isnot(None),
            DistributionLog.clicked_at >= cutoff,
        ))
        .order_by(DistributionLog.clicked_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    items = []
    for log, supplier, bid in click_result.all():
        time_to_click = None
        if log.sent_at and log.clicked_at:
            delta = log.clicked_at - log.sent_at
            time_to_click = int(delta.total_seconds())

        items.append({
            "id": log.id,
            "supplier_name": supplier.company_name,
            "supplier_email": supplier.email,
            "bid_name": bid.name,
            "bid_source_id": bid.source_id,
            "bid_id": bid.id,
            "clicked_at": log.clicked_at.isoformat() if log.clicked_at else None,
            "sent_at": log.sent_at.isoformat() if log.sent_at else None,
            "time_to_click_seconds": time_to_click,
        })

    return {
        "items": items,
        "total_clicks": total_clicks,
        "unique_clickers": unique_clickers,
        "total_sent": total_sent,
        "click_rate": click_rate,
        "page": page,
        "page_size": page_size,
    }

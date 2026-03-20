import asyncio
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Bid, DistributionBatch
from backend.schemas import BidResponse, BidListResponse
from backend.services.bid_parser import run_parse_cycle

router = APIRouter(prefix="/api/bids", tags=["bids"])


@router.get("", response_model=BidListResponse)
async def list_bids(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    search: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Bid)
    count_query = select(func.count(Bid.id))

    if status:
        query = query.where(Bid.status == status)
        count_query = count_query.where(Bid.status == status)

    if search:
        search_filter = Bid.name.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Bid.parsed_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    bids = result.scalars().all()

    items = []
    for bid in bids:
        batch_count_result = await db.execute(
            select(func.count(DistributionBatch.id)).where(DistributionBatch.bid_id == bid.id)
        )
        batch_count = batch_count_result.scalar() or 0

        items.append(BidResponse(
            id=bid.id,
            source_id=bid.source_id,
            name=bid.name,
            brand=bid.brand,
            model=bid.model,
            year=bid.year,
            spare_part_type=bid.spare_part_type,
            count=bid.count,
            delivery_place=bid.delivery_place,
            description=bid.description,
            buyer_name=bid.buyer_name,
            status=bid.status,
            validity_days=bid.validity_days,
            source_url=bid.source_url,
            created_at=bid.created_at,
            parsed_at=bid.parsed_at,
            batch_count=batch_count,
        ))

    return BidListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{bid_id}", response_model=BidResponse)
async def get_bid(bid_id: int, db: AsyncSession = Depends(get_db)):
    bid = await db.get(Bid, bid_id)
    if not bid:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    batch_count_result = await db.execute(
        select(func.count(DistributionBatch.id)).where(DistributionBatch.bid_id == bid.id)
    )
    batch_count = batch_count_result.scalar() or 0

    return BidResponse(
        id=bid.id,
        source_id=bid.source_id,
        name=bid.name,
        brand=bid.brand,
        model=bid.model,
        year=bid.year,
        spare_part_type=bid.spare_part_type,
        count=bid.count,
        delivery_place=bid.delivery_place,
        description=bid.description,
        buyer_name=bid.buyer_name,
        status=bid.status,
        validity_days=bid.validity_days,
        source_url=bid.source_url,
        created_at=bid.created_at,
        parsed_at=bid.parsed_at,
        batch_count=batch_count,
    )


@router.post("/parse")
async def trigger_parse():
    """Manually trigger a parse cycle."""
    count = await run_parse_cycle()
    return {"message": f"Парсинг завершён. Новых заявок: {count}", "new_bids": count}


@router.get("/{bid_id}/logs")
async def get_bid_logs(bid_id: int, db: AsyncSession = Depends(get_db)):
    """Get distribution logs for a specific bid."""
    from backend.models import DistributionLog, DistributionBatch, Supplier

    bid = await db.get(Bid, bid_id)
    if not bid:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    # Get all batches for this bid
    batch_result = await db.execute(
        select(DistributionBatch).where(DistributionBatch.bid_id == bid_id).order_by(DistributionBatch.batch_number)
    )
    batches = batch_result.scalars().all()

    logs = []
    for batch in batches:
        log_result = await db.execute(
            select(DistributionLog, Supplier)
            .join(Supplier, Supplier.id == DistributionLog.supplier_id)
            .where(DistributionLog.batch_id == batch.id)
            .order_by(DistributionLog.sent_at)
        )
        for log, supplier in log_result.all():
            logs.append({
                "id": log.id,
                "batch_number": batch.batch_number,
                "batch_status": batch.status,
                "supplier_name": supplier.company_name,
                "supplier_email": supplier.email,
                "supplier_website": supplier.website or "",
                "email_status": log.email_status,
                "sent_at": log.sent_at.isoformat() if log.sent_at else None,
                "opened_at": log.opened_at.isoformat() if log.opened_at else None,
                "clicked_at": log.clicked_at.isoformat() if log.clicked_at else None,
                "error_message": log.error_message or "",
            })

    return {
        "bid": {
            "id": bid.id,
            "source_id": bid.source_id,
            "name": bid.name,
            "source_url": bid.source_url,
            "status": bid.status,
        },
        "logs": logs,
        "total": len(logs),
    }


PRIORITY_LABELS = {
    1: "P1 — Деталь по номеру + в наличии + рядом",
    2: "P2 — Деталь по номеру + в наличии",
    3: "P3 — Тип детали + рядом с заказчиком",
    4: "P4 — Тип детали + любой регион",
    5: "P5 — Модель техники + в наличии + рядом",
    6: "P6 — Модель техники + в наличии",
    7: "P7 — Модель техники + рядом",
    8: "P8 — Модель техники + любой регион",
    9: "Совпадение по ключевым словам",
}

PRIORITY_COLORS = {
    1: "#22c55e", 2: "#84cc16", 3: "#eab308", 4: "#f97316",
    5: "#06b6d4", 6: "#3b82f6", 7: "#8b5cf6", 8: "#a855f7",
    9: "#6b7280",
}


@router.get("/{bid_id}/search-results")
async def get_bid_search_results(bid_id: int, db: AsyncSession = Depends(get_db)):
    """Get all suppliers found for a bid, ordered by search priority."""
    from backend.models import DistributionLog, DistributionBatch, Supplier

    bid = await db.get(Bid, bid_id)
    if not bid:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    # Get all logs for this bid with supplier info
    log_result = await db.execute(
        select(DistributionLog, Supplier, DistributionBatch.batch_number)
        .join(Supplier, Supplier.id == DistributionLog.supplier_id)
        .join(DistributionBatch, DistributionBatch.id == DistributionLog.batch_id)
        .where(DistributionBatch.bid_id == bid_id)
        .order_by(DistributionLog.search_priority.asc(), DistributionLog.sent_at.asc())
    )

    results = []
    for log, supplier, batch_num in log_result.all():
        priority = log.search_priority or 9
        results.append({
            "supplier_id": supplier.id,
            "company_name": supplier.company_name,
            "email": supplier.email,
            "phone": supplier.phone or "",
            "website": supplier.website or "",
            "categories": supplier.categories or [],
            "regions": supplier.regions or [],
            "description": supplier.description or "",
            "source": supplier.source or "manual",
            "priority": priority,
            "priority_label": PRIORITY_LABELS.get(priority, f"P{priority}"),
            "priority_color": PRIORITY_COLORS.get(priority, "#6b7280"),
            "email_status": log.email_status,
            "sent_at": log.sent_at.isoformat() if log.sent_at else None,
            "clicked_at": log.clicked_at.isoformat() if log.clicked_at else None,
            "batch_number": batch_num,
        })

    # Extract part number for display
    from backend.services.supplier_ai import _extract_part_number
    part_number = _extract_part_number(bid.name)

    return {
        "bid": {
            "id": bid.id,
            "source_id": bid.source_id,
            "name": bid.name,
            "brand": bid.brand,
            "model": bid.model,
            "year": bid.year,
            "spare_part_type": bid.spare_part_type,
            "delivery_place": bid.delivery_place,
            "status": bid.status,
            "source_url": bid.source_url,
            "part_number": part_number,
        },
        "results": results,
        "total": len(results),
        "priority_legend": [
            {"priority": k, "label": v, "color": PRIORITY_COLORS.get(k, "#6b7280")}
            for k, v in PRIORITY_LABELS.items()
        ],
    }

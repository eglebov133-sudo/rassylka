import os
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.database import get_db
from backend.models import DistributionLog, DistributionBatch, Bid, Supplier
from backend.schemas import LogEntry, LogListResponse, SystemStatus
from backend.services.bid_parser import parser_state
from backend.services.mail_engine import distributor_state

router = APIRouter(prefix="/api", tags=["logs"])


@router.get("/logs", response_model=LogListResponse)
async def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    status: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(DistributionLog)
        .join(DistributionBatch, DistributionBatch.id == DistributionLog.batch_id)
        .join(Bid, Bid.id == DistributionBatch.bid_id)
        .join(Supplier, Supplier.id == DistributionLog.supplier_id)
    )

    count_query = (
        select(func.count(DistributionLog.id))
        .join(DistributionBatch, DistributionBatch.id == DistributionLog.batch_id)
    )

    if status:
        query = query.where(DistributionLog.email_status == status)
        count_query = count_query.where(DistributionLog.email_status == status)

    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(DistributionLog.id.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    items = []
    for log in logs:
        batch = await db.get(DistributionBatch, log.batch_id)
        bid = await db.get(Bid, batch.bid_id) if batch else None
        supplier = await db.get(Supplier, log.supplier_id)

        items.append(LogEntry(
            id=log.id,
            bid_id=bid.id if bid else 0,
            bid_name=bid.name if bid else "—",
            bid_source_id=bid.source_id if bid else 0,
            supplier_name=supplier.company_name if supplier else "—",
            supplier_email=supplier.email if supplier else "—",
            email_status=log.email_status,
            batch_number=batch.batch_number if batch else 0,
            sent_at=log.sent_at,
            clicked_at=log.clicked_at,
            error_message=log.error_message or "",
        ))

    return LogListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/system/status", response_model=SystemStatus)
async def get_system_status():
    return SystemStatus(
        parser_running=parser_state.get("running", False),
        distributor_running=distributor_state.get("running", False),
        last_parse_at=parser_state.get("last_run"),
        last_distribution_at=distributor_state.get("last_run"),
        smtp_configured=bool(os.getenv("SMTP_USER")),
        openrouter_configured=bool(os.getenv("OPENROUTER_API_KEY")),
    )

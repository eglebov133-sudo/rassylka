"""
Telegram Mailing — API Router.
Hard safety limits to prevent Telegram account bans.
"""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, HTTPException, Body, UploadFile, File
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import TgCampaign, TgCampaignRecipient, TgCampaignStatus

import os

logger = logging.getLogger("bidroute.telegram")
router = APIRouter(prefix="/api/telegram", tags=["telegram"])

# ═══════════════════════════════════════════════════
#  HARD SAFETY LIMITS (cannot be overridden by user)
# ═══════════════════════════════════════════════════
TG_MIN_DELAY = 35          # Minimum seconds between messages
TG_MAX_DELAY = 300         # Maximum delay
TG_DEFAULT_DELAY = 60      # Default delay for new campaigns (safe for new accounts)
TG_DAILY_LIMIT = 15        # Max messages per day — safe for NEW accounts (< 1 month)
TG_MAX_RECIPIENTS = 50     # Max recipients per campaign


# ── Status ──

@router.get("/status")
async def tg_status():
    from backend.services.telegram_sender import get_tg_status
    return await get_tg_status()


@router.post("/accounts/rename")
async def rename_tg_account(payload: dict = Body(...)):
    """Rename a Telegram account's first/last name."""
    from backend.services.telegram_sender import rename_account
    session_name = payload.get("session_name", "")
    first_name = payload.get("first_name", "").strip()
    last_name = payload.get("last_name", "").strip()

    if not session_name:
        raise HTTPException(status_code=400, detail="session_name обязателен")
    if not first_name:
        raise HTTPException(status_code=400, detail="Имя не может быть пустым")

    try:
        result = await rename_account(session_name, first_name, last_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Campaigns CRUD ──

@router.get("/campaigns")
async def list_tg_campaigns(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(TgCampaign)
    count_query = select(func.count(TgCampaign.id))

    if status:
        query = query.where(TgCampaign.status == status)
        count_query = count_query.where(TgCampaign.status == status)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(TgCampaign.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    campaigns = result.scalars().all()

    items = []
    for c in campaigns:
        progress = 0
        if c.total_recipients > 0:
            progress = round((c.sent_count + c.failed_count) / c.total_recipients * 100)
        items.append({
            "id": c.id,
            "name": c.name,
            "message_text": c.message_text[:200] if c.message_text else "",
            "source_channel": c.source_channel,
            "status": c.status,
            "delay_seconds": c.delay_seconds,
            "image_path": c.image_path or "",
            "total_recipients": c.total_recipients,
            "sent_count": c.sent_count,
            "failed_count": c.failed_count,
            "progress": progress,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "started_at": c.started_at.isoformat() if c.started_at else None,
            "completed_at": c.completed_at.isoformat() if c.completed_at else None,
        })

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/campaigns")
async def create_tg_campaign(data: dict = Body(...), db: AsyncSession = Depends(get_db)):
    name = data.get("name", "Без названия")
    message_text = data.get("message_text", "")
    source_channel = data.get("source_channel", "")
    delay_seconds = max(TG_MIN_DELAY, min(TG_MAX_DELAY, data.get("delay_seconds", TG_DEFAULT_DELAY)))

    campaign = TgCampaign(
        name=name,
        message_text=message_text,
        source_channel=source_channel,
        delay_seconds=delay_seconds,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return {"id": campaign.id, "message": "TG-кампания создана"}


@router.get("/campaigns/{campaign_id}")
async def get_tg_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(TgCampaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="TG-кампания не найдена")

    recip_result = await db.execute(
        select(TgCampaignRecipient)
        .where(TgCampaignRecipient.campaign_id == campaign_id)
        .order_by(TgCampaignRecipient.id)
    )
    recipients = recip_result.scalars().all()

    stats = {"pending": 0, "sent": 0, "failed": 0, "blocked": 0}
    for r in recipients:
        stats[r.status] = stats.get(r.status, 0) + 1

    return {
        "id": campaign.id,
        "name": campaign.name,
        "message_text": campaign.message_text,
        "source_channel": campaign.source_channel,
        "status": campaign.status,
        "delay_seconds": campaign.delay_seconds,
        "image_path": campaign.image_path or "",
        "total_recipients": campaign.total_recipients,
        "sent_count": campaign.sent_count,
        "failed_count": campaign.failed_count,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
        "started_at": campaign.started_at.isoformat() if campaign.started_at else None,
        "completed_at": campaign.completed_at.isoformat() if campaign.completed_at else None,
        "stats": stats,
        "recipients": [
            {
                "id": r.id,
                "tg_user_id": r.tg_user_id,
                "username": r.username,
                "first_name": r.first_name,
                "status": r.status,
                "error_message": r.error_message or "",
                "sent_at": r.sent_at.isoformat() if r.sent_at else None,
            }
            for r in recipients
        ],
    }


@router.put("/campaigns/{campaign_id}")
async def update_tg_campaign(campaign_id: int, data: dict = Body(...), db: AsyncSession = Depends(get_db)):
    campaign = await db.get(TgCampaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="TG-кампания не найдена")
    if campaign.status != TgCampaignStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="Можно редактировать только черновик")

    for field in ("name", "message_text", "source_channel", "delay_seconds"):
        if field in data:
            val = data[field]
            if field == "delay_seconds":
                val = max(TG_MIN_DELAY, min(TG_MAX_DELAY, val))
            setattr(campaign, field, val)

    await db.commit()
    return {"message": "TG-кампания обновлена"}


@router.delete("/campaigns/{campaign_id}")
async def delete_tg_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(TgCampaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="TG-кампания не найдена")
    if campaign.status == TgCampaignStatus.SENDING.value:
        raise HTTPException(status_code=400, detail="Нельзя удалить активную рассылку")

    await db.delete(campaign)
    await db.commit()
    return {"message": "TG-кампания удалена"}


# ── Fetch Members ──

@router.post("/campaigns/{campaign_id}/fetch-members")
async def fetch_members(campaign_id: int, db: AsyncSession = Depends(get_db)):
    """Fetch channel members and add as recipients."""
    from backend.services.telegram_sender import fetch_channel_members

    campaign = await db.get(TgCampaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="TG-кампания не найдена")
    if not campaign.source_channel:
        raise HTTPException(status_code=400, detail="Не указан канал-источник")

    try:
        members = await fetch_channel_members(campaign.source_channel)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Remove old recipients
    await db.execute(
        delete(TgCampaignRecipient).where(TgCampaignRecipient.campaign_id == campaign_id)
    )

    # Add new
    added = 0
    for m in members:
        db.add(TgCampaignRecipient(
            campaign_id=campaign_id,
            tg_user_id=m["tg_user_id"],
            access_hash=m.get("access_hash", ""),
            username=m["username"],
            first_name=m["first_name"],
        ))
        added += 1

    campaign.total_recipients = added
    campaign.sent_count = 0
    campaign.failed_count = 0
    await db.commit()

    return {"message": f"Загружено {added} подписчиков", "count": added}


# ── Add Recipients Manually ──

@router.post("/campaigns/{campaign_id}/recipients")
async def add_tg_recipients(campaign_id: int, data: dict = Body(...), db: AsyncSession = Depends(get_db)):
    """Add recipients manually by user IDs."""
    campaign = await db.get(TgCampaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="TG-кампания не найдена")

    user_ids = data.get("user_ids", [])
    added = 0
    for uid in user_ids:
        try:
            uid = int(uid)
        except (TypeError, ValueError):
            continue
        # Check duplicate
        existing = (await db.execute(
            select(TgCampaignRecipient).where(
                TgCampaignRecipient.campaign_id == campaign_id,
                TgCampaignRecipient.tg_user_id == uid,
            )
        )).scalar_one_or_none()
        if not existing:
            db.add(TgCampaignRecipient(
                campaign_id=campaign_id,
                tg_user_id=uid,
            ))
            added += 1

    campaign.total_recipients = (campaign.total_recipients or 0) + added
    await db.commit()
    return {"message": f"Добавлено {added} получателей", "added": added}


# ── Campaign Control ──

@router.post("/campaigns/{campaign_id}/send")
async def send_tg_campaign(campaign_id: int, data: dict = Body(default={}), db: AsyncSession = Depends(get_db)):
    from backend.services.telegram_sender import start_tg_campaign

    campaign = await db.get(TgCampaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="TG-кампания не найдена")
    if campaign.status not in (TgCampaignStatus.DRAFT.value, TgCampaignStatus.PAUSED.value):
        raise HTTPException(status_code=400, detail=f"Нельзя запустить кампанию в статусе '{campaign.status}'")
    if campaign.total_recipients == 0:
        raise HTTPException(status_code=400, detail="Нет получателей")
    if not campaign.message_text:
        raise HTTPException(status_code=400, detail="Не указан текст сообщения")

    # Mark excluded recipients as skipped
    exclude_ids = data.get("exclude_recipient_ids", [])
    if exclude_ids:
        result = await db.execute(
            select(TgCampaignRecipient).where(
                TgCampaignRecipient.campaign_id == campaign_id,
                TgCampaignRecipient.id.in_(exclude_ids),
                TgCampaignRecipient.status == "pending",
            )
        )
        for r in result.scalars().all():
            r.status = "skipped"
        logger.info(f"TG campaign {campaign_id}: skipped {len(exclude_ids)} recipients")

    # Enforce hard delay floor
    if campaign.delay_seconds < TG_MIN_DELAY:
        campaign.delay_seconds = TG_MIN_DELAY

    # Check daily capacity (across ALL sender accounts)
    from backend.services.telegram_sender import _get_active_senders, TG_DAILY_LIMIT_PER_ACCOUNT
    active = len(_get_active_senders())
    total_daily_capacity = active * TG_DAILY_LIMIT_PER_ACCOUNT

    since = datetime.utcnow() - timedelta(hours=24)
    daily_sent = (await db.execute(
        select(func.count(TgCampaignRecipient.id)).where(
            TgCampaignRecipient.status == "sent",
            TgCampaignRecipient.sent_at >= since,
        )
    )).scalar() or 0

    remaining = total_daily_capacity - daily_sent
    if remaining <= 0:
        raise HTTPException(
            status_code=429,
            detail=f"Достигнут дневной лимит ({total_daily_capacity} сообщений за 24ч, {active} аккаунтов × {TG_DAILY_LIMIT_PER_ACCOUNT}). "
                   f"Отправлено: {daily_sent}. Попробуйте завтра."
        )

    if active == 0:
        raise HTTPException(status_code=400, detail="Нет активных аккаунтов-отправителей")

    campaign.status = TgCampaignStatus.SENDING.value
    if not campaign.started_at:
        campaign.started_at = datetime.utcnow()
    await db.commit()

    logger.info(f"TG campaign {campaign_id} started. {active} senders, sent: {daily_sent}/{total_daily_capacity}, remaining: {remaining}")
    start_tg_campaign(campaign_id)
    return {
        "message": f"TG-рассылка запущена ({active} аккаунтов, осталось {remaining} из {total_daily_capacity} на сегодня)",
        "daily_sent": daily_sent,
        "daily_remaining": remaining,
        "active_senders": active,
    }


@router.post("/campaigns/{campaign_id}/pause")
async def pause_tg_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(TgCampaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="TG-кампания не найдена")
    if campaign.status != TgCampaignStatus.SENDING.value:
        raise HTTPException(status_code=400, detail="Кампания не запущена")

    campaign.status = TgCampaignStatus.PAUSED.value
    await db.commit()
    return {"message": "TG-рассылка приостановлена"}


@router.post("/campaigns/{campaign_id}/cancel")
async def cancel_tg_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(TgCampaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="TG-кампания не найдена")

    campaign.status = TgCampaignStatus.CANCELLED.value
    await db.commit()
    return {"message": "TG-рассылка отменена"}


# ── Image Upload ──

TG_IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "tg_images")

@router.post("/campaigns/{campaign_id}/upload-image")
async def upload_tg_image(
    campaign_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    campaign = await db.get(TgCampaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="TG-кампания не найдена")

    # Validate file type
    allowed = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Формат {ext} не поддерживается. Используйте: {', '.join(allowed)}")

    # Validate size (max 5MB)
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Файл слишком большой (макс. 5 МБ)")

    # Save file
    os.makedirs(TG_IMAGES_DIR, exist_ok=True)
    filename = f"tg_campaign_{campaign_id}{ext}"
    filepath = os.path.join(TG_IMAGES_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(content)

    campaign.image_path = filepath
    await db.commit()

    logger.info(f"TG Campaign {campaign_id}: image uploaded ({len(content)} bytes)")
    return {"message": "Изображение загружено", "image_path": filepath, "size": len(content)}


@router.delete("/campaigns/{campaign_id}/image")
async def delete_tg_image(campaign_id: int, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(TgCampaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="TG-кампания не найдена")

    if campaign.image_path and os.path.exists(campaign.image_path):
        os.remove(campaign.image_path)

    campaign.image_path = ""
    await db.commit()
    return {"message": "Изображение удалено"}

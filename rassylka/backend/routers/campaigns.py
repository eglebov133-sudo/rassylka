"""
CRUD + campaign control API.
"""
import os
import uuid
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException, Body
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import (
    Campaign, CampaignRecipient, CampaignAttachment, CampaignStatus,
)

logger = logging.getLogger("bidroute.campaigns")
router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])

UPLOAD_DIR = "/opt/bidroute/data/campaign_attachments"


@router.get("")
async def list_campaigns(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Campaign)
    count_query = select(func.count(Campaign.id))

    if status:
        query = query.where(Campaign.status == status)
        count_query = count_query.where(Campaign.status == status)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(Campaign.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
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
            "subject": c.subject,
            "status": c.status,
            "delay_seconds": c.delay_seconds,
            "total_recipients": c.total_recipients,
            "sent_count": c.sent_count,
            "failed_count": c.failed_count,
            "opened_count": c.opened_count,
            "clicked_count": c.clicked_count,
            "progress": progress,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "started_at": c.started_at.isoformat() if c.started_at else None,
            "completed_at": c.completed_at.isoformat() if c.completed_at else None,
        })

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("")
async def create_campaign(data: dict = Body(...)):
    """Create campaign using direct sqlite3 with busy_timeout to avoid async lock contention."""
    import sqlite3
    import asyncio

    db_path = "/opt/bidroute/data/bidroute.db"
    name = data.get("name", "Без названия")
    subject = data.get("subject", "")
    html_body = data.get("html_body", "")
    delay_seconds = max(10, min(300, data.get("delay_seconds", 30)))
    now = datetime.utcnow().isoformat()

    def _do_insert():
        conn = sqlite3.connect(db_path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        try:
            cursor = conn.execute(
                """INSERT INTO campaigns (name, subject, html_body, status, delay_seconds,
                   total_recipients, sent_count, failed_count, opened_count, clicked_count,
                   created_at, started_at, completed_at)
                   VALUES (?, ?, ?, 'draft', ?, 0, 0, 0, 0, 0, ?, NULL, NULL)""",
                (name, subject, html_body, delay_seconds, now)
            )
            campaign_id = cursor.lastrowid

            # Parse and insert recipients
            emails_raw = data.get("recipients", "")
            emails = _parse_emails(emails_raw) if emails_raw else []
            for email in emails:
                token = uuid.uuid4().hex[:16]
                conn.execute(
                    """INSERT INTO campaign_recipients (campaign_id, email, name, status,
                       error_message, sent_at, opened_at, clicked_at, track_token)
                       VALUES (?, ?, '', 'pending', '', NULL, NULL, NULL, ?)""",
                    (campaign_id, email.strip().lower(), token)
                )
            if emails:
                conn.execute(
                    "UPDATE campaigns SET total_recipients = ? WHERE id = ?",
                    (len(emails), campaign_id)
                )

            conn.commit()
            return campaign_id, len(emails)
        finally:
            conn.close()

    try:
        # Run sync sqlite3 in a thread to avoid blocking the event loop
        campaign_id, recip_count = await asyncio.get_event_loop().run_in_executor(None, _do_insert)
        return {"id": campaign_id, "message": f"Кампания создана ({recip_count} получателей)"}
    except Exception as e:
        logger.error(f"Campaign creation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка создания: {str(e)}")


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Кампания не найдена")

    # Get recipients
    recip_result = await db.execute(
        select(CampaignRecipient)
        .where(CampaignRecipient.campaign_id == campaign_id)
        .order_by(CampaignRecipient.id)
    )
    recipients = recip_result.scalars().all()

    # Get attachments
    att_result = await db.execute(
        select(CampaignAttachment)
        .where(CampaignAttachment.campaign_id == campaign_id)
    )
    attachments = att_result.scalars().all()

    # Count stats
    stats = {"pending": 0, "sent": 0, "failed": 0, "opened": 0, "clicked": 0}
    for r in recipients:
        stats[r.status] = stats.get(r.status, 0) + 1

    return {
        "id": campaign.id,
        "name": campaign.name,
        "subject": campaign.subject,
        "html_body": campaign.html_body,
        "status": campaign.status,
        "delay_seconds": campaign.delay_seconds,
        "total_recipients": campaign.total_recipients,
        "sent_count": campaign.sent_count,
        "failed_count": campaign.failed_count,
        "opened_count": campaign.opened_count,
        "clicked_count": campaign.clicked_count,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
        "started_at": campaign.started_at.isoformat() if campaign.started_at else None,
        "completed_at": campaign.completed_at.isoformat() if campaign.completed_at else None,
        "stats": stats,
        "recipients": [
            {
                "id": r.id,
                "email": r.email,
                "name": r.name,
                "status": r.status,
                "error_message": r.error_message or "",
                "sent_at": r.sent_at.isoformat() if r.sent_at else None,
                "opened_at": r.opened_at.isoformat() if r.opened_at else None,
                "clicked_at": r.clicked_at.isoformat() if r.clicked_at else None,
            }
            for r in recipients
        ],
        "attachments": [
            {
                "id": a.id,
                "filename": a.filename,
                "size_bytes": a.size_bytes,
            }
            for a in attachments
        ],
    }


@router.put("/{campaign_id}")
async def update_campaign(campaign_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Кампания не найдена")
    if campaign.status != CampaignStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="Можно редактировать только черновик")

    for field in ("name", "subject", "html_body", "delay_seconds"):
        if field in data:
            val = data[field]
            if field == "delay_seconds":
                val = max(10, min(300, val))
            setattr(campaign, field, val)

    # Update recipients if provided
    if "recipients" in data:
        await db.execute(
            delete(CampaignRecipient).where(CampaignRecipient.campaign_id == campaign_id)
        )
        emails = _parse_emails(data["recipients"])
        for email in emails:
            recip = CampaignRecipient(
                campaign_id=campaign.id,
                email=email.strip().lower(),
                track_token=uuid.uuid4().hex[:16],
            )
            db.add(recip)
        campaign.total_recipients = len(emails)

    await db.commit()
    return {"message": "Кампания обновлена"}


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Кампания не найдена")
    if campaign.status == CampaignStatus.SENDING.value:
        raise HTTPException(status_code=400, detail="Нельзя удалить активную рассылку")

    # Delete attachment files
    att_result = await db.execute(
        select(CampaignAttachment).where(CampaignAttachment.campaign_id == campaign_id)
    )
    for att in att_result.scalars().all():
        try:
            if os.path.exists(att.filepath):
                os.remove(att.filepath)
        except Exception:
            pass

    await db.delete(campaign)
    await db.commit()
    return {"message": "Кампания удалена"}


@router.post("/{campaign_id}/recipients")
async def add_recipients(campaign_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Кампания не найдена")

    emails = _parse_emails(data.get("emails", ""))
    added = 0
    for email in emails:
        email = email.strip().lower()
        # Check duplicate
        existing = (await db.execute(
            select(CampaignRecipient).where(
                CampaignRecipient.campaign_id == campaign_id,
                CampaignRecipient.email == email,
            )
        )).scalar_one_or_none()
        if not existing:
            db.add(CampaignRecipient(
                campaign_id=campaign_id,
                email=email,
                track_token=uuid.uuid4().hex[:16],
            ))
            added += 1

    campaign.total_recipients = (campaign.total_recipients or 0) + added
    await db.commit()
    return {"message": f"Добавлено {added} получателей", "added": added}


@router.post("/{campaign_id}/attachments")
async def upload_attachment(
    campaign_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Кампания не найдена")

    # Size limit: 10MB
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Файл слишком большой (макс. 10 МБ)")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_name = f"{campaign_id}_{uuid.uuid4().hex[:8]}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, safe_name)

    with open(filepath, "wb") as f:
        f.write(content)

    att = CampaignAttachment(
        campaign_id=campaign_id,
        filename=file.filename,
        filepath=filepath,
        size_bytes=len(content),
    )
    db.add(att)
    await db.commit()
    return {"id": att.id, "filename": file.filename, "size_bytes": len(content)}


@router.delete("/{campaign_id}/attachments/{att_id}")
async def delete_attachment(campaign_id: int, att_id: int, db: AsyncSession = Depends(get_db)):
    att = await db.get(CampaignAttachment, att_id)
    if not att or att.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="Вложение не найдено")
    try:
        if os.path.exists(att.filepath):
            os.remove(att.filepath)
    except Exception:
        pass
    await db.delete(att)
    await db.commit()
    return {"message": "Вложение удалено"}


@router.post("/{campaign_id}/send")
async def send_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    from backend.services.campaign_sender import start_campaign

    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Кампания не найдена")
    if campaign.status not in (CampaignStatus.DRAFT.value, CampaignStatus.PAUSED.value):
        raise HTTPException(status_code=400, detail=f"Нельзя запустить кампанию в статусе '{campaign.status}'")
    if campaign.total_recipients == 0:
        raise HTTPException(status_code=400, detail="Нет получателей")
    if not campaign.subject:
        raise HTTPException(status_code=400, detail="Не указана тема письма")

    campaign.status = CampaignStatus.SENDING.value
    if not campaign.started_at:
        campaign.started_at = datetime.utcnow()
    await db.commit()

    start_campaign(campaign_id)
    return {"message": "Рассылка запущена"}


@router.post("/{campaign_id}/pause")
async def pause_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Кампания не найдена")
    if campaign.status != CampaignStatus.SENDING.value:
        raise HTTPException(status_code=400, detail="Кампания не запущена")

    campaign.status = CampaignStatus.PAUSED.value
    await db.commit()
    return {"message": "Рассылка приостановлена"}


@router.post("/{campaign_id}/resume")
async def resume_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    from backend.services.campaign_sender import start_campaign

    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Кампания не найдена")
    if campaign.status != CampaignStatus.PAUSED.value:
        raise HTTPException(status_code=400, detail="Кампания не на паузе")

    campaign.status = CampaignStatus.SENDING.value
    await db.commit()

    start_campaign(campaign_id)
    return {"message": "Рассылка возобновлена"}


@router.post("/{campaign_id}/cancel")
async def cancel_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Кампания не найдена")

    campaign.status = CampaignStatus.CANCELLED.value
    await db.commit()
    return {"message": "Рассылка отменена"}


@router.post("/{campaign_id}/preview")
async def preview_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    """Return rendered HTML preview of campaign."""
    from backend.services.campaign_sender import build_campaign_html
    from fastapi.responses import HTMLResponse

    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Кампания не найдена")

    body = campaign.html_body or "<p>Текст письма не задан</p>"
    is_raw = body.strip().lower().startswith(("<!doctype", "<html"))
    if is_raw:
        html = body
    else:
        html = build_campaign_html(
            subject=campaign.subject or "Предпросмотр",
            content_body=body,
        )
    return HTMLResponse(content=html)


@router.post("/{campaign_id}/test")
async def test_campaign(campaign_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    """Send a test email to specified address."""
    from backend.services.campaign_sender import send_campaign_email, build_campaign_html

    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Кампания не найдена")

    test_email = data.get("email", "")
    if not test_email:
        raise HTTPException(status_code=400, detail="Укажите email для тестовой отправки")

    body = campaign.html_body or ""
    is_raw = body.strip().lower().startswith(("<!doctype", "<html"))
    if is_raw:
        html = body
    else:
        html = build_campaign_html(
            subject=campaign.subject,
            content_body=body,
        )

    # Load attachments
    att_result = await db.execute(
        select(CampaignAttachment).where(CampaignAttachment.campaign_id == campaign_id)
    )
    attachments = [
        {"filepath": a.filepath, "filename": a.filename}
        for a in att_result.scalars().all()
    ]

    success, error = await send_campaign_email(
        test_email, f"[ТЕСТ] {campaign.subject}", html, attachments
    )

    if success:
        return {"message": f"Тестовое письмо отправлено на {test_email}"}
    raise HTTPException(status_code=500, detail=f"Ошибка отправки: {error}")


def _parse_emails(raw: str) -> list[str]:
    """Parse emails from text — supports comma, semicolon, newline separators."""
    import re
    if not raw:
        return []
    # Split by comma, semicolon, newline, space
    parts = re.split(r'[,;\n\r\s]+', raw.strip())
    # Filter valid-looking emails
    emails = []
    seen = set()
    for part in parts:
        part = part.strip().lower()
        if '@' in part and '.' in part and part not in seen:
            emails.append(part)
            seen.add(part)
    return emails

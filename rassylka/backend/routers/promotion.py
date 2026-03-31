"""
Promotion API — Yandex Direct campaign management.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from typing import Optional

from backend.database import async_session
from backend.models import YandexDirectConfig, YandexDirectCampaign

logger = logging.getLogger("bidroute.promotion")
router = APIRouter(prefix="/api/promotion", tags=["promotion"])


# ── Schemas ──

class ConfigIn(BaseModel):
    oauth_token: str
    client_id: str = ""
    client_login: str = ""


class CampaignCreateIn(BaseModel):
    name: str = "Запчасти — Umit"
    daily_budget: float = 300.0
    keywords: list[str] = ["запчасти оптом", "запчасти для спецтехники", "купить запчасти"]
    regions: list[int] = [225]  # 225 = Россия


# ── Config endpoints ──

@router.get("/config")
async def get_config():
    """Get current Yandex Direct connection config."""
    async with async_session() as db:
        result = await db.execute(select(YandexDirectConfig).where(YandexDirectConfig.id == 1))
        config = result.scalar_one_or_none()

    if not config:
        return {"connected": False, "has_token": False, "client_login": ""}

    return {
        "connected": config.connected,
        "has_token": bool(config.oauth_token),
        "client_login": config.client_login or "",
        "last_sync": config.last_sync_at.isoformat() if config.last_sync_at else None,
    }


@router.post("/config")
async def save_config(data: ConfigIn):
    """Save OAuth token and verify connection."""
    import httpx

    async with async_session() as db:
        result = await db.execute(select(YandexDirectConfig).where(YandexDirectConfig.id == 1))
        config = result.scalar_one_or_none()

        if not config:
            config = YandexDirectConfig(id=1)
            db.add(config)

        config.oauth_token = data.oauth_token
        config.client_id = data.client_id
        config.client_login = data.client_login

        # Verify token via Yandex Login API (works for any valid Yandex token)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    "https://login.yandex.ru/info?format=json",
                    headers={"Authorization": f"OAuth {data.oauth_token}"},
                )
                info = r.json()
                if "login" in info:
                    config.connected = True
                    config.client_login = data.client_login or info.get("login", "")
                    msg = f"Подключено (аккаунт: {info.get('login', '?')})"
                else:
                    config.connected = False
                    msg = "Токен невалиден"
        except Exception as e:
            config.connected = False
            msg = f"Ошибка проверки: {e}"

        await db.commit()

    return {"connected": config.connected, "message": msg}


@router.delete("/config")
async def disconnect():
    """Disconnect Yandex Direct (remove token)."""
    async with async_session() as db:
        result = await db.execute(select(YandexDirectConfig).where(YandexDirectConfig.id == 1))
        config = result.scalar_one_or_none()
        if config:
            config.oauth_token = ""
            config.connected = False
            await db.commit()
    return {"ok": True}


# ── Campaign endpoints ──

@router.get("/campaigns")
async def get_campaigns():
    """Get local campaign list with cached stats."""
    async with async_session() as db:
        result = await db.execute(
            select(YandexDirectCampaign).order_by(YandexDirectCampaign.created_at.desc())
        )
        campaigns = result.scalars().all()

    return {
        "campaigns": [
            {
                "id": c.id,
                "yd_campaign_id": c.yd_campaign_id,
                "name": c.name,
                "status": c.status,
                "yd_status": c.yd_status,
                "impressions": c.impressions,
                "clicks": c.clicks,
                "cost": round(c.cost, 2),
                "ctr": round(c.ctr, 2),
                "daily_budget": c.daily_budget,
                "keywords": c.keywords or [],
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in campaigns
        ],
        "totals": {
            "impressions": sum(c.impressions for c in campaigns),
            "clicks": sum(c.clicks for c in campaigns),
            "cost": round(sum(c.cost for c in campaigns), 2),
            "ctr": round(
                (sum(c.clicks for c in campaigns) / max(sum(c.impressions for c in campaigns), 1)) * 100, 2
            ),
            "active": sum(1 for c in campaigns if c.status == "active"),
            "total": len(campaigns),
        },
    }


@router.post("/campaigns/enable")
async def enable_promotion(data: CampaignCreateIn):
    """Create a new campaign in Yandex Direct and save locally."""
    from backend.services.yandex_direct import YandexDirectClient

    async with async_session() as db:
        # Get config
        result = await db.execute(select(YandexDirectConfig).where(YandexDirectConfig.id == 1))
        config = result.scalar_one_or_none()
        if not config or not config.oauth_token:
            raise HTTPException(400, "Сначала подключите Yandex Direct (укажите OAuth-токен)")

        # Create in Yandex Direct
        client = YandexDirectClient(config.oauth_token, config.client_login)
        try:
            yd_result = client_result = await client.create_campaign(
                name=data.name,
                daily_budget=data.daily_budget,
                keywords=data.keywords,
                regions=data.regions,
            )
        except Exception as e:
            raise HTTPException(400, f"Ошибка Яндекс.Директ: {e}")

        # Save locally
        campaign = YandexDirectCampaign(
            yd_campaign_id=yd_result["id"],
            name=data.name,
            status="pending",
            yd_status=yd_result.get("status", "DRAFT"),
            daily_budget=data.daily_budget,
            keywords=data.keywords,
            regions=data.regions,
        )
        db.add(campaign)
        await db.commit()

    return {"ok": True, "campaign_id": campaign.id, "yd_campaign_id": yd_result["id"],
            "message": "Кампания создана! Ожидайте прохождения модерации Яндексом."}


@router.post("/campaigns/{campaign_id}/pause")
async def pause_campaign(campaign_id: int):
    """Pause a campaign."""
    from backend.services.yandex_direct import YandexDirectClient

    async with async_session() as db:
        campaign = await db.get(YandexDirectCampaign, campaign_id)
        if not campaign:
            raise HTTPException(404, "Кампания не найдена")

        result = await db.execute(select(YandexDirectConfig).where(YandexDirectConfig.id == 1))
        config = result.scalar_one_or_none()
        if not config or not config.oauth_token:
            raise HTTPException(400, "Нет подключения к Яндекс.Директ")

        if campaign.yd_campaign_id:
            client = YandexDirectClient(config.oauth_token, config.client_login)
            try:
                await client.pause_campaign(campaign.yd_campaign_id)
            except Exception as e:
                raise HTTPException(400, f"Ошибка: {e}")

        campaign.status = "paused"
        await db.commit()

    return {"ok": True, "message": "Кампания приостановлена"}


@router.post("/campaigns/{campaign_id}/resume")
async def resume_campaign(campaign_id: int):
    """Resume a paused campaign."""
    from backend.services.yandex_direct import YandexDirectClient

    async with async_session() as db:
        campaign = await db.get(YandexDirectCampaign, campaign_id)
        if not campaign:
            raise HTTPException(404, "Кампания не найдена")

        result = await db.execute(select(YandexDirectConfig).where(YandexDirectConfig.id == 1))
        config = result.scalar_one_or_none()
        if not config or not config.oauth_token:
            raise HTTPException(400, "Нет подключения к Яндекс.Директ")

        if campaign.yd_campaign_id:
            client = YandexDirectClient(config.oauth_token, config.client_login)
            try:
                await client.resume_campaign(campaign.yd_campaign_id)
            except Exception as e:
                raise HTTPException(400, f"Ошибка: {e}")

        campaign.status = "active"
        await db.commit()

    return {"ok": True, "message": "Кампания возобновлена"}


@router.post("/sync")
async def sync_campaigns():
    """Sync only OUR campaign data from Yandex Direct (not foreign campaigns)."""
    from backend.services.yandex_direct import YandexDirectClient

    async with async_session() as db:
        result = await db.execute(select(YandexDirectConfig).where(YandexDirectConfig.id == 1))
        config = result.scalar_one_or_none()
        if not config or not config.oauth_token:
            raise HTTPException(400, "Нет подключения к Яндекс.Директ")

        # Only sync campaigns that WE created (exist in our DB)
        result = await db.execute(
            select(YandexDirectCampaign).where(YandexDirectCampaign.yd_campaign_id.isnot(None))
        )
        our_campaigns = result.scalars().all()

        if not our_campaigns:
            config.last_sync_at = datetime.utcnow()
            await db.commit()
            return {"ok": True, "synced": 0, "message": "Нет кампаний для синхронизации"}

        client = YandexDirectClient(config.oauth_token, config.client_login)

        try:
            yd_campaigns = await client.get_campaigns()
        except Exception as e:
            raise HTTPException(400, f"Ошибка синхронизации: {e}")

        yd_map = {c["id"]: c for c in yd_campaigns}
        synced = 0

        for campaign in our_campaigns:
            yc = yd_map.get(campaign.yd_campaign_id)
            if not yc:
                continue

            # Update YD status from Status field (MODERATION, ACCEPTED, etc.)
            campaign.yd_status = yc.get("status", campaign.yd_status or "")
            campaign.impressions = yc.get("impressions", 0)
            campaign.clicks = yc.get("clicks", 0)

            # Map State to our internal status
            state = yc.get("state", "")
            yd_status = yc.get("status", "")

            if state == "ON":
                campaign.status = "active"
            elif state == "SUSPENDED":
                campaign.status = "paused"
            elif state == "OFF":
                # OFF can mean draft, moderation, or stopped
                if yd_status == "DRAFT":
                    campaign.status = "draft"
                elif yd_status in ("MODERATION", "PENDING"):
                    campaign.status = "moderation"
                elif yd_status == "ACCEPTED":
                    campaign.status = "ready"  # accepted but OFF (e.g. no funds)
                elif yd_status == "REJECTED":
                    campaign.status = "rejected"
                else:
                    campaign.status = "stopped"
            elif state == "ENDED":
                campaign.status = "archived"
            elif state == "CONVERTED":
                campaign.status = "archived"
            else:
                campaign.status = "draft"

            if campaign.impressions > 0:
                campaign.ctr = round((campaign.clicks / campaign.impressions) * 100, 2)

            # Update budget only if API returns a valid value
            api_budget = yc.get("daily_budget", 0)
            if api_budget > 0:
                campaign.daily_budget = api_budget

            campaign.updated_at = datetime.utcnow()
            synced += 1

        config.last_sync_at = datetime.utcnow()
        await db.commit()

    return {"ok": True, "synced": synced, "message": f"Синхронизировано {synced} кампаний"}

"""
Click & open tracking for email.

/api/track/{token}       — click tracking (redirects to bid URL)
/api/track/open/{token}  — open tracking (returns 1x1 transparent pixel)
"""
import base64
import datetime
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import select

from backend.database import async_session
from backend.models import DistributionLog, DistributionBatch, Bid

logger = logging.getLogger("bidroute.tracking")
router = APIRouter(prefix="/api/track", tags=["tracking"])

# 1x1 transparent GIF
TRACKING_PIXEL = base64.b64decode(
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)


@router.get("/open/{token}")
async def track_open(token: str):
    """Record email open via tracking pixel and return 1x1 GIF."""
    async with async_session() as session:
        result = await session.execute(
            select(DistributionLog).where(DistributionLog.click_token == token)
        )
        log = result.scalar_one_or_none()

        if log and not log.opened_at:
            log.opened_at = datetime.datetime.utcnow()
            await session.commit()
            logger.info(f"Email opened: token={token}, supplier_id={log.supplier_id}")

    return Response(
        content=TRACKING_PIXEL,
        media_type="image/gif",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )


@router.get("/{token}")
async def track_click(token: str):
    """Record supplier click and redirect to bid URL."""
    async with async_session() as session:
        result = await session.execute(
            select(DistributionLog).where(DistributionLog.click_token == token)
        )
        log = result.scalar_one_or_none()

        if not log:
            logger.warning(f"Invalid tracking token: {token}")
            return RedirectResponse("https://umit.pro/", status_code=302)

        # Record click (also counts as open if not opened yet)
        if not log.clicked_at:
            log.clicked_at = datetime.datetime.utcnow()
            if not log.opened_at:
                log.opened_at = datetime.datetime.utcnow()
            await session.commit()
            logger.info(f"Click recorded: token={token}, supplier_id={log.supplier_id}")
        else:
            logger.info(f"Repeat click: token={token}")

        # Get the bid URL to redirect to
        batch_result = await session.execute(
            select(DistributionBatch).where(DistributionBatch.id == log.batch_id)
        )
        batch = batch_result.scalar_one_or_none()
        redirect_url = "https://umit.pro/"

        if batch:
            bid_result = await session.execute(
                select(Bid).where(Bid.id == batch.bid_id)
            )
            bid = bid_result.scalar_one_or_none()
            if bid and bid.source_url:
                redirect_url = bid.source_url

    return RedirectResponse(redirect_url, status_code=302)


# ── Campaign tracking ──

@router.get("/campaign/open/{token}")
async def track_campaign_open(token: str):
    """Record campaign email open via tracking pixel."""
    from backend.models import CampaignRecipient, Campaign

    async with async_session() as session:
        result = await session.execute(
            select(CampaignRecipient).where(CampaignRecipient.track_token == token)
        )
        recip = result.scalar_one_or_none()

        if recip and not recip.opened_at:
            recip.opened_at = datetime.datetime.utcnow()
            if recip.status == "sent":
                recip.status = "opened"
            # Update campaign counter
            campaign = await session.get(Campaign, recip.campaign_id)
            if campaign:
                campaign.opened_count = (campaign.opened_count or 0) + 1
            await session.commit()

    return Response(
        content=TRACKING_PIXEL,
        media_type="image/gif",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )


@router.get("/campaign/click/{token}")
async def track_campaign_click(token: str):
    """Record campaign email click."""
    from backend.models import CampaignRecipient, Campaign

    async with async_session() as session:
        result = await session.execute(
            select(CampaignRecipient).where(CampaignRecipient.track_token == token)
        )
        recip = result.scalar_one_or_none()

        if not recip:
            return RedirectResponse("https://umit.pro/", status_code=302)

        if not recip.clicked_at:
            recip.clicked_at = datetime.datetime.utcnow()
            if not recip.opened_at:
                recip.opened_at = datetime.datetime.utcnow()
            recip.status = "clicked"
            campaign = await session.get(Campaign, recip.campaign_id)
            if campaign:
                campaign.clicked_count = (campaign.clicked_count or 0) + 1
            await session.commit()

    return RedirectResponse("https://umit.pro/", status_code=302)


# ── Unsubscribe ──
unsub_router = APIRouter(prefix="/api/unsubscribe", tags=["unsubscribe"])


@unsub_router.get("/{token}")
async def unsubscribe(token: str):
    """Deactivate supplier via unsubscribe link."""
    from backend.models import Supplier
    from fastapi.responses import HTMLResponse

    async with async_session() as session:
        result = await session.execute(
            select(Supplier).where(Supplier.unsubscribe_token == token)
        )
        supplier = result.scalar_one_or_none()

        if not supplier:
            return HTMLResponse(
                '<html><body style="font-family:sans-serif;text-align:center;padding:60px">'
                '<h2>Ссылка недействительна</h2>'
                '<p>Возможно, вы уже отписались ранее.</p>'
                '</body></html>',
                status_code=404,
            )

        supplier.active = False
        await session.commit()
        logger.info(f"Supplier {supplier.company_name} ({supplier.email}) unsubscribed via token")

    return HTMLResponse(
        '<html><body style="font-family:sans-serif;text-align:center;padding:60px">'
        f'<h2>Вы успешно отписались</h2>'
        f'<p>Адрес <strong>{supplier.email}</strong> больше не будет получать рассылку от Umit.</p>'
        '</body></html>',
        status_code=200,
    )

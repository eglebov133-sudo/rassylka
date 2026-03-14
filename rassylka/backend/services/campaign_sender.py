"""
Background campaign sender — sends emails for manual campaigns
with configurable delay, MX validation, tracking, and attachments.
"""
import asyncio
import logging
import os
import uuid
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formataddr, make_msgid, formatdate

import aiosmtplib
from sqlalchemy import select, func

from backend.database import async_session
from backend.models import (
    Campaign, CampaignRecipient, CampaignAttachment,
    CampaignStatus, SmtpAccount,
)

logger = logging.getLogger("bidroute.campaign_sender")

APP_BASE_URL = os.getenv("APP_BASE_URL", "http://155.212.223.142")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.mail.ru")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")

# Active campaign tasks
_active_tasks: dict[int, asyncio.Task] = {}


def inject_tracking(html_body: str, track_token: str) -> str:
    """Inject tracking pixel and wrap links."""
    open_url = f"{APP_BASE_URL}/api/track/campaign/open/{track_token}"
    pixel = f'<img src="{open_url}" width="1" height="1" alt="" style="display:none" />'

    if "</body>" in html_body:
        return html_body.replace("</body>", f"{pixel}</body>")
    return html_body + pixel


async def get_smtp_credentials():
    """Get SMTP credentials with rotation."""
    try:
        async with async_session() as db:
            result = await db.execute(
                select(SmtpAccount)
                .where(SmtpAccount.active == True)
                .order_by(SmtpAccount.send_count.asc())
                .limit(1)
            )
            account = result.scalar_one_or_none()
            if account:
                return {
                    "host": account.smtp_host,
                    "port": account.smtp_port,
                    "user": account.email,
                    "pass": account.password,
                    "tls": account.use_tls,
                    "db_id": account.id,
                }
    except Exception as e:
        logger.warning(f"Failed to fetch SMTP accounts: {e}")

    if SMTP_USER and SMTP_PASS:
        return {
            "host": SMTP_HOST, "port": SMTP_PORT,
            "user": SMTP_USER, "pass": SMTP_PASS,
            "tls": True, "db_id": None,
        }
    return None


async def send_campaign_email(
    to_email: str,
    subject: str,
    html_body: str,
    attachments: list[dict] = None,
) -> tuple[bool, str]:
    """Send a single campaign email. Returns (success, error_message)."""
    creds = await get_smtp_credentials()
    if not creds:
        return False, "No SMTP credentials configured"

    sender_email = creds["user"]
    domain = sender_email.split("@")[1] if "@" in sender_email else "pochtamt.online"

    msg = MIMEMultipart("mixed")
    msg["From"] = formataddr(("Umit — Маркетплейс запчастей", sender_email))
    msg["To"] = to_email
    msg["Subject"] = subject
    msg["Reply-To"] = sender_email
    msg["Message-ID"] = make_msgid(domain=domain)
    msg["Date"] = formatdate(localtime=True)
    msg["List-Unsubscribe"] = f"<mailto:{sender_email}?subject=unsubscribe>"
    msg["X-Mailer"] = "Umit Marketplace Campaign"
    msg["Precedence"] = "bulk"

    # HTML body
    html_part = MIMEText(html_body, "html", "utf-8")
    msg.attach(html_part)

    # Attachments
    if attachments:
        for att in attachments:
            try:
                filepath = att["filepath"]
                filename = att["filename"]
                if os.path.exists(filepath):
                    with open(filepath, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename={filename}")
                    msg.attach(part)
            except Exception as e:
                logger.warning(f"Failed to attach {att.get('filename')}: {e}")

    try:
        response = await aiosmtplib.send(
            msg,
            hostname=creds["host"],
            port=creds["port"],
            username=creds["user"],
            password=creds["pass"],
            use_tls=creds["tls"],
        )
        # Update send count
        if creds["db_id"]:
            try:
                async with async_session() as db:
                    acc = await db.get(SmtpAccount, creds["db_id"])
                    if acc:
                        acc.send_count = (acc.send_count or 0) + 1
                        acc.last_used_at = datetime.utcnow()
                        await db.commit()
            except Exception:
                pass
        return True, ""
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


async def run_campaign(campaign_id: int):
    """Background task: send campaign emails one by one with delay."""
    from backend.services.mail_engine import validate_email_mx

    logger.info(f"Campaign {campaign_id}: starting send loop")

    async with async_session() as db:
        campaign = await db.get(Campaign, campaign_id)
        if not campaign:
            logger.error(f"Campaign {campaign_id} not found")
            return

        # Load attachments
        att_result = await db.execute(
            select(CampaignAttachment).where(CampaignAttachment.campaign_id == campaign_id)
        )
        attachments = [
            {"filepath": a.filepath, "filename": a.filename}
            for a in att_result.scalars().all()
        ]

        # Get pending recipients
        recip_result = await db.execute(
            select(CampaignRecipient)
            .where(
                CampaignRecipient.campaign_id == campaign_id,
                CampaignRecipient.status == "pending",
            )
            .order_by(CampaignRecipient.id)
        )
        recipients = recip_result.scalars().all()

        delay = campaign.delay_seconds or 30
        sent = campaign.sent_count or 0
        failed = campaign.failed_count or 0

        for recipient in recipients:
            # Check if paused or cancelled
            await db.refresh(campaign)
            if campaign.status in (CampaignStatus.PAUSED.value, CampaignStatus.CANCELLED.value):
                logger.info(f"Campaign {campaign_id}: {campaign.status}, stopping")
                break

            # Generate tracking token
            if not recipient.track_token:
                recipient.track_token = uuid.uuid4().hex[:16]

            # MX validation
            is_valid, reason = await validate_email_mx(recipient.email)
            if not is_valid:
                recipient.status = "failed"
                recipient.error_message = f"Email validation: {reason}"
                failed += 1
                campaign.failed_count = failed
                await db.commit()
                logger.warning(f"  Skipped {recipient.email}: {reason}")
                continue

            # Inject tracking pixel
            html = inject_tracking(campaign.html_body, recipient.track_token)

            # Send
            success, error = await send_campaign_email(
                recipient.email, campaign.subject, html, attachments
            )

            if success:
                recipient.status = "sent"
                recipient.sent_at = datetime.utcnow()
                sent += 1
            else:
                recipient.status = "failed"
                recipient.error_message = error
                failed += 1

            campaign.sent_count = sent
            campaign.failed_count = failed
            await db.commit()
            logger.info(f"  [{sent+failed}/{campaign.total_recipients}] {recipient.email}: {'OK' if success else error}")

            # Delay between sends
            await asyncio.sleep(delay)

        # Final status update
        await db.refresh(campaign)
        if campaign.status == CampaignStatus.SENDING.value:
            campaign.status = CampaignStatus.COMPLETED.value
            campaign.completed_at = datetime.utcnow()
            await db.commit()
            logger.info(f"Campaign {campaign_id}: completed ({sent} sent, {failed} failed)")

    # Clean up task reference
    _active_tasks.pop(campaign_id, None)


def start_campaign(campaign_id: int):
    """Start or resume a campaign in the background."""
    if campaign_id in _active_tasks:
        task = _active_tasks[campaign_id]
        if not task.done():
            return False  # Already running

    task = asyncio.create_task(run_campaign(campaign_id))
    _active_tasks[campaign_id] = task
    return True


def is_campaign_running(campaign_id: int) -> bool:
    task = _active_tasks.get(campaign_id)
    return task is not None and not task.done()

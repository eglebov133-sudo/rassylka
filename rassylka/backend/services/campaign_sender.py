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

APP_BASE_URL = os.getenv("APP_BASE_URL", "https://umit-info.ru")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.mail.ru")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")

import re

# Active campaign tasks
_active_tasks: dict[int, asyncio.Task] = {}


def _rewrite_asset_urls(html: str) -> str:
    """Rewrite relative /campaign-assets/ and /email-assets/ paths to absolute URLs.

    Email clients cannot resolve relative paths, so we prepend APP_BASE_URL.
    Handles src="...", url(...), and url('...') patterns.
    """
    base = APP_BASE_URL.rstrip("/")

    # src="/campaign-assets/..." or src="/email-assets/..."
    html = re.sub(
        r'''(src\s*=\s*["'])(/(?:campaign-assets|email-assets)/[^"']+)(["'])''',
        lambda m: f'{m.group(1)}{base}{m.group(2)}{m.group(3)}',
        html,
        flags=re.IGNORECASE,
    )

    # url(/campaign-assets/...) or url('/campaign-assets/...') or url("/campaign-assets/...")
    html = re.sub(
        r"""(url\s*\(\s*['"]?)(/(?:campaign-assets|email-assets)/[^)'"]+)(['"]?\s*\))""",
        lambda m: f'{m.group(1)}{base}{m.group(2)}{m.group(3)}',
        html,
        flags=re.IGNORECASE,
    )

    return html


def inject_tracking(html: str, track_token: str) -> str:
    """Inject tracking pixel into raw HTML template (before </body>)."""
    tracking_url = f"{APP_BASE_URL}/api/track/campaign/open/{track_token}"
    pixel = f'<img src="{tracking_url}" width="1" height="1" style="display:none" alt="">'
    if "</body>" in html.lower():
        idx = html.lower().rfind("</body>")
        return html[:idx] + pixel + html[idx:]
    return html + pixel


def build_campaign_html(subject: str, content_body: str, tracking_url: str = "", unsubscribe_url: str = "", cta_url: str = "", cta_text: str = "") -> str:
    """Wrap campaign content in the professional Umit-branded email template.
    Matches the visual style of the automatic distribution template (mail_engine.build_email_html).
    """
    img_base = f"{APP_BASE_URL}/email-assets"

    # Build CTA button if provided
    cta_block = ""
    if cta_url and cta_text:
        cta_block = f'''
                            <tr>
                                <td style="padding-top:20px; text-align:center">
                                    <a style="display:inline-block; color:#ffffff; text-align:center; font-family:'Gilroy',sans-serif,Arial,Helvetica; font-size:15px; font-weight:600; line-height:24px; padding:12px 32px; background-color:#27ae60; border-radius:8px; text-decoration:none" href="{cta_url}" target="_blank">
                                        {cta_text} →
                                    </a>
                                </td>
                            </tr>'''

    # Tracking pixel
    pixel = ""
    if tracking_url:
        pixel = f'<img src="{tracking_url}" width="1" height="1" alt="" style="display:none;width:1px;height:1px;border:0" />'

    # Unsubscribe block in footer
    unsub_left = ""
    unsub_extra = ""
    if unsubscribe_url:
        unsub_left = f'<a href="{unsubscribe_url}" target="_blank" style="color:#828282; font-family:\'Gilroy\',sans-serif,Arial,Helvetica; font-size:12px; font-weight:500; line-height:18px; text-decoration:underline" rel="noopener noreferrer">Отписаться от рассылки</a>'
        unsub_extra = f'<p style="margin:8px 0 0; font-size:10px; color:#aaa;"><a href="{unsubscribe_url}" style="color:#aaa; text-decoration:underline;">Отписаться от рассылки</a></p>'
    else:
        unsub_left = '&nbsp;'

    return f'''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="ru">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
    <!--[if (gte mso 9)|(IE)]>
    <style type="text/css">
        table {{ border-collapse: collapse !important; }}
        body, table, td, p, a {{ font-family: sans-serif, Arial, Helvetica !important; }}
    </style>
    <![endif]-->
</head>
<body style="margin:0; padding:0; min-width:100%; background:#f8f8f8">
    <center style="width:100%; table-layout:fixed; background:#f8f8f8; padding-top:30px; padding-bottom:30px">
        <div style="max-width:600px; background:#ffffff; border-radius:5px">
            <!--[if (gte mso 9)|(IE)]>
            <table width="600" align="center" border="0" cellspacing="0" cellpadding="0" role="presentation" style="color:#333333"><tr><td>
            <![endif]-->
            <table align="center" border="0" cellspacing="0" cellpadding="0" role="presentation" style="color:#333333; font-family:'Gilroy',sans-serif,Arial,Helvetica; background:#ffffff; margin:0; padding:30px; width:100%; max-width:600px">

                <!-- LOGO -->
                <tr>
                    <td>
                        <table align="center" border="0" cellspacing="0" cellpadding="0" role="presentation" style="margin:0; padding:0; width:100%; max-width:540px">
                            <tr>
                                <td align="left">
                                    <a href="https://umit.pro/" target="_blank" rel="noopener noreferrer">
                                        <img width="82" height="50" src="{img_base}/logo.png" alt="Umit" style="display:block">
                                    </a>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>

                <!-- HEADER BANNER -->
                <tr>
                    <td>
                        <table align="center" cellspacing="0" cellpadding="0" role="presentation" style="border:1px solid #f2f2f2; border-radius:8px; margin:0; margin-top:25px; padding:8px 10px; width:100%; max-width:540px; background-image:url({img_base}/background-1.png)">
                            <tr>
                                <td>
                                    <img width="65" height="67" src="{img_base}/cart.png" alt="" style="display:inline-block; vertical-align:middle">
                                </td>
                                <td>
                                    <p style="margin-left:20px; font-size:22px; font-weight:700; line-height:138%; color:#333333; font-family:'Gilroy',sans-serif,Arial,Helvetica; display:inline-block">
                                        Umit — <span style="color:#57c76f">маркетплейс</span> запчастей
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>

                <!-- CONTENT -->
                <tr>
                    <td>
                        <table align="center" border="0" cellspacing="0" cellpadding="0" role="presentation" style="margin:0; margin-top:25px; padding:0; width:100%; max-width:540px">
                            <tr>
                                <td style="font-size:14px; font-weight:500; color:#333333; font-family:'Gilroy',sans-serif,Arial,Helvetica; line-height:160%">
                                    {content_body}
                                </td>
                            </tr>
                            {cta_block}
                            <tr>
                                <td style="padding-top:15px">
                                    <p style="margin:0; font-size:14px; font-weight:600; color:#333333; font-family:'Gilroy',sans-serif,Arial,Helvetica">
                                        Команда Umit
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>

                <!-- MOBILE APP SECTION -->
                <tr>
                    <td>
                        <table align="center" border="0" cellspacing="0" cellpadding="0" role="presentation" style="color:#333333; font-family:'Gilroy',sans-serif,Arial,Helvetica; margin:0; padding:0; width:100%; max-width:540px; border:1px solid #f2f2f2; border-radius:8px; background-image:url({img_base}/background-2.png)">
                            <tr>
                                <td>
                                    <table align="center" border="0" cellspacing="0" cellpadding="0" role="presentation" style="margin:0; padding:0; padding-left:30px; margin-top:30px; width:100%; max-width:540px">
                                        <tr>
                                            <td>
                                                <p style="margin:0; color:#333333; font-family:'Gilroy',sans-serif,Arial,Helvetica; font-size:22px; font-weight:700; line-height:138%">
                                                    Мобильное приложение <span style="color:#57c76f">Umit</span>
                                                </p>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td>
                                                <p style="margin:0; margin-top:10px; color:#333333; font-family:'Gilroy',sans-serif,Arial,Helvetica; font-size:18px; font-weight:500; line-height:138%">
                                                    Все заявки и заказы всегда под рукой
                                                </p>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td>
                                                <table>
                                                    <tr>
                                                        <td>
                                                            <a href="https://apps.apple.com/ru/app/umit/id6450985794" target="_blank" style="display:inline-block; text-decoration:none; margin-top:15px" rel="noopener noreferrer">
                                                                <img width="116" height="32" src="{img_base}/apple.png" alt="App Store" style="display:block">
                                                            </a>
                                                        </td>
                                                        <td>
                                                            <a href="https://play.google.com/store/apps/details?id=com.umitauto.app" target="_blank" style="display:inline-block; margin-left:16px; text-decoration:none; margin-top:15px" rel="noopener noreferrer">
                                                                <img width="116" height="32" src="{img_base}/google.png" alt="Google Play" style="display:block">
                                                            </a>
                                                        </td>
                                                    </tr>
                                                </table>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="padding-top:20px; padding-bottom:20px">
                                                <a href="https://umit.pro/" target="_blank" style="display:inline-block; text-decoration:none" rel="noopener noreferrer">
                                                    <img width="80" height="auto" src="{img_base}/logo.png" alt="Umit" style="display:block">
                                                </a>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                                <td align="right" style="vertical-align:bottom">
                                    <img width="180" height="200" src="{img_base}/phone.png" alt="Umit application" style="display:block">
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>

                <!-- FOOTER -->
                <tr>
                    <td>
                        <table align="center" border="0" cellspacing="0" cellpadding="0" role="presentation" style="color:#333333; font-family:'Gilroy',sans-serif,Arial,Helvetica; background:#f9f9f9; margin:0; padding:15px; width:100%; max-width:540px; margin-top:30px; border-radius:8px">
                            <tr>
                                <td align="left">
                                    {unsub_left}
                                </td>
                                <td align="right">
                                    <p style="margin:0; color:#828282; font-family:'Gilroy',sans-serif,Arial,Helvetica; font-size:12px; font-weight:500; line-height:18px">
                                        © Umit. Все права защищены
                                    </p>
                                    {unsub_extra}
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>

            </table>
            <!--[if (gte mso 9)|(IE)]>
            </td></tr></table>
            <![endif]-->
        </div>
    </center>
{pixel}
</body>
</html>'''


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
    domain = sender_email.split("@")[1] if "@" in sender_email else "umit-info.ru"

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

            # Build email — detect raw HTML template vs content for Umit wrapper
            open_tracking_url = f"{APP_BASE_URL}/api/track/campaign/open/{recipient.track_token}"
            body = campaign.html_body or ""
            is_raw_html = body.strip().lower().startswith(("<!doctype", "<html"))
            if is_raw_html:
                # Raw HTML template (e.g. Prom28) — inject tracking pixel only
                # Rewrite relative /campaign-assets/ paths to absolute URLs
                # so email clients can load images
                body = _rewrite_asset_urls(body)
                html = inject_tracking(body, recipient.track_token)
            else:
                html = build_campaign_html(
                    subject=campaign.subject,
                    content_body=body,
                    tracking_url=open_tracking_url,
                )

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

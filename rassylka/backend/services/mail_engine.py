"""
Mail Engine — SMTP batch distribution with escalation.
"""
import os
import asyncio
import logging
import uuid
import socket
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid, formataddr
from typing import List, Optional

import aiosmtplib
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import async_session
from backend.models import (
    Bid, Supplier, DistributionBatch, DistributionLog,
    RoutingRule, BidStatus, BatchStatus, EmailStatus,
)
from backend.services.matching import find_matching_suppliers, get_already_notified_supplier_ids

logger = logging.getLogger("bidroute.mail_engine")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.beget.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
SENDER_NAME = os.getenv("SENDER_NAME", "BidRoute AI")

# TEST WHITELIST: only emails to these addresses are actually sent.
# All other recipients are skipped. Comma-separated. Empty = send to everyone.
TEST_WHITELIST = [e.strip() for e in os.getenv("TEST_WHITELIST", "").split(",") if e.strip()]

# Base URL for tracking links (our VPS or domain)
APP_BASE_URL = os.getenv("APP_BASE_URL", "https://umit-info.ru")

# Module-level state
distributor_state = {
    "running": False,
    "last_run": None,
    "error": None,
}


async def backfill_timeout_at():
    """Ensure all 'waiting' batches have a timeout_at value.
    If timeout_at is NULL (e.g. column was added after batch creation),
    backfill it using sent_at + escalation_hours."""
    try:
        async with async_session() as session:
            # Get escalation_hours from rules
            r = await session.execute(select(RoutingRule).where(RoutingRule.id == 1))
            rules = r.scalar_one_or_none()
            esc_hours = (getattr(rules, 'escalation_hours', None) or 24) if rules else 24

            # Find batches with NULL timeout_at
            result = await session.execute(
                select(DistributionBatch).where(
                    and_(
                        DistributionBatch.timeout_at.is_(None),
                        DistributionBatch.status.in_([BatchStatus.WAITING.value, BatchStatus.SENT.value]),
                    )
                )
            )
            batches = result.scalars().all()
            if batches:
                for batch in batches:
                    base_time = batch.sent_at or batch.created_at or datetime.utcnow()
                    batch.timeout_at = base_time + timedelta(hours=esc_hours)
                    logger.info(f"Backfilled timeout_at for batch {batch.id}: {batch.timeout_at}")
                await session.commit()
                logger.info(f"Backfilled timeout_at for {len(batches)} batches (escalation={esc_hours}h)")
            else:
                logger.info("All batches have timeout_at set — no backfill needed")
    except Exception as e:
        logger.error(f"Error backfilling timeout_at: {e}")


def build_email_html(bid: Bid, tracking_url: str = "", unsubscribe_url: str = "", open_tracking_url: str = "") -> str:
    """Build HTML email body for a bid notification — Umit brand style."""
    # Build optional fields
    brand_row = ""
    if bid.brand:
        brand_model = bid.brand
        if bid.model:
            brand_model += f" {bid.model}"
        if bid.year:
            brand_model += f" ({bid.year})"
        brand_row = f'''
        <tr>
            <td style="padding: 8px 0; border-bottom: 1px solid #f2f2f2">
                <p style="margin:0; font-size:12px; font-weight:500; color:#828282; font-family:'Gilroy',sans-serif,Arial,Helvetica; text-transform:uppercase; letter-spacing:0.5px">Бренд / Модель</p>
                <p style="margin:4px 0 0; font-size:15px; font-weight:600; color:#333333; font-family:'Gilroy',sans-serif,Arial,Helvetica">{brand_model}</p>
            </td>
        </tr>'''

    type_row = ""
    if bid.spare_part_type:
        type_row = f'''
        <tr>
            <td style="padding: 8px 0; border-bottom: 1px solid #f2f2f2">
                <p style="margin:0; font-size:12px; font-weight:500; color:#828282; font-family:'Gilroy',sans-serif,Arial,Helvetica; text-transform:uppercase; letter-spacing:0.5px">Тип запчасти</p>
                <p style="margin:4px 0 0; font-size:15px; font-weight:600; color:#333333; font-family:'Gilroy',sans-serif,Arial,Helvetica">{bid.spare_part_type}</p>
            </td>
        </tr>'''

    delivery_row = ""
    if bid.delivery_place:
        delivery_row = f'''
        <tr>
            <td style="padding: 8px 0; border-bottom: 1px solid #f2f2f2">
                <p style="margin:0; font-size:12px; font-weight:500; color:#828282; font-family:'Gilroy',sans-serif,Arial,Helvetica; text-transform:uppercase; letter-spacing:0.5px">Место доставки</p>
                <p style="margin:4px 0 0; font-size:15px; font-weight:600; color:#333333; font-family:'Gilroy',sans-serif,Arial,Helvetica">{bid.delivery_place}</p>
            </td>
        </tr>'''

    buyer_row = ""
    if bid.buyer_name:
        buyer_row = f'''
        <tr>
            <td style="padding: 8px 0; border-bottom: 1px solid #f2f2f2">
                <p style="margin:0; font-size:12px; font-weight:500; color:#828282; font-family:'Gilroy',sans-serif,Arial,Helvetica; text-transform:uppercase; letter-spacing:0.5px">Покупатель</p>
                <p style="margin:4px 0 0; font-size:15px; font-weight:600; color:#333333; font-family:'Gilroy',sans-serif,Arial,Helvetica">{bid.buyer_name}</p>
            </td>
        </tr>'''

    desc_block = ""
    if bid.description:
        desc_block = f'''
        <tr>
            <td style="padding: 12px 0 0">
                <p style="margin:0; font-size:12px; font-weight:500; color:#828282; font-family:'Gilroy',sans-serif,Arial,Helvetica; text-transform:uppercase; letter-spacing:0.5px">Описание</p>
                <p style="margin:6px 0 0; font-size:14px; font-weight:500; color:#333333; font-family:'Gilroy',sans-serif,Arial,Helvetica; line-height:150%; background:#f9f9f9; padding:10px 14px; border-radius:6px">{bid.description}</p>
            </td>
        </tr>'''

    source_url = bid.source_url or "https://umit.pro/"
    cta_url = tracking_url if tracking_url else source_url
    img_base = f"{APP_BASE_URL}/email-assets"

    return f'''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="ru">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Запрос предложения — Umit</title>
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
                                    <img width="65" height="67" src="{img_base}/cart.png" alt="Запрос предложения" style="display:inline-block; vertical-align:middle">
                                </td>
                                <td>
                                    <p style="margin-left:20px; font-size:22px; font-weight:700; line-height:138%; color:#333333; font-family:'Gilroy',sans-serif,Arial,Helvetica; display:inline-block">
                                        Запрос <span style="color:#57c76f">предложения</span>
                                    </p>
                                </td>
                                <td align="right">
                                    <a style="display:inline-block; color:#ffffff; text-align:center; font-family:'Gilroy',sans-serif,Arial,Helvetica; font-size:14px; font-weight:600; line-height:24px; padding:8px 20px; background-color:#27ae60; border-radius:8px; text-decoration:none" href="{cta_url}" target="_blank">
                                        <span style="vertical-align:middle">Подробнее</span>
                                    </a>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>

                <!-- BID DETAILS -->
                <tr>
                    <td>
                        <table align="center" border="0" cellspacing="0" cellpadding="0" role="presentation" style="margin:0; margin-top:25px; padding:0; width:100%; max-width:540px">
                            <tr>
                                <td>
                                    <p style="margin:0; font-size:20px; font-weight:700; line-height:138%; color:#333333; font-family:'Gilroy',sans-serif,Arial,Helvetica">
                                        Заявка №{bid.source_id} ждёт вашего предложения
                                    </p>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding-top:20px">
                                    <table border="0" cellspacing="0" cellpadding="0" role="presentation" style="width:100%">
                                        <!-- Наименование -->
                                        <tr>
                                            <td style="padding:8px 0; border-bottom:1px solid #f2f2f2">
                                                <p style="margin:0; font-size:12px; font-weight:500; color:#828282; font-family:'Gilroy',sans-serif,Arial,Helvetica; text-transform:uppercase; letter-spacing:0.5px">Наименование</p>
                                                <p style="margin:4px 0 0; font-size:17px; font-weight:700; color:#333333; font-family:'Gilroy',sans-serif,Arial,Helvetica">{bid.name}</p>
                                            </td>
                                        </tr>
                                        {brand_row}
                                        {type_row}
                                        <!-- Количество -->
                                        <tr>
                                            <td style="padding:8px 0; border-bottom:1px solid #f2f2f2">
                                                <p style="margin:0; font-size:12px; font-weight:500; color:#828282; font-family:'Gilroy',sans-serif,Arial,Helvetica; text-transform:uppercase; letter-spacing:0.5px">Количество</p>
                                                <p style="margin:4px 0 0; font-size:15px; font-weight:600; color:#333333; font-family:'Gilroy',sans-serif,Arial,Helvetica">{bid.count} шт.</p>
                                            </td>
                                        </tr>
                                        {delivery_row}
                                        {buyer_row}
                                        {desc_block}
                                    </table>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding-top:20px; text-align:center">
                                    <a style="display:inline-block; color:#ffffff; text-align:center; font-family:'Gilroy',sans-serif,Arial,Helvetica; font-size:15px; font-weight:600; line-height:24px; padding:12px 32px; background-color:#27ae60; border-radius:8px; text-decoration:none" href="{cta_url}" target="_blank">
                                        Просмотреть заявку на сайте →
                                    </a>
                                </td>
                            </tr>
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
                                    <a href="{unsubscribe_url if unsubscribe_url else '#'}" target="_blank" style="color:#828282; font-family:'Gilroy',sans-serif,Arial,Helvetica; font-size:12px; font-weight:500; line-height:18px; text-decoration:underline" rel="noopener noreferrer">Отписаться от рассылки</a>
                                </td>
                                <td align="right">
                                    <p style="margin:0; color:#828282; font-family:'Gilroy',sans-serif,Arial,Helvetica; font-size:12px; font-weight:500; line-height:18px">
                                        © Umit. Все права защищены
                                    </p>
                                    {f'<p style="margin:8px 0 0; font-size:10px; color:#aaa;"><a href="{unsubscribe_url}" style="color:#aaa; text-decoration:underline;">Отписаться от рассылки</a></p>' if unsubscribe_url else ''}
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
{f'<img src="{open_tracking_url}" width="1" height="1" alt="" style="display:none;width:1px;height:1px;border:0" />' if open_tracking_url else ''}
</body>
</html>'''


async def send_email(to_email: str, subject: str, html_body: str) -> tuple[bool, int | None]:
    """Send a single email via SMTP, using round-robin across configured accounts.
    Returns (success, smtp_account_id)."""
    from backend.models import SmtpAccount

    # WHITELIST MODE: only send to whitelisted addresses
    if TEST_WHITELIST:
        if to_email not in TEST_WHITELIST:
            logger.info(f"WHITELIST: skipping {to_email} (not in whitelist)")
            return True, None
        else:
            logger.info(f"WHITELIST: sending to {to_email} (whitelisted)")

    # Pick SMTP credentials: try DB accounts first, then .env fallback
    smtp_user = None
    smtp_pass = None
    smtp_host = SMTP_HOST
    smtp_port = SMTP_PORT
    use_tls = (SMTP_PORT == 465)  # SSL only on port 465; port 2525/25 = no TLS
    db_account_id = None

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
                smtp_user = account.email
                smtp_pass = account.password
                smtp_host = account.smtp_host
                smtp_port = account.smtp_port
                use_tls = account.use_tls
                db_account_id = account.id
    except Exception as e:
        logger.warning(f"Failed to fetch SMTP accounts from DB: {e}")

    # Fallback to .env credentials
    if not smtp_user:
        smtp_user = SMTP_USER
        smtp_pass = SMTP_PASS

    if not smtp_user or not smtp_pass:
        logger.warning("No SMTP credentials configured, skipping email")
        return False, None

    sender_email = smtp_user
    domain = sender_email.split("@")[1] if "@" in sender_email else "umit-info.ru"

    msg = MIMEMultipart("alternative")
    msg["From"] = formataddr(("Umit \u2014 \u041c\u0430\u0440\u043a\u0435\u0442\u043f\u043b\u0435\u0439\u0441 \u0437\u0430\u043f\u0447\u0430\u0441\u0442\u0435\u0439", sender_email))
    msg["To"] = to_email
    msg["Subject"] = subject
    msg["Reply-To"] = sender_email
    msg["Message-ID"] = make_msgid(domain=domain)
    msg["Date"] = formatdate(localtime=True)
    msg["List-Unsubscribe"] = f"<mailto:{sender_email}?subject=unsubscribe>"
    msg["X-Mailer"] = "Umit Marketplace Notifications"
    msg["Precedence"] = "bulk"
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        response = await aiosmtplib.send(
            msg,
            hostname=smtp_host,
            port=smtp_port,
            username=smtp_user,
            password=smtp_pass,
            use_tls=use_tls,
        )
        logger.info(f"Email sent to {to_email} via {sender_email}, SMTP: {response}")

        # Update send_count for DB account
        if db_account_id:
            try:
                async with async_session() as db:
                    acc = await db.get(SmtpAccount, db_account_id)
                    if acc:
                        acc.send_count = (acc.send_count or 0) + 1
                        acc.last_used_at = datetime.utcnow()
                        await db.commit()
            except Exception:
                pass

        return True, db_account_id
    except Exception as e:
        logger.error(f"Failed to send email to {to_email} via {sender_email}: {type(e).__name__}: {e}")
        return False, db_account_id


async def validate_email_mx(email: str) -> tuple[bool, str]:
    """Validate email by checking MX records of the domain and pinging via SMTP.
    Returns (is_valid, reason)."""
    import dns.resolver
    import re
    import aiosmtplib

    # Basic syntax check
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return False, "invalid_syntax"

    domain = email.split('@')[1]

    # Known disposable domains
    disposable = {'tempmail.com', 'throwaway.email', 'guerrillamail.com', 'mailinator.com',
                  'yopmail.com', 'trashmail.com', 'sharklasers.com', 'guerrillamailblock.com'}
    if domain.lower() in disposable:
        return False, "disposable_email"

    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        # Sort by preference
        mx_list = sorted([(r.preference, str(r.exchange).rstrip('.')) for r in mx_records])
        if not mx_list:
            return False, "no_mx_records"
            
        # Optional: SMTP Ping (RCPT TO check)
        # We try the primary MX server with a very short timeout.
        mx_host = mx_list[0][1]
        try:
            # We connect to port 25 without TLS initially, as it's standard for MX-to-MX delivery
            smtp = aiosmtplib.SMTP(hostname=mx_host, port=25, timeout=4)
            await smtp.connect()
            await smtp.ehlo(hostname="umit-info.ru")
            await smtp.mail("bounces@umit-info.ru")
            code, message = await smtp.rcpt(email)
            await smtp.quit()
            
            # If server explicitly rejects with a 5xx code (usually 550 User unknown),
            # the user mail address is invalid.
            if code >= 500 and code <= 559:
                return False, f"smtp_user_unknown: {message.strip()}"
        except Exception as e:
            # If the server drops connection, timeouts, or requires STARTTLS etc, 
            # we just let it pass, to avoid false negatives.
            pass

        return True, "ok"
    except dns.resolver.NXDOMAIN:
        return False, "domain_not_found"
    except dns.resolver.NoAnswer:
        return False, "no_mx_records"
    except dns.resolver.Timeout:
        # On timeout, allow sending (don't block legitimate emails)
        return True, "mx_timeout_allowed"
    except Exception as e:
        logger.warning(f"MX validation error for {email}: {e}")
        return True, "mx_check_error_allowed"


async def process_single_bid(session: AsyncSession, bid: Bid, rules: RoutingRule):
    """Process distribution for a single bid — smart search + create batch + send emails."""
    from backend.services.supplier_ai import smart_search_for_bid

    # Get already notified suppliers
    notified_ids = await get_already_notified_supplier_ids(session, bid.id)

    # ── Smart AI search for NEW bids ──
    bid_priorities = {}  # {supplier_id: priority}

    if bid.status == BidStatus.NEW.value:
        logger.info(f"Bid {bid.source_id}: running smart AI search...")
        try:
            search_results = await smart_search_for_bid(bid, target_count=rules.batch_size * 3)

            for item in search_results:
                supplier_data = item["data"]
                priority = item["priority"]
                email = supplier_data["email"].lower().strip()

                # Check if supplier already exists
                existing = (await session.execute(
                    select(Supplier).where(Supplier.email == email)
                )).scalar_one_or_none()

                if existing:
                    bid_priorities[existing.id] = priority
                else:
                    # Create new supplier
                    new_sup = Supplier(
                        company_name=supplier_data.get("company_name", ""),
                        email=email,
                        phone=supplier_data.get("phone", ""),
                        contact_person=supplier_data.get("contact_person", ""),
                        website=supplier_data.get("website", ""),
                        categories=supplier_data.get("categories", []),
                        regions=supplier_data.get("regions", []),
                        description=supplier_data.get("description", ""),
                        source="ai",
                        active=True,
                    )
                    session.add(new_sup)
                    await session.flush()
                    bid_priorities[new_sup.id] = priority
                    logger.info(f"  New supplier: {new_sup.company_name} (P{priority})")

            logger.info(f"Bid {bid.source_id}: smart search found {len(search_results)} suppliers")
        except Exception as e:
            logger.error(f"Smart search failed for bid {bid.source_id}: {e}")

    # Find matching suppliers (sorted by priority)
    matching = await find_matching_suppliers(
        session,
        bid,
        sensitivity=rules.matching_sensitivity,
        exclude_supplier_ids=notified_ids,
        limit=rules.batch_size,
        bid_priorities=bid_priorities,
    )

    if not matching:
        bid.status = BidStatus.FULLY_NOTIFIED.value
        await session.commit()
        logger.info(f"Bid {bid.source_id}: no more suppliers, marked as fully_notified")
        return

    # Determine batch number
    result = await session.execute(
        select(func.max(DistributionBatch.batch_number))
        .where(DistributionBatch.bid_id == bid.id)
    )
    max_batch = result.scalar() or 0
    current_batch_num = max_batch + 1

    # ── Новая схема: размер и delay зависят от номера батча ──
    if current_batch_num == 1:
        actual_batch_size = getattr(rules, 'batch1_size', None) or rules.batch_size
        delay_between = getattr(rules, 'batch1_delay_seconds', None) or 120
    else:
        actual_batch_size = getattr(rules, 'batch2_size', None) or rules.batch_size
        delay_between = getattr(rules, 'batch2_delay_seconds', None) or 120

    # Ограничим matching размером батча
    matching = matching[:actual_batch_size]

    # Escalation timeout: используем escalation_hours (по умолчанию 24ч)
    esc_hours = getattr(rules, 'escalation_hours', None) or 24
    timeout_at = datetime.utcnow() + timedelta(hours=esc_hours)

    # Create new batch
    batch = DistributionBatch(
        bid_id=bid.id,
        batch_number=current_batch_num,
        status=BatchStatus.SENT.value,
        sent_at=datetime.utcnow(),
        timeout_at=timeout_at,
    )
    session.add(batch)
    await session.flush()

    # IMPORTANT: Commit batch creation to release write lock before sending emails
    bid.status = BidStatus.DISTRIBUTING.value
    await session.commit()

    # Send emails and create logs — commit after each to release DB lock
    subject = f"Запрос предложения: {bid.name} (Заявка №{bid.source_id})"

    for supplier, priority in matching:
        # Generate unique click token
        click_token = uuid.uuid4().hex[:16]
        tracking_url = f"{APP_BASE_URL}/api/track/{click_token}"
        open_tracking_url = f"{APP_BASE_URL}/api/track/open/{click_token}"

        # Validate email before sending
        is_valid, reason = await validate_email_mx(supplier.email)
        if not is_valid:
            log = DistributionLog(
                batch_id=batch.id,
                supplier_id=supplier.id,
                email_status=EmailStatus.FAILED.value,
                error_message=f"Email validation failed: {reason}",
                click_token=click_token,
                search_priority=priority,
            )
            session.add(log)
            await session.commit()  # Release lock
            logger.warning(f"Skipped {supplier.email}: {reason}")
            continue

        # Generate unsubscribe token if missing
        if not supplier.unsubscribe_token:
            supplier.unsubscribe_token = uuid.uuid4().hex
            await session.flush()
        unsubscribe_url = f"{APP_BASE_URL}/api/unsubscribe/{supplier.unsubscribe_token}"

        # Build personalized email with tracking + unsubscribe links
        html_body = build_email_html(bid, tracking_url=tracking_url, unsubscribe_url=unsubscribe_url, open_tracking_url=open_tracking_url)
        success, smtp_account_id = await send_email(supplier.email, subject, html_body)

        log = DistributionLog(
            batch_id=batch.id,
            supplier_id=supplier.id,
            email_status=EmailStatus.SENT.value if success else EmailStatus.FAILED.value,
            error_message="" if success else "SMTP send failed",
            sent_at=datetime.utcnow() if success else None,
            click_token=click_token,
            search_priority=priority,
            smtp_account_id=smtp_account_id,
        )
        session.add(log)
        await session.commit()  # Release lock after each email

        await asyncio.sleep(delay_between)

    # Finalize batch status
    batch.status = BatchStatus.WAITING.value
    await session.commit()

    logger.info(f"Bid {bid.source_id}: batch {current_batch_num} sent to {len(matching)} suppliers (delay={delay_between}s, escalation={esc_hours}h)")


async def check_timeouts(session: AsyncSession, rules: RoutingRule):
    """Check for batches that have timed out and escalate."""
    now = datetime.utcnow()

    # Debug: log all waiting batches
    debug_result = await session.execute(
        select(DistributionBatch).where(
            DistributionBatch.status == BatchStatus.WAITING.value
        )
    )
    waiting_batches = debug_result.scalars().all()
    if waiting_batches:
        for wb in waiting_batches:
            logger.info(f"Waiting batch {wb.id} (bid={wb.bid_id}, batch#{wb.batch_number}): "
                       f"timeout_at={wb.timeout_at}, now={now}, "
                       f"timed_out={wb.timeout_at <= now if wb.timeout_at else 'NULL timeout_at'}")
    
    result = await session.execute(
        select(DistributionBatch)
        .where(
            and_(
                DistributionBatch.status == BatchStatus.WAITING.value,
                DistributionBatch.timeout_at.isnot(None),
                DistributionBatch.timeout_at <= now,
            )
        )
    )
    timed_out = result.scalars().all()

    if timed_out:
        logger.info(f"Found {len(timed_out)} timed-out batches to escalate")

    for batch in timed_out:
        batch.status = BatchStatus.TIMEOUT.value

        # Check if any supplier responded (clicked)
        log_result = await session.execute(
            select(DistributionLog).where(
                and_(
                    DistributionLog.batch_id == batch.id,
                    DistributionLog.clicked_at.isnot(None),
                )
            )
        )
        responded = log_result.scalars().all()

        if not responded:
            # Escalate → process next batch for this bid
            batch.status = BatchStatus.ESCALATED.value
            bid = await session.get(Bid, batch.bid_id)
            if bid and bid.status == BidStatus.DISTRIBUTING.value:
                logger.info(f"Escalating bid {bid.source_id}: batch {batch.batch_number} → next batch")
                await process_single_bid(session, bid, rules)

        logger.info(f"Batch {batch.id} timed out. Responded: {len(responded)}. Escalated: {not responded}")

    await session.commit()


async def run_distribution_cycle():
    """Run a single distribution cycle — process new bids + check timeouts.
    Uses separate short sessions to avoid holding DB locks during SMTP operations.
    """
    # Step 1: Get routing rules
    async with async_session() as session:
        result = await session.execute(select(RoutingRule).where(RoutingRule.id == 1))
        rules = result.scalar_one_or_none()
        if not rules:
            rules = RoutingRule(id=1)
            session.add(rules)
            await session.commit()
            # Re-read to detach properly
            result = await session.execute(select(RoutingRule).where(RoutingRule.id == 1))
            rules = result.scalar_one_or_none()

    if not rules or not rules.auto_distribute:
        return

    # Step 2: Expire old bids (short session)
    async with async_session() as session:
        all_active = await session.execute(
            select(Bid).where(Bid.status.in_([BidStatus.NEW.value, BidStatus.DISTRIBUTING.value]))
        )
        for bid in all_active.scalars().all():
            expire_at = bid.created_at + timedelta(days=bid.validity_days or 4)
            if datetime.utcnow() > expire_at:
                bid.status = BidStatus.EXPIRED.value
                logger.info(f"Bid {bid.source_id} expired (created {bid.created_at}, validity {bid.validity_days}d)")
        await session.commit()

    # Step 3: Get new bid IDs (short session, read-only)
    async with async_session() as session:
        result = await session.execute(
            select(Bid.id).where(Bid.status == BidStatus.NEW.value).order_by(Bid.created_at.asc())
        )
        new_bid_ids = [row[0] for row in result.all()]

    # Step 4: Process each bid in its own session (releases lock between bids)
    for bid_id in new_bid_ids:
        try:
            async with async_session() as session:
                bid = await session.get(Bid, bid_id)
                if bid and bid.status == BidStatus.NEW.value:
                    # Re-read rules in this session
                    r = await session.execute(select(RoutingRule).where(RoutingRule.id == 1))
                    rules_local = r.scalar_one_or_none()
                    if rules_local:
                        await process_single_bid(session, bid, rules_local)
            await asyncio.sleep(5)  # Anti-spam: pause between bids
        except Exception as e:
            logger.error(f"Error distributing bid {bid_id}: {e}")

    # Step 5: Check timeouts (short session)
    async with async_session() as session:
        r = await session.execute(select(RoutingRule).where(RoutingRule.id == 1))
        rules_local = r.scalar_one_or_none()
        if rules_local:
            await check_timeouts(session, rules_local)




async def check_unresponsive_suppliers():
    """Check suppliers who never respond and archive them.
    Logic: if a supplier was sent emails from multiple SMTP accounts
    and never clicked/opened, increment no_response_count.
    After max_no_response (configurable) → archive."""
    async with async_session() as session:
        # Get max_no_response from rules
        r = await session.execute(select(RoutingRule).where(RoutingRule.id == 1))
        rules = r.scalar_one_or_none()
        max_nr = (getattr(rules, 'max_no_response', None) or 10) if rules else 10

        # Find suppliers with sent emails but zero clicks/opens
        result = await session.execute(
            select(
                Supplier.id,
                func.count(DistributionLog.id).label('total_sent'),
                func.count(func.distinct(DistributionLog.smtp_account_id)).label('unique_smtp'),
            )
            .join(DistributionLog, DistributionLog.supplier_id == Supplier.id)
            .where(
                and_(
                    Supplier.active == True,
                    Supplier.archived_at.is_(None),
                    DistributionLog.email_status == EmailStatus.SENT.value,
                )
            )
            .group_by(Supplier.id)
            .having(func.count(DistributionLog.id) >= max_nr)
        )

        for row in result.all():
            supplier_id = row[0]
            total_sent = row[1]

            # Check if supplier ever clicked or opened
            click_check = await session.execute(
                select(func.count(DistributionLog.id))
                .where(
                    and_(
                        DistributionLog.supplier_id == supplier_id,
                        DistributionLog.clicked_at.isnot(None),
                    )
                )
            )
            clicks = click_check.scalar() or 0
            if clicks > 0:
                continue  # has responded at least once

            # Archive the supplier
            supplier = await session.get(Supplier, supplier_id)
            if supplier:
                supplier.active = False
                supplier.archived_at = datetime.utcnow()
                supplier.no_response_count = total_sent
                logger.info(f"Archived unresponsive supplier: {supplier.company_name} "
                           f"({supplier.email}) after {total_sent} emails without response")

        await session.commit()


async def distributor_loop():
    """Background loop that runs distribution cycles."""
    logger.info("Distributor loop started")
    distributor_state["running"] = True

    # Backfill timeout_at for batches that were created before the column existed
    await backfill_timeout_at()

    cycle_count = 0
    while True:
        try:
            await run_distribution_cycle()
            distributor_state["last_run"] = datetime.utcnow()
            distributor_state["error"] = None

            # Check unresponsive suppliers every 10 cycles (~10 minutes)
            cycle_count += 1
            if cycle_count % 10 == 0:
                await check_unresponsive_suppliers()
        except Exception as e:
            logger.error(f"Distributor loop error: {e}")
            distributor_state["error"] = str(e)

        await asyncio.sleep(60)

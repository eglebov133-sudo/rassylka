"""
Weekly analytics report — sends every Monday at 9:00 AM (UTC+3).
"""
import asyncio
import logging
import datetime as dt
from sqlalchemy import select, func, and_

from backend.database import async_session
from backend.models import (
    Bid, Supplier, DistributionLog, EmailStatus, SmtpAccount,
)
from backend.services.mail_engine import send_email

logger = logging.getLogger("bidroute.report")


async def generate_report_html() -> tuple[str, dict]:
    """Generate weekly report HTML and stats dict."""
    now = dt.datetime.utcnow()
    week_ago = now - dt.timedelta(days=7)
    two_weeks_ago = now - dt.timedelta(days=14)

    async with async_session() as db:
        # Bids
        bids_week = (await db.execute(
            select(func.count(Bid.id)).where(Bid.parsed_at >= week_ago)
        )).scalar() or 0

        bids_prev = (await db.execute(
            select(func.count(Bid.id)).where(
                and_(Bid.parsed_at >= two_weeks_ago, Bid.parsed_at < week_ago)
            )
        )).scalar() or 0

        # Emails
        sent_week = (await db.execute(
            select(func.count(DistributionLog.id)).where(
                and_(DistributionLog.sent_at >= week_ago,
                     DistributionLog.email_status == EmailStatus.SENT.value)
            )
        )).scalar() or 0

        clicked_week = (await db.execute(
            select(func.count(DistributionLog.id)).where(
                and_(DistributionLog.clicked_at >= week_ago,
                     DistributionLog.clicked_at.isnot(None))
            )
        )).scalar() or 0

        failed_week = (await db.execute(
            select(func.count(DistributionLog.id)).where(
                and_(DistributionLog.sent_at >= week_ago,
                     DistributionLog.email_status == EmailStatus.FAILED.value)
            )
        )).scalar() or 0

        # Previous week click rate
        sent_prev = (await db.execute(
            select(func.count(DistributionLog.id)).where(
                and_(DistributionLog.sent_at >= two_weeks_ago,
                     DistributionLog.sent_at < week_ago,
                     DistributionLog.email_status == EmailStatus.SENT.value)
            )
        )).scalar() or 0

        clicked_prev = (await db.execute(
            select(func.count(DistributionLog.id)).where(
                and_(DistributionLog.clicked_at >= two_weeks_ago,
                     DistributionLog.clicked_at < week_ago,
                     DistributionLog.clicked_at.isnot(None))
            )
        )).scalar() or 0

        rate_this = round(clicked_week / sent_week * 100, 1) if sent_week > 0 else 0
        rate_prev = round(clicked_prev / sent_prev * 100, 1) if sent_prev > 0 else 0
        spam_alert = rate_prev > 0 and rate_this < rate_prev * 0.5

        # Top categories
        cat_result = await db.execute(
            select(Bid.spare_part_type, func.count(Bid.id).label("cnt"))
            .where(and_(Bid.spare_part_type != "", Bid.parsed_at >= week_ago))
            .group_by(Bid.spare_part_type)
            .order_by(func.count(Bid.id).desc())
            .limit(5)
        )
        top_cats = cat_result.fetchall()

        # Top suppliers
        sup_result = await db.execute(
            select(Supplier.company_name, Supplier.email,
                   func.count(DistributionLog.id).label("clicks"))
            .join(DistributionLog, DistributionLog.supplier_id == Supplier.id)
            .where(and_(DistributionLog.clicked_at >= week_ago,
                        DistributionLog.clicked_at.isnot(None)))
            .group_by(Supplier.id)
            .order_by(func.count(DistributionLog.id).desc())
            .limit(5)
        )
        top_sups = sup_result.fetchall()

        # SMTP accounts status
        smtp_count = (await db.execute(
            select(func.count(SmtpAccount.id)).where(SmtpAccount.active == True)
        )).scalar() or 0

    stats = {
        "bids_week": bids_week, "bids_prev": bids_prev,
        "sent_week": sent_week, "clicked_week": clicked_week,
        "failed_week": failed_week,
        "rate_this": rate_this, "rate_prev": rate_prev,
        "spam_alert": spam_alert, "smtp_count": smtp_count,
    }

    # Generate HTML
    period = f"{(now - dt.timedelta(days=7)).strftime('%d.%m.%Y')} — {now.strftime('%d.%m.%Y')}"

    spam_block = ""
    if spam_alert:
        spam_block = """
        <tr><td colspan="2" style="padding:12px;background:#ff4444;color:#fff;font-weight:bold;text-align:center;border-radius:8px">
            ⚠️ ВНИМАНИЕ: Процент переходов упал более чем на 50%! Возможно, адрес попал в спам.
        </td></tr>
        """

    cats_rows = "".join(
        f'<tr><td style="padding:6px 12px">{r[0] or "—"}</td><td style="padding:6px 12px;text-align:right;font-weight:bold">{r[1]}</td></tr>'
        for r in top_cats
    ) or '<tr><td colspan="2" style="padding:6px 12px;color:#999">Нет данных</td></tr>'

    sups_rows = "".join(
        f'<tr><td style="padding:6px 12px">{r[0]}<br><small style="color:#999">{r[1]}</small></td><td style="padding:6px 12px;text-align:right;font-weight:bold">{r[2]}</td></tr>'
        for r in top_sups
    ) or '<tr><td colspan="2" style="padding:6px 12px;color:#999">Нет кликов</td></tr>'

    bids_diff = bids_week - bids_prev
    bids_arrow = f'<span style="color:{"#22c55e" if bids_diff >= 0 else "#ef4444"}">{"↑" if bids_diff >= 0 else "↓"} {abs(bids_diff)}</span>'

    html = f"""
    <html><body style="font-family:Inter,Arial,sans-serif;background:#f5f7fa;margin:0;padding:20px">
    <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08)">
        <div style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:24px;color:#fff;text-align:center">
            <h1 style="margin:0;font-size:22px">📊 Еженедельный отчёт Umit</h1>
            <p style="margin:8px 0 0;opacity:0.8;font-size:14px">{period}</p>
        </div>

        <div style="padding:24px">
            {spam_block}

            <h3 style="margin:0 0 12px;font-size:16px;color:#333">Основные показатели</h3>
            <table style="width:100%;border-collapse:collapse;margin-bottom:24px">
                <tr style="background:#f8fafc"><td style="padding:10px 12px">Заявок обработано</td><td style="padding:10px 12px;text-align:right;font-weight:bold;font-size:18px">{bids_week} {bids_arrow}</td></tr>
                <tr><td style="padding:10px 12px">Писем отправлено</td><td style="padding:10px 12px;text-align:right;font-weight:bold;font-size:18px">{sent_week}</td></tr>
                <tr style="background:#f8fafc"><td style="padding:10px 12px">Кликов по ссылкам</td><td style="padding:10px 12px;text-align:right;font-weight:bold;font-size:18px;color:#22c55e">{clicked_week}</td></tr>
                <tr><td style="padding:10px 12px">Ошибок отправки</td><td style="padding:10px 12px;text-align:right;font-weight:bold;font-size:18px;color:{"#ef4444" if failed_week > 0 else "#666"}">{failed_week}</td></tr>
                <tr style="background:#f8fafc"><td style="padding:10px 12px">% переходов</td><td style="padding:10px 12px;text-align:right;font-weight:bold;font-size:18px">{rate_this}%<small style="color:#999;font-size:12px"> (пред. {rate_prev}%)</small></td></tr>
                <tr><td style="padding:10px 12px">SMTP-аккаунтов</td><td style="padding:10px 12px;text-align:right;font-weight:bold">{smtp_count}</td></tr>
            </table>

            <h3 style="margin:0 0 12px;font-size:16px;color:#333">Топ-5 категорий</h3>
            <table style="width:100%;border-collapse:collapse;margin-bottom:24px;background:#f8fafc;border-radius:8px">
                <tr style="border-bottom:1px solid #e2e8f0"><th style="padding:8px 12px;text-align:left;font-size:13px;color:#999">Категория</th><th style="padding:8px 12px;text-align:right;font-size:13px;color:#999">Заявок</th></tr>
                {cats_rows}
            </table>

            <h3 style="margin:0 0 12px;font-size:16px;color:#333">Топ-5 активных поставщиков</h3>
            <table style="width:100%;border-collapse:collapse;background:#f8fafc;border-radius:8px">
                <tr style="border-bottom:1px solid #e2e8f0"><th style="padding:8px 12px;text-align:left;font-size:13px;color:#999">Поставщик</th><th style="padding:8px 12px;text-align:right;font-size:13px;color:#999">Кликов</th></tr>
                {sups_rows}
            </table>
        </div>

        <div style="padding:16px 24px;background:#f8fafc;text-align:center;font-size:12px;color:#999">
            Автоматический отчёт системы BidRoute AI · <a href="https://umit-info.ru" style="color:#6366f1">Перейти в панель</a>
        </div>
    </div>
    </body></html>
    """

    return html, stats


async def send_weekly_report():
    """Generate and send the weekly analytics report."""
    import os
    admin_emails_str = os.getenv("REPORT_EMAILS", os.getenv("SMTP_USER", ""))
    admin_emails = [e.strip() for e in admin_emails_str.split(",") if e.strip()]

    if not admin_emails:
        logger.warning("No REPORT_EMAILS configured, skipping weekly report")
        return

    html, stats = await generate_report_html()
    subject = f"📊 Umit: Еженедельный отчёт ({dt.datetime.utcnow().strftime('%d.%m.%Y')})"

    for email in admin_emails:
        ok = await send_email(email, subject, html)
        logger.info(f"Weekly report to {email}: {'OK' if ok else 'FAIL'}")

    if stats.get("spam_alert"):
        logger.warning("SPAM ALERT: Click rate dropped >50% week-over-week!")


async def report_scheduler():
    """Background loop — sends report every Monday at 6:00 UTC (9:00 MSK)."""
    logger.info("Weekly report scheduler started")
    while True:
        try:
            now = dt.datetime.utcnow()
            # Next Monday 6:00 UTC
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0 and now.hour >= 6:
                days_until_monday = 7
            next_monday = now.replace(hour=6, minute=0, second=0, microsecond=0) + dt.timedelta(days=days_until_monday)
            wait_seconds = (next_monday - now).total_seconds()

            logger.info(f"Next weekly report at {next_monday} (in {wait_seconds/3600:.1f}h)")
            await asyncio.sleep(wait_seconds)

            await send_weekly_report()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Report scheduler error: {e}")
            await asyncio.sleep(3600)  # Retry in an hour

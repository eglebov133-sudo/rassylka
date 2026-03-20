"""
Auto Supplier Search — background AI-powered supplier discovery.

Runs once per day, collects unique categories from recent bids,
and searches for new suppliers via Perplexity AI.
"""
import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, func, and_

from backend.database import async_session
from backend.models import Bid, Supplier, RoutingRule
from backend.services.supplier_ai import _call_ai

logger = logging.getLogger("bidroute.auto_supplier_search")


async def auto_search_cycle():
    """Run one cycle of auto supplier search.
    Collects categories from recent bids and searches for new suppliers."""
    async with async_session() as session:
        # Check if auto search is enabled
        r = await session.execute(select(RoutingRule).where(RoutingRule.id == 1))
        rules = r.scalar_one_or_none()
        if not rules or not getattr(rules, 'auto_supplier_search', True):
            logger.info("Auto supplier search is disabled")
            return 0

        # Get unique categories from bids in the last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)
        cat_result = await session.execute(
            select(Bid.spare_part_type)
            .where(and_(
                Bid.parsed_at >= week_ago,
                Bid.spare_part_type != "",
                Bid.spare_part_type.isnot(None),
            ))
            .group_by(Bid.spare_part_type)
            .limit(10)
        )
        categories = [row[0] for row in cat_result.all() if row[0]]

        # Also get unique brands
        brand_result = await session.execute(
            select(Bid.brand)
            .where(and_(
                Bid.parsed_at >= week_ago,
                Bid.brand != "",
                Bid.brand.isnot(None),
            ))
            .group_by(Bid.brand)
            .limit(5)
        )
        brands = [row[0] for row in brand_result.all() if row[0]]

    if not categories and not brands:
        logger.info("No recent categories/brands to search for")
        return 0

    total_added = 0

    # Search by categories
    for category in categories[:5]:
        prompt = (
            f"Найди поставщиков запасных частей категории \"{category}\" в России. "
            f"Нужны прямые поставщики с реальными email-адресами, "
            f"у которых есть товары В НАЛИЧИИ на складе."
        )
        try:
            results = await _call_ai(prompt)
            added = await _save_new_suppliers(results, source_query=f"auto: {category}")
            total_added += added
            logger.info(f"Auto search [{category}]: found {len(results)}, added {added} new")
            await asyncio.sleep(10)  # Pause between AI calls
        except Exception as e:
            logger.error(f"Auto search error for [{category}]: {e}")

    # Search by brands
    for brand in brands[:3]:
        prompt = (
            f"Найди поставщиков запасных частей для техники {brand} в России. "
            f"Нужны прямые поставщики и дилеры с реальными email-адресами."
        )
        try:
            results = await _call_ai(prompt)
            added = await _save_new_suppliers(results, source_query=f"auto: {brand}")
            total_added += added
            logger.info(f"Auto search [{brand}]: found {len(results)}, added {added} new")
            await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"Auto search error for [{brand}]: {e}")

    logger.info(f"Auto supplier search complete: {total_added} new suppliers added")
    return total_added


async def _save_new_suppliers(results: list, source_query: str = "") -> int:
    """Save new suppliers to DB, skipping duplicates by email."""
    added = 0
    async with async_session() as session:
        for data in results:
            email = data.get("email", "").lower().strip()
            if not email:
                continue

            # Check duplicate
            existing = (await session.execute(
                select(Supplier).where(Supplier.email == email)
            )).scalar_one_or_none()

            if existing:
                continue

            supplier = Supplier(
                company_name=data.get("company_name", ""),
                email=email,
                phone=data.get("phone", ""),
                contact_person=data.get("contact_person", ""),
                website=data.get("website", ""),
                categories=data.get("categories", []),
                regions=data.get("regions", []),
                description=data.get("description", ""),
                source="ai",
                ai_search_query=source_query,
                active=True,
            )
            session.add(supplier)
            added += 1

        if added > 0:
            await session.commit()

    return added


async def auto_search_loop():
    """Background loop — runs auto supplier search once per 24 hours."""
    logger.info("Auto supplier search loop started")

    # Wait 5 minutes on startup to let other services initialize
    await asyncio.sleep(300)

    while True:
        try:
            count = await auto_search_cycle()
            logger.info(f"Auto search cycle done: {count} new suppliers")
        except Exception as e:
            logger.error(f"Auto search loop error: {e}")

        # Sleep 24 hours
        await asyncio.sleep(24 * 60 * 60)

"""
Bid Parser Service — polls umit.pro API for new bids.
"""
import os
import asyncio
import logging
from datetime import datetime
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import async_session
from backend.models import Bid, BidStatus

logger = logging.getLogger("bidroute.parser")

UMIT_API_URL = os.getenv("UMIT_API_URL", "https://umit-prod.purpleplane-it.com/api/v2/bids/")
PARSE_INTERVAL = int(os.getenv("PARSE_INTERVAL_MINUTES", "5")) * 60

# Module-level state for UI status reporting
parser_state = {
    "running": False,
    "last_run": None,
    "last_count": 0,
    "error": None,
}


async def fetch_bids_page(client: httpx.AsyncClient, page: int = 1, page_size: int = 20) -> dict:
    """Fetch a single page of bids from umit.pro API."""
    resp = await client.get(
        UMIT_API_URL,
        params={"format": "json", "page": page, "page_size": page_size},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def _extract_text(value) -> str:
    """Extract text from a value that may be a string, dict {id, name}, or None."""
    if value is None:
        return ""
    if isinstance(value, dict):
        return value.get("name", "") or ""
    return str(value)


def parse_bid_data(item: dict) -> dict:
    """Extract structured data from single API bid item."""
    technique = item.get("technique_card") or {}
    brand = ""
    model_name = ""
    year = ""

    if technique:
        # technique_card has nested structure: car.brand.name, car.model.name, car.year
        car = technique.get("car") or {}
        special = technique.get("special_vehicle") or {}

        # Try car first, then special_vehicle
        source = car if car else special

        if source:
            brand_obj = source.get("brand") or {}
            model_obj = source.get("model") or {}
            brand = brand_obj.get("name", "") if isinstance(brand_obj, dict) else str(brand_obj or "")
            model_name = model_obj.get("name", "") if isinstance(model_obj, dict) else str(model_obj or "")
            year = str(source.get("year", "")) if source.get("year") else ""

    # spare_part_type can be a dict {"id": 18, "name": "..."} or a string
    spt = item.get("spare_part_type", "")
    if isinstance(spt, dict):
        spt = spt.get("name", "")

    # delivery_place
    delivery = item.get("delivery_place", "")
    if isinstance(delivery, dict):
        delivery = delivery.get("name", "") or delivery.get("city", "") or str(delivery)

    return {
        "source_id": item.get("id"),
        "name": _extract_text(item.get("name", "")),
        "brand": brand,
        "model": model_name,
        "year": year,
        "spare_part_type": _extract_text(str(spt)),
        "count": item.get("count", 1) or 1,
        "delivery_place": _extract_text(str(delivery)),
        "description": _extract_text(item.get("description", "")),
        "buyer_name": _extract_text(item.get("buyer_name", "")),
        "delivery_method": _extract_text(item.get("delivery_method", "")),
        "taxation": _extract_text(item.get("taxation", "")),
        "validity_days": item.get("relevance_in_days", 5) or item.get("validity_days", 5) or 5,
        "source_url": f"https://umit.pro/public-bids/{item.get('id', '')}",
    }


async def upsert_bid(session: AsyncSession, data: dict) -> bool:
    """Insert or update a bid. Returns True if new bid created."""
    result = await session.execute(
        select(Bid).where(Bid.source_id == data["source_id"])
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update non-critical fields
        for key in ("name", "description", "count", "delivery_place", "spare_part_type"):
            if data.get(key):
                setattr(existing, key, data[key])
        return False
    else:
        bid = Bid(
            **data,
            status=BidStatus.NEW.value,
            created_at=datetime.utcnow(),
            parsed_at=datetime.utcnow(),
        )
        session.add(bid)
        return True


async def run_parse_cycle() -> int:
    """Run a single parse cycle. Returns count of new bids."""
    new_count = 0
    async with httpx.AsyncClient(
        headers={"User-Agent": "BidRoute/1.0 (automated procurement parser)"}
    ) as client:
        try:
            # Fetch first 2 pages (40 most recent bids)
            for page in range(1, 3):
                data = await fetch_bids_page(client, page=page, page_size=20)
                results = data.get("results", data) if isinstance(data, dict) else data

                if isinstance(results, list):
                    items = results
                else:
                    items = results.get("results", []) if isinstance(results, dict) else []

                if not items:
                    break

                async with async_session() as session:
                    for item in items:
                        try:
                            bid_data = parse_bid_data(item)
                            if bid_data["source_id"]:
                                is_new = await upsert_bid(session, bid_data)
                                if is_new:
                                    new_count += 1
                        except Exception as e:
                            logger.error(f"Error processing bid {item.get('id')}: {e}")
                            await session.rollback()
                            continue

                    await session.commit()

                await asyncio.sleep(1.0)  # Throttle between pages

        except Exception as e:
            logger.error(f"Parse cycle error: {e}")
            parser_state["error"] = str(e)

    return new_count


async def get_parse_interval() -> int:
    """Read parse interval from DB routing rules, fallback to env var."""
    try:
        from backend.models import RoutingRule
        async with async_session() as session:
            result = await session.execute(select(RoutingRule).where(RoutingRule.id == 1))
            rules = result.scalar_one_or_none()
            if rules and hasattr(rules, 'parse_interval_minutes') and rules.parse_interval_minutes:
                return rules.parse_interval_minutes * 60
    except Exception:
        pass
    return PARSE_INTERVAL


async def parser_loop():
    """Background loop that runs parse cycles at configured intervals."""
    logger.info(f"Parser loop started. Default interval: {PARSE_INTERVAL}s")
    parser_state["running"] = True

    while True:
        try:
            new_count = await run_parse_cycle()
            parser_state["last_run"] = datetime.utcnow()
            parser_state["last_count"] = new_count
            parser_state["error"] = None
            logger.info(f"Parse cycle complete. New bids: {new_count}")
        except Exception as e:
            logger.error(f"Parser loop error: {e}")
            parser_state["error"] = str(e)

        interval = await get_parse_interval()
        await asyncio.sleep(interval)

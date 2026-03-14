"""
Supplier Matching Engine — matches bids to suppliers by priority, categories, regions.

Uses search_priority from smart AI search when available,
falls back to keyword/category/region scoring.
"""
import logging
from typing import List, Tuple

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Supplier, DistributionLog, DistributionBatch, Bid

logger = logging.getLogger("bidroute.matching")


async def find_matching_suppliers(
    session: AsyncSession,
    bid: Bid,
    sensitivity: float = 0.75,
    exclude_supplier_ids: List[int] = None,
    limit: int = 5,
    bid_priorities: dict = None,  # {supplier_id: priority}
) -> List[Tuple[Supplier, int]]:
    """
    Find suppliers matching a bid, sorted by priority then score.
    
    Returns list of (Supplier, priority) tuples.
    priority: 1-8 from smart search, 9 for keyword-only matches.
    """
    exclude_ids = exclude_supplier_ids or []
    priorities = bid_priorities or {}

    # Get all active suppliers not yet contacted
    query = select(Supplier).where(
        and_(
            Supplier.active == True,
            Supplier.id.notin_(exclude_ids) if exclude_ids else True,
        )
    )
    result = await session.execute(query)
    all_suppliers = result.scalars().all()

    # Score each supplier
    scored = []
    bid_keywords = _extract_keywords(bid)

    for supplier in all_suppliers:
        priority = priorities.get(supplier.id, 0)
        score = _calculate_match_score(bid, supplier, bid_keywords)
        
        if priority > 0:
            # Supplier found by smart search — always include
            scored.append((supplier, priority, score))
        elif score >= (1.0 - sensitivity):
            # Keyword match — priority 9 (lowest)
            scored.append((supplier, 9, score))

    # Sort: best priority first, then highest score
    scored.sort(key=lambda x: (x[1], -x[2]))
    return [(s, p) for s, p, _ in scored[:limit]]


def _extract_keywords(bid: Bid) -> set:
    """Extract keywords from bid fields."""
    keywords = set()
    for field in (bid.name, bid.brand, bid.model, bid.spare_part_type, bid.description):
        if field:
            words = field.lower().replace(",", " ").replace(".", " ").split()
            keywords.update(w.strip() for w in words if len(w.strip()) > 2)
    return keywords


def _calculate_match_score(bid: Bid, supplier: Supplier, bid_keywords: set) -> float:
    """Calculate match score between bid and supplier (0.0 - 1.0)."""
    score = 0.0
    max_score = 0.0

    # Category matching (weight: 0.5)
    max_score += 0.5
    supplier_categories = supplier.categories or []
    if supplier_categories:
        cat_keywords = set()
        for cat in supplier_categories:
            words = cat.lower().replace(",", " ").replace(".", " ").split()
            cat_keywords.update(w.strip() for w in words if len(w.strip()) > 2)

        if cat_keywords and bid_keywords:
            overlap = len(cat_keywords & bid_keywords)
            if overlap > 0:
                score += 0.5 * min(overlap / max(len(bid_keywords), 1), 1.0)
    else:
        score += 0.15

    # Region matching (weight: 0.3)
    max_score += 0.3
    supplier_regions = supplier.regions or []
    if bid.delivery_place and supplier_regions:
        bid_place = bid.delivery_place.lower()
        for region in supplier_regions:
            if region.lower() in bid_place or bid_place in region.lower():
                score += 0.3
                break
    elif not supplier_regions:
        score += 0.1

    # Brand matching (weight: 0.2)
    max_score += 0.2
    if bid.brand:
        supplier_desc = (supplier.description or "").lower()
        supplier_cats_text = " ".join(supplier_categories).lower()
        combined = supplier_desc + " " + supplier_cats_text
        if bid.brand.lower() in combined:
            score += 0.2

    return score / max_score if max_score > 0 else 0.0


async def get_already_notified_supplier_ids(session: AsyncSession, bid_id: int) -> List[int]:
    """Get IDs of suppliers already notified for a given bid."""
    result = await session.execute(
        select(DistributionLog.supplier_id)
        .join(DistributionBatch, DistributionBatch.id == DistributionLog.batch_id)
        .where(DistributionBatch.bid_id == bid_id)
    )
    return [row[0] for row in result.all()]

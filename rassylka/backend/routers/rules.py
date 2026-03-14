from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import RoutingRule
from backend.schemas import RoutingRuleResponse, RoutingRuleUpdate

router = APIRouter(prefix="/api/rules", tags=["rules"])


async def get_or_create_rules(db: AsyncSession) -> RoutingRule:
    result = await db.execute(select(RoutingRule).where(RoutingRule.id == 1))
    rules = result.scalar_one_or_none()
    if not rules:
        rules = RoutingRule(id=1)
        db.add(rules)
        await db.commit()
        await db.refresh(rules)
    return rules


@router.get("", response_model=RoutingRuleResponse)
async def get_rules(db: AsyncSession = Depends(get_db)):
    rules = await get_or_create_rules(db)
    return RoutingRuleResponse.model_validate(rules)


@router.put("", response_model=RoutingRuleResponse)
async def update_rules(data: RoutingRuleUpdate, db: AsyncSession = Depends(get_db)):
    rules = await get_or_create_rules(db)

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rules, key, value)

    rules.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(rules)
    return RoutingRuleResponse.model_validate(rules)

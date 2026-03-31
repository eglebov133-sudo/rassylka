"""
Promotion Catalog API — CRUD for car brands, models, and part categories.
"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from typing import Optional

from backend.database import async_session
from backend.models import CarBrand, CarModel, PartCategory

logger = logging.getLogger("bidroute.promotion_catalog")
router = APIRouter(prefix="/api/promotion", tags=["promotion-catalog"])


# ── Schemas ──

class BrandIn(BaseModel):
    name: str
    name_ru: str = ""


class ModelIn(BaseModel):
    name: str
    name_ru: str = ""
    popular: bool = False


class PartIn(BaseModel):
    name: str
    name_ru: str = ""
    cluster: str = ""


# ═══════════════════════════════════════════════════
#  Brands
# ═══════════════════════════════════════════════════

@router.get("/brands")
async def get_brands():
    """Get all car brands with model counts."""
    async with async_session() as db:
        brands = (await db.execute(
            select(CarBrand).order_by(CarBrand.name)
        )).scalars().all()

        # Count models per brand
        counts = {}
        for b in brands:
            cnt = (await db.execute(
                select(func.count(CarModel.id)).where(CarModel.brand_id == b.id)
            )).scalar() or 0
            counts[b.id] = cnt

    return {
        "brands": [
            {
                "id": b.id,
                "name": b.name,
                "name_ru": b.name_ru,
                "active": b.active,
                "model_count": counts.get(b.id, 0),
            }
            for b in brands
        ],
        "total": len(brands),
    }


@router.post("/brands")
async def create_brand(data: BrandIn):
    """Create a new car brand."""
    async with async_session() as db:
        existing = (await db.execute(
            select(CarBrand).where(CarBrand.name == data.name)
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(400, f"Марка '{data.name}' уже существует")

        brand = CarBrand(name=data.name, name_ru=data.name_ru, active=True)
        db.add(brand)
        await db.commit()
        return {"id": brand.id, "name": brand.name, "message": "Марка добавлена"}


@router.delete("/brands/{brand_id}")
async def delete_brand(brand_id: int):
    """Delete a brand and all its models."""
    async with async_session() as db:
        brand = await db.get(CarBrand, brand_id)
        if not brand:
            raise HTTPException(404, "Марка не найдена")
        await db.delete(brand)
        await db.commit()
    return {"ok": True, "message": f"Марка '{brand.name}' удалена"}


# ═══════════════════════════════════════════════════
#  Models
# ═══════════════════════════════════════════════════

@router.get("/brands/{brand_id}/models")
async def get_models(brand_id: int):
    """Get all models for a brand."""
    async with async_session() as db:
        brand = await db.get(CarBrand, brand_id)
        if not brand:
            raise HTTPException(404, "Марка не найдена")

        models = (await db.execute(
            select(CarModel)
            .where(CarModel.brand_id == brand_id)
            .order_by(CarModel.popular.desc(), CarModel.name)
        )).scalars().all()

    return {
        "brand": {"id": brand.id, "name": brand.name, "name_ru": brand.name_ru},
        "models": [
            {
                "id": m.id,
                "name": m.name,
                "name_ru": m.name_ru,
                "popular": m.popular,
                "active": m.active,
            }
            for m in models
        ],
        "total": len(models),
    }


@router.post("/brands/{brand_id}/models")
async def create_model(brand_id: int, data: ModelIn):
    """Add a model to a brand."""
    async with async_session() as db:
        brand = await db.get(CarBrand, brand_id)
        if not brand:
            raise HTTPException(404, "Марка не найдена")

        model = CarModel(
            brand_id=brand_id,
            name=data.name,
            name_ru=data.name_ru,
            popular=data.popular,
            active=True,
        )
        db.add(model)
        await db.commit()
    return {"id": model.id, "name": model.name, "message": "Модель добавлена"}


@router.delete("/models/{model_id}")
async def delete_model(model_id: int):
    """Delete a model."""
    async with async_session() as db:
        model = await db.get(CarModel, model_id)
        if not model:
            raise HTTPException(404, "Модель не найдена")
        name = model.name
        await db.delete(model)
        await db.commit()
    return {"ok": True, "message": f"Модель '{name}' удалена"}


# ═══════════════════════════════════════════════════
#  Part Categories
# ═══════════════════════════════════════════════════

@router.get("/parts")
async def get_parts():
    """Get all part categories grouped by cluster."""
    async with async_session() as db:
        parts = (await db.execute(
            select(PartCategory).order_by(PartCategory.cluster, PartCategory.name)
        )).scalars().all()

    # Group by cluster
    clusters = {}
    for p in parts:
        if p.cluster not in clusters:
            clusters[p.cluster] = []
        clusters[p.cluster].append({
            "id": p.id,
            "name": p.name,
            "name_ru": p.name_ru,
            "cluster": p.cluster,
            "active": p.active,
        })

    return {"parts": [p.__dict__ | {"_sa_instance_state": None} for p in parts] if False else [
        {"id": p.id, "name": p.name, "name_ru": p.name_ru, "cluster": p.cluster, "active": p.active}
        for p in parts
    ], "clusters": clusters, "total": len(parts)}


@router.post("/parts")
async def create_part(data: PartIn):
    """Add a part category."""
    async with async_session() as db:
        existing = (await db.execute(
            select(PartCategory).where(PartCategory.name == data.name)
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(400, f"Категория '{data.name}' уже существует")

        part = PartCategory(name=data.name, name_ru=data.name_ru, cluster=data.cluster, active=True)
        db.add(part)
        await db.commit()
    return {"id": part.id, "name": part.name, "message": "Категория добавлена"}


@router.delete("/parts/{part_id}")
async def delete_part(part_id: int):
    """Delete a part category."""
    async with async_session() as db:
        part = await db.get(PartCategory, part_id)
        if not part:
            raise HTTPException(404, "Категория не найдена")
        name = part.name
        await db.delete(part)
        await db.commit()
    return {"ok": True, "message": f"Категория '{name}' удалена"}


# ═══════════════════════════════════════════════════
#  Seed endpoint
# ═══════════════════════════════════════════════════

@router.post("/seed-catalog")
async def trigger_seed():
    """Seed the catalog with default brands, models, and parts."""
    from backend.services.seed_catalog import seed_catalog
    result = await seed_catalog()
    return {"ok": True, **result}


# ═══════════════════════════════════════════════════
#  Keywords preview & generation
# ═══════════════════════════════════════════════════

@router.get("/keywords/preview")
async def preview_keywords():
    """Preview keyword counts for all brands (quick summary)."""
    from backend.services.keyword_generator import preview_all_brands
    return await preview_all_brands()


@router.get("/keywords/generate/{brand_id}")
async def generate_keywords(brand_id: int):
    """Generate full keyword set for a brand (groups, keywords, ads)."""
    from backend.services.keyword_generator import generate_keywords_for_brand
    result = await generate_keywords_for_brand(brand_id)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


# ═══════════════════════════════════════════════════
#  Batch campaign creation
# ═══════════════════════════════════════════════════

class BatchCreateIn(BaseModel):
    brand_ids: list[int]
    geo_segments: list[str] = ["msk_spb", "regions"]
    daily_budget: float = 150.0
    base_url: str = "https://umit.pro"


@router.post("/campaigns/batch")
async def batch_create(data: BatchCreateIn):
    """Launch batch campaign creation for selected brands."""
    from backend.services.batch_campaign_creator import BATCH_PROGRESS, batch_create_campaigns
    import asyncio

    if BATCH_PROGRESS.get("running"):
        raise HTTPException(409, "Пакетное создание уже запущено")

    if not data.brand_ids:
        raise HTTPException(400, "Выберите хотя бы одну марку")

    # Launch as background task
    asyncio.create_task(batch_create_campaigns(
        brand_ids=data.brand_ids,
        geo_segments=data.geo_segments,
        daily_budget=data.daily_budget,
        base_url=data.base_url,
    ))

    return {"ok": True, "message": f"Запущено создание для {len(data.brand_ids)} марок"}


@router.get("/campaigns/batch/progress")
async def batch_progress():
    """Poll batch creation progress."""
    from backend.services.batch_campaign_creator import BATCH_PROGRESS
    return BATCH_PROGRESS



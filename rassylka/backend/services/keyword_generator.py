"""
Keyword Generator for Yandex Direct campaigns.
Generates keyword phrases from brand × model × part category × template matrix.
Groups them semantically to avoid "мало показов" (too few impressions).
"""
import logging
from typing import Optional
from backend.database import async_session
from backend.models import CarBrand, CarModel, PartCategory
from sqlalchemy import select

logger = logging.getLogger("bidroute.keyword_generator")


# ═══════════════════════════════════════════════════
#  Keyword phrase templates
# ═══════════════════════════════════════════════════

TEMPLATES = [
    "купить {part} {brand} {model}",
    "{part} {brand} {model} цена",
    "{part} на {brand} {model}",
    "{part} для {brand} {model} купить",
    "заказать {part} {brand} {model}",
]

# Alternative templates with Russian brand names
TEMPLATES_RU = [
    "купить {part} {brand_ru} {model}",
    "{part} {brand_ru} {model} цена",
    "{part} на {brand_ru} {model}",
]


# ═══════════════════════════════════════════════════
#  Negative keywords (campaign-level)
# ═══════════════════════════════════════════════════

NEGATIVE_KEYWORDS = [
    "бесплатно", "скачать", "реферат", "своими руками", "форум",
    "отзывы", "фото", "видео", "инструкция", "схема", "мануал",
    "ремонт", "разборка", "бу", "авторазбор", "разбор",
    "выкуп", "сдать", "утилизация", "чертеж", "размеры",
    "каталог номеров", "артикул",
]


# ═══════════════════════════════════════════════════
#  Ad templates
# ═══════════════════════════════════════════════════

def generate_ad_texts(brand: str, model: str, cluster: str) -> list[dict]:
    """Generate 2 ad variants for a given brand/model/cluster."""
    cluster_titles = {
        "тормоза": "Тормозные запчасти",
        "подвеска": "Подвеска и рулевое",
        "привод": "Привод и трансмиссия",
        "двигатель": "Запчасти двигателя",
        "фильтры": "Фильтры и расходники",
        "электрика": "Электрика",
        "кузов": "Кузовные запчасти",
        "выхлоп": "Выхлопная система",
    }

    cluster_name = cluster_titles.get(cluster, cluster.capitalize())

    ads = [
        {
            "title1": f"{cluster_name} {brand} {model} — в наличии"[:56],
            "title2": "Доставка по всей России"[:30],
            "text": f"Оригинал и аналоги по выгодным ценам. Подбор по VIN. Быстрая отправка. Заявка на umit.pro!"[:81],
        },
        {
            "title1": f"Купить {cluster_name.lower()} на {brand} {model}"[:56],
            "title2": "Цены от поставщиков"[:30],
            "text": f"Сравните предложения от проверенных компаний. Гарантия качества. Доставка 1-3 дня!"[:81],
        },
    ]
    return ads


def generate_autotarget_ad(brand: str) -> list[dict]:
    """Generate ad for autotarget group (no keywords)."""
    return [
        {
            "title1": f"Запчасти {brand} — сравните цены"[:56],
            "title2": "Заявка за 2 минуты"[:30],
            "text": "Более 100 поставщиков. Подбор по марке и модели. Оригинал и аналоги. Доставка по России!"[:81],
        },
    ]


# ═══════════════════════════════════════════════════
#  Main generator
# ═══════════════════════════════════════════════════

async def generate_keywords_for_brand(brand_id: int) -> dict:
    """
    Generate all keyword groups for a brand.

    Returns:
    {
        "brand": "Toyota",
        "groups": [
            {
                "name": "Toyota Camry — тормоза",
                "model": "Camry",
                "cluster": "тормоза",
                "keywords": ["купить тормозные колодки toyota camry", ...],
                "ads": [{"title1": ..., "title2": ..., "text": ...}, ...],
                "autotarget": False,
            },
            ...
            {
                "name": "Toyota — автотаргет",
                "model": None,
                "cluster": None,
                "keywords": [],
                "ads": [...],
                "autotarget": True,
            },
        ],
        "total_keywords": 1234,
        "total_groups": 57,
    }
    """
    async with async_session() as db:
        brand = await db.get(CarBrand, brand_id)
        if not brand:
            return {"error": "Brand not found"}

        models = (await db.execute(
            select(CarModel)
            .where(CarModel.brand_id == brand_id, CarModel.active == True)
            .order_by(CarModel.popular.desc(), CarModel.name)
        )).scalars().all()

        parts = (await db.execute(
            select(PartCategory).where(PartCategory.active == True)
            .order_by(PartCategory.cluster, PartCategory.name)
        )).scalars().all()

    # Group parts by cluster
    clusters: dict[str, list[PartCategory]] = {}
    for p in parts:
        if p.cluster not in clusters:
            clusters[p.cluster] = []
        clusters[p.cluster].append(p)

    groups = []
    total_kw = 0

    for model in models:
        for cluster_name, cluster_parts in clusters.items():
            keywords = []

            for part in cluster_parts:
                for tpl in TEMPLATES:
                    kw = tpl.format(
                        part=part.name,
                        brand=brand.name.lower(),
                        model=model.name.lower(),
                    )
                    keywords.append(kw)

                # Also add with Russian brand name if available
                if brand.name_ru:
                    for tpl in TEMPLATES_RU:
                        kw = tpl.format(
                            part=part.name,
                            brand_ru=brand.name_ru.lower(),
                            model=model.name.lower(),
                        )
                        keywords.append(kw)

            # Deduplicate
            keywords = list(dict.fromkeys(keywords))

            ads = generate_ad_texts(brand.name, model.name, cluster_name)

            groups.append({
                "name": f"{brand.name} {model.name} — {cluster_name}",
                "model": model.name,
                "cluster": cluster_name,
                "keywords": keywords,
                "ads": ads,
                "autotarget": False,
            })
            total_kw += len(keywords)

    # Autotarget group
    groups.append({
        "name": f"{brand.name} — автотаргет",
        "model": None,
        "cluster": None,
        "keywords": [],
        "ads": generate_autotarget_ad(brand.name),
        "autotarget": True,
    })

    logger.info(
        f"Generated for {brand.name}: {len(groups)} groups, {total_kw} keywords"
    )

    return {
        "brand": brand.name,
        "brand_id": brand.id,
        "groups": groups,
        "total_keywords": total_kw,
        "total_groups": len(groups),
    }


async def preview_all_brands() -> dict:
    """Preview keyword counts for all brands (without generating actual keywords)."""
    async with async_session() as db:
        brands = (await db.execute(
            select(CarBrand).where(CarBrand.active == True).order_by(CarBrand.name)
        )).scalars().all()

        model_counts = {}
        for b in brands:
            cnt = (await db.execute(
                select(CarModel)
                .where(CarModel.brand_id == b.id, CarModel.active == True)
            )).scalars().all()
            model_counts[b.id] = len(cnt)

        part_count = (await db.execute(
            select(PartCategory).where(PartCategory.active == True)
        )).scalars().all()

        cluster_count = len(set(p.cluster for p in part_count))

    items = []
    total_kw = 0
    total_groups = 0

    for b in brands:
        n_models = model_counts.get(b.id, 0)
        n_groups = n_models * cluster_count + 1  # +1 for autotarget
        n_kw = n_models * len(part_count) * (len(TEMPLATES) + len(TEMPLATES_RU))

        items.append({
            "brand_id": b.id,
            "brand": b.name,
            "models": n_models,
            "groups": n_groups,
            "keywords": n_kw,
        })
        total_kw += n_kw
        total_groups += n_groups

    return {
        "brands": items,
        "totals": {
            "brands": len(brands),
            "groups": total_groups,
            "keywords": total_kw,
            "campaigns": len(brands) * 2,  # 2 geo segments
        },
    }

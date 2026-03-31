"""
Batch Campaign Creator — orchestrates full campaign hierarchy creation.

Flow per brand:
  1. Create campaign (per geo segment)
  2. Generate keyword groups (from keyword_generator)
  3. Create ad groups (1 per model×cluster + 1 autotarget)
  4. Create ads (2 per group)
  5. Add keywords (per group)

Progress is streamed via a dict that can be polled by frontend.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from backend.database import async_session
from backend.models import YandexDirectConfig, YandexDirectCampaign
from backend.services.yandex_direct import YandexDirectClient
from backend.services.keyword_generator import (
    generate_keywords_for_brand,
    NEGATIVE_KEYWORDS,
)
from sqlalchemy import select

logger = logging.getLogger("bidroute.batch_creator")

# Global progress tracker (polled by frontend)
BATCH_PROGRESS = {
    "running": False,
    "current_brand": "",
    "current_step": "",
    "brands_done": 0,
    "brands_total": 0,
    "campaigns_created": 0,
    "groups_created": 0,
    "ads_created": 0,
    "keywords_added": 0,
    "errors": [],
    "log": [],
}

# Geo segments
GEO_SEGMENTS = {
    "msk_spb": {
        "name_suffix": "МСК+СПб",
        "regions": [1, 10174],  # Moscow + SPb
    },
    "regions": {
        "name_suffix": "Регионы",
        "regions": [225],  # Russia (excluding will be handled later)
    },
}


def _reset_progress(total_brands: int):
    BATCH_PROGRESS.update({
        "running": True,
        "current_brand": "",
        "current_step": "",
        "brands_done": 0,
        "brands_total": total_brands,
        "campaigns_created": 0,
        "groups_created": 0,
        "ads_created": 0,
        "keywords_added": 0,
        "errors": [],
        "log": [],
        "started_at": datetime.utcnow().isoformat(),
    })


def _log(msg: str):
    logger.info(msg)
    BATCH_PROGRESS["log"].append(f"[{datetime.utcnow().strftime('%H:%M:%S')}] {msg}")
    # Keep last 100 log entries
    if len(BATCH_PROGRESS["log"]) > 100:
        BATCH_PROGRESS["log"] = BATCH_PROGRESS["log"][-100:]


async def create_campaigns_for_brand(
    client: YandexDirectClient,
    brand_id: int,
    geo_segments: list[str] = None,
    daily_budget: float = 300.0,
    base_url: str = "https://umit.pro",
) -> dict:
    """Create full campaign hierarchy for a single brand.
    
    Returns: {"campaigns_created": N, "groups": N, "ads": N, "keywords": N}
    """
    if geo_segments is None:
        geo_segments = ["msk_spb", "regions"]

    # 1. Generate keyword groups for this brand
    BATCH_PROGRESS["current_step"] = "Генерация ключевиков"
    kw_data = await generate_keywords_for_brand(brand_id)
    if "error" in kw_data:
        raise Exception(f"Brand {brand_id}: {kw_data['error']}")

    brand_name = kw_data["brand"]
    groups = kw_data["groups"]
    BATCH_PROGRESS["current_brand"] = brand_name
    _log(f"{brand_name}: {len(groups)} групп, {kw_data['total_keywords']} ключевиков")

    stats = {"campaigns": 0, "groups": 0, "ads": 0, "keywords": 0}

    for geo_key in geo_segments:
        geo = GEO_SEGMENTS.get(geo_key)
        if not geo:
            continue

        campaign_name = f"{brand_name} - {geo['name_suffix']}"
        _log(f"Создание кампании: {campaign_name}")
        BATCH_PROGRESS["current_step"] = f"Кампания: {campaign_name}"

        # 2. Create campaign
        try:
            camp_result = await client.create_campaign(
                name=campaign_name,
                daily_budget=daily_budget,
                regions=geo["regions"],
                negative_keywords=NEGATIVE_KEYWORDS,
                geo_segment=geo_key,
            )
            campaign_id = camp_result["id"]
            stats["campaigns"] += 1
            BATCH_PROGRESS["campaigns_created"] += 1
        except Exception as e:
            err = f"Ошибка создания кампании {campaign_name}: {e}"
            _log(err)
            BATCH_PROGRESS["errors"].append(err)
            continue

        # Save campaign to local DB (non-blocking — don't stop pipeline on DB errors)
        try:
            async with async_session() as db:
                local_camp = YandexDirectCampaign(
                    yd_campaign_id=campaign_id,
                    name=campaign_name,
                    status="draft",
                    yd_status="DRAFT",
                    daily_budget=max(daily_budget, 300.0),  # actual enforced budget
                    brand_id=brand_id,
                    geo_segment=geo_key,
                )
                db.add(local_camp)
                await db.commit()
        except Exception as e:
            _log(f"  ⚠ Не удалось сохранить в БД: {e}")
            # Continue — campaign exists in Yandex, we can sync later

        # 3. Create ad groups (batch)
        BATCH_PROGRESS["current_step"] = f"Группы: {campaign_name}"
        _log(f"  Создание {len(groups)} групп объявлений...")

        group_defs = [
            {"name": g["name"][:255], "autotarget": g.get("autotarget", False)}
            for g in groups
        ]

        try:
            group_results = await client.create_ad_groups(
                campaign_id=campaign_id,
                groups=group_defs,
                regions=geo["regions"],
            )
        except Exception as e:
            err = f"Ошибка создания групп для {campaign_name}: {e}"
            _log(err)
            BATCH_PROGRESS["errors"].append(err)
            continue

        # Map group names to IDs
        created_groups = {r["name"]: r["id"] for r in group_results if r.get("id")}
        stats["groups"] += len(created_groups)
        BATCH_PROGRESS["groups_created"] += len(created_groups)
        _log(f"  Создано групп: {len(created_groups)}/{len(groups)}")

        # 4. Create ads for each group (batch)
        BATCH_PROGRESS["current_step"] = f"Объявления: {campaign_name}"
        all_ads = []
        for g in groups:
            gid = created_groups.get(g["name"])
            if not gid:
                continue
            for ad in g.get("ads", []):
                # Add UTM parameters
                utm = f"?utm_source=yandex&utm_medium=cpc&utm_campaign={brand_name.lower().replace(' ', '_')}_{geo_key}&utm_content={g.get('cluster', 'auto')}"
                all_ads.append({
                    "ad_group_id": gid,
                    "title1": ad["title1"],
                    "title2": ad.get("title2", ""),
                    "text": ad["text"],
                    "href": f"{base_url}{utm}",
                })

        if all_ads:
            _log(f"  Создание {len(all_ads)} объявлений...")
            try:
                ad_results = await client.create_ads(all_ads)
                created_ads = len([r for r in ad_results if r.get("id")])
                stats["ads"] += created_ads
                BATCH_PROGRESS["ads_created"] += created_ads
                _log(f"  Создано объявлений: {created_ads}/{len(all_ads)}")
            except Exception as e:
                err = f"Ошибка создания объявлений: {e}"
                _log(err)
                BATCH_PROGRESS["errors"].append(err)

        # 5. Add keywords (batch, skip autotarget groups)
        BATCH_PROGRESS["current_step"] = f"Ключевики: {campaign_name}"
        all_keywords = []
        for g in groups:
            if g.get("autotarget"):
                continue
            gid = created_groups.get(g["name"])
            if not gid:
                continue
            for kw in g.get("keywords", []):
                all_keywords.append({
                    "ad_group_id": gid,
                    "keyword": kw,
                })

        if all_keywords:
            _log(f"  Добавление {len(all_keywords)} ключевиков...")
            try:
                kw_results = await client.add_keywords(all_keywords)
                added_kw = len([r for r in kw_results if r.get("id")])
                stats["keywords"] += added_kw
                BATCH_PROGRESS["keywords_added"] += added_kw
                _log(f"  Добавлено ключевиков: {added_kw}/{len(all_keywords)}")
            except Exception as e:
                err = f"Ошибка добавления ключевиков: {e}"
                _log(err)
                BATCH_PROGRESS["errors"].append(err)

    return stats


async def batch_create_campaigns(
    brand_ids: list[int],
    geo_segments: list[str] = None,
    daily_budget: float = 300.0,
    base_url: str = "https://umit.pro",
):
    """Create campaigns for multiple brands.
    
    Main orchestrator — runs as a background task.
    """
    _reset_progress(len(brand_ids))
    _log(f"Запуск пакетного создания: {len(brand_ids)} марок")

    # Get client
    async with async_session() as db:
        result = await db.execute(
            select(YandexDirectConfig).where(YandexDirectConfig.id == 1)
        )
        config = result.scalar_one_or_none()
        if not config or not config.oauth_token:
            BATCH_PROGRESS["running"] = False
            BATCH_PROGRESS["errors"].append("Нет подключения к Яндекс.Директ")
            return

    client = YandexDirectClient(config.oauth_token, config.client_login)

    totals = {"campaigns": 0, "groups": 0, "ads": 0, "keywords": 0}

    for i, brand_id in enumerate(brand_ids):
        try:
            stats = await create_campaigns_for_brand(
                client=client,
                brand_id=brand_id,
                geo_segments=geo_segments,
                daily_budget=daily_budget,
                base_url=base_url,
            )
            for k in totals:
                totals[k] += stats.get(k, 0)
        except Exception as e:
            err = f"Ошибка для бренда {brand_id}: {e}"
            _log(err)
            BATCH_PROGRESS["errors"].append(err)

        BATCH_PROGRESS["brands_done"] = i + 1

    _log(f"Завершено! Кампаний: {totals['campaigns']}, Групп: {totals['groups']}, "
         f"Объявлений: {totals['ads']}, Ключевиков: {totals['keywords']}")

    BATCH_PROGRESS["running"] = False
    BATCH_PROGRESS["finished_at"] = datetime.utcnow().isoformat()
    BATCH_PROGRESS["totals"] = totals

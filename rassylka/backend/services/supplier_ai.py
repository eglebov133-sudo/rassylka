"""
Supplier AI Search — Multi-factor priority search (8 iterations).

Phase 1: Search by PART (name + spare_part_type)
  P1: Part number + in stock + nearby
  P2: Part number + in stock (any region)
  P3: Part type + nearby (not necessarily in stock)
  P4: Part type + any supplier

Phase 2: Search by EQUIPMENT MODEL (brand + model)
  P5: Model parts + in stock + nearby
  P6: Model parts + in stock (any region)
  P7: Model parts + nearby
  P8: Model parts + any supplier
"""
import os
import json
import logging
import re
from typing import List, Dict, Optional

import httpx

from backend.models import Bid

logger = logging.getLogger("bidroute.supplier_ai")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
PERPLEXITY_MODEL = os.getenv("PERPLEXITY_MODEL", "perplexity/sonar-medium-online")

# Blacklist: marketplaces and aggregators that should never be treated as suppliers
BLACKLIST_DOMAINS = {
    "ozon.ru", "ozon.com", "wildberries.ru", "wb.ru",
    "market.yandex.ru", "yandex.ru", "beru.ru",
    "aliexpress.ru", "aliexpress.com", "alibaba.com",
    "avito.ru", "drom.ru", "auto.ru",
    "goods.ru", "sbermegamarket.ru", "megamarket.ru",
    "vseinstrumenti.ru", "citilink.ru", "dns-shop.ru",
    "lamoda.ru", "amazon.com", "ebay.com",
    "mail.ru", "gmail.com", "yandex.com",
}


SYSTEM_PROMPT = """Ты помощник по поиску поставщиков запасных частей и оборудования в России и СНГ.
Пользователь даёт тебе описание запчасти или оборудования. 
Ты должен найти реальных поставщиков, которые продают подобные товары.

Верни результат СТРОГО в JSON формате (массив объектов):
[
  {
    "company_name": "Название компании",
    "email": "email@example.com",
    "phone": "+7...",
    "contact_person": "Имя контакта",
    "website": "https://...",
    "categories": ["категория1", "категория2"],
    "regions": ["Москва", "Московская область"],
    "description": "Краткое описание деятельности компании"
  }
]

Важно:
- Указывай только реальные компании с реальными контактами
- Email обязателен
- Если не нашёл поставщиков — верни пустой массив []
- Не добавляй текст до или после JSON
- НИКОГДА не включай маркетплейсы (Ozon, Wildberries, Яндекс Маркет, AliExpress, Avito, СберМегаМаркет и т.п.) — только прямые поставщики и производители
"""


def _extract_part_number(name: str) -> Optional[str]:
    """Try to extract a part/catalog number from bid name."""
    if not name:
        return None
    # Common patterns: digits with dots/dashes/letters (e.g. 310.3.56.04, A4VG71, RE505980)
    patterns = [
        r'\b[A-ZА-Я]{1,4}\d{2,}[\w\.\-]*\b',  # RE505980, A4VG71
        r'\b\d{2,}[\.\-]\d+[\.\-\d]*\b',        # 310.3.56.04, 20-925-148
    ]
    for pat in patterns:
        match = re.search(pat, name, re.IGNORECASE)
        if match:
            return match.group(0)
    return None


def build_priority_prompts(bid: Bid) -> List[dict]:
    """Build 8 priority-level search prompts from a bid.
    
    Returns list of {priority: int, prompt: str, phase: str} dicts.
    Skips levels that don't have enough data.
    """
    prompts = []
    
    part_name = bid.name or ""
    part_number = _extract_part_number(part_name)
    part_type = bid.spare_part_type or ""
    brand = bid.brand or ""
    model = bid.model or ""
    year = bid.year or ""
    region = bid.delivery_place or ""
    description = bid.description or ""
    
    model_full = f"{brand} {model}".strip()
    if year:
        model_full += f" ({year} г.)"
    
    # ══════════════════════════════════════════
    # PHASE 1: Search by PART
    # ══════════════════════════════════════════
    
    if part_number and region:
        prompts.append({
            "priority": 1,
            "phase": "part",
            "prompt": f"Найди поставщиков в регионе {region}, у которых ЕСТЬ В НАЛИЧИИ "
                      f"деталь \"{part_name}\" (артикул/номер: {part_number}) "
                      f"{'для ' + brand if brand else ''}. "
                      f"Важно: только те, у кого реально в наличии и кто находится рядом с {region}."
        })
    
    if part_number:
        prompts.append({
            "priority": 2,
            "phase": "part",
            "prompt": f"Найди поставщиков в России, у которых ЕСТЬ В НАЛИЧИИ "
                      f"деталь \"{part_name}\" (артикул/номер: {part_number}) "
                      f"{'для ' + brand if brand else ''}. "
                      f"Регион неважен — главное наличие на складе."
        })
    
    if part_type and region:
        prompts.append({
            "priority": 3,
            "phase": "part",
            "prompt": f"Найди поставщиков в регионе {region}, которые продают "
                      f"запчасти категории \"{part_type}\" "
                      f"{'для техники ' + brand if brand else ''}. "
                      f"Допустимо под заказ, главное — близость к {region}."
        })
    
    if part_type or part_name:
        search_term = part_type if part_type else part_name
        prompts.append({
            "priority": 4,
            "phase": "part",
            "prompt": f"Найди поставщиков в России, которые могут поставить "
                      f"запчасти \"{search_term}\" "
                      f"{'для ' + brand if brand else ''}. "
                      f"Допустимо под заказ, любой регион России."
        })
    
    # ══════════════════════════════════════════
    # PHASE 2: Search by EQUIPMENT MODEL
    # ══════════════════════════════════════════
    
    if model_full and model_full.strip():
        if region:
            prompts.append({
                "priority": 5,
                "phase": "model",
                "prompt": f"Найди поставщиков запчастей для {model_full} в регионе {region}, "
                          f"у которых есть запчасти В НАЛИЧИИ. "
                          f"{'Нужна деталь: ' + part_name if part_name else ''}"
            })
        
        prompts.append({
            "priority": 6,
            "phase": "model",
            "prompt": f"Найди поставщиков запчастей для {model_full} в России, "
                      f"у которых запчасти ЕСТЬ В НАЛИЧИИ. "
                      f"{'Нужна деталь: ' + part_name if part_name else ''}"
        })
        
        if region:
            prompts.append({
                "priority": 7,
                "phase": "model",
                "prompt": f"Найди поставщиков запчастей для {model_full} в регионе {region}. "
                          f"Допустимо под заказ."
            })
        
        prompts.append({
            "priority": 8,
            "phase": "model",
            "prompt": f"Найди поставщиков запчастей для {model_full} в России. "
                      f"Допустимо под заказ, любой регион."
        })
    
    return prompts


async def _call_ai(prompt: str) -> List[Dict]:
    """Call Perplexity AI and return parsed supplier list."""
    if not OPENROUTER_API_KEY:
        logger.warning("OpenRouter API key not configured")
        return []

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://bidroute.local",
                    "X-Title": "BidRoute AI Supplier Search",
                },
                json={
                    "model": PERPLEXITY_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 4000,
                },
            )
            if response.status_code != 200:
                logger.error(f"OpenRouter API error {response.status_code}: {response.text[:500]}")
                return []
            data = response.json()

            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            content = content.strip()
            if not content:
                return []

            suppliers = json.loads(content)
            if not isinstance(suppliers, list):
                suppliers = [suppliers]

            # Validate and filter out blacklisted domains
            valid = []
            for s in suppliers:
                if not (s.get("company_name") and s.get("email")):
                    continue
                # Check email domain against blacklist
                email_domain = s["email"].split("@")[-1].lower().strip()
                if email_domain in BLACKLIST_DOMAINS:
                    logger.info(f"Filtered out marketplace: {s.get('company_name')} ({s['email']})")
                    continue
                # Check website domain against blacklist
                website = (s.get("website") or "").lower()
                if any(bd in website for bd in BLACKLIST_DOMAINS):
                    logger.info(f"Filtered out marketplace by website: {s.get('company_name')} ({website})")
                    continue
                valid.append({
                    "company_name": s.get("company_name", ""),
                    "email": s.get("email", ""),
                    "phone": s.get("phone", ""),
                    "contact_person": s.get("contact_person", ""),
                    "website": s.get("website", ""),
                    "categories": s.get("categories", []),
                    "regions": s.get("regions", []),
                    "description": s.get("description", ""),
                })
            return valid

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"AI supplier search error: {e}")
            return []


async def smart_search_for_bid(bid: Bid, target_count: int = 10) -> List[dict]:
    """Run multi-priority AI search for a bid.
    
    Returns list of {supplier_data: dict, priority: int} items,
    deduplicated by email, keeping the best (lowest) priority.
    Stops early if target_count reached.
    """
    prompts = build_priority_prompts(bid)
    
    all_found = {}  # email -> {data, priority}
    
    for p in prompts:
        priority = p["priority"]
        phase = p["phase"]
        prompt = p["prompt"]
        
        logger.info(f"Bid {bid.source_id}: P{priority} ({phase}) searching...")
        
        results = await _call_ai(prompt)
        new_count = 0
        
        for supplier_data in results:
            email = supplier_data["email"].lower().strip()
            if email not in all_found:
                all_found[email] = {
                    "data": supplier_data,
                    "priority": priority,
                }
                new_count += 1
            # If already found at a better priority, keep that one
        
        logger.info(f"Bid {bid.source_id}: P{priority} found {len(results)} ({new_count} new), total: {len(all_found)}")
        
        # Stop early if we have enough suppliers
        if len(all_found) >= target_count:
            logger.info(f"Bid {bid.source_id}: target {target_count} reached at P{priority}, stopping search")
            break
    
    # Sort by priority (best first)
    result = sorted(all_found.values(), key=lambda x: x["priority"])
    return result


# Legacy compatibility
async def search_suppliers(query: str) -> List[Dict]:
    """Legacy search — single prompt (used by manual AI search from UI)."""
    return await _call_ai(query)


def build_search_query(bid_data: dict) -> str:
    """Build a search query from bid data (legacy)."""
    parts = []
    if bid_data.get("brand"):
        parts.append(f"бренд: {bid_data['brand']}")
    if bid_data.get("model"):
        parts.append(f"модель: {bid_data['model']}")
    if bid_data.get("spare_part_type"):
        parts.append(f"тип запчасти: {bid_data['spare_part_type']}")
    if bid_data.get("name"):
        parts.append(f"название: {bid_data['name']}")

    query = f"Найти поставщиков запасных частей в России: {', '.join(parts)}"

    if bid_data.get("delivery_place"):
        query += f". Предпочтительный регион поставки: {bid_data['delivery_place']}"

    return query

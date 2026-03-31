"""
AI Parts Service — generates auto parts content using Gemini 2.0 Flash via OpenRouter.

Used by the landing page to:
1. Generate landing page content from a search query (brand, model, part category)
2. Search for specific parts with prices and availability
"""
import json
import logging
import os
import re
import httpx
from typing import Optional

logger = logging.getLogger("bidroute.ai_parts")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_PARTS_MODEL", "google/gemini-2.0-flash-001")
PERPLEXITY_MODEL = os.getenv("PERPLEXITY_MODEL", "perplexity/sonar")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


async def _call_ai(system_prompt: str, user_prompt: str, temperature: float = 0.7, model: str = None) -> str:
    """Call AI model via OpenRouter and return the text response."""
    if not OPENROUTER_API_KEY:
        raise Exception("OPENROUTER_API_KEY not configured")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("APP_BASE_URL", "https://umit-info.ru"),
    }

    body = {
        "model": model or GEMINI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": 4096,
    }

    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.post(OPENROUTER_URL, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        logger.error(f"Empty AI response: {data}")
        raise Exception("AI returned empty response")

    return content


def _extract_json(text: str) -> dict:
    """Extract JSON from AI response that may contain markdown code blocks."""
    # Try to find JSON in code blocks
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        text = match.group(1)

    # Try direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        # Try to find first { ... } block
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

    logger.error(f"Failed to parse AI JSON: {text[:500]}")
    return {}


async def generate_landing_content(query: str) -> dict:
    """
    Generate landing page content based on a search query from Yandex Direct.

    Returns dict:
    {
        "brand": "Toyota",
        "model": "Camry",
        "category": "Двигатель",
        "title": "Запчасти для двигателя Toyota Camry",
        "subtitle": "В наличии на складе — доставка по всей России",
        "subcategories": [
            {"name": "Поршни", "icon": "precision_manufacturing", "count": 45},
            {"name": "Клапаны", "icon": "valve", "count": 32},
            ...
        ],
        "popular_parts": [
            {
                "name": "Поршень цилиндра Toyota Camry 2.5L",
                "article": "13101-25030",
                "price": 4500,
                "original": true,
                "in_stock": true,
                "delivery_days": 2
            },
            ...
        ],
        "seo_text": "Купить запчасти для двигателя Toyota Camry..."
    }
    """
    system_prompt = """Ты — эксперт по автозапчастям. Пользователь ищет запчасти для автомобиля.
На основе его поискового запроса, сгенерируй структурированный JSON для лендинг-страницы магазина запчастей.

ВАЖНО:
- Определи марку, модель авто и категорию запчастей из запроса
- Если модель неясна, укажи только марку
- Генерируй реалистичные артикулы и цены (российский рынок, в рублях)
- Подкатегории — 6-8 штук, связанных с основной категорией
- Популярные товары — 6-8 штук с реалистичными ценами
- icon — ТОЛЬКО из этого списка Material Symbols: manufacturing, settings, swap_vert, bolt, ac_unit, filter_alt, lightbulb, garage, air, flip, u_turn_right, do_not_disturb_on, local_shipping, build, handyman, oil_barrel, water_drop, thermostat, speed, tire_repair, shield, visibility, straighten, layers, autorenew, sync_alt, precision_manufacturing, memory, cable, local_gas_station, warning
- Все цены — целые числа в рублях
- delivery_days: от 1 до 7

Формат ответа — ТОЛЬКО валидный JSON, без обёрток и пояснений."""

    user_prompt = f"""Поисковый запрос пользователя: "{query}"

Верни JSON в формате:
{{
  "brand": "Марка авто",
  "model": "Модель (если определена)",
  "category": "Категория запчастей",
  "title": "Заголовок страницы",
  "subtitle": "Подзаголовок",
  "subcategories": [
    {{"name": "Название", "icon": "material_icon_name", "count": число_товаров}},
    ...6-8 подкатегорий
  ],
  "popular_parts": [
    {{
      "name": "Полное название детали",
      "article": "OEM артикул",
      "price": цена_в_рублях,
      "original": true/false,
      "in_stock": true,
      "delivery_days": число_дней
    }},
    ...6-8 товаров
  ],
  "seo_text": "SEO-описание 2-3 предложения"
}}"""

    try:
        response = await _call_ai(system_prompt, user_prompt, temperature=0.6)
        result = _extract_json(response)

        if not result or "title" not in result:
            # Fallback
            return _fallback_landing(query)

        return result
    except Exception as e:
        logger.error(f"AI landing generation failed: {e}")
        return _fallback_landing(query)


async def search_parts(query: str, brand: str = "", category: str = "") -> list[dict]:
    """
    Search for specific parts based on user query within a brand/category context.

    Returns list of parts with detailed info and prices.
    """
    context = ""
    if brand:
        context += f" для {brand}"
    if category:
        context += f", категория: {category}"

    system_prompt = """Ты — эксперт по автозапчастям. Пользователь ищет конкретную запчасть.
Сгенерируй результаты поиска — список из 8-12 подходящих деталей.

ВАЖНО:
- Каждая деталь: название, артикул (OEM или aftermarket), цена в рублях, наличие, срок
- Включи как оригинальные, так и аналоги (aftermarket) — пометь origin
- Цены реалистичные для российского рынка
- Для аналогов укажи бренд производителя
- status: "in_stock", "on_order", "few_left"
- delivery_days: целое число 1-14

Формат ответа — ТОЛЬКО валидный JSON массив, без обёрток."""

    user_prompt = f"""Поиск: "{query}"{context}

Верни JSON массив:
[
  {{
    "name": "Полное название",
    "article": "артикул",
    "manufacturer": "производитель",
    "origin": "original" или "aftermarket",
    "price": цена_рублей,
    "old_price": старая_цена_или_null,
    "status": "in_stock",
    "quantity": число_на_складе,
    "delivery_days": число_дней,
    "description": "Краткое описание, совместимость"
  }},
  ...8-12 результатов
]"""

    try:
        response = await _call_ai(system_prompt, user_prompt, temperature=0.5)
        result = _extract_json(response)

        # If result is a dict with a list inside, extract it
        if isinstance(result, dict):
            for key in ("parts", "results", "items"):
                if key in result and isinstance(result[key], list):
                    return result[key]
            return []

        if isinstance(result, list):
            return result

        # Try parsing as array directly
        try:
            arr = json.loads(response.strip())
            if isinstance(arr, list):
                return arr
        except:
            pass

        return []
    except Exception as e:
        logger.error(f"AI parts search failed: {e}")
        return _fallback_search(query, brand)


async def perplexity_search(query: str) -> list[dict]:
    """
    Global search for auto parts using Perplexity/Sonar via OpenRouter.
    Returns real web-grounded results with detailed descriptions.
    """
    system_prompt = """Ты — поисковая система магазина автозапчастей с доступом к интернету.
Пользователь вводит запрос — найди РЕАЛЬНЫЕ автозапчасти, подходящие под запрос.

Для каждой детали предоставь ПОДРОБНУЮ ИНФОРМАЦИЮ:
- Полное название с указанием совместимости
- Реальный OEM-артикул или артикул производителя
- Производитель (реальный бренд: Bosch, TRW, Koito, Denso, Gates и т.д.)
- Подробное описание: материалы, характеристики, размеры, технические данные (2-4 предложения)
- Совместимость: с какими автомобилями и годами выпуска
- Реалистичная цена в рублях для российского рынка

ВАЖНО:
- Используй РЕАЛЬНЫЕ OEM-номера и артикулы
- Описание должно быть технически грамотным
- Включи как оригинальные, так и качественные аналоги
- 6-10 результатов
- Формат — ТОЛЬКО валидный JSON массив"""

    user_prompt = f"""Найди автозапчасти по запросу: "{query}"

Верни JSON массив:
[
  {{
    "name": "Полное название детали",
    "article": "реальный артикул",
    "manufacturer": "реальный производитель",
    "origin": "original" или "aftermarket",
    "price": цена_рублей,
    "old_price": старая_цена_или_null,
    "status": "in_stock" / "on_order" / "few_left",
    "delivery_days": число_дней_1_14,
    "description": "Подробное описание: материалы, характеристики, размеры, особенности. 2-4 предложения.",
    "specs": "Ключевые ТТХ через точку с запятой (например: Диаметр: 280мм; Толщина: 26мм; Тип: вентилируемый)",
    "compatibility": "Совместимость: модели авто и годы выпуска",
    "quantity": число_на_складе
  }}
]"""

    try:
        response = await _call_ai(
            system_prompt, user_prompt,
            temperature=0.3,
            model=PERPLEXITY_MODEL,
        )
        result = _extract_json(response)

        if isinstance(result, dict):
            for key in ("parts", "results", "items"):
                if key in result and isinstance(result[key], list):
                    return result[key]
            return []

        if isinstance(result, list):
            return result

        return []
    except Exception as e:
        logger.error(f"Perplexity search failed: {e}")
        # Fallback to Gemini search
        return await search_parts(query)


async def load_more_parts(query: str, brand: str = "", category: str = "", page: int = 2) -> list[dict]:
    """
    Generate additional parts for pagination. Each page returns new unique items.
    Uses page number as context to avoid repeating previous results.
    """
    context = ""
    if brand:
        context += f" для {brand}"
    if category:
        context += f", категория: {category}"

    system_prompt = """Ты — эксперт по автозапчастям и база данных магазина запчастей.
Пользователь листает каталог и хочет увидеть СЛЕДУЮЩУЮ порцию товаров.
Сгенерируй НОВЫЕ 8 товаров, которые НЕ ПОВТОРЯЮТ предыдущие.

ВАЖНО:
- Это страница {page} каталога — генерируй ДРУГИЕ детали, не те что были раньше
- Для каждой страницы варьируй: бренды, типы деталей, ценовые сегменты
- Включи mix оригиналов и аналогов разных производителей
- Цены реалистичные для российского рынка в рублях
- status: "in_stock", "on_order", "few_left"
- delivery_days: 1-14

Формат ответа — ТОЛЬКО валидный JSON массив."""

    user_prompt = f"""Запрос: "{query}"{context}
Страница каталога: {page} (покажи НОВЫЕ товары, отличные от страниц 1-{page-1})

Верни JSON массив из 8 товаров:
[
  {{
    "name": "Полное название детали",
    "article": "артикул",
    "manufacturer": "производитель",
    "origin": "original" или "aftermarket",
    "price": цена_рублей,
    "old_price": старая_цена_или_null,
    "status": "in_stock",
    "quantity": число_на_складе,
    "delivery_days": число_дней,
    "description": "Краткое описание"
  }}
]"""

    try:
        response = await _call_ai(
            system_prompt.replace("{page}", str(page)),
            user_prompt,
            temperature=0.7 + (page * 0.05),  # Slightly increase randomness per page
        )
        result = _extract_json(response)

        if isinstance(result, dict):
            for key in ("parts", "results", "items"):
                if key in result and isinstance(result[key], list):
                    return result[key]
            return []

        if isinstance(result, list):
            return result

        return []
    except Exception as e:
        logger.error(f"AI load-more failed (page {page}): {e}")
        return []


def _fallback_landing(query: str) -> dict:
    """Fallback landing content when AI is unavailable."""
    return {
        "brand": "",
        "model": "",
        "category": "Запчасти",
        "title": f"Запчасти: {query}",
        "subtitle": "Найдите нужную деталь — в наличии и под заказ",
        "subcategories": [
            {"name": "Двигатель", "icon": "manufacturing", "count": 150},
            {"name": "Подвеска", "icon": "directions_car", "count": 120},
            {"name": "Тормозная система", "icon": "do_not_disturb_on", "count": 90},
            {"name": "Кузов", "icon": "garage", "count": 200},
            {"name": "Электрика", "icon": "bolt", "count": 80},
            {"name": "Трансмиссия", "icon": "settings", "count": 70},
        ],
        "popular_parts": [],
        "seo_text": f"Купить {query} с доставкой по всей России. Оригинальные запчасти и качественные аналоги в наличии.",
    }


def _fallback_search(query: str, brand: str) -> list[dict]:
    """Fallback search results when AI is unavailable."""
    prefix = f"{brand} " if brand else ""
    return [
        {
            "name": f"{prefix}{query} (оригинал)",
            "article": "N/A",
            "manufacturer": brand or "OEM",
            "origin": "original",
            "price": 5000,
            "old_price": None,
            "status": "on_order",
            "quantity": 0,
            "delivery_days": 5,
            "description": f"Оригинальная запчасть. Уточняйте наличие у менеджера.",
        }
    ]

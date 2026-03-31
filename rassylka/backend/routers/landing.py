"""
Landing page router — serves AI-generated auto parts pages.

Public endpoints (no auth required):
  GET  /parts           — Landing page (SSR via Jinja2 + AI)
  POST /api/parts/search — AJAX search for parts
  POST /api/parts/order  — Submit order
  GET  /parts-static/*   — Static files (CSS)
"""
import os
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional

from backend.services.ai_parts import generate_landing_content, search_parts, load_more_parts, perplexity_search

logger = logging.getLogger("bidroute.landing")

router = APIRouter()

# Templates directory
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Simple in-memory cache for landing content (avoid re-generating for same queries)
_landing_cache: dict[str, dict] = {}
MAX_CACHE_SIZE = 200


# ── Schemas ──

class SearchRequest(BaseModel):
    query: str
    brand: str = ""
    category: str = ""


class LoadMoreRequest(BaseModel):
    query: str
    brand: str = ""
    category: str = ""
    page: int = 2


class OrderRequest(BaseModel):
    customer_name: str
    customer_phone: str
    customer_email: str = ""
    customer_city: str = ""
    comment: str = ""
    items: list[dict] = []
    total_price: float = 0
    query: str = ""
    utm_term: str = ""
    utm_source: str = ""
    utm_campaign: str = ""


# ── Routes ──

# ── Catalog data ──
POPULAR_BRANDS = [
    {"name": "Toyota", "icon": "directions_car", "models": ["Camry", "Corolla", "RAV4", "Land Cruiser", "Prado", "Highlander", "Hilux", "Fortuner"]},
    {"name": "Kia", "icon": "directions_car", "models": ["Rio", "Sportage", "Ceed", "Cerato", "Sorento", "Optima", "Soul", "Seltos"]},
    {"name": "Hyundai", "icon": "directions_car", "models": ["Solaris", "Creta", "Tucson", "Santa Fe", "Elantra", "i30", "ix35", "Sonata"]},
    {"name": "Nissan", "icon": "directions_car", "models": ["Qashqai", "X-Trail", "Almera", "Teana", "Pathfinder", "Juke", "Murano", "Note"]},
    {"name": "Volkswagen", "icon": "directions_car", "models": ["Polo", "Tiguan", "Golf", "Passat", "Touareg", "Jetta", "Multivan", "Amarok"]},
    {"name": "BMW", "icon": "directions_car", "models": ["3 серия", "5 серия", "X3", "X5", "X1", "7 серия", "X6", "1 серия"]},
    {"name": "Mercedes-Benz", "icon": "directions_car", "models": ["C-класс", "E-класс", "GLC", "GLE", "S-класс", "A-класс", "GLA", "GLB"]},
    {"name": "Audi", "icon": "directions_car", "models": ["A4", "A6", "Q5", "Q7", "A3", "Q3", "A5", "Q8"]},
    {"name": "Mazda", "icon": "directions_car", "models": ["CX-5", "3", "6", "CX-9", "CX-3", "CX-30", "MX-5", "2"]},
    {"name": "Ford", "icon": "directions_car", "models": ["Focus", "Kuga", "Mondeo", "Explorer", "Fiesta", "EcoSport", "Ranger", "Transit"]},
    {"name": "Chevrolet", "icon": "directions_car", "models": ["Cruze", "Niva", "Aveo", "Captiva", "Lacetti", "Orlando", "Cobalt", "Tahoe"]},
    {"name": "Renault", "icon": "directions_car", "models": ["Duster", "Logan", "Sandero", "Kaptur", "Arkana", "Megane", "Fluence", "Koleos"]},
    {"name": "Skoda", "icon": "directions_car", "models": ["Octavia", "Rapid", "Kodiaq", "Superb", "Karoq", "Fabia", "Yeti", "Roomster"]},
    {"name": "Mitsubishi", "icon": "directions_car", "models": ["Outlander", "Lancer", "Pajero", "ASX", "L200", "Eclipse Cross", "Pajero Sport", "Colt"]},
    {"name": "Honda", "icon": "directions_car", "models": ["CR-V", "Civic", "Accord", "HR-V", "Fit", "Jazz", "Pilot", "Odyssey"]},
    {"name": "Lada", "icon": "directions_car", "models": ["Vesta", "Granta", "XRAY", "Largus", "Niva", "Priora", "Kalina", "2114"]},
    {"name": "Subaru", "icon": "directions_car", "models": ["Forester", "Outback", "XV", "Impreza", "Legacy", "WRX", "BRZ", "Levorg"]},
    {"name": "Suzuki", "icon": "directions_car", "models": ["Vitara", "SX4", "Jimny", "Swift", "Grand Vitara", "Ignis", "Baleno", "S-Cross"]},
    {"name": "Lexus", "icon": "directions_car", "models": ["RX", "NX", "LX", "IS", "ES", "GX", "UX", "LS"]},
    {"name": "Geely", "icon": "directions_car", "models": ["Atlas", "Coolray", "Tugella", "Emgrand", "Monjaro", "Preface", "Okavango", "Azkarra"]},
    {"name": "Chery", "icon": "directions_car", "models": ["Tiggo 7 Pro", "Tiggo 4 Pro", "Tiggo 8 Pro", "Arrizo", "Tiggo 2", "Tiggo 5", "Tiggo 3", "Exeed"]},
    {"name": "Haval", "icon": "directions_car", "models": ["Jolion", "F7", "H9", "Dargo", "H5", "F7x", "H6", "M6"]},
]

PART_CATEGORIES = [
    {"name": "Двигатель", "icon": "manufacturing"},
    {"name": "Тормозная система", "icon": "do_not_disturb_on"},
    {"name": "Подвеска", "icon": "swap_vert"},
    {"name": "Кузов", "icon": "garage"},
    {"name": "Электрика", "icon": "bolt"},
    {"name": "Трансмиссия", "icon": "settings"},
    {"name": "Рулевое управление", "icon": "u_turn_right"},
    {"name": "Система охлаждения", "icon": "ac_unit"},
    {"name": "Выхлопная система", "icon": "air"},
    {"name": "Фильтры", "icon": "filter_alt"},
    {"name": "Освещение", "icon": "lightbulb"},
    {"name": "Стёкла и зеркала", "icon": "flip"},
]

_brand_names_lower = {b["name"].lower(): b for b in POPULAR_BRANDS}


def _detect_catalog_level(query: str):
    """
    Detect if the query matches a brand or brand+model from our catalog.
    Returns: (catalog_type, brand_data, model_name)
      catalog_type: 'home' | 'brand' | 'model' | 'search'
    """
    if not query:
        return "home", None, None

    q_lower = query.lower().strip()

    # Check if query matches exactly a brand name
    if q_lower in _brand_names_lower:
        return "brand", _brand_names_lower[q_lower], None

    # Check if query is "brand model"
    for brand_key, brand_data in _brand_names_lower.items():
        if q_lower.startswith(brand_key + " "):
            rest = query[len(brand_key):].strip()
            # Check if the rest matches a known model
            for model in brand_data["models"]:
                if rest.lower() == model.lower():
                    return "model", brand_data, model
            # Rest doesn't match a known model — it's a free search with brand context
            break

    return "search", None, None


@router.get("/parts", response_class=HTMLResponse)
async def landing_page(request: Request, q: str = ""):
    """Serve the landing page with smart catalog navigation."""
    query = q.strip()
    catalog_type, brand_data, model_name = _detect_catalog_level(query)

    if catalog_type == "home":
        # Show brands catalog — no AI needed
        data = {
            "brand": "",
            "model": "",
            "category": "",
            "title": "Каталог автозапчастей",
            "subtitle": "Выберите марку автомобиля для подбора запчастей",
            "subcategories": [],
            "popular_parts": [],
            "seo_text": "Интернет-магазин автозапчастей UMIT — оригинальные запчасти и качественные аналоги для всех марок автомобилей. Быстрая доставка по России.",
        }
        return templates.TemplateResponse("landing.html", {
            "request": request,
            "data": data,
            "query": "",
            "catalog_type": "home",
            "brands": POPULAR_BRANDS,
            "models": [],
            "part_categories": [],
        })

    if catalog_type == "brand":
        # Show models for this brand — no AI needed
        data = {
            "brand": brand_data["name"],
            "model": "",
            "category": "",
            "title": f"Запчасти для {brand_data['name']}",
            "subtitle": f"Выберите модель {brand_data['name']} для подбора запчастей",
            "subcategories": [],
            "popular_parts": [],
            "seo_text": f"Купить запчасти для {brand_data['name']} с доставкой по России. Оригиналы и аналоги в наличии.",
        }
        return templates.TemplateResponse("landing.html", {
            "request": request,
            "data": data,
            "query": query,
            "catalog_type": "brand",
            "brands": [],
            "models": brand_data["models"],
            "part_categories": [],
            "brand_name": brand_data["name"],
        })

    if catalog_type == "model":
        # Show part categories for brand+model — no AI needed
        data = {
            "brand": brand_data["name"],
            "model": model_name,
            "category": "",
            "title": f"Запчасти для {brand_data['name']} {model_name}",
            "subtitle": f"Выберите категорию запчастей для {brand_data['name']} {model_name}",
            "subcategories": [],
            "popular_parts": [],
            "seo_text": f"Купить запчасти для {brand_data['name']} {model_name}. Оригинальные и аналоговые детали с гарантией.",
        }
        return templates.TemplateResponse("landing.html", {
            "request": request,
            "data": data,
            "query": query,
            "catalog_type": "model",
            "brands": [],
            "models": [],
            "part_categories": PART_CATEGORIES,
            "brand_name": brand_data["name"],
            "model_name": model_name,
        })

    # catalog_type == "search" → Perplexity for products, Gemini for landing layout
    cache_key = query.lower()
    if cache_key in _landing_cache:
        data = _landing_cache[cache_key]
        logger.info(f"Landing cache hit: {query}")
    else:
        logger.info(f"Generating landing for query: {query}")
        # Run Gemini (landing layout) and Perplexity (product search) in parallel
        import asyncio
        landing_task = asyncio.create_task(generate_landing_content(query))
        search_task = asyncio.create_task(perplexity_search(query))

        data = await landing_task
        perplexity_results = await search_task

        # Replace AI popular_parts with Perplexity results (richer descriptions)
        if perplexity_results:
            data["popular_parts"] = perplexity_results

        if len(_landing_cache) >= MAX_CACHE_SIZE:
            oldest_key = next(iter(_landing_cache))
            del _landing_cache[oldest_key]
        _landing_cache[cache_key] = data

    return templates.TemplateResponse("landing.html", {
        "request": request,
        "data": data,
        "query": query,
        "catalog_type": "search",
        "brands": [],
        "models": [],
        "part_categories": [],
    })


@router.post("/api/parts/search")
async def search_parts_api(req: SearchRequest):
    """AJAX endpoint to search for specific parts."""
    logger.info(f"Parts search: query='{req.query}' brand='{req.brand}' cat='{req.category}'")

    parts = await search_parts(
        query=req.query,
        brand=req.brand,
        category=req.category,
    )

    return {"parts": parts, "count": len(parts)}


@router.post("/api/parts/load-more")
async def load_more_parts_api(req: LoadMoreRequest):
    """AJAX endpoint to load more parts (AI pagination)."""
    logger.info(f"Load more: query='{req.query}' brand='{req.brand}' page={req.page}")

    parts = await load_more_parts(
        query=req.query,
        brand=req.brand,
        category=req.category,
        page=req.page,
    )

    return {"parts": parts, "count": len(parts), "page": req.page}


@router.post("/api/parts/order")
async def submit_order(req: OrderRequest):
    """Save order to database and send notification."""
    logger.info(
        f"New parts order: {req.customer_name} / {req.customer_phone} / "
        f"{len(req.items)} items / {req.total_price}₽"
    )

    # Save order to DB
    try:
        from backend.database import async_session
        from backend.models import PartsOrder

        async with async_session() as session:
            order = PartsOrder(
                customer_name=req.customer_name,
                customer_phone=req.customer_phone,
                customer_email=req.customer_email,
                customer_city=req.customer_city,
                comment=req.comment,
                items_json=json.dumps(req.items, ensure_ascii=False),
                total_price=req.total_price,
                query=req.query,
                utm_term=req.utm_term,
                utm_source=req.utm_source,
                utm_campaign=req.utm_campaign,
                status="new",
            )
            session.add(order)
            await session.commit()
            order_id = order.id

        logger.info(f"Order #{order_id} saved to DB")

        # Send notification email (best-effort)
        try:
            await _send_order_notification(order_id, req)
        except Exception as e:
            logger.warning(f"Order notification email failed: {e}")

        return {"ok": True, "order_id": order_id}

    except Exception as e:
        logger.error(f"Failed to save order: {e}", exc_info=True)

        # Even if DB fails, save to file as backup
        try:
            os.makedirs("data/orders", exist_ok=True)
            backup_file = f"data/orders/order_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(req.dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"Order saved to backup file: {backup_file}")
        except Exception as e2:
            logger.error(f"Backup save also failed: {e2}")

        return {"ok": True, "message": "Заявка принята"}


async def _send_order_notification(order_id: int, req: OrderRequest):
    """Send email notification about new order to admin."""
    import aiosmtplib
    from email.message import EmailMessage

    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    admin_email = os.getenv("SENDER_EMAIL", smtp_user)

    if not all([smtp_host, smtp_user, smtp_pass]):
        return

    items_text = "\n".join(
        f"  • {item.get('name', '?')} (Art: {item.get('article', '?')}) — {item.get('price', '?')} ₽"
        for item in req.items
    )

    body = f"""Новый заказ запчастей #{order_id}

Клиент: {req.customer_name}
Телефон: {req.customer_phone}
Email: {req.customer_email or '—'}
Город: {req.customer_city or '—'}
Комментарий: {req.comment or '—'}

Поисковый запрос: {req.query}
UTM: source={req.utm_source}, campaign={req.utm_campaign}, term={req.utm_term}

Товары:
{items_text}

Итого: {req.total_price:,.0f} ₽
"""

    msg = EmailMessage()
    msg["Subject"] = f"🔧 Заказ запчастей #{order_id} — {req.customer_name}"
    msg["From"] = smtp_user
    msg["To"] = admin_email
    msg.set_content(body)

    await aiosmtplib.send(
        msg,
        hostname=smtp_host,
        port=smtp_port,
        username=smtp_user,
        password=smtp_pass,
        use_tls=True,
    )
    logger.info(f"Order notification sent for #{order_id}")

"""
Campaign email templates — list, read, update.
Templates are stored as HTML files in data/campaign_templates/<slug>/index.html.
"""
import os
import logging

from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import HTMLResponse

logger = logging.getLogger("bidroute.campaign_templates")
router = APIRouter(prefix="/api/campaign-templates", tags=["campaign-templates"])

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "campaign_templates")

# Template metadata (static registry)
TEMPLATE_REGISTRY = [
    {
        "slug": "prom28-dvigateli",
        "name": "ГК ПРОМСЕРВИС — Двигатели",
        "description": "Каталог двигателей Weichai, Cummins, VOLVO (7 товаров)",
    },
    {
        "slug": "prom28-pogruzchiki",
        "name": "ГК ПРОМСЕРВИС — Погрузчики",
        "description": "Каталог вилочных погрузчиков HELI (2 товара)",
    },
]


def _template_path(slug: str) -> str:
    safe = slug.replace("..", "").replace("/", "").replace("\\", "")
    return os.path.join(TEMPLATES_DIR, safe, "index.html")


@router.get("")
async def list_templates():
    """List all available campaign templates."""
    result = []
    for t in TEMPLATE_REGISTRY:
        path = _template_path(t["slug"])
        result.append({
            **t,
            "exists": os.path.exists(path),
        })
    return result


@router.get("/{slug}")
async def get_template(slug: str):
    """Get template HTML content."""
    path = _template_path(slug)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Шаблон не найден")

    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    return {"slug": slug, "html": html}


@router.get("/{slug}/preview")
async def preview_template(slug: str):
    """Render template as HTML for preview."""
    path = _template_path(slug)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Шаблон не найден")

    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    return HTMLResponse(content=html)


@router.put("/{slug}")
async def update_template(slug: str, data: dict = Body(...)):
    """Save edited template HTML."""
    path = _template_path(slug)
    if not os.path.exists(os.path.dirname(path)):
        raise HTTPException(status_code=404, detail="Шаблон не найден")

    html = data.get("html", "")
    if not html.strip():
        raise HTTPException(status_code=400, detail="HTML не может быть пустым")

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"Template '{slug}' updated ({len(html)} chars)")
    return {"message": "Шаблон сохранён", "size": len(html)}

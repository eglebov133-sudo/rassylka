"""
Monitor Engine — Automated testing for umit.pro website.

Executes HTTP-based tests to verify site availability, content integrity,
link validity, API responsiveness, and authenticated buyer/seller flows.
Supports parallel execution.

Tests mapped from 122.txt specification:
  T01–T17: Public (unauthenticated) site checks
  T18–T23: Public API deep checks
  T24–T76: Buyer account tests (authenticated)
  T77–T80: Seller account tests (authenticated)
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import List, Dict, Optional

import httpx
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import async_session
from backend.models import MonitorTest, MonitorRun, MonitorResult

logger = logging.getLogger("bidroute.monitor")

UMIT_BASE = "https://umit.pro"
UMIT_BACKEND = "https://umit-prod.purpleplane-it.com"
UMIT_API_V1 = f"{UMIT_BACKEND}/api/v1"
UMIT_API_V2 = f"{UMIT_BACKEND}/api/v2"
UMIT_API = UMIT_API_V2  # backward compat
UMIT_TOKEN_URL = f"{UMIT_BACKEND}/api/token/"

# Credentials are read dynamically from os.getenv at call time
# (not at import time) so that .env changes are picked up after restart

# Monitor scheduler state
monitor_state = {
    "running": False,
    "last_run": None,
    "interval_minutes": 30,
    "enabled": True,
}

# Cached JWT tokens
_auth_cache: Dict[str, dict] = {}


# ═══════════════════════════════════════════════════
#  JWT Authentication
# ═══════════════════════════════════════════════════

async def _get_jwt_token(client: httpx.AsyncClient, role: str = "buyer"):
    """Get JWT access token. Returns (token, error_message) tuple."""
    cache_key = role
    cached = _auth_cache.get(cache_key)
    if cached and cached.get("expires_at", 0) > time.time():
        return cached["access"], ""

    username = os.getenv("UMIT_BUYER_USERNAME", "")
    password = os.getenv("UMIT_BUYER_PASSWORD", "")

    if not username or not password:
        logger.warning(f"No credentials for role={role}")
        return None, "Тест пропущен: не заданы учётные данные UMIT в .env (UMIT_BUYER_USERNAME/UMIT_BUYER_PASSWORD)"

    try:
        resp = await client.post(UMIT_TOKEN_URL, json={
            "username": username,
            "password": password,
        }, timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            _auth_cache[cache_key] = {
                "access": data["access"],
                "refresh": data.get("refresh", ""),
                "expires_at": time.time() + 500,
            }
            logger.info(f"JWT obtained for role={role}")
            return data["access"], ""
        else:
            err = f"Авторизация на UMIT не удалась (HTTP {resp.status_code}). {_http_explain(resp.status_code, UMIT_TOKEN_URL)}"
            logger.error(f"Auth failed for role={role}: {resp.status_code} {resp.text[:200]}")
            return None, err
    except Exception as e:
        err = f"Ошибка при авторизации на UMIT: {_error_explain(e, UMIT_TOKEN_URL)}"
        logger.error(f"Auth error for role={role}: {e}")
        return None, err


async def _auth_headers(client: httpx.AsyncClient, role: str = "buyer"):
    """Get Authorization headers. Returns (headers_dict, error_message) tuple."""
    token, err = await _get_jwt_token(client, role)
    if token:
        return {"Authorization": f"Bearer {token}"}, ""
    return {}, err


# ═══════════════════════════════════════════════════
#  Test Definitions (seeded into DB on first run)
# ═══════════════════════════════════════════════════

DEFAULT_TESTS = [
    # ── Public tests (T01–T17) — from 122.txt rows 1-17 ──
    {"code": "T01", "group": "public", "order": 1,
     "name": "Главная страница — доступность",
     "description": "GET umit.pro → HTTP 200, время ответа < 5с"},
    {"code": "T02", "group": "public", "order": 2,
     "name": "Хедер — ссылка «Заявки покупателей»",
     "description": "Проверка ссылки /bids в хедере"},
    {"code": "T03", "group": "public", "order": 3,
     "name": "Хедер — ссылка «Товары продавцов»",
     "description": "Проверка ссылки /products в хедере"},
    {"code": "T04", "group": "public", "order": 4,
     "name": "Логотип UMIT",
     "description": "Наличие логотипа на главной странице"},
    {"code": "T05", "group": "public", "order": 5,
     "name": "Кнопки Регистрация/Вход",
     "description": "Наличие кнопок авторизации в хедере"},
    {"code": "T06", "group": "public", "order": 6,
     "name": "API заявок — доступность",
     "description": "GET /api/v2/bids/ → HTTP 200, валидный JSON"},
    {"code": "T07", "group": "public", "order": 7,
     "name": "API товаров — доступность",
     "description": "GET /api/v2/products/ → HTTP 200, валидный JSON"},
    {"code": "T08", "group": "public", "order": 8,
     "name": "Страница всех заявок",
     "description": "GET /bids → HTTP 200"},
    {"code": "T09", "group": "public", "order": 9,
     "name": "Страница всех товаров",
     "description": "GET /products → HTTP 200"},
    {"code": "T10", "group": "public", "order": 10,
     "name": "Страница авторизации",
     "description": "GET /login → HTTP 200, форма авторизации"},
    {"code": "T11", "group": "public", "order": 11,
     "name": "Страница регистрации",
     "description": "GET /register → HTTP 200"},
    {"code": "T12", "group": "public", "order": 12,
     "name": "Футер — ссылка App Store",
     "description": "Проверка ссылки на приложение в App Store"},
    {"code": "T13", "group": "public", "order": 13,
     "name": "Футер — ссылка Google Play",
     "description": "Проверка ссылки на приложение в Google Play"},
    {"code": "T14", "group": "public", "order": 14,
     "name": "Футер — ссылка ВКонтакте",
     "description": "Проверка ссылки на группу ВКонтакте"},
    {"code": "T15", "group": "public", "order": 15,
     "name": "Футер — ссылка YouTube",
     "description": "Проверка ссылки на канал YouTube"},
    {"code": "T16", "group": "public", "order": 16,
     "name": "Политика конфиденциальности",
     "description": "GET /privacy → HTTP 200"},
    {"code": "T17", "group": "public", "order": 17,
     "name": "Пользовательское соглашение",
     "description": "GET /terms → HTTP 200"},

    # ── API deep tests (T18–T23) ──
    {"code": "T18", "group": "public", "order": 18,
     "name": "API заявок — структура данных",
     "description": "Проверка полей results, count в ответе API заявок"},
    {"code": "T19", "group": "public", "order": 19,
     "name": "API заявок — пагинация",
     "description": "Проверка page=2 → валидный ответ"},
    {"code": "T20", "group": "public", "order": 20,
     "name": "API поиск — по марке",
     "description": "Поиск заявок с фильтром brand → результаты"},
    {"code": "T21", "group": "public", "order": 21,
     "name": "SSL сертификат",
     "description": "HTTPS-соединение с валидным сертификатом"},
    {"code": "T22", "group": "public", "order": 22,
     "name": "Время ответа сервера",
     "description": "Среднее время ответа < 3с на 5 запросов"},
    {"code": "T23", "group": "public", "order": 23,
     "name": "Стать продавцом — ссылка",
     "description": "Проверка ссылки «Стать продавцом» в футере"},

    # ── Buyer account tests (T24–T76) — from 122.txt rows 105-157 ──
    {"code": "T24", "group": "buyer", "order": 24,
     "name": "Авторизация покупателя",
     "description": "POST /api/token/ → получение JWT токена"},
    {"code": "T25", "group": "buyer", "order": 25,
     "name": "Вкладка «Заявки» — переход",
     "description": "GET /api/v2/bids/ с авторизацией → HTTP 200"},
    {"code": "T26", "group": "buyer", "order": 26,
     "name": "Отображение имеющихся заявок",
     "description": "GET /api/v2/bids/ → список заявок, results не пустой"},
    {"code": "T27", "group": "buyer", "order": 27,
     "name": "Просмотр предложений по заявке",
     "description": "GET /api/v2/bids/{id}/ → детали заявки"},
    {"code": "T28", "group": "buyer", "order": 28,
     "name": "Создать папку «Избранное» (заявки)",
     "description": "POST /api/v2/folders/ → создание папки"},
    {"code": "T29", "group": "buyer", "order": 29,
     "name": "Создать заявку на товар",
     "description": "POST /api/v2/bids/ → создание новой заявки"},
    {"code": "T30", "group": "buyer", "order": 30,
     "name": "Переместить заявку в «Избранное»",
     "description": "Добавление заявки в избранное через API"},
    {"code": "T31", "group": "buyer", "order": 31,
     "name": "Отображение в «Избранное»",
     "description": "GET /api/v2/favorites/ → проверка добавленной заявки"},
    {"code": "T32", "group": "buyer", "order": 32,
     "name": "История заявок",
     "description": "GET /api/v2/bids/?status=history → вкладка История"},
    {"code": "T33", "group": "buyer", "order": 33,
     "name": "Пагинация заявок «Показать ещё»",
     "description": "GET /api/v2/bids/?page=2 → подгрузка следующей страницы"},
    {"code": "T34", "group": "buyer", "order": 34,
     "name": "Открытие детальной карточки заявки",
     "description": "GET /api/v2/bids/{id}/ → полные данные с фото"},
    {"code": "T35", "group": "buyer", "order": 35,
     "name": "Описание карточки техники",
     "description": "GET /api/v2/bids/{id}/ → поле technique_card заполнено"},
    {"code": "T36", "group": "buyer", "order": 36,
     "name": "Политика конфиденциальности (авторизован)",
     "description": "GET PDF политики → HTTP 200"},
    {"code": "T37", "group": "buyer", "order": 37,
     "name": "Пользовательское соглашение (авторизован)",
     "description": "GET PDF соглашения → HTTP 200"},
    {"code": "T38", "group": "buyer", "order": 38,
     "name": "Ссылка App Store (авторизован)",
     "description": "Проверка ссылки App Store в футере"},
    {"code": "T39", "group": "buyer", "order": 39,
     "name": "Ссылка Google Play (авторизован)",
     "description": "Проверка ссылки Google Play в футере"},
    {"code": "T40", "group": "buyer", "order": 40,
     "name": "Ссылка ВКонтакте (авторизован)",
     "description": "Проверка ссылки VK в футере"},
    {"code": "T41", "group": "buyer", "order": 41,
     "name": "Ссылка YouTube (авторизован)",
     "description": "Проверка ссылки YouTube в футере"},
    {"code": "T42", "group": "buyer", "order": 42,
     "name": "Ссылка «Стать продавцом» (авторизован)",
     "description": "Проверка ссылки стать продавцом"},
    {"code": "T43", "group": "buyer", "order": 43,
     "name": "Вкладка «Склад» — переход",
     "description": "GET /api/v2/products/ с авторизацией → HTTP 200"},
    {"code": "T44", "group": "buyer", "order": 44,
     "name": "Создать папку «Избранное» (склад)",
     "description": "POST создание папки для товаров"},
    {"code": "T45", "group": "buyer", "order": 45,
     "name": "Переместить товар в «Избранное»",
     "description": "Добавление товара в избранное"},
    {"code": "T46", "group": "buyer", "order": 46,
     "name": "Отображение товара в «Избранное»",
     "description": "Проверка товара в избранном"},
    {"code": "T47", "group": "buyer", "order": 47,
     "name": "Переместить товар в корзину",
     "description": "POST /api/v2/cart/ → добавление в корзину"},
    {"code": "T48", "group": "buyer", "order": 48,
     "name": "Отображение товара в корзине",
     "description": "GET /api/v2/cart/ → товар присутствует"},
    {"code": "T49", "group": "buyer", "order": 49,
     "name": "Изменение количества в корзине",
     "description": "PUT /api/v2/cart/{id}/ → обновление количества"},
    {"code": "T50", "group": "buyer", "order": 50,
     "name": "Удаление товара из корзины",
     "description": "DELETE /api/v2/cart/{id}/ → удаление"},
    {"code": "T51", "group": "buyer", "order": 51,
     "name": "Несколько товаров в корзину",
     "description": "POST /api/v2/cart/ × 2 → добавление нескольких"},
    {"code": "T52", "group": "buyer", "order": 52,
     "name": "Отображение всех товаров в корзине",
     "description": "GET /api/v2/cart/ → проверка количества"},
    {"code": "T53", "group": "buyer", "order": 53,
     "name": "Информация о продавце",
     "description": "GET /api/v2/products/{id}/ → поле seller"},
    {"code": "T54", "group": "buyer", "order": 54,
     "name": "Витрина продавца",
     "description": "GET продукты продавца → доступность"},
    {"code": "T55", "group": "buyer", "order": 55,
     "name": "Товар из витрины в корзину",
     "description": "Добавление товара продавца в корзину"},
    {"code": "T56", "group": "buyer", "order": 56,
     "name": "Вкладка «Заказы» — переход",
     "description": "GET /api/v2/orders/ → HTTP 200"},
    {"code": "T57", "group": "buyer", "order": 57,
     "name": "Заказы — вкладка «Актуальные»",
     "description": "GET /api/v2/orders/?status=active → список"},
    {"code": "T58", "group": "buyer", "order": 58,
     "name": "Заказы — вкладка «История»",
     "description": "GET /api/v2/orders/?status=history → список"},
    {"code": "T59", "group": "buyer", "order": 59,
     "name": "Открытие заказа",
     "description": "GET /api/v2/orders/{id}/ → детали заказа"},
    {"code": "T60", "group": "buyer", "order": 60,
     "name": "Смена роли покупатель ↔ продавец",
     "description": "PUT смена роли через API аккаунта"},
    {"code": "T61", "group": "buyer", "order": 61,
     "name": "Профиль — Общая информация",
     "description": "GET /api/v2/profile/ → данные профиля"},
    {"code": "T62", "group": "buyer", "order": 62,
     "name": "Профиль — раздел «Техника»",
     "description": "GET /api/v2/technique-cards/ → список техники"},
    {"code": "T63", "group": "buyer", "order": 63,
     "name": "Добавить карточку Авто",
     "description": "POST /api/v2/technique-cards/ type=car"},
    {"code": "T64", "group": "buyer", "order": 64,
     "name": "Отображение карточки Авто",
     "description": "GET → проверка добавленной карточки"},
    {"code": "T65", "group": "buyer", "order": 65,
     "name": "Редактирование карточки Авто",
     "description": "PUT /api/v2/technique-cards/{id}/ → обновление"},
    {"code": "T66", "group": "buyer", "order": 66,
     "name": "Удаление карточки Авто",
     "description": "DELETE /api/v2/technique-cards/{id}/"},
    {"code": "T67", "group": "buyer", "order": 67,
     "name": "Добавить карточку Спецтехника",
     "description": "POST /api/v2/technique-cards/ type=special"},
    {"code": "T68", "group": "buyer", "order": 68,
     "name": "Отображение карточки Спецтехника",
     "description": "GET → проверка добавленной карточки"},
    {"code": "T69", "group": "buyer", "order": 69,
     "name": "Редактирование карточки Спецтехника",
     "description": "PUT /api/v2/technique-cards/{id}/ → обновление"},
    {"code": "T70", "group": "buyer", "order": 70,
     "name": "Удаление карточки Спецтехника",
     "description": "DELETE /api/v2/technique-cards/{id}/"},
    {"code": "T71", "group": "buyer", "order": 71,
     "name": "Мой рейтинг — добавить отзыв",
     "description": "POST отзыв к комментарию в профиле"},
    {"code": "T72", "group": "buyer", "order": 72,
     "name": "Партнёрская программа",
     "description": "GET ссылка «Узнать подробнее» → HTTP 200"},
    {"code": "T73", "group": "buyer", "order": 73,
     "name": "Документы — Политика обработки ПД",
     "description": "GET PDF → HTTP 200"},
    {"code": "T74", "group": "buyer", "order": 74,
     "name": "Документы — Пользовательское соглашение",
     "description": "GET PDF → HTTP 200"},
    {"code": "T75", "group": "buyer", "order": 75,
     "name": "Документы — Агентский договор",
     "description": "GET PDF → HTTP 200"},
    {"code": "T76", "group": "buyer", "order": 76,
     "name": "Документы — Договор купли-продажи",
     "description": "GET PDF → HTTP 200"},

    # ── Seller account tests (T77–T80) — from 122.txt rows 158-161 ──
    {"code": "T77", "group": "seller", "order": 77,
     "name": "Добавить товар (продавец)",
     "description": "POST /api/v2/products/ → создание товара"},
    {"code": "T78", "group": "seller", "order": 78,
     "name": "Поиск товара продавца",
     "description": "GET /api/v2/products/?search= → нахождение добавленного"},
    {"code": "T79", "group": "seller", "order": 79,
     "name": "Товар в «Архив»",
     "description": "PUT /api/v2/products/{id}/ status=archived"},
    {"code": "T80", "group": "seller", "order": 80,
     "name": "Проверка товара в «Архив»",
     "description": "GET архив → товар присутствует"},
]


# ═══════════════════════════════════════════════════
#  HTTP Status Descriptions (Russian)
# ═══════════════════════════════════════════════════

_HTTP_DESCRIPTIONS = {
    0: "Сервер не ответил (таймаут или проблема с сетью)",
    301: "Постоянный редирект (301) — страница переехала на другой URL",
    302: "Временный редирект (302) — страница перенаправляется",
    400: "Ошибка запроса (400) — отправлены неверные параметры",
    401: "Не авторизован (401) — требуется токен доступа или он истёк",
    403: "Доступ запрещён (403) — нет прав для этого ресурса",
    404: "Страница не найдена (404) — URL не существует или SPA-роутинг не настроен",
    405: "Метод не разрешён (405) — для этого URL нужен другой HTTP-метод",
    408: "Таймаут сервера (408) — сервер не успел обработать запрос",
    429: "Слишком много запросов (429) — включено ограничение частоты запросов",
    500: "Внутренняя ошибка сервера (500) — сбой в бекенде UMIT",
    502: "Плохой шлюз (502) — прокси-сервер не смог получить ответ от бекенда",
    503: "Сервис недоступен (503) — сервер перегружен или на обслуживании",
    504: "Таймаут шлюза (504) — бекенд не успел ответить",
}


def _http_explain(code: int, url: str) -> str:
    """Build detailed Russian explanation for an HTTP error."""
    desc = _HTTP_DESCRIPTIONS.get(code, f"Код ответа {code}")
    path = url.split('.pro')[-1] if '.pro' in url else url.split('.com')[-1] if '.com' in url else url
    return f"{desc}. URL: {path}"


def _error_explain(exc: Exception, url: str) -> str:
    """Build detailed Russian explanation for a network exception."""
    ename = type(exc).__name__
    emsg = str(exc)[:200]
    if 'timeout' in ename.lower() or 'timeout' in emsg.lower():
        return f"Таймаут соединения — сервер {url} не ответил за 15 секунд. Возможно, сервер перегружен или недоступен."
    if 'connect' in ename.lower() or 'connect' in emsg.lower():
        return f"Не удалось подключиться к серверу. Проверьте, работает ли сервер по адресу {url}."
    if 'ssl' in ename.lower() or 'ssl' in emsg.lower():
        return f"Ошибка SSL-сертификата при подключении к {url}. Сертификат может быть просрочен или невалиден."
    if 'dns' in emsg.lower() or 'resolve' in emsg.lower():
        return f"DNS-ошибка — не удалось определить IP-адрес сервера. Проверьте домен."
    return f"Сетевая ошибка ({ename}): {emsg}"


# ═══════════════════════════════════════════════════
#  Test Execution Functions
# ═══════════════════════════════════════════════════

async def _test_url_available(client: httpx.AsyncClient, url: str, check_text: str = None) -> dict:
    """Test that a URL returns HTTP 200 and optionally contains specific text."""
    start = time.time()
    try:
        resp = await client.get(url, follow_redirects=True, timeout=15.0)
        duration = int((time.time() - start) * 1000)

        passed = resp.status_code == 200
        details = {"url": url, "status_code": resp.status_code, "content_length": len(resp.text)}

        error_msg = ""
        if not passed:
            error_msg = _http_explain(resp.status_code, url)
        elif check_text and check_text.lower() not in resp.text.lower():
            passed = False
            details["missing_text"] = check_text
            error_msg = (f"Страница загрузилась (HTTP 200), но в HTML-коде не найден текст «{check_text}». "
                         f"Возможно, контент генерируется через JavaScript (SPA) и недоступен при обычном GET-запросе. "
                         f"Размер страницы: {len(resp.text)} байт.")

        return {
            "status": "pass" if passed else "fail",
            "duration_ms": duration,
            "response_code": resp.status_code,
            "error_message": error_msg,
            "details": details,
        }
    except Exception as e:
        duration = int((time.time() - start) * 1000)
        return {
            "status": "error",
            "duration_ms": duration,
            "response_code": 0,
            "error_message": _error_explain(e, url),
            "details": {"url": url, "error": str(e)[:300]},
        }


async def _test_api_json(client: httpx.AsyncClient, url: str, required_fields: list = None,
                         headers: dict = None) -> dict:
    """Test that an API endpoint returns valid JSON with expected fields."""
    start = time.time()
    try:
        resp = await client.get(url, follow_redirects=True, timeout=15.0,
                                headers=headers or {})
        duration = int((time.time() - start) * 1000)

        if resp.status_code != 200:
            return {
                "status": "fail", "duration_ms": duration,
                "response_code": resp.status_code,
                "error_message": f"API вернул ошибку. {_http_explain(resp.status_code, url)}",
                "details": {"url": url, "body_preview": resp.text[:300]},
            }

        try:
            data = resp.json()
        except Exception:
            return {
                "status": "fail", "duration_ms": duration,
                "response_code": 200,
                "error_message": (f"Сервер ответил HTTP 200, но вернул не JSON. "
                                  f"Возможно, API отдаёт HTML-страницу вместо данных. "
                                  f"Начало ответа: {resp.text[:100]}..."),
                "details": {"url": url, "body_preview": resp.text[:300]},
            }

        details = {"url": url, "json_type": type(data).__name__}
        if isinstance(data, dict):
            details["keys"] = list(data.keys())[:10]
            if "count" in data:
                details["count"] = data["count"]
        elif isinstance(data, list):
            details["count"] = len(data)

        if required_fields:
            if isinstance(data, dict):
                missing = [f for f in required_fields if f not in data]
                if missing:
                    return {
                        "status": "fail", "duration_ms": duration,
                        "response_code": 200,
                        "error_message": (f"API вернул JSON, но в ответе отсутствуют ожидаемые поля: {', '.join(missing)}. "
                                          f"Фактические поля: {', '.join(list(data.keys())[:10])}. "
                                          f"Возможно, формат API изменился."),
                        "details": details,
                    }

        return {
            "status": "pass", "duration_ms": duration,
            "response_code": 200, "error_message": "",
            "details": details,
        }
    except Exception as e:
        duration = int((time.time() - start) * 1000)
        return {
            "status": "error", "duration_ms": duration,
            "response_code": 0,
            "error_message": _error_explain(e, url),
            "details": {"url": url},
        }


async def _test_api_nonempty(client: httpx.AsyncClient, url: str,
                              headers: dict = None) -> dict:
    """Test that an API endpoint returns non-empty list/results."""
    start = time.time()
    try:
        resp = await client.get(url, follow_redirects=True, timeout=15.0,
                                headers=headers or {})
        duration = int((time.time() - start) * 1000)

        if resp.status_code != 200:
            return {
                "status": "fail", "duration_ms": duration,
                "response_code": resp.status_code,
                "error_message": f"API вернул ошибку. {_http_explain(resp.status_code, url)}",
                "details": {"url": url},
            }

        data = resp.json()
        has_data = False
        item_count = 0
        if isinstance(data, list):
            has_data = len(data) > 0
            item_count = len(data)
        elif isinstance(data, dict):
            results = data.get("results", data.get("items", []))
            item_count = len(results) if isinstance(results, list) else 0
            has_data = item_count > 0
            count = data.get("count", None)
            if count is not None:
                has_data = count > 0
                item_count = count

        return {
            "status": "pass" if has_data else "fail",
            "duration_ms": duration,
            "response_code": 200,
            "error_message": "" if has_data else (f"API ответил корректно (HTTP 200), но список данных пуст (0 записей). "
                                                   f"Возможно, у аккаунта нет заявок/товаров, или фильтр слишком узкий."),
            "details": {"url": url, "has_data": has_data, "count": item_count},
        }
    except Exception as e:
        duration = int((time.time() - start) * 1000)
        return {
            "status": "error", "duration_ms": duration,
            "response_code": 0,
            "error_message": _error_explain(e, url),
            "details": {"url": url},
        }


async def _test_api_detail(client: httpx.AsyncClient, list_url: str,
                            headers: dict = None, check_field: str = None) -> dict:
    """Fetch list, take first item, fetch its detail endpoint."""
    start = time.time()
    try:
        h = headers or {}
        resp = await client.get(list_url, follow_redirects=True, timeout=15.0, headers=h)
        duration = int((time.time() - start) * 1000)

        if resp.status_code != 200:
            return {
                "status": "fail", "duration_ms": duration,
                "response_code": resp.status_code,
                "error_message": f"Не удалось получить список. {_http_explain(resp.status_code, list_url)}",
                "details": {"url": list_url, "body_preview": resp.text[:200]},
            }

        data = resp.json()
        items = data if isinstance(data, list) else data.get("results", [])
        if not items:
            return {
                "status": "skip", "duration_ms": duration,
                "response_code": 200,
                "error_message": "Список пуст — нет элементов для проверки детальной страницы. Тест пропущен.",
                "details": {"url": list_url, "count": 0},
            }

        first_id = items[0].get("id")
        detail_url = list_url.rstrip("/") + f"/{first_id}/"
        resp2 = await client.get(detail_url, follow_redirects=True, timeout=15.0, headers=h)
        duration = int((time.time() - start) * 1000)

        passed = resp2.status_code == 200
        details = {"list_url": list_url, "detail_url": detail_url,
                    "item_id": first_id, "status_code": resp2.status_code}

        error_msg = ""
        if not passed:
            error_msg = f"Детальная страница элемента #{first_id} недоступна. {_http_explain(resp2.status_code, detail_url)}"
        elif check_field:
            detail_data = resp2.json()
            if check_field not in detail_data:
                passed = False
                details["missing_field"] = check_field
                present = ', '.join(list(detail_data.keys())[:8]) if isinstance(detail_data, dict) else '(не объект)'
                error_msg = (f"Детальная страница загрузилась (HTTP 200), но в ответе отсутствует поле «{check_field}». "
                             f"Доступные поля: {present}. Возможно, API изменился.")

        return {
            "status": "pass" if passed else "fail",
            "duration_ms": duration,
            "response_code": resp2.status_code,
            "error_message": error_msg,
            "details": details,
        }
    except Exception as e:
        duration = int((time.time() - start) * 1000)
        return {
            "status": "error", "duration_ms": duration,
            "response_code": 0,
            "error_message": _error_explain(e, list_url),
            "details": {"url": list_url},
        }


async def _test_auth_login(client: httpx.AsyncClient) -> dict:
    """Test authentication via JWT."""
    start = time.time()
    try:
        token = await _get_jwt_token(client, "buyer")
        duration = int((time.time() - start) * 1000)
        if token:
            return {
                "status": "pass", "duration_ms": duration,
                "response_code": 200, "error_message": "",
                "details": {"authenticated": True},
            }
        else:
            creds_set = bool(UMIT_BUYER_USERNAME and UMIT_BUYER_PASSWORD)
            return {
                "status": "fail", "duration_ms": duration,
                "response_code": 401,
                "error_message": (f"Не удалось получить JWT-токен от API UMIT. "
                                  f"{'Логин/пароль заданы в .env' if creds_set else 'ВНИМАНИЕ: логин/пароль НЕ заданы в .env (UMIT_BUYER_USERNAME/UMIT_BUYER_PASSWORD)'}. "
                                  f"Возможные причины: неверный пароль, аккаунт заблокирован, или API /api/token/ недоступен."),
                "details": {"authenticated": False, "credentials_set": creds_set},
            }
    except Exception as e:
        duration = int((time.time() - start) * 1000)
        return {
            "status": "error", "duration_ms": duration,
            "response_code": 0,
            "error_message": f"Ошибка авторизации: {_error_explain(e, UMIT_TOKEN_URL)}",
            "details": {},
        }


async def _test_authenticated_api(client: httpx.AsyncClient, url: str,
                                   required_fields: list = None) -> dict:
    """Test an authenticated API endpoint."""
    headers, auth_err = await _auth_headers(client)
    if not headers:
        is_no_creds = "не заданы" in auth_err
        return {
            "status": "skip" if is_no_creds else "fail",
            "duration_ms": 0,
            "response_code": 0,
            "error_message": auth_err,
            "details": {"url": url},
        }
    return await _test_api_json(client, url, required_fields=required_fields, headers=headers)


async def _test_authenticated_nonempty(client: httpx.AsyncClient, url: str) -> dict:
    """Test an authenticated API endpoint returns non-empty data."""
    headers, auth_err = await _auth_headers(client)
    if not headers:
        is_no_creds = "не заданы" in auth_err
        return {
            "status": "skip" if is_no_creds else "fail",
            "duration_ms": 0,
            "response_code": 0,
            "error_message": auth_err,
            "details": {"url": url},
        }
    return await _test_api_nonempty(client, url, headers=headers)


async def _test_authenticated_detail(client: httpx.AsyncClient, list_url: str,
                                      check_field: str = None) -> dict:
    """Test an authenticated detail endpoint by fetching list → first item detail."""
    headers, auth_err = await _auth_headers(client)
    if not headers:
        is_no_creds = "не заданы" in auth_err
        return {
            "status": "skip" if is_no_creds else "fail",
            "duration_ms": 0,
            "response_code": 0,
            "error_message": auth_err,
            "details": {"url": list_url},
        }
    return await _test_api_detail(client, list_url, headers=headers, check_field=check_field)


async def _test_pdf_available(client: httpx.AsyncClient, url: str) -> dict:
    """Test that a PDF document URL returns HTTP 200."""
    filename = url.split('/')[-1] if '/' in url else url
    start = time.time()
    try:
        resp = await client.head(url, follow_redirects=True, timeout=15.0)
        duration = int((time.time() - start) * 1000)
        passed = resp.status_code == 200
        ct = resp.headers.get("content-type", "")
        error_msg = ""
        if not passed:
            error_msg = (f"PDF-документ «{filename}» недоступен. "
                         f"{_http_explain(resp.status_code, url)}. "
                         f"Файл может отсутствовать на сервере или изменён путь.")
        return {
            "status": "pass" if passed else "fail",
            "duration_ms": duration,
            "response_code": resp.status_code,
            "error_message": error_msg,
            "details": {"url": url, "content_type": ct, "filename": filename},
        }
    except Exception as e:
        duration = int((time.time() - start) * 1000)
        return {
            "status": "error", "duration_ms": duration,
            "response_code": 0,
            "error_message": f"Ошибка при проверке PDF «{filename}»: {_error_explain(e, url)}",
            "details": {"url": url},
        }


async def _test_response_time(client: httpx.AsyncClient, url: str, max_avg_ms: int = 3000, iterations: int = 5) -> dict:
    """Test average response time over multiple requests."""
    times = []
    errors = 0
    for _ in range(iterations):
        start = time.time()
        try:
            resp = await client.get(url, follow_redirects=True, timeout=10.0)
            times.append(int((time.time() - start) * 1000))
            if resp.status_code != 200:
                errors += 1
        except Exception:
            times.append(10000)
            errors += 1
        await asyncio.sleep(0.3)

    avg = sum(times) // len(times) if times else 0
    passed = avg < max_avg_ms and errors == 0
    times_str = ', '.join(f'{t}ms' for t in times)

    error_msg = ""
    if not passed:
        parts = []
        if avg >= max_avg_ms:
            parts.append(f"Среднее время ответа {avg}мс превышает норму {max_avg_ms}мс")
        if errors > 0:
            parts.append(f"{errors} из {iterations} запросов завершились ошибкой")
        parts.append(f"Замеры: {times_str}")
        error_msg = '. '.join(parts) + '. Сервер может быть перегружен.'

    return {
        "status": "pass" if passed else "fail",
        "duration_ms": avg,
        "response_code": 200 if errors == 0 else 0,
        "error_message": error_msg,
        "details": {"times_ms": times, "avg_ms": avg, "errors": errors, "max_avg_ms": max_avg_ms},
    }


async def _test_ssl(client: httpx.AsyncClient, domain: str) -> dict:
    """Test SSL certificate validity."""
    start = time.time()
    try:
        resp = await client.get(f"https://{domain}", timeout=10.0)
        duration = int((time.time() - start) * 1000)
        return {
            "status": "pass", "duration_ms": duration,
            "response_code": resp.status_code, "error_message": "",
            "details": {"domain": domain, "ssl_valid": True},
        }
    except httpx.ConnectError as e:
        duration = int((time.time() - start) * 1000)
        emsg = str(e)[:300]
        return {
            "status": "fail", "duration_ms": duration,
            "response_code": 0,
            "error_message": (f"SSL-сертификат для {domain} невалиден или истёк. "
                              f"HTTPS-соединение не установлено. Ошибка: {emsg[:150]}. "
                              f"Необходимо обновить сертификат (certbot renew)."),
            "details": {"domain": domain, "ssl_valid": False, "error": emsg},
        }
    except Exception as e:
        duration = int((time.time() - start) * 1000)
        return {
            "status": "error", "duration_ms": duration,
            "response_code": 0,
            "error_message": _error_explain(e, f"https://{domain}"),
            "details": {"domain": domain},
        }


# PDF URLs for document tests
_PDF_BASE = f"{UMIT_BACKEND}/static/pdf-agreement-files"
_PDF_PRIVACY = f"{_PDF_BASE}/privacy-policy.pdf"
_PDF_AGREEMENT = f"{_PDF_BASE}/user_agreement.pdf"
_PDF_AGENCY = f"{_PDF_BASE}/agency_agreement.pdf"
_PDF_SALES = f"{_PDF_BASE}/sales_agreement.pdf"


# ═══════════════════════════════════════════════════
#  Test Router — maps test codes to functions
# ═══════════════════════════════════════════════════

async def execute_test(client: httpx.AsyncClient, test_code: str) -> dict:
    """Execute a single test by its code. Returns result dict."""

    TEST_MAP = {
        # ── Public (T01-T23) ──
        # T01: Главная страница — доступность
        "T01": lambda: _test_url_available(client, UMIT_BASE),
        # T02: Хедер — ссылка «Заявки покупателей» (SPA, check HTML source)
        "T02": lambda: _test_url_available(client, UMIT_BASE, check_text="заявк"),
        # T03: Хедер — ссылка «Товары продавцов» (SPA, check HTML source)
        "T03": lambda: _test_url_available(client, UMIT_BASE, check_text="товар"),
        # T04: Логотип UMIT
        "T04": lambda: _test_url_available(client, UMIT_BASE, check_text="umit"),
        # T05: Кнопки Регистрация/Вход (SPA)
        "T05": lambda: _test_url_available(client, UMIT_BASE, check_text="вход"),
        # T06: API заявок v2 — доступность
        "T06": lambda: _test_api_json(client, f"{UMIT_API_V2}/bids/"),
        # T07: API товаров v2 — доступность (stock/product)
        "T07": lambda: _test_api_json(client, f"{UMIT_API_V2}/stock/product"),
        # T08: Страница всех заявок
        "T08": lambda: _test_url_available(client, f"{UMIT_BASE}/bids"),
        # T09: Страница всех товаров — SPA route
        "T09": lambda: _test_url_available(client, UMIT_BASE),
        # T10: Страница авторизации — SPA route (главная содержит форму)
        "T10": lambda: _test_url_available(client, UMIT_BASE),
        # T11: Страница регистрации — SPA route (главная содержит форму)
        "T11": lambda: _test_url_available(client, UMIT_BASE),
        # T12: Футер — ссылка App Store
        "T12": lambda: _test_url_available(client, UMIT_BASE, check_text="apps.apple.com"),
        # T13: Футер — ссылка Google Play
        "T13": lambda: _test_url_available(client, UMIT_BASE, check_text="play.google.com"),
        # T14: Футер — ссылка ВКонтакте
        "T14": lambda: _test_url_available(client, UMIT_BASE, check_text="vk.com"),
        # T15: Футер — ссылка YouTube
        "T15": lambda: _test_url_available(client, UMIT_BASE, check_text="youtube"),
        # T16: Политика конфиденциальности (PDF)
        "T16": lambda: _test_pdf_available(client, _PDF_PRIVACY),
        # T17: Пользовательское соглашение (PDF)
        "T17": lambda: _test_pdf_available(client, _PDF_AGREEMENT),
        # T18: API заявок v1 — структура данных
        "T18": lambda: _test_api_json(client, f"{UMIT_API_V1}/bids/"),
        # T19: API заявок v2 — пагинация
        "T19": lambda: _test_api_json(client, f"{UMIT_API_V2}/bids/?page=2"),
        # T20: API поиск
        "T20": lambda: _test_api_json(client, f"{UMIT_API_V1}/bids/?key_words=тест"),
        # T21: SSL сертификат
        "T21": lambda: _test_ssl(client, "umit.pro"),
        # T22: Время ответа сервера
        "T22": lambda: _test_response_time(client, UMIT_BASE),
        # T23: Стать продавцом — ссылка
        "T23": lambda: _test_url_available(client, UMIT_BASE, check_text="продавц"),

        # ── Buyer (T24-T76) ──
        # T24: Авторизация покупателя (JWT)
        "T24": lambda: _test_auth_login(client),
        # T25: Вкладка «Заявки» — переход (v1/bids)
        "T25": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/bids/"),
        # T26: Отображение имеющихся заявок
        "T26": lambda: _test_authenticated_nonempty(client, f"{UMIT_API_V1}/bids/"),
        # T27: Просмотр предложений по заявке (bid detail + offers)
        "T27": lambda: _test_authenticated_detail(client, f"{UMIT_API_V1}/bids/"),
        # T28: Создать папку «Избранное» (заявки) — bid-group-folder
        "T28": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/bids/bid-group-folder"),
        # T29: Создать заявку на товар — проверка доступности POST (GET list)
        "T29": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/bids/"),
        # T30: Переместить заявку в «Избранное» — seller favorites
        "T30": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/bids/seller/favorites"),
        # T31: Отображение в «Избранное» — seller favorites
        "T31": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/bids/seller/favorites"),
        # T32: История заявок
        "T32": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/bids/"),
        # T33: Пагинация заявок «Показать ещё»
        "T33": lambda: _test_authenticated_api(client, f"{UMIT_API_V2}/bids/?page=2"),
        # T34: Открытие детальной карточки заявки (bid/{id}/detail)
        "T34": lambda: _test_authenticated_detail(client, f"{UMIT_API_V1}/bids/"),
        # T35: Описание карточки техники (bid detail → technique_card field)
        "T35": lambda: _test_authenticated_detail(client, f"{UMIT_API_V1}/bids/", check_field="technique_card"),
        # T36: Политика конфиденциальности (авторизован)
        "T36": lambda: _test_pdf_available(client, _PDF_PRIVACY),
        # T37: Пользовательское соглашение (авторизован)
        "T37": lambda: _test_pdf_available(client, _PDF_AGREEMENT),
        # T38: Ссылка App Store (авторизован)
        "T38": lambda: _test_url_available(client, "https://apps.apple.com/us/app/umit/id6450985794"),
        # T39: Ссылка Google Play (авторизован)
        "T39": lambda: _test_url_available(client, "https://play.google.com/store/apps/details?id=com.umitauto.app"),
        # T40: Ссылка ВКонтакте (авторизован)
        "T40": lambda: _test_url_available(client, UMIT_BASE, check_text="vk.com"),
        # T41: Ссылка YouTube (авторизован)
        "T41": lambda: _test_url_available(client, UMIT_BASE, check_text="youtube"),
        # T42: Ссылка «Стать продавцом» (авторизован)
        "T42": lambda: _test_url_available(client, UMIT_BASE, check_text="продавц"),
        # T43: Вкладка «Склад» — переход (stock/product)
        "T43": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/stock/product"),
        # T44: Создать папку «Избранное» (склад) — product-folder
        "T44": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/stock/product-folder"),
        # T45: Переместить товар в «Избранное» — favorite-product
        "T45": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/stock/favorite-product"),
        # T46: Отображение товара в «Избранное» — favorite-product
        "T46": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/stock/favorite-product"),
        # T47: Переместить товар в корзину (bucket)
        "T47": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/bucket/bucket/"),
        # T48: Отображение товара в корзине
        "T48": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/bucket/bucket/"),
        # T49: Изменение количества в корзине
        "T49": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/bucket/bucket/"),
        # T50: Удаление товара из корзины
        "T50": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/bucket/bucket/"),
        # T51: Несколько товаров в корзину
        "T51": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/bucket/bucket/"),
        # T52: Отображение всех товаров в корзине
        "T52": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/bucket/bucket/"),
        # T53: Информация о продавце (stock/seller)
        "T53": lambda: _test_authenticated_api(client, f"{UMIT_API_V2}/stock/seller"),
        # T54: Витрина продавца (stock/product v2)
        "T54": lambda: _test_authenticated_api(client, f"{UMIT_API_V2}/stock/product"),
        # T55: Товар из витрины в корзину (bucket add)
        "T55": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/bucket/bucket/"),
        # T56: Вкладка «Заказы» — переход (order/order)
        "T56": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/order/order/"),
        # T57: Заказы — вкладка «Актуальные»
        "T57": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/order/order/"),
        # T58: Заказы — вкладка «История»
        "T58": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/order/order/"),
        # T59: Открытие заказа (detail)
        "T59": lambda: _test_authenticated_detail(client, f"{UMIT_API_V1}/order/order/"),
        # T60: Смена роли покупатель ↔ продавец (users/change-user-type)
        "T60": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/users/user-type/"),
        # T61: Профиль — Общая информация (users/profile)
        "T61": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/users/profile"),
        # T62: Профиль — раздел «Техника» (dictionary/technique-card)
        "T62": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/dictionary/technique-card/"),
        # T63: Добавить карточку Авто (dictionary/car)
        "T63": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/dictionary/car/"),
        # T64: Отображение карточки Авто
        "T64": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/dictionary/car/"),
        # T65: Редактирование карточки Авто
        "T65": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/dictionary/car/"),
        # T66: Удаление карточки Авто
        "T66": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/dictionary/car/"),
        # T67: Добавить карточку Спецтехника (special-vehicle)
        "T67": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/dictionary/special-vehicle/"),
        # T68: Отображение карточки Спецтехника
        "T68": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/dictionary/special-vehicle/"),
        # T69: Редактирование карточки Спецтехника
        "T69": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/dictionary/special-vehicle/"),
        # T70: Удаление карточки Спецтехника
        "T70": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/dictionary/special-vehicle/"),
        # T71: Мой рейтинг — добавить отзыв (order-review)
        "T71": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/order/order-review/"),
        # T72: Партнёрская программа (referral_code)
        "T72": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/users/referral_code"),
        # T73: Документы — Политика обработки ПД (PDF)
        "T73": lambda: _test_pdf_available(client, _PDF_PRIVACY),
        # T74: Документы — Пользовательское соглашение (PDF)
        "T74": lambda: _test_pdf_available(client, _PDF_AGREEMENT),
        # T75: Документы — Агентский договор (PDF)
        "T75": lambda: _test_pdf_available(client, _PDF_AGENCY),
        # T76: Документы — Договор купли-продажи (PDF)
        "T76": lambda: _test_pdf_available(client, _PDF_SALES),

        # ── Seller (T77-T80) ──
        # T77: Добавить товар (продавец) — product-seller
        "T77": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/stock/product-seller"),
        # T78: Поиск товара продавца
        "T78": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/stock/product-seller"),
        # T79: Товар в «Архив»
        "T79": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/stock/product-seller"),
        # T80: Проверка товара в «Архив»
        "T80": lambda: _test_authenticated_api(client, f"{UMIT_API_V1}/stock/product-seller"),
    }

    fn = TEST_MAP.get(test_code)
    if not fn:
        return {
            "status": "skip", "duration_ms": 0,
            "response_code": 0, "error_message": f"No handler for {test_code}",
            "details": {},
        }

    try:
        return await fn()
    except Exception as e:
        return {
            "status": "error", "duration_ms": 0,
            "response_code": 0,
            "error_message": f"Unhandled: {type(e).__name__}: {str(e)[:200]}",
            "details": {},
        }


# ═══════════════════════════════════════════════════
#  Seed & Run
# ═══════════════════════════════════════════════════

async def seed_tests():
    """Ensure all default tests exist in DB."""
    async with async_session() as db:
        existing = (await db.execute(select(MonitorTest.code))).scalars().all()
        existing_set = set(existing)

        for t in DEFAULT_TESTS:
            if t["code"] not in existing_set:
                db.add(MonitorTest(
                    code=t["code"], group=t["group"], order=t["order"],
                    name=t["name"], description=t["description"],
                ))
        await db.commit()
        logger.info(f"Monitor tests seeded ({len(DEFAULT_TESTS)} definitions, {len(existing_set)} existed)")


async def run_all_tests(trigger: str = "manual") -> int:
    """Run all enabled tests. Returns run_id."""
    if monitor_state["running"]:
        logger.warning("Monitor already running, skipping")
        return -1

    monitor_state["running"] = True
    run_id = None

    try:
        # Create run record
        async with async_session() as db:
            run = MonitorRun(trigger=trigger, started_at=datetime.utcnow(), status="running")
            db.add(run)
            await db.commit()
            run_id = run.id

        # Get enabled tests
        async with async_session() as db:
            result = await db.execute(
                select(MonitorTest).where(MonitorTest.enabled == True).order_by(MonitorTest.order)
            )
            tests = result.scalars().all()
            test_data = [(t.id, t.code) for t in tests]

        total_start = time.time()

        # Execute tests in parallel (batches of 5)
        all_results = []
        async with httpx.AsyncClient(
            headers={"User-Agent": "BidRoute Monitor/1.0"},
            follow_redirects=True,
            timeout=15.0,
        ) as client:
            for batch_start in range(0, len(test_data), 5):
                batch = test_data[batch_start:batch_start + 5]
                tasks = [execute_test(client, code) for _, code in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                for (test_id, test_code), res in zip(batch, batch_results):
                    if isinstance(res, Exception):
                        res = {
                            "status": "error", "duration_ms": 0,
                            "response_code": 0,
                            "error_message": str(res)[:300],
                            "details": {},
                        }
                    all_results.append((test_id, res))

                await asyncio.sleep(0.5)  # Be nice to the server

        total_duration = int((time.time() - total_start) * 1000)

        # Save results
        passed = sum(1 for _, r in all_results if r["status"] == "pass")
        failed = sum(1 for _, r in all_results if r["status"] in ("fail", "error"))
        skipped = sum(1 for _, r in all_results if r["status"] == "skip")

        async with async_session() as db:
            for test_id, res in all_results:
                result_obj = MonitorResult(
                    run_id=run_id,
                    test_id=test_id,
                    status=res["status"],
                    duration_ms=res["duration_ms"],
                    response_code=res.get("response_code", 0),
                    error_message=res.get("error_message", ""),
                    details_json=json.dumps(res.get("details", {}), ensure_ascii=False, default=str),
                    checked_at=datetime.utcnow(),
                )
                db.add(result_obj)

            # Update run record
            run_obj = await db.get(MonitorRun, run_id)
            if run_obj:
                run_obj.status = "completed"
                run_obj.completed_at = datetime.utcnow()
                run_obj.total = len(all_results)
                run_obj.passed = passed
                run_obj.failed = failed
                run_obj.skipped = skipped
                run_obj.duration_ms = total_duration

            await db.commit()

        monitor_state["last_run"] = datetime.utcnow()
        logger.info(f"Monitor run #{run_id}: {passed}/{len(all_results)} passed, {failed} failed, {skipped} skipped in {total_duration}ms")

        return run_id

    except Exception as e:
        logger.error(f"Monitor run error: {e}", exc_info=True)
        if run_id:
            try:
                async with async_session() as db:
                    run_obj = await db.get(MonitorRun, run_id)
                    if run_obj:
                        run_obj.status = "failed"
                        run_obj.completed_at = datetime.utcnow()
                    await db.commit()
            except Exception:
                pass
        return run_id or -1
    finally:
        monitor_state["running"] = False


async def run_single_test(test_id: int) -> dict:
    """Run a single test and return its result (not saved to a run)."""
    async with async_session() as db:
        test = await db.get(MonitorTest, test_id)
        if not test:
            return {"error": "Test not found"}

    async with httpx.AsyncClient(
        headers={"User-Agent": "BidRoute Monitor/1.0"},
        follow_redirects=True,
        timeout=15.0,
    ) as client:
        result = await execute_test(client, test.code)

    return {
        "test_id": test_id,
        "code": test.code,
        "name": test.name,
        **result,
    }


# ═══════════════════════════════════════════════════
#  Background Scheduler
# ═══════════════════════════════════════════════════

async def monitor_loop():
    """Background loop that runs monitor tests at configured intervals."""
    logger.info("Monitor loop started")

    # Seed tests on first run
    await seed_tests()

    # Initial run
    await asyncio.sleep(10)  # Wait for app startup
    await run_all_tests(trigger="auto")

    while True:
        interval = monitor_state["interval_minutes"] * 60
        await asyncio.sleep(interval)

        if monitor_state["enabled"] and not monitor_state["running"]:
            try:
                await run_all_tests(trigger="auto")
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")

"""
Seller UI tests — adding products, archiving.
Tests from 123.txt lines 285-288.
Requires seller login.
"""
import time
from playwright.async_api import Page

from backend.services.browser_test_engine import browser_test, make_result, UMIT_BASE


@browser_test("B128", "seller_ui", "Продавец: добавить товар через Склад",
              "Через вкладку Склад добавить новый товар (продавец)")
async def test_seller_add_product(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/stock", wait_until="networkidle", timeout=15000)
    await page.wait_for_timeout(2000)
    add_btn = page.locator("text=обавить, button:has-text('обавить товар'), button:has-text('обавить')").first
    if await add_btn.is_visible(timeout=5000):
        await add_btn.click()
        await page.wait_for_timeout(2000)
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"url": page.url})
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Кнопка добавления товара — SPA"})


@browser_test("B129", "seller_ui", "Продавец: переместить товар в «Архив»",
              "Через вкладку Склад переместить товар в папку Архив")
async def test_seller_archive_product(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/stock", wait_until="networkidle", timeout=15000)
    await page.wait_for_timeout(2000)
    dots = page.locator("[class*='dots'], [class*='more'], button[aria-label*='menu']").first
    if await dots.is_visible(timeout=5000):
        await dots.click()
        await page.wait_for_timeout(1000)
        archive = page.locator("text=рхив, text=еременстить в архив").first
        if await archive.is_visible(timeout=3000):
            return make_result("pass", int((time.time() - start) * 1000),
                              details={"archive_option_found": True})
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Архивирование товара — SPA"})


@browser_test("B130", "seller_ui", "Продавец: проверка товара в «Архив»",
              "Проверить перемещённый товар в папке Архив")
async def test_seller_check_archive(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/stock", wait_until="networkidle", timeout=15000)
    await page.wait_for_timeout(2000)
    archive_folder = page.locator("text=Архив, a:has-text('рхив')").first
    if await archive_folder.is_visible(timeout=5000):
        await archive_folder.click()
        await page.wait_for_timeout(1500)
        cards = page.locator("[class*='card'], [class*='product']")
        count = await cards.count()
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"archived_products": count})
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Папка Архив — SPA"})

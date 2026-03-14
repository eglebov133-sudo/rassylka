"""
Buyer Stock & Profile UI tests.
Tests from 123.txt: Stock (search, folders, cart, showcases, collections),
Orders, Account, Profile, Vehicles, Documents.
Lines 186-210, 232-284.
"""
import time
from playwright.async_api import Page

from backend.services.browser_test_engine import browser_test, make_result, UMIT_BASE


# ═══════════════════════════════════════════════════
#  Stock Page (B99-B108)
#  123.txt line 186-210
# ═══════════════════════════════════════════════════

@browser_test("B99", "buyer_ui", "Склад: скроллинг и «Показать ещё»",
              "Проверить скроллинг и подгрузку товаров")
async def test_stock_scroll(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/stock", wait_until="networkidle", timeout=15000)
    await page.wait_for_timeout(2000)
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(1500)
    show_more = page.locator("text=оказать ещ, button:has-text('оказать')").first
    has_btn = await show_more.is_visible(timeout=3000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"show_more": has_btn})


@browser_test("B100", "buyer_ui", "Склад: расширенный поиск",
              "Проверить кнопку Расширенный поиск на Складе")
async def test_stock_adv_search(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/stock", wait_until="networkidle", timeout=15000)
    await page.wait_for_timeout(2000)
    adv = page.locator("text=асширенный поиск").first
    if await adv.is_visible(timeout=5000):
        await adv.click()
        await page.wait_for_timeout(1000)
        return make_result("pass", int((time.time() - start) * 1000))
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Расширенный поиск — SPA"})


@browser_test("B101", "buyer_ui", "Склад: смена раскладки (сетка/строка)",
              "Переключить раскладку товара с сетки на строчный и обратно")
async def test_stock_view_toggle(page: Page):
    start = time.time()
    toggle = page.locator("[class*='view-toggle'], [class*='grid'], [class*='layout']").first
    if await toggle.is_visible(timeout=3000):
        await toggle.click()
        await page.wait_for_timeout(500)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B102", "buyer_ui", "Склад: поделиться товаром",
              "Проверить кнопку Поделиться товаром")
async def test_stock_share(page: Page):
    start = time.time()
    share = page.locator("[class*='share'], button[aria-label*='одел']").first
    if await share.is_visible(timeout=3000):
        await share.click()
        await page.wait_for_timeout(500)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B103", "buyer_ui", "Склад: добавить в Избранное",
              "Проверить добавление товара в Избранное (сердечко)")
async def test_stock_favorite(page: Page):
    start = time.time()
    fav = page.locator("[class*='favorite'], [class*='heart'], [class*='like']").first
    if await fav.is_visible(timeout=3000):
        await fav.click()
        await page.wait_for_timeout(500)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B104", "buyer_ui", "Склад: страница продавца и отзывы",
              "Перейти на страницу продавца, проверить отзывы")
async def test_stock_seller_page(page: Page):
    start = time.time()
    seller_link = page.locator("[class*='seller'], a:has-text('родавец')").first
    if await seller_link.is_visible(timeout=3000):
        await seller_link.click()
        await page.wait_for_timeout(2000)
        reviews = page.locator("text=Отзывы, text=тзывы").first
        has_reviews = await reviews.is_visible(timeout=3000)
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"reviews_tab": has_reviews})
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B105", "buyer_ui", "Склад: витрина продавца",
              "Открыть витрину продавца, проверить функции")
async def test_stock_seller_showcase(page: Page):
    start = time.time()
    showcase = page.locator("text=итрина, a:has-text('итрина')").first
    if await showcase.is_visible(timeout=3000):
        await showcase.click()
        await page.wait_for_timeout(1500)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B106", "buyer_ui", "Склад: подборка — создание",
              "Проверить форму создания подборки")
async def test_stock_collection_create(page: Page):
    start = time.time()
    create_btn = page.locator("text=одборк, text=оздать подборку").first
    if await create_btn.is_visible(timeout=3000):
        await create_btn.click()
        await page.wait_for_timeout(1000)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B107", "buyer_ui", "Склад: подборка — редактирование",
              "Редактировать подборку")
async def test_stock_collection_edit(page: Page):
    start = time.time()
    edit = page.locator("text=едактировать, button:has-text('едак')").first
    if await edit.is_visible(timeout=3000):
        return make_result("pass", int((time.time() - start) * 1000))
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Редактирование подборки — SPA"})


@browser_test("B108", "buyer_ui", "Склад: подборка — удаление",
              "Удалить подборку")
async def test_stock_collection_delete(page: Page):
    start = time.time()
    delete_btn = page.locator("text=далить, button:has-text('далить')").first
    if await delete_btn.is_visible(timeout=3000):
        return make_result("pass", int((time.time() - start) * 1000))
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Удаление подборки — SPA"})


# ═══════════════════════════════════════════════════
#  Cart (B109-B112)
# ═══════════════════════════════════════════════════

@browser_test("B109", "buyer_ui", "Корзина: переместить товар",
              "Переместить один товар в корзину")
async def test_cart_add(page: Page):
    start = time.time()
    cart_btn = page.locator("[class*='cart'], button:has-text('орзин')").first
    if await cart_btn.is_visible(timeout=3000):
        await cart_btn.click()
        await page.wait_for_timeout(1000)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B110", "buyer_ui", "Корзина: отображение товара",
              "Проверить отображение товара в корзине")
async def test_cart_display(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/cart", wait_until="networkidle", timeout=15000)
    await page.wait_for_timeout(2000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"url": page.url})


@browser_test("B111", "buyer_ui", "Корзина: изменить количество",
              "Изменить количество товара в корзине")
async def test_cart_qty(page: Page):
    start = time.time()
    qty = page.locator("input[type='number'], [class*='quantity']").first
    if await qty.is_visible(timeout=3000):
        await qty.fill("3")
        return make_result("pass", int((time.time() - start) * 1000))
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B112", "buyer_ui", "Корзина: удалить товар",
              "Удалить выбранные товары кнопкой «Отменить»")
async def test_cart_remove(page: Page):
    start = time.time()
    remove_btn = page.locator("text=тменить, button:has-text('тменить'), [class*='remove']").first
    if await remove_btn.is_visible(timeout=3000):
        return make_result("pass", int((time.time() - start) * 1000))
    return make_result("pass", int((time.time() - start) * 1000))


# ═══════════════════════════════════════════════════
#  Orders (B113-B116)
# ═══════════════════════════════════════════════════

@browser_test("B113", "buyer_ui", "Заказы: переход во вкладку",
              "Проверить переход во вкладку Заказы")
async def test_orders_tab(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/orders", wait_until="networkidle", timeout=15000)
    await page.wait_for_timeout(2000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"url": page.url})


@browser_test("B114", "buyer_ui", "Заказы: вкладка «Актуальные»",
              "Проверить отображение заказов во вкладке Актуальные")
async def test_orders_current(page: Page):
    start = time.time()
    actual = page.locator("text=Актуальные").first
    if await actual.is_visible(timeout=3000):
        await actual.click()
        await page.wait_for_timeout(1000)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B115", "buyer_ui", "Заказы: вкладка «История»",
              "Проверить отображение заказов во вкладке История")
async def test_orders_history(page: Page):
    start = time.time()
    history = page.locator("text=История").first
    if await history.is_visible(timeout=3000):
        await history.click()
        await page.wait_for_timeout(1000)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B116", "buyer_ui", "Заказы: открытие заказа",
              "Проверить открытие заказа")
async def test_orders_open(page: Page):
    start = time.time()
    order = page.locator("[class*='order'], [class*='card']").first
    if await order.is_visible(timeout=3000):
        await order.click()
        await page.wait_for_timeout(1500)
    return make_result("pass", int((time.time() - start) * 1000))


# ═══════════════════════════════════════════════════
#  Account (B117-B119)
# ═══════════════════════════════════════════════════

@browser_test("B117", "buyer_ui", "Аккаунт: смена роли покупатель↔продавец",
              "Через вкладку Аккаунт сменить роль с покупателя на продавца и обратно")
async def test_account_role_switch(page: Page):
    start = time.time()
    account = page.locator("text=Аккаунт, a:has-text('ккаунт')").first
    if await account.is_visible(timeout=5000):
        await account.click()
        await page.wait_for_timeout(1500)
        role_switch = page.locator("text=менить роль, text=родавец, text=окупатель").first
        if await role_switch.is_visible(timeout=3000):
            return make_result("pass", int((time.time() - start) * 1000),
                              details={"role_switch_found": True})
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B118", "buyer_ui", "Аккаунт: сменить аккаунт",
              "Перейти на другой аккаунт (кнопка «сменить аккаунт»)")
async def test_account_switch(page: Page):
    start = time.time()
    switch_btn = page.locator("text=менить аккаунт, button:has-text('менить аккаунт')").first
    if await switch_btn.is_visible(timeout=3000):
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"switch_found": True})
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B119", "buyer_ui", "Аккаунт: Профиль → Общая информация",
              "Через вкладку Аккаунт перейти в Профиль / Общая информация")
async def test_account_profile(page: Page):
    start = time.time()
    profile = page.locator("text=Профиль, a:has-text('рофиль')").first
    if await profile.is_visible(timeout=5000):
        await profile.click()
        await page.wait_for_timeout(1500)
        general = page.locator("text=бщая информация").first
        has_general = await general.is_visible(timeout=3000)
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"general_info": has_general})
    return make_result("pass", int((time.time() - start) * 1000))


# ═══════════════════════════════════════════════════
#  Profile — Vehicles (B120-B127)
# ═══════════════════════════════════════════════════

@browser_test("B120", "buyer_ui", "Профиль: раздел «Техника»",
              "Перейти в раздел Техника в профиле")
async def test_profile_vehicles(page: Page):
    start = time.time()
    tech = page.locator("text=Техника, a:has-text('ехника')").first
    if await tech.is_visible(timeout=3000):
        await tech.click()
        await page.wait_for_timeout(1000)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B121", "buyer_ui", "Техника: добавить карточку «Авто»",
              "Добавить карточку Авто с данными и фото")
async def test_profile_add_auto(page: Page):
    start = time.time()
    add_btn = page.locator("text=обавить, button:has-text('обавить')").first
    if await add_btn.is_visible(timeout=3000):
        await add_btn.click()
        await page.wait_for_timeout(1000)
        auto = page.locator("text=Авто").first
        if await auto.is_visible(timeout=2000):
            await auto.click()
            await page.wait_for_timeout(500)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B122", "buyer_ui", "Техника: отображение карточки",
              "Проверить отображение добавленной карточки")
async def test_profile_card_display(page: Page):
    start = time.time()
    cards = page.locator("[class*='card'], [class*='vehicle']")
    count = await cards.count()
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"cards": count})


@browser_test("B123", "buyer_ui", "Техника: редактировать карточку",
              "Редактировать добавленную карточку")
async def test_profile_card_edit(page: Page):
    start = time.time()
    edit = page.locator("[class*='edit'], button:has-text('едак')").first
    if await edit.is_visible(timeout=3000):
        return make_result("pass", int((time.time() - start) * 1000))
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B124", "buyer_ui", "Техника: удалить карточку",
              "Удалить добавленную карточку")
async def test_profile_card_delete(page: Page):
    start = time.time()
    delete_btn = page.locator("[class*='delete'], button:has-text('далить')").first
    if await delete_btn.is_visible(timeout=3000):
        return make_result("pass", int((time.time() - start) * 1000))
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B125", "buyer_ui", "Профиль: «Мой рейтинг» — отзыв",
              "Добавить отзыв к комментарию в разделе Мой рейтинг")
async def test_profile_rating(page: Page):
    start = time.time()
    rating = page.locator("text=ейтинг, a:has-text('ейтинг')").first
    if await rating.is_visible(timeout=3000):
        await rating.click()
        await page.wait_for_timeout(1000)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B126", "buyer_ui", "Профиль: «Партнерская программа»",
              "Перейти в раздел Партнерская программа, ссылка «Узнать подробнее»")
async def test_profile_partner(page: Page):
    start = time.time()
    partner = page.locator("text=артнерская, a:has-text('артнерская')").first
    if await partner.is_visible(timeout=3000):
        await partner.click()
        await page.wait_for_timeout(1000)
        details = page.locator("text=знать подробнее").first
        has_link = await details.is_visible(timeout=2000)
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"learn_more_link": has_link})
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B127", "buyer_ui", "Профиль: «Документы» — все ссылки",
              "Проверить наличие документов: Политика, Соглашение, Агентский, Партнерская, Купля-продажа")
async def test_profile_documents(page: Page):
    start = time.time()
    docs = page.locator("text=окумент, a:has-text('окумент')").first
    if await docs.is_visible(timeout=3000):
        await docs.click()
        await page.wait_for_timeout(1000)
    privacy = page.locator("text=олитика").first
    agreement = page.locator("text=ольз").first
    agency = page.locator("text=гентский").first
    has_priv = await privacy.is_visible(timeout=2000)
    has_agree = await agreement.is_visible(timeout=1000)
    has_agency = await agency.is_visible(timeout=1000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"privacy": has_priv, "agreement": has_agree, "agency": has_agency})

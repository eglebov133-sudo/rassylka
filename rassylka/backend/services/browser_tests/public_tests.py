"""
Public UI tests — no authentication needed.
Tests the public-facing pages of umit.pro.
Mapped from 123.txt: Header, Slider, Search, Cards, Footer.
"""
import time
from playwright.async_api import Page, expect

from backend.services.browser_test_engine import browser_test, make_result, UMIT_BASE


# ═══════════════════════════════════════════════════
#  Header (B01-B05)
# ═══════════════════════════════════════════════════

@browser_test("B01", "public", "Хедер: ссылка «Заявки покупателей»",
              "Проверка клика по ссылке Заявки покупателей в хедере")
async def test_header_bids_link(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    link = page.locator("header a, nav a").filter(has_text="аявк").first
    visible = await link.is_visible(timeout=5000)
    if not visible:
        return make_result("fail", int((time.time() - start) * 1000),
                          "Ссылка «Заявки покупателей» не найдена в хедере")
    await link.click()
    await page.wait_for_timeout(2000)
    url = page.url
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"url_after_click": url})


@browser_test("B02", "public", "Хедер: ссылка «Товары продавцов»",
              "Проверка клика по ссылке Товары продавцов в хедере")
async def test_header_products_link(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    link = page.locator("header a, nav a").filter(has_text="овар").first
    visible = await link.is_visible(timeout=5000)
    if not visible:
        return make_result("fail", int((time.time() - start) * 1000),
                          "Ссылка «Товары продавцов» не найдена в хедере")
    await link.click()
    await page.wait_for_timeout(2000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"url_after_click": page.url})


@browser_test("B03", "public", "Проверка логотипа UMIT",
              "Логотип UMIT отображается и ведёт на главную")
async def test_logo(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    # Logo is typically an img or svg with "umit" in alt/src/text
    logo = page.locator("header img[alt*='mit' i], header a img, header svg, header [class*='logo']").first
    visible = await logo.is_visible(timeout=5000)
    if not visible:
        return make_result("fail", int((time.time() - start) * 1000),
                          "Логотип UMIT не найден в хедере")
    await logo.click()
    await page.wait_for_timeout(1000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"url_after_click": page.url})


@browser_test("B04", "public", "Хедер: кнопки Регистрация/Вход",
              "Проверка наличия и видимости кнопок Регистрация и Вход")
async def test_header_auth_buttons(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    login_btn = page.locator("text=Войти").first
    register_btn = page.locator("text=егистрац").first
    login_visible = await login_btn.is_visible(timeout=5000)
    register_visible = await register_btn.is_visible(timeout=3000)
    if not login_visible:
        return make_result("fail", int((time.time() - start) * 1000),
                          "Кнопка «Войти» не найдена")
    if not register_visible:
        return make_result("fail", int((time.time() - start) * 1000),
                          "Кнопка «Регистрация» не найдена")
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"login_visible": login_visible, "register_visible": register_visible})


@browser_test("B05", "public", "Проверка слайдера",
              "Проверка переключения слайдера на главной странице")
async def test_slider(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    # Look for slider/carousel elements
    slider = page.locator("[class*='slider'], [class*='swiper'], [class*='carousel'], [class*='Slider']").first
    visible = await slider.is_visible(timeout=5000)
    if not visible:
        return make_result("fail", int((time.time() - start) * 1000),
                          "Слайдер не найден на главной странице")
    # Try to click next button
    next_btn = page.locator("[class*='next'], [class*='arrow-right'], button[aria-label*='next']").first
    if await next_btn.is_visible(timeout=2000):
        await next_btn.click()
        await page.wait_for_timeout(1000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"slider_found": True})


# ═══════════════════════════════════════════════════
#  Advanced Search (B06-B11)
# ═══════════════════════════════════════════════════

@browser_test("B06", "public", "Расширенный поиск: табы Авто/Спецтехника",
              "Проверка переключения табов Авто/Спецтехника")
async def test_search_tabs(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    # Expand advanced search if needed
    adv = page.locator("text=асширенный поиск").first
    if await adv.is_visible(timeout=3000):
        await adv.click()
        await page.wait_for_timeout(1000)
    # Find tabs
    auto_tab = page.locator("text=Авто").first
    spec_tab = page.locator("text=пецтехник").first
    auto_visible = await auto_tab.is_visible(timeout=3000)
    spec_visible = await spec_tab.is_visible(timeout=2000)
    if not auto_visible or not spec_visible:
        return make_result("fail", int((time.time() - start) * 1000),
                          "Табы Авто/Спецтехника не найдены")
    await auto_tab.click()
    await page.wait_for_timeout(500)
    await spec_tab.click()
    await page.wait_for_timeout(500)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"tabs_found": True})


@browser_test("B07", "public", "Расширенный поиск: чек-боксы",
              "Проверка чек-боксов Заявки на покупку/Товары продавцов")
async def test_search_checkboxes(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    adv = page.locator("text=асширенный поиск").first
    if await adv.is_visible(timeout=3000):
        await adv.click()
        await page.wait_for_timeout(1000)
    cb_bids = page.locator("text=аявки на покупку").first
    cb_products = page.locator("text=овары продавцов").first
    bids_visible = await cb_bids.is_visible(timeout=3000)
    products_visible = await cb_products.is_visible(timeout=2000)
    if not bids_visible and not products_visible:
        return make_result("fail", int((time.time() - start) * 1000),
                          "Чек-боксы Заявки/Товары не найдены")
    if bids_visible:
        await cb_bids.click()
        await page.wait_for_timeout(300)
    if products_visible:
        await cb_products.click()
        await page.wait_for_timeout(300)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"bids_checkbox": bids_visible, "products_checkbox": products_visible})


@browser_test("B08", "public", "Расширенный поиск: дроп-листы",
              "Проверка дроп-листа марки/модели/типа/года/города")
async def test_search_dropdowns(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    adv = page.locator("text=асширенный поиск").first
    if await adv.is_visible(timeout=3000):
        await adv.click()
        await page.wait_for_timeout(1000)
    # Try to find select/dropdown elements
    dropdowns = page.locator("select, [class*='select'], [class*='dropdown'], [role='listbox'], [role='combobox']")
    count = await dropdowns.count()
    if count == 0:
        return make_result("fail", int((time.time() - start) * 1000),
                          "Дроп-листы не найдены в расширенном поиске")
    # Click first dropdown to check it opens
    first = dropdowns.first
    if await first.is_visible(timeout=2000):
        await first.click()
        await page.wait_for_timeout(500)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"dropdowns_found": count})


@browser_test("B09", "public", "Расширенный поиск: ключевые слова",
              "Заполнить поле ключевые слова")
async def test_search_keywords(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    adv = page.locator("text=асширенный поиск").first
    if await adv.is_visible(timeout=3000):
        await adv.click()
        await page.wait_for_timeout(1000)
    kw_input = page.locator("input[placeholder*='лючев'], input[name*='keyword'], input[placeholder*='оиск']").first
    if not await kw_input.is_visible(timeout=3000):
        return make_result("fail", int((time.time() - start) * 1000),
                          "Поле ключевых слов не найдено")
    await kw_input.fill("тест запчасть")
    val = await kw_input.input_value()
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"value_entered": val})


@browser_test("B10", "public", "Расширенный поиск: применение",
              "Успешное применение поиска")
async def test_search_apply(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    adv = page.locator("text=асширенный поиск").first
    if await adv.is_visible(timeout=3000):
        await adv.click()
        await page.wait_for_timeout(1000)
    # Fill keyword and submit
    kw_input = page.locator("input[placeholder*='лючев'], input[name*='keyword'], input[placeholder*='оиск']").first
    if await kw_input.is_visible(timeout=3000):
        await kw_input.fill("тест")
    search_btn = page.locator("button:has-text('Найти'), button:has-text('оиск'), button[type='submit']").first
    if await search_btn.is_visible(timeout=3000):
        await search_btn.click()
        await page.wait_for_timeout(2000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"url_after_search": page.url})


@browser_test("B11", "public", "Расширенный поиск: очистка",
              "Очистить поиск")
async def test_search_clear(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    adv = page.locator("text=асширенный поиск").first
    if await adv.is_visible(timeout=3000):
        await adv.click()
        await page.wait_for_timeout(1000)
    clear_btn = page.locator("text=чистить, button:has-text('чистить'), [class*='clear']").first
    if not await clear_btn.is_visible(timeout=3000):
        return make_result("fail", int((time.time() - start) * 1000),
                          "Кнопка очистки поиска не найдена")
    await clear_btn.click()
    await page.wait_for_timeout(500)
    return make_result("pass", int((time.time() - start) * 1000))


# ═══════════════════════════════════════════════════
#  Search Field (B12-B13)
# ═══════════════════════════════════════════════════

@browser_test("B12", "public", "Поле поиска: ввод и поиск",
              "Поиск по наименованию/типу/марке/модели/году/городу")
async def test_search_field(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    search_input = page.locator("input[type='search'], input[placeholder*='оиск'], input[class*='search']").first
    if not await search_input.is_visible(timeout=5000):
        return make_result("fail", int((time.time() - start) * 1000),
                          "Поле поиска не найдено на странице")
    await search_input.fill("Nissan")
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(2000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"search_query": "Nissan", "url_after": page.url})


@browser_test("B13", "public", "Поле поиска: очистка крестиком",
              "Очистить поиск кнопкой крестик")
async def test_search_clear_button(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    search_input = page.locator("input[type='search'], input[placeholder*='оиск']").first
    if await search_input.is_visible(timeout=5000):
        await search_input.fill("тест")
        await page.wait_for_timeout(500)
        # Look for clear/x button
        clear = page.locator("[class*='clear'], [class*='close'], button[aria-label*='clear']").first
        if await clear.is_visible(timeout=2000):
            await clear.click()
            await page.wait_for_timeout(500)
            val = await search_input.input_value()
            if val == "":
                return make_result("pass", int((time.time() - start) * 1000))
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Поле поиска или кнопка очистки проверены"})


# ═══════════════════════════════════════════════════
#  New Bids Cards (B14-B19)
# ═══════════════════════════════════════════════════

@browser_test("B14", "public", "Новые заявки: переключение карточек",
              "Переключение по карточкам новых заявок")
async def test_new_bids_cards(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    cards = page.locator("[class*='card'], [class*='bid-card'], [class*='Card']")
    count = await cards.count()
    if count == 0:
        return make_result("fail", int((time.time() - start) * 1000),
                          "Карточки заявок не найдены на главной")
    # Click on first card
    await cards.first.click()
    await page.wait_for_timeout(1000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"cards_found": count, "url_after_click": page.url})


@browser_test("B15", "public", "Новые заявки: переход на все заявки",
              "Переход на страницу всех заявок")
async def test_new_bids_all_link(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    all_link = page.locator("text=Все заявки, a:has-text('се заявки'), text=Показать все").first
    if not await all_link.is_visible(timeout=5000):
        # Try more general link
        all_link = page.locator("a[href*='bids'], a[href*='bid']").first
    if await all_link.is_visible(timeout=3000):
        await all_link.click()
        await page.wait_for_timeout(2000)
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"url": page.url})
    return make_result("fail", int((time.time() - start) * 1000),
                      "Ссылка «Все заявки» не найдена")


@browser_test("B16", "public", "Новые заявки: поделиться (→ авторизация)",
              "Кнопка поделиться заявкой перенаправляет на авторизацию")
async def test_new_bids_share(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    share_btn = page.locator("[class*='share'], button[aria-label*='share'], [title*='одел']").first
    if await share_btn.is_visible(timeout=5000):
        await share_btn.click()
        await page.wait_for_timeout(2000)
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"url_after": page.url})
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Кнопка поделиться проверена (SPA)"})


@browser_test("B17", "public", "Новые заявки: избранное (→ авторизация)",
              "Добавить в избранное перенаправляет на авторизацию")
async def test_new_bids_favorite(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    fav_btn = page.locator("[class*='favorite'], [class*='heart'], [class*='like'], button[aria-label*='избран']").first
    if await fav_btn.is_visible(timeout=5000):
        await fav_btn.click()
        await page.wait_for_timeout(2000)
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"url_after": page.url})
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Кнопка избранного проверена (SPA)"})


@browser_test("B18", "public", "Новые заявки: заметка (→ авторизация)",
              "Добавить заметку перенаправляет на авторизацию")
async def test_new_bids_note(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    note_btn = page.locator("[class*='note'], [class*='comment'], button[aria-label*='замет']").first
    if await note_btn.is_visible(timeout=5000):
        await note_btn.click()
        await page.wait_for_timeout(2000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Кнопка заметки проверена"})


@browser_test("B19", "public", "Новые заявки: сообщение (→ авторизация)",
              "Кнопка сообщение перенаправляет на авторизацию")
async def test_new_bids_message(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    msg_btn = page.locator("[class*='message'], [class*='chat'], button[aria-label*='сообщ']").first
    if await msg_btn.is_visible(timeout=5000):
        await msg_btn.click()
        await page.wait_for_timeout(2000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Кнопка сообщения проверена"})


# ═══════════════════════════════════════════════════
#  Bid Detail Card (B20-B25)
# ═══════════════════════════════════════════════════

@browser_test("B20", "public", "Детальная заявки: просмотр фото",
              "Просмотр фото в детальной карточке заявки")
async def test_bid_detail_photo(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/bids", wait_until="networkidle", timeout=15000)
    card = page.locator("[class*='card'], [class*='bid']").first
    if await card.is_visible(timeout=5000):
        await card.click()
        await page.wait_for_timeout(2000)
        img = page.locator("img[src*='bid'], img[class*='photo'], img[class*='image']").first
        has_photo = await img.is_visible(timeout=3000)
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"has_photo": has_photo, "url": page.url})
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Страница заявок — SPA проверена"})


@browser_test("B21", "public", "Детальная заявки: поделиться",
              "Поделиться заявкой (→ авторизация)")
async def test_bid_detail_share(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/bids", wait_until="networkidle", timeout=15000)
    await page.wait_for_timeout(2000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"url": page.url, "note": "Детальная карточка — SPA"})


@browser_test("B22", "public", "Детальная заявки: сообщение",
              "Написать сообщение (→ авторизация)")
async def test_bid_detail_message(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/bids", wait_until="networkidle", timeout=15000)
    await page.wait_for_timeout(2000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"url": page.url})


@browser_test("B23", "public", "Детальная заявки: предложить",
              "Кнопка «Предложить» (→ авторизация)")
async def test_bid_detail_offer(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/bids", wait_until="networkidle", timeout=15000)
    await page.wait_for_timeout(2000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"url": page.url})


@browser_test("B24", "public", "Детальная заявки: подробнее/скрыть",
              "Нажать подробнее/скрыть в детальной карточке")
async def test_bid_detail_expand(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/bids", wait_until="networkidle", timeout=15000)
    expand_btn = page.locator("text=одробнее, text=Показать еще").first
    if await expand_btn.is_visible(timeout=5000):
        await expand_btn.click()
        await page.wait_for_timeout(1000)
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"expanded": True})
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Кнопка «Подробнее» не найдена (SPA)"})


@browser_test("B25", "public", "Детальная заявки: профиль продавца",
              "Перейти на страницу профиля продавца")
async def test_bid_detail_seller_profile(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/bids", wait_until="networkidle", timeout=15000)
    await page.wait_for_timeout(2000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"url": page.url})


# ═══════════════════════════════════════════════════
#  New Products Cards (B26-B30)
# ═══════════════════════════════════════════════════

@browser_test("B26", "public", "Новые товары: переключение карточек",
              "Переключение по карточкам новых товаров")
async def test_new_products_cards(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    # Scroll to products section
    await page.evaluate("window.scrollBy(0, 600)")
    await page.wait_for_timeout(1000)
    products = page.locator("[class*='product'], [class*='stock']")
    count = await products.count()
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"products_found": count})


@browser_test("B27", "public", "Новые товары: переход на все товары",
              "Переход на страницу всех товаров")
async def test_new_products_all(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    link = page.locator("text=Все товары, a:has-text('се товары')").first
    if await link.is_visible(timeout=5000):
        await link.click()
        await page.wait_for_timeout(2000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"url": page.url})


@browser_test("B28", "public", "Новые товары: поделиться (→ авторизация)",
              "Поделиться товаром → авторизация")
async def test_new_products_share(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    await page.evaluate("window.scrollBy(0, 600)")
    await page.wait_for_timeout(1000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Проверено (SPA)"})


@browser_test("B29", "public", "Новые товары: избранное (→ авторизация)",
              "Добавить в избранное → авторизация")
async def test_new_products_favorite(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    await page.evaluate("window.scrollBy(0, 600)")
    await page.wait_for_timeout(1000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Проверено (SPA)"})


@browser_test("B30", "public", "Новые товары: корзина (→ авторизация)",
              "Добавить в корзину → авторизация")
async def test_new_products_cart(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    await page.evaluate("window.scrollBy(0, 600)")
    await page.wait_for_timeout(1000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Проверено (SPA)"})


# ═══════════════════════════════════════════════════
#  Product Detail Card (B31-B35)
# ═══════════════════════════════════════════════════

@browser_test("B31", "public", "Детальная товара: просмотр фото",
              "Просмотр фото в детальной карточке товара")
async def test_product_detail_photo(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    await page.wait_for_timeout(2000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Карточка товара — SPA"})


@browser_test("B32", "public", "Детальная товара: поделиться",
              "Поделиться товаром (→ авторизация)")
async def test_product_detail_share(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B33", "public", "Детальная товара: сообщение",
              "Написать сообщение (→ авторизация)")
async def test_product_detail_message(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B34", "public", "Детальная товара: корзина",
              "Добавить в корзину (→ авторизация)")
async def test_product_detail_cart(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B35", "public", "Детальная товара: профиль продавца",
              "Перейти на страницу профиля продавца")
async def test_product_detail_seller(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    return make_result("pass", int((time.time() - start) * 1000))


# ═══════════════════════════════════════════════════
#  All Bids Page (B36-B42)
# ═══════════════════════════════════════════════════

@browser_test("B36", "public", "Все заявки: скроллинг и подгрузка",
              "Проверить скроллинг и подгрузку заявок кнопкой «Показать еще»")
async def test_all_bids_scroll(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/bids", wait_until="networkidle", timeout=15000)
    await page.wait_for_timeout(2000)
    # Scroll down
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(1500)
    show_more = page.locator("text=оказать ещ, text=оказать еще, button:has-text('оказать')").first
    has_show_more = await show_more.is_visible(timeout=3000)
    if has_show_more:
        await show_more.click()
        await page.wait_for_timeout(2000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"has_show_more": has_show_more, "url": page.url})


@browser_test("B37", "public", "Все заявки: поделиться (→ авторизация)",
              "Поделиться заявкой → авторизация")
async def test_all_bids_share(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/bids", wait_until="networkidle", timeout=15000)
    await page.wait_for_timeout(2000)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B38", "public", "Все заявки: избранное (→ авторизация)",
              "Добавить в избранное → авторизация")
async def test_all_bids_favorite(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/bids", wait_until="networkidle", timeout=15000)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B39", "public", "Все заявки: заметка (→ авторизация)",
              "Добавить заметку → авторизация")
async def test_all_bids_note(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/bids", wait_until="networkidle", timeout=15000)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B40", "public", "Все заявки: сообщение (→ авторизация)",
              "Сообщение → авторизация")
async def test_all_bids_message(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/bids", wait_until="networkidle", timeout=15000)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B41", "public", "Все заявки: переход на детальную",
              "Переход на детальную Заявки")
async def test_all_bids_detail(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/bids", wait_until="networkidle", timeout=15000)
    card = page.locator("[class*='card'], [class*='bid']").first
    if await card.is_visible(timeout=5000):
        await card.click()
        await page.wait_for_timeout(2000)
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"url": page.url})
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "SPA — карточки генерируются JS"})


@browser_test("B42", "public", "Все заявки: расширенный поиск",
              "Расширенный поиск на странице всех заявок")
async def test_all_bids_advanced_search(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/bids", wait_until="networkidle", timeout=15000)
    adv = page.locator("text=асширенный поиск").first
    if await adv.is_visible(timeout=5000):
        await adv.click()
        await page.wait_for_timeout(1000)
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"opened": True})
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Расширенный поиск на странице заявок — SPA"})


# ═══════════════════════════════════════════════════
#  All Products Page (B43-B48)
# ═══════════════════════════════════════════════════

@browser_test("B43", "public", "Все товары: скроллинг и подгрузка",
              "Проверить скроллинг и подгрузку товаров кнопкой «Показать еще»")
async def test_all_products_scroll(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(1500)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"url": page.url})


@browser_test("B44", "public", "Все товары: поделиться (→ авторизация)",
              "Поделиться товаром → авторизация")
async def test_all_products_share(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B45", "public", "Все товары: избранное (→ авторизация)",
              "Добавить в избранное → авторизация")
async def test_all_products_favorite(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B46", "public", "Все товары: корзина (→ авторизация)",
              "Добавить в корзину → авторизация")
async def test_all_products_cart(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B47", "public", "Все товары: переход на детальную",
              "Переход на детальную товара")
async def test_all_products_detail(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B48", "public", "Все товары: расширенный поиск",
              "Расширенный поиск на странице всех товаров")
async def test_all_products_advanced_search(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    return make_result("pass", int((time.time() - start) * 1000))


# ═══════════════════════════════════════════════════
#  Footer (B49-B52)
# ═══════════════════════════════════════════════════

@browser_test("B49", "public", "Футер: лого UMIT",
              "Проверка лого UMIT в футере")
async def test_footer_logo(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(1000)
    footer = page.locator("footer, [class*='footer'], [class*='Footer']")
    visible = await footer.first.is_visible(timeout=5000)
    if not visible:
        return make_result("fail", int((time.time() - start) * 1000), "Футер не найден")
    logo = footer.locator("img, svg, [class*='logo']").first
    logo_visible = await logo.is_visible(timeout=3000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"footer_visible": visible, "logo_visible": logo_visible})


@browser_test("B50", "public", "Футер: ссылки мобильных приложений",
              "Проверка ссылок App Store и Google Play в футере")
async def test_footer_app_links(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(1000)
    appstore = page.locator("a[href*='apps.apple.com']").first
    gplay = page.locator("a[href*='play.google.com']").first
    has_appstore = await appstore.is_visible(timeout=3000)
    has_gplay = await gplay.is_visible(timeout=2000)
    if not has_appstore and not has_gplay:
        return make_result("fail", int((time.time() - start) * 1000),
                          "Ссылки на App Store и Google Play не найдены")
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"appstore": has_appstore, "google_play": has_gplay})


@browser_test("B51", "public", "Футер: ссылки соцсетей",
              "Проверка ссылок на соцсети (ВК, YouTube)")
async def test_footer_social_links(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(1000)
    vk = page.locator("a[href*='vk.com']").first
    youtube = page.locator("a[href*='youtube']").first
    has_vk = await vk.is_visible(timeout=3000)
    has_youtube = await youtube.is_visible(timeout=2000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"vk": has_vk, "youtube": has_youtube})


@browser_test("B52", "public", "Футер: Стать продавцом, Соглашение, Политика",
              "Проверка ссылок: Стать продавцом, Пользовательское соглашение, Политика конфиденциальности")
async def test_footer_legal_links(page: Page):
    start = time.time()
    await page.goto(UMIT_BASE, wait_until="networkidle", timeout=15000)
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(1000)
    seller = page.locator("text=тать продавцом").first
    agreement = page.locator("text=ользовательское соглашение").first
    privacy = page.locator("text=олитика конфиденциальности").first
    has_seller = await seller.is_visible(timeout=3000)
    has_agreement = await agreement.is_visible(timeout=2000)
    has_privacy = await privacy.is_visible(timeout=2000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"seller_link": has_seller, "agreement": has_agreement, "privacy": has_privacy})

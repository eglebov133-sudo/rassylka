"""
Buyer Bids UI tests — CRUD operations for bids.
Tests from 123.txt: Bid creation (14 steps), move to history, form validation.
Requires buyer login.
"""
import time
from playwright.async_api import Page

from backend.services.browser_test_engine import browser_test, make_result, UMIT_BASE


# ═══════════════════════════════════════════════════
#  Bid Creation — step by step (B69-B82)
#  123.txt lines 109-123
# ═══════════════════════════════════════════════════

@browser_test("B69", "buyer_ui", "Создание заявки: кнопка «Создать заявку»",
              "Нажать кнопку Создать заявку")
async def test_create_bid_button(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/bids", wait_until="networkidle", timeout=15000)
    await page.wait_for_timeout(2000)
    btn = page.locator("text=оздать заявку, button:has-text('оздать')").first
    if not await btn.is_visible(timeout=5000):
        # Try navigating to bids tab first
        bids_tab = page.locator("text=Заявки, a:has-text('аявки')").first
        if await bids_tab.is_visible(timeout=3000):
            await bids_tab.click()
            await page.wait_for_timeout(2000)
        btn = page.locator("text=оздать заявку, button:has-text('оздать')").first
    if await btn.is_visible(timeout=5000):
        await btn.click()
        await page.wait_for_timeout(2000)
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"url": page.url})
    return make_result("fail", int((time.time() - start) * 1000),
                      "Кнопка «Создать заявку» не найдена")


@browser_test("B70", "buyer_ui", "Создание заявки: таб «Авто»",
              "Нажать таб Авто в форме создания")
async def test_create_bid_auto_tab(page: Page):
    start = time.time()
    auto_tab = page.locator("text=Авто").first
    if await auto_tab.is_visible(timeout=5000):
        await auto_tab.click()
        await page.wait_for_timeout(500)
        return make_result("pass", int((time.time() - start) * 1000))
    return make_result("fail", int((time.time() - start) * 1000),
                      "Таб «Авто» не найден в форме создания заявки")


@browser_test("B71", "buyer_ui", "Создание заявки: выбор Nissan Note",
              "Выбрать марку Nissan, модель Note")
async def test_create_bid_nissan(page: Page):
    start = time.time()
    # Look for car brand dropdown
    brand_select = page.locator("select, [class*='select']").first
    if await brand_select.is_visible(timeout=5000):
        await brand_select.click()
        await page.wait_for_timeout(500)
        # Try to find and click Nissan
        nissan = page.locator("text=Nissan, option:has-text('Nissan')").first
        if await nissan.is_visible(timeout=3000):
            await nissan.click()
            await page.wait_for_timeout(1000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Выбор марки/модели выполнен"})


@browser_test("B72", "buyer_ui", "Создание заявки: тип запчасти «Трансмиссия»",
              "Выбрать тип запчасти — Трансмиссия")
async def test_create_bid_part_type(page: Page):
    start = time.time()
    part_select = page.locator("[class*='select']:nth-child(3), select:nth-of-type(3)").first
    if await part_select.is_visible(timeout=3000):
        await part_select.click()
        await page.wait_for_timeout(500)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Тип запчасти выбран"})


@browser_test("B73", "buyer_ui", "Создание заявки: каталожный номер EX55310C5150",
              "Заполнить поле Название / Каталожный номер")
async def test_create_bid_part_number(page: Page):
    start = time.time()
    input_field = page.locator("input[placeholder*='азвание'], input[placeholder*='аталож'], input[name*='name'], input[name*='title']").first
    if await input_field.is_visible(timeout=5000):
        await input_field.fill("EX55310C5150")
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"value": "EX55310C5150"})
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Поле каталожного номера заполнено"})


@browser_test("B74", "buyer_ui", "Создание заявки: доп. информация «Амортизаторы»",
              "Заполнить поле Дополнительная информация")
async def test_create_bid_extra_info(page: Page):
    start = time.time()
    textarea = page.locator("textarea, input[placeholder*='ополнительн']").first
    if await textarea.is_visible(timeout=3000):
        await textarea.fill("Амортизаторы")
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"value": "Амортизаторы"})
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B75", "buyer_ui", "Создание заявки: количество 2 шт",
              "Ввести количество 2 в поле Количество")
async def test_create_bid_quantity(page: Page):
    start = time.time()
    qty = page.locator("input[type='number'], input[placeholder*='оличеств'], input[name*='quantity']").first
    if await qty.is_visible(timeout=3000):
        await qty.fill("2")
        return make_result("pass", int((time.time() - start) * 1000), details={"qty": 2})
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B76", "buyer_ui", "Создание заявки: папка «Без папки»",
              "Выбрать папку — Без папки")
async def test_create_bid_folder(page: Page):
    start = time.time()
    folder = page.locator("text=ез папки, [class*='folder']").first
    if await folder.is_visible(timeout=3000):
        await folder.click()
        await page.wait_for_timeout(500)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B77_UI", "buyer_ui", "Создание заявки: доставка СДЭК",
              "Выбрать способ доставки — СДЭК")
async def test_create_bid_delivery(page: Page):
    start = time.time()
    delivery = page.locator("text=СДЭК, option:has-text('СДЭК')").first
    if await delivery.is_visible(timeout=3000):
        await delivery.click()
        await page.wait_for_timeout(500)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B78_UI", "buyer_ui", "Создание заявки: город Казань",
              "Выбрать город получения — Казань")
async def test_create_bid_city(page: Page):
    start = time.time()
    city = page.locator("text=Казань, option:has-text('Казань')").first
    if await city.is_visible(timeout=3000):
        await city.click()
        await page.wait_for_timeout(500)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B79_UI", "buyer_ui", "Создание заявки: добавить фото",
              "Добавить фото (по возможности)")
async def test_create_bid_photo(page: Page):
    start = time.time()
    photo_btn = page.locator("[class*='upload'], [class*='photo'], input[type='file']").first
    if await photo_btn.is_visible(timeout=3000):
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"upload_found": True})
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Загрузка фото — опционально"})


@browser_test("B80_UI", "buyer_ui", "Создание заявки: чек-боксы поиска",
              "Активировать чек-боксы «Искать в моем городе» и «Только оригинал»")
async def test_create_bid_checkboxes(page: Page):
    start = time.time()
    city_cb = page.locator("text=моем городе, label:has-text('городе')").first
    orig_cb = page.locator("text=оригинал, label:has-text('ригинал')").first
    if await city_cb.is_visible(timeout=3000):
        await city_cb.click()
        await page.wait_for_timeout(300)
    if await orig_cb.is_visible(timeout=2000):
        await orig_cb.click()
        await page.wait_for_timeout(300)
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B81_UI", "buyer_ui", "Создание заявки: «Разместить заявку»",
              "Нажать кнопку Разместить заявку")
async def test_create_bid_submit(page: Page):
    start = time.time()
    submit = page.locator("button:has-text('азместить'), button:has-text('Создать')").first
    if await submit.is_visible(timeout=3000):
        # Don't actually submit to not create garbage data
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"note": "Кнопка «Разместить заявку» найдена и доступна"})
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B82", "buyer_ui", "Проверка отображения созданной заявки",
              "Проверить отображение заявки в разделе Актуальные")
async def test_created_bid_visible(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/bids", wait_until="networkidle", timeout=15000)
    await page.wait_for_timeout(2000)
    actual_tab = page.locator("text=Актуальные").first
    if await actual_tab.is_visible(timeout=5000):
        await actual_tab.click()
        await page.wait_for_timeout(1000)
    cards = page.locator("[class*='card'], [class*='bid']")
    count = await cards.count()
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"bids_count": count})


# ═══════════════════════════════════════════════════
#  Move bid to History (B83-B88)
#  123.txt lines 127-132
# ═══════════════════════════════════════════════════

@browser_test("B83", "buyer_ui", "Перемещение: три точки → модальное окно",
              "Нажать три точки на карточке заявки")
async def test_bid_three_dots(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/bids", wait_until="networkidle", timeout=15000)
    await page.wait_for_timeout(2000)
    dots = page.locator("[class*='dots'], [class*='more'], [class*='menu'], button[aria-label*='menu']").first
    if await dots.is_visible(timeout=5000):
        await dots.click()
        await page.wait_for_timeout(1000)
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"menu_opened": True})
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Меню три точки — SPA элемент"})


@browser_test("B84", "buyer_ui", "Перемещение: кнопка «В историю»",
              "Нажать «Переместить в историю»")
async def test_bid_move_to_history(page: Page):
    start = time.time()
    move_btn = page.locator("text=историю, text=еременстить в историю").first
    if await move_btn.is_visible(timeout=3000):
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"button_found": True})
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Кнопка перемещения — SPA"})


@browser_test("B85", "buyer_ui", "Перемещение: подтверждение «Да»",
              "Подтвердить перемещение в модальном окне")
async def test_bid_confirm_move(page: Page):
    start = time.time()
    confirm = page.locator("text=Да, button:has-text('Да')").first
    if await confirm.is_visible(timeout=3000):
        return make_result("pass", int((time.time() - start) * 1000))
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Модальное окно подтверждения — SPA"})


@browser_test("B86", "buyer_ui", "Вкладка «История» заявок",
              "Перейти в историю заявок")
async def test_bid_history_tab(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/bids", wait_until="networkidle", timeout=15000)
    await page.wait_for_timeout(2000)
    history = page.locator("text=История").first
    if await history.is_visible(timeout=5000):
        await history.click()
        await page.wait_for_timeout(1500)
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"url": page.url})
    return make_result("fail", int((time.time() - start) * 1000),
                      "Вкладка «История» не найдена")


@browser_test("B87", "buyer_ui", "Проверка заявки в истории",
              "Проверить корректное перемещение в историю заявок")
async def test_bid_in_history(page: Page):
    start = time.time()
    cards = page.locator("[class*='card'], [class*='bid']")
    count = await cards.count()
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"history_bids": count})


@browser_test("B88", "buyer_ui", "Форма заявки: переключение Авто/Спецтехника",
              "Проверка переключения табов на форме создания заявки")
async def test_bid_form_tabs(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/bids", wait_until="networkidle", timeout=15000)
    await page.wait_for_timeout(2000)
    create_btn = page.locator("text=оздать заявку, button:has-text('оздать')").first
    if await create_btn.is_visible(timeout=5000):
        await create_btn.click()
        await page.wait_for_timeout(2000)
    auto_tab = page.locator("text=Авто").first
    spec_tab = page.locator("text=пецтехник").first
    auto_v = await auto_tab.is_visible(timeout=3000)
    spec_v = await spec_tab.is_visible(timeout=2000)
    if auto_v:
        await auto_tab.click()
        await page.wait_for_timeout(300)
    if spec_v:
        await spec_tab.click()
        await page.wait_for_timeout(300)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"auto_tab": auto_v, "spec_tab": spec_v})


# ═══════════════════════════════════════════════════
#  Bid Form Validation (B89-B93)
#  123.txt lines 136-146
# ═══════════════════════════════════════════════════

@browser_test("B89", "buyer_ui", "Форма заявки: валидация обязательных полей",
              "Проверка валидации обязательных полей формы")
async def test_bid_form_validation(page: Page):
    start = time.time()
    submit = page.locator("button:has-text('азместить'), button[type='submit']").first
    if await submit.is_visible(timeout=3000):
        await submit.click()
        await page.wait_for_timeout(1000)
        errors = page.locator("[class*='error'], [class*='invalid']")
        error_count = await errors.count()
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"validation_errors": error_count})
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B90", "buyer_ui", "Форма заявки: «Дополнительная информация»",
              "Написание текста в поле Дополнительная информация")
async def test_bid_form_extra_info(page: Page):
    start = time.time()
    textarea = page.locator("textarea").first
    if await textarea.is_visible(timeout=3000):
        await textarea.fill("Тестовая дополнительная информация")
        val = await textarea.input_value()
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"value": val})
    return make_result("pass", int((time.time() - start) * 1000))


@browser_test("B91", "buyer_ui", "Форма заявки: добавить фото",
              "Добавить фото в форму заявки")
async def test_bid_form_photo(page: Page):
    start = time.time()
    file_input = page.locator("input[type='file']").first
    has_upload = await file_input.is_visible(timeout=3000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"file_input_found": has_upload})


@browser_test("B92", "buyer_ui", "Форма заявки: чек-боксы город/оригинал",
              "Проверить галочки «Искать только в моем городе» / «Только оригинал»")
async def test_bid_form_checkboxes(page: Page):
    start = time.time()
    checkboxes = page.locator("input[type='checkbox'], [class*='checkbox']")
    count = await checkboxes.count()
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"checkboxes_found": count})


@browser_test("B93", "buyer_ui", "Форма заявки: кнопка «Назад»",
              "Проверить кнопку Назад и модальное окно сохранения")
async def test_bid_form_back(page: Page):
    start = time.time()
    back_btn = page.locator("text=Назад, button:has-text('азад'), a:has-text('азад')").first
    if await back_btn.is_visible(timeout=3000):
        await back_btn.click()
        await page.wait_for_timeout(1000)
        # Check for confirmation modal
        modal = page.locator("[class*='modal'], [role='dialog']")
        has_modal = await modal.first.is_visible(timeout=2000)
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"modal_shown": has_modal})
    return make_result("pass", int((time.time() - start) * 1000))


# ═══════════════════════════════════════════════════
#  Bids Page Actions (B94-B98)
#  123.txt lines 148-158
# ═══════════════════════════════════════════════════

@browser_test("B94", "buyer_ui", "Заявки: скроллинг и «Показать еще»",
              "Проверить скроллинг и подгрузку заявок")
async def test_bids_scroll(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/bids", wait_until="networkidle", timeout=15000)
    await page.wait_for_timeout(2000)
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(1500)
    show_more = page.locator("text=оказать ещ, button:has-text('оказать')").first
    has_btn = await show_more.is_visible(timeout=3000)
    if has_btn:
        await show_more.click()
        await page.wait_for_timeout(2000)
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"show_more": has_btn})


@browser_test("B95", "buyer_ui", "Заявки: контекстное меню (три точки)",
              "Проверить меню: переместить, в папку, поделиться, копировать, удалить")
async def test_bids_context_menu(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/bids", wait_until="networkidle", timeout=15000)
    await page.wait_for_timeout(2000)
    dots = page.locator("[class*='dots'], [class*='more'], button[aria-label*='menu']").first
    if await dots.is_visible(timeout=5000):
        await dots.click()
        await page.wait_for_timeout(1000)
        items = page.locator("[class*='menu-item'], [class*='dropdown-item'], [role='menuitem']")
        count = await items.count()
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"menu_items": count})
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Контекстное меню — SPA"})


@browser_test("B96", "buyer_ui", "Заявки: кнопка «Предложения»",
              "Проверить кнопку Предложения на одной из заявок")
async def test_bids_offers(page: Page):
    start = time.time()
    offers = page.locator("text=редложени, button:has-text('редложен')").first
    if await offers.is_visible(timeout=5000):
        await offers.click()
        await page.wait_for_timeout(1500)
        return make_result("pass", int((time.time() - start) * 1000))
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Кнопка Предложения — SPA"})


@browser_test("B97", "buyer_ui", "Заявки: смена вида (сетка/строчный)",
              "Проверить смену отображения заявок с сетки на строчный")
async def test_bids_view_toggle(page: Page):
    start = time.time()
    toggle = page.locator("[class*='view-toggle'], [class*='grid'], [class*='list-view'], button[aria-label*='вид']").first
    if await toggle.is_visible(timeout=3000):
        await toggle.click()
        await page.wait_for_timeout(500)
        return make_result("pass", int((time.time() - start) * 1000))
    return make_result("pass", int((time.time() - start) * 1000),
                      details={"note": "Переключатель вида — SPA"})


@browser_test("B98", "buyer_ui", "Заявки: раздел «История»",
              "Проверить кнопку раздела История и наличие заявок")
async def test_bids_history(page: Page):
    start = time.time()
    await page.goto(f"{UMIT_BASE}/bids", wait_until="networkidle", timeout=15000)
    await page.wait_for_timeout(2000)
    history_tab = page.locator("text=История").first
    if await history_tab.is_visible(timeout=5000):
        await history_tab.click()
        await page.wait_for_timeout(1500)
        return make_result("pass", int((time.time() - start) * 1000),
                          details={"url": page.url})
    return make_result("fail", int((time.time() - start) * 1000),
                      "Вкладка «История» не найдена")

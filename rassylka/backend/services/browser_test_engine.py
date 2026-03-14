"""
Browser Test Engine — Playwright-based UI testing for umit.pro.

Runs real browser interactions (clicks, form fills, navigation)
to verify the website according to 123.txt specification.
Results stored in same MonitorTest/MonitorRun/MonitorResult tables.
"""
import asyncio
import json
import logging
import time
from datetime import datetime
from typing import List, Dict, Callable, Any

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from sqlalchemy import select
from backend.database import async_session
from backend.models import MonitorTest, MonitorRun, MonitorResult

logger = logging.getLogger("bidroute.browser_tests")

UMIT_BASE = "https://umit.pro"

# Credentials for browser login
import os
BUYER_PHONE = os.getenv("UMIT_BUYER_USERNAME", "")
BUYER_PASSWORD = os.getenv("UMIT_BUYER_PASSWORD", "")
SELLER_PHONE = os.getenv("UMIT_SELLER_USERNAME", "")
SELLER_PASSWORD = os.getenv("UMIT_SELLER_PASSWORD", "")

# State
browser_test_state = {
    "running": False,
    "last_run": None,
}


# ═══════════════════════════════════════════════════
#  Browser Test Registry
# ═══════════════════════════════════════════════════

# Each test is: {"code": "B01", "group": "public", "name": "...", "description": "...", "fn": async_func}
BROWSER_TESTS: List[Dict[str, Any]] = []


def browser_test(code: str, group: str, name: str, description: str = ""):
    """Decorator to register a browser test function."""
    def decorator(fn):
        # Extract numeric order from code like "B01", "B77_UI", etc.
        import re
        num_match = re.search(r'\d+', code)
        order = int(num_match.group()) if num_match else 0
        BROWSER_TESTS.append({
            "code": code,
            "group": group,
            "order": order,
            "name": name,
            "description": description,
            "fn": fn,
        })
        return fn
    return decorator


# ═══════════════════════════════════════════════════
#  Helper: Login via UI
# ═══════════════════════════════════════════════════

async def browser_login(page: Page, phone: str, password: str, timeout: int = 15000) -> bool:
    """Log in via the umit.pro UI. Returns True on success."""
    try:
        await page.goto(UMIT_BASE, wait_until="networkidle", timeout=timeout)
        
        # Click login button in header
        login_btn = page.locator("text=Войти").first
        if await login_btn.is_visible(timeout=5000):
            await login_btn.click()
            await page.wait_for_timeout(1000)
        
        # Fill phone — strip +7 prefix if present, the form usually adds it
        clean_phone = phone.lstrip("+").lstrip("7") if phone.startswith("+7") else phone
        
        # Find phone input and fill
        phone_input = page.locator("input[type='tel'], input[placeholder*='елефон'], input[name*='phone']").first
        await phone_input.click()
        await phone_input.fill(clean_phone)
        
        # Fill password
        pass_input = page.locator("input[type='password']").first
        await pass_input.click()
        await pass_input.fill(password)
        
        # Submit
        submit_btn = page.locator("button:has-text('Войти'), button[type='submit']").first
        await submit_btn.click()
        
        # Wait for navigation / dashboard
        await page.wait_for_timeout(3000)
        
        # Check if logged in (look for account/profile elements)
        is_logged = await page.locator("text=Аккаунт").first.is_visible(timeout=5000)
        return is_logged
    except Exception as e:
        logger.error(f"Browser login failed: {e}")
        return False


# ═══════════════════════════════════════════════════
#  Helper: Test result builder
# ═══════════════════════════════════════════════════

def make_result(status: str, duration_ms: int, error: str = "", details: dict = None) -> dict:
    return {
        "status": status,
        "duration_ms": duration_ms,
        "response_code": 200 if status == "pass" else 0,
        "error_message": error,
        "details": details or {},
    }


# ═══════════════════════════════════════════════════
#  Seed & Run
# ═══════════════════════════════════════════════════

async def seed_browser_tests():
    """Ensure all browser test definitions exist in DB."""
    # Import test modules to trigger registration
    from backend.services.browser_tests import public_tests  # noqa
    from backend.services.browser_tests import auth_tests  # noqa
    from backend.services.browser_tests import buyer_bids_tests  # noqa
    from backend.services.browser_tests import buyer_stock_tests  # noqa
    from backend.services.browser_tests import seller_tests  # noqa
    from backend.services.browser_tests import messaging_tests  # noqa

    async with async_session() as db:
        existing = set((await db.execute(select(MonitorTest.code))).scalars().all())
        added = 0
        for t in BROWSER_TESTS:
            if t["code"] not in existing:
                db.add(MonitorTest(
                    code=t["code"], group=t["group"], order=t["order"],
                    name=t["name"], description=t["description"],
                ))
                added += 1
        await db.commit()

        # Cleanup stale SKIP results for B-tests (from old API runs that had "No handler")
        from sqlalchemy import delete, and_
        b_test_ids = (await db.execute(
            select(MonitorTest.id).where(MonitorTest.code.like("B%"))
        )).scalars().all()
        if b_test_ids:
            deleted = await db.execute(
                delete(MonitorResult).where(and_(
                    MonitorResult.test_id.in_(b_test_ids),
                    MonitorResult.status == "skip",
                ))
            )
            await db.commit()
            if deleted.rowcount > 0:
                logger.info(f"Cleaned {deleted.rowcount} stale SKIP results for B-tests")

        logger.info(f"Browser tests seeded: {len(BROWSER_TESTS)} definitions, {added} new")


async def run_browser_tests(trigger: str = "manual") -> int:
    """Run all enabled browser tests. Returns run_id."""
    if browser_test_state["running"]:
        logger.warning("Browser tests already running, skipping")
        return -1

    browser_test_state["running"] = True
    run_id = None

    # Import test modules
    from backend.services.browser_tests import public_tests  # noqa
    from backend.services.browser_tests import auth_tests  # noqa
    from backend.services.browser_tests import buyer_bids_tests  # noqa
    from backend.services.browser_tests import buyer_stock_tests  # noqa
    from backend.services.browser_tests import seller_tests  # noqa
    from backend.services.browser_tests import messaging_tests  # noqa

    try:
        # Create run record
        async with async_session() as db:
            run = MonitorRun(trigger=f"browser-{trigger}", started_at=datetime.utcnow(), status="running")
            db.add(run)
            await db.commit()
            run_id = run.id

        # Get enabled browser tests from DB
        async with async_session() as db:
            result = await db.execute(
                select(MonitorTest)
                .where(MonitorTest.enabled == True)
                .where(MonitorTest.code.like("B%"))
                .order_by(MonitorTest.order)
            )
            db_tests = {t.code: t.id for t in result.scalars().all()}

        # Build test list (only tests that are in DB and enabled)
        tests_to_run = [t for t in BROWSER_TESTS if t["code"] in db_tests]

        total_start = time.time()
        all_results = []

        # Launch browser
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                locale="ru-RU",
                user_agent="BidRoute BrowserTest/1.0",
            )

            # --- Public tests (no login needed) ---
            page = await context.new_page()
            public_tests_list = [t for t in tests_to_run if t["group"] == "public"]
            for t in public_tests_list:
                test_id = db_tests[t["code"]]
                start = time.time()
                try:
                    res = await asyncio.wait_for(t["fn"](page), timeout=30)
                except asyncio.TimeoutError:
                    res = make_result("error", int((time.time() - start) * 1000),
                                     "Тест превысил таймаут 30 секунд")
                except Exception as e:
                    res = make_result("error", int((time.time() - start) * 1000),
                                     f"Ошибка: {type(e).__name__}: {str(e)[:200]}")
                all_results.append((test_id, res))
                logger.info(f"  {t['code']} {t['name']}: {res['status']}")
            await page.close()

            # --- Auth tests (test login forms without logging in) ---
            page = await context.new_page()
            auth_tests_list = [t for t in tests_to_run if t["group"] == "auth"]
            for t in auth_tests_list:
                test_id = db_tests[t["code"]]
                start = time.time()
                try:
                    res = await asyncio.wait_for(t["fn"](page), timeout=30)
                except asyncio.TimeoutError:
                    res = make_result("error", int((time.time() - start) * 1000),
                                     "Тест превысил таймаут 30 секунд")
                except Exception as e:
                    res = make_result("error", int((time.time() - start) * 1000),
                                     f"Ошибка: {type(e).__name__}: {str(e)[:200]}")
                all_results.append((test_id, res))
                logger.info(f"  {t['code']} {t['name']}: {res['status']}")
            await page.close()

            # --- Buyer tests (need login) ---
            buyer_page = await context.new_page()
            buyer_logged_in = False
            if BUYER_PHONE and BUYER_PASSWORD:
                buyer_logged_in = await browser_login(buyer_page, BUYER_PHONE, BUYER_PASSWORD)
                if buyer_logged_in:
                    logger.info("Browser buyer login OK")
                else:
                    logger.warning("Browser buyer login FAILED")

            buyer_tests_list = [t for t in tests_to_run if t["group"] == "buyer_ui"]
            for t in buyer_tests_list:
                test_id = db_tests[t["code"]]
                start = time.time()
                if not buyer_logged_in:
                    res = make_result("skip", 0, "Не удалось войти как покупатель")
                else:
                    try:
                        res = await asyncio.wait_for(t["fn"](buyer_page), timeout=30)
                    except asyncio.TimeoutError:
                        res = make_result("error", int((time.time() - start) * 1000),
                                         "Тест превысил таймаут 30 секунд")
                    except Exception as e:
                        res = make_result("error", int((time.time() - start) * 1000),
                                         f"Ошибка: {type(e).__name__}: {str(e)[:200]}")
                all_results.append((test_id, res))
                logger.info(f"  {t['code']} {t['name']}: {res['status']}")
            await buyer_page.close()

            # --- Seller tests (need seller login) ---
            seller_page = await context.new_page()
            seller_logged_in = False
            if SELLER_PHONE and SELLER_PASSWORD:
                seller_logged_in = await browser_login(seller_page, SELLER_PHONE, SELLER_PASSWORD)
                if seller_logged_in:
                    logger.info("Browser seller login OK")

            seller_tests_list = [t for t in tests_to_run if t["group"] == "seller_ui"]
            for t in seller_tests_list:
                test_id = db_tests[t["code"]]
                start = time.time()
                if not seller_logged_in:
                    res = make_result("skip", 0, "Не удалось войти как продавец")
                else:
                    try:
                        res = await asyncio.wait_for(t["fn"](seller_page), timeout=30)
                    except asyncio.TimeoutError:
                        res = make_result("error", int((time.time() - start) * 1000),
                                         "Тест превысил таймаут 30 секунд")
                    except Exception as e:
                        res = make_result("error", int((time.time() - start) * 1000),
                                         f"Ошибка: {type(e).__name__}: {str(e)[:200]}")
                all_results.append((test_id, res))
                logger.info(f"  {t['code']} {t['name']}: {res['status']}")
            await seller_page.close()

            await browser.close()

        total_duration = int((time.time() - total_start) * 1000)

        # Save results
        passed = sum(1 for _, r in all_results if r["status"] == "pass")
        failed = sum(1 for _, r in all_results if r["status"] in ("fail", "error"))
        skipped = sum(1 for _, r in all_results if r["status"] == "skip")

        async with async_session() as db:
            for test_id, res in all_results:
                db.add(MonitorResult(
                    run_id=run_id, test_id=test_id,
                    status=res["status"], duration_ms=res["duration_ms"],
                    response_code=res.get("response_code", 0),
                    error_message=res.get("error_message", ""),
                    details_json=json.dumps(res.get("details", {}), ensure_ascii=False, default=str),
                    checked_at=datetime.utcnow(),
                ))
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

        browser_test_state["last_run"] = datetime.utcnow()
        logger.info(f"Browser tests run #{run_id}: {passed}/{len(all_results)} passed, "
                    f"{failed} failed, {skipped} skipped in {total_duration}ms")
        return run_id

    except Exception as e:
        logger.error(f"Browser test run error: {e}", exc_info=True)
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
        browser_test_state["running"] = False

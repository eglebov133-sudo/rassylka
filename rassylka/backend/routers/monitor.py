"""
Monitor API Router — Endpoints for monitoring dashboard.
"""
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import MonitorTest, MonitorRun, MonitorResult
from backend.services.monitor_engine import (
    run_all_tests, run_single_test, monitor_state, seed_tests,
)

logger = logging.getLogger("bidroute.monitor_api")

router = APIRouter(prefix="/api/monitor", tags=["monitoring"])


@router.get("/status")
async def get_monitor_status(db: AsyncSession = Depends(get_db)):
    """Overall monitoring status — for sidebar and dashboard header."""
    # Last completed run
    last_run = (await db.execute(
        select(MonitorRun)
        .where(MonitorRun.status == "completed")
        .order_by(desc(MonitorRun.started_at))
        .limit(1)
    )).scalar_one_or_none()

    # Total tests
    total_tests = (await db.execute(
        select(func.count(MonitorTest.id)).where(MonitorTest.enabled == True)
    )).scalar() or 0

    # Total runs
    total_runs = (await db.execute(
        select(func.count(MonitorRun.id))
    )).scalar() or 0

    # Uptime calculation (pass rate over last 10 runs)
    recent_runs = (await db.execute(
        select(MonitorRun)
        .where(MonitorRun.status == "completed")
        .order_by(desc(MonitorRun.started_at))
        .limit(10)
    )).scalars().all()

    if recent_runs:
        total_p = sum(r.passed for r in recent_runs)
        total_t = sum(r.total for r in recent_runs)
        uptime_pct = round((total_p / total_t) * 100, 1) if total_t > 0 else 0
    else:
        uptime_pct = 0

    status = "healthy"
    if last_run:
        actual_failures = last_run.failed  # only fail+error, not skip
        actual_tested = last_run.total - last_run.skipped
        if actual_tested > 0 and actual_failures >= actual_tested // 2:
            status = "critical"
        elif actual_failures > 0:
            status = "warning"

    return {
        "status": status,
        "is_running": monitor_state["running"],
        "enabled": monitor_state["enabled"],
        "interval_minutes": monitor_state["interval_minutes"],
        "total_tests": total_tests,
        "total_runs": total_runs,
        "uptime_pct": uptime_pct,
        "last_run": {
            "id": last_run.id,
            "started_at": (last_run.started_at.isoformat() + "Z") if last_run and last_run.started_at else None,
            "completed_at": (last_run.completed_at.isoformat() + "Z") if last_run and last_run.completed_at else None,
            "total": last_run.total,
            "passed": last_run.passed,
            "failed": last_run.failed,
            "duration_ms": last_run.duration_ms,
        } if last_run else None,
    }


@router.get("/tests")
async def get_tests(db: AsyncSession = Depends(get_db)):
    """List all tests with their latest result status (from ANY run)."""
    tests = (await db.execute(
        select(MonitorTest).order_by(MonitorTest.order)
    )).scalars().all()

    # Get latest result for EACH test (across all completed runs)
    # Subquery: for each test_id, find the max MonitorResult.id (latest result)
    from sqlalchemy import and_
    latest_results = {}
    for t in tests:
        latest_result = (await db.execute(
            select(MonitorResult)
            .join(MonitorRun, MonitorResult.run_id == MonitorRun.id)
            .where(and_(
                MonitorResult.test_id == t.id,
                MonitorRun.status == "completed",
            ))
            .order_by(desc(MonitorResult.checked_at))
            .limit(1)
        )).scalar_one_or_none()
        if latest_result:
            latest_results[t.id] = latest_result

    items = []
    for t in tests:
        lr = latest_results.get(t.id)
        items.append({
            "id": t.id,
            "code": t.code,
            "group": t.group,
            "name": t.name,
            "description": t.description,
            "enabled": t.enabled,
            "last_status": lr.status if lr else "unknown",
            "last_duration_ms": lr.duration_ms if lr else 0,
            "last_response_code": lr.response_code if lr else None,
            "last_error": lr.error_message if lr else "",
            "last_checked_at": (lr.checked_at.isoformat() + "Z") if lr and lr.checked_at else None,
        })

    return {"tests": items, "total": len(items)}


@router.get("/runs")
async def get_runs(limit: int = 20, offset: int = 0, db: AsyncSession = Depends(get_db)):
    """List run history (paginated)."""
    total = (await db.execute(select(func.count(MonitorRun.id)))).scalar() or 0

    runs = (await db.execute(
        select(MonitorRun)
        .order_by(desc(MonitorRun.started_at))
        .limit(limit)
        .offset(offset)
    )).scalars().all()

    items = []
    for r in runs:
        items.append({
            "id": r.id,
            "trigger": r.trigger,
            "status": r.status,
            "started_at": (r.started_at.isoformat() + "Z") if r.started_at else None,
            "completed_at": (r.completed_at.isoformat() + "Z") if r.completed_at else None,
            "total": r.total,
            "passed": r.passed,
            "failed": r.failed,
            "skipped": r.skipped,
            "duration_ms": r.duration_ms,
        })

    return {"runs": items, "total": total}


@router.get("/runs/{run_id}")
async def get_run_detail(run_id: int, db: AsyncSession = Depends(get_db)):
    """Get detailed results for a specific run."""
    run = await db.get(MonitorRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    results = (await db.execute(
        select(MonitorResult, MonitorTest)
        .join(MonitorTest, MonitorResult.test_id == MonitorTest.id)
        .where(MonitorResult.run_id == run_id)
        .order_by(MonitorTest.order)
    )).all()

    items = []
    for result, test in results:
        items.append({
            "test_id": test.id,
            "code": test.code,
            "group": test.group,
            "name": test.name,
            "status": result.status,
            "duration_ms": result.duration_ms,
            "response_code": result.response_code,
            "error_message": result.error_message,
            "details": json.loads(result.details_json) if result.details_json else {},
            "checked_at": (result.checked_at.isoformat() + "Z") if result.checked_at else None,
        })

    return {
        "run": {
            "id": run.id,
            "trigger": run.trigger,
            "status": run.status,
            "started_at": (run.started_at.isoformat() + "Z") if run.started_at else None,
            "completed_at": (run.completed_at.isoformat() + "Z") if run.completed_at else None,
            "total": run.total,
            "passed": run.passed,
            "failed": run.failed,
            "skipped": run.skipped,
            "duration_ms": run.duration_ms,
        },
        "results": items,
    }


@router.post("/run")
async def trigger_run():
    """Trigger a manual test run."""
    if monitor_state["running"]:
        raise HTTPException(status_code=409, detail="Тесты уже выполняются")

    import asyncio
    asyncio.create_task(run_all_tests(trigger="manual"))
    return {"message": "Тесты запущены", "status": "running"}


@router.post("/run/{test_id}")
async def trigger_single_test(test_id: int):
    """Run a single test and return immediate result."""
    result = await run_single_test(test_id)
    if "error" in result and result["error"] == "Test not found":
        raise HTTPException(status_code=404, detail="Тест не найден")
    return result


@router.put("/config")
async def update_config(data: dict = Body(...)):
    """Update monitor configuration."""
    if "enabled" in data:
        monitor_state["enabled"] = bool(data["enabled"])
    if "interval_minutes" in data:
        val = int(data["interval_minutes"])
        monitor_state["interval_minutes"] = max(5, min(1440, val))

    return {
        "enabled": monitor_state["enabled"],
        "interval_minutes": monitor_state["interval_minutes"],
    }


@router.post("/seed")
async def trigger_seed():
    """Re-seed test definitions."""
    await seed_tests()
    return {"message": "Tests seeded"}


# ── Browser Tests (Playwright) ──

@router.post("/browser-seed")
async def trigger_browser_seed():
    """Seed browser test definitions into DB."""
    from backend.services.browser_test_engine import seed_browser_tests
    await seed_browser_tests()
    return {"message": "Browser tests seeded"}


@router.post("/browser-run")
async def trigger_browser_run():
    """Run all browser-based UI tests (Playwright)."""
    from backend.services.browser_test_engine import run_browser_tests, browser_test_state
    if browser_test_state["running"]:
        raise HTTPException(status_code=409, detail="Browser tests already running")

    import asyncio
    asyncio.create_task(run_browser_tests(trigger="manual"))
    return {"message": "Browser tests started", "status": "running"}

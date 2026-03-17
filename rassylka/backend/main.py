"""
BidRoute AI — FastAPI Application Entry Point
"""
import os
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv(encoding="utf-8")

from backend.database import init_db
from backend.routers import dashboard, bids, suppliers, rules, logs, tracking
from backend.services.bid_parser import parser_loop
from backend.services.mail_engine import distributor_loop
from backend.services.weekly_report import report_scheduler
from backend.services.monitor_engine import monitor_loop
from backend.services.auto_supplier_search import auto_search_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("bidroute")

# Ensure data directory exists
os.makedirs("data", exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Start background tasks
    parser_task = asyncio.create_task(parser_loop())
    distributor_task = asyncio.create_task(distributor_loop())
    report_task = asyncio.create_task(report_scheduler())
    monitor_task = asyncio.create_task(monitor_loop())
    auto_search_task = asyncio.create_task(auto_search_loop())
    logger.info("Background tasks started (5 tasks: parser, distributor, report, monitor, auto_search)")

    yield

    # Shutdown
    parser_task.cancel()
    distributor_task.cancel()
    report_task.cancel()
    monitor_task.cancel()
    auto_search_task.cancel()
    logger.info("Background tasks stopped")


app = FastAPI(
    title="BidRoute AI",
    description="Автоматическая система рассылки заявок поставщикам",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount API routers
app.include_router(dashboard.router)
app.include_router(bids.router)
app.include_router(suppliers.router)
app.include_router(rules.router)
app.include_router(logs.router)
app.include_router(tracking.router)
from backend.routers.tracking import unsub_router
app.include_router(unsub_router)
from backend.routers import smtp_accounts
app.include_router(smtp_accounts.router)
from backend.routers import campaigns
app.include_router(campaigns.router)
from backend.routers import campaign_templates
app.include_router(campaign_templates.router)
from backend.routers import monitor
app.include_router(monitor.router)

# Serve email assets (images from atribut/ folder)
ATRIBUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "atribut")
if os.path.isdir(ATRIBUT_DIR):
    app.mount("/email-assets", StaticFiles(directory=ATRIBUT_DIR), name="email-assets")

# Serve campaign template assets (images, fonts for Prom28 etc.)
CAMPAIGN_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "campaign_templates")
os.makedirs(CAMPAIGN_TEMPLATES_DIR, exist_ok=True)
app.mount("/campaign-assets", StaticFiles(directory=CAMPAIGN_TEMPLATES_DIR), name="campaign-assets")

# Serve frontend static files
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Catch-all route serving the SPA index.html."""
        file_path = os.path.join(FRONTEND_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

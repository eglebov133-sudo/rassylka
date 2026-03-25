"""
BidRoute AI — FastAPI Application Entry Point
"""
import os
import asyncio
import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from dotenv import load_dotenv

load_dotenv(encoding="utf-8")

from backend.database import init_db
from backend.routers import dashboard, bids, suppliers, rules, logs, tracking
from backend.services.bid_parser import parser_loop
from backend.services.mail_engine import distributor_loop
from backend.services.weekly_report import report_scheduler
from backend.services.monitor_engine import monitor_loop
from backend.services.auto_supplier_search import auto_search_loop
from backend.services.bounce_handler import bounce_loop

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

    # Connect Telegram client
    try:
        from backend.services.telegram_sender import connect_tg
        await connect_tg()
    except Exception as e:
        logger.warning(f"Telegram client startup failed (non-critical): {e}")

    # Start background tasks
    parser_task = asyncio.create_task(parser_loop())
    distributor_task = asyncio.create_task(distributor_loop())
    report_task = asyncio.create_task(report_scheduler())
    monitor_task = asyncio.create_task(monitor_loop())
    auto_search_task = asyncio.create_task(auto_search_loop())
    bounce_task = asyncio.create_task(bounce_loop())
    logger.info("Background tasks started (6 tasks: parser, distributor, report, monitor, auto_search, bounce_handler)")

    yield

    # Shutdown
    parser_task.cancel()
    distributor_task.cancel()
    report_task.cancel()
    monitor_task.cancel()
    auto_search_task.cancel()
    bounce_task.cancel()
    logger.info("Background tasks stopped")

    # Disconnect Telegram
    try:
        from backend.services.telegram_sender import disconnect_tg
        await disconnect_tg()
    except Exception:
        pass


app = FastAPI(
    title="BidRoute AI",
    description="Автоматическая система рассылки заявок поставщикам",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Session Auth with Custom Login Page ──
import hashlib, base64, time

PANEL_USER = os.getenv("PANEL_USER", "admin")
PANEL_PASS = os.getenv("PANEL_PASS", "BidRoute2026!")
SESSION_SECRET = hashlib.sha256(f"{PANEL_USER}:{PANEL_PASS}:bidroute".encode()).hexdigest()[:32]

# Public paths that don't require auth (tracking pixels, click redirects, unsubscribe)
PUBLIC_PREFIXES = ("/api/t/", "/api/track/", "/api/unsubscribe", "/email-assets/", "/campaign-assets/")

LOGIN_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BidRoute AI — Вход</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    font-family: 'Inter', sans-serif;
    background: #0f1117;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }
  body::before {
    content: '';
    position: fixed;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(ellipse at 30% 20%, rgba(99,102,241,0.15) 0%, transparent 50%),
                radial-gradient(ellipse at 70% 80%, rgba(139,92,246,0.1) 0%, transparent 50%);
    animation: bg-shift 20s ease-in-out infinite alternate;
  }
  @keyframes bg-shift {
    0% { transform: translate(0, 0); }
    100% { transform: translate(-5%, 3%); }
  }
  .login-card {
    position: relative;
    background: rgba(22, 24, 35, 0.85);
    backdrop-filter: blur(24px);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px;
    padding: 48px 40px;
    width: 100%;
    max-width: 400px;
    box-shadow: 0 25px 60px rgba(0,0,0,0.4);
    animation: card-appear 0.5s ease-out;
  }
  @keyframes card-appear {
    from { opacity: 0; transform: translateY(20px) scale(0.97); }
    to { opacity: 1; transform: translateY(0) scale(1); }
  }
  .brand {
    text-align: center;
    margin-bottom: 32px;
  }
  .brand-icon {
    width: 56px;
    height: 56px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    border-radius: 16px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 16px;
    box-shadow: 0 8px 24px rgba(99,102,241,0.3);
  }
  .brand-icon span { font-size: 28px; color: #fff; }
  .brand h1 { color: #fff; font-size: 22px; font-weight: 800; letter-spacing: -0.02em; }
  .brand p { color: rgba(255,255,255,0.4); font-size: 13px; margin-top: 4px; }
  .form-group { margin-bottom: 16px; }
  .form-label { display:block; color: rgba(255,255,255,0.5); font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
  .form-input {
    width: 100%;
    padding: 12px 16px;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 10px;
    color: #fff;
    font-size: 15px;
    font-family: inherit;
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
  }
  .form-input:focus {
    border-color: #6366f1;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.2);
  }
  .form-input::placeholder { color: rgba(255,255,255,0.25); }
  .btn-login {
    width: 100%;
    padding: 13px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: #fff;
    border: none;
    border-radius: 10px;
    font-size: 15px;
    font-weight: 600;
    font-family: inherit;
    cursor: pointer;
    margin-top: 8px;
    transition: opacity 0.2s, transform 0.1s;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }
  .btn-login:hover { opacity: 0.9; }
  .btn-login:active { transform: scale(0.98); }
  .error-msg {
    color: #ef4444;
    font-size: 13px;
    text-align: center;
    margin-top: 12px;
    display: none;
  }
  .error-msg.show { display: block; animation: shake 0.3s ease; }
  @keyframes shake {
    0%,100% { transform: translateX(0); }
    25% { transform: translateX(-6px); }
    75% { transform: translateX(6px); }
  }
</style>
</head>
<body>
<div class="login-card">
  <div class="brand">
    <div class="brand-icon"><span class="material-symbols-outlined">route</span></div>
    <h1>BidRoute AI</h1>
    <p>Система управления рассылками</p>
  </div>
  <form id="login-form">
    <div class="form-group">
      <label class="form-label">Логин</label>
      <input class="form-input" id="username" type="text" placeholder="admin" autocomplete="username" autofocus>
    </div>
    <div class="form-group">
      <label class="form-label">Пароль</label>
      <input class="form-input" id="password" type="password" placeholder="••••••••" autocomplete="current-password">
    </div>
    <button type="submit" class="btn-login">
      <span class="material-symbols-outlined" style="font-size:20px">login</span> Войти
    </button>
    <div class="error-msg" id="error-msg">Неверный логин или пароль</div>
  </form>
</div>
<script>
document.getElementById('login-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const user = document.getElementById('username').value;
  const pass = document.getElementById('password').value;
  const r = await fetch('/api/auth/login', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({username: user, password: pass}),
  });
  if (r.ok) {
    window.location.reload();
  } else {
    document.getElementById('error-msg').classList.add('show');
    setTimeout(() => document.getElementById('error-msg').classList.remove('show'), 2000);
  }
});
</script>
</body>
</html>"""

from fastapi.responses import HTMLResponse

@app.post("/api/auth/login")
async def auth_login(request: Request):
    data = await request.json()
    user = data.get("username", "")
    pwd = data.get("password", "")
    if secrets.compare_digest(user, PANEL_USER) and secrets.compare_digest(pwd, PANEL_PASS):
        response = Response(content='{"ok":true}', media_type="application/json")
        response.set_cookie(
            key="bidroute_session",
            value=SESSION_SECRET,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=7 * 24 * 3600,  # 7 days
        )
        return response
    return Response(content='{"error":"invalid"}', status_code=401, media_type="application/json")

@app.get("/api/auth/logout")
async def auth_logout():
    response = Response(content='{"ok":true}', media_type="application/json")
    response.delete_cookie("bidroute_session")
    return response

@app.middleware("http")
async def session_auth_middleware(request: Request, call_next):
    path = request.url.path

    # Allow public endpoints
    if any(path.startswith(p) for p in PUBLIC_PREFIXES):
        return await call_next(request)

    # Allow auth endpoints
    if path in ("/api/auth/login", "/api/auth/logout"):
        return await call_next(request)

    # Check session cookie
    session = request.cookies.get("bidroute_session", "")
    if secrets.compare_digest(session, SESSION_SECRET):
        return await call_next(request)

    # Also support Basic Auth (for API/scripts)
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Basic "):
        try:
            decoded = base64.b64decode(auth[6:]).decode("utf-8")
            user, pwd = decoded.split(":", 1)
            if secrets.compare_digest(user, PANEL_USER) and secrets.compare_digest(pwd, PANEL_PASS):
                return await call_next(request)
        except Exception:
            pass

    # Show login page for browser requests, 401 for API
    accept = request.headers.get("Accept", "")
    if "text/html" in accept:
        return HTMLResponse(content=LOGIN_HTML, status_code=401)

    return Response(
        content="Unauthorized",
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="BidRoute AI"'},
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
from backend.routers import promotion
app.include_router(promotion.router)
from backend.routers import telegram
app.include_router(telegram.router)

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

"""
dashboard/main.py
------------------
FastAPI entry point for the BotBudget admin dashboard.

Run:
    uvicorn dashboard.main:app --host 0.0.0.0 --port 8000
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from db.connection import init_pool, close_pool
from dashboard.routers import landing, overview, users, subscribers, broadcast, data_mgmt, miniapp
from utils.logger import get_logger

ADMIN_PREFIX = os.getenv("DASHBOARD_PREFIX", "/admin")

logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB pool on startup, close on shutdown."""
    logger.info("Dashboard starting — initializing DB pool...")
    await init_pool()
    yield
    logger.info("Dashboard shutting down — closing DB pool...")
    await close_pool()


app = FastAPI(
    title="BotBudget Admin Dashboard",
    description="Admin panel for managing BotBudget users, subscriptions, and stats.",
    version="1.0.0",
    lifespan=lifespan,
)

# Templates & static
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.globals["admin_prefix"] = ADMIN_PREFIX
app.state.templates = templates
_static_dir = BASE_DIR / "static"
_static_dir.mkdir(exist_ok=True)
app.mount(
    "/static",
    StaticFiles(directory=str(_static_dir)),
    name="static",
)

# Routers
# Scoped CORS: only for Mini App JSON routes under /api/miniapp
_MINIAPP_ORIGINS = {
    "https://app.botbudget.it",
    "https://app-staging.botbudget.it",
    "http://localhost:5173",
}


class MiniAppCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        origin = request.headers.get("origin", "")
        is_miniapp = path.startswith("/api/miniapp")
        allow = is_miniapp and origin in _MINIAPP_ORIGINS

        # Preflight
        if is_miniapp and request.method == "OPTIONS" and allow:
            from starlette.responses import Response
            resp = Response(status_code=204)
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Methods"] = "GET,POST,DELETE,OPTIONS"
            resp.headers["Access-Control-Allow-Headers"] = "Content-Type,X-Telegram-Init-Data"
            resp.headers["Access-Control-Max-Age"] = "86400"
            resp.headers["Vary"] = "Origin"
            return resp

        response = await call_next(request)
        if allow:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
        return response


app.add_middleware(MiniAppCORSMiddleware)

app.include_router(landing.router)   # public — no auth
app.include_router(miniapp.router)   # public path, auth via X-Telegram-Init-Data
app.include_router(overview.router, prefix=ADMIN_PREFIX)
app.include_router(users.router, prefix=ADMIN_PREFIX)
app.include_router(subscribers.router, prefix=ADMIN_PREFIX)
app.include_router(broadcast.router, prefix=ADMIN_PREFIX)
app.include_router(data_mgmt.router, prefix=ADMIN_PREFIX)


@app.get("/health")
async def health():
    return {"status": "ok"}

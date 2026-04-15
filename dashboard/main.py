"""
dashboard/main.py
------------------
FastAPI entry point for the BotBudget admin dashboard.

Run:
    uvicorn dashboard.main:app --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from db.connection import init_pool, close_pool
from dashboard.routers import overview, users, subscribers, broadcast
from utils.logger import get_logger

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
app.state.templates = templates
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)

# Routers
app.include_router(overview.router)
app.include_router(users.router)
app.include_router(subscribers.router)
app.include_router(broadcast.router)


@app.get("/health")
async def health():
    return {"status": "ok"}

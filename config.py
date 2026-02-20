"""
config.py
---------
Central configuration module. Loads all environment variables
from the .env file and exposes them as typed constants.
"""

import os
from dotenv import load_dotenv

load_dotenv()


# ── Telegram ──────────────────────────────────────────────
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ── Gemini AI ─────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# ── PostgreSQL ────────────────────────────────────────────
DB_HOST: str = os.getenv("DB_HOST", "localhost")
DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
DB_NAME: str = os.getenv("DB_NAME", "bot_budget")
DB_USER: str = os.getenv("DB_USER", "botbudget_user")
DB_PASS: str = os.getenv("DB_PASS", "")

DATABASE_URL: str = (
    f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ── Security ──────────────────────────────────────────────
_raw_ids = os.getenv("ALLOWED_USER_IDS", "")
ALLOWED_USER_IDS: list[int] = (
    [int(uid.strip()) for uid in _raw_ids.split(",") if uid.strip()]
    if _raw_ids
    else []
)

# ── Rate Limiting ─────────────────────────────────────────
RATE_LIMIT_MESSAGES: int = int(os.getenv("RATE_LIMIT_MESSAGES", "30"))
RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

# ── Currency ──────────────────────────────────────────────
DEFAULT_CURRENCY: str = "EUR"

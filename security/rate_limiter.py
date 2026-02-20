"""
security/rate_limiter.py
-------------------------
Rate limiting middleware to prevent API abuse.
Limits the number of messages a user can send within a time window.
"""

import time
from collections import defaultdict
from functools import wraps
from typing import Callable

from telegram import Update
from telegram.ext import ContextTypes

from config import RATE_LIMIT_MESSAGES, RATE_LIMIT_WINDOW_SECONDS
from utils.logger import get_logger

logger = get_logger(__name__)

# In-memory storage for rate tracking: {user_id: [timestamp1, timestamp2, ...]}
_user_timestamps: dict[int, list[float]] = defaultdict(list)


def _cleanup(user_id: int) -> None:
    """Remove expired timestamps for a user."""
    cutoff = time.time() - RATE_LIMIT_WINDOW_SECONDS
    _user_timestamps[user_id] = [
        t for t in _user_timestamps[user_id] if t > cutoff
    ]


def rate_limited(func: Callable):
    """
    Decorator that enforces rate limiting per user.

    Configuration (via .env):
        RATE_LIMIT_MESSAGES: Max messages per window (default: 30).
        RATE_LIMIT_WINDOW_SECONDS: Window duration in seconds (default: 60).

    Behavior:
        - Tracks message timestamps per user.
        - If exceeded, replies with a warning and blocks the handler.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return

        _cleanup(user.id)

        if len(_user_timestamps[user.id]) >= RATE_LIMIT_MESSAGES:
            logger.warning(f"⚠️ Rate limit hit for user {user.id}")
            await update.message.reply_text(
                "⚠️ أنت بتبعت رسائل كتير. استنى شوية وحاول تاني."
            )
            return

        _user_timestamps[user.id].append(time.time())
        return await func(update, context, *args, **kwargs)

    return wrapper

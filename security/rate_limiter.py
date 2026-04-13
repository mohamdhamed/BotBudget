"""
security/rate_limiter.py
-------------------------
Rate limiting middleware to prevent API abuse.
Uses a PostgreSQL table for persistent tracking across restarts.
"""

from datetime import datetime, timezone, timedelta
from functools import wraps
from typing import Callable

from telegram import Update
from telegram.ext import ContextTypes

from config import RATE_LIMIT_MESSAGES, RATE_LIMIT_WINDOW_SECONDS
from db.connection import get_pool
from utils.logger import get_logger

logger = get_logger(__name__)


async def _cleanup(user_id: int) -> None:
    """Remove expired timestamps for a user from the DB."""
    pool = get_pool()
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM rate_limit_log WHERE user_id = %s AND timestamp < %s;",
                (user_id, cutoff),
            )
        await conn.commit()


async def _count(user_id: int) -> int:
    """Count messages from a user within the current window."""
    pool = get_pool()
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM rate_limit_log WHERE user_id = %s AND timestamp >= %s;",
                (user_id, cutoff),
            )
            row = await cur.fetchone()
            return int(row[0]) if row else 0


async def _record(user_id: int) -> None:
    """Record a new message timestamp for a user."""
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO rate_limit_log (user_id, timestamp) VALUES (%s, NOW());",
                (user_id,),
            )
        await conn.commit()


def rate_limited(func: Callable):
    """
    Decorator that enforces rate limiting per user using DB persistence.

    Configuration (via .env):
        RATE_LIMIT_MESSAGES: Max messages per window (default: 30).
        RATE_LIMIT_WINDOW_SECONDS: Window duration in seconds (default: 60).

    Behavior:
        - Persists message timestamps in PostgreSQL (survives restarts).
        - If exceeded, replies with a warning and blocks the handler.
        - Warns at 80% of the limit.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return

        await _cleanup(user.id)
        current_count = await _count(user.id)

        if current_count >= RATE_LIMIT_MESSAGES:
            logger.warning(f"Rate limit hit for user {user.id}")
            await update.message.reply_text(
                "⚠️ أنت بتبعت رسائل كتير جداً. تم الحظر مؤقتاً لمدة دقيقة. استنى شوية."
            )
            return

        if current_count == int(RATE_LIMIT_MESSAGES * 0.8):
            logger.info(f"User {user.id} approaching rate limit ({current_count}/{RATE_LIMIT_MESSAGES})")
            await update.message.reply_text(
                "⚠️ رسالة تحذير: أنت اقتربت من الحد الأقصى للرسائل المسموحة في الدقيقة. يرجى الانتظار قليلاً."
            )

        await _record(user.id)
        return await func(update, context, *args, **kwargs)

    return wrapper


async def cleanup_old_rate_limit_logs(context) -> None:
    """
    Scheduled job: Remove rate limit log entries older than 1 hour.
    Prevents the table from growing indefinitely.
    """
    pool = get_pool()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM rate_limit_log WHERE timestamp < %s;",
                    (cutoff,),
                )
            await conn.commit()
        logger.info("Rate limit log cleanup completed.")
    except Exception as e:
        logger.error(f"Failed to cleanup rate_limit_log: {e}")

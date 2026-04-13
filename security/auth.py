"""
security/auth.py
-----------------
Authentication middleware for the Telegram bot.
Checks users against the DB-backed allowed_users table.
Admins are defined in ADMIN_USER_IDS (config/.env).
"""

from functools import wraps
from typing import Callable

from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_USER_IDS
from repositories.allowed_users_repo import AllowedUsersRepository
from utils.logger import get_logger

logger = get_logger(__name__)

_allowed_users_repo = AllowedUsersRepository()


def authorized_only(func: Callable):
    """
    Decorator that restricts a handler to users in the allowed_users DB table.
    Admins (ADMIN_USER_IDS) are always allowed.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return

        # Admins always pass
        if user.id in ADMIN_USER_IDS:
            return await func(update, context, *args, **kwargs)

        # Check DB whitelist
        allowed = await _allowed_users_repo.is_allowed(user.id)
        if not allowed:
            logger.warning(
                f"🚫 Unauthorized access attempt: user_id={user.id}, "
                f"username={user.username}, name={user.first_name}"
            )
            await update.message.reply_text(
                "⛔ عذراً, هذا البوت خاص ومش متاح للاستخدام العام."
            )
            return

        return await func(update, context, *args, **kwargs)

    return wrapper


def admin_only(func: Callable):
    """
    Decorator that restricts a handler to admins only (ADMIN_USER_IDS in .env).
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return

        if user.id not in ADMIN_USER_IDS:
            logger.warning(f"🚫 Non-admin tried admin command: user_id={user.id}")
            await update.message.reply_text("⛔ الأمر ده للمشرف بس.")
            return

        return await func(update, context, *args, **kwargs)

    return wrapper

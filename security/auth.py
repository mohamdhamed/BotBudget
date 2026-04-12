"""
security/auth.py
-----------------
Authentication middleware for the Telegram bot.
Blocks any user not in the allowed whitelist.
"""

from functools import wraps
from typing import Callable

from telegram import Update
from telegram.ext import ContextTypes

from config import ALLOWED_USER_IDS
from utils.logger import get_logger

logger = get_logger(__name__)


def authorized_only(func: Callable):
    """
    Decorator that restricts a handler to whitelisted users only.

    Usage:
        @authorized_only
        async def my_handler(update, context):
            ...

    Behavior:
        - If ALLOWED_USER_IDS is empty, ALL users are allowed (dev mode).
        - If the list is set, only those users can use the bot.
        - Unauthorized attempts are logged.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return

        # If no whitelist configured, block all users (safety first)
        if not ALLOWED_USER_IDS:
            logger.critical(
                "⚠️ ALLOWED_USER_IDS is empty! Bot is locked. "
                "Set ALLOWED_USER_IDS in .env to allow users."
            )
            await update.message.reply_text(
                "⚠️ البوت مقفول. لازم تحدد المستخدمين المسموح لهم في إعدادات البوت."
            )
            return

        if user.id not in ALLOWED_USER_IDS:
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

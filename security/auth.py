"""
security/auth.py
-----------------
Authentication middleware for the Telegram bot.
- All users are allowed (self-service registration).
- Plan limits are enforced separately via @check_plan_limit.
- Admins are defined in ADMIN_USER_IDS (config/.env).
"""

from functools import wraps
from typing import Callable

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import ADMIN_USER_IDS
from repositories.user_repo import UserRepository
from repositories.subscription_repo import SubscriptionRepository
from utils.logger import get_logger

logger = get_logger(__name__)

_user_repo = UserRepository()
_sub_repo = SubscriptionRepository()

FREE_MONTHLY_LIMIT = 30


def authorized_only(func: Callable):
    """
    Decorator that auto-registers any user and lets them through.
    No whitelist — the bot is open to everyone.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return

        # Auto-register user + subscription on first contact
        await _user_repo.ensure_user(user.id, user.first_name)
        await _sub_repo.ensure_free(user.id)

        return await func(update, context, *args, **kwargs)

    return wrapper


def check_plan_limit(func: Callable):
    """
    Decorator that checks if a free user has exceeded their monthly transaction limit.
    Must be placed AFTER @authorized_only.
    Premium users and admins bypass this check.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return

        # Admins always pass
        if user.id in ADMIN_USER_IDS:
            return await func(update, context, *args, **kwargs)

        plan_info = await _sub_repo.get_plan(user.id)
        if plan_info["is_premium"]:
            return await func(update, context, *args, **kwargs)

        # Free user — check monthly limit
        count = await _sub_repo.count_month_transactions(user.id)
        if count >= FREE_MONTHLY_LIMIT:
            remaining_msg = (
                f"🚫 <b>وصلت للحد الأقصى الشهري</b>\n\n"
                f"📊 استخدمت {FREE_MONTHLY_LIMIT}/{FREE_MONTHLY_LIMIT} معاملة في الخطة المجانية.\n\n"
                f"✨ <b>ترقّي للخطة المميزة</b> واستمتع بـ:\n"
                f"  • معاملات بلا حدود\n"
                f"  • تقارير ذكية شهرية\n"
                f"  • دعم أولوي\n\n"
                f"💡 تقدر تستخدم /month لعرض تقرير الشهر الحالي."
            )
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🌟 معلومات الترقية", callback_data="show_upgrade_info"),
            ]])
            await update.message.reply_text(remaining_msg, reply_markup=keyboard, parse_mode="HTML")
            return

        # Add remaining count hint if close to limit
        context.user_data["remaining_transactions"] = FREE_MONTHLY_LIMIT - count - 1

        return await func(update, context, *args, **kwargs)

    return wrapper


def admin_only(func: Callable):
    """Restricts a handler to admins only (ADMIN_USER_IDS in .env)."""
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

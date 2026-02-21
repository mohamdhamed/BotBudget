"""
handlers/budget_handler.py
---------------------------
Handles budget management commands.
"""

import re

from telegram import Update
from telegram.ext import ContextTypes

from services.budget_service import BudgetService
from security.auth import authorized_only
from security.rate_limiter import rate_limited
from utils.logger import get_logger

logger = get_logger(__name__)
budget_service = BudgetService()

# Arabic digit conversion
_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


@authorized_only
@rate_limited
async def budget_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /budget command - manage monthly budgets.

    Usage:
        /budget              → show budget status
        /budget set طعام 200  → set budget for category
        /budget set إجمالي 2000 → set overall budget
        /budget delete طعام   → remove budget
    """
    user = update.effective_user

    if not context.args:
        # Show budget status
        msg = budget_service.get_budget_status(user.id)
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    action = context.args[0].lower()

    if action == "set":
        if len(context.args) < 3:
            await update.message.reply_text(
                "💰 *تحديد ميزانية*\n\n"
                "*الصيغة:* `/budget set <الفئة> <المبلغ>`\n\n"
                "*أمثلة:*\n"
                "• `/budget set طعام 200`\n"
                "• `/budget set سوبرماركت 300`\n"
                "• `/budget set إجمالي 2000` ← ميزانية كلية\n",
                parse_mode="Markdown",
            )
            return

        category = context.args[1]
        try:
            amount = float(context.args[2].translate(_AR_DIGITS))
        except ValueError:
            await update.message.reply_text("⚠️ المبلغ لازم يكون رقم.")
            return

        msg = budget_service.set_budget(user.id, category, amount)
        await update.message.reply_text(msg)

    elif action == "delete":
        if len(context.args) < 2:
            await update.message.reply_text("⚠️ الاستخدام: `/budget delete <الفئة>`", parse_mode="Markdown")
            return

        category = context.args[1]
        msg = budget_service.delete_budget(user.id, category)
        await update.message.reply_text(msg)

    else:
        await update.message.reply_text(
            "⚠️ أمر مش معروف.\n"
            "استخدم:\n"
            "• `/budget` → حالة الميزانية\n"
            "• `/budget set <فئة> <مبلغ>`\n"
            "• `/budget delete <فئة>`",
            parse_mode="Markdown",
        )

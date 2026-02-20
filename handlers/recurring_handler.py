"""
handlers/recurring_handler.py
------------------------------
Handles recurring payment interactions.
Delegates all logic to RecurringService.
"""

from telegram import Update
from telegram.ext import ContextTypes

from services.recurring_service import RecurringService
from security.auth import authorized_only
from security.rate_limiter import rate_limited
from utils.logger import get_logger

logger = get_logger(__name__)
recurring_service = RecurringService()


@authorized_only
@rate_limited
async def recurring_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /recurring command - list all active recurring payments."""
    user = update.effective_user
    msg = recurring_service.list_active(user.id)
    await update.message.reply_text(msg)


@authorized_only
@rate_limited
async def add_recurring_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /add_recurring <description> - add a new recurring payment.
    Usage: /add_recurring اشتراك نتفليكس ١٥ يورو كل شهر
    """
    user = update.effective_user

    if not context.args:
        await update.message.reply_text(
            "⚠️ الاستخدام: /add_recurring <وصف الدفعة>\n"
            "مثال: /add_recurring اشتراك نتفليكس ١٥ يورو كل شهر"
        )
        return

    text = " ".join(context.args)
    result = recurring_service.add_from_text(user.id, text)

    if result.get("success"):
        await update.message.reply_text(result["message"])
    else:
        await update.message.reply_text(f"🤔 {result.get('question', 'حاول تاني.')}")


@authorized_only
@rate_limited
async def delete_recurring_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /delete_recurring <id> - delete a recurring payment.
    Usage: /delete_recurring 3
    """
    user = update.effective_user

    if not context.args:
        await update.message.reply_text(
            "⚠️ الاستخدام: /delete_recurring <رقم الدفعة>\n"
            "مثال: /delete_recurring 3"
        )
        return

    try:
        payment_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ رقم الدفعة لازم يكون رقم صحيح.")
        return

    msg = recurring_service.delete_payment(payment_id, user.id)
    await update.message.reply_text(msg)

"""
handlers/expense_handler.py
----------------------------
Handles expense/income-related interactions.
Delegates all logic to ExpenseService.
"""

from telegram import Update
from telegram.ext import ContextTypes

from repositories.user_repo import UserRepository
from services.expense_service import ExpenseService
from security.auth import authorized_only
from security.rate_limiter import rate_limited
from utils.logger import get_logger

logger = get_logger(__name__)
expense_service = ExpenseService()
user_repo = UserRepository()


@authorized_only
@rate_limited
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle any plain text message (not a command).
    Sends the text to Gemini for parsing and saves the result.
    """
    user = update.effective_user
    text = update.message.text.strip()

    if not text:
        return

    # Ensure user exists
    user_repo.ensure_user(user.id, user.first_name)

    # Process via service
    result = expense_service.add_from_text(user.id, text)

    if result.get("success"):
        await update.message.reply_text(result["message"])
    else:
        await update.message.reply_text(f"🤔 {result.get('question', 'حاول تاني.')}")


@authorized_only
@rate_limited
async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /today command - show today's summary."""
    user = update.effective_user
    summary = expense_service.get_today_summary(user.id)
    await update.message.reply_text(summary)


@authorized_only
@rate_limited
async def month_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /month command - show current month's summary."""
    user = update.effective_user
    summary = expense_service.get_month_summary(user.id)
    await update.message.reply_text(summary)


@authorized_only
@rate_limited
async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /delete <id> command - delete a transaction.
    Usage: /delete 5
    """
    user = update.effective_user

    if not context.args:
        await update.message.reply_text("⚠️ الاستخدام: /delete <رقم العملية>\nمثال: /delete 5")
        return

    try:
        expense_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ رقم العملية لازم يكون رقم صحيح.")
        return

    msg = expense_service.delete_expense(expense_id, user.id)
    await update.message.reply_text(msg)

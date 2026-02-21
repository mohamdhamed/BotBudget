"""
handlers/expense_handler.py
----------------------------
Handles expense/income-related interactions.
Delegates all logic to ExpenseService.
"""

import re

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

# Arabic digit conversion
_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


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
async def week_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /week command - show last 7 days summary."""
    user = update.effective_user
    summary = expense_service.get_week_summary(user.id)
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


@authorized_only
@rate_limited
async def edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /edit command - edit an existing transaction.

    Format: /edit <رقم> مبلغ:<قيمة> فئة:<فئة> وصف:<وصف>
    At least one field is required.

    Examples:
        /edit 5 مبلغ:75
        /edit 3 فئة:طعام
        /edit 10 مبلغ:100 فئة:مواصلات وصف:تاكسي
    """
    user = update.effective_user

    if not context.args:
        await update.message.reply_text(
            "✏️ *تعديل معاملة*\n\n"
            "*الصيغة:*\n"
            "`/edit <رقم> مبلغ:<قيمة> فئة:<فئة> وصف:<وصف>`\n\n"
            "*أمثلة:*\n"
            "• `/edit 5 مبلغ:75`\n"
            "• `/edit 3 فئة:طعام`\n"
            "• `/edit 10 مبلغ:100 وصف:تاكسي`\n\n"
            "💡 حدد على الأقل حقل واحد للتعديل.",
            parse_mode="Markdown",
        )
        return

    try:
        expense_id = int(context.args[0].translate(_AR_DIGITS))
    except ValueError:
        await update.message.reply_text("⚠️ أول حاجة بعد /edit لازم يكون رقم العملية.")
        return

    text = " ".join(context.args[1:])
    if not text:
        await update.message.reply_text("⚠️ حدد التعديل المطلوب. مثال: `/edit 5 مبلغ:75`", parse_mode="Markdown")
        return

    # Parse edit fields
    amount = None
    category = None
    description = None

    amount_match = re.search(r"مبلغ[:\s]+([٠-٩\d.]+)", text)
    if amount_match:
        try:
            amount = float(amount_match.group(1).translate(_AR_DIGITS))
        except ValueError:
            pass

    cat_match = re.search(r"فئة[:\s]+([^\s]+)", text)
    if cat_match:
        category = cat_match.group(1)

    desc_match = re.search(r"وصف[:\s]+(.+?)(?=\s+(?:مبلغ|فئة)|$)", text)
    if desc_match:
        description = desc_match.group(1).strip()

    msg = expense_service.edit_expense(expense_id, user.id, amount, category, description)
    await update.message.reply_text(msg)


@authorized_only
@rate_limited
async def category_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /category <name> - show all transactions for a category.

    Usage:
        /category طعام
        /category سوبرماركت
    """
    user = update.effective_user

    if not context.args:
        await update.message.reply_text(
            "🏷️ *عرض حسب الفئة*\n\n"
            "*الصيغة:* `/category <اسم الفئة>`\n\n"
            "*أمثلة:*\n"
            "• `/category طعام`\n"
            "• `/category سوبرماركت`\n"
            "• `/category إيجار`\n\n"
            "*الفئات المتاحة:*\n"
            "طعام، مواصلات، سوبرماركت، إيجار، فواتير، اشتراكات، "
            "ترفيه، صحة، تعليم، ملابس، هدايا، راتب، تحويل، "
            "مطعم، كافيه، بنزين، تأمين، أخرى",
            parse_mode="Markdown",
        )
        return

    category = context.args[0]
    msg = expense_service.get_category_details(user.id, category)
    await update.message.reply_text(msg)

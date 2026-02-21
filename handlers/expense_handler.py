"""
handlers/expense_handler.py
----------------------------
Handles expense/income-related interactions.
Delegates all logic to ExpenseService.
"""

import re
from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

from repositories.user_repo import UserRepository
from services.expense_service import ExpenseService
from services.budget_service import BudgetService
from security.auth import authorized_only
from security.rate_limiter import rate_limited
from utils.logger import get_logger

logger = get_logger(__name__)
expense_service = ExpenseService()
budget_service = BudgetService()
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
        reply = result["message"]
        # Check budget alert
        alert = budget_service.check_budget_alert(
            user.id, result.get("category", ""), 0
        )
        if alert:
            reply += f"\n\n{alert}"
        await update.message.reply_text(reply)
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


@authorized_only
@rate_limited
async def compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /compare command - compare two months.

    Usage:
        /compare           → current vs previous month
        /compare 1 2       → January vs February
        /compare 12 2025 1 2026 → Dec 2025 vs Jan 2026
    """
    user = update.effective_user
    m1, y1, m2, y2 = None, None, None, None

    args = context.args or []
    try:
        if len(args) >= 4:
            m1, y1, m2, y2 = int(args[0]), int(args[1]), int(args[2]), int(args[3])
        elif len(args) >= 2:
            m1, m2 = int(args[0]), int(args[1])
    except ValueError:
        await update.message.reply_text("⚠️ الاستخدام: `/compare [شهر1] [شهر2]`", parse_mode="Markdown")
        return

    msg = expense_service.compare_months(user.id, m1, y1, m2, y2)
    await update.message.reply_text(msg)


@authorized_only
@rate_limited
async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /search command - search transactions.
    Usage: /search نتفليكس
    """
    user = update.effective_user

    if not context.args:
        await update.message.reply_text(
            "🔍 *بحث في المعاملات*\n\n"
            "*الصيغة:* `/search <كلمة البحث>`\n\n"
            "*أمثلة:*\n"
            "• `/search طعام`\n"
            "• `/search نتفليكس`\n"
            "• `/search إيجار`",
            parse_mode="Markdown",
        )
        return

    query = " ".join(context.args)
    msg = expense_service.search_transactions(user.id, query)
    await update.message.reply_text(msg)


@authorized_only
@rate_limited
async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /report command - report for a date range.

    Usage:
        /report 2026-01-01 2026-01-31
        /report 2026-02-01 2026-02-21
    """
    user = update.effective_user

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "📋 *تقرير مخصص*\n\n"
            "*الصيغة:* `/report <من> <إلى>`\n\n"
            "*مثال:*\n"
            "`/report 2026-01-01 2026-01-31`",
            parse_mode="Markdown",
        )
        return

    try:
        start = date.fromisoformat(context.args[0])
        end = date.fromisoformat(context.args[1])
    except ValueError:
        await update.message.reply_text("⚠️ التاريخ لازم يكون بالصيغة: YYYY-MM-DD")
        return

    msg = expense_service.get_date_range_report(user.id, start, end)
    await update.message.reply_text(msg)


@authorized_only
@rate_limited
async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /balance command - show overall balance."""
    user = update.effective_user
    msg = expense_service.get_balance(user.id)
    await update.message.reply_text(msg, parse_mode="Markdown")


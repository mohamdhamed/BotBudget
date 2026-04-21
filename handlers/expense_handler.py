"""
handlers/expense_handler.py
----------------------------
Handles expense/income-related interactions.
All selection commands use inline keyboards instead of manual ID typing.
Multi-step flows (edit, compare) use ConversationHandler.
"""

import re
from datetime import date

from dateutil.relativedelta import relativedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from ai.gemini_parser import parse_transaction
from repositories.user_repo import UserRepository
from services.expense_service import ExpenseService
from services.budget_service import BudgetService
from security.auth import authorized_only, check_plan_limit, premium_only
from security.rate_limiter import rate_limited
from utils.logger import get_logger

logger = get_logger(__name__)
expense_service = ExpenseService()
budget_service = BudgetService()
user_repo = UserRepository()

# ── Constants ─────────────────────────────────────────────
_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

CATEGORIES = [
    "طعام", "مواصلات", "سوبرماركت", "إيجار", "فواتير",
    "اشتراكات", "ترفيه", "صحة", "تعليم", "ملابس",
    "هدايا", "راتب", "تحويل", "مطعم", "كافيه",
    "بنزين", "تأمين", "أخرى",
]

_MONTHS_AR = [
    "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
]

# ConversationHandler states
EDIT_TX, EDIT_FIELD, EDIT_VALUE, EDIT_CAT_PICK = range(4)
CMP_M1, CMP_M2 = range(2)


# ── Shared keyboard builders ─────────────────────────────

def _category_keyboard(prefix: str, cancel_data: str = "cancel_conv") -> InlineKeyboardMarkup:
    """3-column inline keyboard of all categories with cancel button."""
    rows = []
    for i in range(0, len(CATEGORIES), 3):
        rows.append([
            InlineKeyboardButton(c, callback_data=f"{prefix}{c}")
            for c in CATEGORIES[i:i + 3]
        ])
    rows.append([InlineKeyboardButton("❌ إلغاء", callback_data=cancel_data)])
    return InlineKeyboardMarkup(rows)


def _month_keyboard(prefix: str, n=6) -> InlineKeyboardMarkup:
    """Inline keyboard of last N months."""
    today = date.today()
    rows, row = [], []
    for i in range(n):
        d = today - relativedelta(months=i)
        label = f"{_MONTHS_AR[d.month - 1]} {d.year}"
        row.append(InlineKeyboardButton(label, callback_data=f"{prefix}{d.month}_{d.year}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("❌ إلغاء", callback_data="cancel_conv")])
    return InlineKeyboardMarkup(rows)


# ══════════════════════════════════════════════════════════
# TEXT MESSAGE → AI parse → confirmation keyboard
# ══════════════════════════════════════════════════════════

@authorized_only
@rate_limited
@check_plan_limit
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    text = update.message.text.strip()
    if not text:
        return

    db_user = await user_repo.ensure_user(user.id, user.first_name)
    user_currency = db_user.get("currency", "EUR")
    parsed = parse_transaction(text, user_currency)

    if "error" in parsed:
        await update.message.reply_text(f"🤔 {parsed.get('question', 'حاول تاني.')}")
        return

    confidence = parsed.get("confidence", 1.0)
    if confidence < 0.4:
        await update.message.reply_text(
            f"🤔 مش قادر أفهم الرسالة دي بشكل كافي.\n{parsed.get('question', 'ممكن تعيد الصياغة؟')}"
        )
        return

    tx_currency = parsed.get("currency", user_currency)
    context.user_data["pending_expense"] = {**parsed, "raw_text": text, "currency": tx_currency}

    tx_type = "مصروف" if parsed.get("type") == "expense" else "دخل"
    emoji = "💸" if parsed.get("type") == "expense" else "💰"
    note = "\n⚠️ لم أكن متأكداً تماماً، تحقق من التفاصيل." if confidence < 0.6 else ""

    preview = (
        f"{emoji} *تأكيد {tx_type}:*\n"
        f"  📂 الفئة: {parsed.get('category', 'أخرى')}\n"
        f"  💶 المبلغ: {parsed.get('amount', 0):.2f} {tx_currency}\n"
        f"  📅 التاريخ: {parsed.get('date', date.today())}"
        f"{note}"
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ تأكيد", callback_data="confirm_expense"),
        InlineKeyboardButton("❌ إلغاء", callback_data="cancel_expense"),
    ]])
    await update.message.reply_text(preview, reply_markup=keyboard, parse_mode="Markdown")


async def handle_expense_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    if query.data == "cancel_expense":
        context.user_data.pop("pending_expense", None)
        await query.edit_message_text("❌ تم إلغاء العملية.")
        return

    if query.data == "confirm_expense":
        pending = context.user_data.pop("pending_expense", None)
        if not pending:
            await query.edit_message_text("⚠️ انتهت صلاحية التأكيد. أعد إرسال الرسالة.")
            return
        try:
            result = await expense_service.add_from_parsed(user.id, pending)
        except Exception as e:
            logger.error(f"Failed to save expense for user {user.id}: {e}", exc_info=True)
            await query.edit_message_text("⚠️ حصل خطأ في حفظ المعاملة. حاول تاني بعد شوية.")
            return

        if result.get("success"):
            reply = result["message"]
            try:
                alert = await budget_service.check_budget_alert(user.id, result.get("category", ""), 0)
                if alert:
                    reply += f"\n\n{alert}"
            except Exception as e:
                logger.warning(f"Budget alert check failed for user {user.id}: {e}")
            remaining = context.user_data.get("remaining_transactions")
            if remaining is not None and remaining <= 10:
                reply += f"\n\n📊 متبقي {remaining} معاملة مجانية هذا الشهر."
            quick_buttons = InlineKeyboardMarkup([[
                InlineKeyboardButton("📊 ملخص اليوم", callback_data="quick_today"),
                InlineKeyboardButton("🗑️ حذف", callback_data="quick_delete"),
            ]])
            await query.edit_message_text(reply, reply_markup=quick_buttons)
        else:
            await query.edit_message_text(f"⚠️ فشل الحفظ. {result.get('question', 'حاول تاني.')}")


async def handle_quick_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Quick Buttons after a successful transaction."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if query.data == "quick_today":
        summary = await expense_service.get_today_summary(user_id)
        await query.message.reply_text(summary, parse_mode="HTML")
    elif query.data == "quick_delete":
        expenses = await expense_service.repo.get_last_n(user_id, 10)
        if not expenses:
            await query.message.reply_text("📭 مفيش معاملات مسجلة.")
            return
        buttons = []
        for e in expenses:
            sign = "💸" if e.is_expense() else "💰"
            label = f"{sign} #{e.id} | {e.amount:.0f}€ | {e.category} | {e.date}"
            buttons.append([InlineKeyboardButton(label, callback_data=f"del_{e.id}")])
        buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="del_cancel")])
        await query.message.reply_text(
            "🗑️ اختار المعاملة اللي عايز تحذفها:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )


# ══════════════════════════════════════════════════════════
# SIMPLE COMMANDS (today, week, month, balance, last, undo, search, report)
# ══════════════════════════════════════════════════════════

@authorized_only
@rate_limited
async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(await expense_service.get_today_summary(update.effective_user.id), parse_mode="HTML")

@authorized_only
@rate_limited
async def month_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(await expense_service.get_month_summary(update.effective_user.id), parse_mode="HTML")

@authorized_only
@rate_limited
async def week_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(await expense_service.get_week_summary(update.effective_user.id), parse_mode="HTML")

@authorized_only
@rate_limited
async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(await expense_service.get_balance(update.effective_user.id), parse_mode="HTML")

@authorized_only
@rate_limited
async def last_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(await expense_service.get_last_expenses(update.effective_user.id), parse_mode="HTML")

@authorized_only
@rate_limited
async def undo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(await expense_service.undo_last(update.effective_user.id))

@authorized_only
@rate_limited
async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "🔍 <b>بحث في المعاملات</b>\n\n<b>الصيغة:</b> /search &lt;كلمة البحث&gt;\n<b>مثال:</b> /search نتفليكس",
            parse_mode="HTML",
        )
        return
    msg = await expense_service.search_transactions(update.effective_user.id, " ".join(context.args))
    await update.message.reply_text(msg, parse_mode="HTML")

@authorized_only
@premium_only("التقارير المخصصة")
@rate_limited
async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "📋 <b>تقرير مخصص</b>\n\n<b>الصيغة:</b> /report &lt;من&gt; &lt;إلى&gt;\n<b>مثال:</b> /report 2026-01-01 2026-01-31",
            parse_mode="HTML",
        )
        return
    try:
        start = date.fromisoformat(context.args[0])
        end = date.fromisoformat(context.args[1])
    except ValueError:
        await update.message.reply_text("⚠️ التاريخ لازم يكون بالصيغة: YYYY-MM-DD")
        return
    await update.message.reply_text(await expense_service.get_date_range_report(update.effective_user.id, start, end), parse_mode="HTML")


# ══════════════════════════════════════════════════════════
# DELETE — inline transaction picker (no manual ID needed)
# ══════════════════════════════════════════════════════════

@authorized_only
@rate_limited
async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show last 10 transactions as buttons to pick one for deletion."""
    # Still support old syntax: /delete 5
    if context.args:
        try:
            expense_id = int(context.args[0])
            msg = await expense_service.delete_expense(expense_id, update.effective_user.id)
            await update.message.reply_text(msg)
            return
        except ValueError:
            pass

    expenses = await expense_service.repo.get_last_n(update.effective_user.id, 10)
    if not expenses:
        await update.message.reply_text("📭 مفيش معاملات مسجلة.")
        return

    buttons = []
    for e in expenses:
        sign = "💸" if e.is_expense() else "💰"
        label = f"{sign} #{e.id} | {e.amount:.0f}€ | {e.category} | {e.date}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"del_{e.id}")])
    buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="del_cancel")])

    await update.message.reply_text(
        "🗑️ اختار المعاملة اللي عايز تحذفها:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def handle_delete_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show confirmation for selected transaction."""
    query = update.callback_query
    await query.answer()

    if query.data == "del_cancel":
        await query.edit_message_text("✅ تم الإلغاء.")
        return

    tx_id = query.data.split("_")[1]
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ تأكيد الحذف", callback_data=f"delok_{tx_id}"),
        InlineKeyboardButton("❌ إلغاء", callback_data="del_cancel"),
    ]])
    await query.edit_message_text(f"⚠️ تأكيد حذف المعاملة #{tx_id}؟", reply_markup=keyboard)


async def handle_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Execute deletion after confirmation."""
    query = update.callback_query
    await query.answer()
    tx_id = int(query.data.split("_")[1])
    msg = await expense_service.delete_expense(tx_id, update.effective_user.id)
    await query.edit_message_text(msg)


# ══════════════════════════════════════════════════════════
# CATEGORY — inline category grid
# ══════════════════════════════════════════════════════════

@authorized_only
@rate_limited
async def category_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show category grid or direct result if arg provided."""
    if context.args:
        msg = await expense_service.get_category_details(update.effective_user.id, context.args[0])
        await update.message.reply_text(msg, parse_mode="HTML")
        return

    await update.message.reply_text(
        "🏷️ اختار الفئة:",
        reply_markup=_category_keyboard("catshow_", cancel_data="cat_cancel"),
    )


async def handle_category_show(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show transactions for selected category."""
    query = update.callback_query
    await query.answer()
    category = query.data[8:]  # remove "catshow_"
    msg = await expense_service.get_category_details(update.effective_user.id, category)
    await query.edit_message_text(msg, parse_mode="HTML")


async def handle_cancel_generic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generic cancel for standalone inline keyboards."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ تم الإلغاء.")


# ══════════════════════════════════════════════════════════
# EDIT — ConversationHandler (pick tx → pick field → enter value)
# ══════════════════════════════════════════════════════════

@authorized_only
@rate_limited
async def edit_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: show last 10 transactions as buttons."""
    expenses = await expense_service.repo.get_last_n(update.effective_user.id, 10)
    if not expenses:
        await update.message.reply_text("📭 مفيش معاملات مسجلة.")
        return ConversationHandler.END

    buttons = []
    for e in expenses:
        sign = "💸" if e.is_expense() else "💰"
        label = f"{sign} #{e.id} | {e.amount:.0f}€ | {e.category} | {e.date}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"edittx_{e.id}")])
    buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="cancel_conv")])

    await update.message.reply_text(
        "✏️ اختار المعاملة اللي تحب تعدّلها:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return EDIT_TX


async def edit_tx_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store tx ID and show field picker."""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_conv":
        await query.edit_message_text("✅ تم الإلغاء.")
        return ConversationHandler.END

    tx_id = int(query.data.split("_")[1])
    context.user_data["edit_tx_id"] = tx_id

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💶 المبلغ", callback_data="editfield_amount"),
            InlineKeyboardButton("📂 الفئة", callback_data="editfield_category"),
        ],
        [InlineKeyboardButton("📝 الوصف", callback_data="editfield_description")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_conv")],
    ])
    await query.edit_message_text(
        f"✏️ المعاملة #{tx_id} — اختار الحقل اللي تحب تعدّله:",
        reply_markup=keyboard,
    )
    return EDIT_FIELD


async def edit_field_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """For category → show grid. For amount/desc → ask for text."""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_conv":
        await query.edit_message_text("✅ تم الإلغاء.")
        return ConversationHandler.END

    field = query.data.split("_")[1]
    context.user_data["edit_field"] = field

    if field == "category":
        await query.edit_message_text(
            "📂 اختار الفئة الجديدة:",
            reply_markup=_category_keyboard("editcat_"),
        )
        return EDIT_CAT_PICK

    prompts = {"amount": "💶 اكتب المبلغ الجديد:", "description": "📝 اكتب الوصف الجديد:"}
    await query.edit_message_text(prompts[field])
    return EDIT_VALUE


async def edit_value_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Apply text edit (amount or description)."""
    tx_id = context.user_data.get("edit_tx_id")
    field = context.user_data.get("edit_field")
    value = update.message.text.strip()

    amount = category = description = None

    if field == "amount":
        try:
            amount = float(value.translate(_AR_DIGITS))
        except ValueError:
            await update.message.reply_text("⚠️ رقم مش صحيح. اكتب المبلغ الجديد:")
            return EDIT_VALUE
    elif field == "description":
        description = value

    msg = await expense_service.edit_expense(tx_id, update.effective_user.id, amount, category, description)
    await update.message.reply_text(msg)
    return ConversationHandler.END


async def edit_category_picked(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Apply category edit from inline grid."""
    query = update.callback_query
    await query.answer()
    category = query.data[8:]  # remove "editcat_"
    tx_id = context.user_data.get("edit_tx_id")
    msg = await expense_service.edit_expense(tx_id, update.effective_user.id, None, category, None)
    await query.edit_message_text(msg)
    return ConversationHandler.END


async def _cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ تم الإلغاء.")
    return ConversationHandler.END


# Build the edit ConversationHandler
edit_conversation = ConversationHandler(
    entry_points=[CommandHandler("edit", edit_entry)],
    states={
        EDIT_TX: [
            CallbackQueryHandler(edit_tx_selected, pattern=r"^edittx_\d+$"),
            CallbackQueryHandler(_cancel_conv, pattern="^cancel_conv$"),
        ],
        EDIT_FIELD: [
            CallbackQueryHandler(edit_field_selected, pattern=r"^editfield_"),
            CallbackQueryHandler(_cancel_conv, pattern="^cancel_conv$"),
        ],
        EDIT_VALUE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_value_entered),
        ],
        EDIT_CAT_PICK: [
            CallbackQueryHandler(edit_category_picked, pattern=r"^editcat_"),
            CallbackQueryHandler(_cancel_conv, pattern="^cancel_conv$"),
        ],
    },
    fallbacks=[CallbackQueryHandler(_cancel_conv, pattern="^cancel_conv$")],
    per_message=False,
)


# ══════════════════════════════════════════════════════════
# COMPARE — ConversationHandler (pick month 1 → pick month 2)
# ══════════════════════════════════════════════════════════

@authorized_only
@premium_only("المقارنة الشهرية")
@rate_limited
async def compare_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show month picker for first month."""
    await update.message.reply_text(
        "🔄 اختار *الشهر الأول* للمقارنة:",
        reply_markup=_month_keyboard("cmp1_"),
        parse_mode="Markdown",
    )
    return CMP_M1


async def compare_m1_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_conv":
        await query.edit_message_text("✅ تم الإلغاء.")
        return ConversationHandler.END

    parts = query.data.replace("cmp1_", "").split("_")
    context.user_data["cmp_m1"] = int(parts[0])
    context.user_data["cmp_y1"] = int(parts[1])

    label = f"{_MONTHS_AR[int(parts[0]) - 1]} {parts[1]}"
    await query.edit_message_text(
        f"🔄 الشهر الأول: *{label}*\n\nاختار *الشهر الثاني*:",
        reply_markup=_month_keyboard("cmp2_"),
        parse_mode="Markdown",
    )
    return CMP_M2


async def compare_m2_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_conv":
        await query.edit_message_text("✅ تم الإلغاء.")
        return ConversationHandler.END

    parts = query.data.replace("cmp2_", "").split("_")
    m1 = context.user_data.get("cmp_m1")
    y1 = context.user_data.get("cmp_y1")

    await query.edit_message_text("⏳ جاري المقارنة...")
    msg = await expense_service.compare_months(update.effective_user.id, m1, y1, int(parts[0]), int(parts[1]))
    await query.edit_message_text(msg, parse_mode="HTML")
    return ConversationHandler.END


# Build the compare ConversationHandler
compare_conversation = ConversationHandler(
    entry_points=[CommandHandler("compare", compare_entry)],
    states={
        CMP_M1: [
            CallbackQueryHandler(compare_m1_selected, pattern=r"^cmp1_"),
            CallbackQueryHandler(_cancel_conv, pattern="^cancel_conv$"),
        ],
        CMP_M2: [
            CallbackQueryHandler(compare_m2_selected, pattern=r"^cmp2_"),
            CallbackQueryHandler(_cancel_conv, pattern="^cancel_conv$"),
        ],
    },
    fallbacks=[CallbackQueryHandler(_cancel_conv, pattern="^cancel_conv$")],
    per_message=False,
)

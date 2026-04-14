"""
handlers/budget_handler.py
---------------------------
Handles budget management commands with inline keyboard category selection.
Uses a single ConversationHandler for the set flow, triggered from both
/budget button AND /setbudget command.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from handlers.expense_handler import CATEGORIES
from services.budget_service import BudgetService
from security.auth import authorized_only
from security.rate_limiter import rate_limited
from utils.logger import get_logger

logger = get_logger(__name__)
budget_service = BudgetService()

_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

# ConversationHandler states
BUDGET_CAT, BUDGET_AMOUNT = range(2)


def _budget_category_keyboard(prefix: str) -> InlineKeyboardMarkup:
    """3-column category keyboard + overall budget option."""
    cats = ["إجمالي"] + list(CATEGORIES)
    rows = []
    for i in range(0, len(cats), 3):
        rows.append([
            InlineKeyboardButton(c, callback_data=f"{prefix}{c}")
            for c in cats[i:i + 3]
        ])
    rows.append([InlineKeyboardButton("❌ إلغاء", callback_data="cancel_budget")])
    return InlineKeyboardMarkup(rows)


# ══════════════════════════════════════════════════════════
# /budget — show status + action buttons
# ══════════════════════════════════════════════════════════

@authorized_only
@rate_limited
async def budget_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show budget status with action buttons."""
    user = update.effective_user

    # Support old syntax: /budget set طعام 200, /budget delete طعام
    if context.args:
        action = context.args[0].lower()
        if action == "set" and len(context.args) >= 3:
            category = context.args[1]
            try:
                amount = float(context.args[2].translate(_AR_DIGITS))
            except ValueError:
                await update.message.reply_text("⚠️ المبلغ لازم يكون رقم.")
                return
            msg = await budget_service.set_budget(user.id, category, amount)
            await update.message.reply_text(msg)
            return
        elif action == "delete" and len(context.args) >= 2:
            msg = await budget_service.delete_budget(user.id, context.args[1])
            await update.message.reply_text(msg)
            return

    msg = await budget_service.get_budget_status(user.id)
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ تحديد ميزانية", callback_data="budgetaction_set"),
            InlineKeyboardButton("🗑️ حذف ميزانية", callback_data="budgetaction_del"),
        ],
    ])
    await update.message.reply_text(msg, reply_markup=keyboard, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════
# DELETE budget — standalone callback (no ConversationHandler needed)
# ══════════════════════════════════════════════════════════

async def handle_budget_del_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show category grid for deleting a budget."""
    logger.info(">>> handle_budget_del_action CALLED")
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🗑️ اختار الفئة لحذف ميزانيتها:",
        reply_markup=_budget_category_keyboard("budgetdel_"),
    )


async def handle_budget_delete_cat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete budget for selected category."""
    query = update.callback_query
    await query.answer()
    category = query.data[10:]  # remove "budgetdel_"
    msg = await budget_service.delete_budget(update.effective_user.id, category)
    await query.edit_message_text(msg)


async def handle_budget_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ تم الإلغاء.")


# ══════════════════════════════════════════════════════════
# SET budget — ConversationHandler (category → amount)
# Entry: /setbudget command OR "➕ تحديد ميزانية" button
# ══════════════════════════════════════════════════════════

@authorized_only
@rate_limited
async def budget_set_entry_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry from /setbudget command: show category grid."""
    await update.message.reply_text(
        "💰 اختار الفئة لتحديد ميزانيتها:",
        reply_markup=_budget_category_keyboard("budgetsetconv_"),
    )
    return BUDGET_CAT


async def budget_set_entry_btn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry from inline button: show category grid."""
    logger.info(">>> budget_set_entry_btn CALLED — entering BUDGET_CAT state")
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💰 اختار الفئة لتحديد ميزانيتها:",
        reply_markup=_budget_category_keyboard("budgetsetconv_"),
    )
    return BUDGET_CAT


async def budget_set_cat_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store selected category and ask for amount."""
    logger.info(f">>> budget_set_cat_selected CALLED — data={update.callback_query.data}")
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_budget":
        await query.edit_message_text("✅ تم الإلغاء.")
        return ConversationHandler.END

    category = query.data[14:]  # remove "budgetsetconv_"
    context.user_data["budget_set_cat"] = category
    await query.edit_message_text(
        f"💰 فئة: *{category}*\n\nاكتب مبلغ الميزانية الشهرية:",
        parse_mode="Markdown",
    )
    return BUDGET_AMOUNT


async def budget_set_amount_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Set the budget amount."""
    logger.info(f">>> budget_set_amount_entered CALLED — text={update.message.text}")
    category = context.user_data.get("budget_set_cat")
    value = update.message.text.strip()

    try:
        amount = float(value.translate(_AR_DIGITS))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ اكتب مبلغ صحيح (رقم أكبر من 0):")
        return BUDGET_AMOUNT

    msg = await budget_service.set_budget(update.effective_user.id, category, amount)
    await update.message.reply_text(msg)
    return ConversationHandler.END


async def _budget_cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ تم الإلغاء.")
    return ConversationHandler.END


# Build ConversationHandler with TWO entry points
budget_set_conversation = ConversationHandler(
    entry_points=[
        CommandHandler("setbudget", budget_set_entry_cmd),
        CallbackQueryHandler(budget_set_entry_btn, pattern="^budgetaction_set$"),
    ],
    states={
        BUDGET_CAT: [
            CallbackQueryHandler(budget_set_cat_selected, pattern=r"^budgetsetconv_"),
            CallbackQueryHandler(_budget_cancel_conv, pattern="^cancel_budget$"),
        ],
        BUDGET_AMOUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, budget_set_amount_entered),
        ],
    },
    fallbacks=[CallbackQueryHandler(_budget_cancel_conv, pattern="^cancel_budget$")],
    per_message=False,
)

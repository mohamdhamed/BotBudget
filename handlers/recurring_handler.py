"""
handlers/recurring_handler.py
------------------------------
Handles recurring payment interactions with inline keyboards.
- /recurring → list with action buttons per payment
- /add_recurring → ConversationHandler (name → amount → frequency → confirm)
- /delete_recurring → inline picker
"""

from datetime import date, timedelta
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

from services.recurring_service import RecurringService
from security.auth import authorized_only, is_premium, FREE_RECURRING_LIMIT, upgrade_prompt_keyboard
from security.rate_limiter import rate_limited
from utils.logger import get_logger

logger = get_logger(__name__)
recurring_service = RecurringService()

_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

_FREQ_AR = {"daily": "يومي", "weekly": "أسبوعي", "monthly": "شهري", "yearly": "سنوي"}
_FREQ_BUTTONS = [
    ("يومي", "daily"),
    ("أسبوعي", "weekly"),
    ("شهري", "monthly"),
    ("سنوي", "yearly"),
]

# ConversationHandler states
ADD_NAME, ADD_AMOUNT, ADD_FREQ, ADD_CONFIRM = range(4)


# ══════════════════════════════════════════════════════════
# /recurring — list with per-payment action buttons
# ══════════════════════════════════════════════════════════

@authorized_only
@rate_limited
async def recurring_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all recurring payments with action buttons."""
    user = update.effective_user
    payments = await recurring_service.repo.get_all(user.id, active_only=False)

    if not payments:
        await update.message.reply_text(
            "📭 مفيش مدفوعات متكررة مسجلة.\n\nاضغط /add\\_recurring لإضافة دفعة جديدة.",
            parse_mode="Markdown",
        )
        return

    total_monthly = 0.0
    lines = ["🔁 *المدفوعات المتكررة:*\n"]

    for p in payments:
        status = "✅" if p.active else "⏸️"
        freq = _FREQ_AR.get(p.frequency, p.frequency)
        lines.append(
            f"  {status} *#{p.id}* {p.name}\n"
            f"      💶 {p.amount:.2f}€ ({freq}) — القادم: {p.next_due_date}"
        )
        if p.active and p.frequency == "monthly":
            total_monthly += p.amount
        elif p.active and p.frequency == "weekly":
            total_monthly += p.amount * 4.33
        elif p.active and p.frequency == "daily":
            total_monthly += p.amount * 30
        elif p.active and p.frequency == "yearly":
            total_monthly += p.amount / 12

    if total_monthly > 0:
        lines.append(f"\n💶 *إجمالي الالتزامات الشهرية (تقريبي): {total_monthly:.2f}€*")

    # Per-payment action buttons
    buttons = []
    for p in payments:
        toggle_label = "⏸️ إيقاف" if p.active else "▶️ تفعيل"
        buttons.append([
            InlineKeyboardButton(f"🗑️ حذف #{p.id}", callback_data=f"recdel_{p.id}"),
            InlineKeyboardButton(f"{toggle_label} #{p.id}", callback_data=f"rectoggle_{p.id}"),
        ])
    buttons.append([InlineKeyboardButton("➕ إضافة دفعة جديدة → /add_recurring", callback_data="rec_add_hint")])

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown",
    )


async def handle_rec_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirm then delete a recurring payment."""
    query = update.callback_query
    await query.answer()
    payment_id = int(query.data.split("_")[1])

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ تأكيد الحذف", callback_data=f"recdelok_{payment_id}"),
        InlineKeyboardButton("❌ إلغاء", callback_data="rec_cancel"),
    ]])
    await query.edit_message_text(
        f"⚠️ تأكيد حذف الدفعة المتكررة #{payment_id}؟",
        reply_markup=keyboard,
    )


async def handle_rec_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Execute recurring payment deletion."""
    query = update.callback_query
    await query.answer()
    payment_id = int(query.data.split("_")[1])
    msg = await recurring_service.delete_payment(payment_id, update.effective_user.id)
    await query.edit_message_text(msg)


async def handle_rec_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle active/paused for a recurring payment."""
    query = update.callback_query
    await query.answer()
    payment_id = int(query.data.split("_")[1])

    # Get current state to toggle
    payment = await recurring_service.repo.get_by_id(payment_id, update.effective_user.id)
    if not payment:
        await query.edit_message_text(f"⚠️ الدفعة #{payment_id} مش موجودة.")
        return

    new_state = not payment.active
    msg = await recurring_service.toggle_payment(payment_id, update.effective_user.id, new_state)
    await query.edit_message_text(msg + "\n\nاضغط /recurring لعرض القائمة المحدثة.")


async def handle_rec_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ تم الإلغاء.")


async def handle_rec_add_hint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("اكتب /add_recurring لإضافة دفعة جديدة", show_alert=True)


# ══════════════════════════════════════════════════════════
# /delete_recurring — inline picker (backwards compatible with ID)
# ══════════════════════════════════════════════════════════

@authorized_only
@rate_limited
async def delete_recurring_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show active payments as buttons or delete by ID."""
    user = update.effective_user

    # Support old syntax: /delete_recurring 3
    if context.args:
        try:
            payment_id = int(context.args[0])
            msg = await recurring_service.delete_payment(payment_id, user.id)
            await update.message.reply_text(msg)
            return
        except ValueError:
            pass

    payments = await recurring_service.repo.get_all(user.id, active_only=False)
    if not payments:
        await update.message.reply_text("📭 مفيش مدفوعات متكررة مسجلة.")
        return

    buttons = []
    for p in payments:
        status = "✅" if p.active else "⏸️"
        label = f"{status} #{p.id} | {p.name} | {p.amount:.0f}€"
        buttons.append([InlineKeyboardButton(label, callback_data=f"recdel_{p.id}")])
    buttons.append([InlineKeyboardButton("❌ إلغاء", callback_data="rec_cancel")])

    await update.message.reply_text(
        "🗑️ اختار الدفعة المتكررة اللي عايز تحذفها:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# ══════════════════════════════════════════════════════════
# /add_recurring — ConversationHandler (name → amount → freq → confirm)
# ══════════════════════════════════════════════════════════

@authorized_only
@rate_limited
async def add_recurring_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: ask for payment name."""
    user_id = update.effective_user.id
    if not await is_premium(user_id):
        existing = await recurring_service.repo.get_all(user_id, active_only=False)
        if len(existing) >= FREE_RECURRING_LIMIT:
            await update.message.reply_text(
                f"🔒 <b>الحد الأقصى للمدفوعات المتكررة المجانية ({FREE_RECURRING_LIMIT})</b>\n\n"
                f"✨ ترقّي لـ Premium لإضافة مدفوعات متكررة بلا حدود.",
                reply_markup=upgrade_prompt_keyboard(),
                parse_mode="HTML",
            )
            return ConversationHandler.END

    if context.args and "|" in " ".join(context.args):
        text = " ".join(context.args)
        return await _handle_pipe_format(update, text)

    await update.message.reply_text("📝 *إضافة دفعة متكررة*\n\nاكتب اسم الدفعة (مثلاً: نتفليكس، إيجار):", parse_mode="Markdown")
    return ADD_NAME


async def add_name_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store name and ask for amount."""
    name = update.message.text.strip()
    if not name or len(name) > 100:
        await update.message.reply_text("⚠️ اكتب اسم صحيح (أقل من 100 حرف):")
        return ADD_NAME

    context.user_data["rec_name"] = name
    await update.message.reply_text(f"📌 *{name}*\n\n💶 اكتب المبلغ:", parse_mode="Markdown")
    return ADD_AMOUNT


async def add_amount_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store amount and show frequency buttons."""
    value = update.message.text.strip().translate(_AR_DIGITS)
    try:
        amount = float(value)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ اكتب مبلغ صحيح (رقم أكبر من 0):")
        return ADD_AMOUNT

    context.user_data["rec_amount"] = amount

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("يومي", callback_data="recfreq_daily"),
            InlineKeyboardButton("أسبوعي", callback_data="recfreq_weekly"),
        ],
        [
            InlineKeyboardButton("شهري", callback_data="recfreq_monthly"),
            InlineKeyboardButton("سنوي", callback_data="recfreq_yearly"),
        ],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_recconv")],
    ])
    await update.message.reply_text(
        f"📌 {context.user_data['rec_name']} — {amount:.2f}€\n\n🔄 اختار التكرار:",
        reply_markup=keyboard,
    )
    return ADD_FREQ


async def add_freq_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store frequency and show confirmation."""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_recconv":
        await query.edit_message_text("✅ تم الإلغاء.")
        return ConversationHandler.END

    frequency = query.data.split("_")[1]
    context.user_data["rec_freq"] = frequency

    # Calculate next due date
    today = date.today()
    due_map = {
        "daily": today + timedelta(days=1),
        "weekly": today + timedelta(weeks=1),
        "monthly": today + relativedelta(months=1, day=1),
        "yearly": today + relativedelta(years=1),
    }
    next_due = due_map[frequency]
    context.user_data["rec_due"] = next_due.isoformat()

    name = context.user_data["rec_name"]
    amount = context.user_data["rec_amount"]
    freq_ar = _FREQ_AR[frequency]

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ تأكيد", callback_data="recconfirm_yes"),
        InlineKeyboardButton("❌ إلغاء", callback_data="cancel_recconv"),
    ]])
    await query.edit_message_text(
        f"🔁 *تأكيد الدفعة المتكررة:*\n\n"
        f"  📌 الاسم: {name}\n"
        f"  💶 المبلغ: {amount:.2f}€\n"
        f"  🔄 التكرار: {freq_ar}\n"
        f"  📅 الموعد القادم: {next_due}",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    return ADD_CONFIRM


async def add_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save the recurring payment."""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_recconv":
        await query.edit_message_text("✅ تم الإلغاء.")
        return ConversationHandler.END

    result = await recurring_service.add_manual(
        user_id=update.effective_user.id,
        name=context.user_data["rec_name"],
        amount=context.user_data["rec_amount"],
        frequency=context.user_data["rec_freq"],
        next_due_date=date.fromisoformat(context.user_data["rec_due"]),
    )

    if result.get("success"):
        await query.edit_message_text(result["message"])
    else:
        await query.edit_message_text(f"⚠️ {result.get('question', 'حصل مشكلة.')}")

    return ConversationHandler.END


async def _cancel_recconv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ تم الإلغاء.")
    return ConversationHandler.END


async def _handle_pipe_format(update: Update, text: str) -> int:
    """Handle old pipe format for backwards compatibility: الاسم | المبلغ | التكرار"""
    import re
    parts = [p.strip() for p in text.split("|")]
    if len(parts) < 3:
        await update.message.reply_text("⚠️ صيغة غير صحيحة. اكتب /add_recurring وتابع الخطوات.")
        return ConversationHandler.END

    freq_map = {
        "يومي": "daily", "يوم": "daily", "daily": "daily",
        "أسبوعي": "weekly", "اسبوعي": "weekly", "weekly": "weekly",
        "شهري": "monthly", "شهر": "monthly", "monthly": "monthly",
        "سنوي": "yearly", "سنة": "yearly", "yearly": "yearly",
    }

    name = parts[0]
    amount_str = re.sub(r"[^\d.]", "", parts[1].translate(_AR_DIGITS))
    try:
        amount = float(amount_str)
    except ValueError:
        await update.message.reply_text("⚠️ المبلغ مش صحيح.")
        return ConversationHandler.END

    frequency = freq_map.get(parts[2].strip().lower())
    if not frequency:
        await update.message.reply_text("⚠️ التكرار مش معروف. استخدم: يومي، أسبوعي، شهري، سنوي")
        return ConversationHandler.END

    today = date.today()
    due_map = {
        "daily": today + timedelta(days=1),
        "weekly": today + timedelta(weeks=1),
        "monthly": today + relativedelta(months=1, day=1),
        "yearly": today + relativedelta(years=1),
    }
    next_due = due_map[frequency]

    if len(parts) >= 4 and parts[3].strip():
        try:
            next_due = date.fromisoformat(parts[3].strip())
        except ValueError:
            pass

    result = await recurring_service.add_manual(
        user_id=update.effective_user.id,
        name=name, amount=amount,
        frequency=frequency, next_due_date=next_due,
    )

    if result.get("success"):
        await update.message.reply_text(result["message"])
    else:
        await update.message.reply_text(f"⚠️ {result.get('question', 'حصل مشكلة.')}")

    return ConversationHandler.END


# Build the add_recurring ConversationHandler
add_recurring_conversation = ConversationHandler(
    entry_points=[CommandHandler("add_recurring", add_recurring_entry)],
    states={
        ADD_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_name_entered),
        ],
        ADD_AMOUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_amount_entered),
        ],
        ADD_FREQ: [
            CallbackQueryHandler(add_freq_selected, pattern=r"^recfreq_"),
            CallbackQueryHandler(_cancel_recconv, pattern="^cancel_recconv$"),
        ],
        ADD_CONFIRM: [
            CallbackQueryHandler(add_confirmed, pattern=r"^recconfirm_"),
            CallbackQueryHandler(_cancel_recconv, pattern="^cancel_recconv$"),
        ],
    },
    fallbacks=[CallbackQueryHandler(_cancel_recconv, pattern="^cancel_recconv$")],
    per_message=False,
)

"""
handlers/recurring_handler.py
------------------------------
Handles recurring payment interactions.
Supports both structured commands (no AI) and AI-parsed text.
"""

import re
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from telegram import Update
from telegram.ext import ContextTypes

from services.recurring_service import RecurringService
from security.auth import authorized_only
from security.rate_limiter import rate_limited
from utils.logger import get_logger

logger = get_logger(__name__)
recurring_service = RecurringService()

# Arabic/English number conversion
_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

# Frequency mapping
_FREQ_MAP = {
    "يومي": "daily", "يوم": "daily", "daily": "daily",
    "أسبوعي": "weekly", "اسبوعي": "weekly", "أسبوع": "weekly", "weekly": "weekly",
    "شهري": "monthly", "شهر": "monthly", "monthly": "monthly",
    "سنوي": "yearly", "سنة": "yearly", "yearly": "yearly",
}


def _calc_next_due(frequency: str) -> date:
    """Calculate the next due date based on frequency."""
    today = date.today()
    if frequency == "daily":
        return today + timedelta(days=1)
    elif frequency == "weekly":
        return today + timedelta(weeks=1)
    elif frequency == "monthly":
        return today + relativedelta(months=1, day=1)
    elif frequency == "yearly":
        return today + relativedelta(years=1)
    return today + relativedelta(months=1, day=1)


def _parse_manual(text: str) -> dict | None:
    """
    Try to parse structured recurring format:
      الاسم | المبلغ | التكرار
    Example:
      نتفليكس | 15 | شهري
      إيجار الشقة | 800 | شهري
    """
    parts = [p.strip() for p in text.split("|")]
    if len(parts) < 3:
        return None

    name = parts[0]
    
    # Parse amount (support Arabic digits)
    amount_str = parts[1].translate(_AR_DIGITS)
    amount_str = re.sub(r"[^\d.]", "", amount_str)
    if not amount_str:
        return None
    
    try:
        amount = float(amount_str)
    except ValueError:
        return None

    # Parse frequency
    freq_input = parts[2].strip().lower()
    frequency = _FREQ_MAP.get(freq_input)
    if not frequency:
        return None

    # Optional: parse date from 4th part
    next_due = None
    if len(parts) >= 4 and parts[3].strip():
        try:
            next_due = date.fromisoformat(parts[3].strip())
        except ValueError:
            pass

    if next_due is None:
        next_due = _calc_next_due(frequency)

    return {
        "name": name,
        "amount": amount,
        "frequency": frequency,
        "next_due_date": next_due,
    }


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
    Handle /add_recurring - add a new recurring payment.

    Structured format (no AI):
        /add_recurring الاسم | المبلغ | التكرار
        /add_recurring الاسم | المبلغ | التكرار | التاريخ

    Examples:
        /add_recurring نتفليكس | 15 | شهري
        /add_recurring إيجار | 800 | شهري | 2026-03-01
        /add_recurring تأمين السيارة | 600 | سنوي
    """
    user = update.effective_user

    if not context.args:
        await update.message.reply_text(
            "📝 *إضافة دفعة متكررة*\n\n"
            "*الصيغة:*\n"
            "`/add_recurring الاسم | المبلغ | التكرار`\n\n"
            "*أمثلة:*\n"
            "• `/add_recurring نتفليكس | 15 | شهري`\n"
            "• `/add_recurring إيجار | 800 | شهري`\n"
            "• `/add_recurring تأمين | 600 | سنوي`\n"
            "• `/add_recurring نت | 30 | شهري | 2026-03-01`\n\n"
            "*التكرار:* يومي، أسبوعي، شهري، سنوي",
            parse_mode="Markdown",
        )
        return

    text = " ".join(context.args)
    parsed = _parse_manual(text)

    if parsed:
        # Direct structured command → no AI needed
        result = recurring_service.add_manual(
            user_id=user.id,
            name=parsed["name"],
            amount=parsed["amount"],
            frequency=parsed["frequency"],
            next_due_date=parsed["next_due_date"],
        )
    else:
        # Fallback to AI parsing
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

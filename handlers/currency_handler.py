"""
handlers/currency_handler.py
------------------------------
Handles /currency command — lets users set their preferred currency.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

from repositories.user_repo import UserRepository
from security.auth import authorized_only
from security.rate_limiter import rate_limited
from utils.logger import get_logger

logger = get_logger(__name__)
user_repo = UserRepository()

SUPPORTED_CURRENCIES = {
    "EUR": "يورو 🇪🇺",
    "USD": "دولار أمريكي 🇺🇸",
    "GBP": "جنيه إسترليني 🇬🇧",
    "EGP": "جنيه مصري 🇪🇬",
    "SAR": "ريال سعودي 🇸🇦",
    "AED": "درهم إماراتي 🇦🇪",
    "KWD": "دينار كويتي 🇰🇼",
    "QAR": "ريال قطري 🇶🇦",
    "JOD": "دينار أردني 🇯🇴",
    "MAD": "درهم مغربي 🇲🇦",
}


def _build_keyboard(current: str) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for code, label in SUPPORTED_CURRENCIES.items():
        check = " ✅" if code == current else ""
        row.append(InlineKeyboardButton(f"{code}{check}", callback_data=f"setcur_{code}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


@authorized_only
@rate_limited
async def currency_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db_user = await user_repo.get_by_telegram_id(user.id)
    current = db_user["currency"] if db_user else "EUR"
    label = SUPPORTED_CURRENCIES.get(current, current)

    await update.message.reply_text(
        f"💱 <b>اختر عملتك الافتراضية</b>\n\n"
        f"العملة الحالية: <b>{current} — {label}</b>\n\n"
        f"العملة دي بتتحسب تلقائياً لأي معاملة ما بتذكرش فيها العملة.\n"
        f"لو ذكرت عملة في الرسالة (مثلاً: 50 دولار) هيتسجل بيها.",
        parse_mode="HTML",
        reply_markup=_build_keyboard(current),
    )


async def currency_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    code = query.data.replace("setcur_", "")
    if code not in SUPPORTED_CURRENCIES:
        await query.answer("عملة غير مدعومة.", show_alert=True)
        return

    user_id = query.from_user.id
    success = await user_repo.set_currency(user_id, code)

    if success:
        label = SUPPORTED_CURRENCIES[code]
        await query.edit_message_text(
            f"✅ تم تغيير عملتك الافتراضية إلى:\n\n"
            f"<b>{code} — {label}</b>\n\n"
            f"كل معاملة جديدة هتتسجل بالعملة دي تلقائياً.",
            parse_mode="HTML",
        )
        logger.info(f"User {user_id} set currency to {code}")
    else:
        await query.edit_message_text("⚠️ حصل مشكلة. حاول تاني.")

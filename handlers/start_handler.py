"""
handlers/start_handler.py
--------------------------
Handles /start and /help commands.
Registers the user and shows available commands.
"""

from telegram import Update
from telegram.ext import ContextTypes

from repositories.user_repo import UserRepository
from security.auth import authorized_only
from security.rate_limiter import rate_limited
from utils.logger import get_logger

logger = get_logger(__name__)
user_repo = UserRepository()

HELP_TEXT = """
🤖 *أهلاً بيك في BotBudget!*
بوتك الشخصي لإدارة المصاريف 💶

*📝 تسجيل المعاملات:*
اكتب أي جملة طبيعية وأنا هافهمها:
• "صرفت ٥٠ يورو سوبرماركت"
• "جالي راتب ٢٠٠٠ يورو"
• "دفعت إيجار ٨٠٠"

*🔧 الأوامر المتاحة:*
/start - بدء البوت
/help - عرض المساعدة
/today - ملخص النهاردة
/month - ملخص الشهر ده
/recurring - عرض المدفوعات المتكررة
/add\\_recurring - إضافة دفعة متكررة
/export\\_csv - تصدير بيانات الشهر CSV
/export\\_excel - تصدير بيانات الشهر Excel
/delete - حذف عملية (مثال: /delete 5)
/delete\\_recurring - حذف دفعة متكررة
/myid - عرض رقم حسابك (Telegram ID)
"""


@authorized_only
@rate_limited
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - register user and show welcome message."""
    user = update.effective_user
    user_repo.ensure_user(user.id, user.first_name)
    logger.info(f"User {user.id} ({user.first_name}) started the bot.")

    await update.message.reply_text(
        f"مرحباً {user.first_name}! 👋\n"
        f"أنا بوتك الشخصي لإدارة المصاريف.\n"
        f"اكتب أي معاملة مالية وأنا هاسجلها ليك.\n\n"
        f"اكتب /help لعرض كل الأوامر المتاحة.",
        parse_mode="Markdown",
    )


@authorized_only
@rate_limited
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command - show all available commands."""
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")


@authorized_only
async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /myid command - show user's Telegram ID for whitelisting."""
    user = update.effective_user
    await update.message.reply_text(
        f"🆔 رقم حسابك: `{user.id}`\n"
        f"ضيف الرقم ده في `ALLOWED_USER_IDS` في ملف `.env` لتأمين البوت.",
        parse_mode="Markdown",
    )

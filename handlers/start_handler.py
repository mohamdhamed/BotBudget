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

*📊 التقارير:*
/today - ملخص النهاردة
/week - ملخص آخر ٧ أيام
/month - ملخص الشهر
/balance - الرصيد الكلي
/last - آخر ١٠ معاملات
/category - عرض حسب الفئة
/compare - مقارنة بين شهرين
/search - بحث في المعاملات
/report - تقرير لفترة محددة

*✏️ التعديل والحذف:*
/edit - تعديل معاملة (اختر من القائمة)
/delete - حذف معاملة (اختر من القائمة)
/undo - إلغاء آخر معاملة

*💰 الميزانية:*
/budget - عرض وتحديد الميزانية

*🔁 المدفوعات المتكررة:*
/recurring - عرض المدفوعات المتكررة
/add\\_recurring - إضافة دفعة متكررة
/delete\\_recurring - حذف دفعة متكررة

*📈 الرسوم البيانية:*
/chart - رسم بياني شهري
/chart\\_week - رسم بياني أسبوعي

*📄 التصدير:*
/export\\_csv - تصدير CSV
/export\\_excel - تصدير Excel

*🔧 أخرى:*
/myid - رقم حسابك على تيليجرام
/help - عرض المساعدة
"""


@authorized_only
@rate_limited
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - register user and show welcome message."""
    user = update.effective_user
    await user_repo.ensure_user(user.id, user.first_name)
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


async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /myid command - open to all users so they can get their ID for whitelisting."""
    user = update.effective_user
    await update.message.reply_text(
        f"🆔 رقم حسابك على تيليجرام:\n\n`{user.id}`\n\n"
        f"شارك الرقم ده مع مشرف البوت عشان يضيفك.",
        parse_mode="Markdown",
    )

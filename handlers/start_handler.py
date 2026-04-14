"""
handlers/start_handler.py
--------------------------
Handles /start, /help, /myid, /upgrade_info, and /plan commands.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from repositories.user_repo import UserRepository
from repositories.subscription_repo import SubscriptionRepository
from security.auth import authorized_only, FREE_MONTHLY_LIMIT
from security.rate_limiter import rate_limited
from utils.logger import get_logger

logger = get_logger(__name__)
user_repo = UserRepository()
sub_repo = SubscriptionRepository()

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
/plan - خطتك الحالية
/upgrade\\_info - معلومات الترقية
/myid - رقم حسابك على تيليجرام
/help - عرض المساعدة
"""

ONBOARDING_TEXT = """
🎉 *مرحباً {name}! أهلاً بيك في BotBudget*

بوتك الشخصي لإدارة المصاريف بالذكاء الاصطناعي 🤖💶

*كل اللي عليك تعمله:*
اكتب معاملتك بشكل طبيعي وأنا هافهمها:

• "صرفت ٥٠ سوبرماركت"
• "جالي راتب ٣٠٠٠"
• "١٠٠ بنزين"

*خطتك الحالية:* 🆓 مجانية ({limit} معاملة/شهر)
ترقّي لـ Premium لمعاملات بلا حدود! → /upgrade\\_info

*ابدأ دلوقتي:* اكتب أول معاملة! ✍️
أو اكتب /help لكل الأوامر.
"""


@authorized_only
@rate_limited
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — register user and show onboarding or welcome."""
    user = update.effective_user
    await user_repo.ensure_user(user.id, user.first_name)
    await sub_repo.ensure_free(user.id)
    logger.info(f"User {user.id} ({user.first_name}) started the bot.")

    # Check if returning user
    plan_info = await sub_repo.get_plan(user.id)
    count = await sub_repo.count_month_transactions(user.id)

    if count > 0:
        # Returning user
        plan_label = "🌟 مميزة" if plan_info["is_premium"] else "🆓 مجانية"
        await update.message.reply_text(
            f"مرحباً مجدداً {user.first_name}! 👋\n\n"
            f"📊 خطتك: {plan_label}\n"
            f"📝 معاملات هذا الشهر: {count}\n\n"
            f"اكتب معاملتك أو /help للمساعدة.",
            parse_mode="Markdown",
        )
    else:
        # New user — show onboarding
        await update.message.reply_text(
            ONBOARDING_TEXT.format(name=user.first_name, limit=FREE_MONTHLY_LIMIT),
            parse_mode="Markdown",
        )


@authorized_only
@rate_limited
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")


async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(
        f"🆔 رقم حسابك على تيليجرام:\n\n`{user.id}`\n\n"
        f"شارك الرقم ده مع مشرف البوت لو محتاج مساعدة.",
        parse_mode="Markdown",
    )


@authorized_only
@rate_limited
async def plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /plan — show current plan details."""
    user = update.effective_user
    plan_info = await sub_repo.get_plan(user.id)
    count = await sub_repo.count_month_transactions(user.id)

    if plan_info["is_premium"]:
        expires = plan_info["expires_at"].strftime("%Y-%m-%d") if plan_info["expires_at"] else "—"
        await update.message.reply_text(
            f"🌟 *خطتك: مميزة (Premium)*\n\n"
            f"✨ معاملات بلا حدود\n"
            f"📅 تنتهي: {expires}\n"
            f"📝 معاملات هذا الشهر: {count}",
            parse_mode="Markdown",
        )
    else:
        remaining = max(0, FREE_MONTHLY_LIMIT - count)
        await update.message.reply_text(
            f"🆓 *خطتك: مجانية (Free)*\n\n"
            f"📝 معاملات هذا الشهر: {count}/{FREE_MONTHLY_LIMIT}\n"
            f"📊 متبقي: {remaining} معاملة\n\n"
            f"🌟 ترقّي للخطة المميزة! → /upgrade\\_info",
            parse_mode="Markdown",
        )


@authorized_only
@rate_limited
async def upgrade_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /upgrade_info — show premium plan details and how to subscribe."""
    await update.message.reply_text(
        "🌟 *الخطة المميزة (Premium)*\n\n"
        "*المميزات:*\n"
        "  ✅ معاملات بلا حدود\n"
        "  ✅ تقارير متقدمة\n"
        "  ✅ رسوم بيانية\n"
        "  ✅ تصدير Excel/CSV\n"
        "  ✅ مدفوعات متكررة\n"
        "  ✅ تنبيهات الميزانية\n"
        "  ✅ دعم أولوية\n\n"
        "*الخطة المجانية:*\n"
        f"  📊 {FREE_MONTHLY_LIMIT} معاملة/شهر فقط\n\n"
        "*للاشتراك:*\n"
        "تواصل مع المشرف واختار مدة الاشتراك:\n"
        "  • شهري\n"
        "  • 3 أشهر\n"
        "  • سنوي (أوفر)\n\n"
        "📩 للاشتراك تواصل: @BotBudgetSupport",
        parse_mode="Markdown",
    )

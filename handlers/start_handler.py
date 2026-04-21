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
/insights - تحليل ذكي وتوقعات مالية

*📄 التصدير:*
/export\\_csv - تصدير CSV
/export\\_excel - تصدير Excel

*🔧 أخرى:*
/currency - تغيير العملة الافتراضية
/plan - خطتك الحالية
/upgrade\\_info - معلومات الترقية
/about - عن البوت
/terms - شروط الاستخدام
/privacy - سياسة الخصوصية
/myid - رقم حسابك
/help - عرض المساعدة
"""

TRIAL_DAYS = 7

ONBOARDING_TEXT = """
🎉 *مرحباً {name}! أهلاً بيك في BotBudget*

بوتك الشخصي لإدارة المصاريف بالذكاء الاصطناعي 🤖💶

🎁 *هدية الترحيب:* تجربة Premium مجاناً لمدة {trial} أيام!
  ✨ معاملات + ميزانيات بلا حدود
  ✨ كل الرسوم البيانية والتحليلات
  ✨ تصدير Excel / CSV
  ✨ المقارنات والتقارير المخصصة

*كل اللي عليك تعمله:*
اكتب معاملتك بشكل طبيعي وأنا هافهمها:

• "صرفت ٥٠ سوبرماركت"
• "جالي راتب ٣٠٠٠ دولار"
• "١٠٠ بنزين"

💱 اختر عملتك الافتراضية: /currency
📋 اعرف تفاصيل الخطط: /upgrade\\_info

*ابدأ دلوقتي:* اكتب أول معاملة! ✍️
أو اكتب /help لكل الأوامر.
"""


@authorized_only
@rate_limited
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — register user and show onboarding or welcome."""
    user = update.effective_user
    # User registration + trial already handled by @authorized_only
    trial_granted = context.user_data.get("_trial_just_granted", False)
    logger.info(f"User {user.id} ({user.first_name}) started the bot. Trial granted: {trial_granted}")

    plan_info = await sub_repo.get_plan(user.id)
    count = await sub_repo.count_month_transactions(user.id)

    if trial_granted:
        await update.message.reply_text(
            ONBOARDING_TEXT.format(name=user.first_name, trial=TRIAL_DAYS),
            parse_mode="Markdown",
        )
        return

    if count > 0:
        plan_label = "🌟 مميزة" if plan_info["is_premium"] else "🆓 مجانية"
        extra = ""
        if plan_info["is_premium"] and plan_info.get("expires_at"):
            extra = f"\n📅 تنتهي: {plan_info['expires_at'].strftime('%Y-%m-%d')}"
        await update.message.reply_text(
            f"مرحباً مجدداً {user.first_name}! 👋\n\n"
            f"📊 خطتك: {plan_label}{extra}\n"
            f"📝 معاملات هذا الشهر: {count}\n\n"
            f"اكتب معاملتك أو /help للمساعدة.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            ONBOARDING_TEXT.format(name=user.first_name, trial=TRIAL_DAYS),
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
            f"📊 متبقي: {remaining} معاملة\n"
            f"💰 ميزانية واحدة + دفعتين متكررتين\n\n"
            f"🔒 *مميزات Premium:*\n"
            f"  • /chart و /chart\\_week — رسوم بيانية\n"
            f"  • /insights — تحليل ذكي\n"
            f"  • /compare و /report\n"
            f"  • /export\\_csv و /export\\_excel\n"
            f"  • التقرير الأسبوعي التلقائي\n\n"
            f"🌟 ترقّي الآن → /upgrade\\_info",
            parse_mode="Markdown",
        )


UPGRADE_INFO_TEXT = (
    "🌟 *الخطة المميزة (Premium)*\n\n"
    "*مميزات إضافية:*\n"
    "  ✅ معاملات بلا حدود (بدل 30/شهر)\n"
    "  ✅ ميزانيات لكل الفئات (بدل 1)\n"
    "  ✅ مدفوعات متكررة بلا حدود (بدل 2)\n"
    "  ✅ الرسوم البيانية (شهري + أسبوعي)\n"
    "  ✅ التحليل الذكي /insights\n"
    "  ✅ تصدير Excel و CSV\n"
    "  ✅ المقارنة الشهرية /compare\n"
    "  ✅ التقارير المخصصة /report\n"
    "  ✅ التقرير الأسبوعي التلقائي\n"
    "  ✅ دعم أولوي\n\n"
    "🎁 *تجربة مجانية 7 أيام لكل مستخدم جديد!*\n\n"
    "*الخطة المجانية:*\n"
    f"  📊 {FREE_MONTHLY_LIMIT} معاملة/شهر\n"
    "  📊 ميزانية واحدة + دفعتين متكررتين\n"
    "  📊 التقارير الأساسية + التنبيه اليومي\n\n"
    "*الأسعار:*\n"
    "  💵 شهري: $3/شهر\n"
    "  💵 سنوي: $20/سنة (وفّر 44%!)\n\n"
    "*للاشتراك:*\n"
    "📩 تواصل: @BotBudgetSupport\n"
    "💳 طرق الدفع: تحويل بنكي، PayPal، فودافون كاش"
)


async def handle_show_upgrade_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback for the 'show_upgrade_info' inline button."""
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(UPGRADE_INFO_TEXT, parse_mode="Markdown")


@authorized_only
@rate_limited
async def upgrade_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /upgrade_info — show premium plan details and how to subscribe."""
    await update.message.reply_text(UPGRADE_INFO_TEXT, parse_mode="Markdown")

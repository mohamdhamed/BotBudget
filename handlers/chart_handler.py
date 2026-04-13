"""
handlers/chart_handler.py
--------------------------
Handles chart generation commands.
Delegates to ChartService and sends images to the user.
"""

from telegram import Update
from telegram.ext import ContextTypes

from services.chart_service import ChartService
from security.auth import authorized_only
from security.rate_limiter import rate_limited
from utils.logger import get_logger

logger = get_logger(__name__)
chart_service = ChartService()


@authorized_only
@rate_limited
async def chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /chart command - send a pie chart of monthly expenses.

    Usage:
        /chart        → current month
        /chart 1      → January current year
        /chart 12 2025 → December 2025
    """
    user = update.effective_user
    year, month = None, None

    if context.args:
        try:
            month = int(context.args[0])
            if len(context.args) >= 2:
                year = int(context.args[1])
        except ValueError:
            await update.message.reply_text("⚠️ الاستخدام: /chart [شهر] [سنة]")
            return

    await update.message.reply_text("📊 جاري إنشاء الرسم البياني...")

    buf = await chart_service.generate_monthly_pie(user.id, year, month)
    if buf:
        await update.message.reply_photo(photo=buf, caption="📊 توزيع المصاريف حسب الفئة")
    else:
        await update.message.reply_text("📭 مفيش مصاريف مسجلة في الفترة دي.")


@authorized_only
@rate_limited
async def chart_week_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /chart_week command - send a bar chart of daily expenses for last 7 days."""
    user = update.effective_user

    await update.message.reply_text("📈 جاري إنشاء الرسم البياني...")

    buf = await chart_service.generate_weekly_bar(user.id)
    if buf:
        await update.message.reply_photo(photo=buf, caption="📈 المصاريف اليومية - آخر ٧ أيام")
    else:
        await update.message.reply_text("📭 مفيش مصاريف في آخر ٧ أيام.")

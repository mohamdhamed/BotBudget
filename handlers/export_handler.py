"""
handlers/export_handler.py
---------------------------
Handles data export commands (CSV, Excel).
Delegates to ExportService.
"""

from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

from services.export_service import ExportService
from security.auth import authorized_only, premium_only
from security.rate_limiter import rate_limited
from utils.logger import get_logger

logger = get_logger(__name__)
export_service = ExportService()


@authorized_only
@premium_only("تصدير CSV")
@rate_limited
async def export_csv_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /export_csv command - send current month's data as CSV.
    Optional: /export_csv 2026 1 (for January 2026).
    """
    user = update.effective_user
    today = date.today()

    year = today.year
    month = today.month

    if context.args and len(context.args) >= 2:
        try:
            year = int(context.args[0])
            month = int(context.args[1])
        except ValueError:
            await update.message.reply_text("⚠️ الاستخدام: /export_csv [سنة شهر]\nمثال: /export_csv 2026 1")
            return

    await update.message.reply_text("📄 جاري تجهيز ملف CSV...")

    try:
        buffer = await export_service.export_month_csv(user.id, year, month)
        filename = f"expenses_{year}_{month:02d}.csv"
        await update.message.reply_document(
            document=buffer,
            filename=filename,
            caption=f"📊 بيانات شهر {month}/{year} - CSV",
        )
    except Exception as e:
        logger.error(f"CSV export failed: {e}")
        await update.message.reply_text("❌ حصل مشكلة في التصدير. حاول تاني.")


@authorized_only
@premium_only("تصدير Excel")
@rate_limited
async def export_excel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /export_excel command - send current month's data as Excel.
    Optional: /export_excel 2026 1 (for January 2026).
    """
    user = update.effective_user
    today = date.today()

    year = today.year
    month = today.month

    if context.args and len(context.args) >= 2:
        try:
            year = int(context.args[0])
            month = int(context.args[1])
        except ValueError:
            await update.message.reply_text("⚠️ الاستخدام: /export_excel [سنة شهر]\nمثال: /export_excel 2026 1")
            return

    await update.message.reply_text("📊 جاري تجهيز ملف Excel...")

    try:
        buffer = await export_service.export_month_excel(user.id, year, month)
        filename = f"expenses_{year}_{month:02d}.xlsx"
        await update.message.reply_document(
            document=buffer,
            filename=filename,
            caption=f"📊 بيانات شهر {month}/{year} - Excel",
        )
    except Exception as e:
        logger.error(f"Excel export failed: {e}")
        await update.message.reply_text("❌ حصل مشكلة في التصدير. حاول تاني.")

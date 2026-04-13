"""
main.py
-------
Entry point for the BotBudget Telegram bot.

Responsibilities:
    - Initialize the database connection pool and schema.
    - Configure and start the Telegram bot with all handlers.
    - Set up the recurring payment reminder scheduler.
"""

from datetime import date, time as dt_time, timedelta

from telegram import BotCommand
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN
from db.connection import init_pool, close_pool
from db.init_db import create_tables
from handlers.start_handler import start_command, help_command, myid_command
from handlers.expense_handler import (
    handle_text_message,
    today_command,
    month_command,
    week_command,
    delete_command,
    edit_command,
    category_command,
    compare_command,
    search_command,
    report_command,
    balance_command,
    last_command,
    undo_command,
    handle_expense_callback,
)
from handlers.recurring_handler import (
    recurring_command,
    add_recurring_command,
    delete_recurring_command,
)
from handlers.export_handler import export_csv_command, export_excel_command
from handlers.chart_handler import chart_command, chart_week_command
from handlers.budget_handler import budget_command
from services.recurring_service import RecurringService
from services.expense_service import ExpenseService
from security.rate_limiter import cleanup_old_rate_limit_logs
from utils.logger import get_logger

logger = get_logger(__name__)


async def send_weekly_report(context) -> None:
    """
    Scheduled job: send weekly expense summary to all users.
    Runs every Sunday at 20:00.
    """
    from config import ALLOWED_USER_IDS
    expense_service = ExpenseService()

    for user_id in ALLOWED_USER_IDS:
        try:
            summary = await expense_service.get_week_summary(user_id)
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📬 *التقرير الأسبوعي*\n\n{summary}",
                parse_mode="Markdown",
            )
            logger.info(f"Sent weekly report to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send weekly report to {user_id}: {e}")


async def send_reminders(context) -> None:
    """
    Scheduled job: check for upcoming recurring payments and send reminders.
    Runs daily at 09:00 AM.
    """
    recurring_service = RecurringService()
    due_payments = await recurring_service.get_due_reminders()

    for payment in due_payments:
        try:
            msg = (
                f"⏰ *تذكير بدفعة قادمة!*\n\n"
                f"📌 {payment.name}\n"
                f"💶 {payment.amount:.2f}€\n"
                f"📅 الموعد: {payment.next_due_date}\n\n"
                f"لا تنسى الدفع! 💪"
            )
            await context.bot.send_message(
                chat_id=payment.user_id,
                text=msg,
                parse_mode="Markdown",
            )
            # Advance the due date for next cycle
            if payment.next_due_date <= date.today():
                await recurring_service.advance_due_date(payment)

            logger.info(f"Sent reminder for '{payment.name}' to user {payment.user_id}")
        except Exception as e:
            logger.error(f"Failed to send reminder for '{payment.name}': {e}")


async def set_bot_commands(application: Application) -> None:
    """Register bot commands menu in Telegram on startup."""
    commands = [
        BotCommand("start", "🚀 بدء البوت"),
        BotCommand("help", "📖 عرض المساعدة"),
        BotCommand("today", "📅 ملخص النهاردة"),
        BotCommand("week", "📆 ملخص آخر ٧ أيام"),
        BotCommand("month", "📊 ملخص الشهر"),
        BotCommand("category", "🏷️ عرض حسب الفئة"),
        BotCommand("edit", "✏️ تعديل معاملة"),
        BotCommand("delete", "🗑️ حذف عملية"),
        BotCommand("recurring", "🔁 المدفوعات المتكررة"),
        BotCommand("add_recurring", "➕ إضافة دفعة متكررة"),
        BotCommand("delete_recurring", "❌ حذف دفعة متكررة"),
        BotCommand("budget", "💰 الميزانية الشهرية"),
        BotCommand("compare", "🔄 مقارنة شهرية"),
        BotCommand("search", "🔍 بحث"),
        BotCommand("report", "📋 تقرير مخصص"),
        BotCommand("balance", "🏦 الرصيد"),
        BotCommand("chart", "📊 رسم بياني شهري"),
        BotCommand("chart_week", "📈 رسم بياني أسبوعي"),
        BotCommand("export_csv", "📄 تصدير CSV"),
        BotCommand("export_excel", "📊 تصدير Excel"),
        BotCommand("myid", "🆔 رقم حسابك"),
        BotCommand("last", "🕓 آخر ٥ معاملات"),
        BotCommand("undo", "↩️ إلغاء آخر معاملة"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands menu registered successfully.")


async def post_init(application: Application) -> None:
    """Initialize database and set bot commands on startup."""
    logger.info("Initializing database...")
    await init_pool()
    await create_tables()
    await set_bot_commands(application)


def main() -> None:
    """Initialize and run the bot."""

    # ── 1. Build the Telegram application ─────────────────
    logger.info("Starting Telegram bot...")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # ── 3. Register command handlers ──────────────────────
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("myid", myid_command))
    app.add_handler(CommandHandler("today", today_command))
    app.add_handler(CommandHandler("week", week_command))
    app.add_handler(CommandHandler("month", month_command))
    app.add_handler(CommandHandler("category", category_command))
    app.add_handler(CommandHandler("edit", edit_command))
    app.add_handler(CommandHandler("delete", delete_command))
    app.add_handler(CommandHandler("recurring", recurring_command))
    app.add_handler(CommandHandler("add_recurring", add_recurring_command))
    app.add_handler(CommandHandler("delete_recurring", delete_recurring_command))
    app.add_handler(CommandHandler("export_csv", export_csv_command))
    app.add_handler(CommandHandler("export_excel", export_excel_command))
    app.add_handler(CommandHandler("chart", chart_command))
    app.add_handler(CommandHandler("chart_week", chart_week_command))
    app.add_handler(CommandHandler("budget", budget_command))
    app.add_handler(CommandHandler("compare", compare_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("last", last_command))
    app.add_handler(CommandHandler("undo", undo_command))

    # ── 4. Register text message handler (catch-all) ──────
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # ── 4b. Register inline keyboard callback handler ─────
    app.add_handler(CallbackQueryHandler(handle_expense_callback, pattern="^(confirm|cancel)_expense$"))

    # ── 5. Schedule jobs ──────────────────────────────────
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_daily(
            send_reminders,
            time=dt_time(hour=9, minute=0),
            name="daily_reminders",
        )
        # Weekly report every Sunday at 20:00
        job_queue.run_daily(
            send_weekly_report,
            time=dt_time(hour=20, minute=0),
            days=(6,),  # Sunday
            name="weekly_report",
        )
        # Hourly cleanup of old rate limit log entries
        job_queue.run_repeating(
            cleanup_old_rate_limit_logs,
            interval=3600,
            first=60,
            name="rate_limit_cleanup",
        )
        logger.info("Scheduled daily reminders (09:00) + weekly report (Sunday 20:00) + rate limit cleanup (hourly)")

    # ── 6. Start polling ──────────────────────────────────
    logger.info("🚀 BotBudget is running! Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True, allowed_updates=["message", "callback_query"])

    # ── 7. Cleanup on shutdown ────────────────────────────
    import asyncio
    asyncio.get_event_loop().run_until_complete(close_pool())
    logger.info("BotBudget stopped.")


if __name__ == "__main__":
    main()

"""
main.py
-------
Entry point for the BotBudget Telegram bot.

Responsibilities:
    - Initialize the database connection pool and schema.
    - Configure and start the Telegram bot with all handlers.
    - Set up the recurring payment reminder scheduler.
"""

import asyncio
from datetime import time as dt_time

from telegram.ext import (
    Application,
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
    delete_command,
)
from handlers.recurring_handler import (
    recurring_command,
    add_recurring_command,
    delete_recurring_command,
)
from handlers.export_handler import export_csv_command, export_excel_command
from services.recurring_service import RecurringService
from utils.logger import get_logger

logger = get_logger(__name__)


async def send_reminders(context) -> None:
    """
    Scheduled job: check for upcoming recurring payments and send reminders.
    Runs daily at 09:00 AM.
    """
    recurring_service = RecurringService()
    due_payments = recurring_service.get_due_reminders()

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
            if payment.next_due_date <= asyncio.get_event_loop().time():
                recurring_service.advance_due_date(payment)

            logger.info(f"Sent reminder for '{payment.name}' to user {payment.user_id}")
        except Exception as e:
            logger.error(f"Failed to send reminder for '{payment.name}': {e}")


def main() -> None:
    """Initialize and run the bot."""

    # ── 1. Database setup ─────────────────────────────────
    logger.info("Initializing database...")
    init_pool()
    create_tables()

    # ── 2. Build the Telegram application ─────────────────
    logger.info("Starting Telegram bot...")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # ── 3. Register command handlers ──────────────────────
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("myid", myid_command))
    app.add_handler(CommandHandler("today", today_command))
    app.add_handler(CommandHandler("month", month_command))
    app.add_handler(CommandHandler("delete", delete_command))
    app.add_handler(CommandHandler("recurring", recurring_command))
    app.add_handler(CommandHandler("add_recurring", add_recurring_command))
    app.add_handler(CommandHandler("delete_recurring", delete_recurring_command))
    app.add_handler(CommandHandler("export_csv", export_csv_command))
    app.add_handler(CommandHandler("export_excel", export_excel_command))

    # ── 4. Register text message handler (catch-all) ──────
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # ── 5. Schedule daily reminders ───────────────────────
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_daily(
            send_reminders,
            time=dt_time(hour=9, minute=0),
            name="daily_reminders",
        )
        logger.info("Scheduled daily reminder job at 09:00 AM.")

    # ── 6. Start polling ──────────────────────────────────
    logger.info("🚀 BotBudget is running! Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)

    # ── 7. Cleanup on shutdown ────────────────────────────
    close_pool()
    logger.info("BotBudget stopped.")


if __name__ == "__main__":
    main()

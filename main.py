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
from handlers.admin_handler import (
    adduser_command, removeuser_command, users_command,
    upgrade_command, downgrade_command, subscribers_command,
)
from handlers.start_handler import start_command, help_command, myid_command, plan_command, upgrade_info_command
from handlers.expense_handler import (
    handle_text_message,
    today_command,
    month_command,
    week_command,
    delete_command,
    category_command,
    search_command,
    report_command,
    balance_command,
    last_command,
    undo_command,
    handle_expense_callback,
    handle_delete_pick,
    handle_delete_confirm,
    handle_category_show,
    handle_cancel_generic,
    edit_conversation,
    compare_conversation,
)
from handlers.recurring_handler import (
    recurring_command,
    delete_recurring_command,
    add_recurring_conversation,
    handle_rec_delete,
    handle_rec_delete_confirm,
    handle_rec_toggle,
    handle_rec_cancel,
    handle_rec_add_hint,
)
from handlers.export_handler import export_csv_command, export_excel_command
from handlers.chart_handler import chart_command, chart_week_command
from handlers.budget_handler import (
    budget_command,
    handle_budget_action,
    handle_budget_delete_cat,
    handle_budget_cancel,
    budget_set_conversation,
)
from repositories.allowed_users_repo import AllowedUsersRepository
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
    """Register bot commands — regular users see normal commands, admins see extra ones."""
    from config import ADMIN_USER_IDS
    from telegram import BotCommandScopeChat

    user_commands = [
        BotCommand("start", "🚀 بدء البوت"),
        BotCommand("help", "📖 عرض المساعدة"),
        BotCommand("myid", "🆔 رقم حسابك"),
        BotCommand("today", "📅 ملخص النهاردة"),
        BotCommand("week", "📆 ملخص آخر ٧ أيام"),
        BotCommand("month", "📊 ملخص الشهر"),
        BotCommand("balance", "🏦 الرصيد"),
        BotCommand("last", "🕓 آخر ١٠ معاملات"),
        BotCommand("undo", "↩️ إلغاء آخر معاملة"),
        BotCommand("category", "🏷️ عرض حسب الفئة"),
        BotCommand("edit", "✏️ تعديل معاملة"),
        BotCommand("delete", "🗑️ حذف عملية"),
        BotCommand("budget", "💰 الميزانية الشهرية"),
        BotCommand("recurring", "🔁 المدفوعات المتكررة"),
        BotCommand("add_recurring", "➕ إضافة دفعة متكررة"),
        BotCommand("delete_recurring", "❌ حذف دفعة متكررة"),
        BotCommand("compare", "🔄 مقارنة شهرية"),
        BotCommand("search", "🔍 بحث"),
        BotCommand("report", "📋 تقرير مخصص"),
        BotCommand("chart", "📊 رسم بياني شهري"),
        BotCommand("chart_week", "📈 رسم بياني أسبوعي"),
        BotCommand("export_csv", "📄 تصدير CSV"),
        BotCommand("export_excel", "📊 تصدير Excel"),
        BotCommand("plan", "📋 خطتك الحالية"),
        BotCommand("upgrade_info", "🌟 معلومات الترقية"),
    ]

    admin_commands = user_commands + [
        BotCommand("adduser", "➕ إضافة مستخدم"),
        BotCommand("removeuser", "➖ حذف مستخدم"),
        BotCommand("users", "👥 قائمة المستخدمين"),
        BotCommand("upgrade", "🌟 ترقية مستخدم"),
        BotCommand("downgrade", "⬇️ إرجاع للمجاني"),
        BotCommand("subscribers", "📊 المشتركون"),
    ]

    # Set default commands for all users
    await application.bot.set_my_commands(user_commands)

    # Set admin-specific commands for each admin chat
    for admin_id in ADMIN_USER_IDS:
        try:
            await application.bot.set_my_commands(
                admin_commands,
                scope=BotCommandScopeChat(chat_id=admin_id),
            )
        except Exception as e:
            logger.warning(f"Could not set admin commands for {admin_id}: {e}")

    logger.info("Bot commands menu registered successfully.")


async def post_init(application: Application) -> None:
    """Initialize database and set bot commands on startup."""
    logger.info("Initializing database...")
    await init_pool()
    await create_tables()
    # Migrate static ALLOWED_USER_IDS from .env to DB (runs on every startup, safe due to ON CONFLICT DO NOTHING)
    from config import ALLOWED_USER_IDS
    if ALLOWED_USER_IDS:
        await AllowedUsersRepository().seed_from_list(ALLOWED_USER_IDS)
    await set_bot_commands(application)


def main() -> None:
    """Initialize and run the bot."""

    # ── 1. Build the Telegram application ─────────────────
    logger.info("Starting Telegram bot...")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # ── 2. ConversationHandlers (must be registered FIRST) ──
    app.add_handler(edit_conversation)
    app.add_handler(compare_conversation)
    app.add_handler(budget_set_conversation)
    app.add_handler(add_recurring_conversation)

    # ── 3. Register command handlers ──────────────────────
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("myid", myid_command))
    app.add_handler(CommandHandler("today", today_command))
    app.add_handler(CommandHandler("week", week_command))
    app.add_handler(CommandHandler("month", month_command))
    app.add_handler(CommandHandler("category", category_command))
    app.add_handler(CommandHandler("delete", delete_command))
    app.add_handler(CommandHandler("recurring", recurring_command))
    app.add_handler(CommandHandler("delete_recurring", delete_recurring_command))
    app.add_handler(CommandHandler("export_csv", export_csv_command))
    app.add_handler(CommandHandler("export_excel", export_excel_command))
    app.add_handler(CommandHandler("chart", chart_command))
    app.add_handler(CommandHandler("chart_week", chart_week_command))
    app.add_handler(CommandHandler("budget", budget_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("last", last_command))
    app.add_handler(CommandHandler("undo", undo_command))
    app.add_handler(CommandHandler("plan", plan_command))
    app.add_handler(CommandHandler("upgrade_info", upgrade_info_command))
    app.add_handler(CommandHandler("adduser", adduser_command))
    app.add_handler(CommandHandler("removeuser", removeuser_command))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("upgrade", upgrade_command))
    app.add_handler(CommandHandler("downgrade", downgrade_command))
    app.add_handler(CommandHandler("subscribers", subscribers_command))

    # ── 4. Text message handler (catch-all for AI parsing) ──
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # ── 5. Callback query handlers (inline keyboards) ────
    app.add_handler(CallbackQueryHandler(handle_expense_callback, pattern="^(confirm|cancel)_expense$"))
    app.add_handler(CallbackQueryHandler(handle_delete_pick, pattern=r"^del_\d+$"))
    app.add_handler(CallbackQueryHandler(handle_delete_confirm, pattern=r"^delok_\d+$"))
    app.add_handler(CallbackQueryHandler(handle_delete_pick, pattern="^del_cancel$"))
    app.add_handler(CallbackQueryHandler(handle_category_show, pattern=r"^catshow_"))
    app.add_handler(CallbackQueryHandler(handle_budget_action, pattern=r"^budgetaction_"))
    app.add_handler(CallbackQueryHandler(handle_budget_delete_cat, pattern=r"^budgetdel_"))
    app.add_handler(CallbackQueryHandler(handle_budget_cancel, pattern="^cancel_budget$"))
    app.add_handler(CallbackQueryHandler(handle_cancel_generic, pattern="^cat_cancel$"))
    # Recurring payment callbacks
    app.add_handler(CallbackQueryHandler(handle_rec_delete, pattern=r"^recdel_\d+$"))
    app.add_handler(CallbackQueryHandler(handle_rec_delete_confirm, pattern=r"^recdelok_\d+$"))
    app.add_handler(CallbackQueryHandler(handle_rec_toggle, pattern=r"^rectoggle_\d+$"))
    app.add_handler(CallbackQueryHandler(handle_rec_cancel, pattern="^rec_cancel$"))
    app.add_handler(CallbackQueryHandler(handle_rec_add_hint, pattern="^rec_add_hint$"))

    # ── 6. Schedule jobs ──────────────────────────────────
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

    # ── 7. Start polling ──────────────────────────────────
    logger.info("🚀 BotBudget is running! Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True, allowed_updates=["message", "callback_query"])

    # ── 8. Cleanup on shutdown ────────────────────────────
    import asyncio
    asyncio.get_event_loop().run_until_complete(close_pool())
    logger.info("BotBudget stopped.")


if __name__ == "__main__":
    main()

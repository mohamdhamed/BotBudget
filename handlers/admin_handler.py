"""
handlers/admin_handler.py
--------------------------
Admin commands for managing users and subscriptions.
All commands require ADMIN_USER_IDS in .env.
"""

from telegram import Update
from telegram.ext import ContextTypes

from repositories.allowed_users_repo import AllowedUsersRepository
from repositories.subscription_repo import SubscriptionRepository
from security.auth import admin_only
from utils.logger import get_logger

logger = get_logger(__name__)
allowed_users_repo = AllowedUsersRepository()
sub_repo = SubscriptionRepository()


@admin_only
async def adduser_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/adduser <user_id> [name] — Add a user to the allowed list."""
    if not context.args:
        await update.message.reply_text(
            "➕ *إضافة مستخدم*\n\n"
            "*الصيغة:* `/adduser <رقم المستخدم>`\n"
            "*مثال:* `/adduser 123456789`\n\n"
            "💡 المستخدم يقدر يعرف رقمه بكتابة /myid في البوت.",
            parse_mode="Markdown",
        )
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ رقم المستخدم لازم يكون رقم صحيح.")
        return

    name = " ".join(context.args[1:]) if len(context.args) > 1 else None
    added = await allowed_users_repo.add_user(user_id, first_name=name, added_by=update.effective_user.id)

    if added:
        await update.message.reply_text(
            f"✅ تم إضافة المستخدم `{user_id}` بنجاح.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(f"ℹ️ المستخدم `{user_id}` موجود بالفعل.", parse_mode="Markdown")


@admin_only
async def removeuser_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/removeuser <user_id> — Remove a user from the allowed list."""
    if not context.args:
        await update.message.reply_text(
            "➖ *حذف مستخدم*\n\n"
            "*الصيغة:* `/removeuser <رقم المستخدم>`\n"
            "*مثال:* `/removeuser 123456789`",
            parse_mode="Markdown",
        )
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ رقم المستخدم لازم يكون رقم صحيح.")
        return

    removed = await allowed_users_repo.remove_user(user_id)

    if removed:
        await update.message.reply_text(f"🗑️ تم حذف المستخدم `{user_id}`.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"⚠️ المستخدم `{user_id}` مش موجود.", parse_mode="Markdown")


@admin_only
async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/users — List all allowed users."""
    users = await allowed_users_repo.get_all()

    if not users:
        await update.message.reply_text("📭 مفيش مستخدمين.")
        return

    lines = [f"👥 *المستخدمون ({len(users)}):*\n"]
    for u in users:
        name = u["first_name"] or "—"
        dt = u["added_at"].strftime("%Y-%m-%d") if u["added_at"] else "—"
        lines.append(f"  • `{u['user_id']}` — {name} _(أُضيف {dt})_")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ── Subscription management ──────────────────────────────

@admin_only
async def upgrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /upgrade <user_id> [days]
    Upgrade a user to premium. Default 30 days.
    """
    if not context.args:
        await update.message.reply_text(
            "🌟 *ترقية مستخدم*\n\n"
            "*الصيغة:* `/upgrade <رقم المستخدم> [عدد الأيام]`\n\n"
            "*أمثلة:*\n"
            "• `/upgrade 123456789` — 30 يوم (افتراضي)\n"
            "• `/upgrade 123456789 90` — 90 يوم\n"
            "• `/upgrade 123456789 365` — سنة",
            parse_mode="Markdown",
        )
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ رقم المستخدم لازم يكون رقم صحيح.")
        return

    days = 30
    if len(context.args) >= 2:
        try:
            days = int(context.args[1])
        except ValueError:
            await update.message.reply_text("⚠️ عدد الأيام لازم يكون رقم صحيح.")
            return

    success = await sub_repo.upgrade(user_id, days, update.effective_user.id)

    if success:
        await update.message.reply_text(
            f"🌟 تم ترقية المستخدم `{user_id}` للخطة المميزة لمدة *{days} يوم*.",
            parse_mode="Markdown",
        )
        # Notify the user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"🎉 *تم ترقية حسابك للخطة المميزة!*\n\n"
                    f"📅 المدة: {days} يوم\n"
                    f"✨ معاملات بلا حدود\n\n"
                    f"شكراً لثقتك في BotBudget! 🙏"
                ),
                parse_mode="Markdown",
            )
        except Exception:
            pass
    else:
        await update.message.reply_text("⚠️ فشلت الترقية. تأكد إن المستخدم مسجّل.")


@admin_only
async def downgrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/downgrade <user_id> — Downgrade user to free plan."""
    if not context.args:
        await update.message.reply_text(
            "*الصيغة:* `/downgrade <رقم المستخدم>`",
            parse_mode="Markdown",
        )
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ رقم المستخدم لازم يكون رقم صحيح.")
        return

    success = await sub_repo.downgrade(user_id)

    if success:
        await update.message.reply_text(f"تم إرجاع المستخدم `{user_id}` للخطة المجانية.", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ فشلت العملية.")


@admin_only
async def subscribers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/subscribers — List all subscribers with their plan status."""
    subs = await sub_repo.get_all_subscribers()

    if not subs:
        await update.message.reply_text("📭 مفيش مشتركين.")
        return

    premium_count = sum(1 for s in subs if s["plan"] == "premium")
    free_count = len(subs) - premium_count

    lines = [
        f"📊 *المشتركون ({len(subs)})*\n"
        f"🌟 مميز: {premium_count} | 🆓 مجاني: {free_count}\n"
    ]

    for s in subs:
        name = s["first_name"] or "—"
        icon = "🌟" if s["plan"] == "premium" else "🆓"
        expires = ""
        if s["expires_at"]:
            expires = f" ← ينتهي {s['expires_at'].strftime('%Y-%m-%d')}"
        lines.append(f"  {icon} `{s['user_id']}` — {name}{expires}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

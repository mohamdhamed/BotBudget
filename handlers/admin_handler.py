"""
handlers/admin_handler.py
--------------------------
Admin commands for managing allowed users dynamically.
All commands require ADMIN_USER_IDS in .env.
"""

from telegram import Update
from telegram.ext import ContextTypes

from repositories.allowed_users_repo import AllowedUsersRepository
from security.auth import admin_only
from utils.logger import get_logger

logger = get_logger(__name__)
allowed_users_repo = AllowedUsersRepository()


@admin_only
async def adduser_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /adduser <user_id> [name]
    Add a user to the allowed list.
    """
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
            f"✅ تم إضافة المستخدم `{user_id}` بنجاح.\n"
            f"دلوقتي يقدر يستخدم البوت.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(f"ℹ️ المستخدم `{user_id}` موجود بالفعل.", parse_mode="Markdown")


@admin_only
async def removeuser_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /removeuser <user_id>
    Remove a user from the allowed list.
    """
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
        await update.message.reply_text(
            f"🗑️ تم حذف المستخدم `{user_id}` من القائمة.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(f"⚠️ المستخدم `{user_id}` مش موجود في القائمة.", parse_mode="Markdown")


@admin_only
async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /users
    List all allowed users.
    """
    users = await allowed_users_repo.get_all()

    if not users:
        await update.message.reply_text("📭 مفيش مستخدمين في القائمة.")
        return

    lines = [f"👥 *المستخدمون المسموح لهم ({len(users)}):*\n"]
    for u in users:
        name = u["first_name"] or "—"
        date = u["added_at"].strftime("%Y-%m-%d") if u["added_at"] else "—"
        lines.append(f"  • `{u['user_id']}` — {name} _(أُضيف {date})_")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

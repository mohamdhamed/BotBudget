"""
handlers/insights_handler.py
------------------------------
/insights command — Smart financial analysis and predictions.
"""

from telegram import Update
from telegram.ext import ContextTypes

from security.auth import authorized_only
from security.rate_limiter import rate_limited
from services.insights_service import InsightsService
from utils.logger import get_logger

logger = get_logger(__name__)

_svc = InsightsService()


def _score_emoji(score: int) -> str:
    if score >= 80:
        return "🟢"
    if score >= 60:
        return "🟡"
    if score >= 40:
        return "🟠"
    return "🔴"


def _score_bar(score: int) -> str:
    filled = score // 10
    empty = 10 - filled
    return "█" * filled + "░" * empty


def _trend_arrow(pct: float) -> str:
    if pct > 5:
        return "📈"
    if pct < -5:
        return "📉"
    return "➡️"


@authorized_only
@rate_limited
async def insights_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /insights command."""
    user_id = update.effective_user.id
    msg = await update.message.reply_text("🔍 جاري تحليل بياناتك...")

    data = await _svc.generate(user_id)

    if not data:
        await msg.edit_text(
            "📊 مفيش بيانات كافية للتحليل.\n"
            "ابدأ سجل مصاريفك وارجع هنا بعد كام يوم!"
        )
        return

    # ── Build message ──
    lines = []

    # Header
    lines.append(f"🧠 <b>تحليل ذكي — {data['month_name']}</b>")
    lines.append(f"📅 يوم {data['days_passed']} من {data['total_days']} (باقي {data['days_remaining']} يوم)")
    lines.append("")

    # Score
    s = data["score"]
    lines.append(f"{_score_emoji(s)} <b>الصحة المالية: {s}/100</b>")
    lines.append(f"  {_score_bar(s)}")
    lines.append("")

    # Overview
    lines.append("💰 <b>ملخص الشهر:</b>")
    if data["total_income"] > 0:
        lines.append(f"  📥 الدخل: {data['total_income']:,.0f}")
    lines.append(f"  📤 المصروفات: {data['total_expenses']:,.0f}")
    lines.append(f"  📊 المعدل اليومي: {data['daily_avg']:,.0f}/يوم")
    lines.append("")

    # Prediction
    lines.append("🔮 <b>التوقعات:</b>")
    arrow = _trend_arrow(data["predicted_vs_last"])
    lines.append(f"  متوقع نهاية الشهر: {data['predicted_total']:,.0f} {arrow}")
    if data["last_month_total"] > 0:
        sign = "+" if data["predicted_vs_last"] > 0 else ""
        lines.append(f"  مقارنة بالشهر اللي فات: {sign}{data['predicted_vs_last']:.0f}%")
    lines.append("")

    # Top categories
    if data["top_categories"]:
        lines.append("📂 <b>أعلى الفئات:</b>")
        medals = ["🥇", "🥈", "🥉"]
        for i, c in enumerate(data["top_categories"]):
            medal = medals[i] if i < 3 else "  "
            bar_len = int(c["pct"] / 5)  # max 20 chars
            bar = "▓" * bar_len + "░" * (20 - bar_len)
            lines.append(f"  {medal} {c['cat']}: {c['total']:,.0f} ({c['pct']:.0f}%)")
            lines.append(f"     {bar}")
        lines.append("")

    # Biggest expense
    if data["biggest_expense"]:
        b = data["biggest_expense"]
        desc = f" ({b['desc']})" if b["desc"] else ""
        lines.append(f"💸 <b>أكبر مصروف:</b> {b['amount']:,.0f} — {b['cat']}{desc}")
        lines.append("")

    # Peak day
    lines.append(f"📆 <b>أكتر يوم إنفاق:</b> {data['peak_day']}")
    lines.append("")

    # Budget warnings
    if data["budget_warnings"]:
        lines.append("⚠️ <b>تحذيرات الميزانية:</b>")
        for w in data["budget_warnings"]:
            icon = "🔴" if w["pct"] >= 100 else "🟡"
            lines.append(f"  {icon} {w['cat']}: {w['spent']:,.0f}/{w['budget']:,.0f} ({w['pct']:.0f}%)")
        lines.append("")

    # Tips
    if data["tips"]:
        lines.append("💡 <b>نصائح مخصصة ليك:</b>")
        for i, tip in enumerate(data["tips"], 1):
            lines.append(f"  {i}. {tip}")

    text = "\n".join(lines)
    await msg.edit_text(text, parse_mode="HTML")
    logger.info(f"Insights generated for user {user_id} — score={data['score']}")

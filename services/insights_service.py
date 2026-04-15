"""
services/insights_service.py
------------------------------
Smart financial insights engine.
Analyzes spending patterns, predicts end-of-month totals,
and generates personalized Arabic tips.
"""

from datetime import date, timedelta
from calendar import monthrange

from db.connection import get_pool
from utils.logger import get_logger

logger = get_logger(__name__)


class InsightsService:
    """Generates AI-like financial insights from transaction data."""

    async def generate(self, user_id: int) -> dict | None:
        """
        Build a complete insights report for the current month.

        Returns dict with keys:
            month_name, days_passed, days_remaining, total_days,
            total_expenses, total_income, daily_avg,
            predicted_total, predicted_vs_last,
            top_categories, biggest_expense,
            peak_day_name, budget_warnings,
            last_month_total, change_pct,
            score, tips
        Or None if no data at all.
        """
        today = date.today()
        y, m = today.year, today.month
        first = date(y, m, 1)
        _, total_days = monthrange(y, m)
        last = date(y, m, total_days)
        days_passed = (today - first).days + 1
        days_remaining = total_days - days_passed

        # Previous month
        prev_last = first - timedelta(days=1)
        prev_first = date(prev_last.year, prev_last.month, 1)

        pool = get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # 1) Current month totals
                await cur.execute(
                    """SELECT type, SUM(amount) FROM expenses
                       WHERE user_id=%s AND date BETWEEN %s AND %s
                       GROUP BY type""",
                    (user_id, first, last),
                )
                rows = await cur.fetchall()
                cur_exp = cur_inc = 0.0
                for r in rows:
                    if r[0] == "expense":
                        cur_exp = float(r[1])
                    elif r[0] == "income":
                        cur_inc = float(r[1])

                if cur_exp == 0 and cur_inc == 0:
                    return None

                # 2) Previous month total expenses
                await cur.execute(
                    """SELECT SUM(amount) FROM expenses
                       WHERE user_id=%s AND type='expense'
                         AND date BETWEEN %s AND %s""",
                    (user_id, prev_first, prev_last),
                )
                row = await cur.fetchone()
                last_month_total = float(row[0]) if row and row[0] else 0.0

                # 3) Category breakdown (current month)
                await cur.execute(
                    """SELECT category, SUM(amount) as total
                       FROM expenses
                       WHERE user_id=%s AND type='expense'
                         AND date BETWEEN %s AND %s
                       GROUP BY category ORDER BY total DESC""",
                    (user_id, first, last),
                )
                categories = [
                    {"cat": r[0], "total": float(r[1])} for r in await cur.fetchall()
                ]

                # 4) Spending by day-of-week
                await cur.execute(
                    """SELECT EXTRACT(DOW FROM date)::int as dow,
                              SUM(amount) as total
                       FROM expenses
                       WHERE user_id=%s AND type='expense'
                         AND date BETWEEN %s AND %s
                       GROUP BY dow ORDER BY total DESC LIMIT 1""",
                    (user_id, first, last),
                )
                peak_row = await cur.fetchone()
                dow_names = [
                    "الأحد", "الاثنين", "الثلاثاء", "الأربعاء",
                    "الخميس", "الجمعة", "السبت",
                ]
                peak_day = dow_names[peak_row[0]] if peak_row else "—"

                # 5) Biggest single expense
                await cur.execute(
                    """SELECT amount, description, category FROM expenses
                       WHERE user_id=%s AND type='expense'
                         AND date BETWEEN %s AND %s
                       ORDER BY amount DESC LIMIT 1""",
                    (user_id, first, last),
                )
                big = await cur.fetchone()

                # 6) Budget warnings
                await cur.execute(
                    """SELECT b.category, b.limit_amount as budget,
                              COALESCE(SUM(e.amount), 0) as spent
                       FROM budgets b
                       LEFT JOIN expenses e
                         ON e.user_id = b.user_id
                         AND e.category = b.category
                         AND e.type = 'expense'
                         AND e.date BETWEEN %s AND %s
                       WHERE b.user_id = %s
                       GROUP BY b.category, b.limit_amount""",
                    (first, last, user_id),
                )
                budget_warnings = []
                for r in await cur.fetchall():
                    cat, budget, spent = r[0], float(r[1]), float(r[2])
                    pct = (spent / budget * 100) if budget > 0 else 0
                    if pct >= 80:
                        budget_warnings.append(
                            {"cat": cat, "budget": budget, "spent": spent, "pct": pct}
                        )

        # ── Calculations ──
        daily_avg = cur_exp / days_passed if days_passed > 0 else 0
        predicted = daily_avg * total_days
        pred_vs_last = (
            ((predicted - last_month_total) / last_month_total * 100)
            if last_month_total > 0
            else 0
        )
        change_pct = (
            ((cur_exp - last_month_total) / last_month_total * 100)
            if last_month_total > 0
            else 0
        )

        # Top 3 categories with percentage
        top_cats = []
        for c in categories[:3]:
            pct = (c["total"] / cur_exp * 100) if cur_exp > 0 else 0
            top_cats.append({**c, "pct": pct})

        # ── Financial health score (0-100) ──
        score = self._calc_score(
            cur_exp, cur_inc, daily_avg, days_passed,
            top_cats, budget_warnings, last_month_total,
        )

        # ── Tips ──
        tips = self._generate_tips(
            cur_exp, cur_inc, daily_avg, days_remaining,
            top_cats, budget_warnings, predicted, last_month_total, peak_day,
        )

        months_ar = [
            "", "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
            "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
        ]

        return {
            "month_name": months_ar[m],
            "days_passed": days_passed,
            "days_remaining": days_remaining,
            "total_days": total_days,
            "total_expenses": cur_exp,
            "total_income": cur_inc,
            "daily_avg": daily_avg,
            "predicted_total": predicted,
            "predicted_vs_last": pred_vs_last,
            "top_categories": top_cats,
            "biggest_expense": {
                "amount": float(big[0]),
                "desc": big[1] or "",
                "cat": big[2],
            } if big else None,
            "peak_day": peak_day,
            "budget_warnings": budget_warnings,
            "last_month_total": last_month_total,
            "change_pct": change_pct,
            "score": score,
            "tips": tips,
        }

    # ── Score ────────────────────────────────────────────

    @staticmethod
    def _calc_score(
        expenses, income, daily_avg, days_passed,
        top_cats, budget_warnings, last_month,
    ) -> int:
        """Calculate financial health score 0-100."""
        score = 70  # baseline

        # Income vs expenses ratio
        if income > 0:
            ratio = expenses / income
            if ratio < 0.5:
                score += 15
            elif ratio < 0.7:
                score += 10
            elif ratio < 0.9:
                score += 0
            else:
                score -= 10

        # Diversification: top category shouldn't dominate
        if top_cats and top_cats[0]["pct"] > 50:
            score -= 10
        elif top_cats and top_cats[0]["pct"] < 30:
            score += 5

        # Budget discipline
        score -= len(budget_warnings) * 5

        # Month-over-month improvement
        if last_month > 0 and expenses < last_month * 0.9:
            score += 10
        elif last_month > 0 and expenses > last_month * 1.2:
            score -= 5

        return max(0, min(100, score))

    # ── Tips ─────────────────────────────────────────────

    @staticmethod
    def _generate_tips(
        expenses, income, daily_avg, days_remaining,
        top_cats, budget_warnings, predicted, last_month, peak_day,
    ) -> list[str]:
        """Generate personalized Arabic financial tips."""
        tips = []

        # Budget about to exceed
        for w in budget_warnings:
            if w["pct"] >= 100:
                tips.append(
                    f"تجاوزت ميزانية {w['cat']} ({w['spent']:,.0f} من {w['budget']:,.0f}). حاول تقلل الإنفاق في هذه الفئة."
                )
            else:
                tips.append(
                    f"ميزانية {w['cat']} وصلت {w['pct']:.0f}% — خلّي بالك الأيام الجاية."
                )

        # Remaining daily budget
        if income > 0 and days_remaining > 0:
            remaining = income - expenses
            if remaining > 0:
                daily_budget = remaining / days_remaining
                tips.append(
                    f"المتبقي من دخلك: {remaining:,.0f} — يعني {daily_budget:,.0f}/يوم لآخر الشهر."
                )
            else:
                tips.append(
                    "صرفت أكتر من دخلك هذا الشهر! حاول تقلل المصاريف فوراً."
                )

        # Dominant category
        if top_cats and top_cats[0]["pct"] > 40:
            c = top_cats[0]
            tips.append(
                f"{c['cat']} بياخد {c['pct']:.0f}% من مصاريفك. "
                f"لو قللته 20% هتوفر {c['total'] * 0.2:,.0f} شهرياً."
            )

        # Prediction warning
        if last_month > 0 and predicted > last_month * 1.1:
            diff = predicted - last_month
            tips.append(
                f"متوقع مصاريفك تزيد {diff:,.0f} عن الشهر اللي فات. حاول تهدي الإنفاق."
            )

        # Peak day
        if peak_day != "—":
            tips.append(f"أكتر يوم بتصرف فيه: {peak_day}. خطط مشترياتك قبلها.")

        # If no tips, give generic
        if not tips:
            tips.append("استمر في تسجيل مصاريفك يومياً عشان التحليلات تكون أدق!")

        return tips[:5]  # max 5 tips

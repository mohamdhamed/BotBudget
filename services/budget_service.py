"""
services/budget_service.py
---------------------------
Business logic for monthly budget limits and tracking.
"""

from datetime import date, timedelta

from repositories.budget_repo import BudgetRepository
from repositories.expense_repo import ExpenseRepository
from utils.logger import get_logger

logger = get_logger(__name__)


class BudgetService:
    """Manages monthly budget limits and alerts."""

    def __init__(self):
        self.budget_repo = BudgetRepository()
        self.expense_repo = ExpenseRepository()

    def set_budget(self, user_id: int, category: str, amount: float) -> str:
        """Set a monthly budget limit for a category (or 'إجمالي' for overall)."""
        self.budget_repo.set_budget(user_id, category, amount)
        return (
            f"✅ تم تحديد ميزانية \"{category}\":\n"
            f"  💰 الحد: {amount:.2f}€ شهرياً"
        )

    def delete_budget(self, user_id: int, category: str) -> str:
        """Delete a budget limit."""
        deleted = self.budget_repo.delete_budget(user_id, category)
        if deleted:
            return f"🗑️ تم حذف ميزانية \"{category}\"."
        return f"⚠️ مفيش ميزانية محددة لفئة \"{category}\"."

    def get_budget_status(self, user_id: int) -> str:
        """Get current spending vs budget for all categories."""
        budgets = self.budget_repo.get_all_budgets(user_id)
        if not budgets:
            return (
                "📭 مفيش ميزانية محددة.\n\n"
                "💡 استخدم `/budget set <الفئة> <المبلغ>` لتحديد ميزانية.\n"
                "مثال: `/budget set طعام 200`"
            )

        today = date.today()
        start = date(today.year, today.month, 1)
        end = date(today.year, today.month + 1, 1) - timedelta(days=1) if today.month < 12 else date(today.year, 12, 31)

        # Get category spending
        cat_summary = self.expense_repo.get_category_summary(user_id, start, end)
        spending_map = {c["category"]: c["total"] for c in cat_summary}

        # Overall spending
        totals = self.expense_repo.get_monthly_total(user_id, today.year, today.month)
        total_spent = totals["total_expenses"]

        lines = [f"💰 *حالة الميزانية - {today.month}/{today.year}*\n"]

        for b in budgets:
            cat = b["category"]
            limit = b["limit_amount"]

            if cat == "إجمالي":
                spent = total_spent
            else:
                spent = spending_map.get(cat, 0)

            pct = (spent / limit * 100) if limit > 0 else 0

            # Status indicator
            if pct >= 100:
                icon = "🔴"
                status = "تجاوز!"
            elif pct >= 80:
                icon = "🟡"
                status = "تحذير"
            else:
                icon = "🟢"
                status = "آمن"

            bar = self._progress_bar(pct)
            remaining = max(0, limit - spent)

            lines.append(
                f"{icon} *{cat}*: {spent:.2f}€ / {limit:.2f}€ ({pct:.0f}%)\n"
                f"  {bar}\n"
                f"  المتبقي: {remaining:.2f}€ | {status}"
            )

        return "\n\n".join(lines)

    def check_budget_alert(self, user_id: int, category: str, new_amount: float) -> str | None:
        """
        Check if adding a new expense would trigger a budget alert.
        Called after each expense is added.

        Returns:
            Alert message string or None if no alert needed.
        """
        # Check specific category budget
        budget = self.budget_repo.get_budget(user_id, category)
        alerts = []

        today = date.today()
        start = date(today.year, today.month, 1)
        end = date(today.year, today.month + 1, 1) - timedelta(days=1) if today.month < 12 else date(today.year, 12, 31)

        if budget:
            cat_summary = self.expense_repo.get_category_summary(user_id, start, end)
            cat_spent = sum(c["total"] for c in cat_summary if c["category"] == category)
            pct = (cat_spent / budget["limit_amount"] * 100) if budget["limit_amount"] > 0 else 0
            
            if pct >= 100:
                alerts.append(f"🔴 تجاوزت ميزانية \"{category}\"! ({pct:.0f}%)")
            elif pct >= 80:
                alerts.append(f"🟡 وصلت {pct:.0f}% من ميزانية \"{category}\"!")

        # Check overall budget
        overall = self.budget_repo.get_budget(user_id, "إجمالي")
        if overall:
            totals = self.expense_repo.get_monthly_total(user_id, today.year, today.month)
            total_pct = (totals["total_expenses"] / overall["limit_amount"] * 100) if overall["limit_amount"] > 0 else 0

            if total_pct >= 100:
                alerts.append(f"🔴 تجاوزت الميزانية الإجمالية! ({total_pct:.0f}%)")
            elif total_pct >= 80:
                alerts.append(f"🟡 وصلت {total_pct:.0f}% من الميزانية الإجمالية!")

        return "\n".join(alerts) if alerts else None

    @staticmethod
    def _progress_bar(pct: float, length: int = 15) -> str:
        """Generate a text progress bar."""
        filled = int(min(pct, 100) / 100 * length)
        empty = length - filled
        if pct >= 100:
            return "█" * length + " ⚠️"
        elif pct >= 80:
            return "█" * filled + "░" * empty + " ⚡"
        else:
            return "█" * filled + "░" * empty

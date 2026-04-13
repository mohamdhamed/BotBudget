"""
services/expense_service.py
----------------------------
Business logic for managing expenses and income.
Orchestrates between the AI parser and the ExpenseRepository.
"""

from datetime import date, timedelta
from typing import Optional

from ai.gemini_parser import parse_transaction
from models.expense import Expense
from repositories.expense_repo import ExpenseRepository
from utils.logger import get_logger

logger = get_logger(__name__)


class ExpenseService:
    """
    Handles all business logic related to financial transactions.

    Workflow:
        1. Receive raw text from the handler.
        2. Send to Gemini for parsing.
        3. Validate the parsed data.
        4. Persist via the repository.
        5. Return a user-friendly response.
    """

    def __init__(self):
        self.repo = ExpenseRepository()

    async def add_from_text(self, user_id: int, text: str) -> dict:
        """
        Parse natural text and save as an expense or income.

        Args:
            user_id: Telegram user ID.
            text: Raw message text in Arabic.

        Returns:
            Dict with 'success' and 'message' keys, or 'error' and 'question'.
        """
        parsed = parse_transaction(text)

        # If AI couldn't parse, return the clarifying question
        if "error" in parsed:
            return {"success": False, "question": parsed.get("question", "حاول تاني.")}

        try:
            expense = Expense(
                user_id=user_id,
                type=parsed["type"],
                amount=float(parsed["amount"]),
                category=parsed.get("category", "أخرى"),
                description=parsed.get("description"),
                date=date.fromisoformat(parsed["date"]),
                raw_text=text,
            )
            saved = await self.repo.add(expense)

            emoji = "💸" if saved.is_expense() else "💰"
            msg = (
                f"{emoji} تم تسجيل {saved.type}:\n"
                f"  📂 الفئة: {saved.category}\n"
                f"  💶 المبلغ: {saved.amount:.2f} {saved.currency}\n"
                f"  📅 التاريخ: {saved.date}\n"
            )
            if saved.description:
                msg += f"  📝 ملاحظة: {saved.description}\n"
            msg += f"  🔖 رقم العملية: #{saved.id}"

            return {"success": True, "message": msg, "category": saved.category}

        except (KeyError, ValueError) as e:
            logger.error(f"Validation error for parsed data: {e}, parsed: {parsed}")
            return {"success": False, "question": "حصل مشكلة في البيانات. حاول تاني بصيغة مختلفة."}

    async def delete_expense(self, expense_id: int, user_id: int) -> str:
        """
        Delete an expense by ID.

        Returns:
            User-friendly message confirming deletion or error.
        """
        deleted = await self.repo.delete(expense_id, user_id)
        if deleted:
            return f"🗑️ تم حذف العملية رقم #{expense_id} بنجاح."
        return f"⚠️ العملية رقم #{expense_id} مش موجودة أو مش ليك."

    async def get_today_summary(self, user_id: int) -> str:
        """Get a summary of today's transactions."""
        today = date.today()
        expenses = await self.repo.get_by_date_range(user_id, today, today)
        if not expenses:
            return "📭 مفيش معاملات النهاردة."

        total_exp = sum(e.amount for e in expenses if e.is_expense())
        total_inc = sum(e.amount for e in expenses if e.is_income())

        lines = [f"📊 ملخص النهاردة ({today}):\n"]
        for e in expenses:
            sign = "🔴" if e.is_expense() else "🟢"
            lines.append(f"  {sign} {e.category}: {e.amount:.2f}€ {'- ' + e.description if e.description else ''}")

        lines.append(f"\n💸 إجمالي المصاريف: {total_exp:.2f}€")
        lines.append(f"💰 إجمالي الدخل: {total_inc:.2f}€")
        lines.append(f"📈 الصافي: {total_inc - total_exp:.2f}€")
        return "\n".join(lines)

    async def get_month_summary(self, user_id: int, year: Optional[int] = None, month: Optional[int] = None) -> str:
        """Get a summary of a specific month's transactions."""
        today = date.today()
        y = year or today.year
        m = month or today.month

        totals = await self.repo.get_monthly_total(user_id, y, m)
        categories = await self.repo.get_category_summary(
            user_id,
            date(y, m, 1),
            date(y, m + 1, 1) - timedelta(days=1) if m < 12 else date(y, 12, 31),
        )

        lines = [f"📊 ملخص شهر {m}/{y}:\n"]
        lines.append(f"💸 إجمالي المصاريف: {totals['total_expenses']:.2f}€")
        lines.append(f"💰 إجمالي الدخل: {totals['total_income']:.2f}€")
        lines.append(f"📈 الصافي: {totals['net']:.2f}€\n")

        if categories:
            lines.append("📂 توزيع المصاريف بالفئات:")
            for cat in categories:
                pct = (cat["total"] / totals["total_expenses"] * 100) if totals["total_expenses"] > 0 else 0
                lines.append(f"  • {cat['category']}: {cat['total']:.2f}€ ({pct:.0f}%)")

        return "\n".join(lines)

    async def edit_expense(self, expense_id: int, user_id: int,
                     amount: float = None, category: str = None,
                     description: str = None) -> str:
        """
        Edit an existing expense's fields directly (no AI).

        Args:
            expense_id: Transaction ID to edit.
            user_id: Telegram user ID (security scope).
            amount: New amount (optional).
            category: New category (optional).
            description: New description (optional).

        Returns:
            User-friendly confirmation or error message.
        """
        expense = await self.repo.get_by_id(expense_id, user_id)
        if not expense:
            return f"⚠️ العملية رقم #{expense_id} مش موجودة أو مش ليك."

        changes = []
        if amount is not None:
            expense.amount = amount
            changes.append(f"💶 المبلغ: {amount:.2f}€")
        if category is not None:
            expense.category = category
            changes.append(f"📂 الفئة: {category}")
        if description is not None:
            expense.description = description
            changes.append(f"📝 الوصف: {description}")

        if not changes:
            return "⚠️ مفيش تعديلات. حدد على الأقل حاجة واحدة للتعديل."

        updated = await self.repo.update(expense)
        if updated:
            msg = f"✏️ تم تعديل العملية #{expense_id}:\n" + "\n".join(f"  {c}" for c in changes)
            return msg
        return f"⚠️ فشل تعديل العملية #{expense_id}."

    async def get_category_details(self, user_id: int, category: str,
                             year: int = None, month: int = None) -> str:
        """
        Get all transactions for a specific category in a month.

        Args:
            user_id: Telegram user ID.
            category: Category name (Arabic).
            year: Year (defaults to current).
            month: Month (defaults to current).

        Returns:
            Formatted string of transactions in that category.
        """
        today = date.today()
        y = year or today.year
        m = month or today.month

        start = date(y, m, 1)
        end = date(y, m + 1, 1) - timedelta(days=1) if m < 12 else date(y, 12, 31)

        expenses = await self.repo.get_by_category(user_id, category, start, end)
        if not expenses:
            return f"📭 مفيش معاملات في فئة \"{category}\" لشهر {m}/{y}."

        total = sum(e.amount for e in expenses)
        lines = [f"🏷️ فئة \"{category}\" - شهر {m}/{y}:\n"]
        for e in expenses:
            sign = "🔴" if e.is_expense() else "🟢"
            desc = f" - {e.description}" if e.description else ""
            lines.append(f"  {sign} #{e.id} | {e.date} | {e.amount:.2f}€{desc}")

        lines.append(f"\n💶 الإجمالي: {total:.2f}€ ({len(expenses)} معاملة)")
        return "\n".join(lines)

    async def get_week_summary(self, user_id: int) -> str:
        """Get a summary of the last 7 days."""
        today = date.today()
        week_start = today - timedelta(days=6)

        expenses = await self.repo.get_by_date_range(user_id, week_start, today)
        if not expenses:
            return "📭 مفيش معاملات في آخر ٧ أيام."

        total_exp = sum(e.amount for e in expenses if e.is_expense())
        total_inc = sum(e.amount for e in expenses if e.is_income())

        # Group by category
        cat_totals = {}
        for e in expenses:
            if e.is_expense():
                cat_totals[e.category] = cat_totals.get(e.category, 0) + e.amount

        lines = [f"📊 ملخص آخر ٧ أيام ({week_start} → {today}):\n"]
        lines.append(f"💸 إجمالي المصاريف: {total_exp:.2f}€")
        lines.append(f"💰 إجمالي الدخل: {total_inc:.2f}€")
        lines.append(f"📈 الصافي: {total_inc - total_exp:.2f}€\n")

        if cat_totals:
            lines.append("📂 توزيع المصاريف:")
            for cat, total in sorted(cat_totals.items(), key=lambda x: -x[1]):
                pct = (total / total_exp * 100) if total_exp > 0 else 0
                lines.append(f"  • {cat}: {total:.2f}€ ({pct:.0f}%)")

        return "\n".join(lines)

    async def compare_months(self, user_id: int, month1: int = None, year1: int = None,
                       month2: int = None, year2: int = None) -> str:
        """Compare two months' expenses side by side."""
        today = date.today()
        y2 = year2 or today.year
        m2 = month2 or today.month
        # Default month1 = previous month
        if month1 is None:
            if m2 == 1:
                m1, y1 = 12, y2 - 1
            else:
                m1, y1 = m2 - 1, year1 or y2
        else:
            m1, y1 = month1, year1 or today.year

        t1 = await self.repo.get_monthly_total(user_id, y1, m1)
        t2 = await self.repo.get_monthly_total(user_id, y2, m2)

        s1 = date(y1, m1, 1)
        e1 = date(y1, m1 + 1, 1) - timedelta(days=1) if m1 < 12 else date(y1, 12, 31)
        s2 = date(y2, m2, 1)
        e2 = date(y2, m2 + 1, 1) - timedelta(days=1) if m2 < 12 else date(y2, 12, 31)

        cats1 = {c["category"]: c["total"] for c in await self.repo.get_category_summary(user_id, s1, e1)}
        cats2 = {c["category"]: c["total"] for c in await self.repo.get_category_summary(user_id, s2, e2)}
        all_cats = sorted(set(list(cats1.keys()) + list(cats2.keys())))

        lines = [f"📊 مقارنة {m1}/{y1} ↔ {m2}/{y2}:\n"]
        lines.append(f"{'الفئة':>15} | {m1}/{y1}:>10 | {m2}/{y2}:>10 | الفرق")
        lines.append("─" * 50)

        for cat in all_cats:
            v1 = cats1.get(cat, 0)
            v2 = cats2.get(cat, 0)
            diff = v2 - v1
            arrow = "📈" if diff > 0 else ("📉" if diff < 0 else "➡️")
            lines.append(f"  {arrow} {cat}: {v1:.0f}€ → {v2:.0f}€ ({diff:+.0f}€)")

        # Totals
        diff_exp = t2["total_expenses"] - t1["total_expenses"]
        diff_inc = t2["total_income"] - t1["total_income"]
        exp_arrow = "📈" if diff_exp > 0 else "📉"
        inc_arrow = "📈" if diff_inc > 0 else "📉"

        lines.append(f"\n{'─' * 50}")
        lines.append(f"{exp_arrow} المصاريف: {t1['total_expenses']:.2f}€ → {t2['total_expenses']:.2f}€ ({diff_exp:+.2f}€)")
        lines.append(f"{inc_arrow} الدخل: {t1['total_income']:.2f}€ → {t2['total_income']:.2f}€ ({diff_inc:+.2f}€)")

        return "\n".join(lines)

    async def search_transactions(self, user_id: int, query: str) -> str:
        """Search transactions by text."""
        results = await self.repo.search_by_text(user_id, query)
        if not results:
            return f"📭 مفيش نتائج للبحث عن \"{query}\"."

        total = sum(e.amount for e in results)
        lines = [f"🔍 نتائج البحث عن \"{query}\" ({len(results)} نتيجة):\n"]
        for e in results:
            sign = "🔴" if e.is_expense() else "🟢"
            desc = f" - {e.description}" if e.description else ""
            lines.append(f"  {sign} #{e.id} | {e.date} | {e.category} | {e.amount:.2f}€{desc}")

        lines.append(f"\n💶 الإجمالي: {total:.2f}€")
        return "\n".join(lines)

    async def get_date_range_report(self, user_id: int, start: date, end: date) -> str:
        """Get a detailed report for a specific date range."""
        expenses = await self.repo.get_by_date_range(user_id, start, end)
        if not expenses:
            return f"📭 مفيش معاملات في الفترة {start} → {end}."

        total_exp = sum(e.amount for e in expenses if e.is_expense())
        total_inc = sum(e.amount for e in expenses if e.is_income())

        cat_totals = {}
        for e in expenses:
            if e.is_expense():
                cat_totals[e.category] = cat_totals.get(e.category, 0) + e.amount

        num_days = (end - start).days + 1
        daily_avg = total_exp / num_days if num_days > 0 else 0

        lines = [f"📋 تقرير الفترة {start} → {end} ({num_days} يوم):\n"]
        lines.append(f"💸 إجمالي المصاريف: {total_exp:.2f}€")
        lines.append(f"💰 إجمالي الدخل: {total_inc:.2f}€")
        lines.append(f"📈 الصافي: {total_inc - total_exp:.2f}€")
        lines.append(f"📊 متوسط يومي: {daily_avg:.2f}€\n")

        if cat_totals:
            lines.append("📂 توزيع المصاريف:")
            for cat, total in sorted(cat_totals.items(), key=lambda x: -x[1]):
                pct = (total / total_exp * 100) if total_exp > 0 else 0
                lines.append(f"  • {cat}: {total:.2f}€ ({pct:.0f}%)")

        lines.append(f"\n📊 عدد المعاملات: {len(expenses)}")
        return "\n".join(lines)

    async def get_balance(self, user_id: int) -> str:
        """Get overall balance (all-time)."""
        result = await self.repo.get_overall_balance(user_id)

        today = date.today()
        month_totals = await self.repo.get_monthly_total(user_id, today.year, today.month)

        lines = ["🏦 *رصيد الحساب*\n"]
        lines.append(f"💰 إجمالي الدخل: {result['total_income']:.2f}€")
        lines.append(f"💸 إجمالي المصاريف: {result['total_expenses']:.2f}€")

        balance = result["balance"]
        icon = "📈" if balance >= 0 else "📉"
        lines.append(f"\n{icon} *الرصيد الكلي: {balance:.2f}€*")

        lines.append(f"\n📅 هذا الشهر ({today.month}/{today.year}):")
        lines.append(f"  💰 دخل: {month_totals['total_income']:.2f}€")
        lines.append(f"  💸 مصاريف: {month_totals['total_expenses']:.2f}€")
        lines.append(f"  📈 صافي: {month_totals['net']:.2f}€")

        return "\n".join(lines)

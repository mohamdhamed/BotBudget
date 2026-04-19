"""
services/expense_service.py
----------------------------
Business logic for managing expenses and income.
Orchestrates between the AI parser and the ExpenseRepository.
"""

from calendar import monthrange
from datetime import date, timedelta
from typing import Optional

from ai.gemini_parser import parse_transaction
from models.expense import Expense
from repositories.expense_repo import ExpenseRepository
from repositories.user_repo import UserRepository
from utils.logger import get_logger

logger = get_logger(__name__)


def _month_bounds(y: int, m: int) -> tuple[date, date]:
    """Return (first_day, last_day) for a given year/month."""
    first = date(y, m, 1)
    _, last_day = monthrange(y, m)
    return first, date(y, m, last_day)


def _fmt(amount: float, currency: str = "") -> str:
    """Format amount with thousands separator."""
    cur = f" {currency}" if currency else ""
    return f"{amount:,.2f}{cur}"


def _totals_by_currency(expenses: list, tx_type: str = None) -> dict[str, float]:
    """Group transaction amounts by currency.

    Args:
        expenses: list of Expense objects
        tx_type: 'expense', 'income', or None (all)

    Returns:
        {currency: total_amount}
    """
    totals: dict[str, float] = {}
    for e in expenses:
        if tx_type and e.type != tx_type:
            continue
        totals[e.currency] = totals.get(e.currency, 0.0) + e.amount
    return totals


def _fmt_totals(totals: dict[str, float]) -> str:
    """Format a {currency: amount} dict as multi-line or inline."""
    if not totals:
        return "0.00"
    if len(totals) == 1:
        cur, amt = next(iter(totals.items()))
        return _fmt(amt, cur)
    return "\n  " + "\n  ".join(f"• {_fmt(amt, cur)}" for cur, amt in totals.items())


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
        self.user_repo = UserRepository()

    async def _get_currency(self, user_id: int, start: date = None, end: date = None) -> str:
        """Get user's primary currency from their transactions."""
        if start and end:
            currencies = await self.repo.get_currencies_in_range(user_id, start, end)
        else:
            currencies = await self.repo.get_all_currencies(user_id)
        if not currencies:
            return ""
        return currencies[0]  # most common

    def _currency_warning(self, currencies: list[str]) -> str:
        """Return a warning string if multiple currencies are detected."""
        if len(currencies) > 1:
            return f"\n\n⚠️ <i>تنبيه: الأرقام تشمل عملات مختلفة ({', '.join(currencies)}) وغير محوَّلة.</i>"
        return ""

    async def add_from_text(self, user_id: int, text: str) -> dict:
        """
        Parse natural text and save as an expense or income.

        Args:
            user_id: Telegram user ID.
            text: Raw message text in Arabic.

        Returns:
            Dict with 'success' and 'message' keys, or 'error' and 'question'.
        """
        user = await self.user_repo.get_by_telegram_id(user_id)
        user_currency = user["currency"] if user else "EUR"

        parsed = parse_transaction(text, user_currency)

        # If AI couldn't parse, return the clarifying question
        if "error" in parsed:
            return {"success": False, "question": parsed.get("question", "حاول تاني.")}

        try:
            expense = Expense(
                user_id=user_id,
                type=parsed["type"],
                amount=float(parsed["amount"]),
                currency=parsed.get("currency", user_currency),
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
                f"  💶 المبلغ: {_fmt(saved.amount, saved.currency)}\n"
                f"  📅 التاريخ: {saved.date}\n"
            )
            if saved.description:
                msg += f"  📝 ملاحظة: {saved.description}\n"
            msg += f"  🔖 رقم العملية: #{saved.id}"

            return {"success": True, "message": msg, "category": saved.category}

        except (KeyError, ValueError) as e:
            logger.error(f"Validation error for parsed data: {e}, parsed: {parsed}")
            return {"success": False, "question": "حصل مشكلة في البيانات. حاول تاني بصيغة مختلفة."}

    async def add_from_parsed(self, user_id: int, parsed: dict) -> dict:
        """
        Save a pre-parsed transaction (from inline keyboard confirmation).

        Args:
            user_id: Telegram user ID.
            parsed: Dict from Gemini with type, amount, category, description, date, raw_text.

        Returns:
            Same format as add_from_text.
        """
        user = await self.user_repo.get_by_telegram_id(user_id)
        user_currency = user["currency"] if user else "EUR"

        try:
            expense = Expense(
                user_id=user_id,
                type=parsed["type"],
                amount=float(parsed["amount"]),
                currency=parsed.get("currency", user_currency),
                category=parsed.get("category", "أخرى"),
                description=parsed.get("description"),
                date=date.fromisoformat(parsed["date"]),
                raw_text=parsed.get("raw_text"),
            )
            saved = await self.repo.add(expense)

            emoji = "💸" if saved.is_expense() else "💰"
            msg = (
                f"{emoji} تم تسجيل {saved.type}:\n"
                f"  📂 الفئة: {saved.category}\n"
                f"  💶 المبلغ: {_fmt(saved.amount, saved.currency)}\n"
                f"  📅 التاريخ: {saved.date}\n"
            )
            if saved.description:
                msg += f"  📝 ملاحظة: {saved.description}\n"
            msg += f"  🔖 رقم العملية: #{saved.id}"

            return {"success": True, "message": msg, "category": saved.category}

        except (KeyError, ValueError) as e:
            logger.error(f"Validation error in add_from_parsed: {e}")
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

    # ═══════════════════════════════════════════════════════
    # REPORTS
    # ═══════════════════════════════════════════════════════

    async def get_today_summary(self, user_id: int) -> str:
        """Get a summary of today's transactions."""
        today = date.today()
        expenses = await self.repo.get_by_date_range(user_id, today, today)
        if not expenses:
            return "📭 مفيش معاملات النهاردة."

        exp_totals = _totals_by_currency(expenses, "expense")
        inc_totals = _totals_by_currency(expenses, "income")
        net_totals = {
            cur: inc_totals.get(cur, 0) - exp_totals.get(cur, 0)
            for cur in set(list(exp_totals.keys()) + list(inc_totals.keys()))
        }

        lines = [f"📊 <b>ملخص النهاردة</b> ({today}):\n"]
        for e in expenses:
            sign = "🔴" if e.is_expense() else "🟢"
            desc = f" — {e.description}" if e.description else ""
            lines.append(f"  {sign} {e.category}: {_fmt(e.amount, e.currency)}{desc}")

        lines.append(f"\n💸 إجمالي المصاريف: <b>{_fmt_totals(exp_totals)}</b>")
        if inc_totals:
            lines.append(f"💰 إجمالي الدخل: <b>{_fmt_totals(inc_totals)}</b>")
        lines.append(f"📈 الصافي: <b>{_fmt_totals(net_totals)}</b>")
        lines.append(f"\n📝 عدد المعاملات: {len(expenses)}")
        return "\n".join(lines)

    async def get_month_summary(self, user_id: int, year: Optional[int] = None, month: Optional[int] = None) -> str:
        """Get a summary of a specific month's transactions, grouped by currency."""
        today = date.today()
        y = year or today.year
        m = month or today.month

        start, end = _month_bounds(y, m)
        expenses = await self.repo.get_by_date_range(user_id, start, end)

        exp_totals = _totals_by_currency(expenses, "expense")
        inc_totals = _totals_by_currency(expenses, "income")
        net_totals = {
            cur: inc_totals.get(cur, 0) - exp_totals.get(cur, 0)
            for cur in set(list(exp_totals.keys()) + list(inc_totals.keys()))
        }

        # Group by (category, currency)
        cat_totals: dict[tuple[str, str], float] = {}
        for e in expenses:
            if e.is_expense():
                key = (e.category, e.currency)
                cat_totals[key] = cat_totals.get(key, 0) + e.amount

        months_ar = [
            "", "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
            "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
        ]

        lines = [f"📊 <b>ملخص شهر {months_ar[m]} {y}</b>\n"]
        lines.append(f"💸 إجمالي المصاريف: <b>{_fmt_totals(exp_totals) if exp_totals else '0.00'}</b>")
        if inc_totals:
            lines.append(f"💰 إجمالي الدخل: <b>{_fmt_totals(inc_totals)}</b>")
        lines.append(f"📈 الصافي: <b>{_fmt_totals(net_totals) if net_totals else '0.00'}</b>")
        lines.append("")

        if cat_totals:
            lines.append("📂 <b>توزيع المصاريف:</b>")
            for (cat, cur), total in sorted(cat_totals.items(), key=lambda x: -x[1]):
                lines.append(f"  • {cat}: {_fmt(total, cur)}")

        return "\n".join(lines)

    async def get_week_summary(self, user_id: int) -> str:
        """Get a summary of the last 7 days."""
        today = date.today()
        week_start = today - timedelta(days=6)

        expenses = await self.repo.get_by_date_range(user_id, week_start, today)
        if not expenses:
            return "📭 مفيش معاملات في آخر ٧ أيام."

        exp_totals = _totals_by_currency(expenses, "expense")
        inc_totals = _totals_by_currency(expenses, "income")
        net_totals = {
            cur: inc_totals.get(cur, 0) - exp_totals.get(cur, 0)
            for cur in set(list(exp_totals.keys()) + list(inc_totals.keys()))
        }
        exp_count = sum(1 for e in expenses if e.is_expense())

        # Group by (category, currency)
        cat_totals: dict[tuple[str, str], float] = {}
        for e in expenses:
            if e.is_expense():
                key = (e.category, e.currency)
                cat_totals[key] = cat_totals.get(key, 0) + e.amount

        lines = [f"📊 <b>ملخص آخر ٧ أيام</b> ({week_start} → {today})\n"]
        lines.append(f"💸 إجمالي المصاريف: <b>{_fmt_totals(exp_totals)}</b>")
        if inc_totals:
            lines.append(f"💰 إجمالي الدخل: <b>{_fmt_totals(inc_totals)}</b>")
        lines.append(f"📈 الصافي: <b>{_fmt_totals(net_totals)}</b>")
        lines.append(f"📝 عدد المعاملات: {exp_count}")
        lines.append("")

        if cat_totals:
            lines.append("📂 <b>توزيع المصاريف:</b>")
            for (cat, cur), total in sorted(cat_totals.items(), key=lambda x: -x[1]):
                lines.append(f"  • {cat}: {_fmt(total, cur)}")

        return "\n".join(lines)

    async def get_balance(self, user_id: int) -> str:
        """Get overall balance (all-time), grouped by currency."""
        all_expenses = await self.repo.get_by_date_range(user_id, date(1970, 1, 1), date.today())

        today = date.today()
        month_start, month_end = _month_bounds(today.year, today.month)
        month_expenses = [e for e in all_expenses if month_start <= e.date <= month_end]

        exp_all = _totals_by_currency(all_expenses, "expense")
        inc_all = _totals_by_currency(all_expenses, "income")
        bal_all = {
            cur: inc_all.get(cur, 0) - exp_all.get(cur, 0)
            for cur in set(list(exp_all.keys()) + list(inc_all.keys()))
        }

        exp_month = _totals_by_currency(month_expenses, "expense")
        inc_month = _totals_by_currency(month_expenses, "income")
        net_month = {
            cur: inc_month.get(cur, 0) - exp_month.get(cur, 0)
            for cur in set(list(exp_month.keys()) + list(inc_month.keys()))
        }

        months_ar = [
            "", "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
            "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
        ]

        lines = ["🏦 <b>رصيد الحساب</b>\n"]
        lines.append(f"💰 إجمالي الدخل: {_fmt_totals(inc_all) if inc_all else '0.00'}")
        lines.append(f"💸 إجمالي المصاريف: {_fmt_totals(exp_all) if exp_all else '0.00'}")
        lines.append(f"\n📊 <b>الرصيد الكلي:</b> {_fmt_totals(bal_all) if bal_all else '0.00'}")

        lines.append(f"\n📅 <b>شهر {months_ar[today.month]} {today.year}:</b>")
        lines.append(f"  💰 دخل: {_fmt_totals(inc_month) if inc_month else '0.00'}")
        lines.append(f"  💸 مصاريف: {_fmt_totals(exp_month) if exp_month else '0.00'}")
        lines.append(f"  📈 صافي: {_fmt_totals(net_month) if net_month else '0.00'}")

        return "\n".join(lines)

    async def get_last_expenses(self, user_id: int, n: int = 5) -> str:
        """Get the last N transactions for a user."""
        expenses = await self.repo.get_last_n(user_id, n)
        if not expenses:
            return "📭 مفيش معاملات مسجلة."

        lines = [f"🕓 <b>آخر {len(expenses)} معاملات:</b>\n"]
        for e in expenses:
            sign = "🔴" if e.is_expense() else "🟢"
            desc = f" — {e.description}" if e.description else ""
            lines.append(f"  {sign} #{e.id} | {e.date} | {e.category} | {_fmt(e.amount, e.currency)}{desc}")
        lines.append("\n💡 للحذف: /delete | لتعديل: /edit")
        return "\n".join(lines)

    async def search_transactions(self, user_id: int, query: str) -> str:
        """Search transactions by text."""
        results = await self.repo.search_by_text(user_id, query)
        if not results:
            return f"📭 مفيش نتائج للبحث عن \"{query}\"."

        total = sum(e.amount for e in results)
        lines = [f"🔍 <b>نتائج البحث عن \"{query}\"</b> ({len(results)} نتيجة):\n"]
        for e in results:
            sign = "🔴" if e.is_expense() else "🟢"
            desc = f" — {e.description}" if e.description else ""
            lines.append(f"  {sign} #{e.id} | {e.date} | {e.category} | {_fmt(e.amount, e.currency)}{desc}")

        lines.append(f"\n💶 الإجمالي: <b>{_fmt(total)}</b>")
        return "\n".join(lines)

    async def get_date_range_report(self, user_id: int, start: date, end: date) -> str:
        """Get a detailed report for a specific date range."""
        expenses = await self.repo.get_by_date_range(user_id, start, end)
        if not expenses:
            return f"📭 مفيش معاملات في الفترة {start} → {end}."

        total_exp = sum(e.amount for e in expenses if e.is_expense())
        total_inc = sum(e.amount for e in expenses if e.is_income())
        currencies = await self.repo.get_currencies_in_range(user_id, start, end)
        cur = currencies[0] if currencies else ""

        cat_totals = {}
        for e in expenses:
            if e.is_expense():
                cat_totals[e.category] = cat_totals.get(e.category, 0) + e.amount

        num_days = (end - start).days + 1
        daily_avg = total_exp / num_days if num_days > 0 else 0

        lines = [f"📋 <b>تقرير الفترة</b> {start} → {end} ({num_days} يوم)\n"]
        lines.append(f"💸 إجمالي المصاريف: <b>{_fmt(total_exp, cur)}</b>")
        if total_inc > 0:
            lines.append(f"💰 إجمالي الدخل: <b>{_fmt(total_inc, cur)}</b>")
        lines.append(f"📈 الصافي: <b>{_fmt(total_inc - total_exp, cur)}</b>")
        lines.append(f"📊 المعدل اليومي: {_fmt(daily_avg, cur)}")
        lines.append(f"📝 عدد المعاملات: {len(expenses)}")
        lines.append("")

        if cat_totals:
            lines.append("📂 <b>توزيع المصاريف:</b>")
            for cat, total in sorted(cat_totals.items(), key=lambda x: -x[1]):
                pct = (total / total_exp * 100) if total_exp > 0 else 0
                lines.append(f"  • {cat}: {_fmt(total, cur)} ({pct:.0f}%)")

        return "\n".join(lines) + self._currency_warning(currencies)

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

        s1, e1 = _month_bounds(y1, m1)
        s2, e2 = _month_bounds(y2, m2)

        cats1 = {c["category"]: c["total"] for c in await self.repo.get_category_summary(user_id, s1, e1)}
        cats2 = {c["category"]: c["total"] for c in await self.repo.get_category_summary(user_id, s2, e2)}
        all_cats = sorted(set(list(cats1.keys()) + list(cats2.keys())))

        currencies = await self.repo.get_currencies_in_range(user_id, s2, e2)
        cur = currencies[0] if currencies else ""

        months_ar = [
            "", "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
            "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
        ]

        lines = [f"📊 <b>مقارنة {months_ar[m1]} ↔ {months_ar[m2]}</b>\n"]

        for cat in all_cats:
            v1 = cats1.get(cat, 0)
            v2 = cats2.get(cat, 0)
            diff = v2 - v1
            if diff > 0:
                arrow = "📈"
            elif diff < 0:
                arrow = "📉"
            else:
                arrow = "➡️"
            pct_change = ""
            if v1 > 0:
                pct_change = f" ({(diff / v1 * 100):+.0f}%)"
            lines.append(f"  {arrow} {cat}: {_fmt(v1)} → {_fmt(v2)}{pct_change}")

        # Totals
        diff_exp = t2["total_expenses"] - t1["total_expenses"]
        diff_inc = t2["total_income"] - t1["total_income"]
        exp_arrow = "📈" if diff_exp > 0 else "📉" if diff_exp < 0 else "➡️"
        inc_arrow = "📈" if diff_inc > 0 else "📉" if diff_inc < 0 else "➡️"

        lines.append(f"\n{'─' * 30}")
        lines.append(f"{exp_arrow} <b>المصاريف:</b> {_fmt(t1['total_expenses'], cur)} → {_fmt(t2['total_expenses'], cur)} ({diff_exp:+,.0f})")
        if t1['total_income'] > 0 or t2['total_income'] > 0:
            lines.append(f"{inc_arrow} <b>الدخل:</b> {_fmt(t1['total_income'], cur)} → {_fmt(t2['total_income'], cur)} ({diff_inc:+,.0f})")

        return "\n".join(lines)

    async def get_category_details(self, user_id: int, category: str,
                             year: int = None, month: int = None) -> str:
        """
        Get all transactions for a specific category in a month.
        """
        today = date.today()
        y = year or today.year
        m = month or today.month

        start, end = _month_bounds(y, m)

        expenses = await self.repo.get_by_category(user_id, category, start, end)
        if not expenses:
            return f"📭 مفيش معاملات في فئة \"{category}\" هذا الشهر."

        total = sum(e.amount for e in expenses)
        cur = expenses[0].currency if expenses else ""

        months_ar = [
            "", "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
            "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
        ]

        lines = [f"🏷️ <b>فئة \"{category}\" — {months_ar[m]}</b>\n"]
        for e in expenses:
            sign = "🔴" if e.is_expense() else "🟢"
            desc = f" — {e.description}" if e.description else ""
            lines.append(f"  {sign} #{e.id} | {e.date} | {_fmt(e.amount, e.currency)}{desc}")

        lines.append(f"\n💶 الإجمالي: <b>{_fmt(total, cur)}</b> ({len(expenses)} معاملة)")
        return "\n".join(lines)

    async def edit_expense(self, expense_id: int, user_id: int,
                     amount: float = None, category: str = None,
                     description: str = None) -> str:
        """
        Edit an existing expense's fields directly (no AI).
        """
        expense = await self.repo.get_by_id(expense_id, user_id)
        if not expense:
            return f"⚠️ العملية رقم #{expense_id} مش موجودة أو مش ليك."

        changes = []
        if amount is not None:
            expense.amount = amount
            changes.append(f"💶 المبلغ: {_fmt(amount, expense.currency)}")
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

    async def undo_last(self, user_id: int) -> str:
        """Delete the most recent transaction for a user."""
        expenses = await self.repo.get_last_n(user_id, 1)
        if not expenses:
            return "📭 مفيش معاملات لإلغائها."

        expense = expenses[0]
        deleted = await self.repo.delete(expense.id, user_id)
        if deleted:
            sign = "💸" if expense.is_expense() else "💰"
            return (
                f"↩️ تم إلغاء آخر معاملة:\n"
                f"  {sign} #{expense.id} | {expense.category} | {_fmt(expense.amount, expense.currency)}\n"
                f"  📅 {expense.date}"
            )
        return "⚠️ فشل الإلغاء. حاول تاني."

"""
services/recurring_service.py
------------------------------
Business logic for managing recurring payments and sending reminders.
"""

from datetime import date

from ai.gemini_parser import parse_recurring
from models.recurring import RecurringPayment
from repositories.recurring_repo import RecurringRepository
from utils.logger import get_logger

logger = get_logger(__name__)


class RecurringService:
    """
    Handles all business logic for recurring payments.

    Responsibilities:
        - Parse user text to create recurring payments.
        - Check for upcoming due dates.
        - Send reminders via the bot.
    """

    def __init__(self):
        self.repo = RecurringRepository()

    def add_from_text(self, user_id: int, text: str) -> dict:
        """
        Parse natural text and save as a recurring payment.

        Args:
            user_id: Telegram user ID.
            text: Raw message, e.g. "اشتراك نتفليكس ١٥ يورو كل شهر".

        Returns:
            Dict with 'success' and 'message' or 'error' and 'question'.
        """
        parsed = parse_recurring(text)

        if "error" in parsed:
            return {"success": False, "question": parsed.get("question", "حاول تاني.")}

        try:
            payment = RecurringPayment(
                user_id=user_id,
                name=parsed["name"],
                amount=float(parsed["amount"]),
                frequency=parsed["frequency"],
                next_due_date=date.fromisoformat(parsed["next_due_date"]),
            )
            saved = self.repo.add(payment)

            freq_ar = {
                "daily": "يومي",
                "weekly": "أسبوعي",
                "monthly": "شهري",
                "yearly": "سنوي",
            }

            msg = (
                f"🔁 تم إضافة دفعة متكررة:\n"
                f"  📌 الاسم: {saved.name}\n"
                f"  💶 المبلغ: {saved.amount:.2f}€\n"
                f"  🔄 التكرار: {freq_ar.get(saved.frequency, saved.frequency)}\n"
                f"  📅 الموعد القادم: {saved.next_due_date}\n"
                f"  🔖 رقم: #{saved.id}"
            )
            return {"success": True, "message": msg}

        except (KeyError, ValueError) as e:
            logger.error(f"Validation error for recurring: {e}, parsed: {parsed}")
            return {"success": False, "question": "حصل مشكلة. حاول تاني بصيغة واضحة."}

    def list_active(self, user_id: int) -> str:
        """
        Get a formatted list of all active recurring payments.

        Returns:
            Formatted string or "no payments" message.
        """
        payments = self.repo.get_all(user_id, active_only=True)
        if not payments:
            return "📭 مفيش مدفوعات متكررة مسجلة."

        freq_ar = {"daily": "يومي", "weekly": "أسبوعي", "monthly": "شهري", "yearly": "سنوي"}

        lines = ["🔁 المدفوعات المتكررة النشطة:\n"]
        total = 0.0
        for p in payments:
            lines.append(
                f"  #{p.id} {p.name}: {p.amount:.2f}€ "
                f"({freq_ar.get(p.frequency, p.frequency)}) "
                f"- القادم: {p.next_due_date}"
            )
            if p.frequency == "monthly":
                total += p.amount

        if total > 0:
            lines.append(f"\n💶 إجمالي الالتزامات الشهرية: {total:.2f}€")
        return "\n".join(lines)

    def delete_payment(self, payment_id: int, user_id: int) -> str:
        """Delete a recurring payment by ID."""
        deleted = self.repo.delete(payment_id, user_id)
        if deleted:
            return f"🗑️ تم حذف الدفعة المتكررة #{payment_id}."
        return f"⚠️ الدفعة #{payment_id} مش موجودة."

    def toggle_payment(self, payment_id: int, user_id: int, active: bool) -> str:
        """Enable or disable a recurring payment."""
        updated = self.repo.toggle_active(payment_id, user_id, active)
        if updated:
            status = "تفعيل ✅" if active else "إيقاف ❌"
            return f"تم {status} الدفعة #{payment_id}."
        return f"⚠️ الدفعة #{payment_id} مش موجودة."

    def get_due_reminders(self) -> list[RecurringPayment]:
        """
        Get all payments that need reminders sent.
        Called by the scheduler.

        Returns:
            List of RecurringPayment objects due within remind_days_before.
        """
        return self.repo.get_due_soon(days_ahead=2)

    def advance_due_date(self, payment: RecurringPayment) -> None:
        """Advance a payment's next due date after processing."""
        self.repo.advance_due_date(payment)

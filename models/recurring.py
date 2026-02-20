"""
models/recurring.py
-------------------
Domain model for recurring (scheduled) payments.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class RecurringPayment:
    """
    Represents a recurring payment (subscription, bill, etc.).

    Attributes:
        id: Database primary key (None for new records).
        user_id: Telegram user ID.
        name: Friendly name of the payment (e.g., 'Netflix', 'Rent').
        amount: Payment amount.
        currency: ISO currency code (default: EUR).
        frequency: How often ('daily', 'weekly', 'monthly', 'yearly').
        next_due_date: The next upcoming payment date.
        remind_days_before: How many days before due date to send a reminder.
        active: Whether this recurring payment is currently active.
        created_at: Timestamp when the record was created.
    """
    user_id: int
    name: str
    amount: float
    frequency: str  # 'daily' | 'weekly' | 'monthly' | 'yearly'
    next_due_date: date
    currency: str = "EUR"
    remind_days_before: int = 1
    active: bool = True
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    def __str__(self) -> str:
        status = "✅" if self.active else "❌"
        return f"{status} {self.name}: {self.amount:.2f} {self.currency} ({self.frequency}) - Next: {self.next_due_date}"

"""
models/expense.py
-----------------
Domain model for financial transactions (expenses and income).
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class Expense:
    """
    Represents a single financial transaction.

    Attributes:
        id: Database primary key (None for new records).
        user_id: Telegram user ID.
        type: Either 'expense' or 'income'.
        amount: Transaction amount in the specified currency.
        currency: ISO currency code (default: EUR).
        category: Spending category (e.g., food, transport).
        description: Optional human-readable note.
        date: Date of the transaction.
        raw_text: The original message text from the user.
        created_at: Timestamp when the record was created.
    """
    user_id: int
    type: str  # 'expense' | 'income'
    amount: float
    category: str
    date: date = field(default_factory=date.today)
    currency: str = "EUR"
    description: Optional[str] = None
    raw_text: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    def is_expense(self) -> bool:
        """Returns True if this is an expense transaction."""
        return self.type == "expense"

    def is_income(self) -> bool:
        """Returns True if this is an income transaction."""
        return self.type == "income"

    def __str__(self) -> str:
        sign = "-" if self.is_expense() else "+"
        return f"{sign}{self.amount:.2f} {self.currency} | {self.category} | {self.date}"

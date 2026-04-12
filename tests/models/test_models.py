import pytest
from datetime import date
from models.expense import Expense
from models.recurring import RecurringPayment


def test_expense_creation():
    exp = Expense(
        user_id=123,
        type="expense",
        amount=50.5,
        category="Food"
    )
    assert exp.user_id == 123
    assert exp.is_expense() is True
    assert exp.is_income() is False
    assert exp.currency == "EUR"
    assert exp.date == date.today()


def test_income_creation():
    inc = Expense(
        user_id=123,
        type="income",
        amount=1000.0,
        category="Salary"
    )
    assert inc.is_expense() is False
    assert inc.is_income() is True
    assert str(inc).startswith("+1000.00 EUR")


def test_recurring_payment_creation():
    rp = RecurringPayment(
        user_id=123,
        name="Netflix",
        amount=15.0,
        frequency="monthly",
        next_due_date=date.today()
    )
    assert rp.user_id == 123
    assert rp.amount == 15.0
    assert rp.frequency == "monthly"
    assert rp.active is True

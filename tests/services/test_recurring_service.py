"""
test_recurring_service.py
--------------------------
Tests for recurring payment service.

Tests:
    - test_add_from_text
    - test_get_upcoming
    - test_send_reminders
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import date, timedelta
from services.recurring_service import RecurringService
from models.recurring import RecurringPayment


@pytest.fixture
def recurring_service(mock_recurring_repo):
    """RecurringService with mocked repository."""
    service = RecurringService()
    service.repo = mock_recurring_repo
    return service


@pytest.mark.asyncio
@patch('services.recurring_service.parse_recurring')
async def test_add_from_text(
    mock_parse, recurring_service, mock_recurring_repo
):
    """Test adding recurring payment from text."""
    mock_parse.return_value = {
        "frequency": "monthly",
        "amount": 500.0,
        "category": "Rent",
        "description": "Apartment rent"
    }
    
    mock_recurring_repo.add.return_value = RecurringPayment(
        user_id=1, amount=500.0, name="Rent"
    )
    
    result = await recurring_service.add_from_text(
        user_id=1, text="كل شهر 500 إيجار"
    )
    
    assert result["success"] is True
    mock_recurring_repo.add.assert_called_once()


@pytest.mark.asyncio
async def test_get_upcoming(recurring_service, mock_recurring_repo):
    """Test getting upcoming recurring payments."""
    upcoming = [
        RecurringPayment(
            user_id=1,
            amount=500.0,
            name="Rent",
            frequency="monthly",
            next_due_date=date.today() + timedelta(days=5)
        )
    ]
    mock_recurring_repo.get_upcoming_due.return_value = upcoming
    
    result = await recurring_service.get_upcoming(user_id=1)
    
    assert result["success"] is True
    mock_recurring_repo.get_upcoming_due.assert_called_once()


@pytest.mark.asyncio
async def test_send_reminders(recurring_service, mock_recurring_repo):
    """Test sending reminders for due payments."""
    due_items = [
        RecurringPayment(user_id=1, amount=500.0, name="Rent", frequency="monthly")
    ]
    mock_recurring_repo.get_upcoming_due.return_value = due_items
    mock_recurring_repo.mark_reminded = AsyncMock()
    
    result = await recurring_service.send_reminders()
    
    assert result["success"] is True
    mock_recurring_repo.mark_reminded.assert_called()

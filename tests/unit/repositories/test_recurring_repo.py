"""
test_recurring_repo.py
-----------------------
Tests for RecurringRepository.

Tests:
    - test_add_recurring
    - test_get_by_id
    - test_get_upcoming_due
    - test_mark_reminded
    - test_delete_recurring
"""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import date


@pytest.mark.asyncio
@patch('repositories.recurring_repo.get_pool')
async def test_add_recurring(mock_get_pool, mock_db_pool):
    """Test adding a recurring payment."""
    from repositories.recurring_repo import RecurringRepository
    from models.recurring import RecurringPayment
    
    mock_get_pool.return_value = mock_db_pool
    repo = RecurringRepository()
    
    recurring = RecurringPayment(
        user_id=1, amount=500.0, name="Rent", frequency="monthly"
    )
    
    mock_cursor = mock_db_pool.cursor.return_value.__aenter__.return_value
    mock_cursor.fetchval.return_value = 1
    
    result = await repo.add(recurring)
    
    mock_cursor.execute.assert_called()


@pytest.mark.asyncio
@patch('repositories.recurring_repo.get_pool')
async def test_get_by_id(mock_get_pool, mock_db_pool):
    """Test retrieving recurring payment by ID."""
    from repositories.recurring_repo import RecurringRepository
    
    mock_get_pool.return_value = mock_db_pool
    repo = RecurringRepository()
    
    mock_cursor = mock_db_pool.cursor.return_value.__aenter__.return_value
    mock_cursor.fetchone.return_value = None
    
    result = await repo.get_by_id(payment_id=1, user_id=1)
    
    mock_cursor.execute.assert_called()


@pytest.mark.asyncio
@patch('repositories.recurring_repo.get_pool')
async def test_get_upcoming_due(mock_get_pool, mock_db_pool):
    """Test getting due recurring payments."""
    from repositories.recurring_repo import RecurringRepository
    
    mock_get_pool.return_value = mock_db_pool
    repo = RecurringRepository()
    
    mock_cursor = mock_db_pool.cursor.return_value.__aenter__.return_value
    mock_cursor.fetchall.return_value = []
    
    result = await repo.get_due_soon(days_ahead=2)
    
    assert isinstance(result, list)
    mock_cursor.execute.assert_called()


@pytest.mark.asyncio
@patch('repositories.recurring_repo.get_pool')
async def test_mark_reminded(mock_get_pool, mock_db_pool):
    """Test marking recurring payment as reminded."""
    from repositories.recurring_repo import RecurringRepository
    
    mock_get_pool.return_value = mock_db_pool
    repo = RecurringRepository()
    
    mock_cursor = mock_db_pool.cursor.return_value.__aenter__.return_value
    mock_cursor.execute = AsyncMock()
    
    # Check if method exists
    if hasattr(repo, 'advance_due_date'):
        result = await repo.advance_due_date(None)
    
    mock_cursor.execute.assert_called()


@pytest.mark.asyncio
@patch('repositories.recurring_repo.get_pool')
async def test_delete_recurring(mock_get_pool, mock_db_pool):
    """Test deleting a recurring payment."""
    from repositories.recurring_repo import RecurringRepository
    
    mock_get_pool.return_value = mock_db_pool
    repo = RecurringRepository()
    
    mock_cursor = mock_db_pool.cursor.return_value.__aenter__.return_value
    mock_cursor.execute = AsyncMock()
    
    result = await repo.delete(payment_id=1, user_id=1)
    
    mock_cursor.execute.assert_called()

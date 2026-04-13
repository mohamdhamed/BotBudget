"""
test_expense_repo.py
--------------------
Tests for ExpenseRepository database access layer.

Tests CRUD operations:
    - test_add_expense
    - test_get_by_id
    - test_get_by_date_range
    - test_get_category_summary
    - test_get_monthly_total
    - test_get_by_category
    - test_search_by_text
    - test_get_overall_balance
    - test_update_expense
    - test_delete_expense
"""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import date
from models.expense import Expense


@pytest.mark.asyncio
@patch('repositories.expense_repo.get_pool')
async def test_add_expense(mock_get_pool, mock_db_pool):
    """Test adding a new expense."""
    from repositories.expense_repo import ExpenseRepository
    
    mock_get_pool.return_value = mock_db_pool
    
    repo = ExpenseRepository()
    expense = Expense(user_id=1, type="expense", amount=100.0, category="Food", date=date.today())
    
    # Setup mock to return new ID
    mock_cursor = mock_db_pool.cursor.return_value.__aenter__.return_value
    mock_cursor.fetchone.return_value = (42, None)  # ID and created_at
    
    result = await repo.add(expense)
    
    # Verify add was called
    mock_cursor.execute.assert_called_once()


@pytest.mark.asyncio
@patch('repositories.expense_repo.get_pool')
async def test_get_by_id(mock_get_pool, mock_db_pool):
    """Test retrieving expense by ID."""
    from repositories.expense_repo import ExpenseRepository
    
    mock_get_pool.return_value = mock_db_pool
    repo = ExpenseRepository()
    
    # Setup mock return value
    mock_cursor = mock_db_pool.cursor.return_value.__aenter__.return_value
    mock_cursor.fetchone.return_value = (
        1, 1, 100.0, "Food", date.today(), "description", "expense"
    )
    
    result = await repo.get_by_id(user_id=1, expense_id=1)
    
    mock_cursor.execute.assert_called_once()


@pytest.mark.asyncio
@patch('repositories.expense_repo.get_pool')
async def test_get_by_date_range(mock_get_pool, mock_db_pool):
    """Test retrieving expenses by date range."""
    from repositories.expense_repo import ExpenseRepository
    
    mock_get_pool.return_value = mock_db_pool
    repo = ExpenseRepository()
    
    mock_cursor = mock_db_pool.cursor.return_value.__aenter__.return_value
    mock_cursor.fetchall.return_value = []
    
    result = await repo.get_by_date_range(
        user_id=1, 
        start=date.today(), 
        end=date.today()
    )
    
    assert isinstance(result, list)
    mock_cursor.execute.assert_called_once()


@pytest.mark.asyncio
@patch('repositories.expense_repo.get_pool')
async def test_get_category_summary(mock_get_pool, mock_db_pool):
    """Test getting aggregate by category."""
    from repositories.expense_repo import ExpenseRepository
    from datetime import date
    
    mock_get_pool.return_value = mock_db_pool
    repo = ExpenseRepository()
    
    mock_cursor = mock_db_pool.cursor.return_value.__aenter__.return_value
    mock_cursor.fetchall.return_value = [
        ("Food", 450.0),
        ("Transport", 150.0)
    ]
    
    result = await repo.get_category_summary(
        user_id=1,
        start=date.today(),
        end=date.today()
    )
    
    assert isinstance(result, list)
    mock_cursor.execute.assert_called_once()


@pytest.mark.asyncio
@patch('repositories.expense_repo.get_pool')
async def test_get_monthly_total(mock_get_pool, mock_db_pool):
    """Test getting monthly total."""
    from repositories.expense_repo import ExpenseRepository
    
    mock_get_pool.return_value = mock_db_pool
    repo = ExpenseRepository()
    
    mock_cursor = mock_db_pool.cursor.return_value.__aenter__.return_value
    mock_cursor.fetchval.return_value = 1500.0
    
    result = await repo.get_monthly_total(user_id=1, year=2026, month=4)
    
    mock_cursor.execute.assert_called_once()


@pytest.mark.asyncio
@patch('repositories.expense_repo.get_pool')
async def test_get_by_category(mock_get_pool, mock_db_pool):
    """Test filtering expenses by category."""
    from repositories.expense_repo import ExpenseRepository
    
    mock_get_pool.return_value = mock_db_pool
    repo = ExpenseRepository()
    
    mock_cursor = mock_db_pool.cursor.return_value.__aenter__.return_value
    mock_cursor.fetchall.return_value = []
    
    result = await repo.get_by_category(
        user_id=1, 
        category="Food",
        start=date.today(),
        end=date.today()
    )
    
    assert isinstance(result, list)
    mock_cursor.execute.assert_called_once()


@pytest.mark.asyncio
@patch('repositories.expense_repo.get_pool')
async def test_search_by_text(mock_get_pool, mock_db_pool):
    """Test text search in expenses."""
    from repositories.expense_repo import ExpenseRepository
    
    mock_get_pool.return_value = mock_db_pool
    repo = ExpenseRepository()
    
    mock_cursor = mock_db_pool.cursor.return_value.__aenter__.return_value
    mock_cursor.fetchall.return_value = []
    
    result = await repo.search_by_text(user_id=1, query="coffee")
    
    assert isinstance(result, list)
    mock_cursor.execute.assert_called_once()


@pytest.mark.asyncio
@patch('repositories.expense_repo.get_pool')
async def test_get_overall_balance(mock_get_pool, mock_db_pool):
    """Test getting overall balance (income - expense)."""
    from repositories.expense_repo import ExpenseRepository
    
    mock_get_pool.return_value = mock_db_pool
    repo = ExpenseRepository()
    
    mock_cursor = mock_db_pool.cursor.return_value.__aenter__.return_value
    # Mock returns total debit and credit
    mock_cursor.execute = AsyncMock()
    
    result = await repo.get_overall_balance(user_id=1)
    
    mock_cursor.execute.assert_called()


@pytest.mark.asyncio
@patch('repositories.expense_repo.get_pool')
async def test_update_expense(mock_get_pool, mock_db_pool):
    """Test updating an expense."""
    from repositories.expense_repo import ExpenseRepository
    
    mock_get_pool.return_value = mock_db_pool
    repo = ExpenseRepository()
    
    expense = Expense(id=1, user_id=1, type="expense", amount=200.0, category="Food", date=date.today())
    
    mock_cursor = mock_db_pool.cursor.return_value.__aenter__.return_value
    mock_cursor.execute = AsyncMock()
    
    result = await repo.update(expense)
    
    mock_cursor.execute.assert_called()


@pytest.mark.asyncio
@patch('repositories.expense_repo.get_pool')
async def test_delete_expense(mock_get_pool, mock_db_pool):
    """Test deleting an expense."""
    from repositories.expense_repo import ExpenseRepository
    
    mock_get_pool.return_value = mock_db_pool
    repo = ExpenseRepository()
    
    mock_cursor = mock_db_pool.cursor.return_value.__aenter__.return_value
    mock_cursor.execute = AsyncMock()
    
    result = await repo.delete(expense_id=1, user_id=1)
    
    mock_cursor.execute.assert_called()

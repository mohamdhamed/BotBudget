"""
test_budget_repo.py
--------------------
Tests for BudgetRepository.

Tests:
    - test_set_budget
    - test_get_budget
    - test_delete_budget
"""

import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
@patch('repositories.budget_repo.get_pool')
async def test_set_budget(mock_get_pool, mock_db_pool):
    """Test setting a budget."""
    from repositories.budget_repo import BudgetRepository
    
    mock_get_pool.return_value = mock_db_pool
    repo = BudgetRepository()
    
    mock_cursor = mock_db_pool.cursor.return_value.__aenter__.return_value
    mock_cursor.fetchone.return_value = (1,)
    
    result = await repo.set_budget(user_id=1, category="Food", limit_amount=500.0)
    
    mock_cursor.execute.assert_called()


@pytest.mark.asyncio
@patch('repositories.budget_repo.get_pool')
async def test_get_budget(mock_get_pool, mock_db_pool):
    """Test retrieving a budget."""
    from repositories.budget_repo import BudgetRepository
    
    mock_get_pool.return_value = mock_db_pool
    repo = BudgetRepository()
    
    mock_cursor = mock_db_pool.cursor.return_value.__aenter__.return_value
    mock_cursor.fetchone.return_value = (500.0,)
    
    result = await repo.get_budget(user_id=1, category="Food")
    
    mock_cursor.execute.assert_called()


@pytest.mark.asyncio
@patch('repositories.budget_repo.get_pool')
async def test_delete_budget(mock_get_pool, mock_db_pool):
    """Test deleting a budget."""
    from repositories.budget_repo import BudgetRepository
    
    mock_get_pool.return_value = mock_db_pool
    repo = BudgetRepository()
    
    mock_cursor = mock_db_pool.cursor.return_value.__aenter__.return_value
    mock_cursor.execute = AsyncMock()
    
    result = await repo.delete_budget(user_id=1, category="Food")
    
    mock_cursor.execute.assert_called()

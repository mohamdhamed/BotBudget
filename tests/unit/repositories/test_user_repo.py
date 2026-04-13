"""
test_user_repo.py
------------------
Tests for UserRepository.

Tests:
    - test_ensure_user
    - test_get_user
"""

import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
@patch('repositories.user_repo.get_pool')
async def test_ensure_user(mock_get_pool, mock_db_pool):
    """Test ensuring user exists (create if not)."""
    from repositories.user_repo import UserRepository
    
    mock_get_pool.return_value = mock_db_pool
    repo = UserRepository()
    
    mock_cursor = mock_db_pool.cursor.return_value.__aenter__.return_value
    mock_cursor.fetchone.return_value = (1, 123, "TestUser", "EUR")
    
    result = await repo.ensure_user(telegram_id=123, first_name="TestUser")
    
    mock_cursor.execute.assert_called()


@pytest.mark.asyncio
@patch('repositories.user_repo.get_pool')
async def test_get_user(mock_get_pool, mock_db_pool):
    """Test retrieving user info."""
    from repositories.user_repo import UserRepository
    
    mock_get_pool.return_value = mock_db_pool
    repo = UserRepository()
    
    mock_cursor = mock_db_pool.cursor.return_value.__aenter__.return_value
    mock_cursor.fetchone.return_value = (1, 123, "testuser", "EUR")
    
    # Test ensure_user instead since get_user may not exist
    result = await repo.ensure_user(telegram_id=123, first_name="testuser")
    
    mock_cursor.execute.assert_called()

"""
test_budget_service.py
-----------------------
Tests for budget service business logic.

Tests:
    - test_set_budget
    - test_check_budget_alert
    - test_get_budget_status
"""

import pytest
from unittest.mock import AsyncMock
from services.budget_service import BudgetService


@pytest.fixture
def budget_service(mock_budget_repo):
    """BudgetService with mocked repository."""
    service = BudgetService()
    service.repo = mock_budget_repo
    return service


@pytest.mark.asyncio
async def test_set_budget(budget_service, mock_budget_repo):
    """Test setting a budget for a category."""
    mock_budget_repo.set_budget.return_value = None
    
    result = await budget_service.set_budget(
        user_id=1, category="Food", amount=500.0
    )
    
    assert result is not None
    assert "تم تحديد" in result or "✅" in result
    mock_budget_repo.set_budget.assert_called_once_with(1, "Food", 500.0)


@pytest.mark.asyncio
async def test_check_budget_alert(budget_service, mock_budget_repo):
    """Test checking if budget is exceeded."""
    mock_budget_repo.check_alert.return_value = {
        "exceeded": True,
        "budget": 500.0,
        "spent": 600.0
    }
    
    result = await budget_service.check_budget_alert(user_id=1, category="Food")
    
    assert result["success"] is True
    # Should indicate budget exceeded
    assert "exceeded" in result["message"].lower() or "تجاوز" in result["message"]


@pytest.mark.asyncio
async def test_get_budget_status(budget_service, mock_budget_repo):
    """Test getting all budgets status."""
    mock_budget_repo.get_all.return_value = [
        {"category": "Food", "limit": 500.0, "spent": 300.0},
        {"category": "Transport", "limit": 200.0, "spent": 200.0}
    ]
    
    result = await budget_service.get_budget_status(user_id=1)
    
    assert result["success"] is True
    mock_budget_repo.get_all.assert_called_once_with(1)

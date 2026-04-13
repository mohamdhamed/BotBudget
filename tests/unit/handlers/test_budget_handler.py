"""
test_budget_handler.py
----------------------
Tests for budget handler commands.

Tests:
    - test_budget_set_command
    - test_budget_show_command
    - test_budget_delete_command
"""

import pytest
from unittest.mock import patch, AsyncMock
from telegram import Update


@pytest.mark.asyncio
@patch('handlers.budget_handler.rate_limited', lambda f: f)
@patch('handlers.budget_handler.authorized_only', lambda f: f)
@patch('handlers.budget_handler.BudgetService')
async def test_budget_set_command(mock_service_class, mock_update, mock_context):
    """Test /budget set category limit command."""
    from handlers.budget_handler import budget_command
    
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service
    mock_service.set_budget = AsyncMock(
        return_value={"success": True, "message": "✅ تم تحديد الميزانية"}
    )
    
    mock_context.args = ['food', '500']
    
    await budget_command(mock_update, mock_context)
    
    mock_service.set_budget.assert_called_once()
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
@patch('handlers.budget_handler.rate_limited', lambda f: f)
@patch('handlers.budget_handler.authorized_only', lambda f: f)
@patch('handlers.budget_handler.BudgetService')
async def test_budget_show_command(mock_service_class, mock_update, mock_context):
    """Test /budget show command lists all budgets."""
    from handlers.budget_handler import budget_command
    
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service
    mock_service.get_budget_status = AsyncMock(
        return_value={"success": True, "budgets": "Food: 500, Transport: 200"}
    )
    
    mock_context.args = []
    
    await budget_command(mock_update, mock_context)
    
    mock_service.get_budget_status.assert_called_once()
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
@patch('handlers.budget_handler.rate_limited', lambda f: f)
@patch('handlers.budget_handler.authorized_only', lambda f: f)
@patch('handlers.budget_handler.BudgetService')
async def test_budget_delete_command(mock_service_class, mock_update, mock_context):
    """Test /budget delete category command."""
    from handlers.budget_handler import budget_command
    
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service
    mock_service.delete_budget = AsyncMock(
        return_value={"success": True, "message": "✅ تم حذف الميزانية"}
    )
    
    mock_context.args = ['food', 'delete']
    
    await budget_command(mock_update, mock_context)
    
    mock_update.message.reply_text.assert_called_once()

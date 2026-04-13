"""
test_recurring_handler.py
-----------
Tests for recurring payment handler commands.

Tests:
    - test_add_recurring_command
    - test_delete_recurring_command
    - test_recurring_list_command
"""

import pytest
from unittest.mock import patch, AsyncMock
from telegram import Update


@pytest.mark.asyncio
@patch('handlers.recurring_handler.rate_limited', lambda f: f)
@patch('handlers.recurring_handler.authorized_only', lambda f: f)
@patch('handlers.recurring_handler.RecurringService')
async def test_add_recurring_command(mock_service_class, mock_update, mock_context):
    """Test adding recurring payment."""
    from handlers.recurring_handler import add_recurring_command
    
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service
    mock_service.add_from_text = AsyncMock(
        return_value={"success": True, "message": "✅ تم إضافة الدفع المتكرر"}
    )
    
    mock_update.message.text = "/add_recurring كل أسبوع 100 طعام"
    
    await add_recurring_command(mock_update, mock_context)
    
    mock_service.add_from_text.assert_called_once()
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
@patch('handlers.recurring_handler.rate_limited', lambda f: f)
@patch('handlers.recurring_handler.authorized_only', lambda f: f)
@patch('handlers.recurring_handler.RecurringService')
async def test_delete_recurring_command(mock_service_class, mock_update, mock_context):
    """Test deleting recurring payment."""
    from handlers.recurring_handler import delete_recurring_command
    
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service
    mock_service.delete = AsyncMock(
        return_value={"success": True, "message": "✅ تم حذف الدفع"}
    )
    
    mock_context.args = ['5']
    
    await delete_recurring_command(mock_update, mock_context)
    
    mock_service.delete.assert_called_once()
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
@patch('handlers.recurring_handler.rate_limited', lambda f: f)
@patch('handlers.recurring_handler.authorized_only', lambda f: f)
@patch('handlers.recurring_handler.RecurringService')
async def test_recurring_list_command(mock_service_class, mock_update, mock_context):
    """Test listing recurring payments."""
    from handlers.recurring_handler import recurring_command
    
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service
    mock_service.get_upcoming = AsyncMock(
        return_value={"success": True, "recurring": []}
    )
    
    await recurring_command(mock_update, mock_context)
    
    mock_service.get_upcoming.assert_called_once()
    mock_update.message.reply_text.assert_called_once()

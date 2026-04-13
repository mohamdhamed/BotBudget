"""
test_expense_handler.py
-----------------------
Tests for expense handler commands and functions.

Tests:
    - test_handle_text_message_add_expense
    - test_handle_text_message_budget_alert
    - test_today_command
    - test_month_command
    - test_week_command
    - test_delete_command_with_id
    - test_delete_command_no_args
    - test_edit_command
    - test_category_command
    - test_search_command
    - test_report_command
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import date
from telegram import Update
from telegram.ext import ContextTypes


@pytest.mark.asyncio
@patch('security.auth.ADMIN_USER_IDS', [123])
@patch('security.rate_limiter._cleanup', new_callable=AsyncMock)
@patch('security.rate_limiter._count', new_callable=AsyncMock, return_value=0)
@patch('security.rate_limiter._record', new_callable=AsyncMock)
@patch('handlers.expense_handler.parse_transaction')
async def test_handle_text_message_add_expense(mock_parse, mock_record, mock_count, mock_cleanup, mock_update, mock_context):
    """Test adding expense via text message — now shows inline keyboard confirmation."""
    from handlers.expense_handler import handle_text_message

    mock_parse.return_value = {
        "type": "expense",
        "amount": 100.0,
        "category": "طعام",
        "description": "غداء",
        "date": "2026-04-13",
        "confidence": 0.95,
    }
    mock_update.message.text = "صرفت 100 طعام"
    mock_context.user_data = {}

    with patch('handlers.expense_handler.user_repo') as mock_user_repo:
        mock_user_repo.ensure_user = AsyncMock()
        await handle_text_message(mock_update, mock_context)

    # Parser should have been called
    mock_parse.assert_called_once()
    # Inline keyboard preview should be sent
    mock_update.message.reply_text.assert_called_once()
    # Parsed data should be stored in user_data for confirmation
    assert "pending_expense" in mock_context.user_data


@pytest.mark.asyncio
@patch('security.auth.ADMIN_USER_IDS', [123])
@patch('security.rate_limiter._cleanup', new_callable=AsyncMock)
@patch('security.rate_limiter._count', new_callable=AsyncMock, return_value=0)
@patch('security.rate_limiter._record', new_callable=AsyncMock)
@patch('handlers.expense_handler.parse_transaction')
async def test_handle_text_message_budget_alert(mock_parse, mock_record, mock_count, mock_cleanup, mock_update, mock_context):
    """Test that low-confidence parse shows warning flag in preview."""
    from handlers.expense_handler import handle_text_message

    mock_parse.return_value = {
        "type": "expense",
        "amount": 1000.0,
        "category": "طعام",
        "description": "مشتريات",
        "date": "2026-04-13",
        "confidence": 0.5,  # Low confidence → warning shown
    }
    mock_update.message.text = "صرفت 1000 طعام"
    mock_context.user_data = {}

    with patch('handlers.expense_handler.user_repo') as mock_user_repo:
        mock_user_repo.ensure_user = AsyncMock()
        await handle_text_message(mock_update, mock_context)

    mock_parse.assert_called_once()
    # Should still send confirmation keyboard (just with warning note)
    assert mock_update.message.reply_text.called


@pytest.mark.asyncio
@patch('handlers.expense_handler.rate_limited', lambda f: f)
@patch('handlers.expense_handler.authorized_only', lambda f: f)
@patch('handlers.expense_handler.ExpenseService')
async def test_today_command(mock_service_class, mock_update, mock_context):
    """Test /today command shows today's summary."""
    from handlers.expense_handler import today_command
    
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service
    mock_service.get_today_summary = AsyncMock(
        return_value={"success": True, "summary": "Today: 450 IQD"}
    )
    
    await today_command(mock_update, mock_context)
    
    mock_service.get_today_summary.assert_called_once()
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
@patch('handlers.expense_handler.rate_limited', lambda f: f)
@patch('handlers.expense_handler.authorized_only', lambda f: f)
@patch('handlers.expense_handler.ExpenseService')
async def test_month_command(mock_service_class, mock_update, mock_context):
    """Test /month command shows monthly breakdown."""
    from handlers.expense_handler import month_command
    
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service
    mock_service.get_month_summary = AsyncMock(
        return_value={"success": True, "summary": "Food: 1500, Transport: 300"}
    )
    
    await month_command(mock_update, mock_context)
    
    mock_service.get_month_summary.assert_called_once()
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
@patch('handlers.expense_handler.rate_limited', lambda f: f)
@patch('handlers.expense_handler.authorized_only', lambda f: f)
@patch('handlers.expense_handler.ExpenseService')
async def test_week_command(mock_service_class, mock_update, mock_context):
    """Test /week command shows weekly summary."""
    from handlers.expense_handler import week_command
    
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service
    mock_service.get_week_summary = AsyncMock(
        return_value={"success": True, "summary": "Week total: 2200 IQD"}
    )
    
    await week_command(mock_update, mock_context)
    
    mock_service.get_week_summary.assert_called_once()
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
@patch('handlers.expense_handler.rate_limited', lambda f: f)
@patch('handlers.expense_handler.authorized_only', lambda f: f)
@patch('handlers.expense_handler.ExpenseService')
async def test_delete_command_with_id(mock_service_class, mock_update, mock_context):
    """Test /delete command with expense ID."""
    from handlers.expense_handler import delete_command
    
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service
    mock_service.delete_expense = AsyncMock(
        return_value={"success": True, "message": "✅ تم حذف النفقة"}
    )
    
    # Set command args: /delete 5
    mock_context.args = ['5']
    
    await delete_command(mock_update, mock_context)
    
    mock_service.delete_expense.assert_called_once()
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
@patch('handlers.expense_handler.rate_limited', lambda f: f)
@patch('handlers.expense_handler.authorized_only', lambda f: f)
@patch('handlers.expense_handler.ExpenseService')
async def test_delete_command_no_args(mock_service_class, mock_update, mock_context):
    """Test /delete command without ID asks for clarification."""
    from handlers.expense_handler import delete_command
    
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service
    
    # No args provided
    mock_context.args = []
    
    await delete_command(mock_update, mock_context)
    
    # Should ask for expense ID
    mock_update.message.reply_text.assert_called_once()
    msg = mock_update.message.reply_text.call_args[0][0]
    assert "id" in msg.lower() or "رقم" in msg


@pytest.mark.asyncio
@patch('handlers.expense_handler.rate_limited', lambda f: f)
@patch('handlers.expense_handler.authorized_only', lambda f: f)
@patch('handlers.expense_handler.ExpenseService')
async def test_edit_command(mock_service_class, mock_update, mock_context):
    """Test /edit command updates expense."""
    from handlers.expense_handler import edit_command
    
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service
    mock_service.edit_expense = AsyncMock(
        return_value={"success": True, "message": "✅ تم تحديث النفقة"}
    )
    
    mock_context.args = ['5', '200']
    
    await edit_command(mock_update, mock_context)
    
    mock_service.edit_expense.assert_called_once()
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
@patch('handlers.expense_handler.rate_limited', lambda f: f)
@patch('handlers.expense_handler.authorized_only', lambda f: f)
@patch('handlers.expense_handler.ExpenseService')
async def test_category_command(mock_service_class, mock_update, mock_context):
    """Test /category command filters by category."""
    from handlers.expense_handler import category_command
    
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service
    mock_service.get_category_details = AsyncMock(
        return_value={"success": True, "category": "food", "total": 450}
    )
    
    mock_context.args = ['food']
    
    await category_command(mock_update, mock_context)
    
    mock_service.get_category_details.assert_called_once()
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
@patch('handlers.expense_handler.rate_limited', lambda f: f)
@patch('handlers.expense_handler.authorized_only', lambda f: f)
@patch('handlers.expense_handler.ExpenseService')
async def test_search_command(mock_service_class, mock_update, mock_context):
    """Test /search command finds transactions."""
    from handlers.expense_handler import search_command
    
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service
    mock_service.search_transactions = AsyncMock(
        return_value={"success": True, "results": []}
    )
    
    mock_context.args = ['coffee']
    
    await search_command(mock_update, mock_context)
    
    mock_service.search_transactions.assert_called_once()
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
@patch('handlers.expense_handler.rate_limited', lambda f: f)
@patch('handlers.expense_handler.authorized_only', lambda f: f)
@patch('handlers.expense_handler.ExpenseService')
async def test_report_command(mock_service_class, mock_update, mock_context):
    """Test /report command shows comprehensive stats."""
    from handlers.expense_handler import report_command
    
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service
    mock_service.get_date_range_report = AsyncMock(
        return_value={"success": True, "report": "Monthly stats"}
    )
    
    await report_command(mock_update, mock_context)
    
    mock_service.get_date_range_report.assert_called_once()
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
@patch('handlers.expense_handler.rate_limited', lambda f: f)
@patch('handlers.expense_handler.authorized_only', lambda f: f)
@patch('handlers.expense_handler.ExpenseService')
async def test_handle_text_message_parsing_error(mock_service_class, mock_update, mock_context):
    """Test handling parsing error from AI."""
    from handlers.expense_handler import handle_text_message
    
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service
    mock_service.add_from_text = AsyncMock(
        return_value={"success": False, "question": "Can you clarify the amount?"}
    )
    
    mock_update.message.text = "invalid text"
    
    await handle_text_message(mock_update, mock_context)
    
    # Should ask for clarification
    mock_update.message.reply_text.assert_called_once()
    msg = mock_update.message.reply_text.call_args[0][0]
    assert "clarify" in msg.lower() or "واضح" in msg

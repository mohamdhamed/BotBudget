"""
test_start_handler.py
---------------------
Tests for start and help handler commands.

Tests:
    - test_start_command
    - test_help_command
    - test_myid_command
"""

import pytest
from unittest.mock import AsyncMock, patch
from telegram import Update


@pytest.mark.asyncio
@patch('handlers.start_handler.rate_limited', lambda f: f)
@patch('handlers.start_handler.authorized_only', lambda f: f)
async def test_start_command(mock_update, mock_context):
    """Test /start command shows welcome message."""
    from handlers.start_handler import start_command
    
    await start_command(mock_update, mock_context)
    
    mock_update.message.reply_text.assert_called_once()
    msg = mock_update.message.reply_text.call_args[0][0]
    assert "welcome" in msg.lower() or "أهلا" in msg


@pytest.mark.asyncio
@patch('handlers.start_handler.rate_limited', lambda f: f)
@patch('handlers.start_handler.authorized_only', lambda f: f)
async def test_help_command(mock_update, mock_context):
    """Test /help command shows available commands."""
    from handlers.start_handler import help_command
    
    await help_command(mock_update, mock_context)
    
    mock_update.message.reply_text.assert_called_once()
    msg = mock_update.message.reply_text.call_args[0][0]
    assert "/" in msg  # Should contain command examples


@pytest.mark.asyncio
@patch('handlers.start_handler.rate_limited', lambda f: f)
@patch('handlers.start_handler.authorized_only', lambda f: f)
async def test_myid_command(mock_update, mock_context):
    """Test /myid command shows user ID."""
    from handlers.start_handler import myid_command
    
    mock_update.effective_user.id = 123
    
    await myid_command(mock_update, mock_context)
    
    mock_update.message.reply_text.assert_called_once()
    msg = mock_update.message.reply_text.call_args[0][0]
    assert "123" in msg  # Should contain user ID

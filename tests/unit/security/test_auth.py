"""
test_auth.py
-----------
Security authorization decorator tests.

Tests:
    - test_authorized_user_allowed
    - test_unauthorized_user_blocked
    - test_dev_mode_blocks_all
    - test_decorator_preserves_function_name
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from telegram import Update, User, Message


@pytest.mark.asyncio
async def test_authorized_user_allowed(mock_update, mock_context):
    """Test that authorized user (in whitelist) can call handler."""
    from security.auth import authorized_only
    
    # Create a test handler function
    test_handler_called = False
    
    @authorized_only
    async def test_handler(update: Update, context) -> None:
        nonlocal test_handler_called
        test_handler_called = True
    
    # Patch ALLOWED_USER_IDS with authorized user
    with patch('security.auth.ALLOWED_USER_IDS', [123]):
        mock_update.effective_user.id = 123
        await test_handler(mock_update, mock_context)
    
    assert test_handler_called is True


@pytest.mark.asyncio
async def test_unauthorized_user_blocked(mock_update, mock_context):
    """Test that unauthorized user (not in whitelist) is blocked."""
    from security.auth import authorized_only
    
    test_handler_called = False
    
    @authorized_only
    async def test_handler(update: Update, context) -> None:
        nonlocal test_handler_called
        test_handler_called = True
    
    # Patch ALLOWED_USER_IDS without this user
    with patch('security.auth.ALLOWED_USER_IDS', [999]):
        mock_update.effective_user.id = 123  # Different user
        await test_handler(mock_update, mock_context)
    
    # Handler should not be called
    assert test_handler_called is False
    # User should receive error message
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "خاص" in call_args or "غير مصرح" in call_args or "not authorized" in call_args.lower()


@pytest.mark.asyncio
async def test_dev_mode_blocks_all(mock_update, mock_context):
    """Test that dev mode (empty whitelist) blocks all users."""
    from security.auth import authorized_only
    
    test_handler_called = False
    
    @authorized_only
    async def test_handler(update: Update, context) -> None:
        nonlocal test_handler_called
        test_handler_called = True
    
    # Patch ALLOWED_USER_IDS as empty (dev mode)
    with patch('security.auth.ALLOWED_USER_IDS', []):
        mock_update.effective_user.id = 123
        await test_handler(mock_update, mock_context)
    
    # Handler should not be called
    assert test_handler_called is False
    # Developer should receive warning
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_decorator_preserves_function_name(mock_update, mock_context):
    """Test that @authorized_only decorator preserves function name."""
    from security.auth import authorized_only
    
    @authorized_only
    async def my_special_handler(update: Update, context) -> None:
        pass
    
    # Decorator should preserve function name via functools.wraps
    assert my_special_handler.__name__ == 'my_special_handler'


@pytest.mark.asyncio
async def test_authorized_only_logs_unauthorized_attempt(mock_update, mock_context):
    """Test that unauthorized attempts are logged."""
    from security.auth import authorized_only
    
    @authorized_only
    async def test_handler(update: Update, context) -> None:
        pass
    
    with patch('security.auth.logger') as mock_logger:
        with patch('security.auth.ALLOWED_USER_IDS', [999]):
            mock_update.effective_user.id = 123
            await test_handler(mock_update, mock_context)
        
        # Should log the unauthorized attempt
        assert mock_logger.warning.called or mock_logger.error.called


@pytest.mark.asyncio
async def test_multiple_authorized_users(mock_update, mock_context):
    """Test that multiple users in whitelist are all authorized."""
    from security.auth import authorized_only
    
    test_handler_called = False
    
    @authorized_only
    async def test_handler(update: Update, context) -> None:
        nonlocal test_handler_called
        test_handler_called = True
    
    # Multiple users in whitelist
    whitelist = [123, 456, 789]
    
    for user_id in whitelist:
        test_handler_called = False
        with patch('security.auth.ALLOWED_USER_IDS', whitelist):
            mock_update.effective_user.id = user_id
            await test_handler(mock_update, mock_context)
        
        assert test_handler_called is True

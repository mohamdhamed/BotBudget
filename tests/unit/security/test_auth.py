"""
test_auth.py
-----------
Security authorization decorator tests.
Uses DB-backed allowed_users_repo with mocking.
"""

import pytest
from unittest.mock import patch, AsyncMock
from telegram import Update


def _mock_repo(allowed: bool):
    """Helper: create a mock AllowedUsersRepository."""
    repo = AsyncMock()
    repo.is_allowed = AsyncMock(return_value=allowed)
    return repo


@pytest.mark.asyncio
async def test_authorized_user_allowed(mock_update, mock_context):
    """Test that user in DB whitelist can call handler."""
    from security.auth import authorized_only

    test_handler_called = False

    @authorized_only
    async def test_handler(update: Update, context) -> None:
        nonlocal test_handler_called
        test_handler_called = True

    with patch('security.auth.ADMIN_USER_IDS', []):
        with patch('security.auth._allowed_users_repo', _mock_repo(allowed=True)):
            mock_update.effective_user.id = 123
            await test_handler(mock_update, mock_context)

    assert test_handler_called is True


@pytest.mark.asyncio
async def test_unauthorized_user_blocked(mock_update, mock_context):
    """Test that user NOT in DB whitelist is blocked."""
    from security.auth import authorized_only

    test_handler_called = False

    @authorized_only
    async def test_handler(update: Update, context) -> None:
        nonlocal test_handler_called
        test_handler_called = True

    with patch('security.auth.ADMIN_USER_IDS', []):
        with patch('security.auth._allowed_users_repo', _mock_repo(allowed=False)):
            mock_update.effective_user.id = 123
            await test_handler(mock_update, mock_context)

    assert test_handler_called is False
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "خاص" in call_args or "غير مصرح" in call_args or "not authorized" in call_args.lower()


@pytest.mark.asyncio
async def test_admin_always_allowed(mock_update, mock_context):
    """Test that admin user bypasses DB check and is always allowed."""
    from security.auth import authorized_only

    test_handler_called = False

    @authorized_only
    async def test_handler(update: Update, context) -> None:
        nonlocal test_handler_called
        test_handler_called = True

    # Admin ID in ADMIN_USER_IDS — repo should NOT be called
    mock_repo = _mock_repo(allowed=False)
    with patch('security.auth.ADMIN_USER_IDS', [123]):
        with patch('security.auth._allowed_users_repo', mock_repo):
            mock_update.effective_user.id = 123
            await test_handler(mock_update, mock_context)

    assert test_handler_called is True
    mock_repo.is_allowed.assert_not_called()


@pytest.mark.asyncio
async def test_dev_mode_blocks_all(mock_update, mock_context):
    """Test that user not in DB and not admin is blocked."""
    from security.auth import authorized_only

    test_handler_called = False

    @authorized_only
    async def test_handler(update: Update, context) -> None:
        nonlocal test_handler_called
        test_handler_called = True

    with patch('security.auth.ADMIN_USER_IDS', []):
        with patch('security.auth._allowed_users_repo', _mock_repo(allowed=False)):
            mock_update.effective_user.id = 123
            await test_handler(mock_update, mock_context)

    assert test_handler_called is False
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_decorator_preserves_function_name(mock_update, mock_context):
    """Test that @authorized_only preserves function name."""
    from security.auth import authorized_only

    @authorized_only
    async def my_special_handler(update: Update, context) -> None:
        pass

    assert my_special_handler.__name__ == 'my_special_handler'


@pytest.mark.asyncio
async def test_authorized_only_logs_unauthorized_attempt(mock_update, mock_context):
    """Test that unauthorized attempts are logged."""
    from security.auth import authorized_only

    @authorized_only
    async def test_handler(update: Update, context) -> None:
        pass

    with patch('security.auth.logger') as mock_logger:
        with patch('security.auth.ADMIN_USER_IDS', []):
            with patch('security.auth._allowed_users_repo', _mock_repo(allowed=False)):
                mock_update.effective_user.id = 123
                await test_handler(mock_update, mock_context)

        assert mock_logger.warning.called or mock_logger.error.called


@pytest.mark.asyncio
async def test_multiple_authorized_users(mock_update, mock_context):
    """Test that multiple users in DB whitelist are all authorized."""
    from security.auth import authorized_only

    test_handler_called = False

    @authorized_only
    async def test_handler(update: Update, context) -> None:
        nonlocal test_handler_called
        test_handler_called = True

    for user_id in [123, 456, 789]:
        test_handler_called = False
        with patch('security.auth.ADMIN_USER_IDS', []):
            with patch('security.auth._allowed_users_repo', _mock_repo(allowed=True)):
                mock_update.effective_user.id = user_id
                await test_handler(mock_update, mock_context)

        assert test_handler_called is True

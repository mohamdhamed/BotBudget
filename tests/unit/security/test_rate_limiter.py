"""
test_rate_limiter.py
--------------------
Rate limiting decorator tests — DB-backed implementation.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from telegram import Update


@pytest.mark.asyncio
@patch('security.rate_limiter._cleanup', new_callable=AsyncMock)
@patch('security.rate_limiter._count', new_callable=AsyncMock, return_value=0)
@patch('security.rate_limiter._record', new_callable=AsyncMock)
async def test_first_message_allowed(mock_record, mock_count, mock_cleanup, mock_update, mock_context):
    """Test that first message from user is always allowed."""
    from security.rate_limiter import rate_limited

    test_handler_called = False

    @rate_limited
    async def test_handler(update: Update, context) -> None:
        nonlocal test_handler_called
        test_handler_called = True

    mock_update.effective_user.id = 123
    await test_handler(mock_update, mock_context)

    assert test_handler_called is True
    mock_record.assert_called_once()


@pytest.mark.asyncio
@patch('security.rate_limiter._cleanup', new_callable=AsyncMock)
@patch('security.rate_limiter._record', new_callable=AsyncMock)
async def test_messages_within_limit(mock_record, mock_cleanup, mock_update, mock_context):
    """Test that messages within rate limit are allowed."""
    from security.rate_limiter import rate_limited

    handler_calls = 0

    @rate_limited
    async def test_handler(update: Update, context) -> None:
        nonlocal handler_calls
        handler_calls += 1

    with patch('security.rate_limiter.RATE_LIMIT_MESSAGES', 30):
        with patch('security.rate_limiter._count', new_callable=AsyncMock, return_value=5):
            mock_update.effective_user.id = 123
            handler_calls = 0
            await test_handler(mock_update, mock_context)
            assert handler_calls == 1


@pytest.mark.asyncio
@patch('security.rate_limiter._cleanup', new_callable=AsyncMock)
@patch('security.rate_limiter._record', new_callable=AsyncMock)
async def test_exceeds_rate_limit(mock_record, mock_cleanup, mock_update, mock_context):
    """Test that exceeding rate limit blocks the handler."""
    from security.rate_limiter import rate_limited

    handler_calls = 0

    @rate_limited
    async def test_handler(update: Update, context) -> None:
        nonlocal handler_calls
        handler_calls += 1

    # _count returns 3 = at the limit
    with patch('security.rate_limiter.RATE_LIMIT_MESSAGES', 3):
        with patch('security.rate_limiter._count', new_callable=AsyncMock, return_value=3):
            mock_update.effective_user.id = 123
            mock_update.message.reply_text.reset_mock()
            await test_handler(mock_update, mock_context)

            # Handler should NOT have been called
            assert handler_calls == 0
            # Rate limit message should have been sent
            mock_update.message.reply_text.assert_called_once()
            msg = mock_update.message.reply_text.call_args[0][0]
            assert "كتير" in msg or "حد" in msg or "دقيقة" in msg


@pytest.mark.asyncio
@patch('security.rate_limiter._cleanup', new_callable=AsyncMock)
@patch('security.rate_limiter._record', new_callable=AsyncMock)
async def test_80_percent_threshold_warning(mock_record, mock_cleanup, mock_update, mock_context):
    """Test that user gets warning at 80% of rate limit."""
    from security.rate_limiter import rate_limited

    handler_calls = 0

    @rate_limited
    async def test_handler(update: Update, context) -> None:
        nonlocal handler_calls
        handler_calls += 1

    # count = 8 = 80% of limit 10
    with patch('security.rate_limiter.RATE_LIMIT_MESSAGES', 10):
        with patch('security.rate_limiter._count', new_callable=AsyncMock, return_value=8):
            mock_update.effective_user.id = 123
            mock_update.message.reply_text.reset_mock()
            await test_handler(mock_update, mock_context)

            # Handler should have been called (not blocked)
            assert handler_calls == 1
            # Warning should have been sent
            mock_update.message.reply_text.assert_called_once()
            msg = mock_update.message.reply_text.call_args[0][0]
            assert "تحذير" in msg or "اقتربت" in msg


@pytest.mark.asyncio
@patch('security.rate_limiter._cleanup', new_callable=AsyncMock)
@patch('security.rate_limiter._record', new_callable=AsyncMock)
async def test_window_resets(mock_record, mock_cleanup, mock_update, mock_context):
    """Test that cleanup is called on every message (DB handles window expiry)."""
    from security.rate_limiter import rate_limited

    @rate_limited
    async def test_handler(update: Update, context) -> None:
        pass

    with patch('security.rate_limiter._count', new_callable=AsyncMock, return_value=0):
        mock_update.effective_user.id = 123
        await test_handler(mock_update, mock_context)
        await test_handler(mock_update, mock_context)

    # Cleanup must be called for each message
    assert mock_cleanup.call_count == 2


@pytest.mark.asyncio
@patch('security.rate_limiter._cleanup', new_callable=AsyncMock)
@patch('security.rate_limiter._count', new_callable=AsyncMock, return_value=0)
@patch('security.rate_limiter._record', new_callable=AsyncMock)
async def test_cleanup_old_timestamps(mock_record, mock_count, mock_cleanup, mock_update, mock_context):
    """Test that _cleanup is called with the correct user_id."""
    from security.rate_limiter import rate_limited

    @rate_limited
    async def test_handler(update: Update, context) -> None:
        pass

    mock_update.effective_user.id = 42
    await test_handler(mock_update, mock_context)

    mock_cleanup.assert_called_once_with(42)


@pytest.mark.asyncio
@patch('security.rate_limiter._cleanup', new_callable=AsyncMock)
@patch('security.rate_limiter._record', new_callable=AsyncMock)
async def test_rate_limiter_per_user_isolation(mock_record, mock_cleanup, mock_update, mock_context):
    """Test that rate limits are per-user, not global."""
    from security.rate_limiter import rate_limited

    call_counts: dict[int, int] = {123: 0, 456: 0}

    @rate_limited
    async def test_handler(update: Update, context) -> None:
        call_counts[update.effective_user.id] += 1

    with patch('security.rate_limiter.RATE_LIMIT_MESSAGES', 3):
        with patch('security.rate_limiter._count', new_callable=AsyncMock, return_value=1):
            mock_update.effective_user.id = 123
            await test_handler(mock_update, mock_context)
            assert call_counts[123] == 1

            mock_update.effective_user.id = 456
            await test_handler(mock_update, mock_context)
            assert call_counts[456] == 1

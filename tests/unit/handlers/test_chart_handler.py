"""
test_chart_handler.py
---------------------
Tests for chart generation handler commands.

Tests:
    - test_chart_command
    - test_chart_week_command
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from io import BytesIO


@pytest.mark.asyncio
@patch('handlers.chart_handler.rate_limited', lambda f: f)
@patch('handlers.chart_handler.authorized_only', lambda f: f)
@patch('handlers.chart_handler.ChartService')
async def test_chart_command(mock_service_class, mock_update, mock_context):
    """Test /chart command generates and sends pie chart."""
    from handlers.chart_handler import chart_command
    
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service
    
    # Mock chart generation returning BytesIO
    mock_image = BytesIO(b'fake image data')
    mock_service.generate_pie_chart = AsyncMock(return_value=mock_image)
    
    await chart_command(mock_update, mock_context)
    
    mock_service.generate_pie_chart.assert_called_once()
    mock_update.message.reply_document.assert_called_once()


@pytest.mark.asyncio
@patch('handlers.chart_handler.rate_limited', lambda f: f)
@patch('handlers.chart_handler.authorized_only', lambda f: f)
@patch('handlers.chart_handler.ChartService')
async def test_chart_week_command(mock_service_class, mock_update, mock_context):
    """Test /chart_week command generates weekly chart."""
    from handlers.chart_handler import chart_week_command
    
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service
    
    mock_image = BytesIO(b'fake image data')
    mock_service.generate_bar_chart = AsyncMock(return_value=mock_image)
    
    await chart_week_command(mock_update, mock_context)
    
    mock_service.generate_bar_chart.assert_called_once()
    mock_update.message.reply_document.assert_called_once()

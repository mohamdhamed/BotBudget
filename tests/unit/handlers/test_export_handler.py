"""
test_export_handler.py
----------------------
Tests for export handler commands.

Tests:
    - test_export_csv_command
    - test_export_excel_command
"""

import pytest
from unittest.mock import patch, AsyncMock
from io import BytesIO


@pytest.mark.asyncio
@patch('handlers.export_handler.rate_limited', lambda f: f)
@patch('handlers.export_handler.authorized_only', lambda f: f)
@patch('handlers.export_handler.ExportService')
async def test_export_csv_command(mock_service_class, mock_update, mock_context):
    """Test /export_csv command generates and sends CSV file."""
    from handlers.export_handler import export_csv_command
    
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service
    
    mock_csv = BytesIO(b'id,amount,category\n1,100,food\n')
    mock_service.export_month_csv = AsyncMock(return_value=mock_csv)
    
    await export_csv_command(mock_update, mock_context)
    
    mock_service.export_month_csv.assert_called_once()
    mock_update.message.reply_document.assert_called_once()


@pytest.mark.asyncio
@patch('handlers.export_handler.rate_limited', lambda f: f)
@patch('handlers.export_handler.authorized_only', lambda f: f)
@patch('handlers.export_handler.ExportService')
async def test_export_excel_command(mock_service_class, mock_update, mock_context):
    """Test /export_excel command generates and sends Excel file."""
    from handlers.export_handler import export_excel_command
    
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service
    
    mock_excel = BytesIO(b'PK\x03\x04fake excel')
    mock_service.export_month_excel = AsyncMock(return_value=mock_excel)
    
    await export_excel_command(mock_update, mock_context)
    
    mock_service.export_month_excel.assert_called_once()
    mock_update.message.reply_document.assert_called_once()

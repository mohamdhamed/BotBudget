"""
test_export_service.py
-----------------------
Tests for export service (CSV/Excel generation).

Tests:
    - test_export_month_csv
    - test_export_month_excel
"""

import pytest
from io import BytesIO
from unittest.mock import AsyncMock, patch, MagicMock
from services.export_service import ExportService


@pytest.fixture
def export_service(mock_expense_repo):
    """ExportService with mocked repository."""
    service = ExportService()
    service.repo = mock_expense_repo
    return service


@pytest.mark.asyncio
@patch('services.export_service.pd')
async def test_export_month_csv(mock_pd, export_service, mock_expense_repo):
    """Test exporting month expenses to CSV."""
    mock_expense_repo.get_by_date_range.return_value = []
    
    # Mock pandas DataFrame
    mock_df = MagicMock()
    mock_df.to_csv = MagicMock(return_value=None)
    mock_pd.DataFrame.return_value = mock_df
    
    result = await export_service.export_month_csv(user_id=1)
    
    assert isinstance(result, BytesIO) or result is not None
    mock_expense_repo.get_by_date_range.assert_called_once()


@pytest.mark.asyncio
@patch('services.export_service.pd')
async def test_export_month_excel(mock_pd, export_service, mock_expense_repo):
    """Test exporting month expenses to Excel."""
    mock_expense_repo.get_by_date_range.return_value = []
    
    # Mock pandas DataFrame and ExcelWriter
    mock_df = MagicMock()
    mock_pd.DataFrame.return_value = mock_df
    
    result = await export_service.export_month_excel(user_id=1)
    
    assert isinstance(result, BytesIO) or result is not None

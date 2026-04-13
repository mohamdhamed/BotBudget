"""
test_chart_service.py
----------------------
Tests for chart generation service.

Tests:
    - test_generate_pie_chart
    - test_generate_bar_chart
"""

import pytest
from io import BytesIO
from unittest.mock import AsyncMock, patch, MagicMock
from services.chart_service import ChartService


@pytest.fixture
def chart_service(mock_expense_repo):
    """ChartService with mocked repository."""
    service = ChartService()
    service.repo = mock_expense_repo
    return service


@pytest.mark.asyncio
@patch('services.chart_service.plt')
async def test_generate_pie_chart(mock_plt, chart_service, mock_expense_repo):
    """Test generating pie chart from expenses."""
    mock_expense_repo.get_category_summary.return_value = [
        {"category": "Food", "total": 450.0},
        {"category": "Transport", "total": 150.0}
    ]
    
    # Mock matplotlib save to BytesIO
    mock_plt.savefig = MagicMock()
    
    result = await chart_service.generate_pie_chart(user_id=1)
    
    assert isinstance(result, BytesIO) or result is not None
    mock_expense_repo.get_category_summary.assert_called_once()


@pytest.mark.asyncio
@patch('services.chart_service.plt')
async def test_generate_bar_chart(mock_plt, chart_service, mock_expense_repo):
    """Test generating bar chart for weekly expenses."""
    mock_expense_repo.get_by_date_range.return_value = []
    
    mock_plt.savefig = MagicMock()
    
    result = await chart_service.generate_bar_chart(user_id=1)
    
    assert isinstance(result, BytesIO) or result is not None

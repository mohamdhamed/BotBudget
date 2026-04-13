import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from services.expense_service import ExpenseService
from models.expense import Expense


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    return repo


@pytest.fixture
def expense_service(mock_repo):
    service = ExpenseService()
    service.repo = mock_repo
    return service


@pytest.mark.asyncio
@patch('services.expense_service.parse_transaction')
async def test_add_from_text_success(mock_parse, expense_service, mock_repo):
    # Mock the AI parser output
    mock_parse.return_value = {
        "type": "expense",
        "amount": 100.0,
        "category": "Food",
        "description": "Lunch",
        "date": "2026-04-12"
    }

    # Mock the repo returning the saved expense
    saved_mock = Expense(user_id=1, type="expense", amount=100.0, category="Food")
    mock_repo.add.return_value = saved_mock

    # Execute service method
    result = await expense_service.add_from_text(user_id=1, text="دفعنا 100 غداء")

    # Assert correct response
    assert result["success"] is True
    assert "Food" in result["message"]
    assert "100.00" in result["message"]

    # Assert repo was called correctly
    mock_repo.add.assert_called_once()
    saved_param = mock_repo.add.call_args[0][0]
    assert isinstance(saved_param, Expense)
    assert saved_param.user_id == 1
    assert saved_param.amount == 100.0
    assert saved_param.category == "Food"


@pytest.mark.asyncio
@patch('services.expense_service.parse_transaction')
async def test_add_from_text_parse_error(mock_parse, expense_service, mock_repo):
    # Mock AI returning an error (e.g. unclear message)
    mock_parse.return_value = {
        "error": "parse_failed",
        "question": "لم أفهم الرسالة"
    }

    result = await expense_service.add_from_text(user_id=1, text="مش مفهوم")

    assert result["success"] is False
    assert "لم أفهم الرسالة" in result["question"]
    mock_repo.add.assert_not_called()


@pytest.mark.asyncio
async def test_get_week_summary(expense_service, mock_repo):
    # Setup mock data return
    mock_repo.get_by_date_range.return_value = [
        Expense(user_id=1, type="expense", amount=50.0, category="Food"),
        Expense(user_id=1, type="expense", amount=20.0, category="Transport"),
        Expense(user_id=1, type="income", amount=500.0, category="Salary")
    ]

    result = await expense_service.get_week_summary(user_id=1)

    assert "إجمالي المصاريف: 70.00€" in result
    assert "إجمالي الدخل: 500.00€" in result
    assert "الصنافي" not in result # check random word not there
    assert "Food: 50.00€" in result
    assert "Transport: 20.00€" in result

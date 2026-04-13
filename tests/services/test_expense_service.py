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


@pytest.mark.asyncio
async def test_delete_expense(expense_service, mock_repo):
    """Test deleting an expense."""
    mock_repo.delete.return_value = True
    
    result = await expense_service.delete_expense(user_id=1, expense_id=5)
    
    assert result["success"] is True
    mock_repo.delete.assert_called_once()


@pytest.mark.asyncio
async def test_delete_nonexistent_expense(expense_service, mock_repo):
    """Test deleting a non-existent expense."""
    mock_repo.delete.return_value = False
    
    result = await expense_service.delete_expense(user_id=1, expense_id=999)
    
    assert result["success"] is False


@pytest.mark.asyncio
async def test_get_today_summary(expense_service, mock_repo):
    """Test getting today's expense summary."""
    mock_repo.get_by_date_range.return_value = [
        Expense(user_id=1, type="expense", amount=100.0, category="Food", date=date.today()),
        Expense(user_id=1, type="expense", amount=50.0, category="Coffee", date=date.today())
    ]
    
    result = await expense_service.get_today_summary(user_id=1)
    
    assert result["success"] is True
    assert "150" in result["message"]  # Total should be 150


@pytest.mark.asyncio
async def test_get_month_summary(expense_service, mock_repo):
    """Test getting month summary by category."""
    mock_repo.get_category_summary.return_value = [
        {"category": "Food", "total": 450.0},
        {"category": "Transport", "total": 150.0}
    ]
    
    result = await expense_service.get_month_summary(user_id=1)
    
    assert result["success"] is True
    assert "Food" in result["message"]
    assert "450" in result["message"]


@pytest.mark.asyncio
async def test_edit_expense(expense_service, mock_repo):
    """Test editing an expense."""
    mock_repo.update.return_value = Expense(
        user_id=1, type="expense", amount=200.0, category="Food", date=date.today()
    )
    
    result = await expense_service.edit_expense(
        user_id=1, expense_id=5, amount=200.0
    )
    
    assert result["success"] is True
    mock_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_get_category_details(expense_service, mock_repo):
    """Test getting detailed category breakdown."""
    mock_repo.get_by_category.return_value = [
        Expense(user_id=1, type="expense", amount=100.0, category="Food"),
        Expense(user_id=1, type="expense", amount=50.0, category="Food")
    ]
    
    result = await expense_service.get_category_details(
        user_id=1, category="Food"
    )
    
    assert result["success"] is True
    assert "150" in result["message"]


@pytest.mark.asyncio
async def test_search_transactions(expense_service, mock_repo):
    """Test searching transactions by text."""
    mock_repo.search_by_text.return_value = [
        Expense(user_id=1, amount=50.0, description="Coffee")
    ]
    
    result = await expense_service.search_transactions(
        user_id=1, query="coffee"
    )
    
    assert result["success"] is True
    mock_repo.search_by_text.assert_called_once()


@pytest.mark.asyncio
async def test_compare_months(expense_service, mock_repo):
    """Test comparing expenses between two months."""
    mock_repo.get_by_date_range.side_effect = [
        # March expenses
        [Expense(user_id=1, type="expense", amount=500.0, category="Food")],
        # April expenses
        [Expense(user_id=1, type="expense", amount=600.0, category="Food")]
    ]
    
    result = await expense_service.compare_months(user_id=1)
    
    assert result["success"] is True


@pytest.mark.asyncio  
async def test_get_balance(expense_service, mock_repo):
    """Test getting overall balance (income - expenses)."""
    mock_repo.get_overall_balance.return_value = {
        "income": 1000.0,
        "expense": 400.0
    }
    
    result = await expense_service.get_balance(user_id=1)
    
    assert result["success"] is True
    assert "600" in result["message"]  # 1000 - 400 = 600

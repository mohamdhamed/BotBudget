"""
conftest.py
-----------
Shared pytest fixtures for all tests.

Provides:
    - Mock Telegram objects (Update, User, Message, Context)
    - Mock repository fixtures (AsyncMock)
    - Mock database pool fixtures
    - Config/environment patches
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram import Update, User, Message, Chat
from telegram.ext import ContextTypes


# ===== TELEGRAM MOCKS =====

@pytest.fixture
def mock_user():
    """Mock Telegram User object."""
    user = MagicMock(spec=User)
    user.id = 123
    user.first_name = "Test"
    user.username = "testuser"
    return user


@pytest.fixture
def mock_chat():
    """Mock Telegram Chat object."""
    chat = MagicMock(spec=Chat)
    chat.id = 123
    chat.type = "private"
    return chat


@pytest.fixture
def mock_message():
    """Mock Telegram Message object."""
    message = MagicMock(spec=Message)
    message.text = "صرفت 100 طعام"
    message.message_id = 1
    message.reply_text = AsyncMock()
    message.reply_document = AsyncMock()
    message.edit_text = AsyncMock()
    message.delete = AsyncMock()
    return message


@pytest.fixture
def mock_update(mock_user, mock_chat, mock_message):
    """Mock Telegram Update object with all required fields."""
    update = MagicMock(spec=Update)
    update.effective_user = mock_user
    update.effective_chat = mock_chat
    update.message = mock_message
    update.callback_query = None
    update.update_id = 1
    return update


@pytest.fixture
def mock_context():
    """Mock telegram.ext.ContextTypes.DEFAULT_TYPE context."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []  # Default empty args for commands
    context.user_data = {}
    context.chat_data = {}
    context.bot_data = {}
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()
    return context


# ===== REPOSITORY MOCKS =====

@pytest.fixture
def mock_expense_repo():
    """Mock ExpenseRepository with all async methods."""
    repo = MagicMock()
    repo.add = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_by_date_range = AsyncMock()
    repo.get_category_summary = AsyncMock()
    repo.get_monthly_total = AsyncMock()
    repo.get_by_category = AsyncMock()
    repo.search_by_text = AsyncMock()
    repo.get_overall_balance = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    return repo


@pytest.fixture
def mock_budget_repo():
    """Mock BudgetRepository with all async methods."""
    repo = MagicMock()
    repo.set_budget = AsyncMock()
    repo.get_budget = AsyncMock()
    repo.check_alert = AsyncMock()
    repo.delete_budget = AsyncMock()
    repo.get_all = AsyncMock()
    return repo


@pytest.fixture
def mock_recurring_repo():
    """Mock RecurringRepository with all async methods."""
    repo = MagicMock()
    repo.add = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_upcoming_due = AsyncMock()
    repo.mark_reminded = AsyncMock()
    repo.delete = AsyncMock()
    repo.get_all = AsyncMock()
    return repo


@pytest.fixture
def mock_user_repo():
    """Mock UserRepository with all async methods."""
    repo = MagicMock()
    repo.ensure_user = AsyncMock()
    repo.get_user = AsyncMock()
    return repo


# ===== DATABASE MOCKS =====

@pytest.fixture
def mock_db_pool():
    """Mock psycopg AsyncConnectionPool."""
    pool = AsyncMock()
    connection = AsyncMock()
    cursor = AsyncMock()
    
    # Setup context managers
    pool.__aenter__ = AsyncMock(return_value=connection)
    pool.__aexit__ = AsyncMock(return_value=None)
    
    connection.cursor = MagicMock()
    connection.cursor.return_value.__aenter__ = AsyncMock(return_value=cursor)
    connection.cursor.return_value.__aexit__ = AsyncMock(return_value=None)
    
    # Setup common cursor methods
    cursor.execute = AsyncMock()
    cursor.fetchone = AsyncMock(return_value=None)
    cursor.fetchall = AsyncMock(return_value=[])
    cursor.fetchval = AsyncMock(return_value=None)
    
    return pool


# ===== SERVICE FIXTURES =====

@pytest.fixture
def expense_service(mock_expense_repo):
    """ExpenseService with mocked repository."""
    from services.expense_service import ExpenseService
    service = ExpenseService()
    service.repo = mock_expense_repo
    return service


@pytest.fixture
def budget_service(mock_budget_repo):
    """BudgetService with mocked repository."""
    from services.budget_service import BudgetService
    service = BudgetService()
    service.repo = mock_budget_repo
    return service


@pytest.fixture
def recurring_service(mock_recurring_repo):
    """RecurringService with mocked repository."""
    from services.recurring_service import RecurringService
    service = RecurringService()
    service.repo = mock_recurring_repo
    return service


@pytest.fixture
def user_repo_service(mock_user_repo):
    """Service with mocked user repository."""
    from services.expense_service import ExpenseService
    service = ExpenseService()
    return service


# ===== REPOSITORY FIXTURES =====

@pytest.fixture
def expense_repo(mock_db_pool):
    """ExpenseRepository with mocked database pool."""
    from repositories.expense_repo import ExpenseRepository
    from unittest.mock import patch
    
    with patch('repositories.expense_repo.get_pool', return_value=mock_db_pool):
        repo = ExpenseRepository()
    return repo


@pytest.fixture
def budget_repo(mock_db_pool):
    """BudgetRepository with mocked database pool."""
    from repositories.budget_repo import BudgetRepository
    from unittest.mock import patch
    
    with patch('repositories.budget_repo.get_pool', return_value=mock_db_pool):
        repo = BudgetRepository()
    return repo


@pytest.fixture
def recurring_repo(mock_db_pool):
    """RecurringRepository with mocked database pool."""
    from repositories.recurring_repo import RecurringRepository
    from unittest.mock import patch
    
    with patch('repositories.recurring_repo.get_pool', return_value=mock_db_pool):
        repo = RecurringRepository()
    return repo


@pytest.fixture
def user_repo(mock_db_pool):
    """UserRepository with mocked database pool."""
    from repositories.user_repo import UserRepository
    from unittest.mock import patch
    
    with patch('repositories.user_repo.get_pool', return_value=mock_db_pool):
        repo = UserRepository()
    return repo


# ===== MODEL FIXTURES =====

@pytest.fixture
def sample_expense():
    """Sample Expense object for tests."""
    from models.expense import Expense
    from datetime import date
    
    return Expense(
        id=1,
        user_id=123,
        type="expense",
        amount=100.0,
        category="food",
        date=date.today(),
        description="Lunch"
    )


@pytest.fixture
def sample_recurring():
    """Sample RecurringPayment object for tests."""
    from models.recurring import RecurringPayment
    from datetime import date, timedelta
    
    return RecurringPayment(
        id=1,
        user_id=123,
        name="Apartment rent",
        amount=500.0,
        currency="EUR",
        frequency="monthly",
        next_due_date=date.today() + timedelta(days=10),
        remind_days_before=3,
        active=True
    )

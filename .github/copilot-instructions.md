# BotBudget Project Guidelines

## Code Style

### Module Documentation
Every module opens with a docstring that clearly states its purpose and responsibilities:
```python
"""
module_name.py
--------------
One-line purpose.

Responsibilities:
    - Responsibility 1
    - Responsibility 2
"""
```
See [handlers/start_handler.py](../../handlers/start_handler.py) and [services/expense_service.py](../../services/expense_service.py) for examples.

### Naming Conventions
- **Classes**: PascalCase (e.g., `ExpenseRepository`, `ExpenseService`)
- **Functions/Methods**: snake_case async-first (e.g., `async def parse_transaction()`)
- **Constants**: UPPER_SNAKE_CASE (defined in [config.py](../../config.py))
- **Private methods**: prefix with `_` (internal implementation details)

### Type Hints
Use Python 3.12+ type hints throughout:
```python
async def add_from_text(self, user_id: int, text: str) -> dict:
    """Docstring with Args and Returns."""
```

## Architecture

### Layered Structure
The codebase follows a clean, layered design:

1. **handlers/** — Telegram message/command entry points  
   - Parse user input, apply decorators (@authorized_only, @rate_limited)
   - Delegate to services—never access repositories directly

2. **services/** — Business logic and orchestration  
   - Contain core workflows (e.g., expense parsing via Gemini, data validation)
   - Use repositories for data persistence
   - Return structured responses (dict with 'success'/'error' keys)

3. **repositories/** — Async data access (PostgreSQL)  
   - All CRUD operations via psycopg3 async pool
   - Connection from [db/connection.py](../../db/connection.py)
   - Alembic migrations in [alembic/versions/](../../alembic/versions/)

4. **models/** — Domain models (dataclasses for type safety)  
   - [Expense](../../models/expense.py) and [Recurring](../../models/recurring.py)
   - No business logic—pure data structures

5. **ai/** — External AI integrations  
   - Google Gemini API for NLP transaction parsing ([ai/gemini_parser.py](../../ai/gemini_parser.py))
   - Isolated to prevent handler/service coupling to AI provider

6. **security/** — Cross-cutting concerns  
   - [@authorized_only](../../security/auth.py) — Whitelist user ID check
   - [@rate_limited](../../security/rate_limiter.py) — Per-user message throttling
   - Always stack decorators on handler functions

### Async/Await First
The entire codebase is async:
- Handlers inherit `async def` from python-telegram-bot
- All repo methods are `async def` (psycopg3 async pool)
- Services await repositories: `await self.repo.add_expense(user_id, data)`
- Never mix sync/async—use `asyncio` for multi-step concurrent operations

### Error Handling Pattern
Services return structured dicts for graceful error messaging:
```python
# Success case
return {"success": True, "message": "✅ Added expense"}

# User-input errors (validation)
return {"success": False, "question": "Can you clarify the amount?"}

# System errors (log and notify)
logger.error(f"DB error: {e}")
return {"success": False, "message": "⚠️ Something went wrong"}
```

## Build and Test

### Install & Run
```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Set .env file with: TELEGRAM_BOT_TOKEN, GEMINI_API_KEY, DB_* credentials

# Run bot (requires PostgreSQL running)
python main.py

# Run with Docker Compose
docker-compose up
```

### Testing
```bash
# Run all tests with asyncio support
pytest

# Run specific test file
pytest tests/services/test_expense_service.py -v

# Run with coverage
pytest --cov=. --cov-report=html
```
See [pytest.ini](../../pytest.ini) for config (asyncio_mode, testpaths).

### Database
- Managed via Alembic: `alembic revision --autogenerate -m "description"`
- Schema created at startup via [db/init_db.py](../../db/init_db.py)
- Async connection pool configured in [db/connection.py](../../db/connection.py)

## Conventions

### Decorator Stacking (Handlers Only)
Always apply security and rate-limiting decorators in this order:
```python
@authorized_only   # First: check whitelist
@rate_limited      # Second: throttle per-user
async def my_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ...
```

### Logging
Use the module-level logger from [utils/logger.py](../../utils/logger.py):
```python
from utils.logger import get_logger
logger = get_logger(__name__)

logger.info(f"User {user_id} action: {description}")
logger.error(f"Error context: {e}")
```

### Async Repository Access
All repositories are singleton instances initialized at module level:
```python
from repositories.expense_repo import ExpenseRepository
repo = ExpenseRepository()

# In service methods:
expense = await repo.get_expense(user_id, expense_id)
```

### Telegram Message Formatting
Use Markdown formatting (supported by python-telegram-bot):
```python
await update.message.reply_text(
    "✅ *Success!*\n_Details here_",
    parse_mode="Markdown"
)
```

## Key Files

- **[main.py](../../main.py)** — Bot initialization, handler registration, scheduler setup
- **[config.py](../../config.py)** — All environment variables and typed constants
- **[ai/README.md](../../ai/README.md)** — AI parsing workflow and Gemini integration details
- **[db/README.md](../../db/README.md)** — Database schema and async pool architecture
- **[services/README.md](../../services/README.md)** — Service layer workflows
- **[repositories/README.md](../../repositories/README.md)** — Data access patterns and queries
- **[handlers/README.md](../../handlers/README.md)** — Handler organization and Telegram bot patterns
- **[security/README.md](../../security/README.md)** — Auth, rate limiting, and input validation

## Common Gotchas

1. **Forget `await` on repository calls?** TypeErrors will occur—all repo methods are async
2. **Mixing sync/async in handlers?** Handlers must be fully async; use `asyncio` for concurrency
3. **Database connection not pooled?** Ensure [db/connection.py](../../db/connection.py) is initialized at startup in main.py
4. **AI parser returns unexpected structure?** Check [ai/gemini_parser.py](../../ai/gemini_parser.py) for the contract (success key, error key, or exception)
5. **Rate limiter not honored?** Must apply `@rate_limited` decorator *after* `@authorized_only` on handler

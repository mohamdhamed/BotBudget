"""
db/init_db.py
-------------
Creates the database schema (tables) if they do not already exist.
Run this module directly to initialize a fresh database:
    python -m db.init_db
"""

from db.connection import get_connection, release_connection
from utils.logger import get_logger

logger = get_logger(__name__)

SCHEMA_SQL = """
-- Users table: stores allowed Telegram users and their preferences
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    telegram_id     BIGINT UNIQUE NOT NULL,
    first_name      VARCHAR(100),
    language        VARCHAR(10) DEFAULT 'ar',
    currency        VARCHAR(5) DEFAULT 'EUR',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Expenses table: stores every financial transaction (expense or income)
CREATE TABLE IF NOT EXISTS expenses (
    id              SERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    type            VARCHAR(10) NOT NULL CHECK (type IN ('expense', 'income')),
    amount          NUMERIC(12,2) NOT NULL,
    currency        VARCHAR(5) DEFAULT 'EUR',
    category        VARCHAR(50),
    description     TEXT,
    date            DATE NOT NULL DEFAULT CURRENT_DATE,
    raw_text        TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Recurring payments table: stores automatic payment reminders
CREATE TABLE IF NOT EXISTS recurring_payments (
    id              SERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL,
    amount          NUMERIC(12,2) NOT NULL,
    currency        VARCHAR(5) DEFAULT 'EUR',
    frequency       VARCHAR(20) NOT NULL CHECK (frequency IN ('daily', 'weekly', 'monthly', 'yearly')),
    next_due_date   DATE NOT NULL,
    remind_days_before INT DEFAULT 1,
    active          BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Budgets table: monthly spending limits per category
CREATE TABLE IF NOT EXISTS budgets (
    id              SERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    category        VARCHAR(50) NOT NULL,
    limit_amount    NUMERIC(12,2) NOT NULL,
    UNIQUE(user_id, category)
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, date);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(user_id, category);
CREATE INDEX IF NOT EXISTS idx_recurring_due ON recurring_payments(next_due_date) WHERE active = TRUE;
"""


def create_tables() -> None:
    """
    Execute the schema SQL to create all tables.
    Safe to call multiple times (uses IF NOT EXISTS).
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
        conn.commit()
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to initialize schema: {e}")
        raise
    finally:
        release_connection(conn)


if __name__ == "__main__":
    from db.connection import init_pool
    init_pool()
    create_tables()
    print("✅ Database schema created successfully.")

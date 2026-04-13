"""Initial schema

Revision ID: ac1d4ded0b09
Revises: 
Create Date: 2026-04-12 13:28:40.534525

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ac1d4ded0b09'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id              SERIAL PRIMARY KEY,
            telegram_id     BIGINT UNIQUE NOT NULL,
            first_name      VARCHAR(100),
            language        VARCHAR(10) DEFAULT 'ar',
            currency        VARCHAR(5) DEFAULT 'EUR',
            created_at      TIMESTAMPTZ DEFAULT NOW()
        );

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

        CREATE TABLE IF NOT EXISTS budgets (
            id              SERIAL PRIMARY KEY,
            user_id         BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
            category        VARCHAR(50) NOT NULL,
            limit_amount    NUMERIC(12,2) NOT NULL,
            UNIQUE(user_id, category)
        );

        CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, date);
        CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(user_id, category);
        CREATE INDEX IF NOT EXISTS idx_recurring_due ON recurring_payments(next_due_date) WHERE active = TRUE;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS budgets CASCADE;")
    op.execute("DROP TABLE IF EXISTS recurring_payments CASCADE;")
    op.execute("DROP TABLE IF EXISTS expenses CASCADE;")
    op.execute("DROP TABLE IF EXISTS users CASCADE;")

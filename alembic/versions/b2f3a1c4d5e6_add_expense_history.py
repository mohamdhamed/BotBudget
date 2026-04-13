"""Add expense_history audit table

Revision ID: b2f3a1c4d5e6
Revises: ac1d4ded0b09
Create Date: 2026-04-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'b2f3a1c4d5e6'
down_revision: Union[str, None] = 'ac1d4ded0b09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS expense_history (
            id          SERIAL PRIMARY KEY,
            expense_id  INT NOT NULL,
            user_id     BIGINT NOT NULL,
            action      VARCHAR(10) NOT NULL CHECK (action IN ('create', 'update', 'delete')),
            old_data    JSONB,
            new_data    JSONB,
            changed_at  TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_expense_history_user
            ON expense_history(user_id, changed_at DESC);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS expense_history CASCADE;")

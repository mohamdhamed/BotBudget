"""Add rate_limit_log table for persistent rate limiting

Revision ID: c3d4e5f6a7b8
Revises: b2f3a1c4d5e6
Create Date: 2026-04-13 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2f3a1c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS rate_limit_log (
            user_id     BIGINT NOT NULL,
            timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_rate_limit_user_time
            ON rate_limit_log(user_id, timestamp DESC);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS rate_limit_log CASCADE;")

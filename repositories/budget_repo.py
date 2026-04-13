"""
repositories/budget_repo.py
-----------------------------
Data access layer for monthly budgets.
"""

from typing import Optional

from db.connection import get_pool
from utils.logger import get_logger

logger = get_logger(__name__)


class BudgetRepository:
    """Repository for CRUD operations on the budgets table."""

    async def set_budget(self, user_id: int, category: str, limit_amount: float) -> dict:
        """Set or update a budget limit for a category."""
        sql = """
            INSERT INTO budgets (user_id, category, limit_amount)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, category)
            DO UPDATE SET limit_amount = EXCLUDED.limit_amount
            RETURNING id;
        """
        pool = get_pool()
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(sql, (user_id, category, limit_amount))
                    row = await cur.fetchone()
                await conn.commit()
                return {"id": row[0], "category": category, "limit_amount": limit_amount}
        except Exception as e:
            logger.error(f"Failed to set budget: {e}")
            raise

    async def get_budget(self, user_id: int, category: str) -> Optional[dict]:
        """Get the budget for a specific category."""
        sql = "SELECT id, category, limit_amount FROM budgets WHERE user_id = %s AND category = %s;"
        pool = get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, (user_id, category))
                row = await cur.fetchone()
                if row:
                    return {"id": row[0], "category": row[1], "limit_amount": float(row[2])}
                return None

    async def get_all_budgets(self, user_id: int) -> list[dict]:
        """Get all budget limits for a user."""
        sql = "SELECT id, category, limit_amount FROM budgets WHERE user_id = %s ORDER BY category;"
        pool = get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, (user_id,))
                rows = await cur.fetchall()
                return [
                    {"id": r[0], "category": r[1], "limit_amount": float(r[2])}
                    for r in rows
                ]

    async def delete_budget(self, user_id: int, category: str) -> bool:
        """Delete a budget limit for a category."""
        sql = "DELETE FROM budgets WHERE user_id = %s AND category = %s;"
        pool = get_pool()
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(sql, (user_id, category))
                    deleted = cur.rowcount > 0
                await conn.commit()
                return deleted
        except Exception as e:
            logger.error(f"Failed to delete budget: {e}")
            raise

    async def get_total_budget(self, user_id: int) -> float:
        """Get the sum of all budget limits (overall monthly budget)."""
        sql = "SELECT COALESCE(SUM(limit_amount), 0) FROM budgets WHERE user_id = %s;"
        pool = get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, (user_id,))
                row = await cur.fetchone()
                return float(row[0])

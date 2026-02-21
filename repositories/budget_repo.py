"""
repositories/budget_repo.py
-----------------------------
Data access layer for monthly budgets.
"""

from typing import Optional

from db.connection import get_connection, release_connection
from utils.logger import get_logger

logger = get_logger(__name__)


class BudgetRepository:
    """Repository for CRUD operations on the budgets table."""

    def set_budget(self, user_id: int, category: str, limit_amount: float) -> dict:
        """Set or update a budget limit for a category."""
        sql = """
            INSERT INTO budgets (user_id, category, limit_amount)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, category)
            DO UPDATE SET limit_amount = EXCLUDED.limit_amount
            RETURNING id;
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id, category, limit_amount))
                row = cur.fetchone()
            conn.commit()
            return {"id": row[0], "category": category, "limit_amount": limit_amount}
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to set budget: {e}")
            raise
        finally:
            release_connection(conn)

    def get_budget(self, user_id: int, category: str) -> Optional[dict]:
        """Get the budget for a specific category."""
        sql = "SELECT id, category, limit_amount FROM budgets WHERE user_id = %s AND category = %s;"
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id, category))
                row = cur.fetchone()
                if row:
                    return {"id": row[0], "category": row[1], "limit_amount": float(row[2])}
                return None
        finally:
            release_connection(conn)

    def get_all_budgets(self, user_id: int) -> list[dict]:
        """Get all budget limits for a user."""
        sql = "SELECT id, category, limit_amount FROM budgets WHERE user_id = %s ORDER BY category;"
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id,))
                return [
                    {"id": r[0], "category": r[1], "limit_amount": float(r[2])}
                    for r in cur.fetchall()
                ]
        finally:
            release_connection(conn)

    def delete_budget(self, user_id: int, category: str) -> bool:
        """Delete a budget limit for a category."""
        sql = "DELETE FROM budgets WHERE user_id = %s AND category = %s;"
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id, category))
                deleted = cur.rowcount > 0
            conn.commit()
            return deleted
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to delete budget: {e}")
            raise
        finally:
            release_connection(conn)

    def get_total_budget(self, user_id: int) -> float:
        """Get the sum of all budget limits (overall monthly budget)."""
        sql = "SELECT COALESCE(SUM(limit_amount), 0) FROM budgets WHERE user_id = %s;"
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id,))
                return float(cur.fetchone()[0])
        finally:
            release_connection(conn)

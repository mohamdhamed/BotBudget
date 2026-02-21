"""
repositories/expense_repo.py
-----------------------------
Data access layer for expense/income transactions.
All SQL queries related to the `expenses` table live here.
"""

from datetime import date
from typing import Optional

from db.connection import get_connection, release_connection
from models.expense import Expense
from utils.logger import get_logger

logger = get_logger(__name__)


class ExpenseRepository:
    """Repository for CRUD operations on the expenses table."""

    # ── CREATE ────────────────────────────────────────────

    def add(self, expense: Expense) -> Expense:
        """
        Insert a new expense/income record.

        Args:
            expense: The Expense domain object to persist.

        Returns:
            The same Expense with its `id` and `created_at` populated.
        """
        sql = """
            INSERT INTO expenses (user_id, type, amount, currency, category, description, date, raw_text)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at;
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    expense.user_id, expense.type, expense.amount,
                    expense.currency, expense.category, expense.description,
                    expense.date, expense.raw_text,
                ))
                row = cur.fetchone()
                expense.id = row[0]
                expense.created_at = row[1]
            conn.commit()
            logger.info(f"Added {expense.type} #{expense.id} for user {expense.user_id}")
            return expense
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to add expense: {e}")
            raise
        finally:
            release_connection(conn)

    # ── READ ──────────────────────────────────────────────

    def get_by_id(self, expense_id: int, user_id: int) -> Optional[Expense]:
        """
        Fetch a single expense by ID, scoped to a user.

        Args:
            expense_id: Primary key.
            user_id: Telegram user ID (security scope).

        Returns:
            An Expense object or None if not found.
        """
        sql = "SELECT * FROM expenses WHERE id = %s AND user_id = %s;"
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (expense_id, user_id))
                row = cur.fetchone()
                return self._row_to_expense(row) if row else None
        finally:
            release_connection(conn)

    def get_by_date_range(
        self, user_id: int, start: date, end: date, tx_type: Optional[str] = None
    ) -> list[Expense]:
        """
        Fetch all transactions for a user within a date range.

        Args:
            user_id: Telegram user ID.
            start: Start date (inclusive).
            end: End date (inclusive).
            tx_type: Optional filter ('expense' or 'income').

        Returns:
            List of Expense objects ordered by date descending.
        """
        sql = "SELECT * FROM expenses WHERE user_id = %s AND date BETWEEN %s AND %s"
        params: list = [user_id, start, end]
        if tx_type:
            sql += " AND type = %s"
            params.append(tx_type)
        sql += " ORDER BY date DESC, id DESC;"

        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return [self._row_to_expense(r) for r in cur.fetchall()]
        finally:
            release_connection(conn)

    def get_category_summary(
        self, user_id: int, start: date, end: date
    ) -> list[dict]:
        """
        Get total spending grouped by category for a date range.

        Returns:
            List of dicts: [{'category': str, 'total': float}, ...]
        """
        sql = """
            SELECT category, SUM(amount) as total
            FROM expenses
            WHERE user_id = %s AND type = 'expense' AND date BETWEEN %s AND %s
            GROUP BY category
            ORDER BY total DESC;
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id, start, end))
                return [{"category": r[0], "total": float(r[1])} for r in cur.fetchall()]
        finally:
            release_connection(conn)

    def get_monthly_total(self, user_id: int, year: int, month: int) -> dict:
        """
        Get total income and expenses for a specific month.

        Returns:
            Dict with keys 'total_expenses', 'total_income', 'net'.
        """
        sql = """
            SELECT type, SUM(amount) as total
            FROM expenses
            WHERE user_id = %s
              AND EXTRACT(YEAR FROM date) = %s
              AND EXTRACT(MONTH FROM date) = %s
            GROUP BY type;
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id, year, month))
                result = {"total_expenses": 0.0, "total_income": 0.0, "net": 0.0}
                for row in cur.fetchall():
                    if row[0] == "expense":
                        result["total_expenses"] = float(row[1])
                    elif row[0] == "income":
                        result["total_income"] = float(row[1])
                result["net"] = result["total_income"] - result["total_expenses"]
                return result
        finally:
            release_connection(conn)

    def get_by_category(
        self, user_id: int, category: str, start: date, end: date
    ) -> list[Expense]:
        """
        Fetch all transactions for a specific category within a date range.

        Args:
            user_id: Telegram user ID.
            category: Category name (Arabic).
            start: Start date (inclusive).
            end: End date (inclusive).

        Returns:
            List of Expense objects filtered by category.
        """
        sql = """
            SELECT * FROM expenses
            WHERE user_id = %s AND category = %s AND date BETWEEN %s AND %s
            ORDER BY date DESC, id DESC;
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id, category, start, end))
                return [self._row_to_expense(r) for r in cur.fetchall()]
        finally:
            release_connection(conn)

    # ── UPDATE ────────────────────────────────────────────

    def update(self, expense: Expense) -> bool:
        """
        Update an existing expense record.

        Args:
            expense: Expense with updated fields (must have id set).

        Returns:
            True if a row was updated, False otherwise.
        """
        sql = """
            UPDATE expenses
            SET amount = %s, category = %s, description = %s, date = %s, type = %s
            WHERE id = %s AND user_id = %s;
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    expense.amount, expense.category, expense.description,
                    expense.date, expense.type, expense.id, expense.user_id,
                ))
                updated = cur.rowcount > 0
            conn.commit()
            return updated
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update expense #{expense.id}: {e}")
            raise
        finally:
            release_connection(conn)

    # ── DELETE ────────────────────────────────────────────

    def delete(self, expense_id: int, user_id: int) -> bool:
        """
        Delete an expense by ID, scoped to a user.

        Returns:
            True if a row was deleted, False otherwise.
        """
        sql = "DELETE FROM expenses WHERE id = %s AND user_id = %s;"
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (expense_id, user_id))
                deleted = cur.rowcount > 0
            conn.commit()
            if deleted:
                logger.info(f"Deleted expense #{expense_id} for user {user_id}")
            return deleted
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to delete expense #{expense_id}: {e}")
            raise
        finally:
            release_connection(conn)

    # ── HELPERS ───────────────────────────────────────────

    @staticmethod
    def _row_to_expense(row: tuple) -> Expense:
        """Convert a database row tuple to an Expense domain object."""
        return Expense(
            id=row[0],
            user_id=row[1],
            type=row[2],
            amount=float(row[3]),
            currency=row[4],
            category=row[5],
            description=row[6],
            date=row[7],
            raw_text=row[8],
            created_at=row[9],
        )

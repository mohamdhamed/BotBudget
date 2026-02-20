"""
repositories/recurring_repo.py
-------------------------------
Data access layer for recurring payments.
All SQL queries related to the `recurring_payments` table live here.
"""

from datetime import date, timedelta
from typing import Optional

from db.connection import get_connection, release_connection
from models.recurring import RecurringPayment
from utils.logger import get_logger

logger = get_logger(__name__)


class RecurringRepository:
    """Repository for CRUD operations on recurring_payments table."""

    # ── CREATE ────────────────────────────────────────────

    def add(self, payment: RecurringPayment) -> RecurringPayment:
        """
        Insert a new recurring payment.

        Args:
            payment: The RecurringPayment to persist.

        Returns:
            The same object with its `id` and `created_at` populated.
        """
        sql = """
            INSERT INTO recurring_payments
                (user_id, name, amount, currency, frequency, next_due_date, remind_days_before, active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at;
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    payment.user_id, payment.name, payment.amount,
                    payment.currency, payment.frequency, payment.next_due_date,
                    payment.remind_days_before, payment.active,
                ))
                row = cur.fetchone()
                payment.id = row[0]
                payment.created_at = row[1]
            conn.commit()
            logger.info(f"Added recurring payment '{payment.name}' #{payment.id}")
            return payment
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to add recurring payment: {e}")
            raise
        finally:
            release_connection(conn)

    # ── READ ──────────────────────────────────────────────

    def get_all(self, user_id: int, active_only: bool = True) -> list[RecurringPayment]:
        """
        Get all recurring payments for a user.

        Args:
            user_id: Telegram user ID.
            active_only: If True, only return active payments.

        Returns:
            List of RecurringPayment objects.
        """
        sql = "SELECT * FROM recurring_payments WHERE user_id = %s"
        params: list = [user_id]
        if active_only:
            sql += " AND active = TRUE"
        sql += " ORDER BY next_due_date ASC;"

        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return [self._row_to_payment(r) for r in cur.fetchall()]
        finally:
            release_connection(conn)

    def get_due_soon(self, days_ahead: int = 2) -> list[RecurringPayment]:
        """
        Get all active recurring payments due within the next N days.
        Used by the scheduler to send reminders.

        Args:
            days_ahead: Number of days to look ahead.

        Returns:
            List of RecurringPayment objects due soon.
        """
        target_date = date.today() + timedelta(days=days_ahead)
        sql = """
            SELECT * FROM recurring_payments
            WHERE active = TRUE AND next_due_date <= %s
            ORDER BY next_due_date ASC;
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (target_date,))
                return [self._row_to_payment(r) for r in cur.fetchall()]
        finally:
            release_connection(conn)

    def get_by_id(self, payment_id: int, user_id: int) -> Optional[RecurringPayment]:
        """Fetch a single recurring payment by ID, scoped to user."""
        sql = "SELECT * FROM recurring_payments WHERE id = %s AND user_id = %s;"
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (payment_id, user_id))
                row = cur.fetchone()
                return self._row_to_payment(row) if row else None
        finally:
            release_connection(conn)

    # ── UPDATE ────────────────────────────────────────────

    def advance_due_date(self, payment: RecurringPayment) -> None:
        """
        Advance the next_due_date based on the payment's frequency.
        Called after a reminder has been sent.

        Args:
            payment: The recurring payment to advance.
        """
        delta_map = {
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1),
            "monthly": timedelta(days=30),
            "yearly": timedelta(days=365),
        }
        new_date = payment.next_due_date + delta_map.get(
            payment.frequency, timedelta(days=30)
        )
        sql = "UPDATE recurring_payments SET next_due_date = %s WHERE id = %s;"
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (new_date, payment.id))
            conn.commit()
            logger.info(f"Advanced '{payment.name}' next due date to {new_date}")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to advance due date: {e}")
            raise
        finally:
            release_connection(conn)

    def toggle_active(self, payment_id: int, user_id: int, active: bool) -> bool:
        """Enable or disable a recurring payment."""
        sql = "UPDATE recurring_payments SET active = %s WHERE id = %s AND user_id = %s;"
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (active, payment_id, user_id))
                updated = cur.rowcount > 0
            conn.commit()
            return updated
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to toggle recurring #{payment_id}: {e}")
            raise
        finally:
            release_connection(conn)

    # ── DELETE ────────────────────────────────────────────

    def delete(self, payment_id: int, user_id: int) -> bool:
        """Delete a recurring payment by ID, scoped to user."""
        sql = "DELETE FROM recurring_payments WHERE id = %s AND user_id = %s;"
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (payment_id, user_id))
                deleted = cur.rowcount > 0
            conn.commit()
            if deleted:
                logger.info(f"Deleted recurring payment #{payment_id}")
            return deleted
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to delete recurring #{payment_id}: {e}")
            raise
        finally:
            release_connection(conn)

    # ── HELPERS ───────────────────────────────────────────

    @staticmethod
    def _row_to_payment(row: tuple) -> RecurringPayment:
        """Convert a database row tuple to a RecurringPayment domain object."""
        return RecurringPayment(
            id=row[0],
            user_id=row[1],
            name=row[2],
            amount=float(row[3]),
            currency=row[4],
            frequency=row[5],
            next_due_date=row[6],
            remind_days_before=row[7],
            active=row[8],
            created_at=row[9],
        )

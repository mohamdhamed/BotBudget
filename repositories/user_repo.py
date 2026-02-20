"""
repositories/user_repo.py
--------------------------
Data access layer for user records.
"""

from typing import Optional

from db.connection import get_connection, release_connection
from utils.logger import get_logger

logger = get_logger(__name__)


class UserRepository:
    """Repository for CRUD operations on the users table."""

    def ensure_user(self, telegram_id: int, first_name: Optional[str] = None) -> dict:
        """
        Insert a user if they don't exist, or return the existing record.
        Uses PostgreSQL's ON CONFLICT (upsert) for atomicity.

        Args:
            telegram_id: The Telegram user ID.
            first_name: Optional first name from Telegram.

        Returns:
            Dict with user data: {'id', 'telegram_id', 'first_name', 'currency'}.
        """
        sql = """
            INSERT INTO users (telegram_id, first_name)
            VALUES (%s, %s)
            ON CONFLICT (telegram_id) DO UPDATE SET first_name = EXCLUDED.first_name
            RETURNING id, telegram_id, first_name, currency;
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (telegram_id, first_name))
                row = cur.fetchone()
            conn.commit()
            return {
                "id": row[0],
                "telegram_id": row[1],
                "first_name": row[2],
                "currency": row[3],
            }
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to ensure user {telegram_id}: {e}")
            raise
        finally:
            release_connection(conn)

    def get_by_telegram_id(self, telegram_id: int) -> Optional[dict]:
        """
        Fetch a user by their Telegram ID.

        Returns:
            User dict or None.
        """
        sql = "SELECT id, telegram_id, first_name, currency FROM users WHERE telegram_id = %s;"
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (telegram_id,))
                row = cur.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "telegram_id": row[1],
                        "first_name": row[2],
                        "currency": row[3],
                    }
                return None
        finally:
            release_connection(conn)

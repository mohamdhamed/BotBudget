"""
repositories/allowed_users_repo.py
------------------------------------
Data access layer for dynamic user whitelist management.
"""

from db.connection import get_pool
from utils.logger import get_logger

logger = get_logger(__name__)


class AllowedUsersRepository:

    async def is_allowed(self, user_id: int) -> bool:
        """Check if a user is in the allowed list."""
        pool = get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT 1 FROM allowed_users WHERE user_id = %s;",
                    (user_id,),
                )
                return await cur.fetchone() is not None

    async def add_user(self, user_id: int, first_name: str = None, added_by: int = None) -> bool:
        """Add a user to the allowed list. Returns False if already exists."""
        pool = get_pool()
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """INSERT INTO allowed_users (user_id, first_name, added_by)
                           VALUES (%s, %s, %s)
                           ON CONFLICT (user_id) DO NOTHING;""",
                        (user_id, first_name, added_by),
                    )
                    inserted = cur.rowcount > 0
                await conn.commit()
            if inserted:
                logger.info(f"User {user_id} added to whitelist by {added_by}")
            return inserted
        except Exception as e:
            logger.error(f"Failed to add user {user_id}: {e}")
            raise

    async def remove_user(self, user_id: int) -> bool:
        """Remove a user from the allowed list."""
        pool = get_pool()
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "DELETE FROM allowed_users WHERE user_id = %s;",
                        (user_id,),
                    )
                    deleted = cur.rowcount > 0
                await conn.commit()
            if deleted:
                logger.info(f"User {user_id} removed from whitelist")
            return deleted
        except Exception as e:
            logger.error(f"Failed to remove user {user_id}: {e}")
            raise

    async def get_all(self) -> list[dict]:
        """Return all allowed users."""
        pool = get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT user_id, first_name, added_by, added_at FROM allowed_users ORDER BY added_at ASC;"
                )
                rows = await cur.fetchall()
                return [
                    {
                        "user_id": r[0],
                        "first_name": r[1] or "—",
                        "added_by": r[2],
                        "added_at": r[3],
                    }
                    for r in rows
                ]

    async def seed_from_list(self, user_ids: list[int]) -> None:
        """Seed the DB from a static list (migration from .env)."""
        for user_id in user_ids:
            await self.add_user(user_id, added_by=None)
        if user_ids:
            logger.info(f"Seeded {len(user_ids)} users from ALLOWED_USER_IDS config")

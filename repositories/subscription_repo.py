"""
repositories/subscription_repo.py
----------------------------------
Data access layer for user subscriptions (free / premium plans).
"""

from datetime import datetime, timezone
from typing import Optional

from db.connection import get_pool
from utils.logger import get_logger

logger = get_logger(__name__)


class SubscriptionRepository:
    """Repository for subscription/plan management."""

    async def ensure_free(self, user_id: int) -> dict:
        """Create a free subscription if none exists. Returns current plan."""
        sql = """
            INSERT INTO subscriptions (user_id, plan)
            VALUES (%s, 'free')
            ON CONFLICT (user_id) DO NOTHING;
        """
        pool = get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, (user_id,))
            await conn.commit()
        return await self.get_plan(user_id)

    async def grant_trial_if_new(self, user_id: int, days: int = 7) -> bool:
        """Grant a N-day premium trial only if user has no subscription row yet.
        Returns True if trial was granted, False if user already had a sub."""
        sql = f"""
            INSERT INTO subscriptions (user_id, plan, started_at, expires_at)
            VALUES (%s, 'premium', NOW(), NOW() + INTERVAL '{int(days)} days')
            ON CONFLICT (user_id) DO NOTHING
            RETURNING user_id;
        """
        pool = get_pool()
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(sql, (user_id,))
                    row = await cur.fetchone()
                await conn.commit()
            if row:
                logger.info(f"Granted {days}-day trial to new user {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to grant trial to {user_id}: {e}")
            return False

    async def get_plan(self, user_id: int) -> dict:
        """Get user's current plan. Returns dict with plan, expires_at, is_active."""
        sql = "SELECT plan, expires_at FROM subscriptions WHERE user_id = %s;"
        pool = get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, (user_id,))
                row = await cur.fetchone()

        if not row:
            return {"plan": "free", "expires_at": None, "is_premium": False}

        plan, expires_at = row[0], row[1]

        # Check if premium has expired
        if plan == "premium" and expires_at:
            if expires_at < datetime.now(timezone.utc):
                await self._downgrade(user_id)
                return {"plan": "free", "expires_at": None, "is_premium": False}

        return {
            "plan": plan,
            "expires_at": expires_at,
            "is_premium": plan == "premium",
        }

    async def upgrade(self, user_id: int, days: int, upgraded_by: int) -> bool:
        """Upgrade user to premium for N days."""
        sql = """
            INSERT INTO subscriptions (user_id, plan, started_at, expires_at, upgraded_by)
            VALUES (%s, 'premium', NOW(), NOW() + INTERVAL '%s days', %s)
            ON CONFLICT (user_id) DO UPDATE SET
                plan = 'premium',
                started_at = NOW(),
                expires_at = NOW() + INTERVAL '%s days',
                upgraded_by = %s;
        """
        pool = get_pool()
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    # Can't use %s for interval, use string formatting for days only
                    raw_sql = f"""
                        INSERT INTO subscriptions (user_id, plan, started_at, expires_at, upgraded_by)
                        VALUES (%s, 'premium', NOW(), NOW() + INTERVAL '{int(days)} days', %s)
                        ON CONFLICT (user_id) DO UPDATE SET
                            plan = 'premium',
                            started_at = NOW(),
                            expires_at = NOW() + INTERVAL '{int(days)} days',
                            upgraded_by = %s;
                    """
                    await cur.execute(raw_sql, (user_id, upgraded_by, upgraded_by))
                await conn.commit()
            logger.info(f"Upgraded user {user_id} to premium for {days} days")
            return True
        except Exception as e:
            logger.error(f"Failed to upgrade user {user_id}: {e}")
            return False

    async def downgrade(self, user_id: int) -> bool:
        """Downgrade user to free plan."""
        return await self._downgrade(user_id)

    async def _downgrade(self, user_id: int) -> bool:
        sql = """
            UPDATE subscriptions SET plan = 'free', expires_at = NULL
            WHERE user_id = %s;
        """
        pool = get_pool()
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(sql, (user_id,))
                    updated = cur.rowcount > 0
                await conn.commit()
            return updated
        except Exception as e:
            logger.error(f"Failed to downgrade user {user_id}: {e}")
            return False

    async def get_all_subscribers(self) -> list[dict]:
        """Get all users with their subscription info."""
        sql = """
            SELECT s.user_id, s.plan, s.started_at, s.expires_at,
                   u.first_name
            FROM subscriptions s
            LEFT JOIN users u ON u.telegram_id = s.user_id
            ORDER BY s.plan DESC, s.started_at DESC;
        """
        pool = get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql)
                rows = await cur.fetchall()
                return [
                    {
                        "user_id": r[0],
                        "plan": r[1],
                        "started_at": r[2],
                        "expires_at": r[3],
                        "first_name": r[4],
                    }
                    for r in rows
                ]

    async def count_month_transactions(self, user_id: int) -> int:
        """Count transactions this month for a user."""
        sql = """
            SELECT COUNT(*) FROM expenses
            WHERE user_id = %s
            AND date_trunc('month', created_at) = date_trunc('month', NOW());
        """
        pool = get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, (user_id,))
                row = await cur.fetchone()
                return row[0] if row else 0

"""
db/connection.py
----------------
Manages the PostgreSQL async connection pool.
Uses psycopg AsyncConnectionPool for async connection reuse.
"""

import sys
from psycopg_pool import AsyncConnectionPool
import psycopg
from config import DATABASE_URL
from utils.logger import get_logger

logger = get_logger(__name__)

_pool: AsyncConnectionPool | None = None


async def init_pool(min_conn: int = 1, max_conn: int = 5) -> None:
    """
    Initialize the database async connection pool.

    Args:
        min_conn: Minimum number of connections to keep open.
        max_conn: Maximum number of connections allowed.
    """
    global _pool
    if _pool is not None:
        return
    try:
        _pool = AsyncConnectionPool(
            conninfo=DATABASE_URL,
            min_size=min_conn,
            max_size=max_conn,
            open=False  # We will open it explicitly
        )
        await _pool.open()
        await _pool.wait()
        logger.info("Database async connection pool initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}")
        raise


def get_pool() -> AsyncConnectionPool:
    """
    Get the async connection pool.

    Returns:
        The AsyncConnectionPool instance.
    """
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call await init_pool() first.")
    return _pool


async def close_pool() -> None:
    """Close all connections in the pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Database async connection pool closed.")

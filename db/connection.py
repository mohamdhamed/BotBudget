"""
db/connection.py
----------------
Manages the PostgreSQL connection pool.
Uses psycopg2's SimpleConnectionPool for efficient connection reuse.
"""

import psycopg2
from psycopg2 import pool, extras
from config import DATABASE_URL
from utils.logger import get_logger

logger = get_logger(__name__)

_pool: pool.SimpleConnectionPool | None = None


def init_pool(min_conn: int = 1, max_conn: int = 5) -> None:
    """
    Initialize the database connection pool.

    Args:
        min_conn: Minimum number of connections to keep open.
        max_conn: Maximum number of connections allowed.

    Raises:
        psycopg2.OperationalError: If the database is unreachable.
    """
    global _pool
    if _pool is not None:
        return
    try:
        _pool = pool.SimpleConnectionPool(min_conn, max_conn, DATABASE_URL)
        logger.info("Database connection pool initialized successfully.")
    except psycopg2.OperationalError as e:
        logger.error(f"Failed to initialize database pool: {e}")
        raise


def get_connection():
    """
    Get a connection from the pool.

    Returns:
        A psycopg2 connection object.

    Raises:
        RuntimeError: If the pool has not been initialized.
    """
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_pool() first.")
    return _pool.getconn()


def release_connection(conn) -> None:
    """
    Return a connection back to the pool.

    Args:
        conn: The psycopg2 connection to release.
    """
    if _pool is not None:
        _pool.putconn(conn)


def close_pool() -> None:
    """Close all connections in the pool."""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
        logger.info("Database connection pool closed.")

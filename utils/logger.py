"""
utils/logger.py
---------------
Centralized logging configuration.
All modules should use `get_logger(__name__)` to obtain a logger instance.
"""

import logging
import sys

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_initialized = False


def _init_logging() -> None:
    """Configure the root logger once."""
    global _initialized
    if _initialized:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger instance.

    Args:
        name: Usually ``__name__`` of the calling module.

    Returns:
        A configured logging.Logger.
    """
    _init_logging()
    return logging.getLogger(name)

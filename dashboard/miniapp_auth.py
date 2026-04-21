"""
dashboard/miniapp_auth.py
--------------------------
Telegram Mini App initData HMAC verification.

Reference: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

from __future__ import annotations

import hmac
import hashlib
import json
import time
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException, status

from config import TELEGRAM_BOT_TOKEN
from utils.logger import get_logger

logger = get_logger(__name__)


def verify_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int = 86400,
) -> dict:
    """Verify Telegram WebApp initData and return the parsed user dict.

    Raises HTTPException(401) on any failure.
    """
    if not init_data:
        raise HTTPException(status_code=401, detail="Missing initData")
    if not bot_token:
        raise HTTPException(status_code=500, detail="Bot token not configured")

    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=True))
    except ValueError:
        raise HTTPException(status_code=401, detail="Malformed initData")

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=401, detail="Missing hash in initData")

    # Build data_check_string: sorted key=value pairs joined by \n
    data_check_string = "\n".join(
        f"{k}={parsed[k]}" for k in sorted(parsed.keys())
    )

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        logger.warning("initData hash mismatch")
        raise HTTPException(status_code=401, detail="Invalid initData signature")

    # Freshness check
    auth_date_str = parsed.get("auth_date")
    if not auth_date_str:
        raise HTTPException(status_code=401, detail="Missing auth_date")
    try:
        auth_date = int(auth_date_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid auth_date")
    if max_age_seconds > 0 and (time.time() - auth_date) > max_age_seconds:
        raise HTTPException(status_code=401, detail="initData expired")

    user_raw = parsed.get("user")
    if not user_raw:
        raise HTTPException(status_code=401, detail="Missing user in initData")
    try:
        user = json.loads(user_raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=401, detail="Invalid user JSON")

    if not isinstance(user, dict) or "id" not in user:
        raise HTTPException(status_code=401, detail="Invalid user payload")

    return user


async def get_current_user(
    x_telegram_init_data: str = Header(..., alias="X-Telegram-Init-Data"),
) -> dict:
    """FastAPI dependency returning the authenticated Telegram user dict."""
    return verify_init_data(x_telegram_init_data, TELEGRAM_BOT_TOKEN)

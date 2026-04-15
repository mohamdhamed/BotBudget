"""Broadcast messages to users."""

import asyncio

import httpx
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse

from config import TELEGRAM_BOT_TOKEN
from dashboard.auth import verify_admin
from dashboard.queries import get_all_user_ids, get_premium_user_ids
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


async def _send_to_user(client: httpx.AsyncClient, user_id: int, text: str) -> bool:
    """Send a single telegram message. Returns True on success."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = await client.post(
            url,
            json={"chat_id": user_id, "text": text, "parse_mode": "HTML"},
            timeout=10.0,
        )
        return r.status_code == 200
    except Exception as e:
        logger.warning(f"Broadcast failed for {user_id}: {e}")
        return False


async def _broadcast(user_ids: list[int], text: str) -> tuple[int, int]:
    """Send text to all user_ids. Returns (success_count, fail_count)."""
    sent = 0
    failed = 0
    async with httpx.AsyncClient() as client:
        # send in small batches to avoid Telegram rate limits (~30 msg/s)
        for i in range(0, len(user_ids), 25):
            batch = user_ids[i : i + 25]
            results = await asyncio.gather(
                *[_send_to_user(client, uid, text) for uid in batch]
            )
            sent += sum(1 for r in results if r)
            failed += sum(1 for r in results if not r)
            await asyncio.sleep(1)  # pace throughput
    return sent, failed


@router.get("/broadcast", response_class=HTMLResponse)
async def broadcast_page(request: Request, user: str = Depends(verify_admin)):
    all_count = len(await get_all_user_ids())
    premium_count = len(await get_premium_user_ids())
    return request.app.state.templates.TemplateResponse(
        request,
        "broadcast.html",
        {
            "all_count": all_count,
            "premium_count": premium_count,
            "result": None,
            "active_page": "broadcast",
        },
    )


@router.post("/broadcast", response_class=HTMLResponse)
async def broadcast_send(
    request: Request,
    message: str = Form(...),
    target: str = Form("all"),
    user: str = Depends(verify_admin),
):
    if target == "premium":
        user_ids = await get_premium_user_ids()
    else:
        user_ids = await get_all_user_ids()

    sent, failed = await _broadcast(user_ids, message)
    logger.info(f"Broadcast by {user}: target={target}, sent={sent}, failed={failed}")

    all_count = len(await get_all_user_ids())
    premium_count = len(await get_premium_user_ids())

    return request.app.state.templates.TemplateResponse(
        request,
        "broadcast.html",
        {
            "all_count": all_count,
            "premium_count": premium_count,
            "result": {"sent": sent, "failed": failed, "target": target},
            "active_page": "broadcast",
        },
    )

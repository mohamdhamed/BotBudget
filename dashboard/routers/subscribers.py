"""Subscribers / subscription management page."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from dashboard.auth import verify_admin
from dashboard.queries import get_subscribers

router = APIRouter()


@router.get("/subscribers", response_class=HTMLResponse)
async def subscribers_page(request: Request, user: str = Depends(verify_admin)):
    subs = await get_subscribers()
    expiring = [s for s in subs if s["expiring_soon"]]
    return request.app.state.templates.TemplateResponse(
        "subscribers.html",
        {
            "request": request,
            "subscribers": subs,
            "expiring": expiring,
            "active_page": "subscribers",
        },
    )

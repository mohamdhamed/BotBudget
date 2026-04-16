"""Overview / home dashboard page."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from dashboard.auth import verify_admin
from dashboard.queries import (
    get_overview_stats,
    get_user_growth_chart,
    get_daily_activity,
    get_top_categories,
)

router = APIRouter()


@router.get("/admin", response_class=HTMLResponse)
async def overview(request: Request, user: str = Depends(verify_admin)):
    stats = await get_overview_stats()
    growth = await get_user_growth_chart(30)
    activity = await get_daily_activity(30)
    top_cats = await get_top_categories(30)

    return request.app.state.templates.TemplateResponse(
        request,
        "overview.html",
        {
            "stats": stats,
            "growth": growth,
            "activity": activity,
            "top_cats": top_cats,
            "active_page": "overview",
        },
    )

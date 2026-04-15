"""Users management page."""

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from dashboard.auth import verify_admin
from dashboard.queries import get_all_users
from repositories.subscription_repo import SubscriptionRepository

router = APIRouter()
_sub_repo = SubscriptionRepository()


@router.get("/users", response_class=HTMLResponse)
async def users_page(request: Request, search: str = "", user: str = Depends(verify_admin)):
    users = await get_all_users(search=search)
    return request.app.state.templates.TemplateResponse(
        "users.html",
        {
            "request": request,
            "users": users,
            "search": search,
            "active_page": "users",
        },
    )


@router.post("/users/upgrade")
async def upgrade_user(
    user_id: int = Form(...),
    days: int = Form(30),
    user: str = Depends(verify_admin),
):
    await _sub_repo.upgrade(user_id, days, upgraded_by=0)
    return RedirectResponse(url="/users", status_code=303)


@router.post("/users/downgrade")
async def downgrade_user(
    user_id: int = Form(...),
    user: str = Depends(verify_admin),
):
    await _sub_repo.downgrade(user_id)
    return RedirectResponse(url="/users", status_code=303)

"""Users management page."""

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from dashboard.auth import verify_admin
from dashboard.queries import (
    get_all_users,
    get_user_detail,
    delete_user_and_data,
    delete_user_expenses,
)
from repositories.subscription_repo import SubscriptionRepository

router = APIRouter()
_sub_repo = SubscriptionRepository()


@router.get("/admin/users", response_class=HTMLResponse)
async def users_page(request: Request, search: str = "", user: str = Depends(verify_admin)):
    users = await get_all_users(search=search)
    return request.app.state.templates.TemplateResponse(
        request,
        "users.html",
        {
            "users": users,
            "search": search,
            "active_page": "users",
        },
    )


@router.get("/admin/users/{user_id}", response_class=HTMLResponse)
async def user_detail_page(user_id: int, request: Request, user: str = Depends(verify_admin)):
    data = await get_user_detail(user_id)
    if not data:
        return HTMLResponse("<h1>مستخدم غير موجود</h1>", status_code=404)
    return request.app.state.templates.TemplateResponse(
        request,
        "user_detail.html",
        {
            "active_page": "users",
            **data,
        },
    )


@router.post("/admin/users/upgrade")
async def upgrade_user(
    user_id: int = Form(...),
    days: int = Form(30),
    user: str = Depends(verify_admin),
):
    await _sub_repo.upgrade(user_id, days, upgraded_by=0)
    return RedirectResponse(url="/users", status_code=303)


@router.post("/admin/users/downgrade")
async def downgrade_user(
    user_id: int = Form(...),
    user: str = Depends(verify_admin),
):
    await _sub_repo.downgrade(user_id)
    return RedirectResponse(url="/users", status_code=303)


@router.post("/admin/users/{user_id}/delete")
async def delete_user(user_id: int, user: str = Depends(verify_admin)):
    await delete_user_and_data(user_id)
    return RedirectResponse(url="/users", status_code=303)


@router.post("/admin/users/{user_id}/delete-expenses")
async def delete_expenses(user_id: int, user: str = Depends(verify_admin)):
    await delete_user_expenses(user_id)
    return RedirectResponse(url=f"/users/{user_id}", status_code=303)

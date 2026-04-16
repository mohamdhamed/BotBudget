"""Data management page — cleanup, export, stats."""

import csv
import io

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse

from dashboard.auth import verify_admin
from dashboard.queries import (
    get_db_stats,
    get_all_users,
    clean_old_expenses,
    delete_inactive_users,
    clean_orphaned_data,
)

router = APIRouter()


@router.get("/admin/data", response_class=HTMLResponse)
async def data_page(request: Request, user: str = Depends(verify_admin)):
    db_stats = await get_db_stats()
    return request.app.state.templates.TemplateResponse(
        request,
        "data.html",
        {
            "db_stats": db_stats,
            "result": None,
            "active_page": "data",
        },
    )


@router.post("/admin/data/clean-old-expenses", response_class=HTMLResponse)
async def clean_old(request: Request, months: int = Form(12), user: str = Depends(verify_admin)):
    count = await clean_old_expenses(months)
    db_stats = await get_db_stats()
    return request.app.state.templates.TemplateResponse(
        request,
        "data.html",
        {
            "db_stats": db_stats,
            "result": {"success": True, "message": f"✅ تم حذف {count} معاملة أقدم من {months} شهر."},
            "active_page": "data",
        },
    )


@router.post("/admin/data/delete-inactive", response_class=HTMLResponse)
async def delete_inactive(request: Request, days: int = Form(90), user: str = Depends(verify_admin)):
    count = await delete_inactive_users(days)
    db_stats = await get_db_stats()
    return request.app.state.templates.TemplateResponse(
        request,
        "data.html",
        {
            "db_stats": db_stats,
            "result": {"success": True, "message": f"✅ تم حذف {count} مستخدم غير نشط منذ أكثر من {days} يوم."},
            "active_page": "data",
        },
    )


@router.post("/admin/data/clean-orphaned", response_class=HTMLResponse)
async def clean_orphaned(request: Request, user: str = Depends(verify_admin)):
    result = await clean_orphaned_data()
    db_stats = await get_db_stats()
    return request.app.state.templates.TemplateResponse(
        request,
        "data.html",
        {
            "db_stats": db_stats,
            "result": {
                "success": True,
                "message": f"✅ تم حذف {result['subscriptions']} اشتراك و{result['budgets']} ميزانية معلقة.",
            },
            "active_page": "data",
        },
    )


@router.get("/admin/data/export-users")
async def export_users(user: str = Depends(verify_admin)):
    users = await get_all_users(limit=10000)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["user_id", "name", "plan", "created_at", "expires_at", "tx_count"])
    writer.writeheader()
    writer.writerows(users)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=botbudget_users.csv"},
    )

"""
dashboard/routers/miniapp.py
-----------------------------
Telegram Mini App JSON API.

All endpoints require the `X-Telegram-Init-Data` header, verified against
the bot token via HMAC (see `dashboard.miniapp_auth`).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict

from dashboard.miniapp_auth import get_current_user
from models.expense import Expense
from repositories.expense_repo import ExpenseRepository
from repositories.subscription_repo import SubscriptionRepository
from repositories.user_repo import UserRepository
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/miniapp", tags=["miniapp"])

_expense_repo = ExpenseRepository()
_sub_repo = SubscriptionRepository()
_user_repo = UserRepository()


# ── Pydantic schemas ──────────────────────────────────────

class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: str
    amount: float
    currency: str
    category: str
    description: Optional[str] = None
    date: date
    created_at: Optional[datetime] = None


class TransactionCreate(BaseModel):
    type: Literal["expense", "income"]
    amount: float = Field(gt=0)
    currency: str = "EUR"
    category: str = Field(min_length=1, max_length=64)
    description: Optional[str] = Field(default=None, max_length=500)
    date: Optional[date] = None


class CategorySummaryItem(BaseModel):
    category: str
    total: float


class PlanInfo(BaseModel):
    plan: str
    expires_at: Optional[datetime] = None
    is_premium: bool


class MeResponse(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None
    plan: PlanInfo


class DashboardResponse(BaseModel):
    balance: float
    income_month: float
    expense_month: float
    currency: str = "EUR"
    recent: list[TransactionOut]


# ── Helpers ───────────────────────────────────────────────

def _expense_to_out(e: Expense) -> TransactionOut:
    return TransactionOut(
        id=e.id,
        type=e.type,
        amount=e.amount,
        currency=e.currency,
        category=e.category,
        description=e.description,
        date=e.date,
        created_at=e.created_at,
    )


# ── Routes ────────────────────────────────────────────────

@router.get("/me", response_model=MeResponse)
async def me(user: dict = Depends(get_current_user)):
    plan = await _sub_repo.get_plan(int(user["id"]))
    return MeResponse(
        id=int(user["id"]),
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
        username=user.get("username"),
        language_code=user.get("language_code"),
        plan=PlanInfo(**plan),
    )


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(user: dict = Depends(get_current_user)):
    uid = int(user["id"])
    today = date.today()
    monthly = await _expense_repo.get_monthly_total(uid, today.year, today.month)
    overall = await _expense_repo.get_overall_balance(uid)
    recent = await _expense_repo.get_last_n(uid, 5)
    return DashboardResponse(
        balance=overall.get("balance", 0.0),
        income_month=monthly.get("total_income", 0.0),
        expense_month=monthly.get("total_expenses", 0.0),
        recent=[_expense_to_out(e) for e in recent],
    )


@router.get("/transactions", response_model=list[TransactionOut])
async def list_transactions(
    user: dict = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None),
):
    uid = int(user["id"])
    if q:
        items = await _expense_repo.search_by_text(uid, q, limit=limit)
        return [_expense_to_out(e) for e in items]

    # Wide window fetch; simple offset/limit slice on the python side to
    # avoid touching the repository for a one-off method.
    start = date(2000, 1, 1)
    end = date(2999, 12, 31)
    items = await _expense_repo.get_by_date_range(uid, start, end)
    return [_expense_to_out(e) for e in items[offset : offset + limit]]


@router.post("/transactions", response_model=TransactionOut, status_code=201)
async def create_transaction(
    body: TransactionCreate,
    user: dict = Depends(get_current_user),
):
    uid = int(user["id"])
    exp = Expense(
        user_id=uid,
        type=body.type,
        amount=body.amount,
        currency=body.currency,
        category=body.category,
        description=body.description,
        date=body.date or date.today(),
        raw_text=None,
    )
    saved = await _expense_repo.add(exp)
    return _expense_to_out(saved)


@router.delete("/transactions/{tx_id}", status_code=204)
async def delete_transaction(
    tx_id: int,
    user: dict = Depends(get_current_user),
):
    uid = int(user["id"])
    ok = await _expense_repo.delete(tx_id, uid)
    if not ok:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return None


@router.get("/categories/summary", response_model=list[CategorySummaryItem])
async def categories_summary(
    user: dict = Depends(get_current_user),
    period: Literal["month", "year", "all"] = Query("month"),
):
    uid = int(user["id"])
    today = date.today()
    if period == "month":
        start = today.replace(day=1)
        end = today
    elif period == "year":
        start = today.replace(month=1, day=1)
        end = today
    else:
        start = date(2000, 1, 1)
        end = date(2999, 12, 31)
    rows = await _expense_repo.get_category_summary(uid, start, end)
    return [CategorySummaryItem(**r) for r in rows]

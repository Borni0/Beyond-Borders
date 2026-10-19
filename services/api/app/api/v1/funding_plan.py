"""Funding-plan aggregate endpoint.

Composes the existing funding sources, payment events, savings goals, and
FX table into the cards the ``/funding-plan`` page renders:

* ``GET /plans/{plan_id}/funding-plan/summary`` — per-currency buckets,
  savings rollup, upcoming + overdue totals.
* ``GET /plans/{plan_id}/funding-plan/timeline`` — chronological list of
  every payment the student owns (projected recurrences included).
* ``POST /plans/{plan_id}/funding-plan/convert`` — preview a conversion +
  flat transfer fee.
* ``GET /plans/{plan_id}/funding-plan/export.csv`` — CSV export of every
  payment linked to this plan.
"""

from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.deps import CurrentUser, DbSessionDep
from app.core.errors import ApiError
from app.repositories import (
    exchange_rate_repo,
    payment_event_repo,
    study_plan_repo,
)
from app.services.funding_plan_service import (
    DEFAULT_TRANSFER_FEE_PCT,
    estimate_conversion,
    load_funding_plan_summary,
    load_timeline,
)
from app.services.readiness_service import _hydrate_funding, _hydrate_rate

router = APIRouter(prefix="/plans/{plan_id}/funding-plan", tags=["funding-plan"])


# ---------- Schemas (route-local; the page only needs a handful of shapes) --

class FundingPlanSummaryPublic(BaseModel):
    plan_id: str
    base_currency: str
    buckets: list[dict]
    savings_buckets: list[dict]
    upcoming_payments: str
    overdue_payments: str
    upcoming_payments_count: int
    overdue_payments_count: int
    payments_by_currency: dict[str, str]
    notes: list[str]


class TimelinePublic(BaseModel):
    plan_id: str
    entries: list[dict]


class ConvertRequest(BaseModel):
    from_amount: Decimal = Field(ge=0)
    from_currency: str = Field(min_length=3, max_length=3)
    to_currency: str = Field(min_length=3, max_length=3)
    fee_pct: Optional[Decimal] = Field(default=None, ge=0)


class ConvertResponse(BaseModel):
    from_currency: str
    to_currency: str
    from_amount: str
    converted_amount: str
    fee_pct: str
    fee_amount: str
    total_cost: str
    rate_used: str
    rate_type: str


# ---------- Helpers --------------------------------------------------------

def _load_plan_or_404(db, user_id, plan_id):  # type: ignore[no-untyped-def]
    plan = study_plan_repo.get_plan(db, user_id, plan_id)
    if plan is None:
        raise ApiError("NOT_FOUND", "Plan not found.", http_status=404)
    return plan


# ---------- Routes ---------------------------------------------------------

@router.get("/summary", response_model=FundingPlanSummaryPublic)
def funding_plan_summary(
    plan_id: str,
    db: DbSessionDep,
    current_user: CurrentUser,
    upcoming_window_days: int = Query(default=30, ge=1, le=365),
) -> FundingPlanSummaryPublic:
    plan = _load_plan_or_404(db, current_user.id, plan_id)
    summary = load_funding_plan_summary(
        db,
        user_id=current_user.id,
        plan=plan,
        upcoming_window_days=upcoming_window_days,
    )
    return FundingPlanSummaryPublic(
        plan_id=plan.id,
        base_currency=summary.base_currency,
        buckets=summary.to_dict()["buckets"],
        savings_buckets=summary.to_dict()["savings_buckets"],
        upcoming_payments=summary.to_dict()["upcoming_payments"],
        overdue_payments=summary.to_dict()["overdue_payments"],
        upcoming_payments_count=summary.to_dict()["upcoming_payments_count"],
        overdue_payments_count=summary.to_dict()["overdue_payments_count"],
        payments_by_currency=summary.to_dict()["payments_by_currency"],
        notes=summary.to_dict()["notes"],
    )


@router.get("/timeline", response_model=TimelinePublic)
def funding_plan_timeline(
    plan_id: str,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> TimelinePublic:
    plan = _load_plan_or_404(db, current_user.id, plan_id)
    entries = load_timeline(db, user_id=current_user.id, plan=plan)
    return TimelinePublic(
        plan_id=plan.id,
        entries=[e.to_dict() for e in entries],
    )


@router.post(
    "/convert",
    response_model=ConvertResponse,
    status_code=status.HTTP_200_OK,
)
def funding_plan_convert(
    plan_id: str,
    payload: ConvertRequest,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> ConvertResponse:
    # We don't *need* the plan for the math, but we use it as the ownership
    # gate so users can only convert in the context of their own plan.
    plan = _load_plan_or_404(db, current_user.id, plan_id)

    raw_rates = exchange_rate_repo.list_rates(db, current_user.id)
    rates = [_hydrate_rate(r) for r in raw_rates]

    estimate = estimate_conversion(
        payload.from_amount,
        payload.from_currency,
        payload.to_currency,
        rates,
        fee_pct=payload.fee_pct if payload.fee_pct is not None else DEFAULT_TRANSFER_FEE_PCT,
    )
    return ConvertResponse(**estimate.to_dict())


@router.get("/export.csv")
def funding_plan_export_csv(
    plan_id: str,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> StreamingResponse:
    plan = _load_plan_or_404(db, current_user.id, plan_id)
    events = payment_event_repo.list_events(db, current_user.id, plan_id=plan.id)
    today = date.today()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "title", "category", "amount", "currency", "due_date",
        "status", "display_status", "is_recurring",
        "recurrence_frequency", "recurrence_end_date", "notes",
    ])
    for ev in events:
        from app.services.funding_plan_service import derive_display_status

        writer.writerow([
            ev.title,
            ev.category,
            str(ev.amount),
            ev.currency,
            ev.due_date.isoformat(),
            ev.status,
            derive_display_status(ev.status, ev.due_date, today),
            "yes" if ev.is_recurring else "no",
            ev.recurrence_frequency or "",
            ev.recurrence_end_date.isoformat() if ev.recurrence_end_date else "",
            ev.notes or "",
        ])

    buf.seek(0)
    headers = {
        "Content-Disposition": (
            f'attachment; filename="funding-plan-{plan.id}.csv"'
        ),
        "Content-Type": "text/csv; charset=utf-8",
    }
    return StreamingResponse(buf, media_type="text/csv", headers=headers)


__all__ = ["router"]
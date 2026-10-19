"""Expense tracking endpoints (spec §3.6 — Spending Tracker).

* ``GET    /api/v1/expenses``              — list the caller's expenses
* ``POST   /api/v1/expenses``              — log a new expense
* ``GET    /api/v1/expenses/{id}``         — fetch one
* ``PATCH  /api/v1/expenses/{id}``         — edit
* ``DELETE /api/v1/expenses/{id}``         — remove
* ``POST   /api/v1/expenses/import.csv``   — bulk-import from a CSV body
* ``GET    /api/v1/expenses/export.csv``   — export as CSV
* ``GET    /api/v1/expenses/summary``      — per-month + per-category totals

All lookups are scoped to ``current_user`` and return ``404`` on
cross-tenant access.
"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import Response

from app.core.deps import CurrentUser, DbSessionDep
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseImportResult,
    ExpensePublic,
    ExpenseSummary,
    ExpenseUpdate,
)
from app.services import expense_service

router = APIRouter(prefix="/expenses", tags=["expenses"])


# ---------- CRUD -----------------------------------------------------------


@router.get("", response_model=list[ExpensePublic])
def list_expenses(
    db: DbSessionDep,
    current_user: CurrentUser,
    plan_id: str | None = Query(default=None),
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=1000),
) -> list[ExpensePublic]:
    return expense_service.list_expenses(
        db,
        current_user.id,
        plan_id=plan_id,
        since=since,
        until=until,
        limit=limit,
    )


@router.post(
    "",
    response_model=ExpensePublic,
    status_code=status.HTTP_201_CREATED,
)
def create_expense(
    body: ExpenseCreate,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> ExpensePublic:
    return expense_service.create_expense(db, current_user.id, body)


# ---------- CSV import / export / summary (must precede /{expense_id}) ----


@router.post(
    "/import.csv",
    response_model=ExpenseImportResult,
    status_code=status.HTTP_200_OK,
)
async def import_expenses_csv(
    request: Request,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> ExpenseImportResult:
    """Bulk-import expenses from a CSV body. Bad rows are skipped.

    The request body is the raw CSV text — the same shape that
    ``export.csv`` returns.
    """
    text = (await request.body()).decode("utf-8")
    return expense_service.import_csv(db, current_user.id, text)


@router.get("/export.csv")
def export_expenses_csv(
    db: DbSessionDep,
    current_user: CurrentUser,
    plan_id: str | None = Query(default=None),
) -> Response:
    text = expense_service.export_csv(db, current_user.id, plan_id=plan_id)
    return Response(
        content=text,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="expenses.csv"',
        },
    )


@router.get("/summary", response_model=ExpenseSummary)
def summarize_expenses(
    db: DbSessionDep,
    current_user: CurrentUser,
    plan_id: str | None = Query(default=None),
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
) -> ExpenseSummary:
    return expense_service.summarize(
        db,
        current_user.id,
        plan_id=plan_id,
        since=since,
        until=until,
    )


# ---------- Per-expense (declared last so the named routes win) -----------


@router.get("/{expense_id}", response_model=ExpensePublic)
def get_expense(
    expense_id: str,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> ExpensePublic:
    from app.core.errors import ApiError
    from app.repositories import expense_repo

    row = expense_repo.get_expense(db, current_user.id, expense_id)
    if row is None:
        raise ApiError("NOT_FOUND", "Expense not found.", http_status=404)
    return expense_service._to_public(row)


@router.patch("/{expense_id}", response_model=ExpensePublic)
def update_expense(
    expense_id: str,
    body: ExpenseUpdate,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> ExpensePublic:
    return expense_service.update_expense(
        db, current_user.id, expense_id, body
    )


@router.delete(
    "/{expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_expense(
    expense_id: str,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> None:
    expense_service.delete_expense(db, current_user.id, expense_id)
    return None


__all__ = ["router"]
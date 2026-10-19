"""Repository for the per-user expense log."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.expense import Expense


def list_expenses(
    db: Session,
    user_id: str,
    *,
    plan_id: str | None = None,
    since: date | None = None,
    until: date | None = None,
    limit: int | None = None,
) -> Sequence[Expense]:
    stmt = select(Expense).where(Expense.user_id == user_id)
    if plan_id is not None:
        stmt = stmt.where(Expense.plan_id == plan_id)
    if since is not None:
        stmt = stmt.where(Expense.spent_on >= since)
    if until is not None:
        stmt = stmt.where(Expense.spent_on <= until)
    stmt = stmt.order_by(Expense.spent_on.desc(), Expense.created_at.desc())
    if limit is not None:
        stmt = stmt.limit(limit)
    return db.execute(stmt).scalars().all()


def get_expense(db: Session, user_id: str, expense_id: str) -> Expense | None:
    stmt = select(Expense).where(
        Expense.id == expense_id, Expense.user_id == user_id
    )
    return db.execute(stmt).scalar_one_or_none()


def create_expense(
    db: Session,
    *,
    user_id: str,
    plan_id: str | None,
    category: str,
    description: str,
    amount: Decimal,
    currency: str,
    spent_on: date,
    payment_method: str | None,
    notes: str | None,
) -> Expense:
    row = Expense(
        user_id=user_id,
        plan_id=plan_id,
        category=category,
        description=description,
        amount=amount,
        currency=currency,
        spent_on=spent_on,
        payment_method=payment_method,
        notes=notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_expense(db: Session, row: Expense, **fields: object) -> Expense:
    for key, value in fields.items():
        if not hasattr(row, key):
            continue
        if value is None and key not in ("plan_id", "payment_method", "notes"):
            continue
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_expense(db: Session, row: Expense) -> None:
    db.delete(row)
    db.commit()


__all__ = [
    "create_expense",
    "delete_expense",
    "get_expense",
    "list_expenses",
    "update_expense",
]
"""Repository for study plans. Always scope by user_id."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.study_plan import StudyPlan


def end_date_for(start: date, duration_months: int) -> date:
    """Compute the end-date (exclusive) of a plan.

    Adding `duration_months` to a Python date handles month-end rollover:
    2026-01-31 + 1 month → 2026-02-28, not "Feb 31".
    """
    year = start.year + (start.month - 1 + duration_months) // 12
    month = (start.month - 1 + duration_months) % 12 + 1
    # Cap day-of-month at the destination's max.
    import calendar

    last_day = calendar.monthrange(year, month)[1]
    day = min(start.day, last_day)
    return date(year, month, day)


def list_plans(db: Session, user_id: str) -> Sequence[StudyPlan]:
    stmt = (
        select(StudyPlan)
        .where(StudyPlan.user_id == user_id)
        .order_by(StudyPlan.start_date.desc(), StudyPlan.created_at.desc())
    )
    return db.execute(stmt).scalars().all()


def get_plan(db: Session, user_id: str, plan_id: str) -> StudyPlan | None:
    stmt = select(StudyPlan).where(
        StudyPlan.id == plan_id, StudyPlan.user_id == user_id
    )
    return db.execute(stmt).scalar_one_or_none()


def create_plan(
    db: Session,
    *,
    user_id: str,
    name: str,
    destination_country: str | None,
    base_currency: str,
    start_date: date,
    duration_months: int,
    notes: str | None,
    institution_name: str | None = None,
    program_name: str | None = None,
    city: str | None = None,
    tuition_amount: Decimal | None = None,
    tuition_currency: str | None = None,
    home_currency: str | None = None,
) -> StudyPlan:
    plan = StudyPlan(
        user_id=user_id,
        name=name,
        destination_country=destination_country,
        base_currency=base_currency.upper(),
        start_date=start_date,
        duration_months=duration_months,
        end_date=end_date_for(start_date, duration_months),
        notes=notes,
        institution_name=institution_name,
        program_name=program_name,
        city=city,
        tuition_amount=tuition_amount,
        tuition_currency=tuition_currency.upper() if tuition_currency else None,
        home_currency=home_currency.upper() if home_currency else None,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def update_plan(db: Session, plan: StudyPlan, **fields: object) -> StudyPlan:
    for key, value in fields.items():
        if value is None or not hasattr(plan, key):
            continue
        setattr(plan, key, value)
    # Recompute end_date if start_date or duration_months changed.
    if "start_date" in fields or "duration_months" in fields:
        plan.end_date = end_date_for(plan.start_date, plan.duration_months)
    if "base_currency" in fields and isinstance(plan.base_currency, str):
        plan.base_currency = plan.base_currency.upper()
    # Uppercase any currency field on the way through so downstream code
    # never has to think about case.
    for ccy_field in ("tuition_currency", "home_currency"):
        cur = getattr(plan, ccy_field, None)
        if isinstance(cur, str):
            setattr(plan, ccy_field, cur.upper())
    db.commit()
    db.refresh(plan)
    return plan


def delete_plan(db: Session, plan: StudyPlan) -> None:
    db.delete(plan)
    db.commit()


__all__ = [
    "end_date_for",
    "list_plans",
    "get_plan",
    "create_plan",
    "update_plan",
    "delete_plan",
]

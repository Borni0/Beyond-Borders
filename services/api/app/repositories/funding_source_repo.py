"""Repository for funding sources. Always scope by user_id via the parent plan."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.funding_source import FundingSource
from app.models.study_plan import StudyPlan


def list_sources(db: Session, plan: StudyPlan) -> Sequence[FundingSource]:
    stmt = (
        select(FundingSource)
        .where(FundingSource.plan_id == plan.id)
        .order_by(FundingSource.created_at.asc())
    )
    return db.execute(stmt).scalars().all()


def get_source(
    db: Session, plan: StudyPlan, source_id: str
) -> FundingSource | None:
    stmt = select(FundingSource).where(
        FundingSource.id == source_id, FundingSource.plan_id == plan.id
    )
    return db.execute(stmt).scalar_one_or_none()


def create_source(
    db: Session, plan: StudyPlan, **fields: object
) -> FundingSource:
    src = FundingSource(plan_id=plan.id, **fields)
    db.add(src)
    db.commit()
    db.refresh(src)
    return src


def update_source(
    db: Session, src: FundingSource, **fields: object
) -> FundingSource:
    for key, value in fields.items():
        if value is None or not hasattr(src, key):
            continue
        setattr(src, key, value)
    db.commit()
    db.refresh(src)
    return src


def delete_source(db: Session, src: FundingSource) -> None:
    db.delete(src)
    db.commit()


__all__ = [
    "list_sources",
    "get_source",
    "create_source",
    "update_source",
    "delete_source",
]

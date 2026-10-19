"""Repository for cost items. Always scope by user_id via the parent plan."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cost_item import CostItem
from app.models.study_plan import StudyPlan


def list_costs(db: Session, plan: StudyPlan) -> Sequence[CostItem]:
    stmt = (
        select(CostItem)
        .where(CostItem.plan_id == plan.id)
        .order_by(CostItem.created_at.asc())
    )
    return db.execute(stmt).scalars().all()


def get_cost(db: Session, plan: StudyPlan, cost_id: str) -> CostItem | None:
    stmt = select(CostItem).where(
        CostItem.id == cost_id, CostItem.plan_id == plan.id
    )
    return db.execute(stmt).scalar_one_or_none()


def create_cost(db: Session, plan: StudyPlan, **fields: object) -> CostItem:
    cost = CostItem(plan_id=plan.id, **fields)
    db.add(cost)
    db.commit()
    db.refresh(cost)
    return cost


def update_cost(
    db: Session, cost: CostItem, **fields: object
) -> CostItem:
    for key, value in fields.items():
        if value is None or not hasattr(cost, key):
            continue
        setattr(cost, key, value)
    db.commit()
    db.refresh(cost)
    return cost


def delete_cost(db: Session, cost: CostItem) -> None:
    db.delete(cost)
    db.commit()


__all__ = ["list_costs", "get_cost", "create_cost", "update_cost", "delete_cost"]

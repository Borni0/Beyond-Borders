"""Repository for savings goals. Always scope by user_id."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.savings_goal import SavingsGoal


def list_goals(
    db: Session, user_id: str, *, plan_id: str | None = None
) -> Sequence[SavingsGoal]:
    """List savings goals owned by a user, soonest target first."""
    stmt = select(SavingsGoal).where(SavingsGoal.user_id == user_id)
    if plan_id is not None:
        stmt = stmt.where(SavingsGoal.plan_id == plan_id)
    stmt = stmt.order_by(
        SavingsGoal.target_date.asc(), SavingsGoal.created_at.asc()
    )
    return db.execute(stmt).scalars().all()


def get_goal(
    db: Session, user_id: str, goal_id: str
) -> SavingsGoal | None:
    stmt = select(SavingsGoal).where(
        SavingsGoal.id == goal_id, SavingsGoal.user_id == user_id
    )
    return db.execute(stmt).scalar_one_or_none()


def create_goal(
    db: Session, *, user_id: str, **fields: object
) -> SavingsGoal:
    goal = SavingsGoal(user_id=user_id, **fields)
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def update_goal(
    db: Session, goal: SavingsGoal, **fields: object
) -> SavingsGoal:
    for key, value in fields.items():
        if value is None or not hasattr(goal, key):
            continue
        setattr(goal, key, value)
    db.commit()
    db.refresh(goal)
    return goal


def delete_goal(db: Session, goal: SavingsGoal) -> None:
    db.delete(goal)
    db.commit()


__all__ = [
    "create_goal",
    "delete_goal",
    "get_goal",
    "list_goals",
    "update_goal",
]

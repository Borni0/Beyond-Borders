"""Savings-goal CRUD routes.

User-scoped, like payments. Pass ``plan_id`` in the payload to link the
goal to a study plan.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, DbSessionDep
from app.core.errors import ApiError
from app.repositories import savings_goal_repo
from app.schemas.savings_goal import (
    SavingsGoalCreate,
    SavingsGoalPublic,
    SavingsGoalUpdate,
)

router = APIRouter(prefix="/savings-goals", tags=["savings"])


def _to_public(goal) -> SavingsGoalPublic:  # type: ignore[no-untyped-def]
    return SavingsGoalPublic(
        id=goal.id,
        user_id=goal.user_id,
        plan_id=goal.plan_id,
        name=goal.name,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        currency=goal.currency,
        target_date=goal.target_date,
        notes=goal.notes,
        created_at=goal.created_at.isoformat(),
        updated_at=goal.updated_at.isoformat(),
    )


@router.get("", response_model=list[SavingsGoalPublic])
def list_user_savings_goals(
    db: DbSessionDep,
    current_user: CurrentUser,
    plan_id: Optional[str] = Query(default=None),
) -> list[SavingsGoalPublic]:
    goals = savings_goal_repo.list_goals(db, current_user.id, plan_id=plan_id)
    return [_to_public(g) for g in goals]


@router.post(
    "",
    response_model=SavingsGoalPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_user_savings_goal(
    payload: SavingsGoalCreate,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> SavingsGoalPublic:
    goal = savings_goal_repo.create_goal(
        db, user_id=current_user.id, **payload.model_dump()
    )
    return _to_public(goal)


@router.patch("/{goal_id}", response_model=SavingsGoalPublic)
def update_user_savings_goal(
    goal_id: str,
    payload: SavingsGoalUpdate,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> SavingsGoalPublic:
    goal = savings_goal_repo.get_goal(db, current_user.id, goal_id)
    if goal is None:
        raise ApiError("NOT_FOUND", "Savings goal not found.", http_status=404)
    cleaned = {k: v for k, v in payload.model_dump().items() if v is not None}
    goal = savings_goal_repo.update_goal(db, goal, **cleaned)
    return _to_public(goal)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_savings_goal(
    goal_id: str,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> None:
    goal = savings_goal_repo.get_goal(db, current_user.id, goal_id)
    if goal is None:
        raise ApiError("NOT_FOUND", "Savings goal not found.", http_status=404)
    savings_goal_repo.delete_goal(db, goal)


__all__ = ["router"]
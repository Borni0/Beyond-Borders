"""Readiness endpoint: returns the computed ReadinessResult for a plan."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DbSessionDep
from app.core.errors import ApiError
from app.repositories import study_plan_repo
from app.services import readiness_service

router = APIRouter(prefix="/plans/{plan_id}/readiness", tags=["readiness"])


@router.get("")
def get_plan_readiness(
    plan_id: str,
    db: DbSessionDep,
    current_user: CurrentUser,
    upfront_window_days: int = Query(30, ge=1, le=365),
):
    plan = study_plan_repo.get_plan(db, current_user.id, plan_id)
    if plan is None:
        raise ApiError("NOT_FOUND", "Plan not found.", http_status=404)
    result = readiness_service.compute_for_plan(
        db,
        user_id=current_user.id,
        plan=plan,
        upfront_window_days=upfront_window_days,
    )
    # Return the byte-stable dict directly; the frontend treats this as
    # the canonical snapshot.
    return result.to_dict()


__all__ = ["router"]

"""Study plan CRUD routes."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, DbSessionDep
from app.core.errors import ApiError
from app.repositories import study_plan_repo
from app.schemas.study_plan import (
    StudyPlanCreate,
    StudyPlanPublic,
    StudyPlanUpdate,
)

router = APIRouter(prefix="/study-plans", tags=["study-plans"])


def _to_public(plan) -> StudyPlanPublic:  # type: ignore[no-untyped-def]
    return StudyPlanPublic(
        id=plan.id,
        name=plan.name,
        destination_country=plan.destination_country,
        base_currency=plan.base_currency,
        start_date=plan.start_date,
        duration_months=plan.duration_months,
        end_date=plan.end_date,
        notes=plan.notes,
        institution_name=plan.institution_name,
        program_name=plan.program_name,
        city=plan.city,
        tuition_amount=plan.tuition_amount,
        tuition_currency=plan.tuition_currency,
        home_currency=plan.home_currency,
        created_at=plan.created_at.isoformat(),
        updated_at=plan.updated_at.isoformat(),
    )


@router.get("", response_model=list[StudyPlanPublic])
def list_my_plans(
    db: DbSessionDep, current_user: CurrentUser
) -> list[StudyPlanPublic]:
    return [_to_public(p) for p in study_plan_repo.list_plans(db, current_user.id)]


@router.post(
    "",
    response_model=StudyPlanPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_my_plan(
    payload: StudyPlanCreate,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> StudyPlanPublic:
    plan = study_plan_repo.create_plan(
        db,
        user_id=current_user.id,
        name=payload.name,
        destination_country=payload.destination_country,
        base_currency=payload.base_currency,
        start_date=payload.start_date,
        duration_months=payload.duration_months,
        notes=payload.notes,
        institution_name=payload.institution_name,
        program_name=payload.program_name,
        city=payload.city,
        tuition_amount=payload.tuition_amount,
        tuition_currency=payload.tuition_currency,
        home_currency=payload.home_currency,
    )
    return _to_public(plan)


@router.get("/{plan_id}", response_model=StudyPlanPublic)
def get_my_plan(
    plan_id: str,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> StudyPlanPublic:
    plan = study_plan_repo.get_plan(db, current_user.id, plan_id)
    if plan is None:
        raise ApiError("NOT_FOUND", "Plan not found.", http_status=404)
    return _to_public(plan)


@router.patch("/{plan_id}", response_model=StudyPlanPublic)
def update_my_plan(
    plan_id: str,
    payload: StudyPlanUpdate,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> StudyPlanPublic:
    plan = study_plan_repo.get_plan(db, current_user.id, plan_id)
    if plan is None:
        raise ApiError("NOT_FOUND", "Plan not found.", http_status=404)
    plan = study_plan_repo.update_plan(
        db, plan, **{k: v for k, v in payload.model_dump().items() if v is not None}
    )
    return _to_public(plan)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_plan(
    plan_id: str,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> None:
    plan = study_plan_repo.get_plan(db, current_user.id, plan_id)
    if plan is None:
        raise ApiError("NOT_FOUND", "Plan not found.", http_status=404)
    study_plan_repo.delete_plan(db, plan)


__all__ = ["router"]

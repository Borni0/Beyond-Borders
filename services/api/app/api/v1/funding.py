"""Funding source CRUD routes nested under a plan."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, DbSessionDep
from app.core.errors import ApiError
from app.repositories import funding_source_repo, study_plan_repo
from app.schemas.funding_source import (
    FundingSourceCreate,
    FundingSourcePublic,
    FundingSourceUpdate,
)

router = APIRouter(prefix="/plans/{plan_id}/funding", tags=["funding"])


def _to_public(src) -> FundingSourcePublic:  # type: ignore[no-untyped-def]
    return FundingSourcePublic(
        id=src.id,
        plan_id=src.plan_id,
        name=src.name or "",
        funding_type=src.funding_type,  # type: ignore[arg-type]
        amount=src.amount,
        currency=src.currency,
        status=src.status,  # type: ignore[arg-type]
        expected_date=src.expected_date,
        notes=src.notes,
        created_at=src.created_at.isoformat(),
        updated_at=src.updated_at.isoformat(),
    )


def _load_plan_or_404(db, user_id, plan_id):  # type: ignore[no-untyped-def]
    plan = study_plan_repo.get_plan(db, user_id, plan_id)
    if plan is None:
        raise ApiError("NOT_FOUND", "Plan not found.", http_status=404)
    return plan


@router.get("", response_model=list[FundingSourcePublic])
def list_plan_funding(
    plan_id: str, db: DbSessionDep, current_user: CurrentUser
) -> list[FundingSourcePublic]:
    plan = _load_plan_or_404(db, current_user.id, plan_id)
    return [_to_public(s) for s in funding_source_repo.list_sources(db, plan)]


@router.post(
    "",
    response_model=FundingSourcePublic,
    status_code=status.HTTP_201_CREATED,
)
def create_plan_funding(
    plan_id: str,
    payload: FundingSourceCreate,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> FundingSourcePublic:
    plan = _load_plan_or_404(db, current_user.id, plan_id)
    src = funding_source_repo.create_source(db, plan, **payload.model_dump())
    return _to_public(src)


@router.patch("/{source_id}", response_model=FundingSourcePublic)
def update_plan_funding(
    plan_id: str,
    source_id: str,
    payload: FundingSourceUpdate,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> FundingSourcePublic:
    plan = _load_plan_or_404(db, current_user.id, plan_id)
    src = funding_source_repo.get_source(db, plan, source_id)
    if src is None:
        raise ApiError("NOT_FOUND", "Funding source not found.", http_status=404)
    src = funding_source_repo.update_source(
        db, src, **{k: v for k, v in payload.model_dump().items() if v is not None}
    )
    return _to_public(src)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan_funding(
    plan_id: str,
    source_id: str,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> None:
    plan = _load_plan_or_404(db, current_user.id, plan_id)
    src = funding_source_repo.get_source(db, plan, source_id)
    if src is None:
        raise ApiError("NOT_FOUND", "Funding source not found.", http_status=404)
    funding_source_repo.delete_source(db, src)


__all__ = ["router"]

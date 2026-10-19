"""Cost item CRUD routes nested under a plan."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, DbSessionDep
from app.core.errors import ApiError
from app.repositories import cost_item_repo, study_plan_repo
from app.schemas.cost_item import CostItemCreate, CostItemPublic, CostItemUpdate

router = APIRouter(prefix="/plans/{plan_id}/costs", tags=["costs"])


def _to_public(item) -> CostItemPublic:  # type: ignore[no-untyped-def]
    return CostItemPublic(
        id=item.id,
        plan_id=item.plan_id,
        category=item.category,  # type: ignore[arg-type]
        description=item.description or "",
        amount=item.amount,
        currency=item.currency,
        frequency=item.frequency,  # type: ignore[arg-type]
        start_date=item.start_date,
        end_date=item.end_date,
        is_one_time=bool(item.is_one_time),
        is_refundable=bool(item.is_refundable),
        due_before_departure=bool(getattr(item, "due_before_departure", False)),
        source_id=item.source_id,
        created_at=item.created_at.isoformat(),
        updated_at=item.updated_at.isoformat(),
    )


def _load_plan_or_404(db, user_id, plan_id):  # type: ignore[no-untyped-def]
    plan = study_plan_repo.get_plan(db, user_id, plan_id)
    if plan is None:
        raise ApiError("NOT_FOUND", "Plan not found.", http_status=404)
    return plan


@router.get("", response_model=list[CostItemPublic])
def list_plan_costs(
    plan_id: str, db: DbSessionDep, current_user: CurrentUser
) -> list[CostItemPublic]:
    plan = _load_plan_or_404(db, current_user.id, plan_id)
    return [_to_public(c) for c in cost_item_repo.list_costs(db, plan)]


@router.post(
    "",
    response_model=CostItemPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_plan_cost(
    plan_id: str,
    payload: CostItemCreate,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> CostItemPublic:
    plan = _load_plan_or_404(db, current_user.id, plan_id)
    fields = payload.model_dump()
    cost = cost_item_repo.create_cost(db, plan, **fields)
    return _to_public(cost)


@router.patch("/{cost_id}", response_model=CostItemPublic)
def update_plan_cost(
    plan_id: str,
    cost_id: str,
    payload: CostItemUpdate,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> CostItemPublic:
    plan = _load_plan_or_404(db, current_user.id, plan_id)
    cost = cost_item_repo.get_cost(db, plan, cost_id)
    if cost is None:
        raise ApiError("NOT_FOUND", "Cost not found.", http_status=404)
    cost = cost_item_repo.update_cost(
        db, cost, **{k: v for k, v in payload.model_dump().items() if v is not None}
    )
    return _to_public(cost)


@router.delete("/{cost_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan_cost(
    plan_id: str,
    cost_id: str,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> None:
    plan = _load_plan_or_404(db, current_user.id, plan_id)
    cost = cost_item_repo.get_cost(db, plan, cost_id)
    if cost is None:
        raise ApiError("NOT_FOUND", "Cost not found.", http_status=404)
    cost_item_repo.delete_cost(db, cost)


__all__ = ["router"]

"""Payment-event CRUD routes.

Endpoints are user-scoped (no plan nesting) so that "before-a-plan" payments
like an application or visa fee can be tracked. Pass ``plan_id`` in the
payload to link the event to a study plan.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, DbSessionDep
from app.core.errors import ApiError
from app.repositories import payment_event_repo
from app.schemas.payment_event import (
    PaymentEventCreate,
    PaymentEventPublic,
    PaymentEventUpdate,
)
from app.services.funding_plan_service import (
    TimelineEntry,
    derive_display_status,
)

router = APIRouter(prefix="/payments", tags=["payments"])


def _to_public(entry: TimelineEntry | object) -> PaymentEventPublic:
    """Build the public response from a timeline entry.

    Timeline entries already have the derived `display_status`, but the
    stored row's `display_status` should match what the engine returned.
    """
    if isinstance(entry, TimelineEntry):
        return PaymentEventPublic(
            id=entry.event_id,
            user_id="",
            plan_id=entry.plan_id,
            title=entry.title,
            category=entry.category,  # type: ignore[arg-type]
            amount=entry.amount,
            currency=entry.currency,
            due_date=entry.due_date,
            display_status=entry.display_status,  # type: ignore[arg-type]
            notes=None,
            is_recurring=entry.is_recurring,
            recurrence_frequency=None,
            recurrence_end_date=None,
            created_at="",
            updated_at="",
        )

    # Fall back to the raw ORM row.
    return _from_orm(entry)  # type: ignore[arg-type]


def _from_orm(event) -> PaymentEventPublic:  # type: ignore[no-untyped-def]
    today = date.today()
    return PaymentEventPublic(
        id=event.id,
        user_id=event.user_id,
        plan_id=event.plan_id,
        title=event.title,
        category=event.category,  # type: ignore[arg-type]
        amount=event.amount,
        currency=event.currency,
        due_date=event.due_date,
        display_status=derive_display_status(  # type: ignore[arg-type]
            event.status, event.due_date, today
        ),
        notes=event.notes,
        is_recurring=bool(event.is_recurring),
        recurrence_frequency=event.recurrence_frequency,  # type: ignore[arg-type]
        recurrence_end_date=event.recurrence_end_date,
        created_at=event.created_at.isoformat(),
        updated_at=event.updated_at.isoformat(),
    )


@router.get("", response_model=list[PaymentEventPublic])
def list_user_payments(
    db: DbSessionDep,
    current_user: CurrentUser,
    plan_id: Optional[str] = Query(default=None),
) -> list[PaymentEventPublic]:
    events = payment_event_repo.list_events(db, current_user.id, plan_id=plan_id)
    return [_from_orm(e) for e in events]


@router.post(
    "",
    response_model=PaymentEventPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_user_payment(
    payload: PaymentEventCreate,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> PaymentEventPublic:
    fields = payload.model_dump()
    event = payment_event_repo.create_event(db, user_id=current_user.id, **fields)
    return _from_orm(event)


@router.patch("/{event_id}", response_model=PaymentEventPublic)
def update_user_payment(
    event_id: str,
    payload: PaymentEventUpdate,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> PaymentEventPublic:
    event = payment_event_repo.get_event(db, current_user.id, event_id)
    if event is None:
        raise ApiError("NOT_FOUND", "Payment event not found.", http_status=404)
    cleaned = {k: v for k, v in payload.model_dump().items() if v is not None}
    event = payment_event_repo.update_event(db, event, **cleaned)
    return _from_orm(event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_payment(
    event_id: str,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> None:
    event = payment_event_repo.get_event(db, current_user.id, event_id)
    if event is None:
        raise ApiError("NOT_FOUND", "Payment event not found.", http_status=404)
    payment_event_repo.delete_event(db, event)


__all__ = ["router"]
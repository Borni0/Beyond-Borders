"""Repository for payment events. Always scope by user_id."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payment_event import PaymentEvent


def list_events(
    db: Session, user_id: str, *, plan_id: str | None = None
) -> Sequence[PaymentEvent]:
    """List all payment events owned by a user, oldest first.

    Pass ``plan_id`` to restrict to a single plan; pass ``None`` to include
    every event the user owns regardless of plan link.
    """
    stmt = select(PaymentEvent).where(PaymentEvent.user_id == user_id)
    if plan_id is not None:
        stmt = stmt.where(PaymentEvent.plan_id == plan_id)
    stmt = stmt.order_by(PaymentEvent.due_date.asc(), PaymentEvent.created_at.asc())
    return db.execute(stmt).scalars().all()


def get_event(
    db: Session, user_id: str, event_id: str
) -> PaymentEvent | None:
    stmt = select(PaymentEvent).where(
        PaymentEvent.id == event_id, PaymentEvent.user_id == user_id
    )
    return db.execute(stmt).scalar_one_or_none()


def create_event(
    db: Session, *, user_id: str, **fields: object
) -> PaymentEvent:
    event = PaymentEvent(user_id=user_id, **fields)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def update_event(
    db: Session, event: PaymentEvent, **fields: object
) -> PaymentEvent:
    for key, value in fields.items():
        if value is None or not hasattr(event, key):
            continue
        setattr(event, key, value)
    db.commit()
    db.refresh(event)
    return event


def delete_event(db: Session, event: PaymentEvent) -> None:
    db.delete(event)
    db.commit()


__all__ = [
    "create_event",
    "delete_event",
    "get_event",
    "list_events",
    "update_event",
]

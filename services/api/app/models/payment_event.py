"""Payment event ORM model.

A payment event is a specific future (or past) bill the student expects
to pay: a deposit, a tuition installment, a rent charge, a flight, a
visa fee, etc. It carries:

  - a due date (used by the timeline and "overdue" logic)
  - an amount + currency (converted to base in the service layer)
  - a status (planned, scheduled, paid, overdue, cancelled)
  - optional recurrence (e.g. monthly rent) to roll forward into the
    future as paid instances are checked off
  - optional link to a study plan, so a payment can be the "executed"
    counterpart of a CostItem in the readiness model

"Overdue" is a *display* state. The DB stores the user's chosen status
verbatim; the service layer treats any non-paid, non-cancelled payment
with a past due_date as overdue at read time.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class PaymentEvent(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "payment_events"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional link to the originating study plan. Nullable because the
    # spec allows unlinked payments (e.g. a one-off application fee
    # before a plan is finalized).
    plan_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("study_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # Display category; see PaymentCategory in app.schemas.payment_event
    # for the allowed values.
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # planned | scheduled | paid | overdue | cancelled
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="planned")

    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # Recurrence: if is_recurring is True, the service layer generates
    # future instances on the read path (capped at one year ahead so
    # the timeline stays finite).
    is_recurring: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    # monthly | quarterly | semester | annual — same vocabulary as costs.
    recurrence_frequency: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )
    recurrence_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)


__all__ = ["PaymentEvent"]

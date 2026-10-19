"""Cost item ORM model.

Each cost belongs to a study plan. Money is stored as a DECIMAL in the
cost's own currency; conversion to base currency happens in the calculation
engine.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class CostItem(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "cost_items"

    plan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("study_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Category / frequency are stored as the enum `.value` string for forward
    # compatibility (adding a new value is just a code change, no migration).
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    frequency: Mapped[str] = mapped_column(String(16), nullable=False)

    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    is_one_time: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Refundable deposits: tracked in their own bucket and never netted into
    # the projected cost.
    is_refundable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Marked when the user is sure this cost must be paid before
    # `plan.start_date` (e.g. an upfront deposit that the user wants the
    # upfront-cash projection to surface, even if the item's
    # start_date is unset). The engine treats it as in-window regardless.
    due_before_departure: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Optional link to a data source so users can prove where a cost came
    # from. Nullable: most user-typed costs have no source.
    source_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    plan = relationship("StudyPlan", back_populates="cost_items")


__all__ = ["CostItem"]

"""Savings goal ORM model.

A savings goal tracks a target amount, currency, and date by which the
student wants to have that much saved. The service layer computes
remaining amount and the per-period contribution target.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class SavingsGoal(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "savings_goals"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    plan_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("study_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)


__all__ = ["SavingsGoal"]

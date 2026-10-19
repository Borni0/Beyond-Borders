"""Expense ORM model (spec §3.6 — Spending Tracker).

A logged spend event. Optional link to a study plan, but most rows are
user-wide (the user wants to see their monthly burn regardless of
which plan they're on at the moment).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class Expense(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "expenses"

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
    # Same vocabulary as cost_items / payment_events.
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(
        String(500), nullable=False, default=""
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    spent_on: Mapped[date] = mapped_column(Date, nullable=False)
    payment_method: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)


__all__ = ["Expense"]
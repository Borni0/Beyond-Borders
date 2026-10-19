"""Funding source ORM model.

Each funding source belongs to a study plan. Status drives the readiness
classification (only CONFIRMED reduces the funding gap).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class FundingSource(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "funding_sources"

    plan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("study_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    funding_type: Mapped[str] = mapped_column(String(16), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)

    # Date the funding is expected to land; if null and status is CONFIRMED,
    # the source is treated as available immediately. For EXPECTED, this
    # drives available_before_departure.
    expected_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    plan = relationship("StudyPlan", back_populates="funding_sources")


__all__ = ["FundingSource"]

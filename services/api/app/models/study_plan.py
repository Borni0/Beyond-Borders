"""Study plan ORM model.

A study plan is a single self-contained financial scenario: a destination
(start date, duration, base currency) that owns its costs and funding
sources. Users can create multiple plans (e.g. "MSc in Berlin",
"MBA in London") and switch between them.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class StudyPlan(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "study_plans"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Free-form display name shown in the plan picker.
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Destination country (ISO 3166-1 alpha-2) — used for currency hints
    # and the visual chip; nullable in Phase 1 because not all users
    # set it on day one.
    destination_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    # The currency everything is reported in for this plan.
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    duration_months: Mapped[int] = mapped_column(Integer, nullable=False)

    # Computed at write-time for fast sort/filter; kept as a column so
    # indexes work. (Always == start_date + duration_months, end-exclusive.)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Optional narrative the user types in the "About this plan" box.
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # ---- Financial-readiness enrichment (Phase 1 extension) ----
    # The destination university / school. Optional — most plans only fill
    # this in once they've been accepted, but the field is on the plan
    # form from day one.
    institution_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # The degree / course the user is enrolling in.
    program_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Destination city. Separate from `destination_country` because the
    # currency display and the visa info usually need both.
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # First-year tuition the user wants the engine to assume. Quoted in
    # `tuition_currency` (which may differ from `base_currency`); the
    # engine still has to convert it.
    tuition_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    tuition_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    # The currency the user is paying from (their home bank account),
    # separate from `base_currency` (the currency the plan reports in).
    home_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)

    # Convenience reverse refs so the ORM can navigate from a plan to its
    # children without a manual query.
    cost_items = relationship(
        "CostItem",
        back_populates="plan",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    funding_sources = relationship(
        "FundingSource",
        back_populates="plan",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


__all__ = ["StudyPlan"]

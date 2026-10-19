"""User-entered exchange rate (spec §7, §8.4).

Each rate is (base_currency, quote_currency) → rate. The engine treats
the absence of a pair as a missing input and surfaces it; the absence of
a rate between two currencies never silently falls back to 1:1.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class ExchangeRate(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "base_currency", "quote_currency",
            name="uq_exchange_rates_user_pair",
        ),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    quote_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    # reference | provider_quote | user_entered. Phase 1: only user_entered.
    rate_type: Mapped[str] = mapped_column(String(16), nullable=False, default="user_entered")
    observed_at: Mapped[date] = mapped_column(Date, nullable=False)


__all__ = ["ExchangeRate"]

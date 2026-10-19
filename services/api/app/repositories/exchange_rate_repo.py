"""Repository for user-entered exchange rates."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.exchange_rate import ExchangeRate


def list_rates(db: Session, user_id: str) -> Sequence[ExchangeRate]:
    stmt = (
        select(ExchangeRate)
        .where(ExchangeRate.user_id == user_id)
        .order_by(ExchangeRate.base_currency.asc(), ExchangeRate.quote_currency.asc())
    )
    return db.execute(stmt).scalars().all()


def get_rate(
    db: Session, user_id: str, base: str, quote: str
) -> ExchangeRate | None:
    stmt = select(ExchangeRate).where(
        ExchangeRate.user_id == user_id,
        ExchangeRate.base_currency == base.upper(),
        ExchangeRate.quote_currency == quote.upper(),
    )
    return db.execute(stmt).scalar_one_or_none()


def upsert_rate(
    db: Session,
    *,
    user_id: str,
    base_currency: str,
    quote_currency: str,
    rate: Decimal,
    rate_type: str,
    observed_at: date,
) -> ExchangeRate:
    existing = get_rate(db, user_id, base_currency, quote_currency)
    if existing:
        existing.rate = rate
        existing.rate_type = rate_type
        existing.observed_at = observed_at
        db.commit()
        db.refresh(existing)
        return existing
    row = ExchangeRate(
        user_id=user_id,
        base_currency=base_currency.upper(),
        quote_currency=quote_currency.upper(),
        rate=rate,
        rate_type=rate_type,
        observed_at=observed_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_rate(db: Session, rate: ExchangeRate) -> None:
    db.delete(rate)
    db.commit()


__all__ = [
    "list_rates",
    "get_rate",
    "upsert_rate",
    "delete_rate",
]

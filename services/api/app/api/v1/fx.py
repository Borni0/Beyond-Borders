"""Exchange rate routes (per-user)."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSessionDep
from app.core.errors import ApiError
from app.repositories import exchange_rate_repo
from app.schemas.exchange_rate import (
    ExchangeRatePublic,
    ExchangeRateUpsert,
)

router = APIRouter(prefix="/fx", tags=["fx"])


def _to_public(rate) -> ExchangeRatePublic:  # type: ignore[no-untyped-def]
    return ExchangeRatePublic(
        id=rate.id,
        base_currency=rate.base_currency,
        quote_currency=rate.quote_currency,
        rate=rate.rate,
        rate_type=rate.rate_type,  # type: ignore[arg-type]
        observed_at=rate.observed_at,
        created_at=rate.created_at.isoformat(),
        updated_at=rate.updated_at.isoformat(),
    )


@router.get("", response_model=list[ExchangeRatePublic])
def list_my_rates(
    db: DbSessionDep, current_user: CurrentUser
) -> list[ExchangeRatePublic]:
    return [
        _to_public(r) for r in exchange_rate_repo.list_rates(db, current_user.id)
    ]


@router.put("", response_model=ExchangeRatePublic)
def upsert_my_rate(
    payload: ExchangeRateUpsert,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> ExchangeRatePublic:
    rate = exchange_rate_repo.upsert_rate(
        db,
        user_id=current_user.id,
        base_currency=payload.base_currency,
        quote_currency=payload.quote_currency,
        rate=payload.rate,
        rate_type=payload.rate_type,
        observed_at=payload.observed_at,
    )
    return _to_public(rate)


@router.delete("/{rate_id}")
def delete_my_rate(
    rate_id: str,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> None:
    from app.models.exchange_rate import ExchangeRate

    rate = db.get(ExchangeRate, rate_id)
    if rate is None or rate.user_id != current_user.id:
        raise ApiError("NOT_FOUND", "Rate not found.", http_status=404)
    exchange_rate_repo.delete_rate(db, rate)


__all__ = ["router"]

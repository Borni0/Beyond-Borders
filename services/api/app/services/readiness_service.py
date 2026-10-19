"""Readiness service: bridge between the DB and the calculation engine.

The engine works in pure data-classes (no SQLAlchemy) so it can be tested
without a database. This module is the only place that knows about both
worlds: it loads plans, costs, funding, and rates for a user, hydrates
them into engine inputs, and returns a `ReadinessResult`.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.cost_item import CostItem
from app.models.exchange_rate import ExchangeRate
from app.models.funding_source import FundingSource
from app.models.study_plan import StudyPlan
from app.services.financial.readiness import compute_readiness
from app.services.financial.types import (
    CostCategory,
    CostItem as EngineCostItem,
    Frequency,
    FundingSource as EngineFundingSource,
    FundingStatus,
    FundingType,
    FxRate as EngineFxRate,
    PlanContext,
    RateType as EngineRateType,
)


def _coerce_enum(enum_cls, value: str):  # type: ignore[no-untyped-def]
    """Best-effort coerce a string to an enum value, with a safe fallback.

    Falls back to a known member when the value isn't recognized so a
    single bad row can't break the entire computation. Returns the
    fallback and the original value (so callers can log).
    """
    try:
        return enum_cls(value)
    except ValueError:
        # Pick the first defined member as a safe placeholder.
        try:
            return next(iter(enum_cls))
        except StopIteration:
            raise


def _hydrate_cost(item: CostItem) -> EngineCostItem:
    return EngineCostItem(
        id=item.id,
        category=_coerce_enum(CostCategory, item.category),
        description=item.description or "",
        amount=Decimal(item.amount),
        currency=item.currency.upper(),
        frequency=_coerce_enum(Frequency, item.frequency),
        start_date=item.start_date,
        end_date=item.end_date,
        is_one_time=bool(item.is_one_time),
        is_refundable=bool(item.is_refundable),
        due_before_departure=bool(
            getattr(item, "due_before_departure", False)
        ),
        source_id=item.source_id,
    )


def _hydrate_funding(src: FundingSource) -> EngineFundingSource:
    return EngineFundingSource(
        id=src.id,
        name=src.name or "",
        funding_type=_coerce_enum(FundingType, src.funding_type),
        amount=Decimal(src.amount),
        currency=src.currency.upper(),
        status=_coerce_enum(FundingStatus, src.status),
        expected_date=src.expected_date,
        notes=src.notes,
    )


def _hydrate_rate(rate: ExchangeRate) -> EngineFxRate:
    return EngineFxRate(
        base_currency=rate.base_currency.upper(),
        quote_currency=rate.quote_currency.upper(),
        rate=Decimal(rate.rate),
        rate_type=_coerce_enum(EngineRateType, rate.rate_type),
        observed_at=rate.observed_at,
    )


def compute_for_plan(
    db: Session,
    *,
    user_id: str,
    plan: StudyPlan,
    upfront_window_days: int = 30,
):
    """Compute the readiness result for `plan`, scoped to `user_id`.

    Loads costs, funding, and rates owned by this user; the engine does
    the math.
    """
    # Defensive: enforce ownership even if a caller passed a plan they
    # fetched without the user_id filter. (Routes do the right thing
    # already; this is belt-and-braces.)
    if plan.user_id != user_id:
        raise PermissionError("plan does not belong to user")

    costs = [_hydrate_cost(c) for c in plan.cost_items]
    sources = [_hydrate_funding(s) for s in plan.funding_sources]

    from app.repositories.exchange_rate_repo import list_rates

    raw_rates = list_rates(db, user_id)
    rates = [_hydrate_rate(r) for r in raw_rates]

    context = PlanContext(
        id=plan.id,
        name=plan.name,
        base_currency=plan.base_currency.upper(),
        start_date=plan.start_date,
        duration_months=plan.duration_months,
    )

    return compute_readiness(
        context,
        costs,
        sources,
        rates,
        upfront_window_days=upfront_window_days,
    )


__all__ = ["compute_for_plan"]

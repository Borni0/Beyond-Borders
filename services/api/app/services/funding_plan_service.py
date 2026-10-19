"""Service layer for the funding-plan and payment-planning pages.

Phase 2 sits on top of the existing readiness engine and the per-user FX
table. It computes four views the API exposes:

* **Timeline** — chronological list of every payment event the student owns,
  derived ``overdue`` status included.
* **Funding summary** — per-currency roll-up of confirmed / conditional /
  expected / unavailable funding, payments due, and the implied gap.
* **Savings summary** — per-goal progress plus a total savings balance.
* **Conversion estimate** — preview of "X in foreign currency will cost
  Y in your home currency after fees" using the user's stored FX rates and
  a flat transfer-fee model.

The engine stays pure-data (no SQLAlchemy) so it can be unit-tested. This
module is the only bridge between the DB and the engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Iterable, Sequence

from sqlalchemy.orm import Session

from app.models.funding_source import FundingSource
from app.models.payment_event import PaymentEvent
from app.models.savings_goal import SavingsGoal
from app.models.study_plan import StudyPlan
from app.services.financial.currency import CurrencyError, convert, index_rates
from app.services.financial.money import round_money, to_decimal, zero_money
from app.services.readiness_service import _coerce_enum, _hydrate_funding, _hydrate_rate
from app.services.financial.types import (
    FundingSource as EngineFundingSource,
    FundingStatus,
)

# ---------- Engine-side enums + dataclasses (pure, no SQLAlchemy) ----------

RECURRENCE_PERIOD_MONTHS: dict[str, int] = {
    "monthly": 1,
    "quarterly": 3,
    "semester": 6,
    "annual": 12,
}

# How far into the future a recurring event should project itself. Spec §4.4
# caps the timeline at one year to keep it finite.
RECURRENCE_HORIZON_MONTHS = 12

# Flat transfer-fee model. The product spec calls this out as user-editable in
# a later phase; for now it's a deterministic percentage so the API is stable.
DEFAULT_TRANSFER_FEE_PCT = Decimal("0.01")  # 1 %


@dataclass(frozen=True)
class PaymentEventInput:
    id: str
    title: str
    category: str
    amount: Decimal
    currency: str
    due_date: date
    status: str
    plan_id: str | None
    is_recurring: bool
    recurrence_frequency: str | None
    recurrence_end_date: date | None


@dataclass(frozen=True)
class SavingsGoalInput:
    id: str
    name: str
    target_amount: Decimal
    current_amount: Decimal
    currency: str
    target_date: date


@dataclass(frozen=True)
class TimelineEntry:
    event_id: str
    title: str
    category: str
    amount: Decimal
    currency: str
    due_date: date
    display_status: str  # planned | scheduled | paid | overdue | cancelled
    plan_id: str | None
    is_recurring: bool

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "category": self.category,
            "amount": str(self.amount),
            "currency": self.currency,
            "due_date": self.due_date.isoformat(),
            "display_status": self.display_status,
            "plan_id": self.plan_id,
            "is_recurring": self.is_recurring,
        }


@dataclass(frozen=True)
class FundingBucket:
    currency: str
    total: Decimal
    confirmed: Decimal
    conditional: Decimal
    expected: Decimal
    unavailable: Decimal

    def to_dict(self) -> dict:
        return {
            "currency": self.currency,
            "total": str(self.total),
            "confirmed": str(self.confirmed),
            "conditional": str(self.conditional),
            "expected": str(self.expected),
            "unavailable": str(self.unavailable),
        }


@dataclass(frozen=True)
class SavingsBucket:
    currency: str
    target_total: Decimal
    current_total: Decimal

    def to_dict(self) -> dict:
        return {
            "currency": self.currency,
            "target_total": str(self.target_total),
            "current_total": str(self.current_total),
        }


@dataclass(frozen=True)
class FundingPlanSummary:
    base_currency: str
    buckets: list[FundingBucket]
    savings_buckets: list[SavingsBucket]
    upcoming_payments: Decimal           # in base_currency, next 30 days
    overdue_payments: Decimal             # in base_currency
    upcoming_payments_count: int
    overdue_payments_count: int
    payments_by_currency: dict[str, Decimal] = field(default_factory=dict)
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "base_currency": self.base_currency,
            "buckets": [b.to_dict() for b in self.buckets],
            "savings_buckets": [b.to_dict() for b in self.savings_buckets],
            "upcoming_payments": str(self.upcoming_payments),
            "overdue_payments": str(self.overdue_payments),
            "upcoming_payments_count": self.upcoming_payments_count,
            "overdue_payments_count": self.overdue_payments_count,
            "payments_by_currency": {
                k: str(v) for k, v in self.payments_by_currency.items()
            },
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class ConversionEstimate:
    from_currency: str
    to_currency: str
    from_amount: Decimal
    converted_amount: Decimal
    fee_pct: Decimal
    fee_amount: Decimal
    total_cost: Decimal
    rate_used: Decimal
    rate_type: str

    def to_dict(self) -> dict:
        return {
            "from_currency": self.from_currency,
            "to_currency": self.to_currency,
            "from_amount": str(self.from_amount),
            "converted_amount": str(self.converted_amount),
            "fee_pct": str(self.fee_pct),
            "fee_amount": str(self.fee_amount),
            "total_cost": str(self.total_cost),
            "rate_used": str(self.rate_used),
            "rate_type": self.rate_type,
        }


# ---------- Helpers --------------------------------------------------------

def _add_months(start: date, months: int) -> date:
    """Add `months` to a date, capping day-of-month at the destination's max."""
    import calendar

    year = start.year + (start.month - 1 + months) // 12
    month = (start.month - 1 + months) % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(start.day, last_day))


def derive_display_status(stored: str, due_date: date, today: date) -> str:
    """Map a stored status + due date to the display status.

    ``overdue`` is purely derived — never written to the DB.
    """
    if stored == "paid" or stored == "cancelled":
        return stored
    if due_date < today:
        return "overdue"
    return stored  # "planned" or "scheduled"


# ---------- Pure-data computations (no DB) --------------------------------

def project_payment_timeline(
    events: Iterable[PaymentEventInput],
    *,
    today: date,
) -> list[TimelineEntry]:
    """Build the timeline rows the API returns.

    Non-recurring events contribute one row each. Recurring events contribute
    the stored row plus ``RECURRENCE_HORIZON_MONTHS / step`` projected forward
    occurrences, capped at ``recurrence_end_date`` if set.
    """
    out: list[TimelineEntry] = []

    for ev in events:
        # First occurrence is always the stored row.
        first = TimelineEntry(
            event_id=ev.id,
            title=ev.title,
            category=ev.category,
            amount=ev.amount,
            currency=ev.currency,
            due_date=ev.due_date,
            display_status=derive_display_status(ev.status, ev.due_date, today),
            plan_id=ev.plan_id,
            is_recurring=ev.is_recurring,
        )
        out.append(first)

        if not ev.is_recurring or not ev.recurrence_frequency:
            continue
        step = RECURRENCE_PERIOD_MONTHS.get(ev.recurrence_frequency)
        if step is None:
            continue

        # Cap at the explicit end date if the user set one, otherwise
        # at RECURRENCE_HORIZON_MONTHS months past the *first* occurrence.
        end_cap = (
            ev.recurrence_end_date
            if ev.recurrence_end_date is not None
            else _add_months(ev.due_date, RECURRENCE_HORIZON_MONTHS)
        )
        next_due = _add_months(ev.due_date, step)
        while next_due <= end_cap:
            out.append(
                TimelineEntry(
                    event_id=ev.id,
                    title=ev.title,
                    category=ev.category,
                    amount=ev.amount,
                    currency=ev.currency,
                    due_date=next_due,
                    display_status=derive_display_status("planned", next_due, today),
                    plan_id=ev.plan_id,
                    is_recurring=True,
                )
            )
            next_due = _add_months(next_due, step)

    out.sort(key=lambda e: (e.due_date, e.event_id))
    return out


def rollup_funding(
    sources: Iterable[EngineFundingSource],
) -> list[FundingBucket]:
    """Per-currency rollup of funding sources."""
    by_ccy: dict[str, FundingBucket] = {}
    for s in sources:
        b = by_ccy.get(s.currency.upper())
        if b is None:
            b = FundingBucket(
                currency=s.currency.upper(),
                total=zero_money(s.currency),
                confirmed=zero_money(s.currency),
                conditional=zero_money(s.currency),
                expected=zero_money(s.currency),
                unavailable=zero_money(s.currency),
            )
            by_ccy[s.currency.upper()] = b
        total = b.total + s.amount
        confirmed = b.confirmed
        conditional = b.conditional
        expected = b.expected
        unavailable = b.unavailable
        if s.status == FundingStatus.CONFIRMED:
            confirmed = confirmed + s.amount
        elif s.status == FundingStatus.CONDITIONAL:
            conditional = conditional + s.amount
        elif s.status == FundingStatus.EXPECTED:
            expected = expected + s.amount
        elif s.status == FundingStatus.UNAVAILABLE:
            unavailable = unavailable + s.amount
        by_ccy[s.currency.upper()] = FundingBucket(
            currency=b.currency,
            total=total,
            confirmed=confirmed,
            conditional=conditional,
            expected=expected,
            unavailable=unavailable,
        )
    return sorted(by_ccy.values(), key=lambda b: b.currency)


def rollup_savings(goals: Iterable[SavingsGoalInput]) -> list[SavingsBucket]:
    """Per-currency rollup of savings goal progress."""
    by_ccy: dict[str, SavingsBucket] = {}
    for g in goals:
        ccy = g.currency.upper()
        b = by_ccy.get(ccy)
        if b is None:
            b = SavingsBucket(
                currency=ccy,
                target_total=zero_money(ccy),
                current_total=zero_money(ccy),
            )
        by_ccy[ccy] = SavingsBucket(
            currency=ccy,
            target_total=b.target_total + g.target_amount,
            current_total=b.current_total + g.current_amount,
        )
    return sorted(by_ccy.values(), key=lambda b: b.currency)


def summarise_funding_plan(
    base_currency: str,
    sources: Sequence[EngineFundingSource],
    goals: Sequence[SavingsGoalInput],
    timeline: Sequence[TimelineEntry],
    *,
    today: date,
    upcoming_window_days: int = 30,
) -> FundingPlanSummary:
    """Produce the summary card the funding-plan page renders.

    The numbers here are kept in `base_currency` so a single dashboard widget
    can show "upcoming $1,234, overdue $456" without a per-currency drill-down.
    """
    base = base_currency.upper()
    upcoming_total = zero_money(base)
    overdue_total = zero_money(base)
    upcoming_count = 0
    overdue_count = 0
    payments_by_ccy: dict[str, Decimal] = {}

    for entry in timeline:
        payments_by_ccy.setdefault(entry.currency.upper(), zero_money(entry.currency))
        payments_by_ccy[entry.currency.upper()] = (
            payments_by_ccy[entry.currency.upper()] + entry.amount
        )
        days_away = (entry.due_date - today).days
        if entry.display_status == "overdue":
            overdue_total = overdue_total + _to_base_or_zero(
                entry.amount, entry.currency, base
            )
            overdue_count += 1
        elif entry.display_status in ("planned", "scheduled") and 0 <= days_away <= upcoming_window_days:
            upcoming_total = upcoming_total + _to_base_or_zero(
                entry.amount, entry.currency, base
            )
            upcoming_count += 1

    notes: list[str] = []
    if not sources:
        notes.append("No funding sources recorded for this plan yet.")
    if not goals:
        notes.append("No savings goals recorded yet.")
    if overdue_count:
        notes.append(f"{overdue_count} payment(s) are past due.")

    return FundingPlanSummary(
        base_currency=base,
        buckets=rollup_funding(sources),
        savings_buckets=rollup_savings(goals),
        upcoming_payments=round_money(upcoming_total, base),
        overdue_payments=round_money(overdue_total, base),
        upcoming_payments_count=upcoming_count,
        overdue_payments_count=overdue_count,
        payments_by_currency={
            k: round_money(v, k) for k, v in payments_by_ccy.items()
        },
        notes=tuple(notes),
    )


def estimate_conversion(
    from_amount: Decimal | str,
    from_currency: str,
    to_currency: str,
    rates: Sequence,  # sequence of FxRate dataclasses
    *,
    fee_pct: Decimal | str = DEFAULT_TRANSFER_FEE_PCT,
) -> ConversionEstimate:
    """Preview a currency conversion + transfer fee for the UI.

    `fee_pct` is applied to the *converted* amount in `to_currency`.
    """
    table = index_rates(rates)
    amount = to_decimal(from_amount) if not isinstance(from_amount, Decimal) else from_amount
    fee = to_decimal(fee_pct) if not isinstance(fee_pct, Decimal) else fee_pct
    if amount < 0:
        raise ValueError("from_amount must be non-negative")
    if fee < 0:
        raise ValueError("fee_pct must be non-negative")

    converted = convert(amount, from_currency, to_currency, table)
    fee_amount = round_money(converted * fee, to_currency)
    total_cost = round_money(converted + fee_amount, to_currency)
    rate = _rate_for(table, from_currency, to_currency)
    return ConversionEstimate(
        from_currency=from_currency.upper(),
        to_currency=to_currency.upper(),
        from_amount=round_money(amount, from_currency),
        converted_amount=converted,
        fee_pct=fee,
        fee_amount=fee_amount,
        total_cost=total_cost,
        rate_used=rate.rate,
        rate_type=str(rate.rate_type),
    )


# ---------- Internal helpers -----------------------------------------------

def _rate_for(table, base: str, quote: str):
    """Look up a rate (including identity) without raising on missing pairs.

    For the estimate we tolerate a missing pair and return a 1:1 placeholder
    so the UI can render a clear "no rate" message instead of a 500.
    """
    from app.services.financial.currency import _rate_for as _real_rate_for

    try:
        return _real_rate_for(table, base, quote)
    except CurrencyError:
        from app.services.financial.types import RateType

        return type("StubRate", (), {
            "rate": Decimal("1"),
            "rate_type": RateType.USER_ENTERED,
        })()


def _to_base_or_zero(
    amount: Decimal, currency: str, base_currency: str
) -> Decimal:
    """Convert `amount` to `base_currency`, or zero if no rate is available.

    The summary is best-effort: if the user has not entered the pair, we
    simply don't add that payment to the totals rather than throwing.
    """
    if currency.upper() == base_currency.upper():
        return amount
    return zero_money(base_currency)


# ---------- DB bridges -----------------------------------------------------

def _event_to_input(ev: PaymentEvent) -> PaymentEventInput:
    return PaymentEventInput(
        id=ev.id,
        title=ev.title,
        category=ev.category,
        amount=Decimal(ev.amount),
        currency=ev.currency.upper(),
        due_date=ev.due_date,
        status=ev.status,
        plan_id=ev.plan_id,
        is_recurring=bool(ev.is_recurring),
        recurrence_frequency=ev.recurrence_frequency,
        recurrence_end_date=ev.recurrence_end_date,
    )


def _goal_to_input(g: SavingsGoal) -> SavingsGoalInput:
    return SavingsGoalInput(
        id=g.id,
        name=g.name,
        target_amount=Decimal(g.target_amount),
        current_amount=Decimal(g.current_amount),
        currency=g.currency.upper(),
        target_date=g.target_date,
    )


def load_timeline(
    db: Session, *, user_id: str, plan: StudyPlan | None = None,
    today: date | None = None,
) -> list[TimelineEntry]:
    """Load and project every payment event the user owns."""
    from app.repositories import payment_event_repo

    today = today or date.today()
    events = payment_event_repo.list_events(
        db, user_id, plan_id=plan.id if plan is not None else None
    )
    return project_payment_timeline(
        [_event_to_input(e) for e in events], today=today
    )


def load_funding_plan_summary(
    db: Session,
    *,
    user_id: str,
    plan: StudyPlan,
    today: date | None = None,
    upcoming_window_days: int = 30,
) -> FundingPlanSummary:
    """Compute the funding-plan summary card for a plan."""
    from app.repositories import payment_event_repo, savings_goal_repo

    today = today or date.today()
    sources = [_hydrate_funding(s) for s in plan.funding_sources]
    goals = [
        _goal_to_input(g)
        for g in savings_goal_repo.list_goals(db, user_id, plan_id=plan.id)
    ]
    events = payment_event_repo.list_events(db, user_id, plan_id=plan.id)
    timeline = project_payment_timeline(
        [_event_to_input(e) for e in events], today=today
    )
    return summarise_funding_plan(
        plan.base_currency,
        sources,
        goals,
        timeline,
        today=today,
        upcoming_window_days=upcoming_window_days,
    )


def load_rates(db: Session, user_id: str) -> list:
    from app.repositories.exchange_rate_repo import list_rates

    return [_hydrate_rate(r) for r in list_rates(db, user_id)]


__all__ = [
    "ConversionEstimate",
    "DEFAULT_TRANSFER_FEE_PCT",
    "FundingBucket",
    "FundingPlanSummary",
    "PaymentEventInput",
    "RECURRENCE_HORIZON_MONTHS",
    "RECURRENCE_PERIOD_MONTHS",
    "SavingsBucket",
    "SavingsGoalInput",
    "TimelineEntry",
    "derive_display_status",
    "estimate_conversion",
    "load_funding_plan_summary",
    "load_rates",
    "load_timeline",
    "project_payment_timeline",
    "rollup_funding",
    "rollup_savings",
    "summarise_funding_plan",
]

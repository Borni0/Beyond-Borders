"""Year-by-year cost projection.

Spec §8.1: recurring × applicable periods; partial-period rounding rule is
documented and tested. Refundable deposits are kept in a separate bucket.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Iterable, Sequence

from app.services.financial.currency import convert
from app.services.financial.money import decimal_places, round_money
from app.services.financial.types import (
    CostBreakdown,
    CostItem,
    Frequency,
    FxRate,
    PlanContext,
    YearCost,
)


def _months_in_year(year_index: int, plan_start: date, duration_months: int) -> int:
    """How many of the study-plan months fall inside study-year `year_index`.

    Study year 1 starts at `plan_start`. Each subsequent year starts the
    anniversary of `plan_start`. The final year may be partial.
    """
    year_start_month = (year_index - 1) * 12
    year_end_month_exclusive = min(year_index * 12, duration_months)
    return max(0, year_end_month_exclusive - year_start_month)


def _year_window(year_index: int, plan_start: date) -> tuple[date, date]:
    """First day (inclusive) and last day (exclusive) of study-year `year_index`."""
    from calendar import monthrange

    start_month_index = (year_index - 1) * 12
    start_year = plan_start.year + (start_month_index // 12)
    start_month = ((plan_start.month - 1 + start_month_index) % 12) + 1

    end_month_index = year_index * 12
    end_year = plan_start.year + (end_month_index // 12)
    end_month = ((plan_start.month - 1 + end_month_index) % 12) + 1

    start = date(start_year, start_month, plan_start.day)
    # The exclusive end is the first day of the next year-window. Use day=1
    # because we only care about containment, not exact dates.
    if end_month == 12:
        end = date(end_year + 1, 1, 1)
    else:
        end = date(end_year, end_month + 1, 1)

    # Cap day-of-month at the destination's max for short months.
    _, last_day = monthrange(start.year, start.month)
    if start.day > last_day:
        start = start.replace(day=last_day)

    return start, end


def _recurring_periods_in_year(
    item: CostItem,
    plan: PlanContext,
    year_index: int,
) -> int:
    months = _months_in_year(year_index, plan.start_date, plan.duration_months)
    if months == 0:
        return 0
    if item.frequency == Frequency.MONTHLY:
        return months
    if item.frequency == Frequency.QUARTERLY:
        return months // 3
    if item.frequency == Frequency.SEMESTER:
        return 1 if months >= 6 else 0
    if item.frequency == Frequency.ANNUAL:
        return 1
    return 0


def _one_time_year(item: CostItem, plan: PlanContext) -> int | None:
    """Return the 1-based year index where a one-time cost lands, or None if
    the item falls entirely outside the plan's timeline."""
    if not item.is_one_time:
        return None
    target = item.start_date or item.end_date
    if target is None:
        return None

    months_from_start = (target.year - plan.start_date.year) * 12 + (
        target.month - plan.start_date.month
    )
    if target < plan.start_date:
        # Before the plan starts — treat as part of the upfront window
        # (year 1) rather than silently dropping.
        return 1
    if months_from_start >= plan.duration_months:
        return None
    return (months_from_start // 12) + 1


def _category_bucket(item: CostItem) -> str:
    return item.category.value


def project_costs(
    plan: PlanContext,
    costs: Iterable[CostItem],
    fx: dict[tuple[str, str], FxRate],
) -> CostBreakdown:
    """Project the costs in `costs` across the plan's years, in base currency.

    Refundable deposits are summed into a separate bucket and do not
    contribute to `total_projected_cost`.
    """
    base = plan.base_currency.upper()
    years = max(1, (plan.duration_months + 11) // 12)
    per_year_recurring = [Decimal("0")] * years
    per_year_one_time = [Decimal("0")] * years
    per_category: dict[str, Decimal] = {}
    refundable = Decimal("0")

    for item in costs:
        amount_base = convert(item.amount, item.currency, base, fx)

        if item.is_refundable:
            refundable += amount_base
            continue

        if item.is_one_time or item.frequency == Frequency.ONE_TIME:
            yi = _one_time_year(item, plan)
            if yi is None:
                continue
            # Attribute the one-time to its year bucket; the per-category total
            # is the sum of the one-time amount (it's counted once).
            per_category[_category_bucket(item)] = per_category.get(
                _category_bucket(item), Decimal("0")
            ) + amount_base
            if 1 <= yi <= years:
                per_year_one_time[yi - 1] += amount_base
            continue

        # Recurring: sum across all applicable periods to get the full-plan
        # category total, then fan out into per-year buckets.
        total_for_item = Decimal("0")
        for yi in range(1, years + 1):
            periods = _recurring_periods_in_year(item, plan, yi)
            if periods == 0:
                continue
            per_year_recurring[yi - 1] += amount_base * periods
            total_for_item += amount_base * periods
        per_category[_category_bucket(item)] = per_category.get(
            _category_bucket(item), Decimal("0")
        ) + total_for_item

    # Round per-year totals to base currency precision once.
    per_year_recurring = [round_money(v, base) for v in per_year_recurring]
    per_year_one_time = [round_money(v, base) for v in per_year_one_time]

    year_costs = [
        YearCost(
            year_index=yi + 1,
            recurring_total=per_year_recurring[yi],
            one_time_total=per_year_one_time[yi],
            total=round_money(
                per_year_recurring[yi] + per_year_one_time[yi], base
            ),
        )
        for yi in range(years)
    ]

    total = sum((yc.total for yc in year_costs), Decimal("0"))
    total = round_money(total, base)
    first_year = year_costs[0].total if year_costs else round_money(Decimal("0"), base)

    return CostBreakdown(
        base_currency=base,
        per_year=year_costs,
        first_year_cost=first_year,
        total_projected_cost=total,
        refundable_deposits=round_money(refundable, base),
        per_category={k: round_money(v, base) for k, v in per_category.items()},
    )


def project_upfront(
    plan: PlanContext,
    costs: Iterable[CostItem],
    fx: dict[tuple[str, str], FxRate],
    window_days: int = 30,
) -> Decimal:
    """Sum of cost items whose effective date is within `window_days` of
    `plan.start_date` (or earlier). Refundable deposits are excluded.

    `due_before_departure` items are always counted: the user is
    explicitly telling the engine "this one must be paid before I
    leave, regardless of when I created the row".
    """
    base = plan.base_currency.upper()
    from datetime import timedelta

    cutoff = plan.start_date + timedelta(days=window_days)
    total = Decimal("0")
    for item in costs:
        if item.is_refundable:
            continue
        if item.due_before_departure:
            total += convert(item.amount, item.currency, base, fx)
            continue
        target = item.start_date or item.end_date
        if target is None:
            # One-time items without a date are conservatively counted.
            target = plan.start_date
        if target <= cutoff:
            total += convert(item.amount, item.currency, base, fx)
    return round_money(total, base)


__all__ = ["project_costs", "project_upfront"]
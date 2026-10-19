"""Tests for year-by-year cost projection.

Locks the spec §8.1 behavior:
- Refundable deposits live in a separate bucket; never netted.
- One-time costs land in the year that contains their date.
- Recurring × applicable periods, with partial-period rounding at the end.
- Periods past plan end are zero.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.services.financial.currency import index_rates
from app.services.financial.projection import project_costs, project_upfront
from app.services.financial.types import (
    CostCategory,
    CostItem,
    Frequency,
    FxRate,
    PlanContext,
    RateType,
)


def _item(
    *,
    id: str = "i1",
    amount: str = "100.00",
    currency: str = "USD",
    frequency: Frequency = Frequency.MONTHLY,
    start_date: date | None = None,
    end_date: date | None = None,
    is_one_time: bool = False,
    is_refundable: bool = False,
    category: CostCategory = CostCategory.TUITION,
) -> CostItem:
    return CostItem(
        id=id,
        category=category,
        description="",
        amount=Decimal(amount),
        currency=currency,
        frequency=frequency,
        start_date=start_date,
        end_date=end_date,
        is_one_time=is_one_time,
        is_refundable=is_refundable,
    )


@pytest.fixture()
def plan() -> PlanContext:
    # 24-month plan starting Jan 1, 2026 → two full years.
    return PlanContext(
        id="p1",
        name="MSc in Berlin",
        base_currency="USD",
        start_date=date(2026, 1, 1),
        duration_months=24,
    )


@pytest.fixture()
def plan_30_months() -> PlanContext:
    # 30-month plan → 3 years, last one is 6 months.
    return PlanContext(
        id="p2",
        name="MBA",
        base_currency="USD",
        start_date=date(2026, 1, 1),
        duration_months=30,
    )


@pytest.fixture()
def fx_empty() -> dict:
    return index_rates([])


class TestRecurring:
    def test_monthly_24_months_two_full_years(self, plan, fx_empty) -> None:
        # $100/month × 24 = $2400, $1200 per year.
        items = [_item(amount="100.00", frequency=Frequency.MONTHLY)]
        out = project_costs(plan, items, fx_empty)

        assert out.base_currency == "USD"
        assert len(out.per_year) == 2
        assert out.per_year[0].total == Decimal("1200.00")
        assert out.per_year[1].total == Decimal("1200.00")
        assert out.total_projected_cost == Decimal("2400.00")

    def test_quarterly_24_months(self, plan, fx_empty) -> None:
        # $300/quarter × 8 quarters = $2400, $1200 per year.
        items = [_item(amount="300.00", frequency=Frequency.QUARTERLY)]
        out = project_costs(plan, items, fx_empty)

        assert out.per_year[0].total == Decimal("1200.00")
        assert out.per_year[1].total == Decimal("1200.00")
        assert out.total_projected_cost == Decimal("2400.00")

    def test_semester_24_months(self, plan, fx_empty) -> None:
        # We model "semester" as one charge per academic year (the simpler,
        # more conservative interpretation). 24 months / 2 years = 2 charges
        # total = $3000. Each year-window sees exactly one semester.
        items = [_item(amount="1500.00", frequency=Frequency.SEMESTER)]
        out = project_costs(plan, items, fx_empty)

        assert out.per_year[0].total == Decimal("1500.00")
        assert out.per_year[1].total == Decimal("1500.00")
        assert out.total_projected_cost == Decimal("3000.00")

    def test_annual_24_months(self, plan, fx_empty) -> None:
        # $1200/year → 1 charge per year.
        items = [_item(amount="1200.00", frequency=Frequency.ANNUAL)]
        out = project_costs(plan, items, fx_empty)

        assert out.per_year[0].total == Decimal("1200.00")
        assert out.per_year[1].total == Decimal("1200.00")
        assert out.total_projected_cost == Decimal("2400.00")

    def test_partial_last_year(self, plan_30_months, fx_empty) -> None:
        # Monthly over 30 months: 12 + 12 + 6 = 30 charges.
        items = [_item(amount="100.00", frequency=Frequency.MONTHLY)]
        out = project_costs(plan_30_months, items, fx_empty)

        assert len(out.per_year) == 3
        assert out.per_year[0].total == Decimal("1200.00")
        assert out.per_year[1].total == Decimal("1200.00")
        assert out.per_year[2].total == Decimal("600.00")
        assert out.total_projected_cost == Decimal("3000.00")

    def test_zero_duration_means_zero_costs(self, plan, fx_empty) -> None:
        empty_plan = PlanContext(
            id="p0", name="x", base_currency="USD",
            start_date=date(2026, 1, 1), duration_months=0,
        )
        items = [_item(amount="100.00", frequency=Frequency.MONTHLY)]
        out = project_costs(empty_plan, items, fx_empty)
        # One year still exists (the model floor is 1 year) but with zero months.
        assert out.per_year[0].total == Decimal("0.00")
        assert out.total_projected_cost == Decimal("0.00")


class TestOneTime:
    def test_one_time_in_year_one(self, plan, fx_empty) -> None:
        # Acceptance fee on day 1 of plan.
        items = [
            _item(
                amount="500.00",
                frequency=Frequency.ONE_TIME,
                start_date=date(2026, 2, 1),
                is_one_time=True,
            )
        ]
        out = project_costs(plan, items, fx_empty)
        assert out.per_year[0].one_time_total == Decimal("500.00")
        assert out.per_year[1].one_time_total == Decimal("0.00")
        assert out.total_projected_cost == Decimal("500.00")

    def test_one_time_in_year_two(self, plan, fx_empty) -> None:
        # A renewal fee 14 months in lands in year 2.
        items = [
            _item(
                amount="800.00",
                frequency=Frequency.ONE_TIME,
                start_date=date(2027, 3, 1),
                is_one_time=True,
            )
        ]
        out = project_costs(plan, items, fx_empty)
        assert out.per_year[0].one_time_total == Decimal("0.00")
        assert out.per_year[1].one_time_total == Decimal("800.00")
        assert out.total_projected_cost == Decimal("800.00")

    def test_one_time_after_plan_end_is_dropped(self, plan, fx_empty) -> None:
        # Date 5 years in → no year bucket; not silently counted.
        items = [
            _item(
                amount="500.00",
                frequency=Frequency.ONE_TIME,
                start_date=date(2031, 6, 1),
                is_one_time=True,
            )
        ]
        out = project_costs(plan, items, fx_empty)
        assert out.total_projected_cost == Decimal("0.00")

    def test_one_time_before_plan_start_routes_to_year_one(
        self, plan, fx_empty
    ) -> None:
        # A cost dated before the plan starts is part of the upfront window.
        items = [
            _item(
                amount="200.00",
                frequency=Frequency.ONE_TIME,
                start_date=date(2025, 11, 1),
                is_one_time=True,
            )
        ]
        out = project_costs(plan, items, fx_empty)
        assert out.per_year[0].one_time_total == Decimal("200.00")
        assert out.total_projected_cost == Decimal("200.00")


class TestRefundable:
    def test_refundable_separate_bucket(self, plan, fx_empty) -> None:
        # A $1000 deposit is refundable; should appear in refundable_deposits
        # and NOT in any year's total.
        items = [
            _item(
                amount="1000.00",
                frequency=Frequency.ONE_TIME,
                start_date=date(2026, 1, 15),
                is_one_time=True,
                is_refundable=True,
                category=CostCategory.DEPOSITS,
            )
        ]
        out = project_costs(plan, items, fx_empty)
        assert out.refundable_deposits == Decimal("1000.00")
        assert out.total_projected_cost == Decimal("0.00")
        # The deposit must not be counted in any year.
        for y in out.per_year:
            assert y.one_time_total == Decimal("0.00")

    def test_refundable_plus_real_costs(self, plan, fx_empty) -> None:
        # Mix of refundable deposit + monthly rent: only rent hits total.
        items = [
            _item(
                amount="1000.00",
                frequency=Frequency.ONE_TIME,
                start_date=date(2026, 1, 15),
                is_one_time=True,
                is_refundable=True,
                category=CostCategory.DEPOSITS,
            ),
            _item(
                amount="800.00",
                frequency=Frequency.MONTHLY,
                category=CostCategory.ACCOMMODATION,
            ),
        ]
        out = project_costs(plan, items, fx_empty)
        assert out.refundable_deposits == Decimal("1000.00")
        # $800 × 24 = $19200.
        assert out.total_projected_cost == Decimal("19200.00")


class TestPerCategory:
    def test_categories_accumulate(self, plan, fx_empty) -> None:
        items = [
            _item(amount="500.00", frequency=Frequency.ONE_TIME,
                  start_date=date(2026, 1, 1), is_one_time=True,
                  category=CostCategory.TUITION),
            _item(amount="800.00", frequency=Frequency.MONTHLY,
                  category=CostCategory.ACCOMMODATION),
        ]
        out = project_costs(plan, items, fx_empty)
        # Tuition: 500; Accommodation: 800 * 24 = 19200.
        assert out.per_category["tuition"] == Decimal("500.00")
        assert out.per_category["accommodation"] == Decimal("19200.00")

    def test_refundable_excluded_from_categories(self, plan, fx_empty) -> None:
        # Refundable deposits must not inflate any category total.
        items = [
            _item(
                amount="500.00",
                frequency=Frequency.ONE_TIME,
                start_date=date(2026, 1, 1),
                is_one_time=True,
                is_refundable=True,
                category=CostCategory.DEPOSITS,
            ),
        ]
        out = project_costs(plan, items, fx_empty)
        # The deposits category either isn't present or is zero (depending on
        # how we choose to bucket it). Refundable must never inflate.
        assert out.per_category.get("deposits", Decimal("0")) == Decimal("0.00")


class TestProjectUpfront:
    def test_within_30_days(self, plan, fx_empty) -> None:
        # Anything in the first 30 days counts as upfront.
        items = [
            _item(
                amount="500.00",
                frequency=Frequency.ONE_TIME,
                start_date=date(2026, 1, 5),
                is_one_time=True,
            ),
            _item(
                amount="800.00",
                frequency=Frequency.MONTHLY,
                category=CostCategory.ACCOMMODATION,
            ),
        ]
        upfront = project_upfront(plan, items, fx_empty)
        # 500 (one-time in window) + 800 (1 month of rent in window) = 1300.
        assert upfront == Decimal("1300.00")

    def test_outside_window_not_counted(self, plan, fx_empty) -> None:
        items = [
            _item(
                amount="500.00",
                frequency=Frequency.ONE_TIME,
                start_date=date(2026, 6, 1),  # 5 months in
                is_one_time=True,
            ),
        ]
        upfront = project_upfront(plan, items, fx_empty)
        assert upfront == Decimal("0.00")

    def test_refundable_excluded_from_upfront(self, plan, fx_empty) -> None:
        items = [
            _item(
                amount="1000.00",
                frequency=Frequency.ONE_TIME,
                start_date=date(2026, 1, 15),
                is_one_time=True,
                is_refundable=True,
                category=CostCategory.DEPOSITS,
            ),
        ]
        upfront = project_upfront(plan, items, fx_empty)
        assert upfront == Decimal("0.00")

    def test_one_time_without_date_is_conservatively_counted(
        self, plan, fx_empty
    ) -> None:
        # A one-time with no date should still surface as upfront, not vanish.
        items = [
            _item(
                amount="300.00",
                frequency=Frequency.ONE_TIME,
                is_one_time=True,
            ),
        ]
        upfront = project_upfront(plan, items, fx_empty)
        assert upfront == Decimal("300.00")

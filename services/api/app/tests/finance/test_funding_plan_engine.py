"""Pure-data tests for the funding-plan engine.

These don't touch the DB; they verify recurrence, overdue derivation,
funding/savings rollups, and conversion arithmetic.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.services.financial.money import zero_money
from app.services.financial.types import (
    FundingSource as EngineFundingSource,
    FundingStatus,
    FundingType,
    FxRate,
    RateType,
)
from app.services.funding_plan_service import (
    PaymentEventInput,
    SavingsGoalInput,
    derive_display_status,
    estimate_conversion,
    project_payment_timeline,
    rollup_funding,
    rollup_savings,
    summarise_funding_plan,
)


def test_derive_display_status_treats_past_due_as_overdue() -> None:
    today = date(2026, 6, 1)
    assert derive_display_status("planned", date(2026, 5, 20), today) == "overdue"
    assert derive_display_status("scheduled", date(2026, 5, 20), today) == "overdue"
    assert derive_display_status("planned", date(2026, 6, 5), today) == "planned"
    assert derive_display_status("paid", date(2026, 5, 20), today) == "paid"
    assert derive_display_status("cancelled", date(2026, 5, 20), today) == "cancelled"


def test_project_timeline_includes_recurrences() -> None:
    today = date(2026, 6, 1)
    ev = PaymentEventInput(
        id="p1",
        title="Rent",
        category="accommodation",
        amount=Decimal("1000"),
        currency="USD",
        due_date=date(2026, 6, 5),
        status="planned",
        plan_id=None,
        is_recurring=True,
        recurrence_frequency="monthly",
        recurrence_end_date=None,
    )
    entries = project_payment_timeline([ev], today=today)
    # Stored occurrence + 12 forward months within the 12-month horizon.
    assert len(entries) == 13
    assert entries[0].due_date == date(2026, 6, 5)
    assert entries[1].due_date == date(2026, 7, 5)
    assert entries[-1].due_date == date(2027, 6, 5)


def test_project_timeline_honours_recurrence_end_date() -> None:
    today = date(2026, 6, 1)
    ev = PaymentEventInput(
        id="p1",
        title="Insurance",
        category="insurance",
        amount=Decimal("200"),
        currency="USD",
        due_date=date(2026, 7, 1),
        status="planned",
        plan_id=None,
        is_recurring=True,
        recurrence_frequency="quarterly",
        recurrence_end_date=date(2026, 10, 1),
    )
    entries = project_payment_timeline([ev], today=today)
    # 1 stored + 1 quarter (Oct) within the explicit end date
    assert len(entries) == 2
    assert entries[0].due_date == date(2026, 7, 1)
    assert entries[1].due_date == date(2026, 10, 1)


def test_rollup_funding_groups_by_currency_and_status() -> None:
    sources = [
        EngineFundingSource(
            id="s1",
            name="Savings",
            funding_type=FundingType.SAVINGS,
            amount=Decimal("100"),
            currency="USD",
            status=FundingStatus.CONFIRMED,
            expected_date=None,
        ),
        EngineFundingSource(
            id="s2",
            name="Scholarship",
            funding_type=FundingType.SCHOLARSHIP,
            amount=Decimal("50"),
            currency="USD",
            status=FundingStatus.CONDITIONAL,
            expected_date=None,
        ),
        EngineFundingSource(
            id="s3",
            name="Family gift",
            funding_type=FundingType.FAMILY,
            amount=Decimal("200"),
            currency="EUR",
            status=FundingStatus.CONFIRMED,
            expected_date=None,
        ),
    ]
    buckets = rollup_funding(sources)
    assert len(buckets) == 2
    by_ccy = {b.currency: b for b in buckets}
    assert by_ccy["USD"].total == Decimal("150")
    assert by_ccy["USD"].confirmed == Decimal("100")
    assert by_ccy["USD"].conditional == Decimal("50")
    assert by_ccy["EUR"].confirmed == Decimal("200")


def test_rollup_savings_aggregates_per_currency() -> None:
    goals = [
        SavingsGoalInput(
            id="g1", name="A",
            target_amount=Decimal("1000"),
            current_amount=Decimal("100"),
            currency="USD",
            target_date=date(2026, 12, 1),
        ),
        SavingsGoalInput(
            id="g2", name="B",
            target_amount=Decimal("500"),
            current_amount=Decimal("50"),
            currency="USD",
            target_date=date(2027, 6, 1),
        ),
        SavingsGoalInput(
            id="g3", name="C",
            target_amount=Decimal("8000"),
            current_amount=Decimal("0"),
            currency="JPY",
            target_date=date(2026, 12, 1),
        ),
    ]
    out = rollup_savings(goals)
    by_ccy = {b.currency: b for b in out}
    assert by_ccy["USD"].target_total == Decimal("1500")
    assert by_ccy["USD"].current_total == Decimal("150")
    assert by_ccy["JPY"].target_total == Decimal("8000")


def test_summarise_funding_plan_rollups_upcoming_and_overdue() -> None:
    today = date(2026, 6, 1)
    sources = [
        EngineFundingSource(
            id="s1", name="A",
            funding_type=FundingType.SAVINGS,
            amount=Decimal("1000"),
            currency="USD",
            status=FundingStatus.CONFIRMED,
            expected_date=None,
        ),
    ]
    goals: list[SavingsGoalInput] = []
    events = [
        PaymentEventInput(
            id="p1", title="Late", category="accommodation",
            amount=Decimal("100"), currency="USD",
            due_date=date(2026, 5, 1), status="planned",
            plan_id=None, is_recurring=False,
            recurrence_frequency=None, recurrence_end_date=None,
        ),
        PaymentEventInput(
            id="p2", title="Soon", category="tuition",
            amount=Decimal("250"), currency="USD",
            due_date=date(2026, 6, 10), status="scheduled",
            plan_id=None, is_recurring=False,
            recurrence_frequency=None, recurrence_end_date=None,
        ),
        PaymentEventInput(
            id="p3", title="Far", category="travel",
            amount=Decimal("500"), currency="USD",
            due_date=date(2027, 1, 1), status="planned",
            plan_id=None, is_recurring=False,
            recurrence_frequency=None, recurrence_end_date=None,
        ),
        PaymentEventInput(
            id="p4", title="Done", category="visa",
            amount=Decimal("50"), currency="USD",
            due_date=date(2026, 5, 1), status="paid",
            plan_id=None, is_recurring=False,
            recurrence_frequency=None, recurrence_end_date=None,
        ),
    ]
    timeline = project_payment_timeline(events, today=today)
    summary = summarise_funding_plan("USD", sources, goals, timeline, today=today)

    assert summary.base_currency == "USD"
    assert summary.upcoming_payments_count == 1
    assert summary.overdue_payments_count == 1
    assert summary.upcoming_payments == Decimal("250")
    assert summary.overdue_payments == Decimal("100")
    # Notes mention the overdue count
    assert any("past due" in n.lower() for n in summary.notes)


def test_estimate_conversion_applies_fee_to_converted_amount() -> None:
    rates = [
        FxRate(
            base_currency="USD",
            quote_currency="EUR",
            rate=Decimal("0.9"),
            rate_type=RateType.USER_ENTERED,
            observed_at=date(2026, 6, 1),
        )
    ]
    est = estimate_conversion(
        Decimal("1000"), "USD", "EUR", rates, fee_pct=Decimal("0.01")
    )
    assert est.converted_amount == Decimal("900.00")
    assert est.fee_amount == Decimal("9.00")
    assert est.total_cost == Decimal("909.00")


def test_estimate_conversion_rejects_negative_amount() -> None:
    rates = [
        FxRate(
            base_currency="USD",
            quote_currency="EUR",
            rate=Decimal("0.9"),
            rate_type=RateType.USER_ENTERED,
            observed_at=date(2026, 6, 1),
        )
    ]
    with pytest.raises(ValueError):
        estimate_conversion(Decimal("-1"), "USD", "EUR", rates)


def test_estimate_conversion_identity_for_same_currency() -> None:
    est = estimate_conversion(Decimal("100"), "USD", "USD", [], fee_pct=Decimal("0.01"))
    assert est.converted_amount == Decimal("100.00")
    assert est.total_cost == Decimal("101.00")

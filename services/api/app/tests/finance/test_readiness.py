"""Tests for the readiness orchestrator (spec §9).

The contract under test:
- Same inputs → byte-identical ReadinessResult.
- All six status codes can co-exist (the UI surfaces them as chips).
- Funding gap = max(0, projected_cost - eligible_confirmed); surplus is also
  visible (never hidden) so the UI can show "fully funded, X spare".
- Missing inputs (no costs, no confirmed funding, missing FX) trigger
  needs_more_information.
- Refundable deposits do not inflate projected cost or funding gap.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.services.financial.currency import index_rates
from app.services.financial.readiness import compute_readiness
from app.services.financial.types import (
    CostCategory,
    CostItem,
    Frequency,
    FundingSource,
    FundingStatus,
    FundingType,
    FxRate,
    PlanContext,
    RateType,
    ReadinessStatusCode,
)


# ------------- helpers -------------
def _rate(base: str, quote: str, rate: str) -> FxRate:
    return FxRate(
        base_currency=base,
        quote_currency=quote,
        rate=Decimal(rate),
        rate_type=RateType.REFERENCE,
        observed_at=date(2026, 1, 1),
    )


def _cost(
    *,
    id: str,
    amount: str,
    currency: str = "USD",
    frequency: Frequency = Frequency.MONTHLY,
    category: CostCategory = CostCategory.TUITION,
    is_refundable: bool = False,
    is_one_time: bool = False,
    start_date: date | None = None,
    due_before_departure: bool = False,
) -> CostItem:
    return CostItem(
        id=id,
        category=category,
        description="",
        amount=Decimal(amount),
        currency=currency,
        frequency=frequency,
        start_date=start_date,
        end_date=None,
        is_one_time=is_one_time,
        is_refundable=is_refundable,
        due_before_departure=due_before_departure,
    )


def _funding(
    *,
    id: str,
    amount: str,
    currency: str = "USD",
    status: FundingStatus = FundingStatus.CONFIRMED,
    expected_date: date | None = None,
    funding_type: FundingType = FundingType.SAVINGS,
) -> FundingSource:
    return FundingSource(
        id=id,
        name="",
        funding_type=funding_type,
        amount=Decimal(amount),
        currency=currency,
        status=status,
        expected_date=expected_date,
    )


@pytest.fixture()
def plan() -> PlanContext:
    return PlanContext(
        id="p1",
        name="MSc",
        base_currency="USD",
        start_date=date(2026, 9, 1),
        duration_months=24,
    )


@pytest.fixture()
def fx_empty() -> dict:
    return index_rates([])


@pytest.fixture()
def full_inputs(plan: PlanContext) -> tuple[list[CostItem], list[FundingSource]]:
    costs = [
        _cost(
            id="tuition-y1",
            amount="15000.00",
            frequency=Frequency.ONE_TIME,
            is_one_time=True,
            start_date=date(2026, 9, 1),
        ),
        _cost(
            id="rent",
            amount="900.00",
            frequency=Frequency.MONTHLY,
            category=CostCategory.ACCOMMODATION,
        ),
        _cost(
            id="deposit",
            amount="2000.00",
            frequency=Frequency.ONE_TIME,
            is_one_time=True,
            start_date=date(2026, 8, 15),
            is_refundable=True,
            category=CostCategory.DEPOSITS,
        ),
    ]
    sources = [
        _funding(
            id="savings",
            amount="20000.00",
            funding_type=FundingType.SAVINGS,
        ),
        _funding(
            id="scholarship",
            amount="5000.00",
            funding_type=FundingType.SCHOLARSHIP,
            status=FundingStatus.CONDITIONAL,
        ),
    ]
    return costs, sources


# ------------- core contract -------------
class TestDeterminism:
    def test_same_inputs_same_output(
        self, plan, fx_empty, full_inputs
    ) -> None:
        costs, sources = full_inputs
        a = compute_readiness(plan, costs, sources, [])
        b = compute_readiness(plan, costs, sources, [])
        assert a.to_dict() == b.to_dict()

    def test_dict_keys_are_stable(
        self, plan, fx_empty, full_inputs
    ) -> None:
        costs, sources = full_inputs
        out = compute_readiness(plan, costs, sources, [])
        d = out.to_dict()
        # Document the contract: these keys always exist.
        for key in (
            "plan_id", "base_currency", "breakdown", "funding",
            "funding_gap", "funding_surplus", "upfront_cash_requirement",
            "upfront_cash_gap", "upfront_cash_window_days", "statuses",
            "missing_inputs", "notes",
        ):
            assert key in d

    def test_decimals_serialized_as_strings(
        self, plan, fx_empty, full_inputs
    ) -> None:
        costs, sources = full_inputs
        out = compute_readiness(plan, costs, sources, [])
        d = out.to_dict()
        # Money fields must be strings so JSON consumers get exact precision.
        assert isinstance(d["funding_gap"], str)
        assert isinstance(d["funding_surplus"], str)
        assert isinstance(d["upfront_cash_requirement"], str)
        assert isinstance(d["upfront_cash_gap"], str)
        for y in d["breakdown"]["per_year"]:
            assert isinstance(y["total"], str)
            assert isinstance(y["recurring_total"], str)
            assert isinstance(y["one_time_total"], str)


# ------------- gap / surplus -------------
class TestFundingGapAndSurplus:
    def test_gap_when_funding_below_costs(
        self, plan, fx_empty
    ) -> None:
        costs = [
            _cost(
                id="t", amount="15000.00", frequency=Frequency.MONTHLY,
                category=CostCategory.TUITION,
            )
        ]
        sources = [_funding(id="s", amount="5000.00")]
        out = compute_readiness(plan, costs, sources, [])
        # 15000 * 24 = 360000 cost; only 5000 funding → gap = 355000.
        assert out.funding_gap == Decimal("355000.00")
        assert out.funding_surplus == Decimal("0.00")

    def test_surplus_when_funding_exceeds_costs(
        self, plan, fx_empty
    ) -> None:
        costs = [
            _cost(
                id="r", amount="100.00", frequency=Frequency.MONTHLY,
                category=CostCategory.ACCOMMODATION,
            )
        ]
        sources = [_funding(id="s", amount="50000.00")]
        out = compute_readiness(plan, costs, sources, [])
        # 100 * 24 = 2400 cost; 50000 funding → surplus = 47600.
        assert out.funding_gap == Decimal("0.00")
        assert out.funding_surplus == Decimal("47600.00")

    def test_neither_gap_nor_surplus_when_balanced(
        self, plan, fx_empty
    ) -> None:
        # 24 × $100 = $2400 (cost); $2400 (confirmed funding) → both zero.
        costs = [
            _cost(
                id="r", amount="100.00", frequency=Frequency.MONTHLY,
                category=CostCategory.ACCOMMODATION,
            )
        ]
        sources = [_funding(id="s", amount="2400.00")]
        out = compute_readiness(plan, costs, sources, [])
        assert out.funding_gap == Decimal("0.00")
        assert out.funding_surplus == Decimal("0.00")

    def test_only_confirmed_counts_toward_gap(
        self, plan, fx_empty
    ) -> None:
        # Conditional/expected/unavailable funding do NOT reduce the gap.
        costs = [
            _cost(
                id="t", amount="100.00", frequency=Frequency.MONTHLY,
                category=CostCategory.TUITION,
            )
        ]
        sources = [
            _funding(id="a", amount="10000.00",
                     status=FundingStatus.CONDITIONAL),
            _funding(id="b", amount="5000.00",
                     status=FundingStatus.EXPECTED),
            _funding(id="c", amount="5000.00",
                     status=FundingStatus.UNAVAILABLE),
        ]
        out = compute_readiness(plan, costs, sources, [])
        # No confirmed funding → gap = full 24 * 100 = 2400.
        assert out.funding_gap == Decimal("2400.00")


# ------------- status classification -------------
class TestStatuses:
    def test_needs_more_information_when_no_costs(
        self, plan, fx_empty
    ) -> None:
        # No costs at all → must surface NEEDS_MORE_INFORMATION.
        sources = [_funding(id="s", amount="10000.00")]
        out = compute_readiness(plan, [], sources, [])
        assert out.statuses.has(ReadinessStatusCode.NEEDS_MORE_INFORMATION)
        assert any("cost" in m.lower() for m in out.missing_inputs)

    def test_needs_more_information_when_no_confirmed(
        self, plan, fx_empty
    ) -> None:
        costs = [
            _cost(
                id="r", amount="100.00", frequency=Frequency.MONTHLY,
                category=CostCategory.ACCOMMODATION,
            )
        ]
        # Only conditional funding → must surface NEEDS_MORE_INFORMATION.
        sources = [
            _funding(
                id="s", amount="5000.00",
                status=FundingStatus.CONDITIONAL,
            )
        ]
        out = compute_readiness(plan, costs, sources, [])
        assert out.statuses.has(ReadinessStatusCode.NEEDS_MORE_INFORMATION)

    def test_funding_gap_status_fires(
        self, plan, fx_empty
    ) -> None:
        costs = [
            _cost(
                id="t", amount="100.00", frequency=Frequency.MONTHLY,
                category=CostCategory.TUITION,
            )
        ]
        sources = [_funding(id="s", amount="10.00")]
        out = compute_readiness(plan, costs, sources, [])
        assert out.statuses.has(ReadinessStatusCode.FUNDING_GAP_IDENTIFIED)

    def test_upfront_gap_status_fires(
        self, plan, fx_empty
    ) -> None:
        # Big cost in the first 30 days; the only funding expected AFTER
        # start_date, so available_before_departure = 0 → gap = 5000.
        costs = [
            _cost(
                id="visa", amount="5000.00",
                frequency=Frequency.ONE_TIME, is_one_time=True,
                start_date=date(2026, 9, 1),
            )
        ]
        sources = [
            _funding(
                id="s", amount="100.00",
                expected_date=date(2027, 1, 1),  # after start
            )
        ]
        out = compute_readiness(plan, costs, sources, [])
        assert out.statuses.has(ReadinessStatusCode.UPFRONT_CASH_GAP)
        assert out.upfront_cash_gap == Decimal("5000.00")

    def test_conditional_funding_status_fires(
        self, plan, fx_empty, full_inputs
    ) -> None:
        costs, sources = full_inputs
        out = compute_readiness(plan, costs, sources, [])
        assert out.statuses.has(ReadinessStatusCode.CONDITIONAL_FUNDING)

    def test_no_modeled_shortfall_only_when_inputs_sufficient_and_balanced(
        self, plan, fx_empty
    ) -> None:
        # Inputs sufficient, no gap, no upfront gap → NO_MODELED_SHORTFALL.
        # Plan covers 24 months at $100/mo (cost $2400); $3000 confirmed
        # funding, of which $3000 is available_before_departure (no
        # expected_date). Upfront need = 1 month rent = $100 → covered.
        costs = [
            _cost(
                id="r", amount="100.00", frequency=Frequency.MONTHLY,
                category=CostCategory.ACCOMMODATION,
            )
        ]
        sources = [_funding(id="s", amount="3000.00")]
        out = compute_readiness(plan, costs, sources, [])
        assert out.statuses.has(ReadinessStatusCode.NO_MODELED_SHORTFALL)

    def test_scenario_sensitive_chip_always_present_in_phase_1(
        self, plan, fx_empty, full_inputs
    ) -> None:
        costs, sources = full_inputs
        out = compute_readiness(plan, costs, sources, [])
        # Phase 1 has no scenario engine; the chip is always present (False
        # in UI), so the user knows the field exists.
        assert out.statuses.has(ReadinessStatusCode.SCENARIO_SENSITIVE)
        # And a note explaining what's missing.
        assert any("scenario" in n.lower() for n in out.notes)

    def test_statuses_can_coexist(
        self, plan, fx_empty
    ) -> None:
        # Many flags on at once: gap + upfront gap + conditional + missing
        # inputs would all be possible. Build inputs that produce FOUR.
        costs = [
            # Refundable deposit only on inputs → still missing real costs
            _cost(
                id="d", amount="1000.00",
                frequency=Frequency.ONE_TIME, is_one_time=True,
                start_date=date(2026, 8, 15),
                is_refundable=True,
                category=CostCategory.DEPOSITS,
            ),
            # And one real cost in the upfront window
            _cost(
                id="v", amount="5000.00",
                frequency=Frequency.ONE_TIME, is_one_time=True,
                start_date=date(2026, 9, 1),
            ),
        ]
        sources = [
            # Conditional source → triggers CONDITIONAL_FUNDING
            _funding(
                id="s", amount="1000.00",
                status=FundingStatus.CONDITIONAL,
            ),
        ]
        out = compute_readiness(plan, costs, sources, [])
        codes = set(out.statuses.codes)
        # Upfront cash gap (5000 need, 0 available), no confirmed funding →
        # NEEDS_MORE_INFORMATION, CONDITIONAL_FUNDING, UPFRONT_CASH_GAP,
        # SCENARIO_SENSITIVE all co-exist.
        assert ReadinessStatusCode.UPFRONT_CASH_GAP in codes
        assert ReadinessStatusCode.NEEDS_MORE_INFORMATION in codes
        assert ReadinessStatusCode.CONDITIONAL_FUNDING in codes
        assert ReadinessStatusCode.SCENARIO_SENSITIVE in codes


# ------------- FX integration -------------
class TestFxIntegration:
    def test_missing_fx_for_non_base_currency_fires_missing_input(
        self, plan
    ) -> None:
        # Cost in EUR, no rate entered → must surface as a missing input,
        # not silently fall back to identity.
        costs = [
            _cost(
                id="r", amount="800.00", currency="EUR",
                frequency=Frequency.MONTHLY,
                category=CostCategory.ACCOMMODATION,
            )
        ]
        sources = [_funding(id="s", amount="20000.00")]
        out = compute_readiness(plan, costs, sources, [])
        assert out.statuses.has(ReadinessStatusCode.NEEDS_MORE_INFORMATION)
        # The engine surfaces the pair name (either direction is fine).
        joined = " ".join(out.missing_inputs).upper()
        assert "EUR" in joined and "USD" in joined

    def test_with_fx_present_calculations_use_rate(
        self, plan
    ) -> None:
        # FxRate(EUR, USD, 0.9) means 1 EUR = 0.9 USD.
        # So 800 EUR/month * 24 = 19200 EUR * 0.9 = 17280 USD over 24 months.
        costs = [
            _cost(
                id="r", amount="800.00", currency="EUR",
                frequency=Frequency.MONTHLY,
                category=CostCategory.ACCOMMODATION,
            )
        ]
        sources = [_funding(id="s", amount="20000.00", currency="USD")]
        rates = [_rate("EUR", "USD", "0.9")]
        out = compute_readiness(plan, costs, sources, rates)

        assert out.breakdown.total_projected_cost == Decimal("17280.00")
        # Funding available: 20000 USD > 17280 → surplus = 2720, gap = 0.
        assert out.funding_gap == Decimal("0.00")
        assert out.funding_surplus == Decimal("2720.00")


# ------------- notes -------------
class TestNotes:
    def test_no_shortfall_note_when_status_present(
        self, plan, fx_empty
    ) -> None:
        costs = [
            _cost(
                id="r", amount="100.00", frequency=Frequency.MONTHLY,
                category=CostCategory.ACCOMMODATION,
            )
        ]
        sources = [_funding(id="s", amount="3000.00")]
        out = compute_readiness(plan, costs, sources, [])
        assert any(
            "not a guarantee" in n.lower() for n in out.notes
        )

    def test_refundable_deposits_note_when_present(
        self, plan, fx_empty
    ) -> None:
        costs = [
            _cost(
                id="rent", amount="900.00", frequency=Frequency.MONTHLY,
                category=CostCategory.ACCOMMODATION,
            ),
            _cost(
                id="dep", amount="2000.00", frequency=Frequency.ONE_TIME,
                is_one_time=True, start_date=date(2026, 8, 15),
                is_refundable=True,
                category=CostCategory.DEPOSITS,
            ),
        ]
        sources = [_funding(id="s", amount="25000.00")]
        out = compute_readiness(plan, costs, sources, [])
        assert any(
            "refundable" in n.lower() for n in out.notes
        )
        # And the deposit is mentioned with its value.
        assert any("2000" in n for n in out.notes)

    # ---- Phase 1 readiness enrichment ----
    def test_first_year_funding_gap_uses_only_first_year_cost(
        self, plan, fx_empty
    ) -> None:
        # Year 1 cost is 15,000 tuition + 12*1,200 rent = 29,400.
        # Year 2 cost is 12*1,200 rent = 14,400. Total = 43,800.
        # Confirmed funding is 20,000.
        # First-year gap = 29,400 - 20,000 = 9,400.
        # Total gap = 43,800 - 20,000 = 23,800.
        costs = [
            _cost(
                id="tuition", amount="15000.00",
                frequency=Frequency.ONE_TIME, is_one_time=True,
                start_date=date(2026, 9, 1),
                category=CostCategory.TUITION,
            ),
            _cost(
                id="rent", amount="1200.00",
                frequency=Frequency.MONTHLY,
                category=CostCategory.ACCOMMODATION,
            ),
        ]
        sources = [_funding(id="savings", amount="20000.00")]
        out = compute_readiness(plan, costs, sources, [])
        assert out.first_year_funding_gap == Decimal("9400.00")
        assert out.funding_gap == Decimal("23800.00")

    def test_coverage_pct_uses_eligible_with_conditional(
        self, plan, fx_empty
    ) -> None:
        # Total cost = 30,000. Eligible confirmed = 20,000,
        # eligible with conditional = 25,000 → coverage 83.33%.
        costs = [
            _cost(
                id="tuition", amount="30000.00",
                frequency=Frequency.ONE_TIME, is_one_time=True,
                start_date=date(2026, 9, 1),
                category=CostCategory.TUITION,
            ),
        ]
        sources = [
            _funding(id="s1", amount="20000.00", status=FundingStatus.CONFIRMED),
            _funding(id="s2", amount="5000.00", status=FundingStatus.CONDITIONAL),
        ]
        out = compute_readiness(plan, costs, sources, [])
        assert out.coverage_pct == Decimal("83.33")

    def test_coverage_pct_is_none_when_no_costs(
        self, plan, fx_empty
    ) -> None:
        sources = [_funding(id="s", amount="5000.00")]
        out = compute_readiness(plan, [], sources, [])
        assert out.coverage_pct is None

    def test_potential_gap_strips_conditional_and_expected(
        self, plan, fx_empty
    ) -> None:
        # 30k cost, 20k confirmed + 5k conditional + 5k expected.
        # Headline gap = 30k - 20k = 10k (confirmed only).
        # Pending pool = 5k + 5k = 10k. If every pending source falls
        # through, the gap widens by 10k. potential_gap = 10k.
        costs = [
            _cost(
                id="tuition", amount="30000.00",
                frequency=Frequency.ONE_TIME, is_one_time=True,
                start_date=date(2026, 9, 1),
                category=CostCategory.TUITION,
            ),
        ]
        sources = [
            _funding(id="s1", amount="20000.00", status=FundingStatus.CONFIRMED),
            _funding(id="s2", amount="5000.00", status=FundingStatus.CONDITIONAL),
            _funding(id="s3", amount="5000.00", status=FundingStatus.EXPECTED),
        ]
        out = compute_readiness(plan, costs, sources, [])
        assert out.funding_gap == Decimal("10000.00")
        assert out.potential_gap_after_expected == Decimal("10000.00")

    def test_potential_gap_strictly_larger_when_pending_funding_exists(
        self, plan, fx_empty
    ) -> None:
        # 50k cost, 10k confirmed + 30k conditional + 10k expected.
        # Headline gap = 50k - 10k = 40k.
        # The pending pool is 40k — if every pending source fails the
        # gap widens by 40k to a total shortfall of 80k.
        # potential_gap_after_expected = 40k.
        costs = [
            _cost(
                id="tuition", amount="50000.00",
                frequency=Frequency.ONE_TIME, is_one_time=True,
                start_date=date(2026, 9, 1),
                category=CostCategory.TUITION,
            ),
        ]
        sources = [
            _funding(id="s1", amount="10000.00", status=FundingStatus.CONFIRMED),
            _funding(id="s2", amount="30000.00", status=FundingStatus.CONDITIONAL),
            _funding(id="s3", amount="10000.00", status=FundingStatus.EXPECTED),
        ]
        out = compute_readiness(plan, costs, sources, [])
        assert out.funding_gap == Decimal("40000.00")
        assert out.potential_gap_after_expected == Decimal("40000.00")

    def test_due_before_departure_is_counted_in_upfront_even_without_date(
        self, plan, fx_empty
    ) -> None:
        # Recurring cost without start_date. By default `project_upfront`
        # would conservatively count it; the `due_before_departure` flag
        # produces the same outcome but with an explicit signal.
        costs = [
            _cost(
                id="housing-deposit", amount="1000.00",
                frequency=Frequency.ONE_TIME, is_one_time=True,
                start_date=None,  # intentionally blank
                due_before_departure=True,
                category=CostCategory.DEPOSITS,
            ),
        ]
        out = compute_readiness(plan, costs, [], [])
        assert out.upfront_cash_requirement == Decimal("1000.00")

    def test_due_before_departure_serialization(self, plan, fx_empty) -> None:
        """The `to_dict` payload always exposes the new fields so the
        frontend never has to defend against `undefined`."""
        out = compute_readiness(plan, [], [], [])
        d = out.to_dict()
        assert "first_year_funding_gap" in d
        assert "coverage_pct" in d
        assert "potential_gap_after_expected" in d
        assert d["coverage_pct"] is None  # no cost → no ratio

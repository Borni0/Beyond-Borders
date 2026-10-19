"""Readiness orchestration: combine cost projection, funding, FX, and
classify statuses per spec §9.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Sequence

from app.services.financial.currency import CurrencyError, index_rates
from app.services.financial.money import round_money
from app.services.financial.projection import project_costs, project_upfront
from app.services.financial.types import (
    CostBreakdown,
    CostItem,
    FundingBreakdown,
    FundingSource,
    FundingStatus,
    FxRate,
    PlanContext,
    ReadinessResult,
    ReadinessStatusCode,
    StatusSet,
    YearCost,
)


def _funding_breakdown(
    plan: PlanContext,
    sources: Iterable[FundingSource],
    fx: dict[tuple[str, str], FxRate],
    upfront_window_days: int,
) -> FundingBreakdown:
    base = plan.base_currency.upper()
    confirmed = conditional = expected = unavailable = Decimal("0")
    eligible_confirmed = Decimal("0")
    eligible_with_conditional = Decimal("0")
    available_before_departure = Decimal("0")

    for src in sources:
        amount_base = round_money(
            __import__("app.services.financial.currency", fromlist=["convert"]).convert(
                src.amount, src.currency, base, fx
            ),
            base,
        )
        if src.status == FundingStatus.CONFIRMED:
            confirmed += amount_base
            eligible_confirmed += amount_base
            eligible_with_conditional += amount_base
            if src.expected_date is None or src.expected_date <= plan.start_date:
                available_before_departure += amount_base
        elif src.status == FundingStatus.CONDITIONAL:
            conditional += amount_base
            eligible_with_conditional += amount_base
        elif src.status == FundingStatus.EXPECTED:
            expected += amount_base
            if src.expected_date is not None and src.expected_date <= plan.start_date:
                available_before_departure += amount_base
        else:  # UNAVAILABLE
            unavailable += amount_base

    return FundingBreakdown(
        base_currency=base,
        confirmed_total=round_money(confirmed, base),
        conditional_total=round_money(conditional, base),
        expected_total=round_money(expected, base),
        unavailable_total=round_money(unavailable, base),
        eligible_confirmed=round_money(eligible_confirmed, base),
        eligible_with_conditional=round_money(eligible_with_conditional, base),
        available_before_departure=round_money(available_before_departure, base),
    )


def _missing_inputs(
    plan: PlanContext,
    costs: Sequence[CostItem],
    sources: Sequence[FundingSource],
    fx: dict[tuple[str, str], FxRate],
) -> list[str]:
    missing: list[str] = []
    if not costs:
        missing.append("No cost items have been added yet.")
    if not any(s.status == FundingStatus.CONFIRMED for s in sources):
        missing.append("No confirmed funding source has been entered.")

    # Any non-base currency used in costs or funding requires a rate.
    referenced: set[str] = set()
    referenced.update(c.currency for c in costs)
    referenced.update(s.currency for s in sources)
    referenced.discard(plan.base_currency.upper())
    for ccy in sorted(referenced):
        if (plan.base_currency.upper(), ccy.upper()) not in fx and (
            ccy.upper(),
            plan.base_currency.upper(),
        ) not in fx:
            missing.append(f"No FX rate entered for {plan.base_currency}/{ccy}.")
    return missing


def _statuses(
    plan: PlanContext,
    costs: Sequence[CostItem],
    sources: Sequence[FundingSource],
    breakdown_total: Decimal,
    funding: FundingBreakdown,
    funding_gap: Decimal,
    upfront_cash_gap: Decimal,
    missing_inputs: list[str],
) -> StatusSet:
    codes: list[ReadinessStatusCode] = []

    if missing_inputs:
        codes.append(ReadinessStatusCode.NEEDS_MORE_INFORMATION)
    if funding_gap > 0:
        codes.append(ReadinessStatusCode.FUNDING_GAP_IDENTIFIED)
    if upfront_cash_gap > 0:
        codes.append(ReadinessStatusCode.UPFRONT_CASH_GAP)
    if any(s.status in (FundingStatus.CONDITIONAL, FundingStatus.EXPECTED) for s in sources):
        codes.append(ReadinessStatusCode.CONDITIONAL_FUNDING)

    # Phase 1: scenarios not yet supported. Surface the chip, value false.
    # We still append so the UI knows the field exists; the UI displays
    # "Scenario data not yet available" muted when False.
    codes.append(ReadinessStatusCode.SCENARIO_SENSITIVE)

    # No modeled shortfall only if every other flag is also off and we have
    # at least some cost and confirmed funding to evaluate against.
    has_inputs = bool(costs) and any(
        s.status == FundingStatus.CONFIRMED for s in sources
    )
    if (
        has_inputs
        and funding_gap == 0
        and upfront_cash_gap == 0
        and not missing_inputs
    ):
        codes.append(ReadinessStatusCode.NO_MODELED_SHORTFALL)

    return StatusSet(codes=tuple(codes))


def compute_readiness(
    plan: PlanContext,
    costs: Sequence[CostItem],
    sources: Sequence[FundingSource],
    rates: Iterable[FxRate],
    upfront_window_days: int = 30,
) -> ReadinessResult:
    """Compute the readiness result from the given inputs.

    Same inputs → byte-identical result (Decimals serialized as strings;
    no floating-point anywhere).

    If the FX table is insufficient to convert a referenced currency, the
    computation returns a zero-amount readiness with the missing pair
    surfaced in `missing_inputs` (and the NEEDS_MORE_INFORMATION status
    flag set) instead of raising. This keeps the UI usable: the user sees
    exactly which rate they need to enter.
    """
    fx = index_rates(rates)
    try:
        breakdown = project_costs(plan, costs, fx)
        funding = _funding_breakdown(plan, sources, fx, upfront_window_days)
        upfront_req = project_upfront(plan, costs, fx, upfront_window_days)
    except CurrencyError as exc:
        # Surface the missing-pair error as a missing input so the UI can
        # prompt for the rate. We still return a structured, complete
        # ReadinessResult (with zero amounts) so the caller's contract holds.
        zero = round_money(Decimal("0"), plan.base_currency)
        statuses = StatusSet(
            codes=(
                ReadinessStatusCode.NEEDS_MORE_INFORMATION,
                ReadinessStatusCode.SCENARIO_SENSITIVE,
            )
        )
        return ReadinessResult(
            plan_id=plan.id,
            base_currency=plan.base_currency.upper(),
            breakdown=CostBreakdown(
                base_currency=plan.base_currency.upper(),
                per_year=[
                    YearCost(
                        year_index=1,
                        recurring_total=zero,
                        one_time_total=zero,
                        total=zero,
                    )
                ],
                first_year_cost=zero,
                total_projected_cost=zero,
                refundable_deposits=zero,
            ),
            funding=FundingBreakdown(
                base_currency=plan.base_currency.upper(),
            ),
            funding_gap=zero,
            funding_surplus=zero,
            upfront_cash_requirement=zero,
            upfront_cash_gap=zero,
            upfront_cash_window_days=upfront_window_days,
            statuses=statuses,
            missing_inputs=(str(exc),),
            notes=(
                "Add the missing FX rate(s) below to compute your readiness.",
            ),
            first_year_funding_gap=zero,
            coverage_pct=None,
            potential_gap_after_expected=zero,
        )

    gap = max(
        Decimal("0"),
        breakdown.total_projected_cost - funding.eligible_confirmed,
    )
    surplus = max(
        Decimal("0"),
        funding.eligible_confirmed - breakdown.total_projected_cost,
    )
    upfront_gap = max(
        Decimal("0"),
        upfront_req - funding.available_before_departure,
    )

    gap = round_money(gap, plan.base_currency)
    surplus = round_money(surplus, plan.base_currency)
    upfront_req = round_money(upfront_req, plan.base_currency)
    upfront_gap = round_money(upfront_gap, plan.base_currency)

    # ---- First-year funding gap ----
    # Funding still counts in full: we restrict only the cost side to
    # year 1. If the plan has zero first-year cost, the gap is 0.
    first_year_cost = breakdown.first_year_cost
    first_year_gap = max(
        Decimal("0"),
        first_year_cost - funding.eligible_confirmed,
    )
    first_year_gap = round_money(first_year_gap, plan.base_currency)

    # ---- Coverage % (eligible funding / total cost) ----
    # Uses eligible_with_conditional so conditional funding is visible
    # to the user without inflating the headline gap number. Returns
    # None when the denominator is zero (no costs yet) so the UI can
    # render "n/a" instead of 0/0.
    if breakdown.total_projected_cost > 0:
        coverage = (
            funding.eligible_with_conditional
            / breakdown.total_projected_cost
            * Decimal("100")
        )
        coverage_pct = coverage.quantize(Decimal("0.01"))
    else:
        coverage_pct = None

    # ---- Potential gap after expected ----
    # The amount of the projected cost that is currently bridged only
    # by conditional or expected (pending) funding. If every pending
    # source fails, the headline funding gap widens by this much.
    # When confirmed funding already covers the total cost, this is 0
    # because there's no gap to widen.
    if breakdown.total_projected_cost > funding.confirmed_total:
        potential_gap = funding.conditional_total + funding.expected_total
    else:
        potential_gap = Decimal("0")
    potential_gap = round_money(potential_gap, plan.base_currency)

    missing = _missing_inputs(plan, costs, sources, fx)
    statuses = _statuses(
        plan,
        costs,
        sources,
        breakdown.total_projected_cost,
        funding,
        gap,
        upfront_gap,
        missing,
    )

    notes: list[str] = []
    if statuses.has(ReadinessStatusCode.NO_MODELED_SHORTFALL):
        notes.append(
            "No modeled shortfall under current inputs. This is not a guarantee "
            "of affordability; verify costs, currency rates, and visa "
            "requirements before committing."
        )
    if breakdown.refundable_deposits > 0:
        notes.append(
            f"Refundable deposits of {breakdown.refundable_deposits} "
            f"{plan.base_currency} are tracked separately and are not "
            "included in the projected cost."
        )
    if statuses.has(ReadinessStatusCode.SCENARIO_SENSITIVE):
        notes.append(
            "Scenario sensitivity is not yet modeled. Phase 2 will let you "
            "stress-test exchange rates, rent, and scholarships."
        )
    if coverage_pct is not None and coverage_pct < 100:
        notes.append(
            f"Coverage is {coverage_pct}% of the projected total — the "
            "remainder is the funding gap above."
        )

    return ReadinessResult(
        plan_id=plan.id,
        base_currency=plan.base_currency.upper(),
        breakdown=breakdown,
        funding=funding,
        funding_gap=gap,
        funding_surplus=surplus,
        upfront_cash_requirement=upfront_req,
        upfront_cash_gap=upfront_gap,
        upfront_cash_window_days=upfront_window_days,
        statuses=statuses,
        missing_inputs=tuple(missing),
        notes=tuple(notes),
        first_year_funding_gap=first_year_gap,
        coverage_pct=coverage_pct,
        potential_gap_after_expected=potential_gap,
    )


__all__ = ["compute_readiness"]
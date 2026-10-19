"""Decision Studio service.

Responsibilities
----------------

* Validate that every selected plan belongs to the calling user.
* For each plan, run the **existing** readiness engine
  (``readiness_service.compute_for_plan``) and the funding-plan summary
  to gather the canonical cost / funding / upfront numbers.
* Apply a *scenario* to a *deep copy* of the plan — the original row
  is never mutated, so testing a scenario never changes a saved plan.
* Assemble the side-by-side comparison row, missing-data warnings,
  and a sorted, capped list of upcoming payment events.
* Saved-comparison CRUD with strict per-user ownership.

Everything here is deterministic, side-effect-free aside from the
explicit CRUD writes, and uses the same math as the rest of the app —
no parallel financial engine.
"""

from __future__ import annotations

import copy
import logging
import re
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models.cost_item import CostItem
from app.models.funding_source import FundingSource
from app.models.payment_event import PaymentEvent
from app.models.study_plan import StudyPlan
from app.models.study_plan_comparison import StudyPlanComparison
from app.repositories import (
    payment_event_repo,
    study_plan_comparison_repo,
    study_plan_repo,
)
from app.schemas.decision_studio import (
    CompareRequest,
    CompareResult,
    ComparisonCostMetrics,
    ComparisonFundingMetrics,
    ComparisonPaymentRow,
    ComparisonPlan,
    ComparisonRow,
    ComparisonUpfrontMetrics,
    ComparisonWarning,
    DeadlinePlanRanking,
    SavedComparisonCreate,
    SavedComparisonPublic,
    SavedComparisonUpdate,
    ScenarioAdjustment,
    ScenarioSpec,
)
from app.services import readiness_service
from app.services.financial.types import Frequency

log = logging.getLogger(__name__)


# ---------- Constants -------------------------------------------------------

CALCULATION_VERSION = "decision_studio_v1"

# Capped so the comparison table never explodes for plans with many
# recurring payment events. 30 is a comfortable upper bound for a
# 24-month plan.
PAYMENT_ROW_LIMIT = 30

# The currency regex is intentionally narrow: 3 ASCII letters. The
# schema already upper-cases on write, so this is mostly a guard
# against edge cases.
_CCY_RE = re.compile(r"^[A-Z]{3}$")


# ---------- Internal helpers ------------------------------------------------

def _money(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _normalize(value: Any) -> Any:
    """JSON-friendly coercion for Decimals / datetimes / dataclasses."""

    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "to_dict"):
        return _normalize(value.to_dict())
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    return value


def _upper(value: str | None) -> str | None:
    return value.upper() if value else None


# ---------- Scenario application -------------------------------------------

def _apply_scenario(
    plan: StudyPlan,
    payments: list[PaymentEvent],
    scenario: ScenarioSpec | None,
) -> tuple[StudyPlan, list[CostItem], list[FundingSource], list[PaymentEvent], list[str]]:
    """Return a *detached* copy of the plan with the scenario applied.

    The original plan row is not mutated. We deep-copy the children so
    scenario edits never leak back to the database. The returned
    children are detached from the session and have transient IDs, but
    the readiness service only reads the fields it needs, so passing
    them in directly is fine — the service hydrates them through
    ``readiness_service._hydrate_cost`` / ``_hydrate_funding`` which
    accept any object with the right attributes.
    """

    notes: list[str] = []
    if scenario is None or scenario.name == "baseline" or not scenario.adjustments:
        # Pure baseline. Still copy to be safe and to keep the rest of
        # the pipeline uniform.
        return (
            copy.deepcopy(plan),
            [copy.deepcopy(c) for c in plan.cost_items],
            [copy.deepcopy(s) for s in plan.funding_sources],
            [copy.deepcopy(p) for p in payments],
            notes,
        )

    # Build detached copies first.
    new_plan = copy.deepcopy(plan)
    new_costs = {c.id: copy.deepcopy(c) for c in plan.cost_items}
    new_funding = {s.id: copy.deepcopy(s) for s in plan.funding_sources}
    new_payments = [copy.deepcopy(p) for p in payments]

    for adj in scenario.adjustments:
        _apply_adjustment(new_plan, new_costs, new_funding, new_payments, adj, notes)

    notes.append(
        f"Scenario '{scenario.name}' applied with "
        f"{len(scenario.adjustments)} adjustment(s); baseline plan unchanged."
    )
    return (
        new_plan,
        list(new_costs.values()),
        list(new_funding.values()),
        new_payments,
        notes,
    )


def _apply_adjustment(
    plan: StudyPlan,
    costs: dict[str, CostItem],
    funding: dict[str, FundingSource],
    payments: list[PaymentEvent],
    adj: ScenarioAdjustment,
    notes: list[str],
) -> None:
    """Mutate a detached copy of plan data per one adjustment.

    Each branch is narrow on purpose. Anything that can't be applied
    cleanly is recorded in ``notes`` so the UI can surface it instead
    of silently dropping the user's input.
    """

    pct = _parse_pct(adj.value)

    if adj.type == "rent_increase_pct":
        _scale_categories(costs, {"accommodation", "utilities"}, pct, notes)
    elif adj.type == "tuition_increase_pct":
        # Tuition on the plan itself (Phase 1 enrichment) plus cost items
        # categorised as "tuition" — both should shift together.
        if plan.tuition_amount is not None and pct is not None:
            plan.tuition_amount = _scale_decimal(plan.tuition_amount, pct)
        _scale_categories(costs, {"tuition"}, pct, notes)
    elif adj.type == "living_expense_increase_pct":
        # Broader day-to-day cost shock: rent + utilities plus core living
        # costs that students often experience as a single expense basket.
        _scale_categories(
            costs,
            {"accommodation", "food", "transport", "utilities", "insurance", "personal"},
            pct,
            notes,
        )
    elif adj.type == "scholarship_reduction_pct":
        # A scholarship reduction shrinks every funding source with type
        # "scholarship" and status confirmed / conditional. We treat
        # ``pct`` as the *amount by which* to shrink (e.g. 25 means
        # -25% of the source amount).
        if pct is None:
            notes.append("scholarship_reduction_pct: missing value, skipped.")
            return
        delta = -pct
        for src in funding.values():
            if src.funding_type == "scholarship" and src.status in {
                "confirmed",
                "conditional",
            }:
                src.amount = _scale_decimal(src.amount, delta)
    elif adj.type == "family_support_delay_days":
        # Push the ``expected_date`` of every family-support source
        # forward by N days. The engine treats sources without an
        # ``expected_date`` as not-available-before-departure, so this
        # is the most honest interpretation of "delayed".
        days = _parse_int(adj.value)
        if days is None or days <= 0:
            notes.append("family_support_delay_days: missing or zero, skipped.")
            return
        for src in funding.values():
            if src.funding_type == "family" and src.expected_date is not None:
                src.expected_date = src.expected_date.fromordinal(
                    src.expected_date.toordinal() + days
                )
    elif adj.type == "fx_shift_pct":
        # The engine re-converts at request time using the user's stored
        # FX rates, so the only honest way to model an FX shift is to
        # *bump* the rates. Since scenarios must not mutate the user's
        # stored data, we instead leave a note and let the UI flag that
        # this scenario is informational only.
        notes.append(
            "fx_shift_pct: scenarios cannot rewrite stored FX rates; "
            "use the FX page to model currency moves instead."
        )
    elif adj.type == "deposit_change":
        # Signed delta applied to every cost in the "deposits" category.
        delta = _money(adj.value)
        if delta == 0:
            notes.append("deposit_change: zero delta, skipped.")
            return
        for c in costs.values():
            if c.category == "deposits":
                c.amount = max(Decimal("0"), c.amount + delta)
    elif adj.type == "custom_note":
        if adj.note:
            notes.append(f"Note: {adj.note}")
    else:
        notes.append(f"Unknown adjustment type '{adj.type}', skipped.")


def _scale_decimal(value: Decimal, pct: Decimal | None) -> Decimal:
    if pct is None:
        return value
    # Negative pct reduces the value; positive increases.
    factor = Decimal("1") + (pct / Decimal("100"))
    if factor < 0:
        factor = Decimal("0")
    return (value * factor).quantize(Decimal("0.0001"))


def _scale_categories(
    costs: dict[str, CostItem],
    categories: set[str],
    pct: Decimal | None,
    notes: list[str],
) -> None:
    if pct is None:
        notes.append("percentage adjustment: missing value, skipped.")
        return
    affected = 0
    for c in costs.values():
        if c.category in categories:
            c.amount = _scale_decimal(c.amount, pct)
            affected += 1
    if affected == 0:
        notes.append(
            f"percentage adjustment: no items in {sorted(categories)}."
        )


def _parse_pct(raw: str | None) -> Decimal | None:
    if raw is None:
        return None
    try:
        v = Decimal(str(raw).replace("%", "").strip())
    except (InvalidOperation, ValueError):
        return None
    if v < Decimal("-100") or v > Decimal("1000"):
        return None
    return v


def _parse_int(raw: str | None) -> int | None:
    if raw is None:
        return None
    try:
        return int(Decimal(str(raw).strip()))
    except (InvalidOperation, ValueError):
        return None


# ---------- Comparison assembly --------------------------------------------

@dataclass
class _PlanInputs:
    plan: StudyPlan
    costs: list[CostItem]
    funding: list[FundingSource]
    payments: list[PaymentEvent]
    scenario_name: str
    scenario_notes: list[str]


def _resolve_inputs(
    db: Session,
    user_id: str,
    request: CompareRequest,
) -> list[_PlanInputs]:
    """Load + scenario-apply every selected plan.

    Raises ``ApiError(NOT_FOUND)`` if a plan is missing or owned by
    someone else. We deliberately use 404 (not 403) so we don't leak
    the existence of other users' plans.
    """

    plan_ids = list(request.study_plan_ids)
    scenarios_by_plan: dict[str, ScenarioSpec] = {}
    if request.scenarios:
        for sc in request.scenarios:
            scenarios_by_plan[sc.plan_id] = sc

    out: list[_PlanInputs] = []
    for plan_id in plan_ids:
        plan = study_plan_repo.get_plan(db, user_id, plan_id)
        if plan is None:
            raise ApiError(
                "NOT_FOUND",
                f"Plan '{plan_id}' not found or not yours.",
                http_status=404,
            )
        scenario = scenarios_by_plan.get(plan_id)
        # Load payments scoped to the user/plan (StudyPlan ORM has no
        # relationship to PaymentEvent so we go through the repo).
        payments = list(
            payment_event_repo.list_events(db, user_id, plan_id=plan_id)
        )
        detached_plan, costs, funding, payments, notes = _apply_scenario(
            plan, payments, scenario
        )
        out.append(
            _PlanInputs(
                plan=detached_plan,
                costs=costs,
                funding=funding,
                payments=payments,
                scenario_name=(scenario.name if scenario else "baseline"),
                scenario_notes=notes,
            )
        )
    return out


def _classify_completeness(
    inputs: _PlanInputs, missing_inputs: tuple[str, ...]
) -> tuple[str, list[str]]:
    reasons: list[str] = list(missing_inputs)
    if not inputs.costs:
        reasons.append("No cost items entered for this plan.")
    if not inputs.funding:
        reasons.append("No funding sources entered for this plan.")
    if not reasons:
        return "complete", []
    if any("No cost" in r or "No funding" in r for r in reasons):
        return "missing", reasons
    return "partial", reasons


def _per_plan_metrics(
    db: Session,
    user_id: str,
    inputs: _PlanInputs,
    upfront_window_days: int,
) -> tuple[ComparisonRow, list[ComparisonWarning]]:
    """Build one ComparisonRow by running the existing engine."""

    # The readiness service expects a StudyPlan ORM row with its
    # children attached. We rebuild a transient in-memory plan object
    # so the scenario-applied children are picked up.
    transient = _TransientPlan(
        id=inputs.plan.id,
        user_id=inputs.plan.user_id,
        name=inputs.plan.name,
        base_currency=inputs.plan.base_currency,
        start_date=inputs.plan.start_date,
        duration_months=inputs.plan.duration_months,
        destination_country=getattr(inputs.plan, "destination_country", None),
        institution_name=getattr(inputs.plan, "institution_name", None),
        program_name=getattr(inputs.plan, "program_name", None),
        city=getattr(inputs.plan, "city", None),
        tuition_amount=getattr(inputs.plan, "tuition_amount", None),
        tuition_currency=getattr(inputs.plan, "tuition_currency", None),
        home_currency=getattr(inputs.plan, "home_currency", None),
        cost_items=inputs.costs,
        funding_sources=inputs.funding,
    )

    result = readiness_service.compute_for_plan(
        db,
        user_id=user_id,
        plan=transient,  # type: ignore[arg-type]
        upfront_window_days=upfront_window_days,
    )
    rd = result.to_dict()

    funding = rd["funding"]
    breakdown = rd["breakdown"]
    base = str(breakdown["base_currency"])

    # ``displayed_period`` is the plan's full duration; we don't try to
    # clamp to a common period (the spec asks us to disclose different
    # durations instead).
    plan_row = ComparisonPlan(
        id=inputs.plan.id,
        name=inputs.plan.name,
        destination_country=getattr(inputs.plan, "destination_country", None),
        institution_name=getattr(inputs.plan, "institution_name", None),
        program_name=getattr(inputs.plan, "program_name", None),
        city=getattr(inputs.plan, "city", None),
        base_currency=base,
        start_date=inputs.plan.start_date,
        duration_months=inputs.plan.duration_months,
        end_date=inputs.plan.end_date,
        scenario_name=inputs.scenario_name,
        data_completeness="complete",  # patched below
        missing_inputs=[],
    )
    completeness, missing_reasons = _classify_completeness(
        inputs, tuple(rd.get("missing_inputs") or ())
    )
    plan_row.data_completeness = completeness
    plan_row.missing_inputs = list(missing_reasons) + list(inputs.scenario_notes)

    cost_metrics = ComparisonCostMetrics(
        base_currency=base,
        total_projected_cost=str(breakdown["total_projected_cost"]),
        first_year_cost=str(breakdown["first_year_cost"]),
        refundable_deposits=str(breakdown["refundable_deposits"]),
        per_category={k: str(v) for k, v in breakdown["per_category"].items()},
        per_year=list(breakdown["per_year"]),
        cost_for_displayed_period=str(breakdown["total_projected_cost"]),
        displayed_period_months=inputs.plan.duration_months,
    )
    funding_metrics = ComparisonFundingMetrics(
        base_currency=base,
        confirmed_total=str(funding["confirmed_total"]),
        conditional_total=str(funding["conditional_total"]),
        expected_total=str(funding["expected_total"]),
        unavailable_total=str(funding["unavailable_total"]),
        eligible_confirmed=str(funding["eligible_confirmed"]),
        eligible_with_conditional=str(funding["eligible_with_conditional"]),
        funding_gap=str(rd["funding_gap"]),
        funding_surplus=str(rd["funding_surplus"]),
        available_before_departure=str(funding["available_before_departure"]),
    )
    upfront_metrics = ComparisonUpfrontMetrics(
        base_currency=base,
        upfront_window_days=int(rd["upfront_cash_window_days"]),
        upfront_cash_requirement=str(rd["upfront_cash_requirement"]),
        upfront_cash_gap=str(rd["upfront_cash_gap"]),
    )

    # Payments: cap to a reasonable number, sort by due date, and tag
    # the earliest non-paid, non-cancelled event.
    payment_rows = _payment_rows_for(inputs.payments)
    earliest = next(
        (
            r
            for r in payment_rows
            if r.display_status not in {"paid", "cancelled"}
        ),
        None,
    )

    row = ComparisonRow(
        plan=plan_row,
        cost=cost_metrics,
        funding=funding_metrics,
        upfront=upfront_metrics,
        earliest_payment=earliest,
        payments=payment_rows[:PAYMENT_ROW_LIMIT],
    )

    warnings: list[ComparisonWarning] = []
    if not inputs.costs:
        warnings.append(
            ComparisonWarning(
                code="missing_costs",
                message="No cost items recorded for one or more plans.",
                plan_ids=[inputs.plan.id],
            )
        )
    if not inputs.funding:
        warnings.append(
            ComparisonWarning(
                code="missing_funding",
                message="No funding sources recorded for one or more plans.",
                plan_ids=[inputs.plan.id],
            )
        )
    if rd.get("missing_inputs"):
        warnings.append(
            ComparisonWarning(
                code="incomplete_data",
                message="Readiness engine flagged missing inputs.",
                plan_ids=[inputs.plan.id],
            )
        )
    return row, warnings


def _payment_rows_for(events: Iterable[PaymentEvent]) -> list[ComparisonPaymentRow]:
    rows: list[ComparisonPaymentRow] = []
    today = date.today()
    for ev in events:
        stored = (ev.status or "planned").lower()
        due = ev.due_date
        if stored in {"paid", "cancelled"}:
            display = stored
        elif isinstance(due, date) and due < today:
            display = "overdue"
        else:
            display = stored
        rows.append(
            ComparisonPaymentRow(
                id=ev.id,
                title=ev.title or "",
                category=ev.category,
                amount=str(_money(ev.amount)),
                currency=_upper(ev.currency) or "",
                due_date=due if isinstance(due, date) else None,
                display_status=display,
            )
        )
    rows.sort(
        key=lambda r: (
            r.due_date is None,
            r.due_date or date.max,
            r.due_date is None,
        )
    )
    return rows


def _deadline_analysis_for_plan(
    *,
    plan_id: str,
    funding_sources: Sequence[FundingSource],
    payment_events: Sequence[PaymentEvent],
    base_currency: str,
) -> DeadlinePlanRanking:
    """Rank a plan by the earliest date when cumulative payment demand exceeds
    cumulative funding that is either confirmed or expected by that date."""

    if not payment_events:
        return DeadlinePlanRanking(
            plan_id=plan_id,
            rank=1,
            score=0,
            status="no_payment_data",
            rationale=(
                "No payment deadlines were entered, so the plan cannot be ranked "
                "on cash timing yet."
            ),
        )

    relevant_funding: list[FundingSource] = []
    for src in funding_sources:
        if src.status in {"confirmed", "expected", "conditional"}:
            relevant_funding.append(src)

    due_buckets: dict[date, Decimal] = {}
    for ev in payment_events:
        if not isinstance(ev.due_date, date):
            continue
        due_buckets[ev.due_date] = due_buckets.get(ev.due_date, Decimal("0")) + _money(ev.amount)

    if not due_buckets:
        return DeadlinePlanRanking(
            plan_id=plan_id,
            rank=1,
            score=0,
            status="no_payment_data",
            rationale=(
                "No valid payment due dates were found, so the plan cannot be "
                "deadline-ranked."
            ),
        )

    cumulative_due = Decimal("0")
    shortfall_date: date | None = None
    shortfall_amount: Decimal | None = None
    funded_by_deadline: Decimal = Decimal("0")
    required_by_deadline: Decimal = Decimal("0")

    for due_date in sorted(due_buckets):
        cumulative_due += due_buckets[due_date]
        available_by_date = Decimal("0")
        for src in relevant_funding:
            expected = src.expected_date
            if src.status == "confirmed" and (expected is None or expected <= due_date):
                available_by_date += _money(src.amount)
            elif src.status in {"expected", "conditional"} and expected is not None and expected <= due_date:
                available_by_date += _money(src.amount)
        if available_by_date < cumulative_due:
            shortfall_date = due_date
            shortfall_amount = cumulative_due - available_by_date
            funded_by_deadline = available_by_date
            required_by_deadline = cumulative_due
            break
        funded_by_deadline = available_by_date
        required_by_deadline = cumulative_due

    if shortfall_date is None:
        return DeadlinePlanRanking(
            plan_id=plan_id,
            rank=1,
            score=100,
            status="no_shortfall",
            earliest_shortfall_date=None,
            shortfall_amount="0",
            funded_by_deadline=str(funded_by_deadline or Decimal("0")),
            required_by_deadline=str(required_by_deadline or Decimal("0")),
            rationale=(
                "Confirmed and expected funding arrives before every known payment "
                "deadline, so the plan remains cash-positive on schedule."
            ),
        )

    return DeadlinePlanRanking(
        plan_id=plan_id,
        rank=1,
        score=max(0, 100 - int(shortfall_amount / Decimal("1000"))),
        status="shortfall",
        earliest_shortfall_date=shortfall_date,
        shortfall_amount=str(shortfall_amount),
        funded_by_deadline=str(funded_by_deadline),
        required_by_deadline=str(required_by_deadline),
        rationale=(
            f"Earliest cash shortfall hits {shortfall_date.isoformat()}: "
            f"{shortfall_amount} short when {funded_by_deadline} is available "
            f"against {required_by_deadline} due."
        ),
    )


def _annotate_deadline_metrics(
    row: ComparisonRow,
    *,
    funding_sources: Sequence[FundingSource],
    payment_events: Sequence[PaymentEvent],
    base_currency: str,
) -> ComparisonRow:
    ranking = _deadline_analysis_for_plan(
        plan_id=row.plan.id,
        funding_sources=funding_sources,
        payment_events=payment_events,
        base_currency=base_currency,
    )
    row.deadline_status = ranking.status
    row.earliest_shortfall_date = ranking.earliest_shortfall_date
    row.shortfall_amount = ranking.shortfall_amount
    row.deadline_rationale = ranking.rationale
    return row


class _TransientPlan:
    """Lightweight stand-in for ``StudyPlan`` for the readiness service.

    The service uses ``plan.cost_items`` and ``plan.funding_sources`` —
    nothing else — so any object with those attributes will do.
    """

    def __init__(
        self,
        *,
        id: str,
        user_id: str,
        name: str,
        base_currency: str,
        start_date: date,
        duration_months: int,
        destination_country: str | None = None,
        institution_name: str | None = None,
        program_name: str | None = None,
        city: str | None = None,
        tuition_amount: Decimal | None = None,
        tuition_currency: str | None = None,
        home_currency: str | None = None,
        cost_items: Sequence[CostItem] | None = None,
        funding_sources: Sequence[FundingSource] | None = None,
    ) -> None:
        self.id = id
        self.user_id = user_id
        self.name = name
        self.base_currency = base_currency
        self.start_date = start_date
        self.duration_months = duration_months
        self.end_date = study_plan_repo.end_date_for(start_date, duration_months)
        self.destination_country = destination_country
        self.institution_name = institution_name
        self.program_name = program_name
        self.city = city
        self.tuition_amount = tuition_amount
        self.tuition_currency = tuition_currency
        self.home_currency = home_currency
        self.cost_items = list(cost_items or [])
        self.funding_sources = list(funding_sources or [])


# ---------- Public entry point ---------------------------------------------

def compare(
    db: Session,
    *,
    user_id: str,
    request: CompareRequest,
    comparison_id: str | None = None,
) -> CompareResult:
    """Run the comparison pipeline and return the side-by-side result."""

    inputs = _resolve_inputs(db, user_id, request)

    rows: list[ComparisonRow] = []
    warnings: list[ComparisonWarning] = []
    for plan_inputs in inputs:
        row, warns = _per_plan_metrics(
            db, user_id, plan_inputs, request.upfront_window_days
        )
        row = _annotate_deadline_metrics(
            row,
            funding_sources=plan_inputs.funding,
            payment_events=plan_inputs.payments,
            base_currency=row.cost.base_currency,
        )
        rows.append(row)
        warnings.extend(warns)

    warnings.extend(_cross_plan_warnings(rows))
    deadline_rankings = _rank_plans_by_deadline(rows)
    recommended = deadline_rankings[0].plan_id if deadline_rankings else None

    return CompareResult(
        comparison_id=comparison_id,
        plans=rows,
        warnings=warnings,
        generated_at=datetime.now(timezone.utc),
        calculation_version=CALCULATION_VERSION,
        recommended_plan_id=recommended,
        winner=recommended,
        deadline_rankings=deadline_rankings,
        deadline_analysis=deadline_rankings,
        ranked_plans=sorted(rows, key=lambda r: next((x.rank for x in deadline_rankings if x.plan_id == r.plan.id), 999)),
    )


def _rank_plans_by_deadline(rows: Sequence[ComparisonRow]) -> list[DeadlinePlanRanking]:
    """Return a reproducible ranking ordered by deadline feasibility."""

    ranked: list[DeadlinePlanRanking] = []
    for row in rows:
        deadline_amount = Decimal(str(row.shortfall_amount or "0"))
        score = 100 if row.deadline_status == "no_shortfall" else max(0, 100 - int(deadline_amount / Decimal("1000")))
        if row.deadline_status == "no_payment_data":
            score = 0
        ranked.append(
            DeadlinePlanRanking(
                plan_id=row.plan.id,
                rank=1,
                score=score,
                status=row.deadline_status or "no_payment_data",
                earliest_shortfall_date=row.earliest_shortfall_date,
                shortfall_amount=row.shortfall_amount,
                rationale=row.deadline_rationale or "No deadline rationale available.",
            )
        )

    ranked.sort(
        key=lambda r: (
            0 if r.status == "no_shortfall" else 1 if r.status == "shortfall" else 2,
            r.earliest_shortfall_date is None,
            r.earliest_shortfall_date or date.max,
            r.shortfall_amount is None,
            Decimal(str(r.shortfall_amount or "0")),
            -r.score,
        ),
        reverse=False,
    )

    for idx, item in enumerate(ranked, start=1):
        item.rank = idx
    return ranked


def _cross_plan_warnings(rows: Sequence[ComparisonRow]) -> list[ComparisonWarning]:
    """Plan-level warnings that only make sense when comparing ≥2 plans."""

    out: list[ComparisonWarning] = []
    if len(rows) < 2:
        return out

    currencies = {r.cost.base_currency for r in rows}
    if len(currencies) > 1:
        out.append(
            ComparisonWarning(
                code="different_currencies",
                message=(
                    "Plans report in different base currencies. Totals are not "
                    "directly comparable until you normalise."
                ),
                plan_ids=[r.plan.id for r in rows],
            )
        )
    durations = {r.plan.duration_months for r in rows}
    if len(durations) > 1:
        out.append(
            ComparisonWarning(
                code="different_durations",
                message=(
                    "Plans have different durations; totals are over different "
                    "time horizons."
                ),
                plan_ids=[r.plan.id for r in rows],
            )
        )

    has_no_payments = all(not r.payments for r in rows)
    if has_no_payments:
        out.append(
            ComparisonWarning(
                code="no_known_payments",
                message="No payment events recorded for any of the selected plans.",
                plan_ids=[r.plan.id for r in rows],
            )
        )
    return out


# ---------- Saved comparison CRUD ------------------------------------------

def _validate_plan_ids_for_user(
    db: Session, user_id: str, plan_ids: Sequence[str]
) -> None:
    if not 2 <= len(plan_ids) <= 3:
        raise ApiError(
            "VALIDATION_ERROR",
            "A comparison must contain 2 or 3 plans.",
            http_status=400,
        )
    if len(set(plan_ids)) != len(plan_ids):
        raise ApiError(
            "VALIDATION_ERROR",
            "Plan IDs must be unique within a comparison.",
            http_status=400,
        )
    for pid in plan_ids:
        if study_plan_repo.get_plan(db, user_id, pid) is None:
            raise ApiError(
                "NOT_FOUND",
                f"Plan '{pid}' not found or not yours.",
                http_status=404,
            )


def save_comparison(
    db: Session,
    *,
    user_id: str,
    body: SavedComparisonCreate,
) -> SavedComparisonPublic:
    _validate_plan_ids_for_user(db, user_id, body.study_plan_ids)
    scenarios_payload = (
        [s.model_dump() for s in body.scenarios] if body.scenarios else None
    )
    row = study_plan_comparison_repo.create_comparison(
        db,
        user_id=user_id,
        name=body.name,
        selected_plan_ids=list(body.study_plan_ids),
        scenarios=scenarios_payload,
    )
    db.commit()
    return _public(row)


def list_saved_comparisons(
    db: Session, *, user_id: str
) -> list[SavedComparisonPublic]:
    rows = study_plan_comparison_repo.list_comparisons(db, user_id)
    return [_public(r) for r in rows]


def get_saved_comparison(
    db: Session, *, user_id: str, comparison_id: str
) -> tuple[SavedComparisonPublic, CompareResult]:
    row = study_plan_comparison_repo.get_comparison(db, user_id, comparison_id)
    if row is None:
        raise ApiError(
            "NOT_FOUND",
            "Comparison not found.",
            http_status=404,
        )
    raw = study_plan_comparison_repo.as_dict(row)
    selected = list(raw["selected_plan_ids"] or [])
    scenarios = _coerce_scenarios(raw["scenarios"])
    request = CompareRequest(
        study_plan_ids=selected,
        scenarios=scenarios,
    )
    result = compare(db, user_id=user_id, request=request, comparison_id=row.id)
    return _public(row), result


def update_saved_comparison(
    db: Session,
    *,
    user_id: str,
    comparison_id: str,
    body: SavedComparisonUpdate,
) -> SavedComparisonPublic:
    row = study_plan_comparison_repo.get_comparison(db, user_id, comparison_id)
    if row is None:
        raise ApiError(
            "NOT_FOUND",
            "Comparison not found.",
            http_status=404,
        )
    if body.study_plan_ids is not None:
        _validate_plan_ids_for_user(db, user_id, body.study_plan_ids)
    scenarios_payload: list | None | object = ...  # sentinel
    if body.scenarios is not None:
        scenarios_payload = [s.model_dump() for s in body.scenarios]
    elif "scenarios" in body.model_fields_set and body.scenarios is None:
        scenarios_payload = None
    study_plan_comparison_repo.update_comparison(
        db,
        row,
        name=body.name,
        selected_plan_ids=list(body.study_plan_ids) if body.study_plan_ids is not None else None,
        scenarios=scenarios_payload if scenarios_payload is not ... else None,
    )
    db.commit()
    return _public(row)


def delete_saved_comparison(
    db: Session, *, user_id: str, comparison_id: str
) -> None:
    row = study_plan_comparison_repo.get_comparison(db, user_id, comparison_id)
    if row is None:
        raise ApiError(
            "NOT_FOUND",
            "Comparison not found.",
            http_status=404,
        )
    study_plan_comparison_repo.delete_comparison(db, row)
    db.commit()


# ---------- Projection helpers --------------------------------------------

def _public(row: StudyPlanComparison) -> SavedComparisonPublic:
    # The column is JSONB on Postgres and Text on SQLite; go through the
    # repo's normaliser so we never get the raw JSON string back.
    selected = study_plan_comparison_repo._coerce_json(row.selected_plan_ids)
    if not isinstance(selected, list):
        selected = []
    scenarios = _coerce_scenarios(
        study_plan_comparison_repo._coerce_json(row.scenarios)
    )
    return SavedComparisonPublic(
        id=row.id,
        user_id=row.user_id,
        name=row.name,
        study_plan_ids=[str(x) for x in selected],
        scenarios=scenarios,
        calculation_version=row.calculation_version,
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
    )


def _coerce_scenarios(raw: Any) -> list[ScenarioSpec] | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        import json as _json

        try:
            raw = _json.loads(raw)
        except _json.JSONDecodeError:
            return None
    if not isinstance(raw, list):
        return None
    out: list[ScenarioSpec] = []
    for item in raw:
        try:
            out.append(ScenarioSpec.model_validate(item))
        except Exception as exc:  # noqa: BLE001
            # Skip malformed entries; the user can re-save with valid ones.
            # Logged at debug so it never leaks to the user.
            from app.core.logging import get_logger

            get_logger(__name__).debug(
                "scenario_skip_malformed", error=str(exc)
            )
    return out


__all__ = [
    "CALCULATION_VERSION",
    "compare",
    "save_comparison",
    "list_saved_comparisons",
    "get_saved_comparison",
    "update_saved_comparison",
    "delete_saved_comparison",
    "Frequency",  # re-export for any future scenario extension
]


# Tiny helper used in tests / by routes that want a stable request id.
def new_request_id() -> str:
    return uuid.uuid4().hex

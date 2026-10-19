"""Stress Test service.

Models the impact of an FX shock, rent increase, scholarship cut, family
support delay, deposit change, or free-form note on a single plan, and
returns the baseline-vs-scenario deltas in the plan's base currency.

The math reuses ``readiness_service.compute_for_plan`` and the same
scenario-application engine used by Decision Studio, so a stress test
and a comparison cannot disagree about what a given set of adjustments
means.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.repositories import (
    payment_event_repo,
    stress_scenario_repo,
    study_plan_repo,
)
from app.schemas.decision_studio import ScenarioAdjustment, ScenarioSpec
from app.schemas.stress_test import (
    StressRunRequest,
    StressRunResult,
    StressScenarioCreate,
    StressScenarioPublic,
    StressScenarioUpdate,
    _Delta,
)
from app.services import decision_studio_service, readiness_service

log = logging.getLogger(__name__)


# ---------- Constants -------------------------------------------------------

CALCULATION_VERSION = "stress_test_v1"

# Recognised scenario_key presets — the UI uses these to render a
# description + a default adjustment. New presets can be added here
# without a schema change because ``adjustments`` is stored as JSON.
SCENARIO_KEYS: dict[str, dict[str, object]] = {
    "rent_shock": {
        "label": "Rent shock",
        "description": (
            "Increase accommodation and utility costs by 25% to model a "
            "sudden rent hike or utility surge."
        ),
        "default_adjustment": {
            "type": "rent_increase_pct",
            "value": "25",
        },
    },
    "scholarship_cut": {
        "label": "Scholarship cut",
        "description": (
            "Reduce every confirmed or conditional scholarship by 25% to "
            "model a partial loss of an award."
        ),
        "default_adjustment": {
            "type": "scholarship_reduction_pct",
            "value": "25",
        },
    },
    "tuition_shock": {
        "label": "Tuition shock",
        "description": (
            "Increase tuition by 25% to model a fee hike, surcharge, or "
            "unexpected program cost change."
        ),
        "default_adjustment": {
            "type": "tuition_increase_pct",
            "value": "25",
        },
    },
    "living_expense_shock": {
        "label": "Living expense shock",
        "description": (
            "Increase day-to-day living costs by 20% to model a rent, food, "
            "transport, utility, or insurance spike."
        ),
        "default_adjustment": {
            "type": "living_expense_increase_pct",
            "value": "20",
        },
    },
    "fx_shock": {
        "label": "FX shock (informational)",
        "description": (
            "Record a 10% adverse currency move. The scenario is "
            "informational only because stored FX rates are not rewritten."
        ),
        "default_adjustment": {
            "type": "fx_shift_pct",
            "value": "10",
        },
    },
    "family_delay": {
        "label": "Family support delay",
        "description": (
            "Delay every family-support funding source by 60 days, "
            "modelling a late wire from home."
        ),
        "default_adjustment": {
            "type": "family_support_delay_days",
            "value": "60",
        },
    },
    "custom": {
        "label": "Custom scenario",
        "description": "Build your own combination of adjustments.",
        "default_adjustment": {"type": "custom_note", "note": ""},
    },
}


# ---------- Scenario CRUD ---------------------------------------------------

def _to_public(row) -> StressScenarioPublic:  # type: ignore[no-untyped-def]
    d = stress_scenario_repo.as_dict(row)
    return StressScenarioPublic(**d)


def list_scenarios(
    db: Session, user_id: str, plan_id: str | None = None
) -> list[StressScenarioPublic]:
    rows = stress_scenario_repo.list_scenarios(db, user_id, plan_id=plan_id)
    return [_to_public(r) for r in rows]


def create_scenario(
    db: Session, user_id: str, body: StressScenarioCreate
) -> StressScenarioPublic:
    if body.scenario_key not in SCENARIO_KEYS:
        raise ApiError(
            "VALIDATION_ERROR",
            f"scenario_key must be one of {sorted(SCENARIO_KEYS)}.",
            http_status=422,
        )
    if body.plan_id is not None:
        plan = study_plan_repo.get_plan(db, user_id, body.plan_id)
        if plan is None:
            raise ApiError("NOT_FOUND", "Plan not found.", http_status=404)
    payload = body.model_dump(mode="json")
    row = stress_scenario_repo.create_scenario(
        db,
        user_id=user_id,
        name=payload["name"],
        scenario_key=payload["scenario_key"],
        adjustments=payload.get("adjustments") or [],
        plan_id=payload.get("plan_id"),
        notes=payload.get("notes"),
    )
    return _to_public(row)


def update_scenario(
    db: Session, user_id: str, scenario_id: str, body: StressScenarioUpdate
) -> StressScenarioPublic:
    row = stress_scenario_repo.get_scenario(db, user_id, scenario_id)
    if row is None:
        raise ApiError("NOT_FOUND", "Scenario not found.", http_status=404)
    payload = body.model_dump(mode="json", exclude_unset=True)
    if "scenario_key" in payload and payload["scenario_key"] not in SCENARIO_KEYS:
        raise ApiError(
            "VALIDATION_ERROR",
            f"scenario_key must be one of {sorted(SCENARIO_KEYS)}.",
            http_status=422,
        )
    if "plan_id" in payload and payload["plan_id"] is not None:
        plan = study_plan_repo.get_plan(db, user_id, payload["plan_id"])
        if plan is None:
            raise ApiError("NOT_FOUND", "Plan not found.", http_status=404)
    # Drop keys that map to None so we can detect "clear the value"
    # explicitly with the empty string.
    cleaned = {k: v for k, v in payload.items() if v is not None}
    if "adjustments" in cleaned and cleaned["adjustments"] is None:
        cleaned.pop("adjustments")
    if "notes" in payload and payload["notes"] is None:
        cleaned["notes"] = None
    row = stress_scenario_repo.update_scenario(db, row, **cleaned)
    return _to_public(row)


def delete_scenario(db: Session, user_id: str, scenario_id: str) -> None:
    row = stress_scenario_repo.get_scenario(db, user_id, scenario_id)
    if row is None:
        raise ApiError("NOT_FOUND", "Scenario not found.", http_status=404)
    stress_scenario_repo.delete_scenario(db, row)


# ---------- Run ------------------------------------------------------------

def _wrap_plan_with_scenario(plan, payments, scenario: ScenarioSpec | None):  # type: ignore[no-untyped-def]
    """Return a transient ORM-like plan with scenario-applied children.

    Re-uses ``decision_studio_service._apply_scenario`` so the
    semantics of every adjustment are identical between the two
    features.
    """
    detached_plan, costs, funding, payments, notes = (
        decision_studio_service._apply_scenario(plan, payments, scenario)
    )
    return detached_plan, costs, funding, payments, notes


def _build_transient(plan, costs, funding):  # type: ignore[no-untyped-def]
    """Reuse the Decision Studio transient wrapper so the readiness
    service accepts our detached copies."""
    return decision_studio_service._TransientPlan(
        id=plan.id,
        user_id=plan.user_id,
        name=plan.name,
        base_currency=plan.base_currency,
        start_date=plan.start_date,
        duration_months=plan.duration_months,
        destination_country=getattr(plan, "destination_country", None),
        institution_name=getattr(plan, "institution_name", None),
        program_name=getattr(plan, "program_name", None),
        city=getattr(plan, "city", None),
        tuition_amount=getattr(plan, "tuition_amount", None),
        tuition_currency=getattr(plan, "tuition_currency", None),
        home_currency=getattr(plan, "home_currency", None),
        cost_items=costs,
        funding_sources=funding,
    )


def _delta(baseline: str, scenario: str) -> _Delta:
    b = Decimal(str(baseline))
    s = Decimal(str(scenario))
    return _Delta(baseline=str(b), scenario=str(s), delta=str(s - b))


def run_scenario(
    db: Session, user_id: str, body: StressRunRequest
) -> StressRunResult:
    plan = study_plan_repo.get_plan(db, user_id, body.plan_id)
    if plan is None:
        raise ApiError(
            "NOT_FOUND",
            f"Plan '{body.plan_id}' not found or not yours.",
            http_status=404,
        )

    # Resolve the adjustments to apply.
    adjustments: list[ScenarioAdjustment]
    scenario_id: str | None = None
    scenario_name = body.scenario_name or "baseline"
    if body.scenario_id is not None:
        row = stress_scenario_repo.get_scenario(db, user_id, body.scenario_id)
        if row is None:
            raise ApiError(
                "NOT_FOUND", "Scenario not found.", http_status=404
            )
        scenario_id = row.id
        scenario_name = row.name
        raw = stress_scenario_repo.as_dict(row)["adjustments"]
        adjustments = [ScenarioAdjustment(**a) for a in (raw or [])]
    else:
        adjustments = list(body.adjustments or [])

    payments = list(
        payment_event_repo.list_events(db, user_id, plan_id=plan.id)
    )

    # ---- Baseline run ----
    base_transient = _build_transient(plan, list(plan.cost_items), list(plan.funding_sources))
    baseline_result = readiness_service.compute_for_plan(
        db, user_id=user_id, plan=base_transient,  # type: ignore[arg-type]
        upfront_window_days=body.upfront_window_days,
    )
    baseline_dict = baseline_result.to_dict()

    # ---- Scenario run ----
    # Decision Studio treats the literal name ``"baseline"`` as a
    # short-circuit for "no adjustments" — we never want that here, so
    # always pass a non-baseline name whenever we have adjustments.
    if adjustments and (scenario_name == "baseline" or not scenario_name):
        scenario_spec_name = "Stress test scenario"
    else:
        scenario_spec_name = scenario_name
    scenario_spec = ScenarioSpec(
        plan_id=plan.id,
        name=scenario_spec_name,
        adjustments=adjustments,
        note=None,
    )
    detached_plan, scen_costs, scen_funding, _payments, scen_notes = (
        _wrap_plan_with_scenario(plan, payments, scenario_spec)
    )
    scen_transient = _build_transient(detached_plan, scen_costs, scen_funding)
    scen_result = readiness_service.compute_for_plan(
        db, user_id=user_id, plan=scen_transient,  # type: ignore[arg-type]
        upfront_window_days=body.upfront_window_days,
    )
    scen_dict = scen_result.to_dict()

    # ---- Build the deltas ----
    def get(d: dict, *path: str) -> str:  # type: ignore[type-arg]
        cur: object = d
        for key in path:
            cur = cur[key] if isinstance(cur, dict) else getattr(cur, key, None)  # type: ignore[index]
        return str(cur) if cur is not None else "0"

    return StressRunResult(
        plan_id=plan.id,
        base_currency=str(baseline_dict["base_currency"]),
        scenario_id=scenario_id,
        scenario_name=scenario_name,
        upfront_window_days=body.upfront_window_days,
        funding_gap=_delta(
            get(baseline_dict, "funding_gap"),
            get(scen_dict, "funding_gap"),
        ),
        funding_surplus=_delta(
            get(baseline_dict, "funding_surplus"),
            get(scen_dict, "funding_surplus"),
        ),
        upfront_cash_requirement=_delta(
            get(baseline_dict, "upfront_cash_requirement"),
            get(scen_dict, "upfront_cash_requirement"),
        ),
        upfront_cash_gap=_delta(
            get(baseline_dict, "upfront_cash_gap"),
            get(scen_dict, "upfront_cash_gap"),
        ),
        first_year_cost=_delta(
            get(baseline_dict, "breakdown", "first_year_cost"),
            get(scen_dict, "breakdown", "first_year_cost"),
        ),
        total_projected_cost=_delta(
            get(baseline_dict, "breakdown", "total_projected_cost"),
            get(scen_dict, "breakdown", "total_projected_cost"),
        ),
        eligible_confirmed=_delta(
            get(baseline_dict, "funding", "eligible_confirmed"),
            get(scen_dict, "funding", "eligible_confirmed"),
        ),
        eligible_with_conditional=_delta(
            get(baseline_dict, "funding", "eligible_with_conditional"),
            get(scen_dict, "funding", "eligible_with_conditional"),
        ),
        available_before_departure=_delta(
            get(baseline_dict, "funding", "available_before_departure"),
            get(scen_dict, "funding", "available_before_departure"),
        ),
        notes=scen_notes,
        warnings=_derive_warnings(baseline_dict, scen_dict),
        statuses_baseline=[str(s) for s in baseline_dict.get("statuses", [])],
        statuses_scenario=[str(s) for s in scen_dict.get("statuses", [])],
        generated_at=datetime.now(timezone.utc).isoformat(),
        calculation_version=CALCULATION_VERSION,
    )


def _derive_warnings(baseline: dict, scenario: dict) -> list[str]:  # type: ignore[type-arg]
    warnings: list[str] = []
    base_gap = Decimal(str(baseline.get("funding_gap", "0")))
    scen_gap = Decimal(str(scenario.get("funding_gap", "0")))
    if scen_gap > base_gap:
        delta = scen_gap - base_gap
        warnings.append(
            f"Funding gap worsens by {delta} in the scenario."
        )
    if scen_gap > base_gap and Decimal(str(baseline.get("funding_gap", "0"))) <= 0:
        warnings.append(
            "Scenario turns a previously affordable plan into a funding gap."
        )
    base_upfront = Decimal(str(baseline.get("upfront_cash_gap", "0")))
    scen_upfront = Decimal(str(scenario.get("upfront_cash_gap", "0")))
    if scen_upfront > base_upfront:
        delta = scen_upfront - base_upfront
        warnings.append(
            f"Upfront cash gap grows by {delta} in the scenario."
        )
    return warnings


__all__ = [
    "CALCULATION_VERSION",
    "SCENARIO_KEYS",
    "create_scenario",
    "delete_scenario",
    "list_scenarios",
    "run_scenario",
    "update_scenario",
]

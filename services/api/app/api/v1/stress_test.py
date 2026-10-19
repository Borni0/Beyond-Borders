"""Stress Test endpoints (spec §3.5 — Financial Weather).

* ``GET    /api/v1/stress-test/scenarios``               — list the caller's scenarios
* ``POST   /api/v1/stress-test/scenarios``               — save a new scenario
* ``GET    /api/v1/stress-test/scenarios/{id}``          — fetch one
* ``PATCH  /api/v1/stress-test/scenarios/{id}``          — edit
* ``DELETE /api/v1/stress-test/scenarios/{id}``          — remove
* ``GET    /api/v1/stress-test/presets``                 — preset definitions
* ``POST   /api/v1/stress-test/run``                     — run a scenario against a plan

All lookups are scoped to ``current_user`` and return ``404`` on
cross-tenant access.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, DbSessionDep
from app.schemas.stress_test import (
    StressRunRequest,
    StressRunResult,
    StressScenarioCreate,
    StressScenarioPublic,
    StressScenarioUpdate,
)
from app.services import stress_test_service

router = APIRouter(prefix="/stress-test", tags=["stress-test"])


# ---------- Presets ---------------------------------------------------------


@router.get("/presets")
def list_presets() -> dict:
    """Return the catalogue of preset scenario keys for the UI."""
    return {"presets": stress_test_service.SCENARIO_KEYS}


# ---------- Scenarios (CRUD) ------------------------------------------------


@router.get("/scenarios", response_model=list[StressScenarioPublic])
def list_scenarios(
    db: DbSessionDep,
    current_user: CurrentUser,
    plan_id: str | None = None,
) -> list[StressScenarioPublic]:
    return stress_test_service.list_scenarios(
        db, user_id=current_user.id, plan_id=plan_id
    )


@router.post(
    "/scenarios",
    response_model=StressScenarioPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_scenario(
    body: StressScenarioCreate,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> StressScenarioPublic:
    return stress_test_service.create_scenario(
        db, user_id=current_user.id, body=body
    )


@router.get("/scenarios/{scenario_id}", response_model=StressScenarioPublic)
def get_scenario(
    scenario_id: str,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> StressScenarioPublic:
    from app.core.errors import ApiError
    from app.repositories import stress_scenario_repo

    row = stress_scenario_repo.get_scenario(db, current_user.id, scenario_id)
    if row is None:
        raise ApiError("NOT_FOUND", "Scenario not found.", http_status=404)
    return stress_test_service._to_public(row)


@router.patch(
    "/scenarios/{scenario_id}",
    response_model=StressScenarioPublic,
)
def update_scenario(
    scenario_id: str,
    body: StressScenarioUpdate,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> StressScenarioPublic:
    return stress_test_service.update_scenario(
        db,
        user_id=current_user.id,
        scenario_id=scenario_id,
        body=body,
    )


@router.delete(
    "/scenarios/{scenario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_scenario(
    scenario_id: str,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> None:
    stress_test_service.delete_scenario(
        db, user_id=current_user.id, scenario_id=scenario_id
    )
    return None


# ---------- Run -------------------------------------------------------------


@router.post("/run", response_model=StressRunResult)
def run_scenario(
    body: StressRunRequest,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> StressRunResult:
    return stress_test_service.run_scenario(
        db, user_id=current_user.id, body=body
    )


__all__ = ["router"]

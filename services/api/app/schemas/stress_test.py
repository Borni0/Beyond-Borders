"""Pydantic schemas for the Stress Test / Financial Weather feature.

Spec §3.5 — model the impact of an FX shock, rent increase, scholarship
cut, or family-support delay on a single plan and return baseline vs
scenario deltas.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.decision_studio import ScenarioAdjustment

# ---------- Scenario CRUD ---------------------------------------------------

class StressScenarioBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    # Preset key — see app.services.stress_test_service.SCENARIO_KEYS.
    scenario_key: str = Field(min_length=1, max_length=40)
    adjustments: list[ScenarioAdjustment] = Field(default_factory=list)
    plan_id: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=2000)


class StressScenarioCreate(StressScenarioBase):
    pass


class StressScenarioUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    scenario_key: str | None = Field(default=None, min_length=1, max_length=40)
    adjustments: list[ScenarioAdjustment] | None = None
    plan_id: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=2000)


class StressScenarioPublic(StressScenarioBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    created_at: str
    updated_at: str


# ---------- Run / deltas ----------------------------------------------------

class StressRunRequest(BaseModel):
    plan_id: str = Field(min_length=1, max_length=64)
    scenario_id: str | None = Field(default=None, max_length=64)
    # Used when ``scenario_id`` is omitted — the caller supplies the
    # adjustments directly (one-off "what if I just tried this?").
    adjustments: list[ScenarioAdjustment] | None = None
    scenario_name: str | None = Field(default="baseline", max_length=80)
    upfront_window_days: int = Field(default=30, ge=1, le=365)


class _Delta(BaseModel):
    """A signed baseline-vs-scenario delta in the plan's base currency."""
    baseline: str
    scenario: str
    delta: str


class StressRunResult(BaseModel):
    plan_id: str
    base_currency: str
    scenario_id: str | None = None
    scenario_name: str
    upfront_window_days: int
    funding_gap: _Delta
    funding_surplus: _Delta
    upfront_cash_requirement: _Delta
    upfront_cash_gap: _Delta
    first_year_cost: _Delta
    total_projected_cost: _Delta
    eligible_confirmed: _Delta
    eligible_with_conditional: _Delta
    available_before_departure: _Delta
    notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    statuses_baseline: list[str] = Field(default_factory=list)
    statuses_scenario: list[str] = Field(default_factory=list)
    generated_at: str
    calculation_version: str = "stress_test_v1"


__all__ = [
    "StressRunRequest",
    "StressRunResult",
    "StressScenarioCreate",
    "StressScenarioPublic",
    "StressScenarioUpdate",
]

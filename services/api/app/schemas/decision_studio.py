"""Pydantic schemas for the Decision Studio endpoints.

The wire format is deliberately verbose (every numeric is a string of a
Decimal, every status / category is a string enum) so the same JSON
can be re-rendered by the frontend without re-parsing or re-rounding.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------- Scenario support ------------------------------------------------

# A *scenario* is a hypothetical tweak to a single plan. The list of
# fields here covers what the spec calls out in §3.7 (rent increase,
# scholarship reduction, FX shift, etc.) plus a small generic
# ``custom_note`` so a user can annotate an ad-hoc change without us
# having to invent a new field per spec revision.
ScenarioAdjustmentType = Literal[
    "rent_increase_pct",
    "tuition_increase_pct",
    "living_expense_increase_pct",
    "scholarship_reduction_pct",
    "family_support_delay_days",
    "fx_shift_pct",
    "deposit_change",
    "custom_note",
]


class ScenarioAdjustment(BaseModel):
    """One hypothetical change to apply to a plan.

    ``value`` semantics depend on ``type``:
    * percentage changes are stored as a number in [-100, +100]
    * ``family_support_delay_days`` is a non-negative integer
    * ``deposit_change`` is a signed Decimal string
    * ``custom_note`` ignores ``value`` (the note lives in ``note``)
    """

    model_config = ConfigDict(extra="forbid")

    type: ScenarioAdjustmentType
    value: str | None = Field(default=None, max_length=40)
    note: str | None = Field(default=None, max_length=500)


class ScenarioSpec(BaseModel):
    """A list of adjustments for one plan, plus a human label.

    A ``name`` of ``"baseline"`` (the default) means "no changes".
    """

    model_config = ConfigDict(extra="forbid")

    plan_id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(default="baseline", min_length=1, max_length=80)
    adjustments: list[ScenarioAdjustment] = Field(default_factory=list)
    note: str | None = Field(default=None, max_length=500)


# ---------- Request / response ---------------------------------------------

class CompareRequest(BaseModel):
    """The body of ``POST /api/v1/decision-studio/compare``.

    * Exactly 2 or 3 plan IDs are required.
    * Every plan must belong to the authenticated user (verified
      server-side, returns 404 otherwise).
    * Scenarios are optional. When present, there must be one entry
      per selected plan. Use ``name="baseline"`` with no adjustments
      to keep a plan unchanged.
    """

    model_config = ConfigDict(extra="forbid")

    study_plan_ids: list[str] = Field(..., min_length=2, max_length=3)
    scenarios: list[ScenarioSpec] | None = None
    upfront_window_days: int = Field(default=30, ge=1, le=365)

    @field_validator("study_plan_ids")
    @classmethod
    def _no_duplicates(cls, v: list[str]) -> list[str]:
        if len(set(v)) != len(v):
            raise ValueError("study_plan_ids must be unique")
        return v


# ---- Plan summary as it appears in the comparison ----

class ComparisonPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    destination_country: str | None = None
    institution_name: str | None = None
    program_name: str | None = None
    city: str | None = None
    base_currency: str
    start_date: date
    duration_months: int
    end_date: date
    scenario_name: str = "baseline"
    data_completeness: Literal["complete", "partial", "missing"] = "complete"
    missing_inputs: list[str] = Field(default_factory=list)


# ---- Cost / funding / cash metrics per plan ----

class ComparisonCostMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_currency: str
    total_projected_cost: str
    first_year_cost: str
    refundable_deposits: str
    per_category: dict[str, str]
    per_year: list[dict]
    cost_for_displayed_period: str
    displayed_period_months: int


class ComparisonFundingMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_currency: str
    confirmed_total: str
    conditional_total: str
    expected_total: str
    unavailable_total: str
    eligible_confirmed: str
    eligible_with_conditional: str
    funding_gap: str
    funding_surplus: str
    available_before_departure: str


class ComparisonUpfrontMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_currency: str
    upfront_window_days: int
    upfront_cash_requirement: str
    upfront_cash_gap: str


class ComparisonPaymentRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    category: str
    amount: str
    currency: str
    due_date: date | None = None
    display_status: str


class DeadlinePlanRanking(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str
    rank: int
    score: int
    status: Literal["no_shortfall", "shortfall", "no_payment_data"]
    earliest_shortfall_date: date | None = None
    shortfall_amount: str | None = None
    funded_by_deadline: str | None = None
    required_by_deadline: str | None = None
    rationale: str


# ---- Aggregate row in the side-by-side table ----

class ComparisonRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan: ComparisonPlan
    cost: ComparisonCostMetrics
    funding: ComparisonFundingMetrics
    upfront: ComparisonUpfrontMetrics
    earliest_payment: ComparisonPaymentRow | None = None
    payments: list[ComparisonPaymentRow] = Field(default_factory=list)
    deadline_status: Literal["no_shortfall", "shortfall", "no_payment_data"] | None = None
    earliest_shortfall_date: date | None = None
    shortfall_amount: str | None = None
    deadline_rationale: str | None = None


class ComparisonWarning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Literal[
        "missing_costs",
        "missing_funding",
        "missing_fx",
        "different_currencies",
        "different_durations",
        "incomplete_data",
        "no_known_payments",
    ]
    message: str
    plan_ids: list[str] = Field(default_factory=list)


class CompareResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comparison_id: str | None = None  # populated for saved comparisons
    plans: list[ComparisonRow]
    warnings: list[ComparisonWarning] = Field(default_factory=list)
    generated_at: datetime
    calculation_version: str = "decision_studio_v1"
    recommended_plan_id: str | None = None
    winner: str | None = None
    deadline_rankings: list[DeadlinePlanRanking] = Field(default_factory=list)
    deadline_analysis: list[DeadlinePlanRanking] = Field(default_factory=list)
    ranked_plans: list[ComparisonRow] = Field(default_factory=list)


# ---- Saved-comparison CRUD ----

class SavedComparisonCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=120)
    study_plan_ids: list[str] = Field(..., min_length=2, max_length=3)
    scenarios: list[ScenarioSpec] | None = None


class SavedComparisonUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    study_plan_ids: list[str] | None = Field(default=None, min_length=2, max_length=3)
    scenarios: list[ScenarioSpec] | None = None


class SavedComparisonPublic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    user_id: str
    name: str
    study_plan_ids: list[str]
    scenarios: list[ScenarioSpec] | None = None
    calculation_version: str
    created_at: str
    updated_at: str


__all__ = [
    "ScenarioAdjustment",
    "ScenarioAdjustmentType",
    "ScenarioSpec",
    "CompareRequest",
    "ComparisonPlan",
    "ComparisonCostMetrics",
    "ComparisonFundingMetrics",
    "ComparisonUpfrontMetrics",
    "ComparisonPaymentRow",
    "DeadlinePlanRanking",
    "ComparisonRow",
    "ComparisonWarning",
    "CompareResult",
    "SavedComparisonCreate",
    "SavedComparisonUpdate",
    "SavedComparisonPublic",
]

"""Typed dataclasses used by the calculation engine.

These are framework-agnostic — no SQLAlchemy or Pydantic — so the engine can
be unit-tested without touching the database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional


# ---------- Enums ----------
class CostCategory(str, Enum):
    TUITION = "tuition"
    ACCOMMODATION = "accommodation"
    FOOD = "food"
    TRANSPORT = "transport"
    UTILITIES = "utilities"
    INSURANCE = "insurance"
    TRAVEL = "travel"
    VISA = "visa"
    DEPOSITS = "deposits"
    STUDY_MATERIALS = "study_materials"
    PERSONAL = "personal"
    MISCELLANEOUS = "miscellaneous"


class Frequency(str, Enum):
    ONE_TIME = "one_time"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMESTER = "semester"
    ANNUAL = "annual"


class FundingType(str, Enum):
    SAVINGS = "savings"
    FAMILY = "family"
    SCHOLARSHIP = "scholarship"
    LOAN = "loan"
    INCOME = "income"
    OTHER = "other"


class FundingStatus(str, Enum):
    CONFIRMED = "confirmed"
    CONDITIONAL = "conditional"
    EXPECTED = "expected"
    UNAVAILABLE = "unavailable"


class RateType(str, Enum):
    REFERENCE = "reference"
    PROVIDER_QUOTE = "provider_quote"
    USER_ENTERED = "user_entered"


# ---------- Plain inputs ----------
@dataclass(frozen=True)
class CostItem:
    id: str
    category: CostCategory
    description: str
    amount: Decimal
    currency: str
    frequency: Frequency
    start_date: Optional[date]
    end_date: Optional[date]
    is_one_time: bool
    is_refundable: bool
    due_before_departure: bool = False
    source_id: Optional[str] = None


@dataclass(frozen=True)
class FundingSource:
    id: str
    name: str
    funding_type: FundingType
    amount: Decimal
    currency: str
    status: FundingStatus
    expected_date: Optional[date]
    notes: Optional[str] = None


@dataclass(frozen=True)
class FxRate:
    base_currency: str
    quote_currency: str
    rate: Decimal
    rate_type: RateType
    observed_at: date


# ---------- Plan context ----------
@dataclass(frozen=True)
class PlanContext:
    id: str
    name: str
    base_currency: str
    start_date: date
    duration_months: int


# ---------- Outputs ----------
@dataclass(frozen=True)
class YearCost:
    year_index: int  # 1-based
    recurring_total: Decimal
    one_time_total: Decimal
    total: Decimal

    def to_dict(self) -> dict:
        return {
            "year_index": self.year_index,
            "recurring_total": str(self.recurring_total),
            "one_time_total": str(self.one_time_total),
            "total": str(self.total),
        }


@dataclass(frozen=True)
class CostBreakdown:
    base_currency: str
    per_year: list[YearCost] = field(default_factory=list)
    first_year_cost: Decimal = Decimal("0")
    total_projected_cost: Decimal = Decimal("0")
    refundable_deposits: Decimal = Decimal("0")
    per_category: dict[str, Decimal] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "base_currency": self.base_currency,
            "per_year": [y.to_dict() for y in self.per_year],
            "first_year_cost": str(self.first_year_cost),
            "total_projected_cost": str(self.total_projected_cost),
            "refundable_deposits": str(self.refundable_deposits),
            "per_category": {k: str(v) for k, v in self.per_category.items()},
        }


@dataclass(frozen=True)
class FundingBreakdown:
    base_currency: str
    confirmed_total: Decimal = Decimal("0")
    conditional_total: Decimal = Decimal("0")
    expected_total: Decimal = Decimal("0")
    unavailable_total: Decimal = Decimal("0")
    eligible_confirmed: Decimal = Decimal("0")
    eligible_with_conditional: Decimal = Decimal("0")
    available_before_departure: Decimal = Decimal("0")

    def to_dict(self) -> dict:
        return {
            "base_currency": self.base_currency,
            "confirmed_total": str(self.confirmed_total),
            "conditional_total": str(self.conditional_total),
            "expected_total": str(self.expected_total),
            "unavailable_total": str(self.unavailable_total),
            "eligible_confirmed": str(self.eligible_confirmed),
            "eligible_with_conditional": str(self.eligible_with_conditional),
            "available_before_departure": str(self.available_before_departure),
        }


class ReadinessStatusCode(str, Enum):
    FUNDING_GAP_IDENTIFIED = "funding_gap_identified"
    UPFRONT_CASH_GAP = "upfront_cash_gap"
    CONDITIONAL_FUNDING = "conditional_funding"
    SCENARIO_SENSITIVE = "scenario_sensitive"
    NO_MODELED_SHORTFALL = "no_modeled_shortfall"
    NEEDS_MORE_INFORMATION = "needs_more_information"


@dataclass(frozen=True)
class StatusSet:
    codes: tuple[ReadinessStatusCode, ...]

    def has(self, code: ReadinessStatusCode) -> bool:
        return code in self.codes

    def to_list(self) -> list[str]:
        return [c.value for c in self.codes]


@dataclass(frozen=True)
class ReadinessResult:
    plan_id: str
    base_currency: str
    breakdown: CostBreakdown
    funding: FundingBreakdown
    funding_gap: Decimal
    funding_surplus: Decimal
    upfront_cash_requirement: Decimal
    upfront_cash_gap: Decimal
    upfront_cash_window_days: int
    statuses: StatusSet
    missing_inputs: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    # ---- Phase 1 enrichment ----
    # Funding gap restricted to the first study year (year_index == 1).
    first_year_funding_gap: Decimal = Decimal("0")
    # Total eligible funding (confirmed + conditional + expected that lands
    # on time) as a fraction of the total projected cost. None when there
    # is no cost to compare against.
    coverage_pct: Optional[Decimal] = None
    # Hypothetical gap if every conditional/expected funding source were
    # to fall through. Useful for the "potential gap" line in the UI.
    potential_gap_after_expected: Decimal = Decimal("0")

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "base_currency": self.base_currency,
            "breakdown": self.breakdown.to_dict(),
            "funding": self.funding.to_dict(),
            "funding_gap": str(self.funding_gap),
            "funding_surplus": str(self.funding_surplus),
            "upfront_cash_requirement": str(self.upfront_cash_requirement),
            "upfront_cash_gap": str(self.upfront_cash_gap),
            "upfront_cash_window_days": self.upfront_cash_window_days,
            "statuses": self.statuses.to_list(),
            "missing_inputs": list(self.missing_inputs),
            "notes": list(self.notes),
            "first_year_funding_gap": str(self.first_year_funding_gap),
            "coverage_pct": (
                None if self.coverage_pct is None else str(self.coverage_pct)
            ),
            "potential_gap_after_expected": str(
                self.potential_gap_after_expected
            ),
        }


__all__ = [
    "CostCategory",
    "Frequency",
    "FundingType",
    "FundingStatus",
    "RateType",
    "CostItem",
    "FundingSource",
    "FxRate",
    "PlanContext",
    "YearCost",
    "CostBreakdown",
    "FundingBreakdown",
    "ReadinessStatusCode",
    "StatusSet",
    "ReadinessResult",
]
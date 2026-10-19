"""Financial calculation engine (spec §8)."""

from app.services.financial.currency import CurrencyError, convert, index_rates
from app.services.financial.money import (
    decimal_places,
    round_money,
    to_decimal,
    zero_money,
)
from app.services.financial.projection import project_costs, project_upfront
from app.services.financial.readiness import compute_readiness
from app.services.financial.types import (
    CostBreakdown,
    CostCategory,
    CostItem,
    Frequency,
    FundingBreakdown,
    FundingSource,
    FundingStatus,
    FundingType,
    FxRate,
    PlanContext,
    RateType,
    ReadinessResult,
    ReadinessStatusCode,
    StatusSet,
    YearCost,
)

__all__ = [
    "CostBreakdown",
    "CostCategory",
    "CostItem",
    "CurrencyError",
    "Frequency",
    "FundingBreakdown",
    "FundingSource",
    "FundingStatus",
    "FundingType",
    "FxRate",
    "PlanContext",
    "RateType",
    "ReadinessResult",
    "ReadinessStatusCode",
    "StatusSet",
    "YearCost",
    "compute_readiness",
    "convert",
    "decimal_places",
    "index_rates",
    "project_costs",
    "project_upfront",
    "round_money",
    "to_decimal",
    "zero_money",
]
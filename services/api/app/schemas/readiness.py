"""Pydantic schemas for the readiness endpoint output.

The response mirrors `ReadinessResult.to_dict()` byte-for-byte so the same
snapshot is returned regardless of caller path. We define it as a
BaseModel (instead of returning a plain dict) so the OpenAPI docs are
useful and the frontend gets typed responses.
"""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class YearCostPublic(BaseModel):
    year_index: int
    recurring_total: str
    one_time_total: str
    total: str


class CostBreakdownPublic(BaseModel):
    base_currency: str
    per_year: List[YearCostPublic]
    first_year_cost: str
    total_projected_cost: str
    refundable_deposits: str
    per_category: dict[str, str]


class FundingBreakdownPublic(BaseModel):
    base_currency: str
    confirmed_total: str
    conditional_total: str
    expected_total: str
    unavailable_total: str
    eligible_confirmed: str
    eligible_with_conditional: str
    available_before_departure: str


class StatusSetPublic(BaseModel):
    codes: List[str]


class ReadinessResultPublic(BaseModel):
    plan_id: str
    base_currency: str
    breakdown: CostBreakdownPublic
    funding: FundingBreakdownPublic
    funding_gap: str
    funding_surplus: str
    upfront_cash_requirement: str
    upfront_cash_gap: str
    upfront_cash_window_days: int
    statuses: StatusSetPublic
    missing_inputs: List[str]
    notes: List[str]


__all__ = ["ReadinessResultPublic"]

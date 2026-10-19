"""Pydantic schemas for the funding-source endpoints."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


FundingTypeValue = Literal[
    "savings", "family", "scholarship", "loan", "income", "other",
]
FundingStatusValue = Literal[
    "confirmed", "conditional", "expected", "unavailable",
]


class FundingSourceBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    funding_type: FundingTypeValue
    amount: Decimal = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    status: FundingStatusValue
    expected_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=2000)


class FundingSourceCreate(FundingSourceBase):
    pass


class FundingSourceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    funding_type: Optional[FundingTypeValue] = None
    amount: Optional[Decimal] = Field(default=None, ge=0)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    status: Optional[FundingStatusValue] = None
    expected_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=2000)


class FundingSourcePublic(FundingSourceBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    plan_id: str
    created_at: str
    updated_at: str


__all__ = [
    "FundingTypeValue",
    "FundingStatusValue",
    "FundingSourceCreate",
    "FundingSourceUpdate",
    "FundingSourcePublic",
]

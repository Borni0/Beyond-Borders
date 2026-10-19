"""Pydantic schemas for the cost-item endpoints."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# Allowed enum values for request validation. Mirrors the strings stored on
# the row so the engine can compare against them directly.
CostCategoryValue = Literal[
    "tuition", "accommodation", "food", "transport", "utilities",
    "insurance", "travel", "visa", "deposits", "study_materials",
    "personal", "miscellaneous",
]
FrequencyValue = Literal["one_time", "monthly", "quarterly", "semester", "annual"]


class CostItemBase(BaseModel):
    category: CostCategoryValue
    description: str = Field(default="", max_length=500)
    amount: Decimal = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    frequency: FrequencyValue
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_one_time: bool = False
    is_refundable: bool = False
    due_before_departure: bool = False
    source_id: Optional[str] = None


class CostItemCreate(CostItemBase):
    pass


class CostItemUpdate(BaseModel):
    category: Optional[CostCategoryValue] = None
    description: Optional[str] = Field(default=None, max_length=500)
    amount: Optional[Decimal] = Field(default=None, ge=0)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    frequency: Optional[FrequencyValue] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_one_time: Optional[bool] = None
    is_refundable: Optional[bool] = None
    due_before_departure: Optional[bool] = None
    source_id: Optional[str] = None


class CostItemPublic(CostItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    plan_id: str
    created_at: str
    updated_at: str


__all__ = [
    "CostCategoryValue",
    "FrequencyValue",
    "CostItemCreate",
    "CostItemUpdate",
    "CostItemPublic",
]

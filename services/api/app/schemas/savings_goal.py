"""Pydantic schemas for the savings-goal endpoints.

A savings goal records a target amount, currency, and date the student is
saving toward. ``current_amount`` is updated over time (manually in Phase 2).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SavingsGoalBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    target_amount: Decimal = Field(ge=0)
    current_amount: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(min_length=3, max_length=3)
    target_date: date
    notes: Optional[str] = Field(default=None, max_length=2000)


class SavingsGoalCreate(SavingsGoalBase):
    plan_id: Optional[str] = None


class SavingsGoalUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    target_amount: Optional[Decimal] = Field(default=None, ge=0)
    current_amount: Optional[Decimal] = Field(default=None, ge=0)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    target_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=2000)
    plan_id: Optional[str] = None


class SavingsGoalPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    plan_id: Optional[str]
    name: str
    target_amount: Decimal
    current_amount: Decimal
    currency: str
    target_date: date
    notes: Optional[str]
    created_at: str
    updated_at: str


__all__ = [
    "SavingsGoalCreate",
    "SavingsGoalPublic",
    "SavingsGoalUpdate",
]

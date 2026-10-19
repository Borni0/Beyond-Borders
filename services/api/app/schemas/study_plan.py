"""Pydantic schemas for the study plan endpoints."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class StudyPlanBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    destination_country: Optional[str] = Field(
        default=None, min_length=2, max_length=2
    )
    base_currency: str = Field(min_length=3, max_length=3)
    start_date: date
    duration_months: int = Field(ge=1, le=120)
    notes: Optional[str] = Field(default=None, max_length=2000)
    # ---- Financial-readiness enrichment (Phase 1 extension) ----
    institution_name: Optional[str] = Field(default=None, max_length=200)
    program_name: Optional[str] = Field(default=None, max_length=200)
    city: Optional[str] = Field(default=None, max_length=120)
    # Tuition may be 0 (fully funded) but never negative.
    tuition_amount: Optional[Decimal] = Field(default=None, ge=0)
    tuition_currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    home_currency: Optional[str] = Field(default=None, min_length=3, max_length=3)


class StudyPlanCreate(StudyPlanBase):
    pass


class StudyPlanUpdate(BaseModel):
    # All fields optional so the UI can PATCH one at a time.
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    destination_country: Optional[str] = Field(
        default=None, min_length=2, max_length=2
    )
    base_currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    start_date: Optional[date] = None
    duration_months: Optional[int] = Field(default=None, ge=1, le=120)
    notes: Optional[str] = Field(default=None, max_length=2000)
    institution_name: Optional[str] = Field(default=None, max_length=200)
    program_name: Optional[str] = Field(default=None, max_length=200)
    city: Optional[str] = Field(default=None, max_length=120)
    tuition_amount: Optional[Decimal] = Field(default=None, ge=0)
    tuition_currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    home_currency: Optional[str] = Field(default=None, min_length=3, max_length=3)


class StudyPlanPublic(StudyPlanBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    end_date: date
    created_at: str
    updated_at: str


__all__ = ["StudyPlanCreate", "StudyPlanUpdate", "StudyPlanPublic"]

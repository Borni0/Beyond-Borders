"""Pydantic schemas for the payment-event endpoints.

A ``payment_event`` is an operational bill the student expects to pay on a
specific due date — a deposit, tuition installment, rent charge, flight,
visa fee, etc.

The stored ``status`` values are ``planned | scheduled | paid | cancelled``.
``overdue`` is *not* stored: the service layer derives it at read time from
``due_date < today`` AND status in ``(planned, scheduled)``.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# Stored values only. `overdue` is computed.
PaymentStatusValue = Literal["planned", "scheduled", "paid", "cancelled"]
# Display values that the API can return (includes the derived `overdue`).
PaymentStatusDisplay = Literal[
    "planned", "scheduled", "paid", "overdue", "cancelled",
]

# Categories that group payments in the timeline UI. Same vocabulary as costs
# so a tuition CostItem and a tuition PaymentEvent line up in reports, plus
# a couple of operational-only buckets.
PaymentCategoryValue = Literal[
    "tuition", "accommodation", "food", "transport", "utilities",
    "insurance", "travel", "visa", "deposits", "study_materials",
    "personal", "miscellaneous",
]

# How often a recurring event rolls forward. Same vocabulary as CostItem.
RecurrenceFrequencyValue = Literal[
    "monthly", "quarterly", "semester", "annual",
]


class PaymentEventBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    category: PaymentCategoryValue
    amount: Decimal = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    due_date: date
    status: PaymentStatusValue = "planned"
    notes: Optional[str] = Field(default=None, max_length=2000)
    is_recurring: bool = False
    recurrence_frequency: Optional[RecurrenceFrequencyValue] = None
    recurrence_end_date: Optional[date] = None


class PaymentEventCreate(PaymentEventBase):
    plan_id: Optional[str] = None


class PaymentEventUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    category: Optional[PaymentCategoryValue] = None
    amount: Optional[Decimal] = Field(default=None, ge=0)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    due_date: Optional[date] = None
    status: Optional[PaymentStatusValue] = None
    notes: Optional[str] = Field(default=None, max_length=2000)
    is_recurring: Optional[bool] = None
    recurrence_frequency: Optional[RecurrenceFrequencyValue] = None
    recurrence_end_date: Optional[date] = None
    plan_id: Optional[str] = None


class PaymentEventPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    plan_id: Optional[str]
    title: str
    category: PaymentCategoryValue
    amount: Decimal
    currency: str
    due_date: date
    # Display status — includes the derived `overdue`.
    display_status: PaymentStatusDisplay
    notes: Optional[str]
    is_recurring: bool
    recurrence_frequency: Optional[RecurrenceFrequencyValue]
    recurrence_end_date: Optional[date]
    created_at: str
    updated_at: str


__all__ = [
    "PaymentCategoryValue",
    "PaymentStatusDisplay",
    "PaymentStatusValue",
    "PaymentEventCreate",
    "PaymentEventPublic",
    "PaymentEventUpdate",
    "RecurrenceFrequencyValue",
]

"""Pydantic schemas for the expense log / spending tracker (spec §3.6)."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ExpenseBase(BaseModel):
    category: str = Field(min_length=1, max_length=32)
    description: str = Field(default="", max_length=500)
    amount: Decimal
    currency: str = Field(min_length=3, max_length=3)
    spent_on: str  # ISO date
    plan_id: str | None = Field(default=None, max_length=64)
    payment_method: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=2000)


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=1, max_length=32)
    description: str | None = Field(default=None, max_length=500)
    amount: Decimal | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    spent_on: str | None = None
    plan_id: str | None = Field(default=None, max_length=64)
    payment_method: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=2000)


class ExpensePublic(ExpenseBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    created_at: str
    updated_at: str


class ExpenseImportResult(BaseModel):
    created: int
    skipped: int
    errors: list[str] = Field(default_factory=list)


class CategoryTotal(BaseModel):
    category: str
    total: str
    currency: str
    count: int


class MonthlyBucket(BaseModel):
    month: str  # YYYY-MM
    total: str
    currency: str
    count: int
    by_category: list[CategoryTotal] = Field(default_factory=list)


class ExpenseSummary(BaseModel):
    base_currency: str
    total: str
    count: int
    months: list[MonthlyBucket] = Field(default_factory=list)
    by_category: list[CategoryTotal] = Field(default_factory=list)


__all__ = [
    "CategoryTotal",
    "ExpenseCreate",
    "ExpenseImportResult",
    "ExpensePublic",
    "ExpenseSummary",
    "ExpenseUpdate",
    "MonthlyBucket",
]
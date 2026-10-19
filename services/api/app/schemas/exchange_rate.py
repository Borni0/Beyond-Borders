"""Pydantic schemas for the exchange-rate endpoints."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


RateTypeValue = Literal["reference", "provider_quote", "user_entered"]


class ExchangeRateBase(BaseModel):
    base_currency: str = Field(min_length=3, max_length=3)
    quote_currency: str = Field(min_length=3, max_length=3)
    rate: Decimal = Field(gt=0)
    rate_type: RateTypeValue = "user_entered"
    observed_at: date


class ExchangeRateCreate(ExchangeRateBase):
    pass


class ExchangeRateUpsert(ExchangeRateBase):
    """Used by PATCH: same fields; the pair identifies the record."""
    pass


class ExchangeRatePublic(ExchangeRateBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: str
    updated_at: str


__all__ = [
    "RateTypeValue",
    "ExchangeRateCreate",
    "ExchangeRateUpsert",
    "ExchangeRatePublic",
]

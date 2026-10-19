"""Pydantic schemas for the data-source registry endpoints."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DataSourceBase(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    url: Optional[str] = Field(default=None, max_length=2000)
    notes: Optional[str] = Field(default=None, max_length=2000)


class DataSourceCreate(DataSourceBase):
    pass


class DataSourceUpdate(BaseModel):
    label: Optional[str] = Field(default=None, min_length=1, max_length=120)
    url: Optional[str] = Field(default=None, max_length=2000)
    notes: Optional[str] = Field(default=None, max_length=2000)


class DataSourcePublic(DataSourceBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: str
    updated_at: str


__all__ = ["DataSourceCreate", "DataSourceUpdate", "DataSourcePublic"]

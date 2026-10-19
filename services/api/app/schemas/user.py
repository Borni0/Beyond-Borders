"""Pydantic schemas for the User resource."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    home_country: str | None = Field(default=None, min_length=2, max_length=2)
    home_currency: str = Field(default="USD", min_length=3, max_length=3)
    display_currency: str = Field(default="USD", min_length=3, max_length=3)


class UserCreate(UserBase):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    home_country: str | None = Field(default=None, min_length=2, max_length=2)
    home_currency: str | None = Field(default=None, min_length=3, max_length=3)
    display_currency: str | None = Field(default=None, min_length=3, max_length=3)


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    name: str
    home_country: str | None
    home_currency: str
    display_currency: str
    created_at: str
    updated_at: str
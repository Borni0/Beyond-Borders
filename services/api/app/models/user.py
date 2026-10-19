"""User ORM model."""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class User(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    home_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    home_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    display_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    # Phase 2+: reset token hash + expiry, kept here so the table schema
    # is stable across the transition.
    password_reset_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_reset_expires_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
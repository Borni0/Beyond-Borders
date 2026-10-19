"""Shared mixins for ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UUIDPKMixin:
    """Adds a UUID primary key column."""

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid.uuid4()))


class TimestampMixin:
    """Adds created_at / updated_at columns that auto-update."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )


__all__ = ["Base", "UUIDPKMixin", "TimestampMixin"]
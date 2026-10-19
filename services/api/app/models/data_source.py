"""Data source registry (spec §7, §11).

A data source is anything the user might cite to justify a cost or rate:
a university page, a bank statement, a scholarship letter. The Source
Registry is per-user, not per-plan, so the same source can be reused
across plans.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class DataSource(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "data_sources"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    label: Mapped[str] = mapped_column(String(120), nullable=False)
    # Free-form URL or identifier. We don't crawl anything in Phase 1.
    url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)


__all__ = ["DataSource"]

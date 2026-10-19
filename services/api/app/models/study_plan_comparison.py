"""Study-plan comparison: a saved side-by-side snapshot.

A comparison records which plans were selected, the scenarios that were
applied (if any), and the assumptions the user wanted to capture. The
*numeric* results are never persisted here — the comparison is always
re-computed from the underlying plans on read so the user is never shown
stale numbers when a plan changes.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class StudyPlanComparison(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "study_plan_comparisons"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # JSONB on Postgres; the SQLAlchemy Text fallback for SQLite (used
    # in tests) is wired in the migration with ``with_variant``.
    selected_plan_ids: Mapped[list] = mapped_column(
        Text().with_variant(JSONB, "postgresql"),
        nullable=False,
    )
    # Optional scenario specifications — see ``ScenarioSpec`` in the
    # schemas. ``None`` means "use the baseline plans unchanged".
    scenarios: Mapped[list | None] = mapped_column(
        Text().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    # Snapshot of the engine's calculation version, so the UI can
    # warn when results were produced by a newer version of the
    # engine than the one that was originally captured.
    calculation_version: Mapped[str] = mapped_column(
        String(40), nullable=False, default="decision_studio_v1"
    )


__all__ = ["StudyPlanComparison"]

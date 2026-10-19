"""Stress scenario ORM model (spec §3.5 — Financial Weather).

A stress scenario is a named bundle of overrides the user applies to a
plan to model a bad day — rent shock, scholarship cut, delayed family
support, FX shock, deposit change, or a free-form note. Scenarios are
per-user; ``plan_id`` is nullable so the same scenario can be re-run
against any plan (``scope = "global"``) or pinned to a single plan
(``scope = "plan"``).

The ``adjustments`` column is stored as a JSON-encoded string so the
same model works on both Postgres (jsonb) and SQLite (text) without
SQLAlchemy JSONB binding errors during tests. The repo layer
serializes on write and deserializes on read — see
``stress_scenario_repo._coerce_json`` / ``_serialize``.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class StressScenario(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "stress_scenarios"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("study_plans.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Preset key — see app.services.stress_test_service.SCENARIO_KEYS.
    scenario_key: Mapped[str] = mapped_column(String(40), nullable=False)
    # JSON-encoded list of adjustment dicts. Always a string on the
    # Python side; the repo layer deserializes on read.
    adjustments: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]", server_default="[]"
    )
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)


__all__ = ["StressScenario"]

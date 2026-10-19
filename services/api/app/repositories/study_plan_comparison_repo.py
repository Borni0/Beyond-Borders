"""Repository for saved study-plan comparisons.

Always scope by ``user_id``. The repo never returns a row owned by
another user; the route layer is responsible for translating that into
a 404 to avoid leaking the existence of someone else's data.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.study_plan_comparison import StudyPlanComparison


def _coerce_json(value) -> object:  # type: ignore[no-untyped-def]
    """The ``selected_plan_ids`` column is JSONB on Postgres and TEXT on
    SQLite (test engine). Normalize to a Python list."""

    if value is None:
        return []
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []
    return value


def _serialize(value) -> str:  # type: ignore[no-untyped-def]
    """Inverse of ``_coerce_json`` for writes."""

    return json.dumps(value, separators=(",", ":"))


def list_comparisons(
    db: Session, user_id: str
) -> Sequence[StudyPlanComparison]:
    stmt = (
        select(StudyPlanComparison)
        .where(StudyPlanComparison.user_id == user_id)
        .order_by(
            StudyPlanComparison.updated_at.desc(),
            StudyPlanComparison.created_at.desc(),
        )
    )
    return db.execute(stmt).scalars().all()


def get_comparison(
    db: Session, user_id: str, comparison_id: str
) -> StudyPlanComparison | None:
    stmt = select(StudyPlanComparison).where(
        StudyPlanComparison.id == comparison_id,
        StudyPlanComparison.user_id == user_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def create_comparison(
    db: Session,
    *,
    user_id: str,
    name: str,
    selected_plan_ids: list[str],
    scenarios: list | None = None,
) -> StudyPlanComparison:
    row = StudyPlanComparison(
        user_id=user_id,
        name=name,
        selected_plan_ids=_serialize(selected_plan_ids),
        scenarios=_serialize(scenarios) if scenarios is not None else None,
    )
    db.add(row)
    db.flush()
    return row


def update_comparison(
    db: Session,
    row: StudyPlanComparison,
    *,
    name: str | None = None,
    selected_plan_ids: list[str] | None = None,
    scenarios: list | None = None,
) -> StudyPlanComparison:
    if name is not None:
        row.name = name
    if selected_plan_ids is not None:
        row.selected_plan_ids = _serialize(selected_plan_ids)
    if scenarios is not None:
        row.scenarios = _serialize(scenarios)
    db.flush()
    return row


def delete_comparison(db: Session, row: StudyPlanComparison) -> None:
    db.delete(row)
    db.flush()


def as_dict(row: StudyPlanComparison) -> dict:
    """Plain-dict projection of a comparison for API responses."""

    return {
        "id": row.id,
        "user_id": row.user_id,
        "name": row.name,
        "selected_plan_ids": _coerce_json(row.selected_plan_ids),
        "scenarios": _coerce_json(row.scenarios) if row.scenarios is not None else None,
        "calculation_version": row.calculation_version,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


__all__ = [
    "list_comparisons",
    "get_comparison",
    "create_comparison",
    "update_comparison",
    "delete_comparison",
    "as_dict",
]

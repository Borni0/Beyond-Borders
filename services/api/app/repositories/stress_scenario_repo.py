"""Repository for the per-user stress scenario registry.

The ``adjustments`` column is a ``TEXT`` field on both Postgres and
SQLite — the service layer stores the JSON-encoded list, the repo
serializes on write and deserializes on read. Postgres will store it
in a jsonb column in a follow-up if performance becomes a concern,
but the JSON-encoding step makes the same Python code work on both
engines.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.stress_scenario import StressScenario


def _coerce_json(raw, default):  # type: ignore[no-untyped-def]
    if raw is None or raw == "":
        return default
    if isinstance(raw, (list, dict)):
        return raw
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return default
    return default


def _serialize(value) -> str:  # type: ignore[no-untyped-def]
    if value is None:
        return "[]"
    if isinstance(value, str):
        return value
    return json.dumps(value, separators=(",", ":"))


def list_scenarios(
    db: Session, user_id: str, plan_id: str | None = None
) -> Sequence[StressScenario]:
    stmt = select(StressScenario).where(StressScenario.user_id == user_id)
    if plan_id is not None:
        stmt = stmt.where(StressScenario.plan_id == plan_id)
    stmt = stmt.order_by(StressScenario.created_at.asc())
    return db.execute(stmt).scalars().all()


def get_scenario(
    db: Session, user_id: str, scenario_id: str
) -> StressScenario | None:
    stmt = select(StressScenario).where(
        StressScenario.id == scenario_id, StressScenario.user_id == user_id
    )
    return db.execute(stmt).scalar_one_or_none()


def create_scenario(
    db: Session,
    *,
    user_id: str,
    name: str,
    scenario_key: str,
    adjustments: list | str,
    plan_id: str | None,
    notes: str | None,
) -> StressScenario:
    row = StressScenario(
        user_id=user_id,
        plan_id=plan_id,
        name=name,
        scenario_key=scenario_key,
        adjustments=_serialize(adjustments),
        notes=notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_scenario(
    db: Session, row: StressScenario, **fields: object
) -> StressScenario:
    for key, value in fields.items():
        if value is None and key != "notes":
            continue
        if key == "notes" and value is None:
            setattr(row, key, None)
            continue
        if key == "adjustments":
            setattr(row, key, _serialize(value))
            continue
        if not hasattr(row, key):
            continue
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_scenario(db: Session, row: StressScenario) -> None:
    db.delete(row)
    db.commit()


def as_dict(row: StressScenario) -> dict:
    """Public-shape projection used by the routes / service layer."""
    return {
        "id": row.id,
        "user_id": row.user_id,
        "plan_id": row.plan_id,
        "name": row.name,
        "scenario_key": row.scenario_key,
        "adjustments": _coerce_json(row.adjustments, []),
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


__all__ = [
    "as_dict",
    "create_scenario",
    "delete_scenario",
    "get_scenario",
    "list_scenarios",
    "update_scenario",
]
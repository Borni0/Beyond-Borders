"""Repository for the per-user data source registry."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.data_source import DataSource


def list_sources(db: Session, user_id: str) -> Sequence[DataSource]:
    stmt = (
        select(DataSource)
        .where(DataSource.user_id == user_id)
        .order_by(DataSource.created_at.asc())
    )
    return db.execute(stmt).scalars().all()


def get_source(
    db: Session, user_id: str, source_id: str
) -> DataSource | None:
    stmt = select(DataSource).where(
        DataSource.id == source_id, DataSource.user_id == user_id
    )
    return db.execute(stmt).scalar_one_or_none()


def create_source(
    db: Session, *, user_id: str, label: str, url: str | None, notes: str | None
) -> DataSource:
    src = DataSource(user_id=user_id, label=label, url=url, notes=notes)
    db.add(src)
    db.commit()
    db.refresh(src)
    return src


def update_source(
    db: Session, src: DataSource, **fields: object
) -> DataSource:
    for key, value in fields.items():
        if value is None or not hasattr(src, key):
            continue
        setattr(src, key, value)
    db.commit()
    db.refresh(src)
    return src


def delete_source(db: Session, src: DataSource) -> None:
    db.delete(src)
    db.commit()


__all__ = [
    "list_sources",
    "get_source",
    "create_source",
    "update_source",
    "delete_source",
]

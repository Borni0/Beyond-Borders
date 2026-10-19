"""Data source registry routes (per-user, not per-plan)."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, DbSessionDep
from app.core.errors import ApiError
from app.repositories import data_source_repo
from app.schemas.data_source import (
    DataSourceCreate,
    DataSourcePublic,
    DataSourceUpdate,
)

router = APIRouter(prefix="/sources", tags=["sources"])


def _to_public(src) -> DataSourcePublic:  # type: ignore[no-untyped-def]
    return DataSourcePublic(
        id=src.id,
        label=src.label,
        url=src.url,
        notes=src.notes,
        created_at=src.created_at.isoformat(),
        updated_at=src.updated_at.isoformat(),
    )


@router.get("", response_model=list[DataSourcePublic])
def list_my_sources(
    db: DbSessionDep, current_user: CurrentUser
) -> list[DataSourcePublic]:
    return [_to_public(s) for s in data_source_repo.list_sources(db, current_user.id)]


@router.post(
    "",
    response_model=DataSourcePublic,
    status_code=status.HTTP_201_CREATED,
)
def create_my_source(
    payload: DataSourceCreate,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> DataSourcePublic:
    src = data_source_repo.create_source(
        db,
        user_id=current_user.id,
        label=payload.label,
        url=payload.url,
        notes=payload.notes,
    )
    return _to_public(src)


@router.patch("/{source_id}", response_model=DataSourcePublic)
def update_my_source(
    source_id: str,
    payload: DataSourceUpdate,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> DataSourcePublic:
    src = data_source_repo.get_source(db, current_user.id, source_id)
    if src is None:
        raise ApiError("NOT_FOUND", "Source not found.", http_status=404)
    src = data_source_repo.update_source(
        db, src, **{k: v for k, v in payload.model_dump().items() if v is not None}
    )
    return _to_public(src)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_source(
    source_id: str,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> None:
    src = data_source_repo.get_source(db, current_user.id, source_id)
    if src is None:
        raise ApiError("NOT_FOUND", "Source not found.", http_status=404)
    data_source_repo.delete_source(db, src)


__all__ = ["router"]

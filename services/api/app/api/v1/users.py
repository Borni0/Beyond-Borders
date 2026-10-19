"""User routes: read and update the current user's profile."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSessionDep
from app.schemas.user import UserPublic, UserUpdate
from app.services import auth_service

router = APIRouter(prefix="/users", tags=["users"])


def _to_public(user) -> UserPublic:  # type: ignore[no-untyped-def]
    return UserPublic(
        id=user.id,
        email=user.email,
        name=user.name,
        home_country=user.home_country,
        home_currency=user.home_currency,
        display_currency=user.display_currency,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
    )


@router.get("/me", response_model=UserPublic)
def get_me(current_user: CurrentUser) -> UserPublic:
    return _to_public(current_user)


@router.patch("/me", response_model=UserPublic)
def patch_me(payload: UserUpdate, db: DbSessionDep, current_user: CurrentUser) -> UserPublic:
    updated = auth_service.update_profile(db, current_user, payload)
    return _to_public(updated)
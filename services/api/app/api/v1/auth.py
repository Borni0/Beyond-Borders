"""Auth routes: register, login, logout, forgot/reset password."""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Response, status

from app.core.config import settings
from app.core.deps import DbSessionDep
from app.core.security import read_session_cookie, session_ttl_seconds
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
)
from app.schemas.user import UserCreate, UserPublic
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


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


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, response: Response, db: DbSessionDep) -> UserPublic:
    user = auth_service.register_user(db, payload, response)
    return _to_public(user)


@router.post("/login", response_model=UserPublic)
def login(payload: LoginRequest, response: Response, db: DbSessionDep) -> UserPublic:
    user = auth_service.login_user(db, payload.email, payload.password, response)
    return _to_public(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: DbSessionDep,
    session_cookie: str | None = Cookie(default=None, alias=settings.cookie_name),
) -> Response:
    session_id = None
    if session_cookie:
        session_id = read_session_cookie(
            session_cookie, max_age_seconds=session_ttl_seconds()
        )
    auth_service.logout_user(db, session_id, response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
def forgot_password(payload: ForgotPasswordRequest, db: DbSessionDep) -> Response:
    raw_token = auth_service.request_password_reset(db, payload.email)
    if raw_token is not None:
        # In dev, log the token so the developer can use it from the console.
        from app.core.logging import get_logger

        get_logger("auth").info(
            "password_reset_token_issued",
            email=payload.email,
            reset_token=raw_token,
        )
    # Always 204 regardless of whether the user exists.
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(payload: ResetPasswordRequest, db: DbSessionDep) -> Response:
    auth_service.reset_password(db, payload.token, payload.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
"""Authentication-related business logic."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ApiError
from app.core.security import (
    hash_password,
    hash_reset_token,
    issue_session_cookie,
    new_reset_token,
    reset_token_expiry,
    utcnow,
    verify_password,
)
from app.models.session import Session as DbSession
from app.models.user import User
from app.repositories import user_repo
from app.schemas.user import UserCreate, UserUpdate

_SESSION_TTL = timedelta(hours=settings.session_ttl_hours)


def _create_session(db: Session, user: User) -> DbSession:
    now = utcnow()
    db_session = DbSession(
        user_id=user.id,
        created_at=now,
        expires_at=now + _SESSION_TTL,
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


def _attach_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=issue_session_cookie(session_id),
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


def register_user(db: Session, payload: UserCreate, response: Response) -> User:
    """Create a user, ensure the email is unique, and issue a session cookie."""
    if user_repo.get_user_by_email(db, payload.email) is not None:
        raise ApiError(
            "CONFLICT",
            "An account with that email already exists.",
            http_status=409,
        )

    user = user_repo.create_user(
        db,
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        home_country=payload.home_country,
        home_currency=payload.home_currency,
        display_currency=payload.display_currency,
    )

    db_session = _create_session(db, user)
    _attach_cookie(response, db_session.id)
    return user


def login_user(db: Session, email: str, password: str, response: Response) -> User:
    """Verify credentials and issue a fresh session cookie.

    Always returns 401 on any failure to prevent email enumeration.
    """
    user = user_repo.get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        raise ApiError(
            "UNAUTHENTICATED",
            "Invalid email or password.",
            http_status=401,
        )

    db_session = _create_session(db, user)
    _attach_cookie(response, db_session.id)
    return user


def logout_user(db: Session, session_id: str | None, response: Response) -> None:
    """Revoke the server-side session and clear the cookie."""
    if session_id:
        db_session = db.get(DbSession, session_id)
        if db_session is not None:
            db.delete(db_session)
            db.commit()
    response.delete_cookie(key=settings.cookie_name, path="/")


def request_password_reset(db: Session, email: str) -> str | None:
    """Generate a reset token if the user exists. Returns the raw token only
    when running in non-production so the developer can use it from the logs.
    """
    user = user_repo.get_user_by_email(db, email)
    if user is None:
        return None

    raw, hashed = new_reset_token()
    user.password_reset_token_hash = hashed
    user.password_reset_expires_at = reset_token_expiry().isoformat()
    db.commit()
    return raw if not settings.is_production else None


def reset_password(db: Session, token: str, new_password: str) -> None:
    token_hash = hash_reset_token(token)
    user = (
        db.query(User)
        .filter(User.password_reset_token_hash == token_hash)
        .one_or_none()
    )
    if user is None:
        raise ApiError(
            "UNAUTHENTICATED",
            "Reset token is invalid or has expired.",
            http_status=401,
        )

    expires_at_raw = user.password_reset_expires_at
    if expires_at_raw is None:
        raise ApiError(
            "UNAUTHENTICATED",
            "Reset token is invalid or has expired.",
            http_status=401,
        )
    expires_at = datetime.fromisoformat(expires_at_raw)
    if expires_at < datetime.now(timezone.utc):
        raise ApiError(
            "UNAUTHENTICATED",
            "Reset token is invalid or has expired.",
            http_status=401,
        )

    user.password_hash = hash_password(new_password)
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None
    db.commit()


def update_profile(db: Session, user: User, payload: UserUpdate) -> User:
    return user_repo.update_user(
        db,
        user,
        name=payload.name,
        home_country=payload.home_country,
        home_currency=payload.home_currency,
        display_currency=payload.display_currency,
    )
"""FastAPI dependencies: database session and current-user resolution."""

from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.errors import ApiError
from app.core.security import read_session_cookie, session_ttl_seconds
from app.models.session import Session as DbSession
from app.models.user import User
from app.repositories.user_repo import get_user_by_id

DbSessionDep = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSessionDep,
    session_cookie: Annotated[str | None, Cookie(alias=settings.cookie_name)] = None,
) -> User:
    """Resolve the current user from the session cookie. 401 on any failure.

    This is the only path to a User object in request handlers. Always use
    this dependency to enforce authentication.
    """
    if not session_cookie:
        raise ApiError(
            "UNAUTHENTICATED",
            "Authentication required.",
            http_status=401,
        )

    session_id = read_session_cookie(session_cookie, max_age_seconds=session_ttl_seconds())
    if not session_id:
        raise ApiError(
            "UNAUTHENTICATED",
            "Session is invalid or has expired.",
            http_status=401,
        )

    db_session = db.get(DbSession, session_id)
    if db_session is None:
        raise ApiError("UNAUTHENTICATED", "Session not found.", http_status=401)

    user = get_user_by_id(db, db_session.user_id)
    if user is None:
        raise ApiError("UNAUTHENTICATED", "User no longer exists.", http_status=401)

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
"""Password hashing, session signing, and token utilities."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from passlib.context import CryptContext

from app.core.config import settings

# bcrypt cost 12 per spec §13.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Serializer for signed session cookies.
# Uses the secret_key plus a stable salt; rotate the salt to force-invalidate
# outstanding cookies if you ever need to.
_serializer = URLSafeTimedSerializer(
    secret_key=settings.secret_key,
    salt="beyond-borders.session",
)


# ---------- Passwords ----------
def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _pwd_context.verify(plain, hashed)
    except Exception:
        return False


# ---------- Session cookie ----------
def issue_session_cookie(session_id: str) -> str:
    """Sign a session ID for placement in the cookie."""
    return _serializer.dumps(session_id)


def read_session_cookie(value: str, max_age_seconds: int) -> str | None:
    """Return the session ID from a signed cookie, or None on any failure."""
    try:
        return _serializer.loads(value, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None


def session_ttl_seconds() -> int:
    return settings.session_ttl_hours * 3600


# ---------- Password reset ----------
def new_reset_token() -> tuple[str, str]:
    """Generate a (raw_token, hashed_token) pair. The raw token is shown to
    the user once and the hash is stored. Comparing hashes avoids storing the
    raw token at rest."""
    raw = secrets.token_urlsafe(32)
    return raw, _hash_token(raw)


def hash_reset_token(raw: str) -> str:
    return _hash_token(raw)


def reset_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=settings.reset_token_ttl_hours)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---------- Misc ----------
def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def isoformat(dt: datetime) -> str:
    """ISO 8601 with UTC offset."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def add_ttl(any_obj: Any, **kwargs: Any) -> Any:  # pragma: no cover - placeholder
    return any_obj
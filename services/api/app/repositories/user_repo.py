"""User repository functions. Always scope queries by user_id where applicable."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    stmt = select(User).where(User.email == email.lower())
    return db.execute(stmt).scalar_one_or_none()


def create_user(
    db: Session,
    *,
    email: str,
    password_hash: str,
    name: str,
    home_country: str | None,
    home_currency: str,
    display_currency: str,
) -> User:
    user = User(
        email=email.lower(),
        password_hash=password_hash,
        name=name,
        home_country=home_country,
        home_currency=home_currency,
        display_currency=display_currency,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, **fields: object) -> User:
    for key, value in fields.items():
        if value is not None and hasattr(user, key):
            setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user
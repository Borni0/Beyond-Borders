"""Pytest fixtures: in-memory SQLite DB, FastAPI test client."""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Override environment BEFORE importing the app so pydantic-settings picks
# these up. We use a fixed secret to keep signed cookies stable across tests.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-please-do-not-use-in-prod-32b")
os.environ.setdefault("FRONTEND_ORIGIN", "http://localhost:3000")
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("SESSION_TTL_HOURS", "24")
os.environ.setdefault("LOG_LEVEL", "WARNING")

from app.core import db as db_module  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.db import Base  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _build_test_engine() -> Iterator[None]:
    """Swap the production engine for a shared in-memory SQLite one."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )

    db_module.engine = test_engine
    db_module.SessionLocal = TestingSessionLocal
    Base.metadata.create_all(test_engine)
    yield
    test_engine.dispose()


@pytest.fixture()
def db(_build_test_engine: None) -> Iterator[Session]:
    """Per-test DB session wrapped in a transaction that's rolled back."""
    connection = db_module.engine.connect()
    transaction = connection.begin()
    session = db_module.SessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db: Session) -> Iterator[TestClient]:
    """FastAPI test client that overrides get_db with the per-test session."""
    from contextlib import asynccontextmanager

    from app.core.deps import get_db

    def _override_get_db() -> Iterator[Session]:
        try:
            yield db
        finally:
            pass

    # A no-op lifespan keeps tests independent of the production startup
    # handler (which logs and reads from the real DB URL).
    @asynccontextmanager
    async def _noop_lifespan(_app):  # type: ignore[no-untyped-def]
        yield

    app = create_app()
    app.router.lifespan_context = _noop_lifespan
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def settings() -> Any:
    return get_settings()

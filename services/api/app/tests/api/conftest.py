"""API test fixtures: a logged-in client for the v1 endpoints."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.fixture()
def auth_client(client: TestClient, db: Session) -> Iterator[TestClient]:
    """A client that has already registered + logged in a fresh user."""
    payload = {
        "email": "alice@example.com",
        "password": "CorrectHorse-9!Battery",
        "name": "Alice Tester",
        "home_country": "US",
        "home_currency": "USD",
        "display_currency": "USD",
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201, res.text
    return client


def make_user(client: TestClient, *, email: str, name: str = "User") -> str:
    """Helper: register a fresh user; return their id (read from /users/me)."""
    payload = {
        "email": email,
        "password": "CorrectHorse-9!Battery",
        "name": name,
        "home_country": "US",
        "home_currency": "USD",
        "display_currency": "USD",
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201, res.text
    me = client.get("/api/v1/users/me")
    assert me.status_code == 200, me.text
    return me.json()["id"]

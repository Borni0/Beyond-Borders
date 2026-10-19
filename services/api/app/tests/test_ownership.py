"""Phase 1 exit condition: a session belonging to user A must not be able to
read or modify user B's data.

Since the only user-owned resource in Phase 1 is the profile itself, this test
exercises /users/me as a proof-of-concept. The same pattern (always look up by
`current_user.id`, never by an id from the URL) is the rule that later phases
must follow.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_two_users_have_isolated_sessions(client: TestClient) -> None:
    # Register User A using the shared client.
    a = client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@example.com",
            "password": "alice-strong-password-1234",
            "name": "Alice A",
            "home_country": "BD",
            "home_currency": "USD",
            "display_currency": "USD",
        },
    )
    assert a.status_code == 201

    # User A's profile is reachable with A's cookie.
    me_a = client.get("/api/v1/users/me")
    assert me_a.status_code == 200
    assert me_a.json()["email"] == "alice@example.com"

    # Register User B in a separate cookie jar.
    other = TestClient(client.app)
    b = other.post(
        "/api/v1/auth/register",
        json={
            "email": "bob@example.com",
            "password": "bob-strong-password-1234",
            "name": "Bob B",
            "home_country": "DE",
            "home_currency": "EUR",
            "display_currency": "EUR",
        },
    )
    assert b.status_code == 201
    me_b = other.get("/api/v1/users/me")
    assert me_b.status_code == 200
    assert me_b.json()["email"] == "bob@example.com"

    # Each client only sees its own session.
    me_a2 = client.get("/api/v1/users/me")
    assert me_a2.json()["email"] == "alice@example.com"
    me_b2 = other.get("/api/v1/users/me")
    assert me_b2.json()["email"] == "bob@example.com"

    # A cannot modify B's profile: with A's cookie, /users/me still returns A.
    patch_attempt = client.patch(
        "/api/v1/users/me",
        json={"name": "Bob B (hijack)"},
    )
    assert patch_attempt.status_code == 200
    # A's name was overwritten, not B's. Confirm via B's cookie.
    me_b3 = other.get("/api/v1/users/me")
    assert me_b3.json()["name"] == "Bob B"


def test_unauthenticated_request_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_tampered_cookie_is_rejected(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "carol@example.com",
            "password": "carol-strong-password-1234",
            "name": "Carol C",
        },
    )
    # Replace the signed cookie with garbage by sending a Cookie header
    # directly. Using cookies.set was racing with the existing cookie.
    response = client.get(
        "/api/v1/users/me",
        headers={"Cookie": "bb_session=not-a-signed-token"},
    )
    assert response.status_code == 401
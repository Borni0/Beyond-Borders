"""Auth flow tests: register, login, me, logout, password rules."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _register_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "email": "alex@example.com",
        "password": "correct-horse-battery-staple",
        "name": "Alex Student",
        "home_country": "BD",
        "home_currency": "USD",
        "display_currency": "USD",
    }
    base.update(overrides)
    return base


def test_register_creates_user_and_sets_cookie(client: TestClient) -> None:
    response = client.post("/api/v1/auth/register", json=_register_payload())
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "alex@example.com"
    assert body["name"] == "Alex Student"
    assert "password" not in body
    assert "password_hash" not in body
    assert "bb_session" in response.cookies


def test_register_rejects_short_password(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json=_register_payload(password="short"),
    )
    assert response.status_code == 400
    err = response.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert "password" in err.get("details", {})


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    first = client.post("/api/v1/auth/register", json=_register_payload())
    assert first.status_code == 201
    second = client.post("/api/v1/auth/register", json=_register_payload())
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "CONFLICT"


def test_login_success(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=_register_payload())
    client.cookies.clear()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "alex@example.com", "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "alex@example.com"
    assert "bb_session" in response.cookies


def test_login_wrong_password_returns_401(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=_register_payload())
    client.cookies.clear()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "alex@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_login_unknown_email_returns_401(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "noone@example.com", "password": "whatever-1234567890"},
    )
    assert response.status_code == 401


def test_me_returns_current_user(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=_register_payload())
    response = client.get("/api/v1/users/me")
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "alex@example.com"
    assert body["home_currency"] == "USD"


def test_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_logout_revokes_session(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=_register_payload())
    assert client.get("/api/v1/users/me").status_code == 200
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 204
    # After logout the session is revoked server-side.
    assert client.get("/api/v1/users/me").status_code == 401


def test_patch_me_updates_profile(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=_register_payload())
    response = client.patch(
        "/api/v1/users/me",
        json={"name": "Alex Renamed", "display_currency": "EUR"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Alex Renamed"
    assert body["display_currency"] == "EUR"


def test_forgot_password_returns_204_even_for_unknown_email(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "nobody@example.com"},
    )
    assert response.status_code == 204


def test_reset_password_rejects_invalid_token(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "not-a-real-token", "new_password": "another-long-password"},
    )
    assert response.status_code == 401
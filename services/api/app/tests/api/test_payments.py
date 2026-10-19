"""Tests for /api/v1/payments endpoints."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient


def _make_plan(client: TestClient) -> str:
    res = client.post(
        "/api/v1/study-plans",
        json={
            "name": "Test",
            "base_currency": "USD",
            "start_date": "2026-09-01",
            "duration_months": 24,
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_create_list_update_delete_payment(auth_client: TestClient) -> None:
    plan_id = _make_plan(auth_client)
    due = (date.today() + timedelta(days=10)).isoformat()
    res = auth_client.post(
        "/api/v1/payments",
        json={
            "title": "Tuition deposit",
            "category": "tuition",
            "amount": "500.00",
            "currency": "USD",
            "due_date": due,
            "status": "planned",
            "plan_id": plan_id,
        },
    )
    assert res.status_code == 201, res.text
    evt = res.json()
    assert evt["display_status"] == "planned"
    assert evt["plan_id"] == plan_id
    event_id = evt["id"]

    res = auth_client.get("/api/v1/payments")
    assert res.status_code == 200
    assert len(res.json()) == 1

    res = auth_client.get(f"/api/v1/payments?plan_id={plan_id}")
    assert res.status_code == 200
    assert len(res.json()) == 1

    res = auth_client.patch(
        f"/api/v1/payments/{event_id}", json={"status": "paid"}
    )
    assert res.status_code == 200
    assert res.json()["status" if False else "display_status"] == "paid"

    res = auth_client.delete(f"/api/v1/payments/{event_id}")
    assert res.status_code == 204


def test_overdue_is_derived_not_stored(auth_client: TestClient) -> None:
    plan_id = _make_plan(auth_client)
    past = (date.today() - timedelta(days=5)).isoformat()
    res = auth_client.post(
        "/api/v1/payments",
        json={
            "title": "Late rent",
            "category": "accommodation",
            "amount": "900.00",
            "currency": "USD",
            "due_date": past,
            "status": "planned",
            "plan_id": plan_id,
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    # The stored status is "planned" (not "overdue" — overdue is display-only).
    # The API returns display_status=overdue for the read.
    assert body["display_status"] == "overdue"

    res = auth_client.get(f"/api/v1/payments?plan_id={plan_id}")
    assert res.json()[0]["display_status"] == "overdue"


def test_payment_owner_isolation(client: TestClient) -> None:
    """User A creates a payment, User B (different cookie jar) cannot see it."""
    # User A
    a = client.post(
        "/api/v1/auth/register",
        json={
            "email": "a@example.com",
            "password": "CorrectHorse-9!Battery",
            "name": "A",
            "home_country": "US",
            "home_currency": "USD",
            "display_currency": "USD",
        },
    )
    assert a.status_code == 201, a.text
    plan_id = client.post(
        "/api/v1/study-plans",
        json={
            "name": "A plan",
            "base_currency": "USD",
            "start_date": "2026-09-01",
            "duration_months": 24,
        },
    ).json()["id"]
    create = client.post(
        "/api/v1/payments",
        json={
            "title": "Visa fee",
            "category": "visa",
            "amount": "100.00",
            "currency": "USD",
            "due_date": "2026-12-01",
        },
    )
    assert create.status_code == 201, create.text
    a_event_id = create.json()["id"]

    # Logout, register User B in a separate client
    client.post("/api/v1/auth/logout")
    b = client.post(
        "/api/v1/auth/register",
        json={
            "email": "b@example.com",
            "password": "CorrectHorse-9!Battery",
            "name": "B",
            "home_country": "US",
            "home_currency": "USD",
            "display_currency": "USD",
        },
    )
    assert b.status_code == 201, b.text

    res = client.get("/api/v1/payments")
    assert res.status_code == 200
    assert res.json() == []

    res = client.patch(
        f"/api/v1/payments/{a_event_id}", json={"status": "paid"}
    )
    assert res.status_code == 404

    res = client.delete(f"/api/v1/payments/{a_event_id}")
    assert res.status_code == 404

    # Plan scoped query should not return other users' data either
    res = client.get(f"/api/v1/payments?plan_id={plan_id}")
    assert res.status_code == 200
    assert res.json() == []


def test_invalid_status_rejected(auth_client: TestClient) -> None:
    res = auth_client.post(
        "/api/v1/payments",
        json={
            "title": "X",
            "category": "tuition",
            "amount": "100.00",
            "currency": "USD",
            "due_date": date.today().isoformat(),
            "status": "definitely-not-real",
        },
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"

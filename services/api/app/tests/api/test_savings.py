"""Tests for /api/v1/savings-goals endpoints."""

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


def test_create_list_update_delete_goal(auth_client: TestClient) -> None:
    plan_id = _make_plan(auth_client)
    target = (date.today() + timedelta(days=365)).isoformat()
    res = auth_client.post(
        "/api/v1/savings-goals",
        json={
            "name": "First year",
            "target_amount": "12000.00",
            "current_amount": "1500.00",
            "currency": "USD",
            "target_date": target,
            "plan_id": plan_id,
        },
    )
    assert res.status_code == 201, res.text
    goal = res.json()
    assert goal["current_amount"] == "1500.0000"
    goal_id = goal["id"]

    res = auth_client.get("/api/v1/savings-goals")
    assert res.status_code == 200
    assert len(res.json()) == 1

    res = auth_client.patch(
        f"/api/v1/savings-goals/{goal_id}", json={"current_amount": "3000.00"}
    )
    assert res.status_code == 200
    assert float(res.json()["current_amount"]) == 3000.0

    res = auth_client.delete(f"/api/v1/savings-goals/{goal_id}")
    assert res.status_code == 204


def test_goal_owner_isolation(client: TestClient) -> None:
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
    assert a.status_code == 201
    res = client.post(
        "/api/v1/savings-goals",
        json={
            "name": "Hidden goal",
            "target_amount": "1000.00",
            "currency": "USD",
            "target_date": (date.today() + timedelta(days=30)).isoformat(),
        },
    )
    assert res.status_code == 201
    a_goal_id = res.json()["id"]

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
    assert b.status_code == 201

    res = client.get("/api/v1/savings-goals")
    assert res.status_code == 200
    assert res.json() == []

    res = client.patch(
        f"/api/v1/savings-goals/{a_goal_id}", json={"current_amount": "5.00"}
    )
    assert res.status_code == 404

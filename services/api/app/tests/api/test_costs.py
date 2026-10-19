"""Tests for /api/v1/plans/{id}/costs endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _make_plan(client: TestClient) -> str:
    res = client.post(
        "/api/v1/study-plans",
        json={
            "name": "Test Plan",
            "base_currency": "USD",
            "start_date": "2026-09-01",
            "duration_months": 24,
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_create_list_update_delete_cost(auth_client: TestClient) -> None:
    plan_id = _make_plan(auth_client)

    # Create
    res = auth_client.post(
        f"/api/v1/plans/{plan_id}/costs",
        json={
            "category": "accommodation",
            "description": "Rent",
            "amount": "900.00",
            "currency": "USD",
            "frequency": "monthly",
        },
    )
    assert res.status_code == 201, res.text
    cost = res.json()
    assert cost["amount"] == "900.0000"  # SQLAlchemy numeric
    cost_id = cost["id"]

    # List
    res = auth_client.get(f"/api/v1/plans/{plan_id}/costs")
    assert res.status_code == 200
    assert len(res.json()) == 1

    # Update
    res = auth_client.patch(
        f"/api/v1/plans/{plan_id}/costs/{cost_id}",
        json={"amount": "950.00"},
    )
    assert res.status_code == 200
    # The DB column has 4 dp; check the float-friendly comparison.
    assert float(res.json()["amount"]) == 950.0

    # Delete
    res = auth_client.delete(f"/api/v1/plans/{plan_id}/costs/{cost_id}")
    assert res.status_code == 204

    res = auth_client.get(f"/api/v1/plans/{plan_id}/costs")
    assert res.json() == []


def test_one_time_cost_with_date(auth_client: TestClient) -> None:
    plan_id = _make_plan(auth_client)
    res = auth_client.post(
        f"/api/v1/plans/{plan_id}/costs",
        json={
            "category": "tuition",
            "amount": "15000.00",
            "currency": "USD",
            "frequency": "one_time",
            "is_one_time": True,
            "start_date": "2026-09-01",
        },
    )
    assert res.status_code == 201
    assert res.json()["is_one_time"] is True


def test_refundable_deposit(auth_client: TestClient) -> None:
    plan_id = _make_plan(auth_client)
    res = auth_client.post(
        f"/api/v1/plans/{plan_id}/costs",
        json={
            "category": "deposits",
            "amount": "2000.00",
            "currency": "USD",
            "frequency": "one_time",
            "is_one_time": True,
            "is_refundable": True,
            "start_date": "2026-08-15",
        },
    )
    assert res.status_code == 201
    assert res.json()["is_refundable"] is True


def test_invalid_frequency_rejected(auth_client: TestClient) -> None:
    plan_id = _make_plan(auth_client)
    res = auth_client.post(
        f"/api/v1/plans/{plan_id}/costs",
        json={
            "category": "tuition",
            "amount": "100.00",
            "currency": "USD",
            "frequency": "biweekly",  # not in the literal
        },
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_plan_404_returns_404(auth_client: TestClient) -> None:
    res = auth_client.get("/api/v1/plans/does-not-exist/costs")
    assert res.status_code == 404


def test_due_before_departure_round_trips(auth_client: TestClient) -> None:
    """The due_before_departure flag must accept, persist, and echo back."""
    plan_id = _make_plan(auth_client)
    res = auth_client.post(
        f"/api/v1/plans/{plan_id}/costs",
        json={
            "category": "deposits",
            "amount": "1000.00",
            "currency": "USD",
            "frequency": "one_time",
            "is_one_time": True,
            "due_before_departure": True,
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["due_before_departure"] is True

    # Default (omitted) is False
    res = auth_client.post(
        f"/api/v1/plans/{plan_id}/costs",
        json={
            "category": "accommodation",
            "amount": "800.00",
            "currency": "USD",
            "frequency": "monthly",
        },
    )
    assert res.status_code == 201
    assert res.json()["due_before_departure"] is False


def test_due_before_departure_counts_in_upfront_window(
    auth_client: TestClient,
) -> None:
    """End-to-end: a cost flagged due_before_departure with no start_date
    must still be counted in the upfront-cash requirement."""
    plan_id = _make_plan(auth_client)
    res = auth_client.post(
        f"/api/v1/plans/{plan_id}/costs",
        json={
            "category": "deposits",
            "amount": "500.00",
            "currency": "USD",
            "frequency": "one_time",
            "is_one_time": True,
            "due_before_departure": True,
        },
    )
    assert res.status_code == 201, res.text

    res = auth_client.get(
        f"/api/v1/plans/{plan_id}/readiness?upfront_window_days=30"
    )
    assert res.status_code == 200
    body = res.json()
    assert float(body["upfront_cash_requirement"]) == 500.0

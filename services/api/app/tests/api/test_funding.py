"""Tests for /api/v1/plans/{id}/funding endpoints."""

from __future__ import annotations

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


def test_create_list_update_delete_funding(auth_client: TestClient) -> None:
    plan_id = _make_plan(auth_client)
    res = auth_client.post(
        f"/api/v1/plans/{plan_id}/funding",
        json={
            "name": "Family savings",
            "funding_type": "savings",
            "amount": "20000.00",
            "currency": "USD",
            "status": "confirmed",
        },
    )
    assert res.status_code == 201, res.text
    src = res.json()
    assert src["status"] == "confirmed"
    src_id = src["id"]

    res = auth_client.get(f"/api/v1/plans/{plan_id}/funding")
    assert res.status_code == 200
    assert len(res.json()) == 1

    res = auth_client.patch(
        f"/api/v1/plans/{plan_id}/funding/{src_id}",
        json={"amount": "25000.00"},
    )
    assert res.status_code == 200
    assert float(res.json()["amount"]) == 25000.0

    res = auth_client.delete(f"/api/v1/plans/{plan_id}/funding/{src_id}")
    assert res.status_code == 204


def test_invalid_status_rejected(auth_client: TestClient) -> None:
    plan_id = _make_plan(auth_client)
    res = auth_client.post(
        f"/api/v1/plans/{plan_id}/funding",
        json={
            "name": "X",
            "funding_type": "savings",
            "amount": "100.00",
            "currency": "USD",
            "status": "maybe",  # not in literal
        },
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"

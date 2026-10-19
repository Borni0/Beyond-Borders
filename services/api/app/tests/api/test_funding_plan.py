"""Tests for the /api/v1/plans/{id}/funding-plan aggregate endpoints."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient


def _make_plan(client: TestClient, base_currency: str = "USD") -> str:
    res = client.post(
        "/api/v1/study-plans",
        json={
            "name": "Test",
            "base_currency": base_currency,
            "start_date": "2026-09-01",
            "duration_months": 24,
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_summary_includes_buckets_and_totals(auth_client: TestClient) -> None:
    plan_id = _make_plan(auth_client)
    today = date.today()

    # Two funding sources, one confirmed and one conditional
    auth_client.post(
        f"/api/v1/plans/{plan_id}/funding",
        json={
            "name": "Savings",
            "funding_type": "savings",
            "amount": "10000.00",
            "currency": "USD",
            "status": "confirmed",
        },
    )
    auth_client.post(
        f"/api/v1/plans/{plan_id}/funding",
        json={
            "name": "Scholarship",
            "funding_type": "scholarship",
            "amount": "5000.00",
            "currency": "USD",
            "status": "conditional",
            "expected_date": (today + timedelta(days=60)).isoformat(),
        },
    )

    # One upcoming + one overdue payment
    auth_client.post(
        "/api/v1/payments",
        json={
            "title": "Tuition",
            "category": "tuition",
            "amount": "1500.00",
            "currency": "USD",
            "due_date": (today + timedelta(days=14)).isoformat(),
            "status": "planned",
            "plan_id": plan_id,
        },
    )
    auth_client.post(
        "/api/v1/payments",
        json={
            "title": "Late visa fee",
            "category": "visa",
            "amount": "200.00",
            "currency": "USD",
            "due_date": (today - timedelta(days=3)).isoformat(),
            "status": "planned",
            "plan_id": plan_id,
        },
    )

    # Savings goal
    auth_client.post(
        "/api/v1/savings-goals",
        json={
            "name": "First year",
            "target_amount": "12000.00",
            "current_amount": "2000.00",
            "currency": "USD",
            "target_date": (today + timedelta(days=300)).isoformat(),
            "plan_id": plan_id,
        },
    )

    res = auth_client.get(f"/api/v1/plans/{plan_id}/funding-plan/summary")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["base_currency"] == "USD"
    # 1 overdue + 1 upcoming
    assert body["upcoming_payments_count"] == 1
    assert body["overdue_payments_count"] == 1
    assert float(body["upcoming_payments"]) == 1500.0
    assert float(body["overdue_payments"]) == 200.0

    # Funding buckets — single USD currency
    assert len(body["buckets"]) == 1
    bucket = body["buckets"][0]
    assert bucket["currency"] == "USD"
    assert float(bucket["confirmed"]) == 10000.0
    assert float(bucket["conditional"]) == 5000.0
    assert float(bucket["total"]) == 15000.0

    # Savings buckets — single USD currency
    assert len(body["savings_buckets"]) == 1
    sav = body["savings_buckets"][0]
    assert sav["currency"] == "USD"
    assert float(sav["target_total"]) == 12000.0
    assert float(sav["current_total"]) == 2000.0

    # The overdue note should appear
    assert any("past due" in n.lower() for n in body["notes"])


def test_timeline_projects_recurring_events(auth_client: TestClient) -> None:
    plan_id = _make_plan(auth_client)
    today = date.today()
    auth_client.post(
        "/api/v1/payments",
        json={
            "title": "Monthly rent",
            "category": "accommodation",
            "amount": "800.00",
            "currency": "USD",
            "due_date": (today + timedelta(days=5)).isoformat(),
            "status": "planned",
            "is_recurring": True,
            "recurrence_frequency": "monthly",
            "plan_id": plan_id,
        },
    )
    res = auth_client.get(f"/api/v1/plans/{plan_id}/funding-plan/timeline")
    assert res.status_code == 200, res.text
    entries = res.json()["entries"]
    # 1 stored occurrence + at least 11 monthly projections within 12 months
    assert len(entries) >= 12
    assert all(e["is_recurring"] for e in entries)


def test_convert_uses_user_fx_table(auth_client: TestClient) -> None:
    plan_id = _make_plan(auth_client, base_currency="USD")
    # Add a USD->EUR rate: 1 USD = 0.9 EUR
    res = auth_client.put(
        "/api/v1/fx",
        json={
            "base_currency": "USD",
            "quote_currency": "EUR",
            "rate": "0.9",
            "rate_type": "user_entered",
            "observed_at": date.today().isoformat(),
        },
    )
    assert res.status_code == 200, res.text

    res = auth_client.post(
        f"/api/v1/plans/{plan_id}/funding-plan/convert",
        json={
            "from_amount": "1000.00",
            "from_currency": "USD",
            "to_currency": "EUR",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["from_currency"] == "USD"
    assert body["to_currency"] == "EUR"
    # 1000 USD * 0.9 = 900 EUR, then 1% fee = 9 EUR, total 909 EUR
    assert float(body["converted_amount"]) == 900.0
    assert float(body["fee_amount"]) == 9.0
    assert float(body["total_cost"]) == 909.0


def test_convert_uses_inverse_rate(auth_client: TestClient) -> None:
    plan_id = _make_plan(auth_client)
    # User has only USD->EUR. Inverse should be available for EUR->USD.
    auth_client.put(
        "/api/v1/fx",
        json={
            "base_currency": "USD",
            "quote_currency": "EUR",
            "rate": "0.9",
            "rate_type": "user_entered",
            "observed_at": date.today().isoformat(),
        },
    )
    res = auth_client.post(
        f"/api/v1/plans/{plan_id}/funding-plan/convert",
        json={
            "from_amount": "900.00",
            "from_currency": "EUR",
            "to_currency": "USD",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    # 900 EUR * (1/0.9) ≈ 1000 USD, fee 10 USD, total 1010 USD
    assert float(body["converted_amount"]) == 1000.0


def test_csv_export(auth_client: TestClient) -> None:
    plan_id = _make_plan(auth_client)
    auth_client.post(
        "/api/v1/payments",
        json={
            "title": "Housing deposit",
            "category": "deposits",
            "amount": "2000.00",
            "currency": "USD",
            "due_date": date.today().isoformat(),
            "status": "planned",
            "plan_id": plan_id,
        },
    )
    res = auth_client.get(f"/api/v1/plans/{plan_id}/funding-plan/export.csv")
    assert res.status_code == 200, res.text
    text = res.text
    # header + 1 row
    lines = [ln for ln in text.splitlines() if ln.strip()]
    assert len(lines) == 2
    assert "title,category,amount,currency" in lines[0]
    assert "Housing deposit" in lines[1]
    assert "Content-Disposition" in res.headers

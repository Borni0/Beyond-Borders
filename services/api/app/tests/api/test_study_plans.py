"""Tests for /api/v1/study-plans CRUD endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.tests.api.conftest import make_user


def test_list_empty(auth_client: TestClient) -> None:
    res = auth_client.get("/api/v1/study-plans")
    assert res.status_code == 200
    assert res.json() == []


def test_create_get_update_delete(auth_client: TestClient) -> None:
    payload = {
        "name": "MSc in Berlin",
        "destination_country": "DE",
        "base_currency": "USD",
        "start_date": "2026-09-01",
        "duration_months": 24,
        "notes": "TU Berlin, CS",
    }
    res = auth_client.post("/api/v1/study-plans", json=payload)
    assert res.status_code == 201, res.text
    plan = res.json()
    assert plan["name"] == "MSc in Berlin"
    assert plan["end_date"]  # auto-computed
    plan_id = plan["id"]

    # Get by id
    res = auth_client.get(f"/api/v1/study-plans/{plan_id}")
    assert res.status_code == 200
    assert res.json()["id"] == plan_id

    # PATCH the name + add a note
    res = auth_client.patch(
        f"/api/v1/study-plans/{plan_id}",
        json={"name": "MSc @ TU Berlin"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "MSc @ TU Berlin"

    # List contains the plan
    res = auth_client.get("/api/v1/study-plans")
    assert res.status_code == 200
    assert len(res.json()) == 1

    # Delete
    res = auth_client.delete(f"/api/v1/study-plans/{plan_id}")
    assert res.status_code == 204

    # And the next get is 404
    res = auth_client.get(f"/api/v1/study-plans/{plan_id}")
    assert res.status_code == 404


def test_end_date_computed_correctly(auth_client: TestClient) -> None:
    # 24 months from 2026-01-15 → 2028-01-15
    res = auth_client.post(
        "/api/v1/study-plans",
        json={
            "name": "x",
            "base_currency": "USD",
            "start_date": "2026-01-15",
            "duration_months": 24,
        },
    )
    assert res.status_code == 201
    assert res.json()["end_date"] == "2028-01-15"


def test_end_date_handles_jan_31_to_feb_28(auth_client: TestClient) -> None:
    # 2026-01-31 + 1 month → 2026-02-28 (not 2026-03-03).
    res = auth_client.post(
        "/api/v1/study-plans",
        json={
            "name": "x",
            "base_currency": "USD",
            "start_date": "2026-01-31",
            "duration_months": 1,
        },
    )
    assert res.status_code == 201
    assert res.json()["end_date"] == "2026-02-28"


def test_unauthenticated_rejected(client: TestClient) -> None:
    # The global fixture's `client` is not logged in.
    res = client.get("/api/v1/study-plans")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"


def test_other_user_cannot_see_plan(auth_client: TestClient) -> None:
    # Alice creates a plan.
    res = auth_client.post(
        "/api/v1/study-plans",
        json={
            "name": "Alice's plan",
            "base_currency": "USD",
            "start_date": "2026-09-01",
            "duration_months": 12,
        },
    )
    plan_id = res.json()["id"]

    # A fresh user (Bob) — different cookie, different DB row.
    make_user(auth_client, email="bob@example.com")
    # We need a new client to use Bob's cookie. The fixture re-uses the same
    # TestClient but a register call replaces the session cookie. So Bob's
    # register above logged Bob in on `auth_client`.

    res = auth_client.get(f"/api/v1/study-plans/{plan_id}")
    assert res.status_code == 404  # ownership-scoped
    res = auth_client.get("/api/v1/study-plans")
    assert res.json() == []  # no plans visible to Bob


def test_validation_error_envelope(auth_client: TestClient) -> None:
    # Missing required field "name".
    res = auth_client.post(
        "/api/v1/study-plans",
        json={"base_currency": "USD", "start_date": "2026-09-01",
              "duration_months": 12},
    )
    assert res.status_code == 400
    body = res.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "name" in body["error"]["details"]


def test_phase1_readiness_enrichment_fields_round_trip(
    auth_client: TestClient,
) -> None:
    """The Phase 1 readiness enrichment fields (institution, program,
    city, tuition, home_currency) must accept, persist, and echo back
    the values the user submitted."""
    payload = {
        "name": "MSc in Berlin",
        "destination_country": "DE",
        "base_currency": "USD",
        "home_currency": "BDT",
        "start_date": "2026-09-01",
        "duration_months": 24,
        "institution_name": "TU Berlin",
        "program_name": "MSc Computer Science",
        "city": "Berlin",
        "tuition_amount": "1500.00",
        "tuition_currency": "EUR",
        "notes": "Apply by Dec 1.",
    }
    res = auth_client.post("/api/v1/study-plans", json=payload)
    assert res.status_code == 201, res.text
    plan = res.json()
    assert plan["institution_name"] == "TU Berlin"
    assert plan["program_name"] == "MSc Computer Science"
    assert plan["city"] == "Berlin"
    assert plan["tuition_amount"] == "1500.0000"
    assert plan["tuition_currency"] == "EUR"
    assert plan["home_currency"] == "BDT"
    plan_id = plan["id"]

    # Patch one field at a time
    res = auth_client.patch(
        f"/api/v1/study-plans/{plan_id}",
        json={"city": "Munich", "tuition_amount": "1700.00"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["city"] == "Munich"
    assert body["tuition_amount"] == "1700.0000"
    # Untouched fields are preserved
    assert body["institution_name"] == "TU Berlin"
    assert body["home_currency"] == "BDT"


def test_phase1_readiness_enrichment_currencies_are_uppercased(
    auth_client: TestClient,
) -> None:
    """Currency codes are case-insensitive on input; storage is upper."""
    res = auth_client.post(
        "/api/v1/study-plans",
        json={
            "name": "lowercase currencies",
            "base_currency": "usd",
            "home_currency": "bdt",
            "tuition_currency": "eur",
            "start_date": "2026-09-01",
            "duration_months": 12,
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["base_currency"] == "USD"
    assert body["home_currency"] == "BDT"
    assert body["tuition_currency"] == "EUR"

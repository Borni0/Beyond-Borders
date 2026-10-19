"""Tests for the readiness endpoint: the integration of the full pipeline."""

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
    assert res.status_code == 201
    return res.json()["id"]


def test_readiness_empty_plan(auth_client: TestClient) -> None:
    plan_id = _make_plan(auth_client)
    res = auth_client.get(f"/api/v1/plans/{plan_id}/readiness")
    assert res.status_code == 200, res.text
    body = res.json()
    # No costs, no confirmed funding → NEEDS_MORE_INFORMATION.
    assert "needs_more_information" in body["statuses"]
    assert body["base_currency"] == "USD"


def test_readiness_fully_funded(auth_client: TestClient) -> None:
    plan_id = _make_plan(auth_client)
    # One monthly cost of $100 (24 months = $2400).
    auth_client.post(
        f"/api/v1/plans/{plan_id}/costs",
        json={
            "category": "accommodation",
            "amount": "100.00",
            "currency": "USD",
            "frequency": "monthly",
        },
    )
    # And $3000 confirmed savings.
    auth_client.post(
        f"/api/v1/plans/{plan_id}/funding",
        json={
            "name": "Savings",
            "funding_type": "savings",
            "amount": "3000.00",
            "currency": "USD",
            "status": "confirmed",
        },
    )
    res = auth_client.get(f"/api/v1/plans/{plan_id}/readiness")
    body = res.json()
    assert "no_modeled_shortfall" in body["statuses"]
    assert body["funding_surplus"] == "600.00"  # 3000 - 2400
    assert body["funding_gap"] == "0.00"


def test_readiness_with_funding_gap(auth_client: TestClient) -> None:
    plan_id = _make_plan(auth_client)
    # Cost: $5000 one-time.
    auth_client.post(
        f"/api/v1/plans/{plan_id}/costs",
        json={
            "category": "tuition",
            "amount": "5000.00",
            "currency": "USD",
            "frequency": "one_time",
            "is_one_time": True,
            "start_date": "2026-09-01",
        },
    )
    # Only $2000 confirmed → gap = 3000.
    auth_client.post(
        f"/api/v1/plans/{plan_id}/funding",
        json={
            "name": "X",
            "funding_type": "savings",
            "amount": "2000.00",
            "currency": "USD",
            "status": "confirmed",
        },
    )
    res = auth_client.get(f"/api/v1/plans/{plan_id}/readiness")
    body = res.json()
    assert "funding_gap_identified" in body["statuses"]
    assert body["funding_gap"] == "3000.00"


def test_readiness_refundable_excluded(auth_client: TestClient) -> None:
    plan_id = _make_plan(auth_client)
    # $2000 refundable deposit should not affect the projected cost.
    auth_client.post(
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
    res = auth_client.get(f"/api/v1/plans/{plan_id}/readiness")
    body = res.json()
    # No real costs → projected = 0; deposit is in refundable bucket.
    assert body["breakdown"]["total_projected_cost"] == "0.00"
    assert body["breakdown"]["refundable_deposits"] == "2000.00"


def test_readiness_missing_fx_surfaces_missing_input(
    auth_client: TestClient,
) -> None:
    plan_id = _make_plan(auth_client)
    # Cost in EUR with no rate entered.
    auth_client.post(
        f"/api/v1/plans/{plan_id}/costs",
        json={
            "category": "accommodation",
            "amount": "800.00",
            "currency": "EUR",
            "frequency": "monthly",
        },
    )
    auth_client.post(
        f"/api/v1/plans/{plan_id}/funding",
        json={
            "name": "USD savings",
            "funding_type": "savings",
            "amount": "50000.00",
            "currency": "USD",
            "status": "confirmed",
        },
    )
    res = auth_client.get(f"/api/v1/plans/{plan_id}/readiness")
    body = res.json()
    assert "needs_more_information" in body["statuses"]
    assert any("EUR" in m and "USD" in m for m in body["missing_inputs"])


def test_readiness_with_fx_uses_rate(auth_client: TestClient) -> None:
    plan_id = _make_plan(auth_client)
    # EUR cost.
    auth_client.post(
        f"/api/v1/plans/{plan_id}/costs",
        json={
            "category": "accommodation",
            "amount": "800.00",
            "currency": "EUR",
            "frequency": "monthly",
        },
    )
    auth_client.post(
        f"/api/v1/plans/{plan_id}/funding",
        json={
            "name": "USD savings",
            "funding_type": "savings",
            "amount": "20000.00",
            "currency": "USD",
            "status": "confirmed",
        },
    )
    # Enter an EUR→USD rate of 0.9.
    auth_client.put(
        "/api/v1/fx",
        json={
            "base_currency": "EUR",
            "quote_currency": "USD",
            "rate": "0.9",
            "rate_type": "user_entered",
            "observed_at": "2026-01-01",
        },
    )
    res = auth_client.get(f"/api/v1/plans/{plan_id}/readiness")
    body = res.json()
    # 800 EUR * 24 = 19200 EUR * 0.9 = 17280 USD
    assert body["breakdown"]["total_projected_cost"] == "17280.00"
    # 20000 USD funding > 17280 → surplus 2720.
    assert body["funding_surplus"] == "2720.00"
    assert body["funding_gap"] == "0.00"
    # No NEEDS_MORE_INFORMATION anymore.
    assert "needs_more_information" not in body["statuses"]


def test_readiness_404_for_unknown_plan(auth_client: TestClient) -> None:
    res = auth_client.get("/api/v1/plans/does-not-exist/readiness")
    assert res.status_code == 404


def test_readiness_response_includes_phase1_enrichment_fields(
    auth_client: TestClient,
) -> None:
    """The /readiness payload must always include the Phase 1 enrichment
    fields, even when there are no costs (in which case coverage_pct is
    null)."""
    plan_id = _make_plan(auth_client)
    res = auth_client.get(f"/api/v1/plans/{plan_id}/readiness")
    assert res.status_code == 200, res.text
    body = res.json()
    for field in (
        "first_year_funding_gap",
        "coverage_pct",
        "potential_gap_after_expected",
    ):
        assert field in body, f"missing {field} in readiness response"
    assert body["coverage_pct"] is None  # no cost yet → no ratio


def test_readiness_response_with_costs_exposes_real_coverage(
    auth_client: TestClient,
) -> None:
    plan_id = _make_plan(auth_client)
    # 24 months of $100 rent + 24 months of $50 utilities = $3600.
    auth_client.post(
        f"/api/v1/plans/{plan_id}/costs",
        json={
            "category": "accommodation",
            "amount": "100.00",
            "currency": "USD",
            "frequency": "monthly",
        },
    )
    auth_client.post(
        f"/api/v1/plans/{plan_id}/costs",
        json={
            "category": "utilities",
            "amount": "50.00",
            "currency": "USD",
            "frequency": "monthly",
        },
    )
    # 2.5k confirmed + 500 conditional = 3k eligible → 3000/3600 = 83.33%.
    auth_client.post(
        f"/api/v1/plans/{plan_id}/funding",
        json={
            "name": "Savings",
            "funding_type": "savings",
            "amount": "2500.00",
            "currency": "USD",
            "status": "confirmed",
        },
    )
    auth_client.post(
        f"/api/v1/plans/{plan_id}/funding",
        json={
            "name": "Family",
            "funding_type": "family",
            "amount": "500.00",
            "currency": "USD",
            "status": "conditional",
        },
    )
    res = auth_client.get(f"/api/v1/plans/{plan_id}/readiness")
    assert res.status_code == 200
    body = res.json()
    assert body["coverage_pct"] == "83.33"
    # 24 months of $150/month = $3600, confirmed 2500, so first-year
    # gap is (12 * 150) - 2500 = 1800 - 2500 = 0. Funding fully covers
    # year 1; the gap is only across years 2+.
    assert float(body["first_year_funding_gap"]) == 0.0
    # Conditional pool 500 → potential_gap_after_expected = 500.
    assert body["potential_gap_after_expected"] == "500.00"

"""Persistence test: write a plan + costs + funding, then read it back.

The Phase 1 exit criterion (spec §16) explicitly includes: "the user can
create a plan, enter expenses and funding, receive reproducible
calculations, save the plan, reload the application, and see the same
saved data."

This test exercises the save/load round-trip end-to-end through the API.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient


def test_full_round_trip(auth_client: TestClient) -> None:
    # 1. Create a plan.
    plan_res = auth_client.post(
        "/api/v1/study-plans",
        json={
            "name": "MSc at TU Berlin",
            "destination_country": "DE",
            "base_currency": "USD",
            "start_date": "2026-09-01",
            "duration_months": 24,
        },
    )
    plan_id = plan_res.json()["id"]

    # 2. Add three costs.
    auth_client.post(
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
    auth_client.post(
        f"/api/v1/plans/{plan_id}/costs",
        json={
            "category": "accommodation",
            "amount": "900.00",
            "currency": "USD",
            "frequency": "monthly",
        },
    )
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

    # 3. Add two funding sources.
    auth_client.post(
        f"/api/v1/plans/{plan_id}/funding",
        json={
            "name": "Family savings",
            "funding_type": "savings",
            "amount": "20000.00",
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
            "expected_date": "2026-12-01",
        },
    )

    # 4. Compute readiness (snapshot #1).
    snap1 = auth_client.get(f"/api/v1/plans/{plan_id}/readiness").json()

    # 5. Simulate "reload": read everything back through the GET endpoints.
    plan_again = auth_client.get(f"/api/v1/study-plans/{plan_id}").json()
    costs_again = auth_client.get(f"/api/v1/plans/{plan_id}/costs").json()
    sources_again = auth_client.get(f"/api/v1/plans/{plan_id}/funding").json()
    snap2 = auth_client.get(f"/api/v1/plans/{plan_id}/readiness").json()

    # 6. The plan, costs, and funding all came back as written.
    assert plan_again["name"] == "MSc at TU Berlin"
    assert len(costs_again) == 3
    assert len(sources_again) == 2

    # 7. The readiness snapshot is byte-identical between calls. (JSON
    # re-serialization of floats must be stable.)
    assert json.dumps(snap1, sort_keys=True) == json.dumps(
        snap2, sort_keys=True
    ), "Readiness snapshot must be byte-identical on reload."

    # 8. The math is what we expect:
    #     - Tuition $15000 one-time
    #     - Rent $900/mo × 24 = $21600
    #     - Refundable $2000 (separate bucket, not in cost)
    #     - Total projected: $36600
    assert snap1["breakdown"]["total_projected_cost"] == "36600.00"
    assert snap1["breakdown"]["refundable_deposits"] == "2000.00"

    # 9. Funding:
    #     - $20000 confirmed (eligible + available_before_departure)
    #     - $5000 conditional (eligible_with_conditional, not eligible_confirmed)
    assert snap1["funding"]["confirmed_total"] == "20000.00"
    assert snap1["funding"]["conditional_total"] == "5000.00"
    assert snap1["funding"]["eligible_confirmed"] == "20000.00"
    assert snap1["funding"]["eligible_with_conditional"] == "25000.00"

    # 10. Gap = 36600 - 20000 = 16600.
    assert snap1["funding_gap"] == "16600.00"
    # 11. Surplus: max(0, 20000 - 36600) = 0.
    assert snap1["funding_surplus"] == "0.00"

    # 12. Status codes that should be present.
    assert "funding_gap_identified" in snap1["statuses"]
    assert "conditional_funding" in snap1["statuses"]
    assert "scenario_sensitive" in snap1["statuses"]

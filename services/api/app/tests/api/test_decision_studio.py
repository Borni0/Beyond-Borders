"""Tests for /api/v1/decision-studio/* endpoints.

Covers:

* Happy-path ad-hoc compare of 2 and 3 plans.
* Scenario application (rent increase, scholarship reduction, custom note).
* Cross-plan warnings (different currencies, different durations, no
  payments).
* Saved-comparison CRUD (create, list, get-recompute, patch, delete).
* Cross-tenant isolation: user B cannot see / mutate user A's saved
  comparisons or plans.
* Auth gate: unauthenticated requests are 401.
* Validation: 2-3 unique plan ids required.
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

# ---------- helpers --------------------------------------------------------


def _make_plan(
    client: TestClient,
    *,
    name: str,
    base_currency: str = "USD",
    duration_months: int = 24,
    start_date: str = "2026-09-01",
    tuition_amount: str | None = None,
    tuition_currency: str | None = None,
) -> str:
    payload: dict = {
        "name": name,
        "base_currency": base_currency,
        "start_date": start_date,
        "duration_months": duration_months,
    }
    if tuition_amount is not None:
        payload["tuition_amount"] = tuition_amount
        payload["tuition_currency"] = tuition_currency or base_currency
    res = client.post("/api/v1/study-plans", json=payload)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _add_cost(
    client: TestClient,
    plan_id: str,
    *,
    category: str,
    amount: str,
    currency: str = "USD",
    frequency: str = "monthly",
    is_one_time: bool = False,
    is_refundable: bool = False,
    start_date: str | None = None,
) -> None:
    payload: dict = {
        "category": category,
        "amount": amount,
        "currency": currency,
        "frequency": frequency,
    }
    if is_one_time:
        payload["is_one_time"] = True
        payload["start_date"] = start_date or "2026-09-01"
    if is_refundable:
        payload["is_refundable"] = True
    res = client.post(f"/api/v1/plans/{plan_id}/costs", json=payload)
    assert res.status_code == 201, res.text


def _add_funding(
    client: TestClient,
    plan_id: str,
    *,
    name: str,
    funding_type: str,
    amount: str,
    currency: str = "USD",
    status: str = "confirmed",
    expected_date: str | None = None,
) -> None:
    payload: dict = {
        "name": name,
        "funding_type": funding_type,
        "amount": amount,
        "currency": currency,
        "status": status,
    }
    if expected_date:
        payload["expected_date"] = expected_date
    res = client.post(f"/api/v1/plans/{plan_id}/funding", json=payload)
    assert res.status_code == 201, res.text


def _add_payment(
    client: TestClient,
    plan_id: str,
    *,
    title: str,
    category: str,
    amount: str,
    due_date: str,
    currency: str = "USD",
    status: str = "planned",
) -> str:
    res = client.post(
        "/api/v1/payments",
        json={
            "plan_id": plan_id,
            "title": title,
            "category": category,
            "amount": amount,
            "currency": currency,
            "due_date": due_date,
            "status": status,
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _fund_two_simple_plans(client: TestClient) -> tuple[str, str]:
    """Two plans with identical cost/funding structure."""
    a = _make_plan(client, name="Plan A")
    _add_cost(client, a, category="accommodation", amount="500.00")
    _add_cost(client, a, category="tuition", amount="1000.00", is_one_time=True)
    _add_funding(client, a, name="Savings", funding_type="savings", amount="20000.00")
    _add_funding(
        client, a, name="Family", funding_type="family", amount="5000.00",
        status="expected", expected_date="2026-08-15",
    )

    b = _make_plan(client, name="Plan B", start_date="2027-01-15")
    _add_cost(client, b, category="accommodation", amount="600.00")
    _add_cost(client, b, category="tuition", amount="1200.00", is_one_time=True)
    _add_funding(client, b, name="Savings", funding_type="savings", amount="22000.00")
    _add_funding(
        client, b, name="Loan", funding_type="loan", amount="5000.00",
        status="conditional",
    )
    return a, b


# ---------- auth gate ------------------------------------------------------


def test_compare_requires_authentication(client: TestClient) -> None:
    # No registration performed.
    res = client.post(
        "/api/v1/decision-studio/compare",
        json={"study_plan_ids": ["nope-1", "nope-2"]},
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"


# ---------- validation -----------------------------------------------------


def test_compare_requires_two_to_three_plans(auth_client: TestClient) -> None:
    only = _make_plan(auth_client, name="Solo")
    res = auth_client.post(
        "/api/v1/decision-studio/compare",
        json={"study_plan_ids": [only]},
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_compare_rejects_duplicate_plan_ids(auth_client: TestClient) -> None:
    a = _make_plan(auth_client, name="Only")
    res = auth_client.post(
        "/api/v1/decision-studio/compare",
        json={"study_plan_ids": [a, a]},
    )
    assert res.status_code == 400
    body = res.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    # The Pydantic field validator surfaces its message in the details
    # dict (keyed by the field path).
    details_blob = " ".join(str(v) for v in body["error"].get("details", {}).values())
    assert "unique" in details_blob.lower()


def test_compare_unknown_plan_returns_404(auth_client: TestClient) -> None:
    a = _make_plan(auth_client, name="Real")
    res = auth_client.post(
        "/api/v1/decision-studio/compare",
        json={"study_plan_ids": [a, "ghost-id"]},
    )
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


# ---------- happy-path ad-hoc compare --------------------------------------


def test_compare_two_plans(auth_client: TestClient) -> None:
    a, b = _fund_two_simple_plans(auth_client)
    res = auth_client.post(
        "/api/v1/decision-studio/compare",
        json={"study_plan_ids": [a, b], "upfront_window_days": 30},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["calculation_version"] == "decision_studio_v1"
    assert {p["plan"]["id"] for p in body["plans"]} == {a, b}
    for row in body["plans"]:
        cost = row["cost"]
        assert cost["base_currency"] == "USD"
        assert cost["total_projected_cost"] != cost["refundable_deposits"]
        assert row["funding"]["funding_gap"] is not None
        assert row["upfront"]["upfront_window_days"] == 30


def test_compare_three_plans(auth_client: TestClient) -> None:
    a, b = _fund_two_simple_plans(auth_client)
    c = _make_plan(auth_client, name="Plan C", base_currency="USD", duration_months=18)
    _add_cost(client := auth_client, c, category="accommodation", amount="700.00")
    _add_funding(client, c, name="Savings", funding_type="savings", amount="15000.00")

    res = client.post(
        "/api/v1/decision-studio/compare",
        json={"study_plan_ids": [a, b, c]},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body["plans"]) == 3


def test_compare_different_durations_warning(auth_client: TestClient) -> None:
    a = _make_plan(auth_client, name="Short", duration_months=12)
    _add_funding(auth_client, a, name="X", funding_type="savings", amount="1000.00")
    b = _make_plan(auth_client, name="Long", duration_months=36)
    _add_funding(auth_client, b, name="X", funding_type="savings", amount="5000.00")
    res = auth_client.post(
        "/api/v1/decision-studio/compare",
        json={"study_plan_ids": [a, b]},
    )
    body = res.json()
    codes = {w["code"] for w in body["warnings"]}
    assert "different_durations" in codes
    # And there's no `different_currencies` since both are USD.
    assert "different_currencies" not in codes


def test_compare_different_currencies_warning(auth_client: TestClient) -> None:
    a = _make_plan(auth_client, name="USD plan", base_currency="USD")
    _add_funding(auth_client, a, name="X", funding_type="savings", amount="1000.00")
    b = _make_plan(auth_client, name="EUR plan", base_currency="EUR")
    _add_funding(auth_client, b, name="Y", funding_type="savings", amount="1000.00")
    res = auth_client.post(
        "/api/v1/decision-studio/compare",
        json={"study_plan_ids": [a, b]},
    )
    body = res.json()
    codes = {w["code"] for w in body["warnings"]}
    assert "different_currencies" in codes


def test_compare_no_known_payments_warning(auth_client: TestClient) -> None:
    a, b = _fund_two_simple_plans(auth_client)
    res = auth_client.post(
        "/api/v1/decision-studio/compare",
        json={"study_plan_ids": [a, b]},
    )
    body = res.json()
    codes = {w["code"] for w in body["warnings"]}
    assert "no_known_payments" in codes


def test_compare_surfaces_payment_rows_and_earliest(
    auth_client: TestClient,
) -> None:
    a, b = _fund_two_simple_plans(auth_client)
    today = date.today()
    soon = (today + timedelta(days=7)).isoformat()
    later = (today + timedelta(days=60)).isoformat()
    _add_payment(
        auth_client, a, title="Deposit", category="tuition",
        amount="500.00", due_date=later,
    )
    _add_payment(
        auth_client, a, title="Rent", category="accommodation",
        amount="800.00", due_date=soon,
    )
    res = auth_client.post(
        "/api/v1/decision-studio/compare",
        json={"study_plan_ids": [a, b]},
    )
    body = res.json()
    a_row = next(r for r in body["plans"] if r["plan"]["id"] == a)
    assert a_row["earliest_payment"] is not None
    assert a_row["earliest_payment"]["title"] == "Rent"
    assert len(a_row["payments"]) == 2
    # b has no payments.
    b_row = next(r for r in body["plans"] if r["plan"]["id"] == b)
    assert b_row["earliest_payment"] is None
    assert b_row["payments"] == []


def test_compare_ranks_plans_by_deadline_feasibility(auth_client: TestClient) -> None:
    a = _make_plan(auth_client, name="Plan A")
    _add_cost(auth_client, a, category="tuition", amount="5000.00", is_one_time=True)
    _add_funding(auth_client, a, name="Savings", funding_type="savings", amount="8000.00")
    _add_payment(auth_client, a, title="Deposit", category="tuition", amount="5000.00", due_date=(date.today() + timedelta(days=30)).isoformat())

    b = _make_plan(auth_client, name="Plan B")
    _add_cost(auth_client, b, category="tuition", amount="7000.00", is_one_time=True)
    _add_funding(auth_client, b, name="Savings", funding_type="savings", amount="2000.00")
    _add_funding(auth_client, b, name="Loan", funding_type="loan", amount="8000.00", status="expected", expected_date=(date.today() + timedelta(days=40)).isoformat())
    _add_payment(auth_client, b, title="Deposit", category="tuition", amount="7000.00", due_date=(date.today() + timedelta(days=20)).isoformat())

    res = auth_client.post(
        "/api/v1/decision-studio/compare",
        json={"study_plan_ids": [a, b]},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["recommended_plan_id"] == a
    assert body["deadline_rankings"][0]["plan_id"] == a
    assert body["deadline_rankings"][0]["status"] == "no_shortfall"
    assert body["deadline_rankings"][1]["plan_id"] == b
    assert body["deadline_rankings"][1]["status"] == "shortfall"


# ---------- scenarios ------------------------------------------------------


def test_compare_rent_increase_scenario_increases_cost(
    auth_client: TestClient,
) -> None:
    a, b = _fund_two_simple_plans(auth_client)
    baseline = auth_client.post(
        "/api/v1/decision-studio/compare",
        json={"study_plan_ids": [a, b]},
    ).json()
    baseline_a = next(r for r in baseline["plans"] if r["plan"]["id"] == a)
    baseline_total = baseline_a["cost"]["total_projected_cost"]

    res = auth_client.post(
        "/api/v1/decision-studio/compare",
        json={
            "study_plan_ids": [a, b],
            "scenarios": [
                {
                    "plan_id": a,
                    "name": "rent shock",
                    "adjustments": [
                        {"type": "rent_increase_pct", "value": "20"}
                    ],
                },
            ],
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    a_row = next(r for r in body["plans"] if r["plan"]["id"] == a)
    assert a_row["plan"]["scenario_name"] == "rent shock"
    assert float(a_row["cost"]["total_projected_cost"]) > float(baseline_total)


def test_compare_scholarship_reduction_scenario(auth_client: TestClient) -> None:
    a = _make_plan(auth_client, name="With scholarship")
    _add_cost(client := auth_client, a, category="tuition", amount="2000.00", is_one_time=True)
    _add_funding(
        client, a, name="Merit", funding_type="scholarship",
        amount="1000.00", status="confirmed",
    )
    b = _make_plan(auth_client, name="B")
    _add_funding(client, b, name="X", funding_type="savings", amount="500.00")
    baseline = client.post(
        "/api/v1/decision-studio/compare",
        json={"study_plan_ids": [a, b]},
    ).json()
    base_a = next(r for r in baseline["plans"] if r["plan"]["id"] == a)
    base_eligible = float(base_a["funding"]["eligible_confirmed"])

    res = client.post(
        "/api/v1/decision-studio/compare",
        json={
            "study_plan_ids": [a, b],
            "scenarios": [
                {
                    "plan_id": a,
                    "name": "scholarship halved",
                    "adjustments": [
                        {"type": "scholarship_reduction_pct", "value": "50"}
                    ],
                }
            ],
        },
    )
    a_row = next(r for r in res.json()["plans"] if r["plan"]["id"] == a)
    assert float(a_row["funding"]["eligible_confirmed"]) < base_eligible


def test_compare_custom_note_only_does_not_break(auth_client: TestClient) -> None:
    a, b = _fund_two_simple_plans(auth_client)
    res = auth_client.post(
        "/api/v1/decision-studio/compare",
        json={
            "study_plan_ids": [a, b],
            "scenarios": [
                {
                    "plan_id": a,
                    "name": "FYI",
                    "adjustments": [
                        {"type": "custom_note", "note": "hypothetical only"}
                    ],
                }
            ],
        },
    )
    assert res.status_code == 200
    a_row = next(r for r in res.json()["plans"] if r["plan"]["id"] == a)
    assert any(
        "hypothetical only" in n for n in a_row["plan"]["missing_inputs"]
    )


def test_compare_scenario_does_not_mutate_persisted_plan(
    auth_client: TestClient,
) -> None:
    """Ad-hoc scenarios must never leak back to the DB."""
    a, _b = _fund_two_simple_plans(auth_client)
    before = auth_client.get(f"/api/v1/plans/{a}").json()
    auth_client.post(
        "/api/v1/decision-studio/compare",
        json={
            "study_plan_ids": [a, _b],
            "scenarios": [
                {
                    "plan_id": a,
                    "name": "shock",
                    "adjustments": [
                        {"type": "rent_increase_pct", "value": "99"},
                    ],
                }
            ],
        },
    )
    after = auth_client.get(f"/api/v1/plans/{a}").json()
    # The plan row is unchanged.
    assert before == after


# ---------- saved comparison CRUD -----------------------------------------


def test_save_list_get_update_delete_comparison(auth_client: TestClient) -> None:
    a, b = _fund_two_simple_plans(auth_client)

    # Create
    res = auth_client.post(
        "/api/v1/decision-studio/comparisons",
        json={"name": "Side-by-side", "study_plan_ids": [a, b]},
    )
    assert res.status_code == 201, res.text
    comp = res.json()
    assert comp["name"] == "Side-by-side"
    assert comp["user_id"]
    comp_id = comp["id"]

    # List
    res = auth_client.get("/api/v1/decision-studio/comparisons")
    assert res.status_code == 200
    listed = res.json()
    assert len(listed) == 1
    assert listed[0]["id"] == comp_id

    # Get (recomputes the result)
    res = auth_client.get(f"/api/v1/decision-studio/comparisons/{comp_id}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["comparison"]["id"] == comp_id
    assert body["result"]["comparison_id"] == comp_id
    assert len(body["result"]["plans"]) == 2

    # Patch
    res = auth_client.patch(
        f"/api/v1/decision-studio/comparisons/{comp_id}",
        json={"name": "Renamed"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Renamed"

    # Delete
    res = auth_client.delete(f"/api/v1/decision-studio/comparisons/{comp_id}")
    assert res.status_code == 204
    res = auth_client.get("/api/v1/decision-studio/comparisons")
    assert res.json() == []


def test_get_unknown_comparison_returns_404(auth_client: TestClient) -> None:
    res = auth_client.get("/api/v1/decision-studio/comparisons/nope")
    assert res.status_code == 404


def test_patch_comparison_with_new_plans(auth_client: TestClient) -> None:
    a, b = _fund_two_simple_plans(auth_client)
    c = _make_plan(auth_client, name="Plan C")
    res = auth_client.post(
        "/api/v1/decision-studio/comparisons",
        json={"name": "Original", "study_plan_ids": [a, b]},
    )
    comp_id = res.json()["id"]

    res = auth_client.patch(
        f"/api/v1/decision-studio/comparisons/{comp_id}",
        json={"study_plan_ids": [a, c]},
    )
    assert res.status_code == 200
    assert set(res.json()["study_plan_ids"]) == {a, c}


def test_patch_rejects_unknown_plan(auth_client: TestClient) -> None:
    a, b = _fund_two_simple_plans(auth_client)
    res = auth_client.post(
        "/api/v1/decision-studio/comparisons",
        json={"name": "X", "study_plan_ids": [a, b]},
    )
    comp_id = res.json()["id"]
    res = auth_client.patch(
        f"/api/v1/decision-studio/comparisons/{comp_id}",
        json={"study_plan_ids": [a, "ghost"]},
    )
    assert res.status_code == 404


def test_save_comparison_persists_scenarios(auth_client: TestClient) -> None:
    a, b = _fund_two_simple_plans(auth_client)
    res = auth_client.post(
        "/api/v1/decision-studio/comparisons",
        json={
            "name": "With scenario",
            "study_plan_ids": [a, b],
            "scenarios": [
                {
                    "plan_id": a,
                    "name": "stress",
                    "adjustments": [
                        {"type": "rent_increase_pct", "value": "15"},
                        {"type": "custom_note", "note": "anecdotal"},
                    ],
                }
            ],
        },
    )
    assert res.status_code == 201
    comp_id = res.json()["id"]

    # Reopen → the result must include the scenario-derived rent shock.
    base = auth_client.post(
        "/api/v1/decision-studio/compare",
        json={"study_plan_ids": [a, b]},
    ).json()
    base_a = next(r for r in base["plans"] if r["plan"]["id"] == a)
    base_total = float(base_a["cost"]["total_projected_cost"])

    opened = auth_client.get(f"/api/v1/decision-studio/comparisons/{comp_id}").json()
    saved_a = next(
        r for r in opened["result"]["plans"] if r["plan"]["id"] == a
    )
    assert saved_a["plan"]["scenario_name"] == "stress"
    assert float(saved_a["cost"]["total_projected_cost"]) > base_total


# ---------- cross-tenant isolation ----------------------------------------


def test_other_user_cannot_compare_my_plans(client: TestClient) -> None:
    # User A registers and creates two plans.
    a_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "alpha@example.com",
            "password": "CorrectHorse-9!Battery",
            "name": "Alpha",
        },
    )
    assert a_res.status_code == 201
    p1 = _make_plan(client, name="A1")
    p2 = _make_plan(client, name="A2")
    # User A's own request succeeds.
    res = client.post(
        "/api/v1/decision-studio/compare",
        json={"study_plan_ids": [p1, p2]},
    )
    assert res.status_code == 200

    # User B (separate cookie jar) tries to compare A's plans.
    other = TestClient(client.app)
    b_res = other.post(
        "/api/v1/auth/register",
        json={
            "email": "bravo@example.com",
            "password": "CorrectHorse-9!Battery",
            "name": "Bravo",
        },
    )
    assert b_res.status_code == 201
    res = other.post(
        "/api/v1/decision-studio/compare",
        json={"study_plan_ids": [p1, p2]},
    )
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


def test_other_user_cannot_see_my_saved_comparison(client: TestClient) -> None:
    a_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "aa@example.com",
            "password": "CorrectHorse-9!Battery",
            "name": "AA",
        },
    )
    assert a_res.status_code == 201
    p1 = _make_plan(client, name="A1")
    p2 = _make_plan(client, name="A2")
    comp_res = client.post(
        "/api/v1/decision-studio/comparisons",
        json={"name": "Secret", "study_plan_ids": [p1, p2]},
    )
    comp_id = comp_res.json()["id"]

    other = TestClient(client.app)
    other.post(
        "/api/v1/auth/register",
        json={
            "email": "bb@example.com",
            "password": "CorrectHorse-9!Battery",
            "name": "BB",
        },
    )

    # B cannot list, get, patch, or delete A's comparison.
    assert other.get("/api/v1/decision-studio/comparisons").json() == []
    res = other.get(f"/api/v1/decision-studio/comparisons/{comp_id}")
    assert res.status_code == 404
    res = other.patch(
        f"/api/v1/decision-studio/comparisons/{comp_id}",
        json={"name": "hijacked"},
    )
    assert res.status_code == 404
    res = other.delete(f"/api/v1/decision-studio/comparisons/{comp_id}")
    assert res.status_code == 404

    # A's comparison is still there.
    assert client.get(f"/api/v1/decision-studio/comparisons/{comp_id}").status_code == 200

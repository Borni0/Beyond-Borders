"""Tests for /api/v1/stress-test/* endpoints.

Covers:

* Presets catalogue (GET /presets) is non-empty and contains the
  expected preset keys.
* Saved scenario CRUD (list, create, get, patch, delete).
* Run a one-off adjustment without saving.
* Run a saved scenario.
* Cross-tenant isolation: user B cannot see / run / delete user A's
  scenarios, and user B's ``/run`` against user A's plan returns 404.
* Auth gate: unauthenticated requests are 401.
"""

from __future__ import annotations

import copy

from fastapi.testclient import TestClient

from app.tests.api.conftest import make_user


# ---------- helpers --------------------------------------------------------


def _make_plan(
    client: TestClient,
    *,
    name: str,
    base_currency: str = "USD",
    duration_months: int = 24,
    start_date: str = "2026-09-01",
    tuition_amount: str | None = None,
) -> str:
    payload: dict = {
        "name": name,
        "base_currency": base_currency,
        "start_date": start_date,
        "duration_months": duration_months,
    }
    if tuition_amount is not None:
        payload["tuition_amount"] = tuition_amount
        payload["tuition_currency"] = base_currency
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
    start_date: str | None = None,
) -> str:
    payload: dict = {
        "category": category,
        "amount": amount,
        "currency": currency,
        "frequency": frequency,
        "is_one_time": is_one_time,
    }
    if start_date is not None:
        payload["start_date"] = start_date
    res = client.post(f"/api/v1/plans/{plan_id}/costs", json=payload)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _add_funding(
    client: TestClient,
    plan_id: str,
    *,
    name: str,
    amount: str,
    funding_type: str = "savings",
    status: str = "confirmed",
    currency: str = "USD",
) -> str:
    payload = {
        "name": name,
        "funding_type": funding_type,
        "amount": amount,
        "currency": currency,
        "status": status,
    }
    res = client.post(f"/api/v1/plans/{plan_id}/funding", json=payload)
    assert res.status_code == 201, res.text
    return res.json()["id"]


# ---------- tests ---------------------------------------------------------


class TestPresets:
    def test_presets_returns_known_keys(self, auth_client: TestClient) -> None:
        res = auth_client.get("/api/v1/stress-test/presets")
        assert res.status_code == 200
        presets = res.json()["presets"]
        for key in (
            "rent_shock",
            "scholarship_cut",
            "fx_shock",
            "family_delay",
            "tuition_shock",
            "living_expense_shock",
            "custom",
        ):
            assert key in presets
            assert "label" in presets[key]
            assert "default_adjustment" in presets[key]

    def test_presets_accept_living_cost_adjustment_alias(self, auth_client: TestClient) -> None:
        plan_id = _make_plan(auth_client, name="MSc Lisbon")
        _add_cost(auth_client, plan_id, category="tuition", amount="7000", is_one_time=True)
        _add_cost(auth_client, plan_id, category="accommodation", amount="1200")
        _add_funding(auth_client, plan_id, name="Savings", amount="20000")

        res = auth_client.post(
            "/api/v1/stress-test/run",
            json={
                "plan_id": plan_id,
                "adjustments": [{"type": "living_expense_increase_pct", "value": "20"}],
                "scenario_name": "Living expense shock",
            },
        )
        assert res.status_code == 200, res.text
        assert float(res.json()["total_projected_cost"]["scenario"]) > float(
            res.json()["total_projected_cost"]["baseline"]
        )


class TestScenariosCrud:
    def test_create_list_get_patch_delete(self, auth_client: TestClient) -> None:
        plan_id = _make_plan(auth_client, name="MSc Berlin")
        _add_cost(auth_client, plan_id, category="tuition", amount="1000", is_one_time=True)
        _add_cost(
            auth_client, plan_id, category="accommodation", amount="500"
        )
        _add_funding(auth_client, plan_id, name="Savings", amount="20000")

        # create
        res = auth_client.post(
            "/api/v1/stress-test/scenarios",
            json={
                "name": "Rent shock",
                "scenario_key": "rent_shock",
                "plan_id": plan_id,
                "adjustments": [{"type": "rent_increase_pct", "value": "30"}],
            },
        )
        assert res.status_code == 201, res.text
        scenario = res.json()
        assert scenario["name"] == "Rent shock"
        assert scenario["scenario_key"] == "rent_shock"
        sid = scenario["id"]

        # list (scoped to plan)
        listed = auth_client.get(
            f"/api/v1/stress-test/scenarios?plan_id={plan_id}"
        )
        assert listed.status_code == 200
        names = [s["name"] for s in listed.json()]
        assert "Rent shock" in names

        # get
        one = auth_client.get(f"/api/v1/stress-test/scenarios/{sid}")
        assert one.status_code == 200
        assert one.json()["id"] == sid

        # patch
        updated = auth_client.patch(
            f"/api/v1/stress-test/scenarios/{sid}",
            json={"name": "Rent shock 2"},
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "Rent shock 2"

        # delete
        deleted = auth_client.delete(
            f"/api/v1/stress-test/scenarios/{sid}"
        )
        assert deleted.status_code == 204

        # gone
        after = auth_client.get(f"/api/v1/stress-test/scenarios/{sid}")
        assert after.status_code == 404

    def test_create_rejects_unknown_scenario_key(
        self, auth_client: TestClient
    ) -> None:
        plan_id = _make_plan(auth_client, name="MSc Boston")
        res = auth_client.post(
            "/api/v1/stress-test/scenarios",
            json={
                "name": "Bad key",
                "scenario_key": "not_a_real_key",
                "plan_id": plan_id,
            },
        )
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_create_rejects_unknown_plan(
        self, auth_client: TestClient
    ) -> None:
        res = auth_client.post(
            "/api/v1/stress-test/scenarios",
            json={
                "name": "Lonely",
                "scenario_key": "rent_shock",
                "plan_id": "00000000-0000-0000-0000-000000000000",
                "adjustments": [],
            },
        )
        assert res.status_code == 404

    def test_patch_rejects_unknown_scenario(
        self, auth_client: TestClient
    ) -> None:
        res = auth_client.patch(
            "/api/v1/stress-test/scenarios/00000000-0000-0000-0000-000000000000",
            json={"name": "Nope"},
        )
        assert res.status_code == 404


class TestRun:
    def test_run_with_inline_adjustments(
        self, auth_client: TestClient
    ) -> None:
        plan_id = _make_plan(auth_client, name="MSc Paris")
        _add_cost(
            auth_client, plan_id, category="tuition", amount="5000", is_one_time=True
        )
        _add_cost(
            auth_client,
            plan_id,
            category="accommodation",
            amount="1000",
        )
        _add_funding(auth_client, plan_id, name="Savings", amount="20000")
        _add_funding(
            auth_client,
            plan_id,
            name="Scholarship",
            amount="5000",
            funding_type="scholarship",
            status="confirmed",
        )

        res = auth_client.post(
            "/api/v1/stress-test/run",
            json={
                "plan_id": plan_id,
                "adjustments": [{"type": "rent_increase_pct", "value": "25"}],
                "scenario_name": "+25% rent",
            },
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["plan_id"] == plan_id
        assert body["base_currency"] == "USD"
        # Baseline accommodation per month is 1000; +25% should raise
        # the first-year cost delta. We just check that the scenario
        # number is strictly higher than the baseline.
        assert float(body["total_projected_cost"]["scenario"]) > float(
            body["total_projected_cost"]["baseline"]
        )
        # Delta should be positive for an increase.
        assert float(body["total_projected_cost"]["delta"]) > 0
        # Notes should mention baseline-unchanged.
        assert any("baseline" in n.lower() for n in body["notes"])

    def test_run_with_saved_scenario(
        self, auth_client: TestClient
    ) -> None:
        plan_id = _make_plan(auth_client, name="MBA London")
        _add_cost(
            auth_client, plan_id, category="tuition", amount="8000", is_one_time=True
        )
        _add_cost(
            auth_client, plan_id, category="accommodation", amount="1500"
        )
        _add_funding(auth_client, plan_id, name="Loan", amount="30000")

        created = auth_client.post(
            "/api/v1/stress-test/scenarios",
            json={
                "name": "Rent shock",
                "scenario_key": "rent_shock",
                "plan_id": plan_id,
                "adjustments": [{"type": "rent_increase_pct", "value": "40"}],
            },
        ).json()

        res = auth_client.post(
            "/api/v1/stress-test/run",
            json={"plan_id": plan_id, "scenario_id": created["id"]},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["scenario_id"] == created["id"]
        assert body["scenario_name"] == "Rent shock"
        assert float(body["total_projected_cost"]["delta"]) > 0

    def test_run_unknown_plan(self, auth_client: TestClient) -> None:
        res = auth_client.post(
            "/api/v1/stress-test/run",
            json={
                "plan_id": "00000000-0000-0000-0000-000000000000",
                "adjustments": [{"type": "rent_increase_pct", "value": "10"}],
            },
        )
        assert res.status_code == 404

    def test_run_with_scholarship_reduction_lowers_funding(
        self, auth_client: TestClient
    ) -> None:
        plan_id = _make_plan(auth_client, name="PhD Madrid")
        _add_cost(auth_client, plan_id, category="tuition", amount="1000", is_one_time=True)
        _add_funding(
            auth_client,
            plan_id,
            name="Scholarship",
            amount="12000",
            funding_type="scholarship",
            status="confirmed",
        )

        res = auth_client.post(
            "/api/v1/stress-test/run",
            json={
                "plan_id": plan_id,
                "adjustments": [
                    {"type": "scholarship_reduction_pct", "value": "50"}
                ],
            },
        )
        assert res.status_code == 200
        body = res.json()
        # The scenario should report *less* confirmed funding.
        assert float(body["eligible_confirmed"]["scenario"]) < float(
            body["eligible_confirmed"]["baseline"]
        )


class TestCrossTenant:
    def test_user_b_cannot_see_user_a_scenarios(
        self, auth_client: TestClient, client: TestClient
    ) -> None:
        # Alice creates a plan + a scenario.
        plan_id = _make_plan(auth_client, name="MSc Tokyo")
        _add_cost(auth_client, plan_id, category="tuition", amount="1000", is_one_time=True)
        _add_funding(auth_client, plan_id, name="Savings", amount="5000")
        created = auth_client.post(
            "/api/v1/stress-test/scenarios",
            json={
                "name": "Alice's shock",
                "scenario_key": "rent_shock",
                "plan_id": plan_id,
            },
        ).json()

        # Bob registers in a separate session.
        bob_id = make_user(client, email="bob@example.com", name="Bob")
        assert bob_id

        # Bob's list is empty.
        bob_list = client.get("/api/v1/stress-test/scenarios")
        assert bob_list.status_code == 200
        assert bob_list.json() == []

        # Bob's get on Alice's scenario is 404.
        not_found = client.get(f"/api/v1/stress-test/scenarios/{created['id']}")
        assert not_found.status_code == 404

        # Bob cannot delete Alice's scenario.
        cant_delete = client.delete(
            f"/api/v1/stress-test/scenarios/{created['id']}"
        )
        assert cant_delete.status_code == 404

        # Bob cannot run against Alice's plan.
        cant_run = client.post(
            "/api/v1/stress-test/run",
            json={
                "plan_id": plan_id,
                "adjustments": [{"type": "rent_increase_pct", "value": "10"}],
            },
        )
        assert cant_run.status_code == 404

    def test_user_b_cannot_run_user_a_s_saved_scenario(
        self, auth_client: TestClient, client: TestClient
    ) -> None:
        plan_id = _make_plan(auth_client, name="MSc Toronto")
        _add_cost(auth_client, plan_id, category="tuition", amount="1000", is_one_time=True)
        _add_funding(auth_client, plan_id, name="Savings", amount="5000")
        created = auth_client.post(
            "/api/v1/stress-test/scenarios",
            json={
                "name": "Alice's",
                "scenario_key": "rent_shock",
                "plan_id": plan_id,
            },
        ).json()
        make_user(client, email="eve@example.com", name="Eve")

        res = client.post(
            "/api/v1/stress-test/run",
            json={"plan_id": plan_id, "scenario_id": created["id"]},
        )
        assert res.status_code == 404


class TestAuth:
    def test_endpoints_require_auth(self, client: TestClient) -> None:
        # No login at all.
        # /presets is intentionally public (no user data) so it stays
        # accessible without a session — the catalogue is the same for
        # everyone.
        assert client.get("/api/v1/stress-test/presets").status_code == 200
        assert client.get("/api/v1/stress-test/scenarios").status_code == 401
        assert (
            client.post(
                "/api/v1/stress-test/scenarios", json={"name": "x", "scenario_key": "custom"}
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/v1/stress-test/run",
                json={
                    "plan_id": "00000000-0000-0000-0000-000000000000",
                    "adjustments": [],
                },
            ).status_code
            == 401
        )

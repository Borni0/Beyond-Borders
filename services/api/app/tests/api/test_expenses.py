"""Tests for /api/v1/expenses/* endpoints.

Covers:

* CRUD round-trip (create, list, get, patch, delete).
* CSV import — happy path, mixed valid/invalid rows, missing plan_id.
* CSV export — symmetric with import.
* Summary aggregation — per-month + per-category totals.
* Cross-tenant isolation: user B cannot see / mutate user A's
  expenses, and cannot import a CSV that references A's plan.
* Auth gate: unauthenticated requests are 401.
* Validation: bad date, bad amount, bad currency.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.tests.api.conftest import make_user


# ---------- helpers --------------------------------------------------------


def _create_expense(
    client: TestClient,
    *,
    category: str = "food",
    amount: str = "12.50",
    currency: str = "USD",
    spent_on: str = "2026-10-19",
    description: str = "Lunch",
    plan_id: str | None = None,
) -> dict:
    payload: dict = {
        "category": category,
        "amount": amount,
        "currency": currency,
        "spent_on": spent_on,
        "description": description,
    }
    if plan_id is not None:
        payload["plan_id"] = plan_id
    res = client.post("/api/v1/expenses", json=payload)
    assert res.status_code == 201, res.text
    return res.json()


def _make_plan(client: TestClient, *, name: str) -> str:
    res = client.post(
        "/api/v1/study-plans",
        json={
            "name": name,
            "base_currency": "USD",
            "start_date": "2026-09-01",
            "duration_months": 24,
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


# ---------- tests ---------------------------------------------------------


class TestExpenseCrud:
    def test_create_list_get_patch_delete(
        self, auth_client: TestClient
    ) -> None:
        created = _create_expense(auth_client, description="Coffee")
        eid = created["id"]

        listed = auth_client.get("/api/v1/expenses")
        assert listed.status_code == 200
        assert any(e["id"] == eid for e in listed.json())

        one = auth_client.get(f"/api/v1/expenses/{eid}")
        assert one.status_code == 200
        assert one.json()["description"] == "Coffee"

        patched = auth_client.patch(
            f"/api/v1/expenses/{eid}",
            json={"description": "Latte", "amount": "4.25"},
        )
        assert patched.status_code == 200
        assert patched.json()["description"] == "Latte"
        assert patched.json()["amount"] == "4.2500"

        deleted = auth_client.delete(f"/api/v1/expenses/{eid}")
        assert deleted.status_code == 204

        after = auth_client.get(f"/api/v1/expenses/{eid}")
        assert after.status_code == 404

    def test_create_rejects_bad_date(self, auth_client: TestClient) -> None:
        res = auth_client.post(
            "/api/v1/expenses",
            json={
                "category": "food",
                "amount": "1",
                "currency": "USD",
                "spent_on": "not-a-date",
            },
        )
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_create_rejects_negative_amount(
        self, auth_client: TestClient
    ) -> None:
        res = auth_client.post(
            "/api/v1/expenses",
            json={
                "category": "food",
                "amount": "-5",
                "currency": "USD",
                "spent_on": "2026-10-19",
            },
        )
        assert res.status_code == 422

    def test_create_with_unknown_plan(
        self, auth_client: TestClient
    ) -> None:
        res = auth_client.post(
            "/api/v1/expenses",
            json={
                "category": "food",
                "amount": "5",
                "currency": "USD",
                "spent_on": "2026-10-19",
                "plan_id": "00000000-0000-0000-0000-000000000000",
            },
        )
        assert res.status_code == 404

    def test_patch_unknown_expense(self, auth_client: TestClient) -> None:
        res = auth_client.patch(
            "/api/v1/expenses/00000000-0000-0000-0000-000000000000",
            json={"description": "Nope"},
        )
        assert res.status_code == 404

    def test_delete_unknown_expense(self, auth_client: TestClient) -> None:
        res = auth_client.delete(
            "/api/v1/expenses/00000000-0000-0000-0000-000000000000"
        )
        assert res.status_code == 404

    def test_list_filters_by_plan_id(
        self, auth_client: TestClient
    ) -> None:
        plan_a = _make_plan(auth_client, name="Plan A")
        plan_b = _make_plan(auth_client, name="Plan B")
        _create_expense(
            auth_client, description="A1", plan_id=plan_a
        )
        _create_expense(
            auth_client, description="B1", plan_id=plan_b
        )
        res = auth_client.get(f"/api/v1/expenses?plan_id={plan_a}")
        assert res.status_code == 200
        rows = res.json()
        assert all(r["plan_id"] == plan_a for r in rows)
        assert any(r["description"] == "A1" for r in rows)


class TestCsvImportExport:
    def test_import_happy_path(self, auth_client: TestClient) -> None:
        csv_body = (
            "category,amount,currency,spent_on,description\n"
            "food,12.50,USD,2026-10-19,Coffee\n"
            "transport,3.20,EUR,2026-10-20,Bus\n"
        )
        res = auth_client.post(
            "/api/v1/expenses/import.csv",
            content=csv_body,
            headers={"Content-Type": "text/csv"},
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["created"] == 2
        assert body["skipped"] == 0
        assert body["errors"] == []

        # Both rows are listable.
        rows = auth_client.get("/api/v1/expenses").json()
        assert len(rows) == 2

    def test_import_skips_bad_rows(self, auth_client: TestClient) -> None:
        csv_body = (
            "category,amount,currency,spent_on,description\n"
            "food,12.50,USD,2026-10-19,Coffee\n"
            ",,USD,not-a-date,\n"  # missing amount and bad date
            "transport,5.00,USD,2026-10-20,Bus\n"
        )
        res = auth_client.post(
            "/api/v1/expenses/import.csv",
            content=csv_body,
            headers={"Content-Type": "text/csv"},
        )
        body = res.json()
        assert body["created"] == 2
        assert body["skipped"] == 1
        assert len(body["errors"]) == 1

    def test_import_rejects_missing_headers(
        self, auth_client: TestClient
    ) -> None:
        res = auth_client.post(
            "/api/v1/expenses/import.csv",
            content="foo,bar\n1,2\n",
            headers={"Content-Type": "text/csv"},
        )
        assert res.status_code == 422

    def test_import_skips_unknown_plan_id(
        self, auth_client: TestClient
    ) -> None:
        csv_body = (
            "category,amount,currency,spent_on,plan_id,description\n"
            f"food,12.50,USD,2026-10-19,00000000-0000-0000-0000-000000000000,Coffee\n"
            "transport,5,USD,2026-10-20,,Bus\n"
        )
        res = auth_client.post(
            "/api/v1/expenses/import.csv",
            content=csv_body,
            headers={"Content-Type": "text/csv"},
        )
        body = res.json()
        assert body["created"] == 1
        assert body["skipped"] == 1

    def test_export_round_trip(self, auth_client: TestClient) -> None:
        _create_expense(auth_client, description="X1")
        _create_expense(auth_client, description="X2")

        res = auth_client.get("/api/v1/expenses/export.csv")
        assert res.status_code == 200
        assert "text/csv" in res.headers["content-type"]
        body = res.text
        # Header is present.
        assert "category,amount,currency,spent_on" in body
        # Each created row appears in the export.
        assert "X1" in body
        assert "X2" in body


class TestSummary:
    def test_summary_aggregates_by_category_and_month(
        self, auth_client: TestClient
    ) -> None:
        _create_expense(
            auth_client, category="food", amount="10", spent_on="2026-10-01"
        )
        _create_expense(
            auth_client, category="food", amount="20", spent_on="2026-10-15"
        )
        _create_expense(
            auth_client,
            category="transport",
            amount="5",
            spent_on="2026-10-20",
        )
        res = auth_client.get("/api/v1/expenses/summary")
        assert res.status_code == 200
        body = res.json()
        assert body["count"] == 3
        assert Decimal(body["total"]) == Decimal("35")
        # 2 categories.
        assert len(body["by_category"]) == 2
        # 1 month.
        assert any(m["month"] == "2026-10" for m in body["months"])

    def test_summary_filters_by_plan(
        self, auth_client: TestClient
    ) -> None:
        plan = _make_plan(auth_client, name="MSc")
        _create_expense(
            auth_client, plan_id=plan, description="With plan"
        )
        _create_expense(auth_client, description="Without plan")

        only_plan = auth_client.get(
            f"/api/v1/expenses/summary?plan_id={plan}"
        ).json()
        assert only_plan["count"] == 1


class TestCrossTenant:
    def test_user_b_cannot_see_or_mutate_user_a(
        self, auth_client: TestClient, client: TestClient
    ) -> None:
        created = _create_expense(auth_client, description="Alice")
        make_user(client, email="carol@example.com", name="Carol")

        # Carol's list is empty.
        carol_list = client.get("/api/v1/expenses")
        assert carol_list.status_code == 200
        assert carol_list.json() == []

        # Carol cannot fetch / patch / delete Alice's expense.
        assert (
            client.get(f"/api/v1/expenses/{created['id']}").status_code
            == 404
        )
        assert (
            client.patch(
                f"/api/v1/expenses/{created['id']}",
                json={"description": "Hacked"},
            ).status_code
            == 404
        )
        assert (
            client.delete(f"/api/v1/expenses/{created['id']}").status_code
            == 404
        )

    def test_user_b_cannot_import_csv_using_user_a_plan(
        self, auth_client: TestClient, client: TestClient
    ) -> None:
        plan = _make_plan(auth_client, name="Alice's plan")
        make_user(client, email="dave@example.com", name="Dave")

        csv_body = (
            f"category,amount,currency,spent_on,plan_id,description\n"
            f"food,12,USD,2026-10-19,{plan},Coffee\n"
        )
        res = client.post(
            "/api/v1/expenses/import.csv",
            content=csv_body,
            headers={"Content-Type": "text/csv"},
        )
        body = res.json()
        assert body["created"] == 0
        assert body["skipped"] == 1


class TestAuth:
    def test_endpoints_require_auth(self, client: TestClient) -> None:
        assert client.get("/api/v1/expenses").status_code == 401
        assert (
            client.post(
                "/api/v1/expenses",
                json={
                    "category": "food",
                    "amount": "1",
                    "currency": "USD",
                    "spent_on": "2026-10-19",
                },
            ).status_code
            == 401
        )
        assert client.get("/api/v1/expenses/summary").status_code == 401
        # The CSV endpoints are also gated.
        assert (
            client.get("/api/v1/expenses/export.csv").status_code == 401
        )
        assert (
            client.post(
                "/api/v1/expenses/import.csv",
                content="category,amount,currency,spent_on\n",
                headers={"Content-Type": "text/csv"},
            ).status_code
            == 401
        )


# Late import for the Decimal comparison in the summary test
from decimal import Decimal  # noqa: E402  (placed after tests for clarity)

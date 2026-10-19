"""Live smoke test for the Phase 2 endpoints (funding + payments)."""

from __future__ import annotations

import sys
import time
from datetime import date, timedelta

import requests

BASE = "http://127.0.0.1:8000/api/v1"


def step(label, response, expect=200):
    status = response.status_code
    if status != expect:
        print(f"FAIL {label}: expected {expect}, got {status}: {response.text[:300]}")
        sys.exit(1)
    body = response.json() if response.text else {}
    print(f"ok   {label} [{status}]")
    return body


def main() -> None:
    s = requests.Session()
    email = f"smoke-phase2-{int(time.time())}@example.com"

    # Register + create plan
    step(
        "register",
        s.post(
            f"{BASE}/auth/register",
            json={
                "email": email,
                "password": "CorrectHorse-9!Battery",
                "name": "Phase 2 Smoke",
                "home_country": "US",
                "home_currency": "USD",
                "display_currency": "USD",
            },
        ),
        expect=201,
    )
    plan = step(
        "create plan",
        s.post(
            f"{BASE}/study-plans",
            json={
                "name": "Phase 2 plan",
                "base_currency": "USD",
                "start_date": "2026-09-01",
                "duration_months": 24,
            },
        ),
        expect=201,
    )
    plan_id = plan["id"]
    today = date.today()

    # Funding source
    step(
        "create funding",
        s.post(
            f"{BASE}/plans/{plan_id}/funding",
            json={
                "name": "Family savings",
                "funding_type": "savings",
                "amount": "15000.00",
                "currency": "USD",
                "status": "confirmed",
            },
        ),
        expect=201,
    )

    # Savings goal
    sg = step(
        "create savings goal",
        s.post(
            f"{BASE}/savings-goals",
            json={
                "name": "First year",
                "target_amount": "12000.00",
                "current_amount": "2000.00",
                "currency": "USD",
                "target_date": (today + timedelta(days=300)).isoformat(),
                "plan_id": plan_id,
            },
        ),
        expect=201,
    )

    # Two payments: one upcoming, one overdue
    step(
        "create payment upcoming",
        s.post(
            f"{BASE}/payments",
            json={
                "title": "Tuition deposit",
                "category": "tuition",
                "amount": "1500.00",
                "currency": "USD",
                "due_date": (today + timedelta(days=10)).isoformat(),
                "status": "planned",
                "plan_id": plan_id,
            },
        ),
        expect=201,
    )
    step(
        "create payment overdue",
        s.post(
            f"{BASE}/payments",
            json={
                "title": "Late visa fee",
                "category": "visa",
                "amount": "200.00",
                "currency": "USD",
                "due_date": (today - timedelta(days=3)).isoformat(),
                "status": "planned",
                "plan_id": plan_id,
            },
        ),
        expect=201,
    )

    # Recurring payment
    rec = step(
        "create recurring payment",
        s.post(
            f"{BASE}/payments",
            json={
                "title": "Monthly rent",
                "category": "accommodation",
                "amount": "900.00",
                "currency": "USD",
                "due_date": (today + timedelta(days=5)).isoformat(),
                "status": "planned",
                "is_recurring": True,
                "recurrence_frequency": "monthly",
                "plan_id": plan_id,
            },
        ),
        expect=201,
    )

    # Summary
    summary = step(
        "funding-plan summary",
        s.get(f"{BASE}/plans/{plan_id}/funding-plan/summary"),
    )
    print(
        f"     upcoming={summary['upcoming_payments_count']} "
        f"overdue={summary['overdue_payments_count']} "
        f"upcoming_amt={summary['upcoming_payments']} "
        f"overdue_amt={summary['overdue_payments']}"
    )
    if summary["overdue_payments_count"] != 1:
        print("FAIL: expected exactly 1 overdue payment")
        sys.exit(1)
    if summary["upcoming_payments_count"] < 2:
        print("FAIL: expected at least 2 upcoming payments (incl. recurring)")
        sys.exit(1)

    # Timeline (recurring should project forward)
    timeline = step(
        "funding-plan timeline",
        s.get(f"{BASE}/plans/{plan_id}/funding-plan/timeline"),
    )
    rent_entries = [e for e in timeline["entries"] if e["title"] == "Monthly rent"]
    print(f"     rent entries: {len(rent_entries)}")
    if len(rent_entries) < 12:
        print("FAIL: expected at least 12 monthly rent projections")
        sys.exit(1)

    # Convert via the funding-plan endpoint
    step(
        "upsert USD->EUR rate",
        s.put(
            f"{BASE}/fx",
            json={
                "base_currency": "USD",
                "quote_currency": "EUR",
                "rate": "0.9",
                "rate_type": "user_entered",
                "observed_at": today.isoformat(),
            },
        ),
    )
    conv = step(
        "convert 1000 USD to EUR",
        s.post(
            f"{BASE}/plans/{plan_id}/funding-plan/convert",
            json={
                "from_amount": "1000.00",
                "from_currency": "USD",
                "to_currency": "EUR",
            },
        ),
    )
    print(
        f"     converted={conv['converted_amount']} "
        f"fee={conv['fee_amount']} total={conv['total_cost']}"
    )
    if float(conv["converted_amount"]) != 900.0:
        print("FAIL: conversion math wrong")
        sys.exit(1)

    # CSV export
    csv_res = s.get(f"{BASE}/plans/{plan_id}/funding-plan/export.csv")
    if csv_res.status_code != 200:
        print(f"FAIL: CSV export returned {csv_res.status_code}")
        sys.exit(1)
    lines = [ln for ln in csv_res.text.splitlines() if ln.strip()]
    print(f"     csv rows: {len(lines)} (header + 3 payments)")
    if len(lines) != 4:
        print("FAIL: expected 4 csv lines")
        sys.exit(1)

    # Mark the overdue payment paid
    pay_list = s.get(f"{BASE}/payments?plan_id={plan_id}").json()
    overdue_id = next(p["id"] for p in pay_list if p["display_status"] == "overdue")
    step(
        "mark overdue payment paid",
        s.patch(f"{BASE}/payments/{overdue_id}", json={"status": "paid"}),
    )

    # Goal CRUD: PATCH current_amount then DELETE
    step(
        "patch savings goal",
        s.patch(
            f"{BASE}/savings-goals/{sg['id']}",
            json={"current_amount": "3000.00"},
        ),
    )
    step("delete savings goal", s.delete(f"{BASE}/savings-goals/{sg['id']}"), expect=204)

    # Clean up the plan
    step("delete plan", s.delete(f"{BASE}/study-plans/{plan_id}"), expect=204)
    step("logout", s.post(f"{BASE}/auth/logout"), expect=204)
    print("ALL GREEN")


if __name__ == "__main__":
    main()

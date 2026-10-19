"""Live smoke test for the Phase 1 endpoints. Run with the backend up.

Usage:
    python -m scripts.smoke_phase1
"""

from __future__ import annotations

import json
import sys
import time

import requests

BASE = "http://127.0.0.1:8000/api/v1"


def step(label: str, response: requests.Response, expect: int = 200):
    status = response.status_code
    if status != expect:
        print(f"FAIL {label}: expected {expect}, got {status}: {response.text[:300]}")
        sys.exit(1)
    body: object = response.json() if response.text else None
    print(f"ok   {label} [{status}]")
    return body if body is not None else {}


def main() -> None:
    s = requests.Session()

    # Register
    email = f"smoke-{int(time.time())}@example.com"
    step(
        "register",
        s.post(
            f"{BASE}/auth/register",
            json={
                "email": email,
                "password": "CorrectHorse-9!Battery",
                "name": "Smoke Test",
                "home_country": "US",
                "home_currency": "USD",
                "display_currency": "USD",
            },
        ),
        expect=201,
    )

    me = step("me", s.get(f"{BASE}/users/me"))

    # Plans CRUD
    plan = step(
        "create plan",
        s.post(
            f"{BASE}/study-plans",
            json={
                "name": "Smoke Plan",
                "base_currency": "USD",
                "start_date": "2026-09-01",
                "duration_months": 24,
            },
        ),
        expect=201,
    )
    plan_id = plan["id"]
    print(f"     plan_id = {plan_id}")

    # Costs
    step(
        "create cost (one-time tuition)",
        s.post(
            f"{BASE}/plans/{plan_id}/costs",
            json={
                "category": "tuition",
                "amount": "15000.00",
                "currency": "USD",
                "frequency": "one_time",
                "is_one_time": True,
                "start_date": "2026-09-01",
            },
        ),
        expect=201,
    )
    step(
        "create cost (monthly rent)",
        s.post(
            f"{BASE}/plans/{plan_id}/costs",
            json={
                "category": "accommodation",
                "amount": "900.00",
                "currency": "USD",
                "frequency": "monthly",
            },
        ),
        expect=201,
    )
    step(
        "create cost (refundable deposit)",
        s.post(
            f"{BASE}/plans/{plan_id}/costs",
            json={
                "category": "deposits",
                "amount": "2000.00",
                "currency": "USD",
                "frequency": "one_time",
                "is_one_time": True,
                "is_refundable": True,
                "start_date": "2026-08-15",
            },
        ),
        expect=201,
    )

    costs = step("list costs", s.get(f"{BASE}/plans/{plan_id}/costs"))
    print(f"     {len(costs)} costs")

    # Funding
    step(
        "create funding (savings)",
        s.post(
            f"{BASE}/plans/{plan_id}/funding",
            json={
                "name": "Family savings",
                "funding_type": "savings",
                "amount": "20000.00",
                "currency": "USD",
                "status": "confirmed",
            },
        ),
        expect=201,
    )
    step(
        "create funding (scholarship)",
        s.post(
            f"{BASE}/plans/{plan_id}/funding",
            json={
                "name": "Scholarship",
                "funding_type": "scholarship",
                "amount": "5000.00",
                "currency": "USD",
                "status": "conditional",
                "expected_date": "2026-12-01",
            },
        ),
        expect=201,
    )
    sources = step("list funding", s.get(f"{BASE}/plans/{plan_id}/funding"))
    print(f"     {len(sources)} funding sources")

    # Readiness
    snap1 = step("readiness snapshot", s.get(f"{BASE}/plans/{plan_id}/readiness"))
    snap2 = step("readiness snapshot (replay)", s.get(f"{BASE}/plans/{plan_id}/readiness"))

    same = json.dumps(snap1, sort_keys=True) == json.dumps(snap2, sort_keys=True)
    print(f"     reproducible: {same}")
    print(f"     gap          : {snap1['funding_gap']}")
    print(f"     surplus      : {snap1['funding_surplus']}")
    print(f"     deposit      : {snap1['breakdown']['refundable_deposits']}")
    print(f"     total cost   : {snap1['breakdown']['total_projected_cost']}")
    print(f"     statuses     : {snap1['statuses']}")

    if not same:
        print("FAIL: snapshot not reproducible")
        sys.exit(1)

    # DELETE the plan
    step(
        "delete plan",
        s.delete(f"{BASE}/study-plans/{plan_id}"),
        expect=204,
    )

    # Logout
    step(
        "logout",
        s.post(f"{BASE}/auth/logout"),
        expect=204,
    )

    print("ALL GREEN")


if __name__ == "__main__":
    main()

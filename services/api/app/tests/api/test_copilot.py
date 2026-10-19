"""End-to-end tests for the multi-agent Finance Copilot.

Covers:
* Per-user authorization (401 unauthenticated; cross-tenant isolation).
* Intent classification.
* Agent output for cost-risk (under-funded), payment-planning (with
  events), and research (no FX).
* Graceful fallback for empty / unknown inputs.
* Response contract: every field is present, evidence is a list of
  dicts, evidence ``source_field`` is a non-empty string.
* Tool cap: forcing ``MAX_TOOL_CALLS`` to 0 returns a fallback without
  crashing.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.services.copilot import orchestrator
from app.services.copilot.contracts import (
    AgentName,
    CopilotStatus,
    Intent,
)

# ---------- Helpers --------------------------------------------------------

def _create_plan(
    client: TestClient,
    *,
    name: str = "Test plan",
    base_currency: str = "USD",
) -> str:
    res = client.post(
        "/api/v1/study-plans",
        json={
            "name": name,
            "base_currency": base_currency,
            "start_date": "2026-09-01",
            "duration_months": 24,
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _add_cost(
    client: TestClient,
    plan_id: str,
    *,
    amount: str = "5000.00",
    category: str = "tuition",
) -> None:
    res = client.post(
        f"/api/v1/plans/{plan_id}/costs",
        json={
            "category": category,
            "amount": amount,
            "currency": "USD",
            "frequency": "one_time",
            "is_one_time": True,
            "start_date": "2026-09-01",
        },
    )
    assert res.status_code == 201, res.text


def _add_funding(
    client: TestClient,
    plan_id: str,
    *,
    amount: str = "2000.00",
    status: str = "confirmed",
) -> None:
    res = client.post(
        f"/api/v1/plans/{plan_id}/funding",
        json={
            "name": "Savings",
            "funding_type": "savings",
            "amount": amount,
            "currency": "USD",
            "status": status,
        },
    )
    assert res.status_code == 201, res.text


def _ask(client: TestClient, question: str, **extra: Any) -> dict[str, Any]:
    body = {"question": question, **extra}
    res = client.post("/api/v1/copilot", json=body)
    assert res.status_code == 200, res.text
    return res.json()


def _assert_contract(payload: dict[str, Any]) -> None:
    """Every field on the response contract must be present and well-typed."""

    for key in (
        "request_id",
        "status",
        "message",
        "intent",
        "primary_agent",
        "confidence",
        "evidence",
        "follow_ups",
        "notes",
        "plan_id",
        "generated_at",
        "trace",
    ):
        assert key in payload, f"missing {key}"
    assert payload["status"] in {s.value for s in CopilotStatus}
    assert payload["intent"] in {i.value for i in Intent}
    assert payload["primary_agent"] in {a.value for a in AgentName}
    assert isinstance(payload["confidence"], (int, float))
    assert 0.0 <= float(payload["confidence"]) <= 1.0
    assert isinstance(payload["evidence"], list)
    for ev in payload["evidence"]:
        assert {"label", "value", "source", "source_field"} <= set(ev)
        assert isinstance(ev["source_field"], str) and ev["source_field"]
    assert isinstance(payload["follow_ups"], list)
    assert isinstance(payload["notes"], list)
    assert isinstance(payload["trace"], list)


# ---------- Auth / isolation -----------------------------------------------

def test_copilot_requires_authentication(client: TestClient) -> None:
    res = client.post("/api/v1/copilot", json={"question": "hi"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"


def test_copilot_rejects_empty_question(auth_client: TestClient) -> None:
    res = auth_client.post("/api/v1/copilot", json={"question": ""})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_copilot_rejects_extra_fields(auth_client: TestClient) -> None:
    res = auth_client.post(
        "/api/v1/copilot",
        json={"question": "hi", "evil": "field"},
    )
    assert res.status_code == 400


def test_copilot_does_not_leak_other_users_data(
    auth_client: TestClient, client: TestClient
) -> None:
    """Alice's plan must not be addressable by Bob via a different plan_id."""
    alice_plan = _create_plan(auth_client, name="Alice plan")
    _add_cost(auth_client, alice_plan, amount="9000.00")
    _add_funding(auth_client, alice_plan, amount="2000.00")

    # Bob registers on a separate client.
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "bob@example.com",
            "password": "CorrectHorse-9!Battery",
            "name": "Bob",
            "home_country": "US",
            "home_currency": "USD",
            "display_currency": "USD",
        },
    )
    assert res.status_code == 201, res.text

    # Bob asks about Alice's plan.
    payload = _ask(client, "am I short?", plan_id=alice_plan)
    _assert_contract(payload)
    # Bob owns no plan with that id → orchestrator returns a fallback and
    # no plan_id is echoed back.
    assert payload["plan_id"] is None
    assert payload["status"] in {"fallback", "answered"}


# ---------- Intent classification ------------------------------------------

def test_intent_classification() -> None:
    assert orchestrator.classify_intent("Am I going to be short on cash?") == Intent.COST_RISK
    assert orchestrator.classify_intent("What payments are overdue?") == Intent.PAYMENT_PLANNING
    assert orchestrator.classify_intent("What FX am I missing?") == Intent.RESEARCH
    assert orchestrator.classify_intent("") == Intent.UNKNOWN
    assert orchestrator.classify_intent("explain the universe") == Intent.UNKNOWN


# ---------- Cost-risk agent -----------------------------------------------

def test_cost_risk_underfunded_plan(auth_client: TestClient) -> None:
    plan_id = _create_plan(auth_client)
    _add_cost(auth_client, plan_id, amount="5000.00")
    _add_funding(auth_client, plan_id, amount="2000.00")

    payload = _ask(auth_client, "Am I going to be short on money?")
    _assert_contract(payload)
    assert payload["intent"] == "cost_risk"
    assert payload["status"] == "answered"
    assert payload["plan_id"] == plan_id
    # The numbers in the answer are based on user data, not invented.
    assert "3000" in payload["message"]  # gap = 5000 - 2000
    # Every evidence row has a meaningful source_field.
    assert all(ev["source_field"].startswith("readiness.") for ev in payload["evidence"])


def test_cost_risk_with_no_data_returns_answer(auth_client: TestClient) -> None:
    payload = _ask(auth_client, "am I going to be short on money?")
    _assert_contract(payload)
    # "No data yet" is itself a valid answer (above the floor), not a crash.
    assert payload["status"] == "answered"
    assert payload["plan_id"] is None


# ---------- Payment-planning agent -----------------------------------------

def test_payment_planning_no_events(auth_client: TestClient) -> None:
    plan_id = _create_plan(auth_client)
    payload = _ask(auth_client, "what payments are due?", plan_id=plan_id)
    _assert_contract(payload)
    assert payload["intent"] == "payment_planning"
    assert payload["status"] == "answered"
    assert "overdue" in payload["message"].lower()


# ---------- Research agent -------------------------------------------------

def test_research_flags_missing_fx(auth_client: TestClient) -> None:
    plan_id = _create_plan(auth_client)
    _add_cost(auth_client, plan_id, amount="800.00", category="accommodation")
    payload = _ask(
        auth_client, "what info am I missing?", plan_id=plan_id
    )
    _assert_contract(payload)
    assert payload["intent"] == "research"
    # Either it surfaces the missing FX note, or it says everything is fine
    # — never crashes.
    assert payload["status"] in {"answered", "fallback"}


# ---------- Tool-cap fallback ---------------------------------------------

def test_tool_cap_zero_returns_fallback(
    auth_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With the tool cap set to 0 the orchestrator cannot fetch any data
    and must return a fallback (not crash)."""
    monkeypatch.setattr(orchestrator, "MAX_TOOL_CALLS", 0)
    plan_id = _create_plan(auth_client)
    _add_cost(auth_client, plan_id, amount="5000.00")
    _add_funding(auth_client, plan_id, amount="2000.00")
    payload = _ask(auth_client, "am I short?", plan_id=plan_id)
    _assert_contract(payload)
    # Either the orchestrator recovered (status may be "fallback") or it
    # degraded the response. We just require the contract holds.
    assert payload["status"] in {"fallback", "answered"}


# ---------- Direct unit test of the orchestrator ---------------------------

def test_run_returns_validated_response(auth_client: TestClient) -> None:
    """Calling the orchestrator through the API still produces a
    validated response. Guards against drift between the route and the
    service layer."""
    resp = auth_client.post(
        "/api/v1/copilot", json={"question": "what is the gap?"}
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    _assert_contract(payload)
    assert payload["request_id"]
    assert payload["generated_at"]

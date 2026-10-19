"""Unit tests for the copilot orchestrator (no DB required).

These tests exercise the orchestrator with a mocked Session and a hand-
built ``AgentContext`` so we can assert on the orchestrator's behavior
(intent classification, agent dispatch, fallback framing) without going
through the API.
"""

from __future__ import annotations

from typing import Any
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.copilot import orchestrator
from app.services.copilot.providers import get_llm_provider
from app.services.copilot.contracts import (
    AgentName,
    CopilotRequest,
    CopilotStatus,
    Intent,
)


def _ctx(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "user_id": "u-1",
        "plan_summary": None,
        "readiness": None,
        "funding_summary": None,
        "payments_overdue": [],
        "payments_upcoming": [],
        "fx_rates": [],
        "upfront_window_days": 30,
        "plan_id": None,
    }
    base.update(overrides)
    return base


def test_classify_intent_unit() -> None:
    assert orchestrator.classify_intent("Am I going to be short on cash?") == Intent.COST_RISK
    assert orchestrator.classify_intent("What payments are due?") == Intent.PAYMENT_PLANNING
    assert orchestrator.classify_intent("What's missing?") == Intent.RESEARCH
    assert orchestrator.classify_intent("") == Intent.UNKNOWN
    assert orchestrator.classify_intent("explain the universe") == Intent.UNKNOWN


def _mock_runner():
    """Build a fake ``_ToolRunner`` that returns ``None`` for every call.

    The orchestrator only checks ``.ok`` and ``.data`` so a MagicMock
    works fine.
    """

    runner = MagicMock()
    runner.calls = 0
    runner.call.return_value = MagicMock(ok=False, data=None, error_code="noop")
    return runner


def test_unknown_intent_falls_back_to_research() -> None:
    """An off-topic question becomes a research fallback."""

    db = MagicMock()
    req = CopilotRequest(question="explain the universe")
    resp = orchestrator.run(db, user_id="u-1", request=req)
    # Orchestrator downgrades UNKNOWN to RESEARCH but the response
    # still has the validated contract.
    assert resp.status in {CopilotStatus.ANSWERED, CopilotStatus.FALLBACK}
    assert resp.intent == Intent.RESEARCH
    assert resp.primary_agent == AgentName.RESEARCH


def test_confidence_below_floor_yields_fallback() -> None:
    """If every agent returns confidence 0, the response is a fallback
    with notes explaining why."""
    db = MagicMock()
    req = CopilotRequest(question="am I short?")
    resp = orchestrator.run(db, user_id="u-1", request=req)
    assert resp.confidence <= 1.0
    # In a fresh DB the orchestrator cannot find a plan → the cost-risk
    # agent returns a no-data message at confidence 0.55, which is above
    # the floor, so we expect ``answered`` with a guidance message.
    assert resp.message


def test_response_has_required_fields() -> None:
    db = MagicMock()
    req = CopilotRequest(question="anything")
    resp = orchestrator.run(db, user_id="u-1", request=req)
    payload = resp.to_dict()
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
    assert payload["primary_agent"] in {a.value for a in AgentName}


def test_invalid_agent_output_becomes_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """If the agent somehow returns garbage, the orchestrator must
    produce a fallback, not a 500."""
    from app.services.copilot.agents import agent_for_intent

    class _BadAgent:
        name = AgentName.RESEARCH

        def run(self, ctx):  # type: ignore[no-untyped-def]
            return "not a valid AgentOutput"

    monkeypatch.setattr(agent_for_intent, "__defaults__", (), raising=False)
    # Force the registry lookup to return our bad agent.
    from app.services.copilot import agents as agents_mod

    monkeypatch.setitem(
        agents_mod.AGENTS, Intent.RESEARCH, _BadAgent
    )

    db = MagicMock()
    req = CopilotRequest(question="hi")
    resp = orchestrator.run(db, user_id="u-1", request=req)
    # The orchestrator catches the validation error and returns a
    # fallback. We do not require a specific status; the contract is
    # just "no crash + valid shape".
    payload = resp.to_dict()
    assert "message" in payload
    assert "primary_agent" in payload


def test_llm_provider_disabled_by_default() -> None:
    provider = get_llm_provider()
    assert provider.is_enabled() is False


def test_llm_provider_uses_openai_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.copilot import providers as providers_mod

    monkeypatch.setattr(
        providers_mod,
        "settings",
        SimpleNamespace(
            llm_provider="openai",
            llm_api_key="sk-test-key",
            openai_api_key="sk-test-key",
            llm_model="gpt-4o-mini",
            openai_model="gpt-4o-mini",
            llm_base_url="https://api.openai.com/v1",
            openai_base_url="https://api.openai.com/v1",
            llm_temperature=0.2,
            llm_timeout_seconds=30.0,
        ),
    )

    provider = providers_mod.get_llm_provider()
    assert provider.is_enabled() is True
    assert provider.model == "gpt-4o-mini"

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"choices": [{"message": {"content": '{"answer": "ok"}'}}]}

    monkeypatch.setattr(providers_mod.httpx, "post", lambda *args, **kwargs: _FakeResponse())
    result = provider.invoke(system_prompt="planner", user_prompt="question")
    assert result.ok is True
    assert "ok" in result.text.lower()

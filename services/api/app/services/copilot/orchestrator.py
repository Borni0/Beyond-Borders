"""Orchestrator: intent classification, tool bounding, and final response.

The orchestrator is the only place that touches the database, the tools,
the agents, and the response contract. It enforces:

* **Intent classification** — keyword-based, transparent, deterministic.
  No LLM call. The classifier is a tiny function with rules that are
  testable in isolation.
* **Per-user authorization** — every tool call passes ``user_id``. The
  repos already filter by it; the orchestrator never overrides that.
* **Bounded tool calls** — ``MAX_TOOL_CALLS`` caps how many tools may
  run per request. Exceeding the cap returns a fallback response.
* **Timeouts** — every tool call has a wall-clock budget. Timeouts
  degrade gracefully (tool result is ``ok=False``; the agent can
  still produce a partial answer; the orchestrator notes the timeout).
* **Validation** — the agent's output is re-validated by the response
  model. A malformed agent output is converted into a fallback.
* **Trace** — every step is appended to a trace list the response can
  include for debugging. The trace is plain dicts (no SQLAlchemy, no
  secrets).
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.services.copilot import tools
from app.services.copilot.agents import (
    AgentContext,
    agent_for_intent,
)
from app.services.copilot.providers import get_llm_provider
from app.services.copilot.contracts import (
    AgentName,
    AgentOutput,
    CopilotEvidence,
    CopilotRequest,
    CopilotResponse,
    CopilotStatus,
    Intent,
)

log = logging.getLogger(__name__)


# ---------- Tunables --------------------------------------------------------

# A hard cap on how many tool calls one request may trigger. Keeps the
# orchestrator from going haywire if a future agent misbehaves.
MAX_TOOL_CALLS = 6

# Wall-clock budget per tool call (seconds). The tools themselves are
# fast pure-DB work; this is belt-and-braces.
TOOL_TIMEOUT_SECONDS = 2.0

# Below this confidence the orchestrator prefers a fallback response.
ANSWER_CONFIDENCE_FLOOR = 0.35


# ---------- Intent classifier ----------------------------------------------

# Keyword groups, ordered by specificity. The first group with at least
# one match wins. ``RESEARCH`` is the default fallback.
_COST_RISK_PATTERNS = (
    r"\b(gap|short|shortfall|cover|enough|afford|under[-\s]?funded|risk|afford|short on)\b",
    r"\b(funding|fund|cost|expense|budget|total cost|projected)\b.*\?",
)
_PAYMENT_PATTERNS = (
    r"\b(overdue|due|pay(ment)?|when do i|bill|installment|next bill|upcoming)\b",
    r"\b(remind|schedule|postpone|defer)\b",
)
_RESEARCH_PATTERNS = (
    r"\b(missing|don'?t have|what'?s missing|fx|exchange|rate|currency)\b",
    r"\b(what info|complete|gap in data|inputs)\b",
)


def _any_match(patterns: tuple[str, ...], text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def classify_intent(question: str) -> Intent:
    """Keyword-based intent classifier.

    Deterministic, transparent, testable. If the question is empty or
    nothing matches, returns ``RESEARCH`` (the safest default — no
    numeric claims, just a checklist of missing inputs).
    """

    q = (question or "").strip().lower()
    if not q:
        return Intent.UNKNOWN
    if _any_match(_COST_RISK_PATTERNS, q):
        return Intent.COST_RISK
    if _any_match(_PAYMENT_PATTERNS, q):
        return Intent.PAYMENT_PLANNING
    if _any_match(_RESEARCH_PATTERNS, q):
        return Intent.RESEARCH
    return Intent.UNKNOWN


# ---------- Internal trace record ------------------------------------------

@dataclass
class _TraceStep:
    name: str
    elapsed_ms: int
    detail: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


# ---------- Orchestrator ----------------------------------------------------

def _maybe_parse_llm_json(text: str) -> dict[str, Any] | None:
    """Best-effort extraction of JSON from a provider response."""

    raw = (text or "").strip()
    if not raw:
        return None
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _run_llm_specialist_workflow(
    *,
    question: str,
    intent: Intent,
    ctx: AgentContext,
    trace: list[_TraceStep],
) -> AgentOutput | None:
    """Execute the real specialist-agent workflow if a provider is configured."""

    provider = get_llm_provider()
    if not provider.is_enabled():
        return None

    specialized_prompt = (
        "You are a specialist finance analyst. Produce JSON with keys: "
        "answer, confidence, follow_ups, notes, evidence. "
        "Prioritize user-owned financial data and clearly state if data is missing."
    )

    summary = {
        "question": question,
        "intent": intent.value,
        "plan_summary": dict(ctx.plan_summary or {}),
        "readiness": dict(ctx.readiness or {}),
        "funding_summary": dict(ctx.funding_summary or {}),
        "payments_overdue": list(ctx.payments_overdue or []),
        "payments_upcoming": list(ctx.payments_upcoming or []),
        "fx_rates": list(ctx.fx_rates or []),
        "upfront_window_days": ctx.upfront_window_days,
    }

    response = provider.invoke(
        system_prompt=specialized_prompt,
        user_prompt=(
            "Analyze the user question and the facts below as a multi-agent finance workflow. "
            f"Context JSON: {json.dumps(summary, default=str, sort_keys=True)}"
        ),
    )
    trace.append(
        _TraceStep(
            name="llm.specialist_workflow",
            elapsed_ms=0,
            detail={"provider": provider.provider_name, "model": provider.model},
            error=None if response.ok else response.error,
        )
    )
    if not response.ok:
        return None

    payload = _maybe_parse_llm_json(response.text)
    if payload is None:
        return None

    answer = str(payload.get("answer") or response.text).strip()
    if not answer:
        return None

    evidence = payload.get("evidence") or []
    normalized_evidence: list[CopilotEvidence] = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        try:
            normalized_evidence.append(
                CopilotEvidence(
                    label=str(item.get("label") or "Evidence"),
                    value=str(item.get("value") or ""),
                    source=str(item.get("source") or "engine"),
                    source_field=str(item.get("source_field") or "engine.unknown"),
                )
            )
        except Exception:  # noqa: BLE001
            continue

    follow_ups = payload.get("follow_ups") or []
    notes = payload.get("notes") or []
    confidence = float(payload.get("confidence", 0.65))
    if not 0.0 <= confidence <= 1.0:
        confidence = min(max(confidence, 0.0), 1.0)

    return AgentOutput(
        agent=AgentName.RESEARCH,
        intent=intent,
        answer=answer,
        confidence=confidence,
        evidence=normalized_evidence,
        follow_ups=[str(item) for item in follow_ups][:10],
        notes=[str(item) for item in notes][:10],
    )


@dataclass
class _ToolRunner:
    """Wraps a tool call with a wall-clock timeout and tracing.

    The timeout is implemented with a start-time check after the call
    returns; the actual call is synchronous. If a tool ever becomes
    truly blocking, this is the place to swap in a thread-based
    timeout.
    """

    db: Session
    user_id: str
    trace: list[_TraceStep]
    calls: int = 0

    def call(self, fn, /, **kwargs: Any) -> tools.ToolResult:
        if self.calls >= MAX_TOOL_CALLS:
            return tools.ToolResult(
                ok=False,
                error_code="tool_cap_exceeded",
                message="Reached the maximum number of tool calls for one request.",
            )
        self.calls += 1
        start = time.monotonic()
        try:
            result = fn(self.db, user_id=self.user_id, **kwargs)
        except Exception as exc:  # noqa: BLE001
            elapsed = int((time.monotonic() - start) * 1000)
            self.trace.append(
                _TraceStep(
                    name=fn.__name__,
                    elapsed_ms=elapsed,
                    error=type(exc).__name__,
                )
            )
            log.warning("copilot tool %s failed: %s", fn.__name__, exc)
            return tools.ToolResult(
                ok=False,
                error_code=type(exc).__name__,
                message="Tool failed; falling back.",
            )
        elapsed = int((time.monotonic() - start) * 1000)
        self.trace.append(
            _TraceStep(
                name=fn.__name__,
                elapsed_ms=elapsed,
                detail={"ok": result.ok, "elapsed_ms": result.elapsed_ms},
                error=None if result.ok else result.error_code,
            )
        )
        # Soft timeout check: if the tool blew past the budget, downgrade
        # the result to ok=False so the agent doesn't quote stale data.
        if elapsed > TOOL_TIMEOUT_SECONDS * 1000:
            return tools.ToolResult(
                ok=False,
                error_code="tool_timeout",
                message="Tool took too long; skipping its result.",
            )
        return result


# ---------- Public entry point ---------------------------------------------

def run(db: Session, *, user_id: str, request: CopilotRequest) -> CopilotResponse:
    """Run the full copilot pipeline for ``user_id`` and ``request``.

    Always returns a ``CopilotResponse`` — never raises to the caller.
    The route layer can convert the response straight to JSON.
    """

    request_id = uuid.uuid4().hex
    trace: list[_TraceStep] = []
    started = time.monotonic()

    # 1. Intent classification
    intent = classify_intent(request.question)
    trace.append(
        _TraceStep(
            name="classify_intent",
            elapsed_ms=0,
            detail={"intent": intent.value},
        )
    )

    runner = _ToolRunner(db=db, user_id=user_id, trace=trace)

    # 2. Pick a plan (explicit → most recent)
    plan_id = request.plan_id
    plan_summary_data: dict[str, Any] | None = None
    if plan_id is None:
        listed = runner.call(tools.list_user_plans)
        if listed.ok and listed.data:
            plan_id = str(listed.data[0]["id"])
    if plan_id is not None:
        loaded = runner.call(tools.load_plan_summary, plan_id=plan_id)
        if loaded.ok:
            plan_summary_data = dict(loaded.data)
            plan_id = str(loaded.data["id"])
        else:
            # Plan id provided but inaccessible. The user owns nothing
            # usable → fall back to "no plan" path.
            plan_id = None
            plan_summary_data = None

    # 3. Pre-fetch everything the agents might need
    readiness_data: dict[str, Any] | None = None
    funding_summary: dict[str, Any] | None = None
    overdue: list[dict[str, Any]] = []
    upcoming: list[dict[str, Any]] = []
    fx_rows: list[dict[str, Any]] = []

    if plan_id is not None:
        ready = runner.call(
            tools.compute_readiness,
            plan_id=plan_id,
            upfront_window_days=request.upfront_window_days,
        )
        if ready.ok:
            readiness_data = dict(ready.data)
        fund = runner.call(
            tools.compute_funding_plan_summary,
            plan_id=plan_id,
            upcoming_window_days=request.upfront_window_days,
        )
        if fund.ok:
            funding_summary = dict(fund.data)
        over = runner.call(
            tools.list_overdue_payments,
            plan_id=plan_id,
        )
        if over.ok:
            overdue = list(over.data or [])
        up = runner.call(
            tools.list_upcoming_payments,
            plan_id=plan_id,
            window_days=request.upfront_window_days,
        )
        if up.ok:
            upcoming = list(up.data or [])
    fx = runner.call(tools.list_fx_rates)
    if fx.ok:
        fx_rows = list(fx.data or [])

    # 4. Unknown intent → ask the user to clarify, but still run
    #    research (it never makes numeric claims) so we can offer a
    #    useful follow-up.
    if intent == Intent.UNKNOWN:
        intent = Intent.RESEARCH
    primary_agent_name: AgentName = {
        Intent.COST_RISK: AgentName.COST_RISK,
        Intent.PAYMENT_PLANNING: AgentName.PAYMENT_PLANNING,
        Intent.RESEARCH: AgentName.RESEARCH,
    }[intent]

    # 5. Build the agent context and run the agent
    ctx = AgentContext(
        user_id=user_id,
        plan_summary=plan_summary_data,
        readiness=readiness_data,
        funding_summary=funding_summary,
        payments_overdue=overdue,
        payments_upcoming=upcoming,
        fx_rates=fx_rows,
        upfront_window_days=request.upfront_window_days,
        plan_id=plan_id,
    )

    llm_output = _run_llm_specialist_workflow(
        question=request.question,
        intent=intent,
        ctx=ctx,
        trace=trace,
    )
    if llm_output is not None:
        validated = llm_output
        trace.append(
            _TraceStep(
                name="llm.synthesis",
                elapsed_ms=0,
                detail={"confidence": validated.confidence},
            )
        )
        if validated.confidence < ANSWER_CONFIDENCE_FLOOR:
            return _fallback_response(
                request_id=request_id,
                intent=intent,
                plan_id=plan_id,
                message=(
                    "I'm not confident enough to answer that yet. Add a study "
                    "plan with at least one cost and one funding source, then "
                    "ask again."
                ),
                trace=trace,
                evidence=validated.evidence,
                follow_ups=validated.follow_ups,
                notes=(validated.notes or [])
                + ["Confidence below floor; responding with guidance only."],
            )

        status = CopilotStatus.ANSWERED
        response = CopilotResponse(
            request_id=request_id,
            status=status,
            message=validated.answer,
            intent=intent,
            primary_agent=validated.agent,
            confidence=round(float(validated.confidence), 4),
            evidence=list(validated.evidence),
            follow_ups=list(validated.follow_ups),
            notes=list(validated.notes),
            plan_id=plan_id,
            generated_at=datetime.now(timezone.utc),
            trace=[_trace_to_dict(s) for s in trace],
        )
        return response

    agent = agent_for_intent(intent)
    agent_start = time.monotonic()
    try:
        raw_output = agent.run(ctx)
    except Exception as exc:  # noqa: BLE001
        log.exception("agent %s raised", primary_agent_name)
        trace.append(
            _TraceStep(
                name=f"agent.{primary_agent_name.value}",
                elapsed_ms=int((time.monotonic() - agent_start) * 1000),
                error=type(exc).__name__,
            )
        )
        return _fallback_response(
            request_id=request_id,
            intent=intent,
            plan_id=plan_id,
            message=(
                "I hit a snag analyzing your plan. Try rephrasing the "
                "question or check the readiness page directly."
            ),
            trace=trace,
            notes=["Agent raised an exception."],
        )

    # 6. Validate the agent output through the Pydantic contract.
    #    ``model_validate`` enforces the same rules the schema documents.
    #    The trace step is appended *inside* the try so an agent that
    #    returns garbage doesn't crash the orchestrator on the way out.
    try:
        validated = AgentOutput.model_validate(raw_output.model_dump())
        # Append the success trace step here so the ``confidence`` access
        # is guarded by the same try/except as the model validation.
        trace.append(
            _TraceStep(
                name=f"agent.{primary_agent_name.value}",
                elapsed_ms=int((time.monotonic() - agent_start) * 1000),
                detail={"confidence": validated.confidence},
            )
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("agent %s produced invalid output: %s", primary_agent_name, exc)
        return _fallback_response(
            request_id=request_id,
            intent=intent,
            plan_id=plan_id,
            message=(
                "I couldn't put together a clean answer for that question. "
                "Try asking about funding, payments, or missing data."
            ),
            trace=trace,
            notes=[f"Validation failed: {type(exc).__name__}"],
        )

    # 7. Confidence floor → fallback framing
    if validated.confidence < ANSWER_CONFIDENCE_FLOOR:
        return _fallback_response(
            request_id=request_id,
            intent=intent,
            plan_id=plan_id,
            message=(
                "I'm not confident enough to answer that yet. Add a study "
                "plan with at least one cost and one funding source, then "
                "ask again."
            ),
            trace=trace,
            evidence=validated.evidence,
            follow_ups=validated.follow_ups,
            notes=(validated.notes or [])
            + ["Confidence below floor; responding with guidance only."],
        )

    # 8. Build the final response
    status = CopilotStatus.ANSWERED
    notes = list(validated.notes)
    if any(step.error for step in trace):
        status = CopilotStatus.FALLBACK
        notes.append("One or more tools returned an error; the answer may be partial.")

    response = CopilotResponse(
        request_id=request_id,
        status=status,
        message=validated.answer,
        intent=intent,
        primary_agent=primary_agent_name,
        confidence=round(float(validated.confidence), 4),
        evidence=list(validated.evidence),
        follow_ups=list(validated.follow_ups),
        notes=notes,
        plan_id=plan_id,
        generated_at=datetime.now(timezone.utc),
        trace=[_trace_to_dict(s) for s in trace],
    )

    log.info(
        "copilot run user=%s intent=%s status=%s confidence=%.2f elapsed_ms=%d",
        user_id,
        intent.value,
        status.value,
        validated.confidence,
        int((time.monotonic() - started) * 1000),
    )
    return response


# ---------- Helpers ---------------------------------------------------------

def _fallback_response(
    *,
    request_id: str,
    intent: Intent,
    plan_id: str | None,
    message: str,
    trace: list[_TraceStep],
    evidence: list[CopilotEvidence] | None = None,
    follow_ups: list[str] | None = None,
    notes: list[str] | None = None,
) -> CopilotResponse:
    return CopilotResponse(
        request_id=request_id,
        status=CopilotStatus.FALLBACK,
        message=message,
        intent=intent,
        primary_agent=AgentName.RESEARCH,
        confidence=0.0,
        evidence=evidence or [],
        follow_ups=follow_ups
        or [
            "What costs do I have so far?",
            "What's missing from my plan?",
        ],
        notes=notes or [],
        plan_id=plan_id,
        generated_at=datetime.now(timezone.utc),
        trace=[_trace_to_dict(s) for s in trace],
    )


def _trace_to_dict(step: _TraceStep) -> dict[str, Any]:
    return {
        "name": step.name,
        "elapsed_ms": step.elapsed_ms,
        "detail": step.detail,
        "error": step.error,
    }


# Re-export for convenience
__all__ = ["run", "classify_intent", "MAX_TOOL_CALLS", "TOOL_TIMEOUT_SECONDS"]

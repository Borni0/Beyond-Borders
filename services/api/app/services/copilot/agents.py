"""Specialized copilot agents.

Each agent is a pure function: given a deterministic ``AgentContext``
(plan, readiness snapshot, payment snapshot, FX list, intent), it returns
a validated ``AgentOutput``. Agents never touch the database directly;
they receive pre-fetched data via the context, and the orchestrator
controls which tools run before the agent is invoked.

This keeps the agents:

* **Testable** — feed in a fixture context, assert the output model.
* **Deterministic** — same inputs → same answer.
* **Bounded** — the orchestrator caps the number of tool calls, so an
  agent that wanted to "research" more could in principle ask for it
  but only within a hard cap.

The agents here are deliberately rule-based. If a real LLM is wired in
later, it slots in behind the same ``AgentOutput`` contract.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.services.copilot.contracts import (
    AgentName,
    AgentOutput,
    CopilotEvidence,
    Intent,
)

# ---------- Shared context --------------------------------------------------

@dataclass(frozen=True)
class AgentContext:
    """Everything an agent might need, fetched once by the orchestrator.

    ``readiness`` and ``funding_summary`` are dicts (already JSON-safe).
    ``payments_overdue`` and ``payments_upcoming`` are lists of dicts.
    ``fx_rates`` is a list of dicts. Missing values are ``None`` /
    empty rather than keys-that-might-not-exist.
    """

    user_id: str
    plan_summary: Mapping[str, Any] | None
    readiness: Mapping[str, Any] | None
    funding_summary: Mapping[str, Any] | None
    payments_overdue: Sequence[Mapping[str, Any]]
    payments_upcoming: Sequence[Mapping[str, Any]]
    fx_rates: Sequence[Mapping[str, Any]]
    upfront_window_days: int
    plan_id: str | None


# ---------- Helpers --------------------------------------------------------

def _money(value: Any) -> Decimal:
    """Best-effort coerce to Decimal; never raises on a missing key."""

    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _ev(
    label: str, value: Any, *, source: str, field: str
) -> CopilotEvidence:
    return CopilotEvidence(
        label=label,
        value=str(value),
        source=source,
        source_field=field,
    )


def _common_follow_ups() -> list[str]:
    return [
        "How much cash do I need before I fly out?",
        "What's my biggest category of spend?",
        "Am I missing any FX rates?",
    ]


# ---------- Cost-risk agent -------------------------------------------------

class CostRiskAgent:
    """Answers "am I going to be short?", "is my funding enough?", etc.

    Sources its evidence from the deterministic readiness snapshot.
    """

    name = AgentName.COST_RISK

    def run(self, ctx: AgentContext) -> AgentOutput:
        readiness = ctx.readiness
        plan = ctx.plan_summary
        notes: list[str] = []

        if readiness is None or plan is None:
            return AgentOutput(
                agent=self.name,
                intent=Intent.COST_RISK,
                answer=(
                    "I don't have a plan to analyze yet. Add a study plan with "
                    "at least one cost or funding source and I'll have something "
                    "to say."
                ),
                confidence=0.55,  # the no-data case is itself a valid answer
                evidence=[],
                follow_ups=_common_follow_ups(),
                notes=["No plan or readiness snapshot available."],
            )

        gap = _money(readiness.get("funding_gap"))
        surplus = _money(readiness.get("funding_surplus"))
        upfront_req = _money(readiness.get("upfront_cash_requirement"))
        upfront_gap = _money(readiness.get("upfront_cash_gap"))
        base = str(readiness.get("base_currency") or plan.get("base_currency") or "")
        statuses = list(readiness.get("statuses") or [])
        coverage = readiness.get("coverage_pct")
        first_year_gap = _money(readiness.get("first_year_funding_gap"))

        evidence: list[CopilotEvidence] = [
            _ev("Funding gap", gap, source="readiness", field="readiness.funding_gap"),
            _ev(
                "Funding surplus",
                surplus,
                source="readiness",
                field="readiness.funding_surplus",
            ),
            _ev(
                "Upfront cash requirement",
                upfront_req,
                source="readiness",
                field="readiness.upfront_cash_requirement",
            ),
            _ev(
                "Upfront cash gap",
                upfront_gap,
                source="readiness",
                field="readiness.upfront_cash_gap",
            ),
        ]
        if coverage is not None:
            evidence.append(
                _ev(
                    "Coverage",
                    f"{coverage}%",
                    source="readiness",
                    field="readiness.coverage_pct",
                )
            )

        if gap > 0:
            severity = "high" if gap > upfront_req and upfront_req > 0 else "notable"
            answer = (
                f"You have a {severity} funding gap of {gap} {base} "
                f"across the plan. Confirmed funding is short of total "
                f"projected cost; the upfront-cash gap (next "
                f"{ctx.upfront_window_days} days) is {upfront_gap} {base}."
            )
            if first_year_gap > 0:
                answer += (
                    f" The first year alone is short by {first_year_gap} {base}."
                )
            confidence = 0.85
        elif surplus > 0:
            answer = (
                f"You're fully covered with a {surplus} {base} surplus. "
                f"Upfront cash need in the next {ctx.upfront_window_days} days "
                f"is {upfront_req} {base}."
            )
            confidence = 0.85
        else:
            answer = (
                f"Funding matches projected cost exactly in {base}. No gap, no surplus."
            )
            confidence = 0.7

        if "needs_more_information" in statuses:
            missing = list(readiness.get("missing_inputs") or [])
            if missing:
                notes.append(
                    "I couldn't compute everything — " + "; ".join(missing[:3])
                )
                confidence = min(confidence, 0.6)

        follow_ups = [
            "Which category is driving the gap?",
            "What if a conditional source falls through?",
        ]
        if upfront_gap > 0:
            follow_ups.append(
                f"How do I cover the {upfront_gap} {base} I need in the next "
                f"{ctx.upfront_window_days} days?"
            )

        return AgentOutput(
            agent=self.name,
            intent=Intent.COST_RISK,
            answer=answer,
            confidence=confidence,
            evidence=evidence,
            follow_ups=follow_ups,
            notes=notes,
        )


# ---------- Payment-planning agent ------------------------------------------

class PaymentPlanningAgent:
    """Answers "what's due soon?", "what's overdue?", "what can I postpone?"."""

    name = AgentName.PAYMENT_PLANNING

    def run(self, ctx: AgentContext) -> AgentOutput:
        overdue = list(ctx.payments_overdue)
        upcoming = list(ctx.payments_upcoming)
        plan_currency = str(
            (ctx.plan_summary or {}).get("base_currency") or ""
        )
        notes: list[str] = []

        if not overdue and not upcoming:
            return AgentOutput(
                agent=self.name,
                intent=Intent.PAYMENT_PLANNING,
                answer=(
                    "You don't have any overdue payments, and nothing is due in "
                    "the next window. Add payment events to your plan to see them "
                    "here."
                ),
                confidence=0.6,  # accurate but uneventful; above the fallback floor
                evidence=[],
                follow_ups=_common_follow_ups(),
                notes=[],
            )

        evidence: list[CopilotEvidence] = []
        for i, ev in enumerate(overdue[:5]):
            evidence.append(
                _ev(
                    f"Overdue: {ev.get('title') or 'Payment'}",
                    f"{ev.get('amount')} {ev.get('currency')} on {ev.get('due_date')}",
                    source="payment",
                    field=f"payment_events[{i}].overdue",
                )
            )
        for i, ev in enumerate(upcoming[:5]):
            evidence.append(
                _ev(
                    f"Upcoming: {ev.get('title') or 'Payment'}",
                    f"{ev.get('amount')} {ev.get('currency')} on {ev.get('due_date')}",
                    source="payment",
                    field=f"payment_events[overdue+{i}].upcoming",
                )
            )

        if overdue:
            total = sum(
                _money(e.get("amount")) for e in overdue if e.get("currency") == plan_currency
            )
            answer = (
                f"You have {len(overdue)} overdue payment(s) totalling "
                f"{total} {plan_currency or '(mixed currencies)'}."
            )
            confidence = 0.9
            notes.append(
                "Mark paid events as 'paid' to clear them from the overdue list."
            )
        else:
            answer = (
                f"Nothing is overdue. You have {len(upcoming)} payment(s) due in "
                f"the next window."
            )
            confidence = 0.75

        if upcoming and not overdue:
            total_upcoming = sum(
                _money(e.get("amount"))
                for e in upcoming
                if e.get("currency") == plan_currency
            )
            answer += (
                f" Total upcoming in plan currency: {total_upcoming} {plan_currency}."
            )

        return AgentOutput(
            agent=self.name,
            intent=Intent.PAYMENT_PLANNING,
            answer=answer,
            confidence=confidence,
            evidence=evidence,
            follow_ups=[
                "Which overdue payment should I tackle first?",
                "Convert one of these to my home currency.",
            ],
            notes=notes,
        )


# ---------- Research agent -------------------------------------------------

class ResearchAgent:
    """Answers "what info am I missing?", "do I have FX rates for X?".

    Does not fetch the web. Surfaces gaps the user can fill themselves.
    """

    name = AgentName.RESEARCH

    def run(self, ctx: AgentContext) -> AgentOutput:
        notes: list[str] = []
        evidence: list[CopilotEvidence] = []

        # FX gap analysis
        rates = list(ctx.fx_rates)
        currencies_in_costs: set[str] = set()
        if ctx.readiness:
            base = str(ctx.readiness.get("base_currency") or "").upper()
            per_category = ctx.readiness.get("breakdown", {}).get("per_category", {})
            for _cat, total in per_category.items():
                try:
                    if Decimal(str(total)) > 0:
                        currencies_in_costs.add(base)
                except Exception:  # noqa: BLE001, S112
                    # Bad row: skip it instead of breaking the whole agent.
                    continue
        currencies_in_funding: set[str] = set()
        if ctx.funding_summary:
            for b in ctx.funding_summary.get("buckets", []):
                cur = str(b.get("currency") or "").upper()
                if cur:
                    currencies_in_funding.add(cur)
        referenced = (currencies_in_costs | currencies_in_funding) - {""}

        pairs: set[tuple[str, str]] = set()
        for r in rates:
            base = str(r.get("base_currency") or "").upper()
            quote = str(r.get("quote_currency") or "").upper()
            if base and quote:
                pairs.add((base, quote))
                pairs.add((quote, base))  # count inverse as covered

        missing_pairs = []
        if referenced:
            for a, b in ((a, b) for a in referenced for b in referenced if a != b):
                if (a, b) not in pairs:
                    missing_pairs.append((a, b))
                    evidence.append(
                        _ev(
                            "Missing FX rate",
                            f"{a} → {b}",
                            source="fx",
                            field=f"fx.missing.{a}.{b}",
                        )
                    )

        if not rates:
            notes.append(
                "You haven't entered any FX rates yet — the engine uses a 1:1 "
                "fallback for cross-currency math, which is almost certainly wrong."
            )
            evidence.append(
                _ev("FX rates on file", "0", source="fx", field="fx.count")
            )
        else:
            evidence.append(
                _ev(
                    "FX rates on file",
                    str(len(rates)),
                    source="fx",
                    field="fx.count",
                )
            )

        if ctx.readiness:
            for note in ctx.readiness.get("missing_inputs") or []:
                notes.append(f"Readiness flagged: {note}")

        if not notes and not missing_pairs:
            return AgentOutput(
                agent=self.name,
                intent=Intent.RESEARCH,
                answer=(
                    "Your data is complete enough for the engine. There are no "
                    "obvious missing inputs or FX gaps right now."
                ),
                confidence=0.7,
                evidence=evidence,
                follow_ups=_common_follow_ups(),
                notes=[],
            )

        answer = (
            f"You have {len(rates)} FX rate(s) on file"
            + (
                f" and {len(missing_pairs)} missing pair(s) for your currencies."
                if missing_pairs
                else "."
            )
        )
        if notes:
            answer += " " + " ".join(notes[:2])

        return AgentOutput(
            agent=self.name,
            intent=Intent.RESEARCH,
            answer=answer,
            confidence=0.7,
            evidence=evidence,
            follow_ups=[
                "Add the missing FX rate.",
                "Show me my current rates.",
            ],
            notes=notes,
        )


# ---------- Registry -------------------------------------------------------

AGENTS: dict[Intent, type[CostRiskAgent | PaymentPlanningAgent | ResearchAgent]] = {
    Intent.COST_RISK: CostRiskAgent,
    Intent.PAYMENT_PLANNING: PaymentPlanningAgent,
    Intent.RESEARCH: ResearchAgent,
}


def agent_for_intent(intent: Intent) -> CostRiskAgent | PaymentPlanningAgent | ResearchAgent:
    """Return a fresh instance of the agent that handles ``intent``.

    Unknown intents fall back to the research agent, which is the
    safest default — it doesn't make numeric claims.
    """

    cls = AGENTS.get(intent, ResearchAgent)
    return cls()

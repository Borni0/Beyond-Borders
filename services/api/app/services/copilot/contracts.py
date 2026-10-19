"""Typed contracts for the multi-agent copilot.

Everything that crosses an agent boundary — request in, agent output out,
orchestrator response out — is one of the Pydantic models defined here.
Validation is the single source of truth for "the agent's output is
well-formed"; if the model can't be constructed, the call fails fast.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------- Enumerations ----------------------------------------------------

class Intent(str, Enum):
    """The user-facing question categories the orchestrator can route.

    These are coarse on purpose: the orchestrator only needs to pick a
    starting agent. Each agent may decide to call additional tools.
    """

    COST_RISK = "cost_risk"
    PAYMENT_PLANNING = "payment_planning"
    RESEARCH = "research"
    UNKNOWN = "unknown"


class AgentName(str, Enum):
    COST_RISK = "cost_risk"
    PAYMENT_PLANNING = "payment_planning"
    RESEARCH = "research"
    EVIDENCE_VALIDATOR = "evidence_validator"


class CopilotStatus(str, Enum):
    """High-level outcome of a copilot run.

    * ``answered`` — an agent produced a validated response.
    * ``fallback`` — the orchestrator could not produce a confident answer
      (e.g. the question was off-topic, or a tool timed out, or the
      user owns no data yet). The response still includes guidance.
    * ``error`` — something went wrong inside the pipeline. ``message``
      contains a user-safe description; details are redacted.
    """

    ANSWERED = "answered"
    FALLBACK = "fallback"
    ERROR = "error"


# ---------- Request / response ---------------------------------------------

class CopilotRequest(BaseModel):
    """The user-submitted question.

    ``plan_id`` is optional. When present, agents will scope their lookups
    to that plan; when absent, the orchestrator picks the user's most
    recent plan. ``upfront_window_days`` controls the readiness snapshot
    used by cost-risk answers.
    """

    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=1, max_length=2000)
    plan_id: str | None = Field(default=None, max_length=64)
    upfront_window_days: int = Field(default=30, ge=1, le=365)

    @field_validator("plan_id")
    @classmethod
    def _strip_plan_id(cls, v: str | None) -> str | None:
        return v.strip() or None if v is not None else None


class CopilotEvidence(BaseModel):
    """A single traceable fact backing part of an agent's answer.

    The frontend renders the trail next to the answer so users can see
    *where* each number came from. ``source_field`` is a dotted path the
    UI can hyperlink to (e.g. ``readiness.funding_gap``,
    ``payment_events[0].amount``).
    """

    model_config = ConfigDict(extra="forbid")

    label: str = Field(..., min_length=1, max_length=120)
    value: str = Field(..., description="Stringified value for display.")
    source: Literal["readiness", "payment", "funding", "plan", "fx", "engine"] = (
        "engine"
    )
    source_field: str = Field(..., min_length=1, max_length=200)


class AgentOutput(BaseModel):
    """What an agent returns to the orchestrator.

    ``answer`` is a short, user-facing summary (1–3 sentences). The
    orchestrator is responsible for adding framing and turning the
    evidence list into the final response. ``confidence`` is a value
    in [0, 1] the orchestrator may use to decide between ``answered``
    and ``fallback``.
    """

    model_config = ConfigDict(extra="forbid")

    agent: AgentName
    intent: Intent
    answer: str = Field(..., min_length=1, max_length=2000)
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: list[CopilotEvidence] = Field(default_factory=list)
    follow_ups: list[str] = Field(
        default_factory=list,
        description="Suggested next questions the user might ask.",
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Caveats / missing inputs the UI should surface.",
    )

    @field_validator("follow_ups", "notes")
    @classmethod
    def _bound_list(cls, v: list[str]) -> list[str]:
        # Defensive cap: agents should return short lists, not essays.
        return [s.strip() for s in v if s and s.strip()][:10]


class CopilotResponse(BaseModel):
    """The final response the API returns to the client."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., min_length=1, max_length=64)
    status: CopilotStatus
    message: str = Field(..., min_length=1, max_length=4000)
    intent: Intent
    primary_agent: AgentName
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: list[CopilotEvidence] = Field(default_factory=list)
    follow_ups: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    plan_id: str | None = None
    generated_at: datetime
    # The full trace is for debugging; the UI can hide it behind a toggle.
    trace: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("plan_id")
    @classmethod
    def _validate_uuid_like(cls, v: str | None) -> str | None:
        if v is None:
            return None
        try:
            UUID(v)
        except (ValueError, AttributeError) as exc:
            raise ValueError("plan_id must be a valid UUID") from exc
        return v

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-friendly dict (Decimal → str, date → ISO)."""

        def _normalize(value: Any) -> Any:
            if isinstance(value, BaseModel):
                return _normalize(value.model_dump())
            if isinstance(value, dict):
                return {k: _normalize(v) for k, v in value.items()}
            if isinstance(value, (list, tuple)):
                return [_normalize(v) for v in value]
            if isinstance(value, Decimal):
                return str(value)
            if isinstance(value, (date, datetime)):
                return value.isoformat()
            return value

        return _normalize(self.model_dump())

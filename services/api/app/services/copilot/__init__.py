"""Beyond Borders Finance Copilot — provider-aware multi-agent architecture.

This package contains the production-ready deterministic engine and an
optional LLM-backed execution path. When no LLM provider is configured, the
system behaves like a transparent rule-based copilot over the user's
persisted financial data. When ``LLM_PROVIDER`` / ``OPENAI_API_KEY`` are set,
this package uses an OpenAI-compatible provider to run specialist-agent
reasoning and then synthesizes the final answer behind the same response
contract.

Design choices, made on purpose:

* **Provider abstraction.** A real LLM integration is optional and guarded
  by configuration, so the app still runs without any external API key.
* **Per-user authorization.** Every tool requires a ``user_id`` and refuses
to read data that doesn't belong to that user.
* **Bounded tool calls + timeouts.** Each tool execution is wrapped in a
  wall-clock timeout. The orchestrator caps the number of tool calls per
  request and always returns a response, even on failure.
* **Validated structured outputs.** Agent outputs are Pydantic models; the
  orchestrator refuses to forward a malformed payload.
* **Evidence trail.** Numeric claims are paired with a ``CopilotEvidence``
  record pointing to the source field on the underlying object.
"""

from app.services.copilot.contracts import (
    AgentName,
    AgentOutput,
    CopilotEvidence,
    CopilotRequest,
    CopilotResponse,
    CopilotStatus,
    Intent,
)
from app.services.copilot.orchestrator import run as run_copilot
from app.services.copilot.providers import get_llm_provider

__all__ = [
    "AgentName",
    "AgentOutput",
    "CopilotEvidence",
    "CopilotRequest",
    "CopilotResponse",
    "CopilotStatus",
    "Intent",
    "get_llm_provider",
    "run_copilot",
]

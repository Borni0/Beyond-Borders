"""LLM provider abstraction for the finance copilot.

The backend is intentionally provider-agnostic: the deterministic engine is
always available, and the LLM-backed specialist workflow is activated only when
an OpenAI-compatible API key and provider are configured.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)


class LLMResponse:
    """Normalized return payload from an LLM provider."""

    def __init__(
        self,
        *,
        ok: bool,
        text: str = "",
        provider: str = "",
        model: str = "",
        error: str | None = None,
        usage: dict[str, Any] | None = None,
    ) -> None:
        self.ok = ok
        self.text = text
        self.provider = provider
        self.model = model
        self.error = error
        self.usage = usage or {}


class LLMProvider(ABC):
    provider_name: str = "provider"
    model: str = ""
    timeout_seconds: float = 30.0

    @abstractmethod
    def is_enabled(self) -> bool:
        """Whether the provider is configured and usable in the current env."""

    @abstractmethod
    def invoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
    ) -> LLMResponse:
        """Return structured text content from the provider."""


class NoopProvider(LLMProvider):
    provider_name = "disabled"
    model = "disabled"
    timeout_seconds = 0.0

    def is_enabled(self) -> bool:
        return False

    def invoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
    ) -> LLMResponse:
        return LLMResponse(
            ok=False,
            text="",
            provider=self.provider_name,
            model=self.model,
            error="LLM provider is disabled or not configured.",
        )


class OpenAICompatibleProvider(LLMProvider):
    provider_name = "openai"
    model = "gpt-4o-mini"

    def __init__(self, *, base_url: str, model: str, timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model or self.model
        self.timeout_seconds = timeout_seconds

    def is_enabled(self) -> bool:
        provider_name = (settings.llm_provider or "").strip().lower()
        if provider_name in {"", "disabled", "off", "none", "false"}:
            return False
        api_key = (settings.llm_api_key or settings.openai_api_key or "").strip()
        return bool(api_key)

    def invoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
    ) -> LLMResponse:
        api_key = (settings.llm_api_key or settings.openai_api_key or "").strip()
        if not api_key:
            return LLMResponse(
                ok=False,
                text="",
                provider=self.provider_name,
                model=self.model,
                error="No API key configured for the LLM provider.",
            )

        chat_url = self.base_url + "/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        provider_name = (settings.llm_provider or "").strip().lower()
        if provider_name.startswith("azure"):
            headers = {
                "Content-Type": "application/json",
                "api-key": api_key,
            }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature if temperature is not None else settings.llm_temperature,
        }

        try:
            response = httpx.post(
                chat_url,
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
        except Exception as exc:  # noqa: BLE001
            log.warning("LLM provider call failed: %s", exc)
            return LLMResponse(
                ok=False,
                text="",
                provider=self.provider_name,
                model=self.model,
                error=f"LLM request failed: {type(exc).__name__}",
            )

        try:
            candidate = body["choices"][0]["message"]["content"]
            text = _coerce_text(candidate)
            usage = body.get("usage") or {}
            return LLMResponse(
                ok=True,
                text=text,
                provider=self.provider_name,
                model=self.model,
                usage=usage,
            )
        except (KeyError, IndexError, TypeError, ValueError):
            log.warning("Unexpected LLM response payload: %s", body)
            return LLMResponse(
                ok=False,
                text="",
                provider=self.provider_name,
                model=self.model,
                error="LLM returned an unparseable payload.",
            )


def _coerce_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        pieces: list[str] = []
        for item in value:
            if isinstance(item, dict):
                content = item.get("text") or item.get("content") or ""
                if isinstance(content, str):
                    pieces.append(content)
            elif isinstance(item, str):
                pieces.append(item)
        return "\n".join(pieces).strip()
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    return str(value)


def get_llm_provider() -> LLMProvider:
    provider_name = (settings.llm_provider or "").strip().lower()
    if provider_name in {"", "disabled", "off", "none", "false"}:
        return NoopProvider()

    if provider_name in {"openai", "openai_compatible", "openai-compatible", "azure-openai", "azure_openai"}:
        base_url = (settings.llm_base_url or settings.openai_base_url or "https://api.openai.com/v1").strip() or "https://api.openai.com/v1"
        model = (settings.llm_model or settings.openai_model or "gpt-4o-mini").strip() or "gpt-4o-mini"
        return OpenAICompatibleProvider(
            base_url=base_url,
            model=model,
            timeout_seconds=settings.llm_timeout_seconds,
        )

    return NoopProvider()

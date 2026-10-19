"""Common Pydantic schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ApiErrorEnvelope(BaseModel):
    code: str
    message: str
    details: dict[str, str] = Field(default_factory=dict)


class ApiErrorResponse(BaseModel):
    error: ApiErrorEnvelope


def error_envelope(code: str, message: str, **details: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = {k: str(v) for k, v in details.items()}
    return body
"""Consistent error envelope and exception handlers (spec §14)."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    """Raise inside services/routes to produce a consistent error response."""

    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}

    def to_envelope(self) -> dict[str, Any]:
        body: dict[str, Any] = {"error": {"code": self.code, "message": self.message}}
        if self.details:
            body["error"]["details"] = self.details
        return body


def _envelope(code: str, message: str, details: dict[str, str] | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return body


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(status_code=exc.http_status, content=exc.to_envelope())

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        details: dict[str, str] = {}
        for err in exc.errors():
            loc = ".".join(str(p) for p in err.get("loc", []) if p not in ("body",))
            if not loc:
                loc = "_root"
            details[loc] = err.get("msg", "Invalid value")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_envelope(
                "VALIDATION_ERROR",
                "Please review the highlighted inputs.",
                details,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code_map = {
            401: "UNAUTHENTICATED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
        }
        code = code_map.get(exc.status_code, "HTTP_ERROR")
        message = str(exc.detail) if exc.detail else "Request failed."
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(code, message),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        # Never leak tracebacks to the client.
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope("INTERNAL_ERROR", "An unexpected error occurred."),
        )
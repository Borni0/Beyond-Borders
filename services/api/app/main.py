"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import api_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    log = get_logger("startup")
    log.info(
        "api_starting",
        env=settings.app_env,
        version=__version__,
        database_url_redacted=_redact(settings.database_url),
    )
    yield
    log.info("api_shutdown")


def _redact(url: str) -> str:
    # Hide credentials in the DB URL when logging.
    if "@" in url:
        head, tail = url.split("@", 1)
        scheme, _ = head.split("://", 1) if "://" in head else ("", head)
        return f"{scheme}://***@{tail}"
    return url


def create_app() -> FastAPI:
    app = FastAPI(
        title="Beyond Borders API",
        version=__version__,
        description=(
            "Phase 1 foundation. Implements authentication, profile, and a "
            "health probe. Business endpoints land in later phases."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
        max_age=600,
    )

    register_exception_handlers(app)

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/api/v1/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
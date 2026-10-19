"""POST /api/v1/copilot — the user-facing entry point."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSessionDep
from app.core.errors import ApiError
from app.services.copilot import run_copilot
from app.services.copilot.contracts import CopilotRequest

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.post("")
def ask_copilot(
    body: CopilotRequest,
    db: DbSessionDep,
    current_user: CurrentUser,
):
    """Answer a financial-readiness question for the current user.

    The body is a strict Pydantic model (no extra fields allowed). The
    response is the validated ``CopilotResponse`` dict — the frontend
    renders the message, evidence trail, and follow-up suggestions.
    """

    try:
        response = run_copilot(
            db, user_id=current_user.id, request=body
        )
    except ApiError:
        # Domain errors already carry user-facing copy; re-raise.
        raise
    except Exception as exc:  # noqa: BLE001
        # Last-resort guard. The orchestrator already returns a fallback
        # response on its own failures, so this branch should be
        # effectively unreachable — but the API contract is "never
        # crash".
        raise ApiError(
            "INTERNAL_ERROR",
            "The copilot could not answer right now.",
            http_status=500,
            details={"reason": type(exc).__name__},
        ) from exc

    return response.to_dict()


__all__ = ["router"]

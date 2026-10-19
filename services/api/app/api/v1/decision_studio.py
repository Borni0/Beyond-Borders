"""Decision Studio endpoints.

Spec §8.1 (Decision Studio):

* ``POST   /api/v1/decision-studio/compare`` — ad-hoc compare of 2-3 plans.
* ``GET    /api/v1/decision-studio/comparisons`` — list the caller's saved
  comparisons.
* ``POST   /api/v1/decision-studio/comparisons`` — save a new comparison.
* ``GET    /api/v1/decision-studio/comparisons/{id}`` — reopen a saved
  comparison; the response is always re-computed from the underlying plans
  (no cached numeric results).
* ``PATCH  /api/v1/decision-studio/comparisons/{id}`` — rename, change
  plan list, or update scenarios.
* ``DELETE /api/v1/decision-studio/comparisons/{id}`` — remove a saved
  comparison.

All plan/comparison lookups are scoped to ``current_user`` and return
``404`` (not ``403``) on cross-tenant access to avoid leaking existence.
"""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.deps import CurrentUser, DbSessionDep
from app.schemas.decision_studio import (
    CompareRequest,
    CompareResult,
    SavedComparisonCreate,
    SavedComparisonPublic,
    SavedComparisonUpdate,
)
from app.services import decision_studio_service

router = APIRouter(prefix="/decision-studio", tags=["decision-studio"])


# ---------- Ad-hoc compare -------------------------------------------------


@router.post("/compare", response_model=CompareResult)
def compare_plans(
    body: CompareRequest,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> CompareResult:
    """Compute a side-by-side comparison for 2-3 plans.

    Scenarios are applied to in-memory copies; nothing on disk changes.
    """
    return decision_studio_service.compare(
        db, user_id=current_user.id, request=body
    )


# ---------- Saved comparisons (CRUD) ---------------------------------------


@router.get("/comparisons", response_model=list[SavedComparisonPublic])
def list_saved(
    db: DbSessionDep,
    current_user: CurrentUser,
) -> list[SavedComparisonPublic]:
    return decision_studio_service.list_saved_comparisons(
        db, user_id=current_user.id
    )


@router.post(
    "/comparisons",
    response_model=SavedComparisonPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_saved(
    body: SavedComparisonCreate,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> SavedComparisonPublic:
    return decision_studio_service.save_comparison(
        db, user_id=current_user.id, body=body
    )


@router.get("/comparisons/{comparison_id}")
def get_saved(
    comparison_id: str,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> JSONResponse:
    """Reopen a saved comparison.

    Returns both the saved-comparison envelope *and* a freshly recomputed
    ``CompareResult`` in a single response so the UI doesn't need a
    second round trip.
    """
    public, result = decision_studio_service.get_saved_comparison(
        db, user_id=current_user.id, comparison_id=comparison_id
    )
    payload = {
        "comparison": public.model_dump(mode="json"),
        "result": result.model_dump(mode="json"),
    }
    return JSONResponse(status_code=status.HTTP_200_OK, content=payload)


@router.patch(
    "/comparisons/{comparison_id}",
    response_model=SavedComparisonPublic,
)
def update_saved(
    comparison_id: str,
    body: SavedComparisonUpdate,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> SavedComparisonPublic:
    return decision_studio_service.update_saved_comparison(
        db,
        user_id=current_user.id,
        comparison_id=comparison_id,
        body=body,
    )


@router.delete(
    "/comparisons/{comparison_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_saved(
    comparison_id: str,
    db: DbSessionDep,
    current_user: CurrentUser,
) -> None:
    decision_studio_service.delete_saved_comparison(
        db, user_id=current_user.id, comparison_id=comparison_id
    )
    return None


__all__ = ["router"]

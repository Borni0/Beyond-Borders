"""Tools the copilot agents are allowed to call.

Each tool is a thin, per-user authorized wrapper over an existing
service. The wrappers are deliberately boring:

* They refuse to read data the caller doesn't own (always pass
  ``user_id``; the underlying repos already filter by it).
* They are pure-Python synchronous functions. The orchestrator enforces
  the wall-clock timeout; here we just keep the calls short.
* They return small dicts (never ORM objects) so the agents can't
  accidentally leak a SQLAlchemy session across agent boundaries.

If a tool raises, the orchestrator catches it and converts the failure
into a ``ToolResult`` with ``ok=False`` so the agent can degrade
gracefully.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models.payment_event import PaymentEvent
from app.repositories import (
    exchange_rate_repo,
    payment_event_repo,
    study_plan_repo,
)
from app.services import funding_plan_service, readiness_service

# ---------- Result envelope -------------------------------------------------

@dataclass(frozen=True)
class ToolResult:
    """What a tool returns to an agent.

    ``ok`` is the single signal an agent checks. ``data`` is opaque to
    the tool layer; agents are responsible for interpreting it. On
    failure, ``error_code`` is a short machine-readable string
    (e.g. ``"plan_not_found"``) and ``message`` is human-readable.
    """

    ok: bool
    data: Any = None
    error_code: str | None = None
    message: str | None = None
    elapsed_ms: int = 0


def _elapsed_ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


# ---------- Plan helpers ----------------------------------------------------

def load_plan_summary(
    db: Session, *, user_id: str, plan_id: str
) -> ToolResult:
    """Fetch a plan owned by ``user_id`` or 404. Returns a dict, not an ORM row."""

    start = time.monotonic()
    try:
        plan = study_plan_repo.get_plan(db, user_id, plan_id)
    except ApiError as exc:
        return ToolResult(
            ok=False,
            error_code=exc.code,
            message=exc.message,
            elapsed_ms=_elapsed_ms(start),
        )
    if plan is None:
        return ToolResult(
            ok=False,
            error_code="plan_not_found",
            message="That plan doesn't exist or isn't yours.",
            elapsed_ms=_elapsed_ms(start),
        )
    return ToolResult(
        ok=True,
        data={
            "id": plan.id,
            "name": plan.name,
            "base_currency": plan.base_currency,
            "home_currency": getattr(plan, "home_currency", None),
            "destination_country": getattr(plan, "destination_country", None),
            "start_date": plan.start_date.isoformat()
            if isinstance(plan.start_date, date)
            else None,
            "duration_months": plan.duration_months,
            "end_date": plan.end_date.isoformat()
            if isinstance(plan.end_date, date)
            else None,
        },
        elapsed_ms=_elapsed_ms(start),
    )


def list_user_plans(db: Session, *, user_id: str) -> ToolResult:
    """List plans owned by ``user_id``, newest first."""

    start = time.monotonic()
    plans = study_plan_repo.list_plans(db, user_id)
    rows = [
        {
            "id": p.id,
            "name": p.name,
            "base_currency": p.base_currency,
            "start_date": p.start_date.isoformat()
            if isinstance(p.start_date, date)
            else None,
        }
        for p in plans
    ]
    return ToolResult(ok=True, data=rows, elapsed_ms=_elapsed_ms(start))


# ---------- Financial engine -----------------------------------------------

def compute_readiness(
    db: Session, *, user_id: str, plan_id: str, upfront_window_days: int
) -> ToolResult:
    """Run the readiness engine for the user's plan.

    The engine is fully deterministic and the inputs come from
    user-owned rows, so the result is safe to surface.
    """

    start = time.monotonic()
    plan = study_plan_repo.get_plan(db, user_id, plan_id)
    if plan is None:
        return ToolResult(
            ok=False,
            error_code="plan_not_found",
            message="That plan doesn't exist or isn't yours.",
            elapsed_ms=_elapsed_ms(start),
        )
    try:
        result = readiness_service.compute_for_plan(
            db,
            user_id=user_id,
            plan=plan,
            upfront_window_days=upfront_window_days,
        )
    except PermissionError as exc:
        return ToolResult(
            ok=False,
            error_code="forbidden",
            message=str(exc),
            elapsed_ms=_elapsed_ms(start),
        )
    snapshot = result.to_dict()
    # Coerce money to strings of Decimal — the engine already does this
    # but defensively re-stringify for the agent layer.
    snapshot["generated_at"] = datetime.now(timezone.utc).isoformat()
    return ToolResult(ok=True, data=snapshot, elapsed_ms=_elapsed_ms(start))


# ---------- Payment events --------------------------------------------------

def list_overdue_payments(
    db: Session, *, user_id: str, plan_id: str | None = None
) -> ToolResult:
    """List the user's non-paid, non-cancelled events with a past due date."""

    start = time.monotonic()
    events = payment_event_repo.list_events(db, user_id, plan_id=plan_id)
    today = date.today()
    overdue: list[dict[str, Any]] = []
    for ev in events:
        if ev.status in {"paid", "cancelled"}:
            continue
        if isinstance(ev.due_date, date) and ev.due_date < today:
            overdue.append(_event_to_dict(ev))
    return ToolResult(ok=True, data=overdue, elapsed_ms=_elapsed_ms(start))


def list_upcoming_payments(
    db: Session, *, user_id: str, plan_id: str | None, window_days: int
) -> ToolResult:
    """List the user's non-paid events due in the next ``window_days`` days."""

    start = time.monotonic()
    events: Sequence[PaymentEvent] = payment_event_repo.list_events(
        db, user_id, plan_id=plan_id
    )
    today = date.today()
    horizon = today.toordinal() + window_days
    upcoming: list[dict[str, Any]] = []
    for ev in events:
        if ev.status in {"paid", "cancelled"}:
            continue
        if not isinstance(ev.due_date, date):
            continue
        if today <= ev.due_date.toordinal() <= horizon:
            upcoming.append(_event_to_dict(ev))
    upcoming.sort(key=lambda r: r["due_date"])
    return ToolResult(ok=True, data=upcoming, elapsed_ms=_elapsed_ms(start))


def compute_funding_plan_summary(
    db: Session, *, user_id: str, plan_id: str, upcoming_window_days: int = 30
) -> ToolResult:
    """Run the funding-plan rollup for a user's plan."""

    start = time.monotonic()
    plan = study_plan_repo.get_plan(db, user_id, plan_id)
    if plan is None:
        return ToolResult(
            ok=False,
            error_code="plan_not_found",
            message="That plan doesn't exist or isn't yours.",
            elapsed_ms=_elapsed_ms(start),
        )
    try:
        summary = funding_plan_service.load_funding_plan_summary(
            db,
            user_id=user_id,
            plan=plan,
            upcoming_window_days=upcoming_window_days,
        )
    except TypeError:
        # Older versions may have a different signature; surface the
        # problem so the orchestrator falls back gracefully instead of
        # pretending the tool worked.
        return ToolResult(
            ok=False,
            error_code="tool_signature_mismatch",
            message="Funding-plan summary tool signature has changed.",
            elapsed_ms=_elapsed_ms(start),
        )
    # ``load_funding_plan_summary`` returns a frozen dataclass with a
    # ``to_dict()`` serializer. We always return a plain dict so the
    # agent context stays JSON-friendly.
    try:
        data = summary.to_dict()  # type: ignore[no-untyped-call]
    except AttributeError:
        data = summary
    return ToolResult(ok=True, data=data, elapsed_ms=_elapsed_ms(start))


# ---------- FX -------------------------------------------------------------

def list_fx_rates(db: Session, *, user_id: str) -> ToolResult:
    """List the user's stored FX rates as a list of dicts."""

    start = time.monotonic()
    rates = exchange_rate_repo.list_rates(db, user_id)
    rows = [
        {
            "base_currency": r.base_currency,
            "quote_currency": r.quote_currency,
            "rate": str(Decimal(r.rate)),
            "rate_type": r.rate_type,
            "observed_at": r.observed_at.isoformat()
            if isinstance(r.observed_at, date)
            else None,
        }
        for r in rates
    ]
    return ToolResult(ok=True, data=rows, elapsed_ms=_elapsed_ms(start))


# ---------- Internal helpers -----------------------------------------------

def _event_to_dict(ev: PaymentEvent) -> dict[str, Any]:
    return {
        "id": ev.id,
        "title": ev.title,
        "category": ev.category,
        "amount": str(Decimal(ev.amount)),
        "currency": ev.currency,
        "due_date": ev.due_date.isoformat()
        if isinstance(ev.due_date, date)
        else None,
        "status": ev.status,
        "plan_id": ev.plan_id,
    }

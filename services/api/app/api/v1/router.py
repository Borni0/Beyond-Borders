"""Top-level v1 router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    copilot,
    costs,
    decision_studio,
    expenses,
    funding,
    funding_plan,
    fx,
    payments,
    readiness,
    savings,
    sources,
    stress_test,
    study_plans,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(study_plans.router)
api_router.include_router(costs.router)
api_router.include_router(funding.router)
api_router.include_router(sources.router)
api_router.include_router(fx.router)
api_router.include_router(readiness.router)
api_router.include_router(payments.router)
api_router.include_router(savings.router)
api_router.include_router(funding_plan.router)
api_router.include_router(copilot.router)
api_router.include_router(decision_studio.router)
api_router.include_router(stress_test.router)
api_router.include_router(expenses.router)

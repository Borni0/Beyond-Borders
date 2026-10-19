"""Phase 1 readiness enrichment: extended study-plan fields + cost-item flag.

Revision ID: 0004_readiness_enrichment
Revises: 0003_phase2_payments
Create Date: 2026-10-19

Adds columns that the Financial Readiness workspace needs but Phase 1 left
out as deferred details. All new columns are nullable or have a server
default so existing rows survive intact.

study_plans
- institution_name       — the university / school the user picked
- program_name           — the degree / course name
- city                   — destination city (separate from country)
- tuition_amount         — first-year tuition in the plan's base currency
- tuition_currency       — currency the user quoted the tuition in
                           (may differ from base_currency, so the engine
                            still has to convert it)
- home_currency          — the user's home currency (separate from base)

cost_items
- due_before_departure   — flag the cost as "must be paid before the
                           plan's start_date" so the upfront-cash
                           projection can pick it up even when the
                           start_date is in the future
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0004_readiness_enrichment"
down_revision = "0003_phase2_payments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "study_plans",
        sa.Column("institution_name", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "study_plans",
        sa.Column("program_name", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "study_plans",
        sa.Column("city", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "study_plans",
        sa.Column("tuition_amount", sa.Numeric(18, 4), nullable=True),
    )
    op.add_column(
        "study_plans",
        sa.Column("tuition_currency", sa.String(length=3), nullable=True),
    )
    op.add_column(
        "study_plans",
        sa.Column("home_currency", sa.String(length=3), nullable=True),
    )

    op.add_column(
        "cost_items",
        sa.Column(
            "due_before_departure",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("cost_items", "due_before_departure")

    op.drop_column("study_plans", "home_currency")
    op.drop_column("study_plans", "tuition_currency")
    op.drop_column("study_plans", "tuition_amount")
    op.drop_column("study_plans", "city")
    op.drop_column("study_plans", "program_name")
    op.drop_column("study_plans", "institution_name")

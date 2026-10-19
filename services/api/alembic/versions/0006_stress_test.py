"""Stress Test: stress_scenarios table.

Revision ID: 0006_stress_test
Revises: 0005_decision_studio
Create Date: 2026-10-19

A stress scenario is a named, reusable bundle of overrides the user
applies to a plan to model bad days — rent shock, scholarship cut,
delayed family support, FX shock, deposit change, or a free-form note.

Schema
------

* ``scenario_key`` — short identifier the UI uses as a preset chip
  (``rent_shock``, ``scholarship_cut``, ``fx_shock``, ``custom``).
* ``adjustments`` — JSON list of adjustment specs, same shape as the
  Decision Studio scenario adjustments. Stored as JSONB on Postgres
  and TEXT on SQLite.
* ``scope`` — ``"plan"`` (overrides apply to one plan when re-run) or
  ``"global"`` (the same scenario can be re-run against any plan).
  Plan-scoped rows keep the plan_id; global rows leave it NULL.

The numeric results are **never** persisted — every re-run recomputes
from the plan's current costs/funding/rates so stale numbers cannot
leak in.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0006_stress_test"
down_revision = "0005_decision_studio"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stress_scenarios",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "plan_id",
            sa.String(length=36),
            sa.ForeignKey("study_plans.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("scenario_key", sa.String(length=40), nullable=False),
        sa.Column(
            "adjustments",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_stress_scenarios_user_id",
        "stress_scenarios",
        ["user_id"],
    )
    op.create_index(
        "ix_stress_scenarios_plan_id",
        "stress_scenarios",
        ["plan_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_stress_scenarios_plan_id", table_name="stress_scenarios")
    op.drop_index("ix_stress_scenarios_user_id", table_name="stress_scenarios")
    op.drop_table("stress_scenarios")

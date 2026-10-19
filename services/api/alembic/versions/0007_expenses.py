"""Expense tracking: expenses table (Phase 4).

Revision ID: 0007_expenses
Revises: 0006_stress_test
Create Date: 2026-10-19

Adds the ``expenses`` table for the Spending Tracker (spec §3.6).
Each row is one logged expense:

* ``plan_id`` — nullable. Most expenses are logged against a plan,
  but the user can also log standalone rows.
* ``category`` — same vocabulary as cost-items / payment categories
  (food, transport, etc.).
* ``amount`` + ``currency`` — what they spent and in what currency.
* ``spent_on`` — date the expense happened. Stored as DATE so we can
  bucket by month without timezone surprises.
* ``payment_method`` — free-text (cash, card, transfer).
* ``notes`` — optional long-form notes.

Indices:
* ``(user_id, spent_on)`` — every summary query ("this month", "last
  month", "by category") filters by user + date range.
* ``(plan_id)`` — when a row is linked to a plan, lookup by plan.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0007_expenses"
down_revision = "0006_stress_test"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "expenses",
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
            sa.ForeignKey("study_plans.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("spent_on", sa.Date(), nullable=False),
        sa.Column("payment_method", sa.String(length=64), nullable=True),
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
    op.create_index("ix_expenses_user_id", "expenses", ["user_id"])
    op.create_index("ix_expenses_plan_id", "expenses", ["plan_id"])
    op.create_index(
        "ix_expenses_user_spent_on",
        "expenses",
        ["user_id", "spent_on"],
    )


def downgrade() -> None:
    op.drop_index("ix_expenses_user_spent_on", table_name="expenses")
    op.drop_index("ix_expenses_plan_id", table_name="expenses")
    op.drop_index("ix_expenses_user_id", table_name="expenses")
    op.drop_table("expenses")
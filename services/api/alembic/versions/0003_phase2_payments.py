"""Phase 2 funding and payment planning: payment events + savings goals.

Revision ID: 0003_phase2_payments
Revises: 0002_phase1_readiness
Create Date: 2026-10-19

Adds two tables:

* ``payment_events`` — operational bills the student expects to pay (deposits,
  tuition installments, rent, flights, visa fees). Has a due date, status
  (``planned`` / ``scheduled`` / ``paid`` / ``overdue`` / ``cancelled``), and
  optional recurrence for things like monthly rent. ``overdue`` is a *display*
  state — never written to this column.
* ``savings_goals`` — a target amount + currency + target date the student is
  saving toward. ``current_amount`` is updated as the user logs progress.

Both tables cascade on the owning user and ``SET NULL`` on the optional plan
link, matching the pattern in ``0002_phase1_readiness``.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0003_phase2_payments"
down_revision = "0002_phase1_readiness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("plan_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="planned",
        ),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column(
            "is_recurring",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("recurrence_frequency", sa.String(length=16), nullable=True),
        sa.Column("recurrence_end_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_payment_events_user_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["study_plans.id"],
            name="fk_payment_events_plan_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_payment_events_user_id", "payment_events", ["user_id"])
    op.create_index("ix_payment_events_plan_id", "payment_events", ["plan_id"])
    op.create_index("ix_payment_events_due_date", "payment_events", ["due_date"])

    op.create_table(
        "savings_goals",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("plan_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("target_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column(
            "current_amount",
            sa.Numeric(18, 4),
            nullable=False,
            server_default="0",
        ),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_savings_goals_user_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["study_plans.id"],
            name="fk_savings_goals_plan_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_savings_goals_user_id", "savings_goals", ["user_id"])
    op.create_index("ix_savings_goals_plan_id", "savings_goals", ["plan_id"])


def downgrade() -> None:
    op.drop_index("ix_savings_goals_plan_id", table_name="savings_goals")
    op.drop_index("ix_savings_goals_user_id", table_name="savings_goals")
    op.drop_table("savings_goals")

    op.drop_index("ix_payment_events_due_date", table_name="payment_events")
    op.drop_index("ix_payment_events_plan_id", table_name="payment_events")
    op.drop_index("ix_payment_events_user_id", table_name="payment_events")
    op.drop_table("payment_events")

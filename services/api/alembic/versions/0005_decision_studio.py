"""Decision Studio: study_plan_comparisons table.

Revision ID: 0005_decision_studio
Revises: 0004_readiness_enrichment
Create Date: 2026-10-19

Adds the saved-comparison entity. We persist the plan IDs and any
scenario deltas, but **never** persist the numeric results — the
comparison is always re-computed from the underlying plans on read so
the user is never shown stale numbers when a plan changes.

Schema:

* ``selected_plan_ids`` — JSON list of plan UUIDs (2 or 3). On Postgres
  this is a real ``jsonb`` column; on SQLite (used in tests) it falls
  back to ``text`` because the in-memory engine doesn't ship JSONB.
* ``scenarios`` — JSON list of per-plan scenario specs. ``NULL`` means
  "use the baseline plans unchanged".
* ``calculation_version`` — opaque string the service layer stamps so
  the UI can warn when results were produced by a newer engine than
  the one the comparison was originally saved with.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0005_decision_studio"
down_revision = "0004_readiness_enrichment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "study_plan_comparisons",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        # JSON list of plan IDs. JSONB on Postgres; text on SQLite.
        sa.Column(
            "selected_plan_ids",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(
                sa.Text(), "sqlite"
            ),
            nullable=False,
        ),
        sa.Column(
            "scenarios",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(
                sa.Text(), "sqlite"
            ),
            nullable=True,
        ),
        sa.Column(
            "calculation_version",
            sa.String(length=40),
            nullable=False,
            server_default="decision_studio_v1",
        ),
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
        "ix_study_plan_comparisons_user_id",
        "study_plan_comparisons",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_study_plan_comparisons_user_id", table_name="study_plan_comparisons"
    )
    op.drop_table("study_plan_comparisons")

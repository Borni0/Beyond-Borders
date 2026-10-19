"""Phase 1 readiness: study plans, costs, funding, sources, FX.

Revision ID: 0002_phase1_readiness
Revises: 0001_init
Create Date: 2026-10-19

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_phase1_readiness"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_sources",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("url", sa.String(length=2000), nullable=True),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_data_sources_user_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_data_sources_user_id", "data_sources", ["user_id"])

    op.create_table(
        "exchange_rates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("base_currency", sa.String(length=3), nullable=False),
        sa.Column("quote_currency", sa.String(length=3), nullable=False),
        sa.Column("rate", sa.Numeric(18, 8), nullable=False),
        sa.Column(
            "rate_type",
            sa.String(length=16),
            nullable=False,
            server_default="user_entered",
        ),
        sa.Column("observed_at", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_exchange_rates_user_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_id", "base_currency", "quote_currency",
            name="uq_exchange_rates_user_pair",
        ),
    )
    op.create_index("ix_exchange_rates_user_id", "exchange_rates", ["user_id"])

    op.create_table(
        "study_plans",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("destination_country", sa.String(length=2), nullable=True),
        sa.Column("base_currency", sa.String(length=3), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("duration_months", sa.Integer(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_study_plans_user_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_study_plans_user_id", "study_plans", ["user_id"])

    op.create_table(
        "cost_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("plan_id", sa.String(length=36), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("frequency", sa.String(length=16), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_one_time", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "is_refundable", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("source_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["study_plans.id"],
            name="fk_cost_items_plan_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
            name="fk_cost_items_source_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_cost_items_plan_id", "cost_items", ["plan_id"])
    op.create_index("ix_cost_items_source_id", "cost_items", ["source_id"])

    op.create_table(
        "funding_sources",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("plan_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("funding_type", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("expected_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["study_plans.id"],
            name="fk_funding_sources_plan_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_funding_sources_plan_id", "funding_sources", ["plan_id"])


def downgrade() -> None:
    op.drop_index("ix_funding_sources_plan_id", table_name="funding_sources")
    op.drop_table("funding_sources")
    op.drop_index("ix_cost_items_source_id", table_name="cost_items")
    op.drop_index("ix_cost_items_plan_id", table_name="cost_items")
    op.drop_table("cost_items")
    op.drop_index("ix_study_plans_user_id", table_name="study_plans")
    op.drop_table("study_plans")
    op.drop_index("ix_exchange_rates_user_id", table_name="exchange_rates")
    op.drop_table("exchange_rates")
    op.drop_index("ix_data_sources_user_id", table_name="data_sources")
    op.drop_table("data_sources")

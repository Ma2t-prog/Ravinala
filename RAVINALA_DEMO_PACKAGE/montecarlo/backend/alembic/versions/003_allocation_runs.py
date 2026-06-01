"""Add persisted allocation recommendation runs.

Revision ID: 003
Revises: 002
Create Date: 2026-03-24 12:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "allocation_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("recommendation_id", sa.String(length=36), nullable=False, unique=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("base_currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("objective_used", sa.String(length=32), nullable=False),
        sa.Column("risk_profile", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="completed"),
        sa.Column("investor_policy", sa.JSON(), nullable=False),
        sa.Column("eligibility_snapshot", sa.JSON(), nullable=False),
        sa.Column("assumptions_snapshot", sa.JSON(), nullable=False),
        sa.Column("request_payload", sa.JSON(), nullable=False),
        sa.Column("eligible_tickers", sa.JSON(), nullable=False),
        sa.Column("recommended_assets", sa.JSON(), nullable=False),
        sa.Column("rejected_assets", sa.JSON(), nullable=True),
        sa.Column("optimization_summary", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=True),
        sa.Column("total_allocated_amount", sa.Float(), nullable=False),
        sa.Column("cash_reserve_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_allocation_runs_created_at",
        "allocation_runs",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_allocation_runs_objective_used",
        "allocation_runs",
        ["objective_used"],
        unique=False,
    )
    op.create_index(
        "ix_allocation_runs_risk_profile",
        "allocation_runs",
        ["risk_profile"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_allocation_runs_risk_profile", table_name="allocation_runs")
    op.drop_index("ix_allocation_runs_objective_used", table_name="allocation_runs")
    op.drop_index("ix_allocation_runs_created_at", table_name="allocation_runs")
    op.drop_table("allocation_runs")

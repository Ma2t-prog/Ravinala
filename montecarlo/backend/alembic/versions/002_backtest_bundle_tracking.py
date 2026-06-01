"""Add backtest bundle tracking and persisted comparison metadata.

Revision ID: 002
Revises: 001
Create Date: 2026-03-23 18:40:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("backtest_runs", sa.Column("bundle_id", UUID(as_uuid=True), nullable=True))
    op.add_column(
        "backtest_runs",
        sa.Column("bundle_role", sa.String(length=32), nullable=False, server_default="primary"),
    )
    op.add_column("backtest_runs", sa.Column("comparison", sa.JSON(), nullable=True))
    op.add_column("backtest_runs", sa.Column("deployment_policy", sa.Text(), nullable=True))
    op.create_index("ix_backtest_runs_bundle_id", "backtest_runs", ["bundle_id"], unique=False)
    op.create_index("ix_backtest_runs_bundle_role", "backtest_runs", ["bundle_role"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_backtest_runs_bundle_role", table_name="backtest_runs")
    op.drop_index("ix_backtest_runs_bundle_id", table_name="backtest_runs")
    op.drop_column("backtest_runs", "deployment_policy")
    op.drop_column("backtest_runs", "comparison")
    op.drop_column("backtest_runs", "bundle_role")
    op.drop_column("backtest_runs", "bundle_id")

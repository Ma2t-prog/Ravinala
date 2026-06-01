"""Add business entities (portfolios, positions, transactions, backtests, ML, signals, audit)

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'portfolios',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('owner', sa.String(100), nullable=False, index=True),
        sa.Column('strategy', sa.String(50), server_default='balanced'),
        sa.Column('base_currency', sa.String(3), server_default='USD'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('is_active', sa.Boolean, server_default=sa.text('true')),
    )

    op.create_table(
        'positions',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('portfolio_id', UUID(as_uuid=True), sa.ForeignKey('portfolios.id'), nullable=False, index=True),
        sa.Column('symbol', sa.String(20), nullable=False, index=True),
        sa.Column('quantity', sa.Numeric(18, 8), nullable=False),
        sa.Column('avg_cost', sa.Numeric(18, 6)),
        sa.Column('current_price', sa.Numeric(18, 6)),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        'transactions',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('portfolio_id', UUID(as_uuid=True), sa.ForeignKey('portfolios.id'), nullable=False, index=True),
        sa.Column('symbol', sa.String(20), nullable=False, index=True),
        sa.Column('side', sa.String(4), nullable=False),
        sa.Column('quantity', sa.Numeric(18, 8), nullable=False),
        sa.Column('price', sa.Numeric(18, 6), nullable=False),
        sa.Column('fees', sa.Numeric(12, 4), server_default='0'),
        sa.Column('executed_at', sa.DateTime, nullable=False),
        sa.Column('source', sa.String(50), server_default='manual'),
    )

    op.create_table(
        'backtest_runs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('strategy', sa.String(100), nullable=False),
        sa.Column('start_date', sa.Date, nullable=False),
        sa.Column('end_date', sa.Date, nullable=False),
        sa.Column('initial_capital', sa.Numeric(18, 2), server_default='100000'),
        sa.Column('final_value', sa.Numeric(18, 2)),
        sa.Column('total_return_pct', sa.Float),
        sa.Column('sharpe_ratio', sa.Float),
        sa.Column('max_drawdown_pct', sa.Float),
        sa.Column('params', sa.JSON),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        'backtest_trades',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('run_id', UUID(as_uuid=True), sa.ForeignKey('backtest_runs.id'), nullable=False, index=True),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('side', sa.String(4), nullable=False),
        sa.Column('quantity', sa.Numeric(18, 8), nullable=False),
        sa.Column('price', sa.Numeric(18, 6), nullable=False),
        sa.Column('executed_at', sa.DateTime, nullable=False),
        sa.Column('pnl', sa.Float),
    )

    op.create_table(
        'model_versions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('model_name', sa.String(100), nullable=False, index=True),
        sa.Column('version', sa.Integer, nullable=False),
        sa.Column('framework', sa.String(50), nullable=False),
        sa.Column('artifact_path', sa.Text),
        sa.Column('metrics', sa.JSON),
        sa.Column('params', sa.JSON),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('is_active', sa.Boolean, server_default=sa.text('false')),
    )

    op.create_table(
        'prediction_runs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('model_version_id', UUID(as_uuid=True), sa.ForeignKey('model_versions.id')),
        sa.Column('symbol', sa.String(20), nullable=False, index=True),
        sa.Column('horizon_days', sa.Integer, nullable=False),
        sa.Column('predicted_return', sa.Float),
        sa.Column('predicted_direction', sa.String(10)),
        sa.Column('confidence', sa.Float),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        'signal_instances',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('symbol', sa.String(20), nullable=False, index=True),
        sa.Column('signal_type', sa.String(50), nullable=False),
        sa.Column('composite_score', sa.Float, nullable=False),
        sa.Column('confidence', sa.Float),
        sa.Column('sub_signals', sa.JSON),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime),
    )

    op.create_table(
        'audit_events',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('event_type', sa.String(100), nullable=False, index=True),
        sa.Column('actor', sa.String(100)),
        sa.Column('resource', sa.String(200)),
        sa.Column('detail', sa.JSON),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('audit_events')
    op.drop_table('signal_instances')
    op.drop_table('prediction_runs')
    op.drop_table('model_versions')
    op.drop_table('backtest_trades')
    op.drop_table('backtest_runs')
    op.drop_table('transactions')
    op.drop_table('positions')
    op.drop_table('portfolios')

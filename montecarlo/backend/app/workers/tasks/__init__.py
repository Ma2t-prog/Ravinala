"""
workers/tasks — All Celery task modules.
"""
from app.workers.tasks.fetch_task import refresh_snapshot  # noqa: F401
from app.workers.tasks.backtest_task import run_backtest  # noqa: F401
from app.workers.tasks.ml_task import train_model  # noqa: F401
from app.workers.tasks.risk_task import compute_risk  # noqa: F401
from app.workers.tasks.portfolio_task import optimize_portfolio  # noqa: F401
from app.workers.tasks.analysis_task import analyze_company  # noqa: F401

"""
routes — APIRouter registry.
"""

from app.routes.market import router as market_router
from app.routes.export import router as export_router
from app.routes.generate import router as generate_router
from app.routes.events import router as events_router
from app.routes.ml import router as ml_router
from app.routes.backtest import router as backtest_router
from app.routes.risk import router as risk_router
from app.routes.jobs import router as jobs_router
from app.routes.monitoring import router as monitoring_router
from app.routes.auth import router as auth_router
from app.routes.users import router as users_router
from app.routes.universe import router as universe_router
from app.routes.portfolio import router as portfolio_router
from app.routes.allocator import router as allocator_router
from app.routes.analysis import router as analysis_router
try:
    from app.routes.agents import router as agents_router
except ModuleNotFoundError:
    agents_router = None

__all__ = ["market_router", "export_router", "generate_router", "events_router", "ml_router", "backtest_router", "risk_router", "jobs_router", "monitoring_router", "auth_router", "users_router", "universe_router", "portfolio_router", "allocator_router", "analysis_router", "agents_router"]

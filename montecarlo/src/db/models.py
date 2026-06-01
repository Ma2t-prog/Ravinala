"""
src/db/models.py — SQLAlchemy ORM models for market data & business entities.

IMPORTANT — TWO models.py FILES EXIST:
──────────────────────────────────────
1. backend/app/db/models.py:
   - Async SQLAlchemy 2.0 (Mapped style) — used by FastAPI routes
   - Authoritative for: users, sessions, api_events, price_fetch_log,
     ml_runs, ml_predictions, backtest_runs (API), backtest_trades (API),
     risk_snapshots

2. THIS FILE (src/db/models.py):
   - Sync SQLAlchemy Classic (Column style) — used by src/ modules
   - Authoritative for: market_quotes, assets, risk_metrics,
     correlation_snapshots, data_quality_log, portfolios, positions,
     transactions, model_versions, prediction_runs, signal_instances,
     audit_events

Rule: when adding a table, decide which layer owns it and add to ONE file only.
──────────────────────────────────────
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, BigInteger, DateTime,
    Index, Boolean, Date, Text, Numeric, JSON, ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Mapped
from typing import TYPE_CHECKING, List
if TYPE_CHECKING:
    pass
from datetime import datetime
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

# Database connection
_db_password = os.getenv('DB_PASSWORD')
if not _db_password:
    raise EnvironmentError("DB_PASSWORD environment variable is required. Set it in .env or your environment.")

DATABASE_URL = f"postgresql://{os.getenv('DB_USER', 'ravinala')}:{_db_password}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'market_data')}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=40,
    pool_recycle=3600,
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ==================== MODELS ====================

class MarketQuote(Base):
    """Market quote data (OHLCV)"""
    __tablename__ = "market_quotes"
    
    id = Column(BigInteger, primary_key=True, index=True)
    symbol = Column(String(20), index=True)
    ts = Column(DateTime, index=True)
    open = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    close = Column(Float, nullable=True)
    adj_close = Column(Float, nullable=True)
    volume = Column(BigInteger, nullable=True)
    source = Column(String(50))
    interval = Column(String(10), default='1m')

class Asset(Base):
    """Asset metadata"""
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), unique=True, index=True)
    name = Column(String(200), nullable=True)
    asset_type = Column(String(50), nullable=True)
    sector = Column(String(100), nullable=True)
    country = Column(String(50), nullable=True)
    exchange = Column(String(50), nullable=True)

class RiskMetric(Base):
    """Risk calculations"""
    __tablename__ = "risk_metrics"
    
    id = Column(BigInteger, primary_key=True)
    ts = Column(DateTime, index=True)
    symbol = Column(String(20), index=True)
    var_95 = Column(Float, nullable=True)
    cvar_95 = Column(Float, nullable=True)
    volatility = Column(Float, nullable=True)
    sharpe_ratio = Column(Float, nullable=True)
    lookback_days = Column(Integer, default=252)

class CorrelationSnapshot(Base):
    """Correlation matrix snapshot"""
    __tablename__ = "correlation_snapshots"
    
    id = Column(BigInteger, primary_key=True)
    ts = Column(DateTime, index=True)
    symbol1 = Column(String(20), index=True)
    symbol2 = Column(String(20), index=True)
    correlation_pearson = Column(Float, nullable=True)
    correlation_spearman = Column(Float, nullable=True)
    lookback_days = Column(Integer, default=252)

class DataQualityLog(Base):
    """Data quality checks log"""
    __tablename__ = "data_quality_log"
    
    id = Column(BigInteger, primary_key=True)
    symbol = Column(String(20), nullable=True)
    check_type = Column(String(100), nullable=True)
    issue_count = Column(Integer, nullable=True)
    ts_start = Column(DateTime, nullable=True)
    ts_end = Column(DateTime, nullable=True)


# ==================== BUSINESS ENTITIES (Étape 2) ====================

class Portfolio(Base):
    """User portfolio"""
    __tablename__ = "portfolios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    owner = Column(String(100), nullable=False, index=True)
    strategy = Column(String(50), default='balanced')
    base_currency = Column(String(3), default='USD')
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)


class Position(Base):
    """Portfolio position"""
    __tablename__ = "positions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    quantity = Column(Numeric(18, 8), nullable=False)
    avg_cost = Column(Numeric(18, 6), nullable=True)
    current_price = Column(Numeric(18, 6), nullable=True)
    updated_at = Column(DateTime, server_default=func.now())


class Transaction(Base):
    """Trade / cash-flow event"""
    __tablename__ = "transactions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(4), nullable=False)  # BUY / SELL
    quantity = Column(Numeric(18, 8), nullable=False)
    price = Column(Numeric(18, 6), nullable=False)
    fees = Column(Numeric(12, 4), default=0)
    executed_at = Column(DateTime, nullable=False)
    source = Column(String(50), default='manual')


class BacktestRun(Base):
    """Backtest execution record — synced with backend/app/db/models.py (R4)"""
    __tablename__ = "backtest_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bundle_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    bundle_role = Column(String(32), nullable=False, default="primary", index=True)
    run_name = Column(String(128), nullable=False)
    strategy = Column(String(64), nullable=False)
    level = Column(String(16), nullable=False, default="exploration")
    assets = Column(JSON, nullable=False)
    benchmark = Column(String(32), nullable=False, default="SPY")
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    params = Column(JSON, nullable=True)
    seed = Column(Integer, nullable=True)
    initial_capital = Column(Float, nullable=False, default=100_000.0)
    commission_bps = Column(Float, nullable=False, default=5.0)
    slippage_bps = Column(Float, nullable=False, default=5.0)
    cost_model = Column(String(32), nullable=False, default="flat_bps")
    metrics = Column(JSON, nullable=True)
    benchmark_metrics = Column(JSON, nullable=True)
    comparison = Column(JSON, nullable=True)
    limitations = Column(JSON, nullable=True)
    deployment_policy = Column(Text, nullable=True)
    ml_run_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(String(16), nullable=False, default="running")
    error_message = Column(Text, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    n_trades = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    trades: Mapped[list] = relationship("BacktestTrade", back_populates="run", cascade="all, delete-orphan")


class BacktestTrade(Base):
    """Individual trade within a backtest — synced with backend/app/db/models.py (R4)"""
    __tablename__ = "backtest_trades"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey("backtest_runs.id"), nullable=False, index=True)
    trade_date = Column(DateTime, nullable=False)
    asset = Column(String(32), nullable=False)
    side = Column(String(4), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    commission = Column(Float, nullable=False, default=0.0)
    slippage = Column(Float, nullable=False, default=0.0)
    portfolio_value = Column(Float, nullable=True)
    cash_after = Column(Float, nullable=True)
    reason = Column(String(128), nullable=True)

    run: Mapped["BacktestRun"] = relationship("BacktestRun", back_populates="trades")


class ModelVersion(Base):
    """ML model version registry"""
    __tablename__ = "model_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name = Column(String(100), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    framework = Column(String(50), nullable=False)  # xgboost, lightgbm, sklearn
    artifact_path = Column(Text, nullable=True)
    metrics = Column(JSON, nullable=True)
    params = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=False)


class PredictionRun(Base):
    """ML prediction execution"""
    __tablename__ = "prediction_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_version_id = Column(UUID(as_uuid=True), ForeignKey("model_versions.id"), nullable=True)
    symbol = Column(String(20), nullable=False, index=True)
    horizon_days = Column(Integer, nullable=False)
    predicted_return = Column(Float, nullable=True)
    predicted_direction = Column(String(10), nullable=True)  # up / down / flat
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class SignalInstance(Base):
    """Generated trading signal"""
    __tablename__ = "signal_instances"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    signal_type = Column(String(50), nullable=False)  # buy, sell, hold, strong_buy, strong_sell
    composite_score = Column(Float, nullable=False)
    confidence = Column(Float, nullable=True)
    sub_signals = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=True)


class AuditEvent(Base):
    """System audit trail"""
    __tablename__ = "audit_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_type = Column(String(100), nullable=False, index=True)
    actor = Column(String(100), nullable=True)
    resource = Column(String(200), nullable=True)
    detail = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


# Database utilities
def get_db():
    """Get database session (FastAPI dependency)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)


__all__ = [
    "engine",
    "SessionLocal",
    "Base",
    "MarketQuote",
    "Asset",
    "RiskMetric",
    "CorrelationSnapshot",
    "DataQualityLog",
    "Portfolio",
    "Position",
    "Transaction",
    "BacktestRun",
    "BacktestTrade",
    "ModelVersion",
    "PredictionRun",
    "SignalInstance",
    "AuditEvent",
    "get_db",
    "create_tables",
]

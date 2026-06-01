"""
db/models.py — SQLAlchemy ORM models for Ravinala persistence layer.

IMPORTANT — TWO models.py FILES EXIST:
──────────────────────────────────────
1. THIS FILE (backend/app/db/models.py):
   - Async SQLAlchemy 2.0 (Mapped style) — used by FastAPI routes
   - Tables: users, sessions, api_events, price_fetch_log,
     ml_runs, ml_predictions, backtest_runs, backtest_trades,
     risk_snapshots
   - Base from: app.db.base.Base

2. src/db/models.py:
   - Sync SQLAlchemy Classic (Column style) — used by src/ modules
   - Tables: market_quotes, assets, risk_metrics, correlation_snapshots,
     data_quality_log, portfolios, positions, transactions,
     backtest_runs*, backtest_trades*, model_versions, prediction_runs,
     signal_instances, audit_events
   - *BacktestRun/BacktestTrade are defined in BOTH files with DIFFERENT schemas.
     Backend version (this file) is authoritative for API operations.
     src/ version is authoritative for Streamlit/analysis operations.

Rule: when adding a table, decide which layer owns it and add to ONE file only.
──────────────────────────────────────

Étape 2 — Persistance minimale
──────────────────────────────
4 tables:
  users           — registered users (optional auth)
  sessions        — anonymous or authenticated sessions (traceability)
  api_events      — every API call logged (endpoint, latency, demo_data flag)
  price_fetch_log — each yfinance/provider fetch with quality metadata

Design principles (from construction22032026.docx):
  - Every data event MUST be traceable
  - demo_data flag propagated from data_quality: "demo_static" in fetchers
  - No LSTM / no composite signals here — just operational metadata
  - Audit log is append-only (no UPDATE on api_events or price_fetch_log)
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════
# USERS
# ═══════════════════════════════════════════════════════════════════════════

class User(Base):
    """
    Registered user.  Authentication is optional — anonymous sessions are
    allowed (user_id = NULL on Session).
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    # Étape 12 — Bcrypt password hash (nullable for pre-auth users)
    password_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    # Role: "viewer" | "analyst" | "admin"
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="viewer")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, server_default=func.now()
    )
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.username!r} role={self.role!r}>"


# ═══════════════════════════════════════════════════════════════════════════
# SESSIONS
# ═══════════════════════════════════════════════════════════════════════════

class Session(Base):
    """
    Browser/API session.  user_id is nullable for anonymous sessions.
    Provides traceability without requiring authentication.
    """
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # e.g. {"ip": "...", "user_agent": "..."}  stored as JSON text
    client_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User | None"] = relationship(back_populates="sessions")
    events: Mapped[list["ApiEvent"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_sessions_user_id", "user_id"),
        Index("ix_sessions_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Session {self.id} user={self.user_id}>"


# ═══════════════════════════════════════════════════════════════════════════
# API EVENTS  (append-only audit log)
# ═══════════════════════════════════════════════════════════════════════════

class ApiEvent(Base):
    """
    Append-only log of every API request.

    demo_data = True when the response was served from static/mock data
    (i.e. data_quality == "demo_static").  This lets us audit how often
    real vs demo data is served.
    """
    __tablename__ = "api_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
    # HTTP metadata
    endpoint: Mapped[str] = mapped_column(String(256), nullable=False)
    method: Mapped[str] = mapped_column(String(8), nullable=False, default="GET")
    status_code: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=200)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Data quality flag — propagated from data_fetcher.py response
    demo_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Cache hit: True when data was served from Redis / in-memory cache
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, server_default=func.now()
    )

    session: Mapped["Session | None"] = relationship(back_populates="events")

    __table_args__ = (
        Index("ix_api_events_endpoint", "endpoint"),
        Index("ix_api_events_created_at", "created_at"),
        Index("ix_api_events_demo_data", "demo_data"),
    )

    def __repr__(self) -> str:
        return f"<ApiEvent {self.method} {self.endpoint} {self.status_code}>"


# ═══════════════════════════════════════════════════════════════════════════
# PRICE FETCH LOG  (append-only, traceability for data provider calls)
# ═══════════════════════════════════════════════════════════════════════════

class PriceFetchLog(Base):
    """
    Append-only record of every external data provider call.

    Allows us to answer:
      - How many fetches are real (yfinance) vs demo (static)?
      - What's the latency per provider?
      - When was a ticker last successfully fetched?

    data_quality values:
      "live"         — fetched from yfinance successfully
      "demo_static"  — hardcoded demo value (bonds, macro)
      "stale_cache"  — returned from expired cache
      "error"        — provider call failed
    """
    __tablename__ = "price_fetch_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="yfinance")
    data_quality: Mapped[str] = mapped_column(String(32), nullable=False)
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Price returned (nullable — errors may not have a price)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_price_fetch_log_ticker", "ticker"),
        Index("ix_price_fetch_log_fetched_at", "fetched_at"),
        Index("ix_price_fetch_log_data_quality", "data_quality"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# ML RUNS  (append-only — one row per training execution)
# Étape 8 — ML Minimum Sérieux
# ═══════════════════════════════════════════════════════════════════════════

class MLRun(Base):
    """
    Training run metadata — every model training is persisted with its
    parameters, metrics, dataset reference and validation strategy.

    model_type: "random_forest" | "xgboost" | "lightgbm" | "baseline_naive"
                | "baseline_linear"
    stage:      "dev" | "staging" | "production" | "archived"
    """
    __tablename__ = "ml_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Run identifiers
    run_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_type: Mapped[str] = mapped_column(String(32), nullable=False)
    asset: Mapped[str] = mapped_column(String(32), nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    # Serialised params — the exact hyperparams used
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Dataset identification
    dataset_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dataset_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dataset_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    n_samples_train: Mapped[int | None] = mapped_column(Integer, nullable=True)
    n_samples_val: Mapped[int | None] = mapped_column(Integer, nullable=True)
    n_samples_test: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Validation strategy
    validation_method: Mapped[str] = mapped_column(
        String(32), nullable=False, default="walk_forward"
    )
    n_splits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Metrics (train / val / test)
    metrics_train: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    metrics_val: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    metrics_test: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Artifact path (relative to artifact root)
    artifact_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # MLflow integration
    mlflow_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mlflow_experiment: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Status and lifecycle
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    stage: Mapped[str] = mapped_column(String(16), nullable=False, default="dev")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    predictions: Mapped[list["MLPrediction"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_ml_runs_model_type", "model_type"),
        Index("ix_ml_runs_asset", "asset"),
        Index("ix_ml_runs_stage", "stage"),
        Index("ix_ml_runs_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<MLRun {self.run_name!r} {self.model_type} stage={self.stage}>"


# ═══════════════════════════════════════════════════════════════════════════
# ML PREDICTIONS  (append-only — every prediction logged for audit)
# Étape 8 — ML Minimum Sérieux
# ═══════════════════════════════════════════════════════════════════════════

class MLPrediction(Base):
    """
    Append-only prediction log — links each forecast to its originating run
    and allows comparison with actual outcome once observed.

    The actual_return field is NULL at prediction time and backfilled
    when the target date is reached.
    """
    __tablename__ = "ml_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ml_runs.id", ondelete="CASCADE"), nullable=False
    )
    asset: Mapped[str] = mapped_column(String(32), nullable=False)
    prediction_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    target_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    # Prediction output
    predicted_return: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_direction: Mapped[str | None] = mapped_column(String(8), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Feature snapshot hash (for reproducibility)
    features_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Actual outcome (backfilled)
    actual_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_direction: Mapped[str | None] = mapped_column(String(8), nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, server_default=func.now()
    )

    run: Mapped["MLRun"] = relationship(back_populates="predictions")

    __table_args__ = (
        Index("ix_ml_predictions_run_id", "run_id"),
        Index("ix_ml_predictions_asset", "asset"),
        Index("ix_ml_predictions_target_date", "target_date"),
        Index("ix_ml_predictions_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<MLPrediction {self.asset} pred={self.predicted_return}>"


# ═══════════════════════════════════════════════════════════════════════════
# BACKTEST RUNS  (append-only — one row per backtest execution)
# Étape 9 — Backtesting traçable
# ═══════════════════════════════════════════════════════════════════════════

class BacktestRun(Base):
    """
    Every backtest execution persisted with params, metrics, cost
    assumptions, limitations, and benchmark comparison.

    strategy: "buy_and_hold" | "equal_weight" | "momentum" | "mean_reversion"
              | "ml_signal" | custom
    level:    "exploration" | "simulation"
              — exploration: indicative only, NOT for live deployment
              — simulation: more rigorous but still with documented limits

    Limitations matrix fields track known biases explicitly.
    """
    __tablename__ = "backtest_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    bundle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    bundle_role: Mapped[str] = mapped_column(
        String(32), nullable=False, default="primary"
    )
    run_name: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    level: Mapped[str] = mapped_column(
        String(16), nullable=False, default="exploration"
    )
    # Universe
    assets: Mapped[dict] = mapped_column(JSON, nullable=False)  # list of tickers
    benchmark: Mapped[str] = mapped_column(String(32), nullable=False, default="SPY")
    # Time range
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Strategy parameters (fully serialised for reproducibility)
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    initial_capital: Mapped[float] = mapped_column(Float, nullable=False, default=100_000.0)
    # Cost assumptions — explicit honesty
    commission_bps: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    slippage_bps: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    cost_model: Mapped[str] = mapped_column(
        String(32), nullable=False, default="flat_bps"
    )
    # Performance metrics
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Benchmark metrics (buy & hold on benchmark ticker)
    benchmark_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    comparison: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Limitations matrix — explicit honesty about what's NOT modelled
    limitations: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    deployment_policy: Mapped[str | None] = mapped_column(Text, nullable=True)
    # ML run link (if strategy = ml_signal)
    ml_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ml_runs.id", ondelete="SET NULL"), nullable=True
    )
    # Status
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    n_trades: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, server_default=func.now()
    )

    # Relationships
    trades: Mapped[list["BacktestTrade"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_backtest_runs_bundle_id", "bundle_id"),
        Index("ix_backtest_runs_bundle_role", "bundle_role"),
        Index("ix_backtest_runs_strategy", "strategy"),
        Index("ix_backtest_runs_level", "level"),
        Index("ix_backtest_runs_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<BacktestRun {self.run_name!r} {self.strategy} level={self.level}>"


# ═══════════════════════════════════════════════════════════════════════════
# BACKTEST TRADES  (append-only — every trade in the simulation)
# Étape 9 — Backtesting traçable
# ═══════════════════════════════════════════════════════════════════════════

class BacktestTrade(Base):
    """
    Individual trade in a backtest run.
    Persisted for audit, P&L attribution, and reproducibility.
    """
    __tablename__ = "backtest_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False
    )
    trade_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    asset: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(4), nullable=False)  # "buy" | "sell"
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    commission: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    slippage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # Running state after trade
    portfolio_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    cash_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(128), nullable=True)

    run: Mapped["BacktestRun"] = relationship(back_populates="trades")

    __table_args__ = (
        Index("ix_backtest_trades_run_id", "run_id"),
        Index("ix_backtest_trades_asset", "asset"),
        Index("ix_backtest_trades_trade_date", "trade_date"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# PORTFOLIO CONSTRUCTION  (append-only allocation recommendations)
# ═══════════════════════════════════════════════════════════════════════════

class AllocationRun(Base):
    """
    Persisted allocation recommendation with normalized investor policy and
    explainable recommendation payload.
    """
    __tablename__ = "allocation_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    recommendation_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    objective_used: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_profile: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="completed")
    investor_policy: Mapped[dict] = mapped_column(JSON, nullable=False)
    eligibility_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    assumptions_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    risk_inputs_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    request_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    eligible_tickers: Mapped[dict] = mapped_column(JSON, nullable=False)
    recommended_assets: Mapped[dict] = mapped_column(JSON, nullable=False)
    rejected_assets: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    optimization_summary: Mapped[dict] = mapped_column(JSON, nullable=False)
    warnings: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    total_allocated_amount: Mapped[float] = mapped_column(Float, nullable=False)
    cash_reserve_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_allocation_runs_created_at", "created_at"),
        Index("ix_allocation_runs_objective_used", "objective_used"),
        Index("ix_allocation_runs_risk_profile", "risk_profile"),
    )

    def __repr__(self) -> str:
        return f"<AllocationRun {self.recommendation_id} objective={self.objective_used}>"


# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 10 — Risk Engine Governance
# ═══════════════════════════════════════════════════════════════════════════

class RiskSnapshot(Base):
    """
    Point-in-time risk metric snapshot.

    Stores governed metrics with full audit trail:
    method used, conventions applied, data source, governance level.
    """
    __tablename__ = "risk_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True
    )
    asset: Mapped[str] = mapped_column(String(32), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=__import__("datetime").timezone.utc)
    )
    data_source: Mapped[str] = mapped_column(String(64), nullable=False, default="yfinance")
    n_observations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Full risk report (all governed metrics as JSON)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Conventions snapshot at computation time
    conventions_used: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Governance summary: {calculated: N, governed: M, exploitable: K}
    governance_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_risk_snapshots_asset", "asset"),
        Index("ix_risk_snapshots_computed_at", "computed_at"),
    )

    def __repr__(self) -> str:
        return f"<RiskSnapshot asset={self.asset} computed_at={self.computed_at}>"


# ═══════════════════════════════════════════════════════════════════════════
# AUDIT EVENTS  (append-only — security audit trail)
# Étape 12 — Sécurité et Gouvernance
# ═══════════════════════════════════════════════════════════════════════════

class AuditEvent(Base):
    """
    Append-only audit trail for all security-relevant actions.

    action values:
      LOGIN, LOGOUT, LOGIN_FAILED,
      CREATE, UPDATE, DELETE,
      EXPORT, EXECUTE,
      ADMIN_ACTION
    """
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_audit_events_user_id", "user_id"),
        Index("ix_audit_events_action", "action"),
        Index("ix_audit_events_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AuditEvent {self.action} user={self.user_id}>"

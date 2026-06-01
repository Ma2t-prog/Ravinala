"""
FastAPI application — app factory.

Étape 3 — Structuration backend
─────────────────────────────────
This file is now an app factory only.
All route logic lives in app/routes/:
  market.py   — /api/v1/snapshot, indices, bonds, fx-pairs, commodities, macro, refresh
  export.py   — /api/v1/export/excel, /pdf
  generate.py — /api/v1/generate/termsheet, scenariobook, risksummary

Shared services:
  services/snapshot_service.py — full-snapshot builder (used by market + export)
  services/cache.py            — Redis / in-memory cache
  services/data_fetcher.py     — yfinance + static demo fetchers
  db/base.py                   — async SQLAlchemy engine (Étape 2)
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Persistence layer (Étape 2) — graceful-NO-OP when DATABASE_URL not set
from app.db.base import close_db, database_health_snapshot, init_db

# App models
from app.models import HealthCheckResponse

# Route modules (Étape 3)
from app.routes import export_router, generate_router, market_router, events_router, ml_router, backtest_router, risk_router, jobs_router, monitoring_router, auth_router, users_router, universe_router, portfolio_router, allocator_router, analysis_router, agents_router

# Shared services
from app.services.cache import get_cache
from app.services.snapshot_service import get_full_snapshot_async

# Étape 4 — API contracts
import uuid
from app.middleware.headers import ApiHeadersMiddleware
from app.schemas.envelope import ApiError

# Étape 6 — Observabilité
from app.middleware.tracing import TracingMiddleware
from app.core.config import get_settings
from app.core.executor import clear_shared_executor, set_shared_executor

# Étape 11 — Structured logging
from app.observability.logging_config import setup_logging, trace_id_var  # noqa: E402
setup_logging()
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# LIFESPAN
# ═══════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown handlers."""
    logger.info("🚀 Starting Ravinala Backend API...")
    shared_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="backend-shared")
    app.state.executor = shared_executor
    set_shared_executor(shared_executor)

    # Étape 2 — persistence (no-op if DATABASE_URL not set)
    db_ok = await init_db()
    logger.info(
        f"💾 Database: {'connected' if db_ok else 'inactive (set DATABASE_URL to enable)'}"
    )

    # Warm up cache. For local interview demos, skip Celery so the API can start
    # even when Redis is not running.
    if os.getenv("RAVINALA_SKIP_CELERY_WARMUP", "0") == "1":
        logger.info("Cache warm-up skipped by RAVINALA_SKIP_CELERY_WARMUP")
    else:
        try:
            from app.workers.tasks.fetch_task import refresh_snapshot
            refresh_snapshot.delay()
            logger.info("♻️  Cache warm-up dispatched to Celery worker")
        except Exception as exc:
            logger.warning(f"⚠️  Celery unavailable ({exc}), warming cache inline...")
            try:
                await get_full_snapshot_async()
                logger.info("✅ Cache warmed (inline fallback)")
            except Exception as exc2:
                logger.warning(f"⚠️  Cache warm-up failed: {exc2}")

    yield

    logger.info("🛑 Shutting down...")
    shared_executor.shutdown(wait=True)
    clear_shared_executor()
    await close_db()


# ═══════════════════════════════════════════════════════════════════════════
# APP FACTORY
# ═══════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Ravinala Backend API",
    description=(
        "Market data API for Ravinala dashboard. "
        "Indices/FX/Commodities: live via yfinance. "
        "Bonds/Macro: static demo values (no real-time provider configured). "
        "See data_quality field in each response."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ApiHeadersMiddleware must be outermost — Starlette wraps LIFO so register it first
app.add_middleware(ApiHeadersMiddleware)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# TracingMiddleware outermost: sees fully-decorated response (X-Data-Quality, X-Cache-Hit)
app.add_middleware(TracingMiddleware)

# Register routers
app.include_router(market_router)
app.include_router(export_router)
app.include_router(generate_router)
app.include_router(events_router)
app.include_router(ml_router)
app.include_router(backtest_router)
app.include_router(risk_router)
app.include_router(jobs_router)
app.include_router(monitoring_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(universe_router)
app.include_router(portfolio_router)
app.include_router(allocator_router)
app.include_router(analysis_router)
if agents_router is not None:
    app.include_router(agents_router)


# ═══════════════════════════════════════════════════════════════════════════
# UTILITY ENDPOINTS  (health, root)
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/health", response_model=HealthCheckResponse, tags=["system"])
async def health_check() -> HealthCheckResponse:
    """Health check — reports Redis and database connectivity."""
    cache = get_cache()
    db_health = await database_health_snapshot()
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        redis_connected=cache.health(),
        data_service_ok=True,
        db_status=db_health["status"],
    )


@app.get("/", tags=["system"])
async def root() -> dict:
    """API index — lists available endpoint groups."""
    return {
        "name": "Ravinala Backend API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "snapshot": "/api/v1/snapshot",
            "indices": "/api/v1/indices",
            "bonds": "/api/v1/bonds",
            "fx": "/api/v1/fx-pairs",
            "commodities": "/api/v1/commodities",
            "macro": "/api/v1/macro",
            "refresh": "/api/v1/refresh",
            "export_excel": "/api/v1/export/excel",
            "export_pdf": "/api/v1/export/pdf",
            "generate_termsheet": "/api/v1/generate/termsheet",
            "generate_scenariobook": "/api/v1/generate/scenariobook",
            "generate_risksummary": "/api/v1/generate/risksummary",
            "allocator_eligible_universe": "/api/v1/allocator/eligible-universe",
            "allocator_assumptions": "/api/v1/allocator/assumptions",
            "allocator_recommend": "/api/v1/allocator/recommend",
            "allocator_runs": "/api/v1/allocator/runs",
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# ERROR HANDLERS
# ═══════════════════════════════════════════════════════════════════════════

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiError(
            error=str(exc.detail),
            request_id=request_id,
        ).model_dump(mode="json"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1" if settings.security_level == 0 else "0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENVIRONMENT", "development") == "development",
        log_level=os.getenv("LOG_LEVEL", "info"),
    )

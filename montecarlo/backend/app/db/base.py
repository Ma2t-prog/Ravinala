"""
db/base.py — Async SQLAlchemy engine + session factory.

Étape 2 — Persistance minimale
──────────────────────────────
Graceful degradation: if DATABASE_URL is not set, the backend starts
without a database connection. All DB-dependent features return gracefully.

To activate:
  Set DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/ravinala
  in .env or environment before starting the backend.
"""

import logging
import os
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# DECLARATIVE BASE
# ═══════════════════════════════════════════════════════════════════════════

class Base(DeclarativeBase):
    pass


# ═══════════════════════════════════════════════════════════════════════════
# ENGINE STATE  (module-level singletons, None until init_db() is called)
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def engine_status() -> str:
    """Return a human-readable status string for the health endpoint."""
    if _engine is None:
        return "not_configured"
    return "connected"


async def database_health_snapshot() -> dict[str, str]:
    """
    Return the live database health state.

    Distinguishes between:
      - not_configured: no engine/session factory available
      - connected: probe query succeeded
      - unhealthy: engine exists but the probe failed
    """
    if _engine is None or _session_factory is None:
        return {"status": "not_configured", "detail": "not_configured"}

    try:
        async with _engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "connected", "detail": "connected"}
    except Exception as exc:
        logger.error("❌ Database health probe failed: %s", exc)
        return {"status": "unhealthy", "detail": str(exc)}


# ═══════════════════════════════════════════════════════════════════════════
# INIT
# ═══════════════════════════════════════════════════════════════════════════

async def init_db() -> bool:
    """
    Initialise the async engine and create all tables.

    Returns True if a connection was established, False if DATABASE_URL
    is not set or the connection failed (non-fatal — backend remains usable).
    """
    global _engine, _session_factory

    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        logger.info(
            "DATABASE_URL not set — persistence layer inactive. "
            "Set DATABASE_URL=postgresql+asyncpg://... to enable."
        )
        return False

    # Normalise URL: support bare postgres:// scheme from some PaaS providers
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    try:
        _engine = create_async_engine(
            database_url,
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
        _session_factory = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Create all tables if they don't exist yet
        # (Alembic handles schema migrations; create_all is our safety net for dev)
        from app.db.models import Base as _B  # noqa: F401 — ensure models are imported

        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("✅ Database connected and tables created/verified.")
        return True

    except Exception as exc:
        logger.error(f"❌ Database init failed: {exc}. Backend will run without persistence.")
        _engine = None
        _session_factory = None
        return False


async def close_db() -> None:
    """Dispose the engine pool on shutdown."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("Database connection pool closed.")


def async_session() -> async_sessionmaker[AsyncSession] | None:
    """Return the session factory (or None if DB is inactive)."""
    return _session_factory


# ═══════════════════════════════════════════════════════════════════════════
# SESSION DEPENDENCY (FastAPI Depends)
# ═══════════════════════════════════════════════════════════════════════════

async def get_session() -> AsyncGenerator[Optional[AsyncSession], None]:
    """
    FastAPI dependency that yields an AsyncSession, or None if DB is inactive.

    Usage:
        @router.get("/example")
        async def example(db: Optional[AsyncSession] = Depends(get_session)):
            if db is None:
                return {"error": "persistence_not_configured"}
            ...
    """
    if _session_factory is None:
        yield None
        return
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

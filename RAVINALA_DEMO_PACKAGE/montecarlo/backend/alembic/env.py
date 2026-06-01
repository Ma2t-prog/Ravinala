"""
alembic/env.py — Async-compatible Alembic environment.

Reads DATABASE_URL from environment / .env file.
Uses SQLAlchemy async engine for migrations via run_sync pattern.
"""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

# Load .env so DATABASE_URL is available when running alembic CLI
load_dotenv()

# Alembic Config object
config = context.config

# Setup Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all ORM models so Alembic can detect changes
# The order matters: base must be imported before models
from app.db.base import Base  # noqa: E402
import app.db.models  # noqa: E402, F401 — registers all tables on Base.metadata

target_metadata = Base.metadata


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise ValueError(
            "DATABASE_URL is not set. "
            "Set it in .env: postgresql+asyncpg://user:pass@localhost:5432/ravinala"
        )
    # Normalise scheme
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode — generate SQL without a live connection.
    Useful for reviewing migration SQL before applying.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in 'online' mode using an async engine.
    Alembic requires a sync Connection, so we use run_sync.
    """
    connectable = create_async_engine(
        get_database_url(),
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

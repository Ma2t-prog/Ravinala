"""
services/event_log.py — Fire-and-forget API event persistence.

Étape 6 — Observabilité
────────────────────────
Writes one row to `api_events` for every handled API request.
Silently no-ops when DATABASE_URL is not configured so the backend
remains fully operational without a database.

This module is imported lazily (inside TracingMiddleware.dispatch) so
circular-import risks are avoided during application bootstrap.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def record_request_event(
    *,
    endpoint: str,
    method: str,
    status_code: int,
    duration_ms: int,
    demo_data: bool = False,
    cache_hit: bool = False,
) -> None:
    """
    Persist one ``ApiEvent`` row.

    Safe to call as an ``asyncio.create_task`` — all exceptions are caught
    and logged at DEBUG level to avoid polluting the application log.
    """
    # Deferred import so the module is importable before init_db() is called
    from app.db import base as _db  # noqa: PLC0415

    if _db._session_factory is None:  # type: ignore[attr-defined]
        return

    try:
        from app.db.models import ApiEvent  # noqa: PLC0415

        async with _db._session_factory() as session:  # type: ignore[attr-defined]
            session.add(
                ApiEvent(
                    endpoint=endpoint[:256],
                    method=method[:8],
                    status_code=status_code,
                    duration_ms=duration_ms,
                    demo_data=demo_data,
                    cache_hit=cache_hit,
                )
            )
            await session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.debug("event_log: write failed (non-fatal): %s", exc)

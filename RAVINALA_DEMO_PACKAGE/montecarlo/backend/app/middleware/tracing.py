"""
middleware/tracing.py — Request tracing middleware.

Étape 6 — Observabilité
────────────────────────
For every API request (skipping health / docs / static paths), records:
  - endpoint path, HTTP method, response status code
  - wall-clock duration in milliseconds
  - demo_data flag  (derived from X-Data-Quality header set by ApiHeadersMiddleware)
  - cache_hit flag  (derived from X-Cache-Hit header set by ApiHeadersMiddleware)

The DB write is fire-and-forget via asyncio.create_task so it never
blocks the response path.  A missing database is silently tolerated.

Middleware registration order in main.py (LIFO, last = outermost):
  app.add_middleware(ApiHeadersMiddleware)   # 1st registered — inner
  app.add_middleware(CORSMiddleware, ...)    # 2nd registered
  app.add_middleware(TracingMiddleware)      # 3rd registered — outermost

TracingMiddleware being outermost means it captures the fully-decorated
response with X-Data-Quality / X-Cache-Hit already set by ApiHeadersMiddleware.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.observability.logging_config import trace_id_var
from app.observability.metrics import get_metrics

logger = logging.getLogger(__name__)

# Paths that add no analytical value to the audit log
_SKIP_PATHS: frozenset[str] = frozenset(
    [
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/docs/oauth2-redirect",
        "/favicon.ico",
    ]
)


class TracingMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware that captures every API request and persists it as
    an ``ApiEvent`` row via the :mod:`app.services.event_log` service.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        # Étape 11 — propagate trace_id for structured logging
        request_id = request.headers.get(
            "X-Request-Id", ""
        ) or getattr(request.state, "request_id", "")
        if request_id:
            trace_id_var.set(request_id)

        start = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)

        # Read quality / cache headers written by ApiHeadersMiddleware (inner layer)
        data_quality = response.headers.get("X-Data-Quality", "")
        demo_data = data_quality == "demo_static"
        cache_hit = response.headers.get("X-Cache-Hit", "false").lower() == "true"

        # Étape 11 — record in-memory metrics (never blocks)
        try:
            get_metrics().record_request(
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
        except Exception:  # pragma: no cover — metrics are best-effort
            pass

        # Fire-and-forget — never await, never block
        asyncio.create_task(
            _write_event(
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                duration_ms=duration_ms,
                demo_data=demo_data,
                cache_hit=cache_hit,
            )
        )

        return response


async def _write_event(**kwargs: object) -> None:
    """Thin wrapper so the import stays deferred until task execution time."""
    from app.services.event_log import record_request_event  # noqa: PLC0415

    await record_request_event(**kwargs)  # type: ignore[arg-type]

"""
middleware/headers.py — Response headers middleware.

Étape 4 — Contrats API
────────────────────────
Adds to every response:
  X-API-Version  : API version string (from app state or constant)
  X-Request-Id   : UUID per request — echoed back for traceability
  X-Data-Quality : data_quality value extracted from JSON response body
                   ("live" | "demo_static" | "stale_cache" | "error" | "mixed")

The X-Data-Quality header propagates the Étape 1 honesty flags from
data_fetcher.py to every HTTP response so frontend/monitoring can inspect
data quality without parsing body JSON.

Implementation note:
  For non-streaming responses, we buffer the response body, parse JSON,
  extract the top-level `data_quality` field, and rebuffer. For streaming
  responses (PDF generation), we skip body inspection and set
  X-Data-Quality: n/a.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

logger = logging.getLogger(__name__)

API_VERSION = "1.0.0"


class ApiHeadersMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware that enriches every response with traceability headers.

    Headers added:
      X-API-Version  — constant version string
      X-Request-Id   — UUID generated per request (or echoed if provided by client)
      X-Data-Quality — quality level of the data in the response body

    The request_id is also stored on request.state.request_id so route
    handlers can include it in error responses.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Generate or echo request ID
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.request_id = request_id

        response: Response = await call_next(request)

        # Always set version + request ID
        response.headers["X-API-Version"] = API_VERSION
        response.headers["X-Request-Id"] = request_id

        # Skip body inspection for streaming responses (PDF, Excel downloads)
        if isinstance(response, StreamingResponse):
            response.headers["X-Data-Quality"] = "n/a"
            return response

        # For regular JSON responses: buffer body, extract data_quality
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            body_bytes = b""
            async for chunk in response.body_iterator:  # type: ignore[attr-defined]
                body_bytes += chunk if isinstance(chunk, bytes) else chunk.encode()

            data_quality = "unknown"
            try:
                payload = json.loads(body_bytes)
                # Support both direct response dict and ApiResponse envelope
                dq = payload.get("data_quality") or payload.get("data", {}).get(
                    "data_quality"
                )
                if dq:
                    data_quality = dq
                # Also expose cache_hit for TracingMiddleware (Étape 6)
                cache_hit = payload.get("cache_hit") or payload.get("data", {}).get(
                    "cache_hit", False
                )
                response.headers["X-Cache-Hit"] = "true" if cache_hit else "false"
            except Exception:
                pass  # non-JSON body or parse error — leave as "unknown"

            response.headers["X-Data-Quality"] = data_quality

            # Rebuild response with same status/headers but buffered body
            return Response(
                content=body_bytes,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        return response

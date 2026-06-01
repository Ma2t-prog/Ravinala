"""
schemas/envelope.py — Typed API response envelope.

Étape 4 — Contrats API
────────────────────────
Every API response is wrapped in ApiResponse[T], which carries:
  - data         : the typed payload
  - data_quality : "live" | "demo_static" | "stale_cache" | "error"
  - cache_hit    : whether Redis / in-memory cache was used
  - request_id   : UUID, also sent as X-Request-Id response header
  - api_version  : server version string, also sent as X-API-Version header
  - generated_at : UTC timestamp of this response

DataQuality propagates from data_fetcher.py honesty flags (Étape 1):
  - fetch_bonds()  → data_quality: "demo_static"
  - fetch_macro()  → data_quality: "demo_static"
  - fetch_indices() → data_quality: "live" (yfinance)
  - fetch_fx_pairs() → data_quality: "live" (yfinance)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

# ─── DataQuality literal ─────────────────────────────────────────────────────

DataQuality = Literal["live", "demo_static", "stale_cache", "error", "mixed"]
"""
data_quality values:
  live         — real-time data from a live provider (yfinance)
  demo_static  — hardcoded / seeded demo values; not real market data
  stale_cache  — served from an expired cache; may be outdated
  error        — provider call failed; data is a fallback or empty
  mixed        — response contains both live and demo sections (e.g. snapshot)
"""


# ─── Response envelope ────────────────────────────────────────────────────────

class ApiResponse(BaseModel, Generic[T]):
    """
    Standard API response wrapper for all market data endpoints.

    All endpoints return this envelope to ensure:
    - Consistent shape across all routes (client can always access .data)
    - Transparent data quality labelling (Étape 1 honesty)
    - Request traceability via request_id
    - Cache transparency via cache_hit

    Usage in routes:
        @router.get("/indices", response_model=ApiResponse[IndicesSnapshotModel])
        async def get_indices(...) -> ApiResponse[IndicesSnapshotModel]:
            result = fetcher.fetch_indices()
            return ApiResponse(
                data=result,
                data_quality="live",
                cache_hit=False,
            )
    """

    data: T = Field(..., description="Typed response payload")
    data_quality: DataQuality = Field(
        ...,
        description=(
            "live = real provider data; "
            "demo_static = hardcoded illustrative values; "
            "stale_cache = from expired cache; "
            "error = provider failed; "
            "mixed = combination of live and demo sections"
        ),
        examples=["live", "demo_static"],
    )
    cache_hit: bool = Field(
        default=False,
        description="True when data was served from Redis / in-memory cache",
    )
    using_fallback: bool = Field(
        default=False,
        description=(
            "True when the response was produced by a fallback path "
            "(e.g. inline cache warm-up instead of Celery, demo values instead of live provider). "
            "S6.3 — fallback visibility."
        ),
    )
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="UUID for request tracing. Also sent as X-Request-Id header.",
        examples=["a1b2c3d4-..."],
    )
    api_version: str = Field(
        default="1.0.0",
        description="Backend API version. Also sent as X-API-Version header.",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of this response.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "data": {"bonds": [], "data_quality": "demo_static"},
                "data_quality": "demo_static",
                "cache_hit": True,
                "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "api_version": "1.0.0",
                "generated_at": "2026-03-22T10:00:00Z",
            }
        }
    }


# ─── Error envelope ───────────────────────────────────────────────────────────

class ApiError(BaseModel):
    """
    Standard error response returned by the exception handler.
    Shape mirrors ApiResponse but carries error detail instead of data.
    """

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional detail or stack trace excerpt")
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="UUID for request tracing.",
    )
    api_version: str = Field(default="1.0.0")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "error": "Provider timeout",
                "detail": "yfinance did not respond within 10s",
                "request_id": "a1b2c3d4-...",
                "api_version": "1.0.0",
                "generated_at": "2026-03-22T10:00:00Z",
            }
        }
    }

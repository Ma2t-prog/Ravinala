"""
Typed observability read models for event-log endpoints.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class EndpointStat(BaseModel):
    endpoint: str
    total_requests: int
    demo_requests: int
    live_requests: int
    cache_hits: int
    avg_duration_ms: Optional[float]
    p95_duration_ms: Optional[float]


class EventSummaryResponse(BaseModel):
    total_requests: int
    demo_ratio: float
    cache_hit_ratio: float
    avg_duration_ms: Optional[float]
    endpoints: list[EndpointStat]
    generated_at: str

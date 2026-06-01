from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.routes import events
from app.schemas.events import EndpointStat, EventSummaryResponse


def test_events_route_no_longer_owns_sql_aggregation() -> None:
    source = (BACKEND_DIR / "app" / "routes" / "events.py").read_text(encoding="utf-8")
    assert "from app.services.event_read_service import build_event_summary" in source
    assert "from app.db.models import ApiEvent" not in source
    assert "select(" not in source
    assert "func.count(" not in source


@pytest.mark.asyncio
async def test_events_route_delegates_to_service_with_typed_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def _build_summary(db, hours: int) -> EventSummaryResponse:
        captured["db"] = db
        captured["hours"] = hours
        return EventSummaryResponse(
            total_requests=3,
            demo_ratio=0.3333,
            cache_hit_ratio=0.6667,
            avg_duration_ms=11.0,
            endpoints=[
                EndpointStat(
                    endpoint="/api/v1/foo",
                    total_requests=3,
                    demo_requests=1,
                    live_requests=2,
                    cache_hits=2,
                    avg_duration_ms=11.0,
                    p95_duration_ms=None,
                )
            ],
            generated_at="2026-03-24T00:00:00+00:00",
        )

    db = object()
    monkeypatch.setattr(events, "build_event_summary", _build_summary)

    result = await events.get_events_summary(hours=12, db=db)

    assert isinstance(result, EventSummaryResponse)
    assert result.total_requests == 3
    assert captured == {"db": db, "hours": 12}

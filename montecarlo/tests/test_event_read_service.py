from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import event_read_service


@dataclass
class _Event:
    endpoint: str
    created_at: datetime
    demo_data: bool
    cache_hit: bool
    duration_ms: int


class _FakeExecuteResult:
    def __init__(self, rows: list[SimpleNamespace]):
        self._rows = rows

    def all(self) -> list[SimpleNamespace]:
        return list(self._rows)


class _FakeAsyncSession:
    def __init__(self, events: list[_Event]):
        self._events = list(events)

    async def execute(self, query):
        cutoff = None
        for criterion in getattr(query, "_where_criteria", ()):
            column = getattr(getattr(criterion, "left", None), "name", None)
            value = getattr(getattr(criterion, "right", None), "value", None)
            if column == "created_at":
                cutoff = value

        filtered = [
            event for event in self._events if cutoff is None or event.created_at >= cutoff
        ]

        grouped: dict[str, list[_Event]] = {}
        for event in filtered:
            grouped.setdefault(event.endpoint, []).append(event)

        rows = []
        for endpoint, bucket in grouped.items():
            rows.append(
                SimpleNamespace(
                    endpoint=endpoint,
                    total=len(bucket),
                    demo_cnt=sum(1 for event in bucket if event.demo_data),
                    cache_cnt=sum(1 for event in bucket if event.cache_hit),
                    avg_ms=sum(event.duration_ms for event in bucket) / len(bucket),
                )
            )

        rows.sort(key=lambda row: row.total, reverse=True)
        return _FakeExecuteResult(rows)


@pytest.mark.asyncio
async def test_event_read_service_applies_hours_window_and_rolls_up_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 3, 24, 12, 0, tzinfo=timezone.utc)
    session = _FakeAsyncSession(
        [
            _Event(
                endpoint="/api/v1/risk/report",
                created_at=now - timedelta(hours=2),
                demo_data=False,
                cache_hit=True,
                duration_ms=10,
            ),
            _Event(
                endpoint="/api/v1/risk/report",
                created_at=now - timedelta(hours=1),
                demo_data=True,
                cache_hit=False,
                duration_ms=20,
            ),
            _Event(
                endpoint="/api/v1/backtest/run",
                created_at=now - timedelta(hours=3),
                demo_data=False,
                cache_hit=True,
                duration_ms=40,
            ),
            _Event(
                endpoint="/api/v1/backtest/run",
                created_at=now - timedelta(hours=30),
                demo_data=True,
                cache_hit=False,
                duration_ms=999,
            ),
        ]
    )

    monkeypatch.setattr(event_read_service, "_utcnow", lambda: now)

    result = await event_read_service.build_event_summary(session, hours=24)

    assert result.total_requests == 3
    assert result.demo_ratio == pytest.approx(1 / 3, rel=0, abs=1e-4)
    assert result.cache_hit_ratio == pytest.approx(2 / 3, rel=0, abs=1e-4)
    assert result.avg_duration_ms == pytest.approx(23.3, rel=0, abs=0.1)
    assert [endpoint.endpoint for endpoint in result.endpoints] == [
        "/api/v1/risk/report",
        "/api/v1/backtest/run",
    ]
    assert result.endpoints[0].total_requests == 2
    assert result.endpoints[0].demo_requests == 1
    assert result.endpoints[0].cache_hits == 1
    assert result.generated_at == now.isoformat()

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import cache as cache_service
from app.services import snapshot_service


class _FakeCache:
    def __init__(self, payload: dict | None = None) -> None:
        self.store: dict[str, dict] = {}
        if payload is not None:
            self.store["snapshot:full"] = payload

    def get(self, key: str):
        return self.store.get(key)

    def set(self, key: str, value: dict, section: str = "snapshot") -> bool:
        self.store[key] = value
        return True


class _FetcherStub:
    def fetch_indices(self) -> dict:
        return {"indices": ["spx"]}

    def fetch_bonds(self) -> dict:
        return {"bonds": ["ust10y"]}

    def fetch_fx_pairs(self) -> dict:
        return {"fx": ["eurusd"]}

    def fetch_commodities(self) -> dict:
        return {"commodities": ["gold"]}

    def fetch_macro(self) -> dict:
        return {"macro": ["cpi"]}


def test_in_memory_cache_returns_isolated_copies() -> None:
    manager = cache_service.CacheManager.__new__(cache_service.CacheManager)
    manager.redis = None
    manager._memory_cache = {}

    original = {"payload": {"values": [1]}}
    assert manager.set("demo:key", original, section="snapshot") is True

    original["payload"]["values"].append(2)
    cached = manager.get("demo:key")
    assert cached["payload"]["values"] == [1]

    cached["payload"]["values"].append(3)
    assert manager.get("demo:key")["payload"]["values"] == [1]


def test_in_memory_clear_section_removes_only_matching_prefix() -> None:
    manager = cache_service.CacheManager.__new__(cache_service.CacheManager)
    manager.redis = None
    manager._memory_cache = {
        "snapshot:full": ({"x": 1}, cache_service._utcnow()),
        "snapshot:mini": ({"x": 2}, cache_service._utcnow()),
        "macro:cpi": ({"x": 3}, cache_service._utcnow()),
    }

    cleared = manager.clear_section("snapshot")

    assert cleared == 2
    assert "snapshot:full" not in manager._memory_cache
    assert "snapshot:mini" not in manager._memory_cache
    assert "macro:cpi" in manager._memory_cache


def test_cache_module_does_not_require_top_level_redis_import() -> None:
    source = (BACKEND_DIR / "app" / "services" / "cache.py").read_text(encoding="utf-8")

    assert "import redis" not in source.splitlines()[:10]


@pytest.mark.asyncio
async def test_snapshot_service_marks_cache_hits_without_mutating_cached_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    canonical = {
        "indices": {"americas": []},
        "bonds": {"bonds": []},
        "fx": {"usd_base": []},
        "commodities": {"metals": []},
        "macro": {"indicators": []},
        "timestamp": "2026-03-24T00:00:00+00:00",
    }
    cache = _FakeCache(payload=canonical)

    monkeypatch.setattr(snapshot_service, "get_cache", lambda: cache)

    payload = await snapshot_service.get_full_snapshot_async()

    assert payload["cache_hit"] is True
    assert "cache_hit" not in cache.store["snapshot:full"]


@pytest.mark.asyncio
async def test_snapshot_service_cache_miss_caches_canonical_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = _FakeCache()

    monkeypatch.setattr(snapshot_service, "get_cache", lambda: cache)
    monkeypatch.setattr(snapshot_service, "get_data_fetcher", lambda: _FetcherStub())
    monkeypatch.setattr(snapshot_service, "_utcnow_iso", lambda: "2026-03-24T00:00:00+00:00")

    payload = await snapshot_service.get_full_snapshot_async()

    assert payload["cache_hit"] is False
    assert payload["timestamp"] == "2026-03-24T00:00:00+00:00"
    assert cache.store["snapshot:full"]["timestamp"] == "2026-03-24T00:00:00+00:00"
    assert "cache_hit" not in cache.store["snapshot:full"]

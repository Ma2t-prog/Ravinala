from __future__ import annotations

import copy
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models import (  # noqa: E402
    BondsSnapshotModel,
    CacheRefreshResponseModel,
    CommoditiesSnapshotModel,
    FXSnapshotModel,
    IndicesSnapshotModel,
    MacroSnapshotModel,
    SnapshotResponseModel,
)
from app.routes import market  # noqa: E402


TS = "2026-03-23T12:00:00Z"

SAMPLE_INDICES = {
    "americas": [
        {
            "symbol": "^GSPC",
            "name": "S&P 500",
            "region": "Americas",
            "price": 5200.5,
            "change": {
                "absolute": 12.5,
                "percent": 0.24,
                "direction": "up",
                "color": "green",
            },
            "timestamp": TS,
            "is_stale": False,
            "data_source": "yfinance",
        }
    ],
    "europe": [],
    "asia_pacific": [],
    "middle_east_other": [],
    "last_updated": TS,
    "cache_age_seconds": 0,
}

SAMPLE_BONDS = {
    "bonds": [
        {
            "country": "USA",
            "country_code": "US",
            "yield_2y": 4.12,
            "yield_5y": 4.15,
            "yield_10y": 4.22,
            "spread_vs_bund_bp": 245.0,
            "curve_slope_percent": 0.10,
            "direction": "up",
            "last_updated": TS,
        }
    ],
    "benchmark_country": "Germany",
    "last_updated": TS,
    "cache_age_seconds": 0,
    "data_quality": "demo_static",
    "data_quality_note": "Bond yields are hardcoded demo values, not live market data.",
}

SAMPLE_FX = {
    "usd_base": [
        {
            "pair": "EUR/USD",
            "bid": 1.0799,
            "ask": 1.0801,
            "mid_price": 1.08,
            "change_percent": 0.12,
            "volatility_percent": 0.5,
            "last_updated": TS,
        }
    ],
    "crosses": [],
    "last_updated": TS,
    "cache_age_seconds": 0,
}

SAMPLE_COMMODITIES = {
    "metals": [
        {
            "symbol": "GC=F",
            "name": "Gold",
            "category": "Metals",
            "price": 2100.0,
            "unit": "USD",
            "change_percent": 0.3,
            "timestamp": TS,
        }
    ],
    "energy": [],
    "agriculture": [],
    "crypto": [],
    "last_updated": TS,
    "cache_age_seconds": 0,
}

SAMPLE_MACRO = {
    "indicators": [
        {
            "country": "USA",
            "indicator": "CPI YoY",
            "latest_value": 3.4,
            "unit": "%",
            "forecast_value": 3.2,
            "previous_value": 3.5,
            "release_date": TS,
            "source": "BLS",
            "sentiment": "negative",
        }
    ],
    "last_updated": TS,
    "cache_age_seconds": 0,
    "data_quality": "demo_static",
    "data_quality_note": "Macro indicators are hardcoded demo values, not live releases.",
}

SAMPLE_SNAPSHOT = {
    "indices": SAMPLE_INDICES,
    "bonds": SAMPLE_BONDS,
    "fx": SAMPLE_FX,
    "commodities": SAMPLE_COMMODITIES,
    "macro": SAMPLE_MACRO,
    "timestamp": TS,
    "cache_hit": False,
}


class _CacheStub:
    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    def get(self, key: str):
        value = self._store.get(key)
        return copy.deepcopy(value) if value is not None else None

    def set(self, key: str, value: dict, section: str | None = None) -> None:
        self._store[key] = copy.deepcopy(value)

    def get_age(self, key: str) -> int:
        return 5

    def clear_section(self, section: str) -> None:
        prefix = f"{section}:"
        self._store = {k: v for k, v in self._store.items() if not k.startswith(prefix)}


class _FetcherStub:
    def fetch_indices(self, limit: int = 30) -> dict:
        return copy.deepcopy(SAMPLE_INDICES)

    def fetch_bonds(self) -> dict:
        return copy.deepcopy(SAMPLE_BONDS)

    def fetch_fx_pairs(self) -> dict:
        return copy.deepcopy(SAMPLE_FX)

    def fetch_commodities(self) -> dict:
        return copy.deepcopy(SAMPLE_COMMODITIES)

    def fetch_macro(self) -> dict:
        return copy.deepcopy(SAMPLE_MACRO)


def _client(monkeypatch) -> TestClient:
    cache = _CacheStub()

    async def _snapshot() -> dict:
        return copy.deepcopy(SAMPLE_SNAPSHOT)

    async def _indices(limit: int = 30) -> dict:
        return copy.deepcopy(SAMPLE_INDICES)

    async def _bonds() -> dict:
        return copy.deepcopy(SAMPLE_BONDS)

    async def _fx() -> dict:
        return copy.deepcopy(SAMPLE_FX)

    async def _commodities() -> dict:
        return copy.deepcopy(SAMPLE_COMMODITIES)

    async def _macro() -> dict:
        return copy.deepcopy(SAMPLE_MACRO)

    monkeypatch.setattr(market, "get_cache", lambda: cache)
    monkeypatch.setattr(market, "get_full_snapshot_async", _snapshot)
    monkeypatch.setattr(market, "get_indices_async", _indices)
    monkeypatch.setattr(market, "get_bonds_async", _bonds)
    monkeypatch.setattr(market, "get_fx_async", _fx)
    monkeypatch.setattr(market, "get_commodities_async", _commodities)
    monkeypatch.setattr(market, "get_macro_async", _macro)

    app = FastAPI()
    app.include_router(market.router)
    return TestClient(app)


def test_market_endpoints_contracts(monkeypatch) -> None:
    client = _client(monkeypatch)

    indices = client.get("/api/v1/indices").json()
    bonds = client.get("/api/v1/bonds").json()
    fx = client.get("/api/v1/fx-pairs").json()
    commodities = client.get("/api/v1/commodities").json()
    macro = client.get("/api/v1/macro").json()
    snapshot = client.get("/api/v1/snapshot").json()
    refresh = client.post("/api/v1/refresh", params={"section": "indices"}).json()

    assert IndicesSnapshotModel(**indices).americas[0].symbol == "^GSPC"
    assert BondsSnapshotModel(**bonds).data_quality == "demo_static"
    assert FXSnapshotModel(**fx).usd_base[0].pair == "EUR/USD"
    assert CommoditiesSnapshotModel(**commodities).metals[0].symbol == "GC=F"
    assert MacroSnapshotModel(**macro).data_quality_note is not None
    assert SnapshotResponseModel(**snapshot).cache_hit is False
    assert CacheRefreshResponseModel(**refresh).section == "indices"


def test_snapshot_sections_filter_keeps_partial_contract(monkeypatch) -> None:
    client = _client(monkeypatch)
    payload = client.get("/api/v1/snapshot", params={"sections": "indices,bonds"}).json()
    snapshot = SnapshotResponseModel(**payload)

    assert snapshot.indices is not None
    assert snapshot.bonds is not None
    assert snapshot.fx is None
    assert snapshot.commodities is None
    assert snapshot.macro is None
    assert snapshot.cache_hit is False


def test_refresh_all_contract(monkeypatch) -> None:
    client = _client(monkeypatch)
    payload = client.post("/api/v1/refresh").json()
    refresh = CacheRefreshResponseModel(**payload)

    assert refresh.status == "refreshed"
    assert refresh.section == "all"

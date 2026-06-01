from __future__ import annotations

import copy
import sys
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.risk.conventions import CORRECTION_PLAN, CURRENT_INCOHERENCES, GOVERNANCE_LEVELS
from app.risk.conventions import METRIC_SPECS
from app.routes import risk
from app.schemas.risk_api import (
    GovernanceLevelInfo,
    GovernanceLevelsCatalog,
    RiskIncoherencesResponse,
    RiskMetricSpec,
    RiskMetricsCatalog,
    RiskSnapshotRecord,
)


TS = "2026-03-23T12:00:00Z"

SAMPLE_SNAPSHOT = {
    "snapshot_id": "snap_001",
    "asset": "AAPL",
    "computed_at": TS,
    "data_source": "yfinance",
    "n_observations": 252,
    "metrics": {
        "var_historical": {
            "value": -0.034,
            "governance_level": "exploitable",
            "confidence": 0.95,
        }
    },
    "governance_summary": {
        "level": "governed",
        "usable_for_decisions": True,
    },
    "conventions_used": {
        "risk_free_rate": 0.05,
        "trading_days_per_year": 252,
    },
}


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(risk.router)
    return app


def _route(path: str, method: str = "GET") -> APIRoute:
    route = next(
        r
        for r in _app().routes
        if isinstance(r, APIRoute) and r.path == path and method in r.methods
    )
    return route


def _client(monkeypatch, snapshots: list[dict[str, object]] | None = None) -> TestClient:
    if snapshots is not None:
        async def _list_snapshots_with_fallback(**kwargs):
            return [RiskSnapshotRecord.model_validate(snapshot) for snapshot in copy.deepcopy(snapshots)]

        monkeypatch.setattr(risk, "list_risk_snapshots_with_fallback", _list_snapshots_with_fallback)
    app = _app()
    return TestClient(app)


def test_risk_contract_response_models_are_explicit() -> None:
    contracts = {
        "/api/v1/risk/metrics": RiskMetricsCatalog,
        "/api/v1/risk/metrics/{name}": RiskMetricSpec,
        "/api/v1/risk/governance-levels": GovernanceLevelsCatalog,
        "/api/v1/risk/incoherences": RiskIncoherencesResponse,
        "/api/v1/risk/snapshots": list[RiskSnapshotRecord],
    }

    for path, payload_type in contracts.items():
        route = _route(path)
        assert route.response_model.__name__.startswith("ApiResponse[")
        assert route.response_model.model_fields["data"].annotation == payload_type


def test_risk_catalog_endpoints_return_typed_payloads(monkeypatch) -> None:
    client = _client(monkeypatch)

    metrics = client.get("/api/v1/risk/metrics").json()
    metric = client.get("/api/v1/risk/metrics/var_historical").json()
    governance = client.get("/api/v1/risk/governance-levels").json()
    incoherences = client.get("/api/v1/risk/incoherences").json()

    assert metrics["data_quality"] == "demo_static"
    assert metric["data_quality"] == "demo_static"
    assert governance["data_quality"] == "demo_static"
    assert incoherences["data_quality"] == "demo_static"

    metrics_catalog = RiskMetricsCatalog.model_validate(metrics["data"])
    metric_spec = RiskMetricSpec.model_validate(metric["data"])
    governance_catalog = GovernanceLevelsCatalog.model_validate(governance["data"])
    incoherence_payload = RiskIncoherencesResponse.model_validate(incoherences["data"])

    assert set(metrics_catalog.root) == set(METRIC_SPECS)
    assert metric_spec.name == METRIC_SPECS["var_historical"]["name"]
    assert governance_catalog.root["calculated"] == GovernanceLevelInfo.model_validate(GOVERNANCE_LEVELS["calculated"])
    assert [item.model_dump() for item in incoherence_payload.incoherences] == CURRENT_INCOHERENCES
    assert [step.model_dump() for step in incoherence_payload.correction_plan] == CORRECTION_PLAN


def test_risk_snapshot_contract_accepts_typed_records(monkeypatch) -> None:
    client = _client(monkeypatch, snapshots=[SAMPLE_SNAPSHOT])

    payload = client.get("/api/v1/risk/snapshots").json()

    assert payload["data_quality"] == "mixed"
    assert len(payload["data"]) == 1

    snapshot = RiskSnapshotRecord.model_validate(payload["data"][0])
    assert snapshot.snapshot_id == "snap_001"
    assert snapshot.asset == "AAPL"
    assert snapshot.n_observations == 252
    assert snapshot.computed_at == datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc)
    assert snapshot.governance_summary["usable_for_decisions"] is True

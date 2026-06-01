from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.routes import ml as ml_routes
from app.routes.ml import RunDetail, router
from app.schemas.ml import MLTrainAsyncResponse


def _route(path: str, method: str) -> APIRoute:
    for candidate in router.routes:
        if isinstance(candidate, APIRoute) and candidate.path == path and method in candidate.methods:
            return candidate
    raise AssertionError(f"Route not found for {method} {path}")


def test_get_run_route_uses_typed_response_model() -> None:
    route = _route("/api/v1/ml/runs/{run_id}", "GET")
    assert route.response_model is not dict
    assert "ApiResponse" in str(route.response_model)
    assert "RunDetail" in str(route.response_model)


def test_train_async_route_uses_typed_response_model() -> None:
    route = _route("/api/v1/ml/train/async", "POST")
    assert route.response_model is not dict
    assert "ApiResponse" in str(route.response_model)
    assert "MLTrainAsyncResponse" in str(route.response_model)


def test_train_async_schema_requires_pending_status() -> None:
    payload = MLTrainAsyncResponse(job_id="job-123")
    assert payload.status == "PENDING"


@pytest.mark.asyncio
async def test_get_run_returns_404_when_run_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _missing(_: str) -> None:
        return None

    monkeypatch.setattr(ml_routes, "fetch_run_detail", _missing)

    with pytest.raises(HTTPException) as exc:
        await ml_routes.get_run("missing-run")

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_run_returns_typed_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    detail = RunDetail(
        run_id="run-1",
        run_name="rf_spy_5d",
        model_type="random_forest",
        asset="SPY",
        horizon_days=5,
        status="completed",
    )

    async def _found(_: str) -> RunDetail:
        return detail

    monkeypatch.setattr(ml_routes, "fetch_run_detail", _found)

    response = await ml_routes.get_run("run-1")

    assert isinstance(response.data, RunDetail)
    assert response.data.run_id == "run-1"
    assert response.data.asset == "SPY"
    assert response.data.model_type == "random_forest"

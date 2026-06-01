from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from pydantic import ValidationError

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.routes import analysis as analysis_routes
from app.routes.analysis import router
from app.schemas.analysis import (
    CompanyAnalysisAsyncResponse,
    CompanyAnalysisRequest,
    CompanyAnalysisResponse,
)


def _route(path: str, method: str) -> APIRoute:
    for candidate in router.routes:
        if isinstance(candidate, APIRoute) and candidate.path == path and method in candidate.methods:
            return candidate
    raise AssertionError(f"Route not found for {method} {path}")


def test_company_async_route_uses_typed_response_model() -> None:
    route = _route("/api/v1/analysis/company/async", "POST")
    assert route.response_model is not dict
    assert "ApiResponse" in str(route.response_model)
    assert "CompanyAnalysisAsyncResponse" in str(route.response_model)


def test_company_analysis_async_schema_pending_shape() -> None:
    payload = CompanyAnalysisAsyncResponse(status="PENDING", job_id="job-123")
    assert payload.status == "PENDING"
    assert payload.job_id == "job-123"
    assert payload.result is None


def test_company_analysis_async_schema_completed_sync_shape() -> None:
    payload = CompanyAnalysisAsyncResponse(
        status="COMPLETED_SYNC",
        result=CompanyAnalysisResponse(ticker="AAPL", company_name="Apple"),
    )
    assert payload.status == "COMPLETED_SYNC"
    assert payload.result is not None
    assert payload.result.ticker == "AAPL"


def test_company_analysis_async_schema_rejects_mixed_shape() -> None:
    with pytest.raises(ValidationError):
        CompanyAnalysisAsyncResponse(
            status="PENDING",
            job_id="job-123",
            result=CompanyAnalysisResponse(ticker="AAPL", company_name="Apple"),
        )


@pytest.mark.asyncio
async def test_company_analysis_async_returns_pending_when_celery_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Task:
        id = "job-xyz"

    class _Celery:
        @staticmethod
        def send_task(name: str, kwargs: dict):
            return _Task()

    fake_module = types.SimpleNamespace(celery_app=_Celery())
    monkeypatch.setitem(sys.modules, "app.workers.celery_app", fake_module)

    req = CompanyAnalysisRequest(ticker="AAPL")
    resp = await analysis_routes.company_analysis_async(req)
    assert resp.data.status == "PENDING"
    assert resp.data.job_id == "job-xyz"
    assert resp.data.result is None


@pytest.mark.asyncio
async def test_company_analysis_async_falls_back_to_completed_sync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _CeleryFail:
        @staticmethod
        def send_task(name: str, kwargs: dict):
            raise RuntimeError("broker down")

    fake_module = types.SimpleNamespace(celery_app=_CeleryFail())
    monkeypatch.setitem(sys.modules, "app.workers.celery_app", fake_module)
    monkeypatch.setattr(
        analysis_routes,
        "_run_analysis",
        lambda req: {"ticker": req.ticker.upper(), "company_name": "Apple"},
    )

    req = CompanyAnalysisRequest(ticker="AAPL")
    resp = await analysis_routes.company_analysis_async(req)
    assert resp.data.status == "COMPLETED_SYNC"
    assert resp.data.job_id is None
    assert resp.data.result is not None
    assert resp.data.result.ticker == "AAPL"

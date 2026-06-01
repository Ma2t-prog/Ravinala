from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.routes import agents as agents_routes
from app.routes.agents import (
    AgentCatalogResponse,
    MissionRequest,
    MissionResponse,
    MissionStatusResponse,
    router,
)
from app.workers.celery_app import celery_app


def _route(path: str, method: str) -> APIRoute:
    for candidate in router.routes:
        if isinstance(candidate, APIRoute) and candidate.path == path and method in candidate.methods:
            return candidate
    raise AssertionError(f"Route not found for {method} {path}")


def test_agents_routes_use_explicit_response_models() -> None:
    assert _route("/api/v1/agents/list", "GET").response_model is AgentCatalogResponse
    assert _route("/api/v1/agents/missions/start", "POST").response_model is MissionResponse
    assert _route("/api/v1/agents/missions/{mission_id}/cancel", "POST").response_model is MissionStatusResponse
    assert _route("/api/v1/agents/missions/{mission_id}/status", "GET").response_model is MissionStatusResponse


@pytest.mark.asyncio
async def test_start_mission_returns_503_when_agent_runtime_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(agents_routes, "run_mission", None)

    with pytest.raises(HTTPException) as exc:
        await agents_routes.start_mission(MissionRequest(mission_type="quick_scan"))

    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_mission_status_returns_typed_payload_when_missing() -> None:
    with pytest.raises(HTTPException) as exc:
        await agents_routes.get_mission_status("mission-123")

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_start_mission_rejects_unknown_mission_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _runner(mission_type: str, params: dict, user_id: str, mission_id: str | None = None):
        if False:
            yield None

    monkeypatch.setattr(agents_routes, "run_mission", _runner)

    with pytest.raises(HTTPException) as exc:
        await agents_routes.start_mission(MissionRequest(mission_type="unknown_mission"))

    assert exc.value.status_code == 422


def test_agents_catalog_lists_runtime_agents_present_in_mission_flows() -> None:
    names = {item["name"] for item in agents_routes.AGENT_DEFINITIONS}
    assert {"ReportAgent", "AlertAgent", "SpawnerAgent"}.issubset(names)


def test_celery_app_includes_analysis_and_portfolio_tasks() -> None:
    includes = set(celery_app.conf.include)
    assert "app.workers.tasks.analysis_task" in includes
    assert "app.workers.tasks.portfolio_task" in includes

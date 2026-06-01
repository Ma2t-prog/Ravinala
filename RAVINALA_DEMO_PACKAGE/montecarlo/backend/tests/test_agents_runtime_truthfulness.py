"""
Tests de vérité runtime — MLAgent et MonitoringAgent.

But:
- empêcher les retours simulés présentés comme réels
- vérifier que les agents s'appuient sur les services backend partagés
"""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace
from unittest import mock

import pytest

sys.modules.setdefault("langgraph", mock.MagicMock())
sys.modules.setdefault("langgraph.config", mock.MagicMock())
sys.modules.setdefault("langgraph.graph", mock.MagicMock())
sys.modules.setdefault("langgraph.graph.message", mock.MagicMock())

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agents.nodes import ml_agent, monitoring_agent  # noqa: E402


class _Dumpable:
    def __init__(self, payload: dict):
        self._payload = payload
        for key, value in payload.items():
            setattr(self, key, value)

    def model_dump(self) -> dict:
        return dict(self._payload)


@pytest.mark.asyncio
async def test_ml_agent_reports_not_executed_when_predict_inputs_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[dict] = []
    monkeypatch.setattr(ml_agent, "get_stream_writer", lambda: events.append)
    monkeypatch.setattr(
        ml_agent,
        "list_model_artifacts",
        lambda: [_Dumpable({"model_type": "random_forest", "asset": "SPY", "run_name": "rf_spy", "artifact_path": "artifacts/rf_spy.joblib"})],
    )

    async def fake_fetch_runs(**kwargs):
        return [_Dumpable({"run_id": "run-1", "asset": "SPY", "model_type": "random_forest"})]

    monkeypatch.setattr(ml_agent, "fetch_runs", fake_fetch_runs)

    result = await ml_agent.ml_agent_node({"params": {"task": "predict"}})

    assert result["agents_completed"] == ["MLAgent"]
    assert result["ml_data"]["source"] == "ml_service"
    assert result["ml_data"]["status"] == "not_executed"
    assert result["ml_data"]["reason"] == "predict requires both asset and run_id"
    assert "accuracy" not in result["ml_data"]
    assert [event["event"] for event in events] == ["ml_start", "ml_inventory", "ml_skipped"]


@pytest.mark.asyncio
async def test_ml_agent_prediction_uses_backend_ml_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[dict] = []
    monkeypatch.setattr(ml_agent, "get_stream_writer", lambda: events.append)
    monkeypatch.setattr(ml_agent, "get_shared_executor", lambda: None)
    monkeypatch.setattr(ml_agent, "list_model_artifacts", lambda: [])

    async def fake_fetch_runs(**kwargs):
        return []

    async def fake_run_prediction(**kwargs):
        return _Dumpable(
            {
                "asset": "SPY",
                "predicted_return": 0.031,
                "predicted_direction": "up",
                "confidence": 0.64,
                "prediction_date": "2026-03-24T00:00:00Z",
                "target_date": "2026-03-31T00:00:00Z",
                "horizon_days": 5,
                "run_id": "run-123",
            }
        )

    monkeypatch.setattr(ml_agent, "fetch_runs", fake_fetch_runs)
    monkeypatch.setattr(ml_agent, "run_prediction", fake_run_prediction)

    result = await ml_agent.ml_agent_node(
        {
            "params": {
                "task": "predict",
                "asset": "SPY",
                "run_id": "run-123",
                "horizon_days": 5,
            }
        }
    )

    assert result["agents_completed"] == ["MLAgent"]
    assert result["ml_data"]["source"] == "ml_service"
    assert result["ml_data"]["status"] == "completed"
    assert result["ml_data"]["prediction"]["run_id"] == "run-123"
    assert result["ml_data"]["predicted_direction"] == "up"
    assert [event["event"] for event in events] == ["ml_start", "ml_inventory", "ml_complete"]


@pytest.mark.asyncio
async def test_monitoring_agent_uses_deep_health_instead_of_demo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[dict] = []
    monkeypatch.setattr(monitoring_agent, "get_stream_writer", lambda: events.append)

    async def fake_deep_health_check():
        return {
            "status": "critical",
            "timestamp": "2026-03-24T00:00:00Z",
            "checks": {
                "database": {"status": "critical", "detail": "connection refused"},
                "cache": {"status": "ok", "detail": "memory", "latency_ms": 2.5},
            },
        }

    class _Alerts:
        def summary(self) -> dict:
            return {"total_active": 1}

        def active(self, limit: int = 10) -> list[dict]:
            return [{"tier": "critical", "category": "database", "title": "DB down"}]

    monkeypatch.setattr(monitoring_agent, "deep_health_check", fake_deep_health_check)
    monkeypatch.setattr(monitoring_agent, "get_alert_manager", lambda: _Alerts())

    result = await monitoring_agent.monitoring_agent_node({})

    assert result["agents_completed"] == ["MonitoringAgent"]
    assert result["monitoring_data"]["source"] == "observability.health"
    assert result["monitoring_data"]["status"] == "critical"
    assert result["monitoring_data"]["services"]["database"] == "critical"
    assert result["monitoring_data"]["alerts"][0]["category"] == "database"
    assert [event["event"] for event in events] == [
        "monitoring_start",
        "service_checked",
        "service_checked",
        "monitoring_complete",
    ]

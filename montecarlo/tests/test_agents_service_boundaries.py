from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import agent_mission_service


def test_agents_route_no_longer_owns_global_mission_state_or_broadcast_logic() -> None:
    source = (BACKEND_DIR / "app" / "routes" / "agents.py").read_text(encoding="utf-8")
    assert "_active_missions" not in source
    assert "_connected_clients" not in source
    assert "_broadcast_event" not in source
    assert "app.services.agent_mission_service" in source


@pytest.mark.asyncio
async def test_agent_mission_service_tracks_lifecycle() -> None:
    async def _runner(mission_type: str, params: dict, user_id: str):
        yield {"agent": "System", "event": "noop", "data": {}, "status": "running", "progress": 0.1, "timestamp": 0.0}

    mission_id = agent_mission_service.start_mission_task(
        mission_type="quick_scan",
        params={},
        user_id="system",
        runner=_runner,
    )

    await asyncio.sleep(0)
    await asyncio.sleep(0)

    assert agent_mission_service.get_mission_status_value(mission_id) == "completed"


@pytest.mark.asyncio
async def test_agent_mission_service_passes_stable_mission_id_to_runner() -> None:
    captured: dict[str, str] = {}

    async def _runner(mission_type: str, params: dict, user_id: str, mission_id: str | None = None):
        captured["mission_id"] = mission_id or ""
        yield {"agent": "System", "event": "noop", "data": {"mission_id": mission_id}, "status": "running", "progress": 0.1, "timestamp": 0.0}

    mission_id = agent_mission_service.start_mission_task(
        mission_type="quick_scan",
        params={},
        user_id="system",
        runner=_runner,
        mission_type_validator=lambda mission_type: mission_type == "quick_scan",
    )

    await asyncio.sleep(0)
    await asyncio.sleep(0)

    assert captured["mission_id"] == mission_id


def test_agent_mission_service_rejects_unknown_mission_type() -> None:
    async def _runner(mission_type: str, params: dict, user_id: str):
        if False:
            yield None

    with pytest.raises(agent_mission_service.InvalidMissionTypeError):
        agent_mission_service.start_mission_task(
            mission_type="unknown",
            params={},
            user_id="system",
            runner=_runner,
            mission_type_validator=lambda mission_type: mission_type == "quick_scan",
        )


class _DummyWebSocket:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.sent.append(payload)


def _reset_agent_runtime_state() -> None:
    agent_mission_service._active_missions.clear()
    agent_mission_service._mission_statuses.clear()
    agent_mission_service._mission_timestamps.clear()
    agent_mission_service._connected_clients.clear()
    agent_mission_service._client_missions.clear()
    agent_mission_service._mission_clients.clear()


@pytest.mark.asyncio
async def test_agent_mission_service_scopes_ws_events_to_mission_subscriber() -> None:
    _reset_agent_runtime_state()
    ws_owner = _DummyWebSocket()
    ws_other = _DummyWebSocket()
    agent_mission_service.register_client(ws_owner)
    agent_mission_service.register_client(ws_other)

    async def _runner(mission_type: str, params: dict, user_id: str, mission_id: str | None = None):
        yield {
            "agent": "AnalysisAgent",
            "event": "progress",
            "data": {"step": "analysis"},
            "status": "running",
            "progress": 0.5,
            "timestamp": 0.0,
        }

    await agent_mission_service.handle_ws_command(
        ws=ws_owner,
        raw='{"action":"start","mission_type":"quick_scan","params":{}}',
        runner=_runner,
        mission_type_validator=lambda mission_type: mission_type == "quick_scan",
    )

    await asyncio.sleep(0)
    await asyncio.sleep(0)

    owner_events = [payload["event"] for payload in ws_owner.sent]
    other_events = [payload["event"] for payload in ws_other.sent]

    assert "mission_accepted" in owner_events
    assert "progress" in owner_events
    assert other_events == []
    progress_payload = next(payload for payload in ws_owner.sent if payload["event"] == "progress")
    assert progress_payload["data"]["mission_id"]

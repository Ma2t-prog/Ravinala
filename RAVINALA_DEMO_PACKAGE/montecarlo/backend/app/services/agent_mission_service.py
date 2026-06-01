"""
services/agent_mission_service.py - shared agent mission manager.

Owns mission lifecycle state, websocket client registry, and shared mission
orchestration so the agents route does not duplicate control flow across REST
and WebSocket entrypoints.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import time
import uuid
from typing import Any, Awaitable, Callable

from fastapi import WebSocket

logger = logging.getLogger(__name__)

MissionRunner = Callable[..., Awaitable[Any]]

_active_missions: dict[str, asyncio.Task] = {}
_mission_statuses: dict[str, str] = {}
_mission_timestamps: dict[str, float] = {}
_connected_clients: list[WebSocket] = []
_client_missions: dict[WebSocket, set[str]] = {}
_mission_clients: dict[str, set[WebSocket]] = {}
_MISSION_TTL_SECONDS = 3600
_TERMINAL_STATUSES = {"completed", "cancelled", "error", "not_found"}


class AgentRuntimeUnavailableError(Exception):
    """Raised when the optional agent runtime dependencies are unavailable."""


class MissionNotFoundError(Exception):
    """Raised when a requested mission id is unknown."""


class InvalidMissionTypeError(Exception):
    """Raised when a mission type is not part of the configured graph."""


def _ts() -> float:
    return time.time()


def _record_status(mission_id: str, status: str) -> None:
    _mission_statuses[mission_id] = status
    if mission_id not in _mission_timestamps or status in _TERMINAL_STATUSES:
        _mission_timestamps[mission_id] = _ts()


def _cleanup_stale_missions() -> int:
    """Purge terminal mission states that have outlived the retention window."""
    now = _ts()
    stale_ids = [
        mission_id
        for mission_id, status in list(_mission_statuses.items())
        if status in _TERMINAL_STATUSES
        and now - _mission_timestamps.get(mission_id, now) > _MISSION_TTL_SECONDS
    ]
    for mission_id in stale_ids:
        _active_missions.pop(mission_id, None)
        _mission_statuses.pop(mission_id, None)
        _mission_timestamps.pop(mission_id, None)
    return len(stale_ids)


async def _broadcast_system_event(
    *,
    event: str,
    data: dict[str, Any],
    status: str,
    progress: float,
    mission_id: str | None = None,
) -> None:
    await broadcast_event(
        {
            "agent": "System" if event in {"connected", "unavailable", "mission_accepted"} else "OrchestratorAgent",
            "event": event,
            "data": data,
            "status": status,
            "progress": progress,
            "timestamp": _ts(),
        },
        mission_id=mission_id,
    )


def _subscribe_client_to_mission(ws: WebSocket, mission_id: str) -> None:
    client_missions = _client_missions.setdefault(ws, set())
    client_missions.add(mission_id)
    _mission_clients.setdefault(mission_id, set()).add(ws)


def _extract_mission_id(event: Any) -> str | None:
    if isinstance(event, dict):
        if isinstance(event.get("data"), dict) and event["data"].get("mission_id"):
            return str(event["data"]["mission_id"])
        if event.get("mission_id"):
            return str(event["mission_id"])
    if isinstance(event, tuple) and len(event) == 2:
        _, data = event
        if isinstance(data, dict) and data.get("mission_id"):
            return str(data["mission_id"])
    return None


def _normalize_event_for_mission(event: Any, mission_id: str) -> Any:
    if isinstance(event, dict):
        normalized = dict(event)
        data = normalized.get("data")
        normalized_data = dict(data) if isinstance(data, dict) else {}
        normalized_data.setdefault("mission_id", mission_id)
        normalized["data"] = normalized_data
        normalized.setdefault("mission_id", mission_id)
        return normalized
    if isinstance(event, tuple) and len(event) == 2:
        mode, data = event
        if isinstance(data, dict):
            normalized_data = dict(data)
            normalized_data.setdefault("mission_id", mission_id)
            return (mode, normalized_data)
    return event


async def _run_and_broadcast_mission(
    *,
    mission_id: str,
    mission_type: str,
    params: dict[str, Any],
    user_id: str,
    runner: MissionRunner | None,
) -> None:
    if runner is None:
        _record_status(mission_id, "error")
        await _broadcast_system_event(
            event="mission_failed",
            data={"mission_id": mission_id, "error": "Agent runtime dependencies unavailable"},
            status="error",
            progress=0.0,
            mission_id=mission_id,
        )
        return

    _record_status(mission_id, "running")
    try:
        runner_kwargs = {}
        try:
            signature = inspect.signature(runner)
            if "mission_id" in signature.parameters:
                runner_kwargs["mission_id"] = mission_id
        except (TypeError, ValueError):
            runner_kwargs = {}

        async for event in runner(mission_type, params, user_id, **runner_kwargs):
            await broadcast_event(
                _normalize_event_for_mission(event, mission_id),
                mission_id=mission_id,
            )
        _record_status(mission_id, "completed")
    except asyncio.CancelledError:
        _record_status(mission_id, "cancelled")
        await _broadcast_system_event(
            event="mission_cancelled",
            data={"mission_id": mission_id},
            status="idle",
            progress=0.0,
            mission_id=mission_id,
        )
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("Mission %s failed: %s", mission_id, exc)
        _record_status(mission_id, "error")
        await _broadcast_system_event(
            event="mission_failed",
            data={"mission_id": mission_id, "error": str(exc)},
            status="error",
            progress=0.0,
            mission_id=mission_id,
        )
    finally:
        _active_missions.pop(mission_id, None)
        subscribers = _mission_clients.pop(mission_id, set())
        for client in subscribers:
            missions = _client_missions.get(client)
            if missions is not None:
                missions.discard(mission_id)


def ensure_runtime_available(runner: MissionRunner | None) -> None:
    """Raise a typed error when the agent runtime is not available."""
    if runner is None:
        raise AgentRuntimeUnavailableError("Agent runtime dependencies unavailable")


def start_mission_task(
    *,
    mission_type: str,
    params: dict[str, Any] | None,
    user_id: str,
    runner: MissionRunner | None,
    mission_type_validator: Callable[[str], bool] | None = None,
) -> str:
    """Create and register a mission task, returning its mission id."""
    ensure_runtime_available(runner)
    if mission_type_validator is not None and not mission_type_validator(mission_type):
        raise InvalidMissionTypeError(f"Unknown mission type '{mission_type}'")
    _cleanup_stale_missions()
    mission_id = str(uuid.uuid4())
    _record_status(mission_id, "started")
    task = asyncio.create_task(
        _run_and_broadcast_mission(
            mission_id=mission_id,
            mission_type=mission_type,
            params=params or {},
            user_id=user_id,
            runner=runner,
        )
    )
    _active_missions[mission_id] = task
    return mission_id


def cancel_mission_task(mission_id: str) -> str:
    """Cancel a running mission or raise when it is unknown."""
    _cleanup_stale_missions()
    task = _active_missions.get(mission_id)
    if task is None:
        if mission_id in _mission_statuses:
            return _mission_statuses[mission_id]
        raise MissionNotFoundError("Mission not found")
    task.cancel()
    _record_status(mission_id, "cancelled")
    return "cancelled"


def get_mission_status_value(mission_id: str) -> str:
    """Return the mission status, preserving terminal states after completion."""
    _cleanup_stale_missions()
    task = _active_missions.get(mission_id)
    if task is not None:
        if task.cancelled():
            _record_status(mission_id, "cancelled")
            return "cancelled"
        if task.done():
            status = _mission_statuses.get(mission_id, "completed")
            _record_status(mission_id, status)
            return status
        return _mission_statuses.get(mission_id, "running")
    return _mission_statuses.get(mission_id, "not_found")


def register_client(ws: WebSocket) -> None:
    _cleanup_stale_missions()
    if ws not in _connected_clients:
        _connected_clients.append(ws)
    _client_missions.setdefault(ws, set())


def unregister_client(ws: WebSocket) -> None:
    try:
        _connected_clients.remove(ws)
    except ValueError:
        pass
    for mission_id in _client_missions.pop(ws, set()):
        subscribers = _mission_clients.get(mission_id)
        if subscribers is None:
            continue
        subscribers.discard(ws)
        if not subscribers:
            _mission_clients.pop(mission_id, None)


async def send_unavailable_and_close(ws: WebSocket) -> None:
    await ws.send_json(
        {
            "agent": "System",
            "event": "unavailable",
            "data": {"message": "Agent runtime dependencies unavailable"},
            "status": "error",
            "progress": 0.0,
            "timestamp": _ts(),
        }
    )
    await ws.close(code=1013)


async def send_connected(ws: WebSocket) -> None:
    await ws.send_json(
        {
            "agent": "System",
            "event": "connected",
            "data": {"message": "Connected to agent stream"},
            "status": "idle",
            "progress": 0.0,
            "timestamp": _ts(),
        }
    )


async def handle_ws_command(
    *,
    ws: WebSocket,
    raw: str,
    runner: MissionRunner | None,
    mission_type_validator: Callable[[str], bool] | None = None,
) -> None:
    """Handle one websocket command payload."""
    command = json.loads(raw)
    action = command.get("action")

    if action == "start":
        mission_type = command.get("mission_type", "quick_scan")
        params = command.get("params", {})
        mission_id = start_mission_task(
            mission_type=mission_type,
            params=params,
            user_id="ws_user",
            runner=runner,
            mission_type_validator=mission_type_validator,
        )
        _subscribe_client_to_mission(ws, mission_id)
        await ws.send_json(
            {
                "agent": "System",
                "event": "mission_accepted",
                "data": {"mission_id": mission_id, "mission_type": mission_type},
                "status": "running",
                "progress": 0.0,
                "timestamp": _ts(),
            }
        )
        return

    if action == "cancel":
        mission_id = command.get("mission_id")
        if mission_id:
            cancel_mission_task(mission_id)


async def broadcast_event(event: Any, mission_id: str | None = None) -> None:
    """Broadcast an event to websocket clients, scoped by mission when available."""
    if mission_id is not None:
        event = _normalize_event_for_mission(event, mission_id)
    mission_scope = mission_id or _extract_mission_id(event)
    clients = (
        list(_mission_clients.get(mission_scope, set()))
        if mission_scope is not None
        else list(_connected_clients)
    )
    if not clients:
        return

    dead: list[WebSocket] = []
    for client in clients:
        try:
            if isinstance(event, tuple):
                mode, data = event
                if mode == "custom":
                    await client.send_json(data)
                elif mode == "updates":
                    await client.send_json(
                        {
                            "agent": "System",
                            "event": "state_update",
                            "data": data,
                            "status": "running",
                            "progress": 0.5,
                            "timestamp": _ts(),
                        }
                    )
            elif isinstance(event, dict):
                await client.send_json(event)
        except Exception:  # noqa: BLE001
            dead.append(client)

    for client in dead:
        unregister_client(client)


__all__ = [
    "AgentRuntimeUnavailableError",
    "InvalidMissionTypeError",
    "MissionNotFoundError",
    "broadcast_event",
    "cancel_mission_task",
    "ensure_runtime_available",
    "get_mission_status_value",
    "handle_ws_command",
    "register_client",
    "send_connected",
    "send_unavailable_and_close",
    "start_mission_task",
    "unregister_client",
]

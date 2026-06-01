"""
Agent orchestration routes — WebSocket streaming + REST endpoints.
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel, Field

try:
    from app.agents.runner import run_mission
    from app.agents.nodes.orchestrator import available_mission_types, is_valid_mission_type
except ModuleNotFoundError:
    run_mission = None
    available_mission_types = lambda: tuple()
    is_valid_mission_type = lambda _mission_type: False

from app.services.agent_mission_service import (
    AgentRuntimeUnavailableError,
    InvalidMissionTypeError,
    MissionNotFoundError,
    cancel_mission_task,
    ensure_runtime_available,
    get_mission_status_value,
    handle_ws_command,
    register_client,
    send_connected,
    send_unavailable_and_close,
    start_mission_task,
    unregister_client,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


class MissionRequest(BaseModel):
    mission_type: str
    params: dict = Field(default_factory=dict)


class MissionResponse(BaseModel):
    mission_id: str
    status: str
    message: str


class AgentDefinition(BaseModel):
    name: str
    color: str
    role: str


class AgentCatalogResponse(BaseModel):
    agents: list[AgentDefinition]


class MissionStatusResponse(BaseModel):
    status: str
    mission_id: str


AGENT_DEFINITIONS = [
    {"name": "OrchestratorAgent", "color": "#D4AF37", "role": "Supervisor"},
    {"name": "MarketAgent",       "color": "#00D4FF", "role": "Market Data"},
    {"name": "AnalysisAgent",     "color": "#3B82F6", "role": "Fundamentals"},
    {"name": "RiskAgent",         "color": "#EF4444", "role": "Risk Engine"},
    {"name": "PortfolioAgent",    "color": "#10B981", "role": "Optimization"},
    {"name": "BacktestAgent",     "color": "#F59E0B", "role": "Backtesting"},
    {"name": "MLAgent",           "color": "#8B5CF6", "role": "ML/Prediction"},
    {"name": "MonitoringAgent",   "color": "#6366F1", "role": "Health Check"},
    {"name": "ErrorHandlerAgent", "color": "#F43F5E", "role": "Error Handler"},
    {"name": "LoggerAgent",       "color": "#94A3B8", "role": "Logger"},
    {"name": "ReportAgent",       "color": "#F97316", "role": "Narrative Report"},
    {"name": "AlertAgent",        "color": "#FB7185", "role": "Alerting"},
    {"name": "SpawnerAgent",      "color": "#14B8A6", "role": "Dynamic Delegation"},
]


@router.get("/list", response_model=AgentCatalogResponse)
async def list_agents() -> AgentCatalogResponse:
    """Return the list of available agents."""
    return AgentCatalogResponse(
        agents=[AgentDefinition(**definition) for definition in AGENT_DEFINITIONS]
    )


@router.post("/missions/start", response_model=MissionResponse)
async def start_mission(req: MissionRequest):
    """Start a new agent mission."""
    try:
        mission_id = start_mission_task(
            mission_type=req.mission_type,
            params=req.params,
            user_id="system",
            runner=run_mission,
            mission_type_validator=is_valid_mission_type,
        )
    except AgentRuntimeUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except InvalidMissionTypeError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error": str(exc),
                "available_mission_types": list(available_mission_types()),
            },
        )

    return MissionResponse(
        mission_id=mission_id,
        status="started",
        message=f"Mission {req.mission_type} started",
    )


@router.post("/missions/{mission_id}/cancel", response_model=MissionStatusResponse)
async def cancel_mission(mission_id: str) -> MissionStatusResponse:
    """Cancel a running mission."""
    try:
        status = cancel_mission_task(mission_id)
    except MissionNotFoundError as exc:
        raise HTTPException(404, str(exc))
    return MissionStatusResponse(status=status, mission_id=mission_id)


@router.get("/missions/{mission_id}/status", response_model=MissionStatusResponse)
async def get_mission_status(mission_id: str) -> MissionStatusResponse:
    """Get mission status."""
    status_value = get_mission_status_value(mission_id)
    if status_value == "not_found":
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found")
    return MissionStatusResponse(status=status_value, mission_id=mission_id)


@router.websocket("/stream")
async def agent_stream(ws: WebSocket):
    """
    WebSocket endpoint for real-time agent event streaming.
    Clients connect here and receive all agent events.
    Can also send commands (start/cancel).
    """
    await ws.accept()
    register_client(ws)

    try:
        try:
            ensure_runtime_available(run_mission)
        except AgentRuntimeUnavailableError:
            await send_unavailable_and_close(ws)
            return

        await send_connected(ws)

        while True:
            try:
                raw = await ws.receive_text()
                await handle_ws_command(
                    ws=ws,
                    raw=raw,
                    runner=run_mission,
                    mission_type_validator=is_valid_mission_type,
                )
            except WebSocketDisconnect:
                break
            except InvalidMissionTypeError as exc:
                await ws.send_json(
                    {
                        "agent": "System",
                        "event": "invalid_command",
                        "data": {
                            "error": str(exc),
                            "available_mission_types": list(available_mission_types()),
                        },
                        "status": "error",
                        "progress": 0.0,
                    }
                )
    finally:
        unregister_client(ws)

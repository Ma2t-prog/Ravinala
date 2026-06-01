"""
OrchestratorAgent — entry point and supervisor node.
Plans agents for the mission, tracks completion.
"""

import uuid
import time
from langgraph.config import get_stream_writer


_VALID_AGENT_NAMES = {
    "market",
    "analysis",
    "risk",
    "portfolio",
    "backtest",
    "ml",
    "monitoring",
    "logger",
    "report",
    "alert",
    "spawner",
}

MISSION_FLOWS = {
    # Core missions
    "full_analysis":       ["market", "analysis", "risk", "portfolio", "spawner", "alert", "report", "logger"],
    "quick_scan":          ["market", "analysis", "logger"],
    "risk_check":          ["market", "risk", "alert", "logger"],
    "backtest_run":        ["market", "backtest", "logger"],
    "ml_predict":          ["market", "ml", "logger"],
    "portfolio_optimize":  ["market", "analysis", "risk", "portfolio", "spawner", "alert", "report", "logger"],
    "health_check":        ["monitoring", "alert", "logger"],
    # New missions
    "deep_analysis":       ["market", "analysis", "risk", "portfolio", "backtest", "ml", "spawner", "alert", "report", "logger"],
    "signal_hunt":         ["market", "analysis", "spawner", "alert", "logger"],
}


def _validate_mission_flows() -> None:
    for mission_type, agents in MISSION_FLOWS.items():
        for agent in agents:
            if agent not in _VALID_AGENT_NAMES:
                raise ValueError(
                    f"MISSION_FLOWS['{mission_type}'] references unknown agent '{agent}'"
                )


def available_mission_types() -> tuple[str, ...]:
    return tuple(sorted(MISSION_FLOWS.keys()))


def is_valid_mission_type(mission_type: str) -> bool:
    return mission_type in MISSION_FLOWS


_validate_mission_flows()


async def orchestrator_node(state: dict) -> dict:
    """Entry point. Plans agents to execute for this mission."""
    writer = get_stream_writer()

    mission_id = state.get("mission_id") or str(uuid.uuid4())
    mission_type = state["mission_type"]
    planned_agents = MISSION_FLOWS.get(mission_type, [])

    writer({
        "agent": "OrchestratorAgent",
        "event": "mission_start",
        "data": {
            "mission_id": mission_id,
            "mission_type": mission_type,
            "planned_agents": [_NODE_TO_AGENT.get(a, a.capitalize() + "Agent") for a in planned_agents],
        },
        "status": "running",
        "progress": 0.0,
        "timestamp": time.time(),
    })

    return {
        "mission_id": mission_id,
        "status": "running",
    }


_NODE_TO_AGENT = {
    "market":    "MarketAgent",
    "analysis":  "AnalysisAgent",
    "risk":      "RiskAgent",
    "portfolio": "PortfolioAgent",
    "backtest":  "BacktestAgent",
    "ml":        "MLAgent",
    "monitoring":"MonitoringAgent",
    "logger":    "LoggerAgent",
    "report":    "ReportAgent",
    "alert":     "AlertAgent",
    "spawner":   "SpawnerAgent",
}


def route_after_dispatch(state: dict) -> str:
    """After orchestrator, route to first uncompleted agent in the flow."""
    mission_type = state["mission_type"]
    flow = MISSION_FLOWS.get(mission_type, [])
    completed = set(state.get("agents_completed", []))

    for agent_name in flow:
        agent_class = _NODE_TO_AGENT.get(agent_name, agent_name.capitalize() + "Agent")
        if agent_class not in completed:
            return agent_name

    return "done"

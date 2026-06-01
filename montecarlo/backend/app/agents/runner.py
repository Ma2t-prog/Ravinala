"""
Mission runner — executes agent missions with streaming.
"""

from app.agents.graph import build_agent_graph

# Compile the graph once at import time
agent_graph = build_agent_graph()


async def run_mission(
    mission_type: str,
    params: dict,
    user_id: str,
    mission_id: str | None = None,
):
    """
    Launch a mission and yield streaming events.
    Uses LangGraph streaming API v2.
    """
    initial_state = {
        "mission_id": mission_id or "",
        "mission_type": mission_type,
        "user_id": user_id,
        "status": "pending",
        "params": params,
        "market_data": {},
        "analysis_data": {},
        "risk_data": {},
        "portfolio_data": {},
        "backtest_data": {},
        "ml_data": {},
        "monitoring_data": {},
        "agents_completed": [],
        "agents_failed": [],
        "errors": [],
        "result": {},
        "duration_ms": 0,
        "messages": [],
    }

    async for event in agent_graph.astream(
        initial_state,
        stream_mode=["custom", "updates"],
        config={"recursion_limit": 50},
    ):
        yield event

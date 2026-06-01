"""
MissionState — shared state schema for the LangGraph agent graph.
"""

import operator
from typing import Any, Annotated, TypedDict
from langgraph.graph.message import add_messages


class MissionStateSchema(TypedDict):
    # Mission metadata
    mission_id: str
    mission_type: str  # "full_analysis", "quick_scan", etc.
    user_id: str
    status: str  # "pending", "running", "completed", "failed", "cancelled"

    # Input params
    params: dict[str, Any]

    # Data flowing between agents
    market_data: dict[str, Any]
    analysis_data: dict[str, Any]
    risk_data: dict[str, Any]
    portfolio_data: dict[str, Any]
    backtest_data: dict[str, Any]
    ml_data: dict[str, Any]
    monitoring_data: dict[str, Any]
    log_data: dict[str, Any]
    report_data: dict[str, Any]
    alert_data: dict[str, Any]
    spawned_data: dict[str, Any]   # results from dynamically spawned agents

    # Tracking — use operator.add reducer so lists ACCUMULATE across nodes
    agents_completed: Annotated[list[str], operator.add]
    agents_failed: Annotated[list[str], operator.add]
    errors: Annotated[list[dict[str, Any]], operator.add]

    # Final result
    result: dict[str, Any]
    duration_ms: int

    # Messages (LangGraph built-in)
    messages: Annotated[list, add_messages]

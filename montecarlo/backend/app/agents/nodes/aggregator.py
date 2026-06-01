"""
Aggregator — final node that combines all agent results.
"""

import time
from langgraph.config import get_stream_writer


async def aggregator_node(state: dict) -> dict:
    """Aggregate all agent results into a final mission result."""
    writer = get_stream_writer()

    result = {
        "market":    state.get("market_data", {}),
        "analysis":  state.get("analysis_data", {}),
        "risk":      state.get("risk_data", {}),
        "portfolio": state.get("portfolio_data", {}),
        "backtest":  state.get("backtest_data", {}),
        "ml":        state.get("ml_data", {}),
        "monitoring":state.get("monitoring_data", {}),
        "log":       state.get("log_data", {}),
        "report":    state.get("report_data", {}),
        "alerts":    state.get("alert_data", {}),
        "spawned":   state.get("spawned_data", {}),
    }

    # Remove empty entries
    result = {k: v for k, v in result.items() if v}

    writer({
        "agent": "OrchestratorAgent",
        "event": "mission_complete",
        "data": {
            "mission_id": state.get("mission_id", ""),
            "results_summary": list(result.keys()),
            "agents_completed": state.get("agents_completed", []),
            "agents_failed": state.get("agents_failed", []),
        },
        "status": "completed",
        "progress": 1.0,
        "timestamp": time.time(),
    })

    return {
        "result": result,
        "status": "completed",
    }

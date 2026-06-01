"""
ErrorHandlerAgent — transversal error interception and recovery.
"""

import time
import logging
from langgraph.config import get_stream_writer

logger = logging.getLogger(__name__)

AGENT_NAME = "ErrorHandlerAgent"


async def error_handler_node(state: dict) -> dict:
    """Handle errors from other agents. Decide retry/fallback/abort."""
    writer = get_stream_writer()

    errors = state.get("errors", [])
    failed = state.get("agents_failed", [])
    last_error = errors[-1] if errors else {"agent": "unknown", "error": "no error info"}

    writer({
        "agent": AGENT_NAME,
        "event": "error_caught",
        "data": {
            "agent_name": last_error.get("agent", "unknown"),
            "error_type": "runtime",
            "message": last_error.get("error", "unknown"),
        },
        "status": "running",
        "progress": 0.5,
        "timestamp": time.time(),
    })

    # Simple strategy: log and continue (skip the failed agent)
    action = "skip"
    reason = f"Agent {last_error.get('agent')} failed, skipping to next"

    writer({
        "agent": AGENT_NAME,
        "event": "error_action",
        "data": {"agent_name": last_error.get("agent"), "action": action, "reason": reason},
        "status": "completed",
        "progress": 1.0,
        "timestamp": time.time(),
    })

    # Mark the failed agents as "completed" so routing moves to next.
    # Only return the NEW entries (operator.add reducer will append them).
    already_completed = set(state.get("agents_completed", []))
    newly_completed = [f for f in failed if f not in already_completed]

    return {
        "agents_completed": newly_completed,
    }

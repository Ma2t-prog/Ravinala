"""
LoggerAgent — structured event logger.
Receives all agent data and persists a structured activity log.
"""

import asyncio
import time
import logging
from langgraph.config import get_stream_writer

logger = logging.getLogger(__name__)

AGENT_NAME = "LoggerAgent"


async def logger_agent_node(state: dict) -> dict:
    """Format and persist a structured log of the mission."""
    writer = get_stream_writer()

    writer({
        "agent": AGENT_NAME,
        "event": "logger_start",
        "data": {"mission_id": state.get("mission_id", "")},
        "status": "running",
        "progress": 0.0,
        "timestamp": time.time(),
    })

    await asyncio.sleep(0.1)

    completed = state.get("agents_completed", [])
    failed    = state.get("agents_failed", [])
    errors    = state.get("errors", [])

    writer({
        "agent": AGENT_NAME,
        "event": "logger_indexing",
        "data": {"agents_logged": len(completed)},
        "status": "running",
        "progress": 0.4,
        "timestamp": time.time(),
    })

    await asyncio.sleep(0.15)

    log_entries = []
    for ag in completed:
        log_entries.append({
            "agent": ag,
            "status": "completed",
            "ts": time.time(),
        })
    for ag in failed:
        log_entries.append({
            "agent": ag,
            "status": "failed",
            "ts": time.time(),
        })

    writer({
        "agent": AGENT_NAME,
        "event": "logger_done",
        "data": {
            "entries": len(log_entries),
            "errors": len(errors),
            "mission_id": state.get("mission_id", ""),
        },
        "status": "completed",
        "progress": 1.0,
        "timestamp": time.time(),
    })

    return {
        "log_data": {
            "entries": log_entries,
            "total": len(log_entries),
            "errors": errors,
        },
        "agents_completed": [AGENT_NAME],
    }

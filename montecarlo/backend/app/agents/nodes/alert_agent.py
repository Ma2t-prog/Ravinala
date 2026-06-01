"""
AlertAgent — threshold monitor and alert emitter.
Checks risk/analysis data against defined thresholds and fires alerts.
"""

import time
import asyncio
import logging
from langgraph.config import get_stream_writer

logger = logging.getLogger(__name__)

AGENT_NAME = "AlertAgent"

# Default alert thresholds (no hardcoded risk_free_rate — only risk thresholds)
THRESHOLDS = {
    "var_95_max":        -0.05,   # Portfolio VaR 95% below -5% triggers alert
    "max_drawdown_max":  -0.20,   # Max drawdown below -20% triggers alert
    "score_min":          40.0,   # Fundamental score below 40 triggers alert
}


async def alert_agent_node(state: dict) -> dict:
    """Scan all agent data and emit alerts for threshold violations."""
    writer = get_stream_writer()

    writer({
        "agent": AGENT_NAME,
        "event": "alert_scan_start",
        "data": {"thresholds": THRESHOLDS},
        "status": "running",
        "progress": 0.0,
        "timestamp": time.time(),
    })

    await asyncio.sleep(0.1)
    alerts = []

    # ── Risk alerts ───────────────────────────────────────────────────────────
    risk = state.get("risk_data", {})
    if risk:
        writer({
            "agent": AGENT_NAME,
            "event": "alert_checking",
            "data": {"target": "risk"},
            "status": "running",
            "progress": 0.25,
            "timestamp": time.time(),
        })
        var_95 = risk.get("portfolio_var_95", 0)
        if isinstance(var_95, (int, float)) and var_95 < THRESHOLDS["var_95_max"]:
            alerts.append({
                "level":   "CRITICAL",
                "source":  "RiskAgent",
                "message": f"Portfolio VaR 95% = {var_95:.2%} — exceeds threshold {THRESHOLDS['var_95_max']:.2%}",
            })
        max_dd = risk.get("max_drawdown", 0)
        if isinstance(max_dd, (int, float)) and max_dd < THRESHOLDS["max_drawdown_max"]:
            alerts.append({
                "level":   "WARNING",
                "source":  "RiskAgent",
                "message": f"Max drawdown = {max_dd:.2%} — exceeds threshold",
            })

    await asyncio.sleep(0.1)

    # ── Analysis alerts ───────────────────────────────────────────────────────
    analysis = state.get("analysis_data", {})
    if analysis:
        writer({
            "agent": AGENT_NAME,
            "event": "alert_checking",
            "data": {"target": "analysis"},
            "status": "running",
            "progress": 0.55,
            "timestamp": time.time(),
        })
        for ticker, data in analysis.items():
            if not isinstance(data, dict):
                continue
            score = data.get("score", 100)
            if isinstance(score, (int, float)) and score < THRESHOLDS["score_min"]:
                alerts.append({
                    "level":   "WARNING",
                    "source":  "AnalysisAgent",
                    "message": f"{ticker} fundamental score = {score:.0f} — below minimum {THRESHOLDS['score_min']:.0f}",
                })

    await asyncio.sleep(0.1)

    # ── Spawned-agent alerts ──────────────────────────────────────────────────
    spawned_data = state.get("spawned_data", {})
    for agent_name, sdata in spawned_data.items():
        if isinstance(sdata, dict) and sdata.get("alert"):
            alerts.append({
                "level":   "INFO",
                "source":  agent_name,
                "message": sdata["alert"],
            })

    writer({
        "agent": AGENT_NAME,
        "event": "alert_done",
        "data": {
            "total":    len(alerts),
            "critical": sum(1 for a in alerts if a["level"] == "CRITICAL"),
            "warning":  sum(1 for a in alerts if a["level"] == "WARNING"),
            "info":     sum(1 for a in alerts if a["level"] == "INFO"),
            "alerts":   alerts,
        },
        "status": "completed",
        "progress": 1.0,
        "timestamp": time.time(),
    })

    return {
        "alert_data": {
            "alerts": alerts,
            "total": len(alerts),
        },
        "agents_completed": [AGENT_NAME],
    }

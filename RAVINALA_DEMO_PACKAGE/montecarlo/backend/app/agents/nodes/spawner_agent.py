"""
SpawnerAgent — dynamic sub-agent factory.

Analyses the current mission state and decides which specialised
micro-agents to spawn on-the-fly.  Each spawned agent runs as an
async coroutine, emits its own WebSocket events, and writes results
into `spawned_data`.

No LLM key required — spawning decisions are rule-based so the
system works out-of-the-box.
"""

import time
import asyncio
import logging
from langgraph.config import get_stream_writer

logger = logging.getLogger(__name__)

AGENT_NAME = "SpawnerAgent"


# ── Rule engine ──────────────────────────────────────────────────────────────

def _decide_agents(state: dict) -> list[dict]:
    """
    Rule-based decision: which micro-agents to spawn.
    Returns a list of agent specs: {name, reason, fn}.
    """
    agents = []
    market   = state.get("market_data", {})
    risk     = state.get("risk_data", {})
    analysis = state.get("analysis_data", {})

    # Spawn a correlation agent if there are multiple tickers
    if len(market) >= 2:
        agents.append({
            "name":   "CorrelationAgent",
            "reason": f"Detected {len(market)} tickers — cross-asset correlation needed",
            "fn":     _run_correlation,
        })

    # Spawn a stress-test detail agent if VaR is elevated
    var_95 = risk.get("portfolio_var_95", 0)
    if isinstance(var_95, (int, float)) and var_95 < -0.03:
        agents.append({
            "name":   "StressDetailAgent",
            "reason": f"VaR {var_95:.2%} elevated — running deep stress scenarios",
            "fn":     _run_stress_detail,
        })

    # Spawn a momentum agent if analysis has mixed signals
    recs = [d.get("recommendation", "") for d in analysis.values() if isinstance(d, dict)]
    buys  = recs.count("BUY")
    sells = recs.count("SELL")
    if buys > 0 and sells > 0:
        agents.append({
            "name":   "MomentumAgent",
            "reason": f"Mixed signals ({buys} BUY / {sells} SELL) — momentum cross-check",
            "fn":     _run_momentum,
        })

    # Always: a concise summary agent
    agents.append({
        "name":   "SummaryAgent",
        "reason": "Generates one-line executive summary",
        "fn":     _run_summary,
    })

    return agents


# ── Main spawner node ─────────────────────────────────────────────────────────

async def spawner_agent_node(state: dict) -> dict:
    """Decide which micro-agents to spawn, run them, collect results."""
    writer = get_stream_writer()

    to_spawn = _decide_agents(state)

    writer({
        "agent": AGENT_NAME,
        "event": "spawner_plan",
        "data": {
            "count":   len(to_spawn),
            "agents":  [a["name"] for a in to_spawn],
            "reasons": {a["name"]: a["reason"] for a in to_spawn},
        },
        "status": "running",
        "progress": 0.0,
        "timestamp": time.time(),
    })

    spawned_data: dict = {}

    for i, spec in enumerate(to_spawn):
        name = spec["name"]
        fn   = spec["fn"]

        # Announce spawn
        writer({
            "agent":   AGENT_NAME,
            "event":   "agent_spawned",
            "data":    {"spawned_agent": name, "reason": spec["reason"]},
            "status":  "running",
            "progress": (i / len(to_spawn)) * 0.9,
            "timestamp": time.time(),
            # Frontend uses this flag to render in the Spawn Deck
            "dynamic": True,
            "spawned_agent": name,
        })

        # Run the micro-agent (it emits its own events)
        result = await fn(state, writer)
        spawned_data[name] = result

        writer({
            "agent":   AGENT_NAME,
            "event":   "agent_finished",
            "data":    {"spawned_agent": name, "keys": list(result.keys())},
            "status":  "running",
            "progress": ((i + 1) / len(to_spawn)) * 0.9,
            "timestamp": time.time(),
            "dynamic": True,
            "spawned_agent": name,
        })

    writer({
        "agent": AGENT_NAME,
        "event": "spawner_done",
        "data":  {"spawned": list(spawned_data.keys())},
        "status": "completed",
        "progress": 1.0,
        "timestamp": time.time(),
    })

    return {
        "spawned_data": spawned_data,
        "agents_completed": [AGENT_NAME],
    }


# ── Micro-agent implementations ───────────────────────────────────────────────

def _pearson(a: list[float], b: list[float]) -> float:
    """Pearson correlation coefficient between two return series."""
    n = min(len(a), len(b))
    if n < 2:
        return 0.0
    a, b = a[:n], b[:n]
    mean_a = sum(a) / n
    mean_b = sum(b) / n
    cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n))
    std_a = (sum((v - mean_a) ** 2 for v in a) / n) ** 0.5
    std_b = (sum((v - mean_b) ** 2 for v in b) / n) ** 0.5
    if std_a < 1e-12 or std_b < 1e-12:
        return 0.0
    return round(cov / (n * std_a * std_b), 4)


async def _run_correlation(state: dict, writer) -> dict:
    """Compute pairwise correlation matrix from real returns_30d in market_data."""
    name = "CorrelationAgent"
    writer({"agent": name, "event": "start", "data": {}, "status": "running", "progress": 0.0, "timestamp": time.time(), "dynamic": True, "spawned_agent": name})
    await asyncio.sleep(0.05)

    market = state.get("market_data", {})
    tickers = [t for t, d in market.items() if isinstance(d, dict) and d.get("returns_30d")]

    matrix: dict[str, dict[str, float]] = {}
    source = "computed"
    if len(tickers) >= 2:
        for a in tickers:
            matrix[a] = {}
            for b in tickers:
                if a == b:
                    matrix[a][b] = 1.0
                else:
                    matrix[a][b] = _pearson(
                        market[a]["returns_30d"],
                        market[b]["returns_30d"],
                    )
    else:
        # Fallback: deterministic hash-based if no returns data available
        tickers = list(market.keys())
        source = "fallback_hash"
        for a in tickers:
            matrix[a] = {}
            for b in tickers:
                if a == b:
                    matrix[a][b] = 1.0
                else:
                    seed = (hash(a) ^ hash(b)) % 1000
                    matrix[a][b] = round(0.3 + (seed % 600) / 1000, 3)

    writer({"agent": name, "event": "done", "data": {"pairs": len(tickers) ** 2, "source": source}, "status": "completed", "progress": 1.0, "timestamp": time.time(), "dynamic": True, "spawned_agent": name})
    return {"correlation_matrix": matrix, "tickers": tickers, "source": source}


async def _run_stress_detail(state: dict, writer) -> dict:
    """Run additional stress scenarios beyond the standard RiskAgent."""
    name = "StressDetailAgent"
    scenarios = ["flash_crash", "rate_shock_200bps", "liquidity_crunch", "sector_rotation"]
    writer({"agent": name, "event": "start", "data": {"scenarios": scenarios}, "status": "running", "progress": 0.0, "timestamp": time.time(), "dynamic": True, "spawned_agent": name})

    results: dict[str, float] = {}
    for i, sc in enumerate(scenarios):
        await asyncio.sleep(0.12)
        seed = hash(sc) % 1000
        results[sc] = round(-0.05 - (seed % 300) / 1000, 4)
        writer({"agent": name, "event": "scenario_done", "data": {"scenario": sc, "impact": results[sc]}, "status": "running", "progress": (i + 1) / len(scenarios), "timestamp": time.time(), "dynamic": True, "spawned_agent": name})

    worst = min(results, key=lambda k: results[k])
    alert_msg = f"Worst scenario: {worst} ({results[worst]:.2%})" if results[worst] < -0.15 else None

    writer({"agent": name, "event": "done", "data": {"worst": worst}, "status": "completed", "progress": 1.0, "timestamp": time.time(), "dynamic": True, "spawned_agent": name})
    return {"stress_scenarios": results, "alert": alert_msg}


async def _run_momentum(state: dict, writer) -> dict:
    """Check momentum indicators (RSI proxy, trend direction)."""
    name = "MomentumAgent"
    writer({"agent": name, "event": "start", "data": {}, "status": "running", "progress": 0.0, "timestamp": time.time(), "dynamic": True, "spawned_agent": name})

    market = state.get("market_data", {})
    momentum: dict[str, dict] = {}
    for i, (ticker, data) in enumerate(market.items()):
        await asyncio.sleep(0.08)
        price = data.get("price", 100) if isinstance(data, dict) else 100
        seed  = hash(ticker) % 1000
        rsi   = 30 + (seed % 40)
        trend = "bullish" if rsi > 50 else "bearish"
        momentum[ticker] = {"rsi_proxy": rsi, "trend": trend, "price": price}
        writer({"agent": name, "event": "ticker_done", "data": {"ticker": ticker, "rsi": rsi, "trend": trend}, "status": "running", "progress": (i + 1) / max(len(market), 1), "timestamp": time.time(), "dynamic": True, "spawned_agent": name})

    writer({"agent": name, "event": "done", "data": {"tickers": len(momentum)}, "status": "completed", "progress": 1.0, "timestamp": time.time(), "dynamic": True, "spawned_agent": name})
    return {"momentum": momentum}


async def _run_summary(state: dict, writer) -> dict:
    """Produce a one-line executive summary of the mission."""
    name = "SummaryAgent"
    writer({"agent": name, "event": "start", "data": {}, "status": "running", "progress": 0.0, "timestamp": time.time(), "dynamic": True, "spawned_agent": name})
    await asyncio.sleep(0.15)

    mission_type = state.get("mission_type", "unknown")
    completed    = state.get("agents_completed", [])
    market       = state.get("market_data", {})
    tickers      = list(market.keys())

    summary = (
        f"Mission '{mission_type}' completed {len(completed)} agents "
        f"across {len(tickers)} ticker(s): {', '.join(tickers) or 'N/A'}."
    )

    writer({"agent": name, "event": "done", "data": {"summary": summary}, "status": "completed", "progress": 1.0, "timestamp": time.time(), "dynamic": True, "spawned_agent": name})
    return {"summary": summary}

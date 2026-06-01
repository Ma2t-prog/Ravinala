"""
LangGraph agent graph — builds and compiles the multi-agent orchestration graph.
"""

from langgraph.graph import StateGraph, START, END
from app.agents.state import MissionStateSchema
from app.agents.nodes.orchestrator import orchestrator_node, route_after_dispatch, MISSION_FLOWS
from app.agents.nodes.market_agent import market_agent_node
from app.agents.nodes.analysis_agent import analysis_agent_node
from app.agents.nodes.risk_agent import risk_agent_node
from app.agents.nodes.portfolio_agent import portfolio_agent_node
from app.agents.nodes.backtest_agent import backtest_agent_node
from app.agents.nodes.ml_agent import ml_agent_node
from app.agents.nodes.monitoring_agent import monitoring_agent_node
from app.agents.nodes.logger_agent import logger_agent_node
from app.agents.nodes.report_agent import report_agent_node
from app.agents.nodes.alert_agent import alert_agent_node
from app.agents.nodes.spawner_agent import spawner_agent_node
from app.agents.nodes.error_handler import error_handler_node
from app.agents.nodes.aggregator import aggregator_node


# Mapping from flow node name → agent class name used in agents_completed
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

# All routable agent names (used for conditional edge maps)
_ALL_AGENTS = list(_NODE_TO_AGENT.keys())


def route_after_agent(state: dict) -> str:
    """
    Determine next agent in the mission flow.
    If agent failed → error_handler.
    If all agents completed → aggregator.
    Otherwise → next agent in sequence.
    """
    mission_type = state["mission_type"]
    flow = MISSION_FLOWS.get(mission_type, [])
    completed = set(state.get("agents_completed", []))
    failed = state.get("agents_failed", [])

    if failed:
        last_failed = failed[-1]
        if last_failed not in completed:
            return "error_handler"

    for agent_name in flow:
        agent_class = _NODE_TO_AGENT.get(agent_name, agent_name.capitalize() + "Agent")
        if agent_class not in completed:
            return agent_name

    return "aggregator"


def build_agent_graph():
    """Build and compile the LangGraph multi-agent graph."""

    graph = StateGraph(MissionStateSchema)

    # ── Core agents ────────────────────────────────────────────────────────────
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("market",       market_agent_node)
    graph.add_node("analysis",     analysis_agent_node)
    graph.add_node("risk",         risk_agent_node)
    graph.add_node("portfolio",    portfolio_agent_node)
    graph.add_node("backtest",     backtest_agent_node)
    graph.add_node("ml",           ml_agent_node)
    graph.add_node("monitoring",   monitoring_agent_node)

    # ── New agents ─────────────────────────────────────────────────────────────
    graph.add_node("logger",   logger_agent_node)
    graph.add_node("report",   report_agent_node)
    graph.add_node("alert",    alert_agent_node)
    graph.add_node("spawner",  spawner_agent_node)

    # ── Support nodes ──────────────────────────────────────────────────────────
    graph.add_node("error_handler", error_handler_node)
    graph.add_node("aggregator",    aggregator_node)

    # ── Entry point ────────────────────────────────────────────────────────────
    graph.add_edge(START, "orchestrator")

    # ── Orchestrator dispatches to first agent in flow ─────────────────────────
    orchestrator_targets = {name: name for name in _ALL_AGENTS}
    orchestrator_targets["done"] = "aggregator"
    graph.add_conditional_edges("orchestrator", route_after_dispatch, orchestrator_targets)

    # ── Each agent routes to the next / aggregator / error_handler ─────────────
    agent_routing = {name: name for name in _ALL_AGENTS}
    agent_routing["aggregator"]    = "aggregator"
    agent_routing["error_handler"] = "error_handler"

    for agent_name in _ALL_AGENTS:
        graph.add_conditional_edges(agent_name, route_after_agent, agent_routing)

    # ── Error handler returns to orchestrator for re-routing ───────────────────
    graph.add_edge("error_handler", "orchestrator")

    # ── Aggregator → END ───────────────────────────────────────────────────────
    graph.add_edge("aggregator", END)

    return graph.compile()

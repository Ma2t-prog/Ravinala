"""
ReportAgent — mission journalist & live documentor.

Generates three outputs in sequence:
  1. NARRATIVE  — human-readable story of what happened, written like a captain's log
  2. AGENT DOCS — auto-generated doc card for every spawned dynamic agent
  3. MARKDOWN   — structured technical report saved to disk (reports/)
"""

import time
import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from langgraph.config import get_stream_writer

logger = logging.getLogger(__name__)

AGENT_NAME = "ReportAgent"
REPORTS_DIR = Path(__file__).parents[4] / "reports"


# ── Narrative templates ───────────────────────────────────────────────────────

_MISSION_INTROS = {
    "full_analysis":      "Full-spectrum analysis mission launched.",
    "quick_scan":         "Rapid intelligence sweep initiated.",
    "risk_check":         "Risk assessment protocol engaged.",
    "backtest_run":       "Historical backtesting sequence started.",
    "ml_predict":         "Machine learning prediction pipeline activated.",
    "portfolio_optimize": "Portfolio optimisation mission commenced.",
    "health_check":       "System-wide health diagnostic running.",
    "deep_analysis":      "Deep-dive analysis — all stations active.",
    "signal_hunt":        "Signal hunting mission — scanners at full power.",
}

_STATUS_FLAVOR = {
    "completed": "✓",
    "failed":    "✗",
    "running":   "…",
}


def _fmt_pct(v) -> str:
    if isinstance(v, (int, float)):
        return f"{v:.2%}"
    return str(v)


def _fmt_float(v, decimals=2) -> str:
    if isinstance(v, (int, float)):
        return f"{v:.{decimals}f}"
    return str(v)


# ── Section builders ──────────────────────────────────────────────────────────

def _build_header(state: dict, ts: str) -> str:
    mission_type = state.get("mission_type", "unknown")
    mission_id   = state.get("mission_id",   "—")
    intro        = _MISSION_INTROS.get(mission_type, "Mission executed.")
    tickers      = list(state.get("market_data", {}).keys())
    ticker_str   = ", ".join(f"`{t}`" for t in tickers) if tickers else "_none_"

    return (
        f"# GENESIX Ω — Mission Report\n\n"
        f"> {intro}\n\n"
        f"| Field | Value |\n"
        f"|-------|-------|\n"
        f"| Mission ID   | `{mission_id}` |\n"
        f"| Type         | `{mission_type}` |\n"
        f"| Tickers      | {ticker_str} |\n"
        f"| Generated    | {ts} |\n"
    )


def _build_narrative(state: dict) -> str:
    """Captain's log — a plain-English story of the mission."""
    lines = ["## Captain's Log\n"]
    completed = state.get("agents_completed", [])
    failed    = state.get("agents_failed",    [])
    errors    = state.get("errors",           [])

    lines.append(f"Mission deployed **{len(completed)}** agent(s).")
    if failed:
        lines.append(f"**{len(failed)}** agent(s) encountered errors: {', '.join(failed)}.")

    # Market narrative
    market = state.get("market_data", {})
    if market:
        tickers = list(market.keys())
        prices  = [f"{t} @ {_fmt_float(market[t].get('price', '?'))}" for t in tickers if isinstance(market.get(t), dict)]
        lines.append(f"MarketAgent pulled live data for {', '.join(tickers)}. "
                     + (f"Prices: {'; '.join(prices)}." if prices else ""))

    # Analysis narrative
    analysis = state.get("analysis_data", {})
    if analysis:
        buys  = [t for t, d in analysis.items() if isinstance(d, dict) and d.get("recommendation") == "BUY"]
        sells = [t for t, d in analysis.items() if isinstance(d, dict) and d.get("recommendation") == "SELL"]
        holds = [t for t, d in analysis.items() if isinstance(d, dict) and d.get("recommendation") == "HOLD"]
        parts = []
        if buys:  parts.append(f"**{len(buys)} BUY** ({', '.join(buys)})")
        if sells: parts.append(f"**{len(sells)} SELL** ({', '.join(sells)})")
        if holds: parts.append(f"**{len(holds)} HOLD** ({', '.join(holds)})")
        if parts:
            lines.append(f"AnalysisAgent returned signals: {', '.join(parts)}.")

    # Risk narrative
    risk = state.get("risk_data", {})
    if risk:
        var95 = risk.get("portfolio_var_95", None)
        mdd   = risk.get("max_drawdown", None)
        risk_line = "RiskAgent computed portfolio risk."
        if var95 is not None:
            level = "ELEVATED" if var95 < -0.04 else "MODERATE" if var95 < -0.02 else "LOW"
            risk_line += f" VaR(95%) = {_fmt_pct(var95)} → risk level **{level}**."
        if mdd is not None:
            risk_line += f" Max drawdown: {_fmt_pct(mdd)}."
        lines.append(risk_line)

    # Backtest narrative
    bt = state.get("backtest_data", {})
    if bt:
        ret   = bt.get("total_return",   None)
        sharpe= bt.get("sharpe_ratio",   None)
        trades= bt.get("trade_count",    None)
        bt_line = "BacktestAgent ran historical simulation."
        if ret    is not None: bt_line += f" Total return: {_fmt_pct(ret)}."
        if sharpe is not None: bt_line += f" Sharpe: {_fmt_float(sharpe)}."
        if trades is not None: bt_line += f" {trades} trades executed."
        lines.append(bt_line)

    # ML narrative
    ml = state.get("ml_data", {})
    if ml:
        acc   = ml.get("accuracy",   None)
        model = ml.get("model_type", "unknown model")
        ml_line = f"MLAgent trained **{model}**."
        if acc is not None: ml_line += f" Accuracy: {_fmt_pct(acc)}."
        lines.append(ml_line)

    # Spawned agents narrative
    spawned = state.get("spawned_data", {})
    if spawned:
        lines.append(f"SpawnerAgent dynamically created **{len(spawned)}** specialist agent(s): "
                     f"{', '.join(f'`{k}`' for k in spawned.keys())}.")
        if "CorrelationAgent" in spawned:
            corr = spawned["CorrelationAgent"]
            n = len(corr.get("tickers", []))
            lines.append(f"CorrelationAgent built a {n}×{n} correlation matrix.")
        if "StressDetailAgent" in spawned:
            sc = spawned["StressDetailAgent"].get("stress_scenarios", {})
            if sc:
                worst = min(sc, key=lambda k: sc[k])
                lines.append(f"StressDetailAgent: worst scenario **{worst}** ({_fmt_pct(sc[worst])}).")
        if "MomentumAgent" in spawned:
            mom = spawned["MomentumAgent"].get("momentum", {})
            bulls = [t for t, d in mom.items() if d.get("trend") == "bullish"]
            bears = [t for t, d in mom.items() if d.get("trend") == "bearish"]
            lines.append(f"MomentumAgent: {len(bulls)} bullish, {len(bears)} bearish.")
        if "SummaryAgent" in spawned:
            summary = spawned["SummaryAgent"].get("summary", "")
            if summary:
                lines.append(f"> _{summary}_")

    # Alerts narrative
    alert_data = state.get("alert_data", {})
    alerts = alert_data.get("alerts", [])
    if alerts:
        criticals = [a for a in alerts if a.get("level") == "CRITICAL"]
        warnings  = [a for a in alerts if a.get("level") == "WARNING"]
        if criticals:
            lines.append(f"🔴 AlertAgent raised **{len(criticals)} CRITICAL** alert(s).")
            for a in criticals[:2]:
                lines.append(f"  - {a.get('message', '')}")
        if warnings:
            lines.append(f"🟡 **{len(warnings)} warning(s)** flagged.")
    else:
        if state.get("alert_data"):
            lines.append("✅ AlertAgent: no threshold violations detected.")

    # Errors
    if errors:
        lines.append(f"\n⚠️ {len(errors)} error(s) logged during execution.")

    return "\n\n".join(lines)


def _build_agent_status(state: dict) -> str:
    """Table of all agents that ran in this mission."""
    completed = state.get("agents_completed", [])
    failed    = state.get("agents_failed",    [])
    all_agents = list(dict.fromkeys(completed + failed))  # preserve order, dedupe

    if not all_agents:
        return ""

    rows = ["## Agent Roster\n", "| Agent | Status | Notes |", "|-------|--------|-------|"]
    for ag in all_agents:
        status = _STATUS_FLAVOR["completed"] if ag in completed else _STATUS_FLAVOR["failed"]
        note   = "nominal" if ag in completed else "error — see log"
        rows.append(f"| `{ag}` | {status} | {note} |")

    return "\n".join(rows)


def _build_spawned_docs(spawned: dict) -> str:
    """Auto-generated doc card for every dynamic agent."""
    if not spawned:
        return ""

    lines = ["## Spawned Agent Documentation\n",
             "_Auto-generated by ReportAgent at mission end._\n"]

    doc_templates = {
        "CorrelationAgent": (
            "Cross-asset correlation matrix builder.",
            "Computes pairwise correlations between all tickers in market_data.",
            ["correlation_matrix: dict[str, dict[str, float]]", "tickers: list[str]"],
        ),
        "StressDetailAgent": (
            "Extended stress-test scenario runner.",
            "Runs flash_crash, rate_shock_200bps, liquidity_crunch, and sector_rotation scenarios.",
            ["stress_scenarios: dict[str, float]", "alert: str | None"],
        ),
        "MomentumAgent": (
            "RSI-proxy momentum classifier.",
            "Estimates trend direction (bullish/bearish) for each ticker using an RSI proxy.",
            ["momentum: dict[str, {rsi_proxy, trend, price}]"],
        ),
        "SummaryAgent": (
            "Executive summary generator.",
            "Produces a single human-readable sentence summarising the mission outcome.",
            ["summary: str"],
        ),
    }

    for name, data in spawned.items():
        tmpl = doc_templates.get(name)
        if tmpl:
            desc, detail, outputs = tmpl
            lines.append(f"### `{name}`")
            lines.append(f"**{desc}**  \n{detail}\n")
            lines.append("**Outputs:**")
            for o in outputs:
                lines.append(f"- `{o}`")
        else:
            lines.append(f"### `{name}`")
            lines.append(f"_Dynamic agent — no static documentation available._")
            lines.append(f"**Keys returned:** {', '.join(f'`{k}`' for k in data.keys()) if data else '—'}")
        lines.append("")

    return "\n".join(lines)


def _build_metrics_table(state: dict) -> str:
    """Key numeric metrics in a scannable table."""
    rows = []

    risk = state.get("risk_data", {})
    if isinstance(risk, dict):
        if "portfolio_var_95" in risk:
            rows.append(("Portfolio VaR 95%", _fmt_pct(risk["portfolio_var_95"])))
        if "portfolio_cvar_95" in risk:
            rows.append(("Portfolio CVaR 95%", _fmt_pct(risk["portfolio_cvar_95"])))
        if "max_drawdown" in risk:
            rows.append(("Max Drawdown", _fmt_pct(risk["max_drawdown"])))

    bt = state.get("backtest_data", {})
    if isinstance(bt, dict):
        if "total_return" in bt:
            rows.append(("Backtest Total Return", _fmt_pct(bt["total_return"])))
        if "sharpe_ratio" in bt:
            rows.append(("Sharpe Ratio", _fmt_float(bt["sharpe_ratio"])))
        if "trade_count" in bt:
            rows.append(("Trades Executed", str(bt["trade_count"])))

    ml = state.get("ml_data", {})
    if isinstance(ml, dict) and "accuracy" in ml:
        rows.append(("ML Accuracy", _fmt_pct(ml["accuracy"])))

    if not rows:
        return ""

    lines = ["## Key Metrics\n", "| Metric | Value |", "|--------|-------|"]
    for metric, val in rows:
        lines.append(f"| {metric} | **{val}** |")
    return "\n".join(lines)


# ── Main node ─────────────────────────────────────────────────────────────────

async def report_agent_node(state: dict) -> dict:
    writer = get_stream_writer()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    writer({
        "agent": AGENT_NAME, "event": "report_start",
        "data": {"mission_id": state.get("mission_id", ""), "timestamp": ts},
        "status": "running", "progress": 0.0, "timestamp": time.time(),
    })

    await asyncio.sleep(0.05)

    # ── 1. Narrative (Captain's log) ──────────────────────────────────────────
    writer({
        "agent": AGENT_NAME, "event": "report_section",
        "data": {"section": "narrative"}, "status": "running",
        "progress": 0.2, "timestamp": time.time(),
    })
    narrative = _build_narrative(state)
    await asyncio.sleep(0.1)

    # ── 2. Agent roster ───────────────────────────────────────────────────────
    writer({
        "agent": AGENT_NAME, "event": "report_section",
        "data": {"section": "roster"}, "status": "running",
        "progress": 0.4, "timestamp": time.time(),
    })
    roster = _build_agent_status(state)
    await asyncio.sleep(0.08)

    # ── 3. Spawned agent docs ─────────────────────────────────────────────────
    spawned = state.get("spawned_data", {})
    writer({
        "agent": AGENT_NAME, "event": "report_section",
        "data": {"section": "spawned_docs", "count": len(spawned)},
        "status": "running", "progress": 0.6, "timestamp": time.time(),
    })
    spawned_docs = _build_spawned_docs(spawned)
    await asyncio.sleep(0.08)

    # ── 4. Metrics table ──────────────────────────────────────────────────────
    writer({
        "agent": AGENT_NAME, "event": "report_section",
        "data": {"section": "metrics"}, "status": "running",
        "progress": 0.75, "timestamp": time.time(),
    })
    metrics = _build_metrics_table(state)
    await asyncio.sleep(0.08)

    # ── 5. Assemble full report ───────────────────────────────────────────────
    header   = _build_header(state, ts)
    sections = [s for s in [header, narrative, metrics, roster, spawned_docs] if s]
    report_md = "\n\n---\n\n".join(sections)

    # ── 6. Persist to disk ────────────────────────────────────────────────────
    writer({
        "agent": AGENT_NAME, "event": "report_saving",
        "data": {"section": "disk"}, "status": "running",
        "progress": 0.9, "timestamp": time.time(),
    })
    saved_path = None
    try:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{state.get('mission_id', 'unknown')}_{int(time.time())}.md"
        saved_path = REPORTS_DIR / filename
        saved_path.write_text(report_md, encoding="utf-8")
        logger.info(f"[ReportAgent] Report saved → {saved_path}")
    except Exception as exc:
        logger.warning(f"[ReportAgent] Could not save report to disk: {exc}")

    await asyncio.sleep(0.05)

    writer({
        "agent": AGENT_NAME, "event": "report_done",
        "data": {
            "sections":     len(sections),
            "length":       len(report_md),
            "spawned_docs": len(spawned),
            "saved_path":   str(saved_path) if saved_path else None,
            "mission_id":   state.get("mission_id", ""),
        },
        "status": "completed", "progress": 1.0, "timestamp": time.time(),
    })

    return {
        "report_data": {
            "markdown":     report_md,
            "sections":     len(sections),
            "saved_path":   str(saved_path) if saved_path else None,
            "spawned_docs": len(spawned),
        },
        "agents_completed": [AGENT_NAME],
    }

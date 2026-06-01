"""
BacktestAgent — strategy backtesting on historical data.
"""

import time
import logging
from langgraph.config import get_stream_writer

logger = logging.getLogger(__name__)

AGENT_NAME = "BacktestAgent"


async def backtest_agent_node(state: dict) -> dict:
    """Run a backtest on the given strategy and tickers."""
    writer = get_stream_writer()
    start_time = time.time()

    params = state.get("params", {})
    tickers = params.get("tickers", [])
    strategy = params.get("strategy", "momentum")

    writer({
        "agent": AGENT_NAME,
        "event": "backtest_start",
        "data": {"strategy": strategy, "nb_tickers": len(tickers)},
        "status": "running",
        "progress": 0.0,
        "timestamp": time.time(),
    })

    try:
        # Simulate year-by-year progress
        years = [2021, 2022, 2023, 2024, 2025]
        for i, year in enumerate(years):
            writer({
                "agent": AGENT_NAME,
                "event": "backtest_year",
                "data": {"year": year, "return_ytd": round(0.05 + i * 0.02, 3), "nb_trades": 12 + i * 3},
                "status": "running",
                "progress": (i + 1) / len(years),
                "timestamp": time.time(),
            })

        backtest_result = {
            "total_return": 0.45,
            "sharpe": 1.32,
            "max_drawdown": -0.15,
            "nb_trades": 75,
            "strategy": strategy,
            "source": "demo_backtest",
        }

        duration_ms = int((time.time() - start_time) * 1000)

        writer({
            "agent": AGENT_NAME,
            "event": "backtest_complete",
            "data": {"total_return": backtest_result["total_return"], "sharpe": backtest_result["sharpe"], "nb_trades": backtest_result["nb_trades"], "duration_ms": duration_ms},
            "status": "completed",
            "progress": 1.0,
            "timestamp": time.time(),
        })

        return {
            "backtest_data": backtest_result,
            "agents_completed": ["BacktestAgent"],
        }

    except Exception as e:
        logger.error(f"BacktestAgent error: {e}")
        writer({
            "agent": AGENT_NAME,
            "event": "backtest_error",
            "data": {"error": str(e)},
            "status": "error",
            "progress": 0.0,
            "timestamp": time.time(),
        })
        return {
            "agents_failed": ["BacktestAgent"],
            "errors": [{"agent": AGENT_NAME, "error": str(e), "timestamp": time.time()}],
        }

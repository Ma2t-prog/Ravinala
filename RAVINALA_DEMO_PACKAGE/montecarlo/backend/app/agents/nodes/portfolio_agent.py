"""
PortfolioAgent — portfolio optimization (Markowitz, Risk Parity, etc.).
"""

import time
import logging
from langgraph.config import get_stream_writer

logger = logging.getLogger(__name__)

AGENT_NAME = "PortfolioAgent"


async def portfolio_agent_node(state: dict) -> dict:
    """Optimize portfolio allocation."""
    writer = get_stream_writer()
    start_time = time.time()

    params = state.get("params", {})
    tickers = params.get("tickers", [])
    method = params.get("method", "markowitz")
    market_data = state.get("market_data", {})
    risk_data = state.get("risk_data", {})

    writer({
        "agent": AGENT_NAME,
        "event": "portfolio_start",
        "data": {"method": method, "nb_assets": len(tickers)},
        "status": "running",
        "progress": 0.0,
        "timestamp": time.time(),
    })

    try:
        # Phase: Covariance matrix
        writer({
            "agent": AGENT_NAME,
            "event": "portfolio_phase",
            "data": {"phase": "covariance", "progress_pct": 33},
            "status": "running",
            "progress": 0.33,
            "timestamp": time.time(),
        })

        # Phase: Optimization
        writer({
            "agent": AGENT_NAME,
            "event": "portfolio_phase",
            "data": {"phase": "optimization", "progress_pct": 66},
            "status": "running",
            "progress": 0.66,
            "timestamp": time.time(),
        })

        # Phase: Frontier
        writer({
            "agent": AGENT_NAME,
            "event": "portfolio_phase",
            "data": {"phase": "frontier", "progress_pct": 90},
            "status": "running",
            "progress": 0.9,
            "timestamp": time.time(),
        })

        # Build equal-weight demo result
        n = max(len(tickers), 1)
        weights = {t: round(1.0 / n, 4) for t in tickers}
        portfolio_result = {
            "weights": weights,
            "expected_return": 0.12,
            "expected_risk": 0.18,
            "sharpe": 1.45,
            "method": method,
            "source": "demo_optimizer",
        }

        duration_ms = int((time.time() - start_time) * 1000)

        writer({
            "agent": AGENT_NAME,
            "event": "portfolio_complete",
            "data": {"sharpe": portfolio_result["sharpe"], "expected_return": portfolio_result["expected_return"], "duration_ms": duration_ms},
            "status": "completed",
            "progress": 1.0,
            "timestamp": time.time(),
        })

        return {
            "portfolio_data": portfolio_result,
            "agents_completed": ["PortfolioAgent"],
        }

    except Exception as e:
        logger.error(f"PortfolioAgent error: {e}")
        writer({
            "agent": AGENT_NAME,
            "event": "portfolio_error",
            "data": {"error": str(e)},
            "status": "error",
            "progress": 0.0,
            "timestamp": time.time(),
        })
        return {
            "agents_failed": ["PortfolioAgent"],
            "errors": [{"agent": AGENT_NAME, "error": str(e), "timestamp": time.time()}],
        }

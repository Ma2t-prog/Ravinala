"""
MarketAgent — fetches real-time market data + historical returns.
Provides returns_30d, volatility_30d, beta for downstream risk computation.
"""

import asyncio
import time
import math
import hashlib
import logging
from langgraph.config import get_stream_writer

logger = logging.getLogger(__name__)

AGENT_NAME = "MarketAgent"
_FETCH_TIMEOUT_SECONDS = 15


def _synthetic_returns(ticker: str, n: int = 30) -> list[float]:
    """Deterministic synthetic returns based on ticker hash — no np.random."""
    seed = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
    return [math.sin(seed * i * 0.37 + i) * 0.012 + math.cos(seed * 0.01 + i * 0.5) * 0.005
            for i in range(1, n + 1)]


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


def _beta(ticker_returns: list[float], spy_returns: list[float]) -> float:
    n = min(len(ticker_returns), len(spy_returns))
    if n < 2:
        return 1.0
    t = ticker_returns[:n]
    s = spy_returns[:n]
    t_mean = sum(t) / n
    s_mean = sum(s) / n
    cov = sum((t[i] - t_mean) * (s[i] - s_mean) for i in range(n)) / (n - 1)
    var_s = sum((v - s_mean) ** 2 for v in s) / (n - 1)
    return round(cov / var_s, 3) if var_s > 0 else 1.0


def _synthetic_fallback(ticker: str, spy_returns: list[float], *, reason: str) -> dict:
    returns_30d = _synthetic_returns(ticker)
    vol = _std(returns_30d) * math.sqrt(252)
    beta = _beta(returns_30d, spy_returns) if spy_returns else 1.0
    return {
        "price": 0.0,
        "change_pct": 0.0,
        "volume": 0,
        "name": ticker,
        "market_cap": 0.0,
        "returns_30d": returns_30d,
        "volatility_30d": round(vol, 4),
        "beta": beta,
        "source": f"fallback_{reason}",
    }


def _fetch_ticker_sync(ticker: str, spy_returns: list[float]) -> dict:
    """Fetch one ticker with full enrichment through the blocking provider."""
    try:
        import yfinance as yf

        t = yf.Ticker(ticker)
        info = t.info
        hist = t.history(period="2mo")

        price = info.get("regularMarketPrice") or info.get("previousClose") or 0.0
        change_pct = info.get("regularMarketChangePercent", 0.0) or 0.0

        # Historical returns
        if len(hist) >= 5:
            closes = hist["Close"].tolist()
            returns_30d = [
                (closes[i] - closes[i - 1]) / closes[i - 1]
                for i in range(1, min(len(closes), 31))
                if closes[i - 1] != 0
            ]
        else:
            returns_30d = _synthetic_returns(ticker)

        vol = _std(returns_30d) * math.sqrt(252)
        beta = _beta(returns_30d, spy_returns) if spy_returns else 1.0

        return {
            "price":          round(float(price), 4),
            "change_pct":     round(float(change_pct), 4),
            "volume":         int(info.get("regularMarketVolume", 0) or 0),
            "name":           info.get("shortName", ticker),
            "market_cap":     float(info.get("marketCap", 0) or 0),
            "returns_30d":    [round(r, 6) for r in returns_30d],
            "volatility_30d": round(vol, 4),
            "beta":           beta,
            "source":         "yfinance",
        }
    except (KeyError, TypeError, ValueError) as exc:
        logger.error("[MarketAgent] Data parsing error for %s: %s", ticker, exc)
        return _synthetic_fallback(ticker, spy_returns, reason="parse_error")
    except Exception as exc:  # noqa: BLE001
        logger.warning("[MarketAgent] Fetch failed for %s: %s", ticker, exc)
        return _synthetic_fallback(ticker, spy_returns, reason="fetch_error")


def _fetch_spy_returns_sync() -> list[float]:
    import yfinance as yf

    spy_hist = yf.Ticker("SPY").history(period="2mo")
    if len(spy_hist) < 5:
        return _synthetic_returns("SPY")

    closes = spy_hist["Close"].tolist()
    return [
        (closes[i] - closes[i - 1]) / closes[i - 1]
        for i in range(1, min(len(closes), 31))
        if closes[i - 1] != 0
    ]


async def _fetch_ticker(ticker: str, spy_returns: list[float]) -> dict:
    """Fetch one ticker with timeout protection so yfinance cannot hang forever."""
    loop = asyncio.get_running_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, _fetch_ticker_sync, ticker, spy_returns),
            timeout=_FETCH_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "[MarketAgent] Timeout (%ss) for %s, using deterministic fallback",
            _FETCH_TIMEOUT_SECONDS,
            ticker,
        )
        return _synthetic_fallback(ticker, spy_returns, reason="timeout")


async def _fetch_spy_returns() -> list[float]:
    loop = asyncio.get_running_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, _fetch_spy_returns_sync),
            timeout=_FETCH_TIMEOUT_SECONDS,
        )
    except Exception:  # noqa: BLE001
        return _synthetic_returns("SPY")


async def market_agent_node(state: dict) -> dict:
    """Fetch market data for requested tickers with historical enrichment."""
    writer = get_stream_writer()
    start_time = time.time()

    tickers = state["params"].get("tickers", [])
    data_types = state["params"].get("data_types", ["price"])

    writer({
        "agent": AGENT_NAME, "event": "market_fetch_start",
        "data": {"tickers": tickers, "data_types": data_types},
        "status": "running", "progress": 0.0, "timestamp": time.time(),
    })

    market_data: dict = {}
    spy_returns: list[float] = []

    spy_returns = await _fetch_spy_returns()

    for i, ticker in enumerate(tickers):
        data = await _fetch_ticker(ticker, spy_returns)
        market_data[ticker] = data

        writer({
            "agent": AGENT_NAME, "event": "market_data_partial",
            "data": {
                "ticker":       ticker,
                "price":        data["price"],
                "change_pct":   data["change_pct"],
                "volatility":   data["volatility_30d"],
                "beta":         data["beta"],
                "returns_count": len(data["returns_30d"]),
                "source":       data["source"],
            },
            "status": "running",
            "progress": (i + 1) / max(len(tickers), 1),
            "timestamp": time.time(),
        })

    duration_ms = int((time.time() - start_time) * 1000)

    writer({
        "agent": AGENT_NAME, "event": "market_fetch_done",
        "data": {"nb_tickers": len(tickers), "duration_ms": duration_ms},
        "status": "completed", "progress": 1.0, "timestamp": time.time(),
    })

    return {
        "market_data": market_data,
        "agents_completed": ["MarketAgent"],
    }

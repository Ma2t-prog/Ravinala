"""
AnalysisAgent — real fundamental analysis via yfinance.
Scoring 0-100 based on P/E, P/B, ROE, debt/equity, revenue growth, profit margins.
No demo_fallback when data is available.
"""

import time
import logging
from langgraph.config import get_stream_writer

logger = logging.getLogger(__name__)

AGENT_NAME = "AnalysisAgent"


def _score_ticker(ticker: str, info: dict) -> dict:
    """Score a ticker 0-100 on fundamental metrics. Returns score + reasons."""
    score   = 50.0
    reasons = []

    pe  = info.get("trailingPE")
    pb  = info.get("priceToBook")
    roe = info.get("returnOnEquity")
    de  = info.get("debtToEquity")
    rg  = info.get("revenueGrowth")
    pm  = info.get("profitMargins")
    peg = info.get("pegRatio")
    cr  = info.get("currentRatio")

    # P/E ratio
    if isinstance(pe, (int, float)) and pe > 0:
        if pe < 15:
            score += 12; reasons.append(f"P/E très attractif ({pe:.1f})")
        elif pe < 25:
            score += 6;  reasons.append(f"P/E raisonnable ({pe:.1f})")
        elif pe > 50:
            score -= 12; reasons.append(f"P/E élevé ({pe:.1f})")
        elif pe > 35:
            score -= 6;  reasons.append(f"P/E tendu ({pe:.1f})")

    # P/B ratio
    if isinstance(pb, (int, float)) and pb > 0:
        if pb < 1.5:
            score += 8;  reasons.append(f"P/B < 1.5 ({pb:.2f})")
        elif pb < 3:
            score += 3;  reasons.append(f"P/B correct ({pb:.2f})")
        elif pb > 8:
            score -= 8;  reasons.append(f"P/B élevé ({pb:.2f})")

    # ROE
    if isinstance(roe, (int, float)):
        if roe > 0.20:
            score += 12; reasons.append(f"ROE excellent ({roe:.1%})")
        elif roe > 0.12:
            score += 6;  reasons.append(f"ROE correct ({roe:.1%})")
        elif roe < 0:
            score -= 10; reasons.append(f"ROE négatif ({roe:.1%})")

    # Debt/Equity
    if isinstance(de, (int, float)):
        if de < 30:
            score += 8;  reasons.append(f"Faible endettement (D/E {de:.0f}%)")
        elif de < 80:
            score += 2;  reasons.append(f"Endettement modéré (D/E {de:.0f}%)")
        elif de > 200:
            score -= 12; reasons.append(f"Endettement élevé (D/E {de:.0f}%)")
        elif de > 120:
            score -= 6;  reasons.append(f"Endettement tendu (D/E {de:.0f}%)")

    # Revenue growth
    if isinstance(rg, (int, float)):
        if rg > 0.20:
            score += 10; reasons.append(f"Forte croissance revenus ({rg:.1%})")
        elif rg > 0.08:
            score += 5;  reasons.append(f"Croissance revenus correcte ({rg:.1%})")
        elif rg < 0:
            score -= 8;  reasons.append(f"Revenus en baisse ({rg:.1%})")

    # Profit margins
    if isinstance(pm, (int, float)):
        if pm > 0.20:
            score += 10; reasons.append(f"Marge nette excellente ({pm:.1%})")
        elif pm > 0.10:
            score += 5;  reasons.append(f"Marge nette correcte ({pm:.1%})")
        elif pm < 0:
            score -= 10; reasons.append(f"Marge nette négative ({pm:.1%})")

    # PEG ratio (bonus)
    if isinstance(peg, (int, float)) and peg > 0:
        if peg < 1:
            score += 5;  reasons.append(f"PEG < 1 (sous-évalué vs croissance)")
        elif peg > 3:
            score -= 4;  reasons.append(f"PEG élevé ({peg:.1f})")

    # Current ratio (liquidity)
    if isinstance(cr, (int, float)):
        if cr > 2:
            score += 4;  reasons.append(f"Bonne liquidité (CR {cr:.1f})")
        elif cr < 1:
            score -= 6;  reasons.append(f"Liquidité faible (CR {cr:.1f})")

    score = max(0.0, min(100.0, score))

    if score >= 68:   recommendation = "BUY"
    elif score <= 40: recommendation = "SELL"
    else:             recommendation = "HOLD"

    confidence = round(min(len(reasons) / 7, 1.0), 2)

    return {
        "score":          round(score, 1),
        "recommendation": recommendation,
        "confidence":     confidence,
        "reasons":        reasons,
        "pe_ratio":       pe,
        "pb_ratio":       pb,
        "roe":            roe,
        "debt_equity":    de,
        "revenue_growth": rg,
        "profit_margin":  pm,
    }


def _deterministic_fallback(ticker: str) -> dict:
    """Deterministic fallback — no np.random."""
    seed  = sum(ord(c) for c in ticker)
    score = 40.0 + (seed % 35)
    rec   = "BUY" if score > 62 else "HOLD" if score > 45 else "SELL"
    return {
        "score":          round(score, 1),
        "recommendation": rec,
        "confidence":     0.25,
        "reasons":        ["données fondamentales indisponibles — estimation déterministe"],
        "pe_ratio":       None,
        "pb_ratio":       None,
        "roe":            None,
        "debt_equity":    None,
        "revenue_growth": None,
        "profit_margin":  None,
        "source":         "fallback_deterministic",
    }


async def analysis_agent_node(state: dict) -> dict:
    """Run fundamental scoring on tickers."""
    writer = get_stream_writer()
    start_time = time.time()

    tickers     = state["params"].get("tickers", [])
    market_data = state.get("market_data", {})  # noqa: F841 — available for future use

    writer({
        "agent": AGENT_NAME, "event": "analysis_start",
        "data": {"tickers": tickers, "analysis_type": "fundamental"},
        "status": "running", "progress": 0.0, "timestamp": time.time(),
    })

    analysis_results: dict = {}

    for i, ticker in enumerate(tickers):
        writer({
            "agent": AGENT_NAME, "event": "analysis_phase",
            "data": {"phase": "scoring", "ticker": ticker,
                     "progress_pct": int((i / max(len(tickers), 1)) * 100)},
            "status": "running",
            "progress": (i + 0.5) / max(len(tickers), 1),
            "timestamp": time.time(),
        })

        try:
            import yfinance as yf
            info   = yf.Ticker(ticker).info
            result = _score_ticker(ticker, info)
            result["source"] = "yfinance_fundamental"
        except Exception as e:
            logger.warning(f"AnalysisAgent: yfinance failed for {ticker}: {e}")
            result = _deterministic_fallback(ticker)

        analysis_results[ticker] = result

        writer({
            "agent": AGENT_NAME, "event": "analysis_phase",
            "data": {"phase": "done", "ticker": ticker,
                     "score": result["score"],
                     "recommendation": result["recommendation"],
                     "progress_pct": int(((i + 1) / max(len(tickers), 1)) * 100)},
            "status": "running",
            "progress": (i + 1) / max(len(tickers), 1),
            "timestamp": time.time(),
        })

    duration_ms = int((time.time() - start_time) * 1000)

    writer({
        "agent": AGENT_NAME, "event": "analysis_complete",
        "data": {"nb_tickers": len(tickers), "duration_ms": duration_ms},
        "status": "completed", "progress": 1.0, "timestamp": time.time(),
    })

    return {
        "analysis_data":    analysis_results,
        "agents_completed": ["AnalysisAgent"],
    }

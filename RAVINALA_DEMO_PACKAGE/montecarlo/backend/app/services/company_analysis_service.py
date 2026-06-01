"""
services/company_analysis_service.py - company analysis orchestration.

Centralises the legacy bridge to `src/analysis` so routes and workers stay
thin and do not manage sys.path or direct analyzer imports themselves.
"""

from __future__ import annotations

import logging
from typing import Any

from app.schemas.analysis import AnalysisModule, CompanyAnalysisRequest
from app.services.legacy_quant_bridge import get_legacy_attr

logger = logging.getLogger(__name__)


def _load_analyzer_class():
    """Lazy-load the legacy analyzer from `src/analysis`."""
    return get_legacy_attr("analysis.fundamentals", "FundamentalAnalyzer")


def _normalise_modules(
    modules: list[str | AnalysisModule] | None,
) -> set[str]:
    if not modules:
        return {
            AnalysisModule.fundamentals.value,
            AnalysisModule.ratios.value,
        }
    return {
        module.value if isinstance(module, AnalysisModule) else str(module)
        for module in modules
    }


def run_company_analysis(req: CompanyAnalysisRequest) -> dict[str, Any]:
    """Execute company analysis from a validated request model."""
    return run_company_analysis_payload(ticker=req.ticker, modules=req.modules)


def run_company_analysis_payload(
    *,
    ticker: str,
    modules: list[str | AnalysisModule] | None = None,
) -> dict[str, Any]:
    """Execute requested company analysis modules and return a serialisable payload."""
    analyzer = _load_analyzer_class()
    ticker_upper = ticker.upper()
    selected_modules = _normalise_modules(modules)

    result: dict[str, Any] = {"ticker": ticker_upper, "company_name": ""}

    profile = analyzer.get_company_profile(ticker_upper)
    result["company_name"] = profile.get("name", ticker_upper)

    if AnalysisModule.fundamentals.value in selected_modules:
        result["fundamentals"] = {
            "market_cap": profile.get("market_cap"),
            "sector": profile.get("sector", ""),
            "industry": profile.get("industry", ""),
            "description": profile.get("description", ""),
        }

    if AnalysisModule.ratios.value in selected_modules:
        ratios = analyzer.get_valuation_ratios(ticker_upper)
        profit = analyzer.get_profitability_metrics(ticker_upper)
        result["ratios"] = {
            "valuation": {
                "pe_trailing": ratios.get("pe_trailing"),
                "pe_forward": ratios.get("pe_forward"),
                "peg_ratio": ratios.get("peg_ratio"),
                "pb_ratio": ratios.get("pb_ratio"),
                "ps_ratio": ratios.get("ps_ratio"),
                "ev_ebitda": ratios.get("ev_ebitda"),
            },
            "profitability": {
                "roe": profit.get("roe"),
                "roa": profit.get("roa"),
                "gross_margin": profit.get("gross_margin"),
                "operating_margin": profit.get("operating_margin"),
                "net_margin": profit.get("net_margin"),
            },
            "liquidity": {
                "current_ratio": profit.get("current_ratio"),
            },
            "leverage": {
                "debt_to_equity": profit.get("debt_to_equity"),
            },
            "efficiency": {},
        }

    if AnalysisModule.dcf.value in selected_modules:
        try:
            dcf_data = analyzer.get_dcf_valuation(ticker_upper)
            result["dcf"] = {
                "intrinsic_value": dcf_data.get("intrinsic_value"),
                "current_price": dcf_data.get("current_price"),
                "upside_pct": dcf_data.get("upside_pct"),
                "wacc": dcf_data.get("wacc"),
                "terminal_growth_rate": dcf_data.get("terminal_growth"),
                "fcf_projections": dcf_data.get("fcf_projections", []),
            }
        except Exception as exc:
            logger.warning("DCF failed for %s: %s", ticker_upper, exc)

    if AnalysisModule.peers.value in selected_modules:
        try:
            peers_data = analyzer.get_peer_comparison(ticker_upper)
            result["peers"] = {
                "peer_tickers": peers_data.get("peers", []),
                "comparison": peers_data.get("comparison", []),
            }
        except Exception as exc:
            logger.warning("Peers failed for %s: %s", ticker_upper, exc)

    return result

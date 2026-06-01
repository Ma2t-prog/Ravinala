from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.analysis import AnalysisModule, CompanyAnalysisRequest
from app.services import company_analysis_service
from app.workers.tasks import analysis_task


def test_analysis_route_no_longer_manages_src_path_directly() -> None:
    source = (BACKEND_DIR / "app" / "routes" / "analysis.py").read_text(encoding="utf-8")
    assert "sys.path.insert" not in source
    assert "run_company_analysis" in source


def test_company_analysis_service_builds_expected_payload(monkeypatch) -> None:
    class _Analyzer:
        @staticmethod
        def get_company_profile(ticker: str) -> dict:
            return {
                "name": "Apple Inc.",
                "market_cap": 3_000_000_000_000,
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "description": "Hardware and services",
            }

        @staticmethod
        def get_valuation_ratios(ticker: str) -> dict:
            return {
                "pe_trailing": 28.4,
                "pe_forward": 25.1,
                "peg_ratio": 2.1,
                "pb_ratio": 38.0,
                "ps_ratio": 7.2,
                "ev_ebitda": 20.4,
            }

        @staticmethod
        def get_profitability_metrics(ticker: str) -> dict:
            return {
                "roe": 0.41,
                "roa": 0.22,
                "gross_margin": 0.45,
                "operating_margin": 0.31,
                "net_margin": 0.25,
                "current_ratio": 1.1,
                "debt_to_equity": 1.5,
            }

        @staticmethod
        def get_dcf_valuation(ticker: str) -> dict:
            return {
                "intrinsic_value": 210.0,
                "current_price": 185.0,
                "upside_pct": 0.135,
                "wacc": 0.09,
                "terminal_growth": 0.025,
                "fcf_projections": [100.0, 110.0],
            }

        @staticmethod
        def get_peer_comparison(ticker: str) -> dict:
            return {
                "peers": ["MSFT", "GOOGL"],
                "comparison": [{"ticker": "MSFT", "pe": 32.0}],
            }

    monkeypatch.setattr(company_analysis_service, "_load_analyzer_class", lambda: _Analyzer)

    result = company_analysis_service.run_company_analysis(
        CompanyAnalysisRequest(
            ticker="aapl",
            modules=[
                AnalysisModule.fundamentals,
                AnalysisModule.ratios,
                AnalysisModule.dcf,
                AnalysisModule.peers,
            ],
        )
    )

    assert result["ticker"] == "AAPL"
    assert result["company_name"] == "Apple Inc."
    assert result["fundamentals"]["sector"] == "Technology"
    assert result["ratios"]["valuation"]["pe_trailing"] == 28.4
    assert result["dcf"]["intrinsic_value"] == 210.0
    assert result["peers"]["peer_tickers"] == ["MSFT", "GOOGL"]


def test_analysis_worker_delegates_to_service(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.company_analysis_service.run_company_analysis_payload",
        lambda ticker, modules=None: {
            "ticker": ticker.upper(),
            "company_name": "Apple Inc.",
        },
    )

    result = analysis_task.analyze_company(ticker="aapl", modules=["fundamentals"])

    assert result["status"] == "ok"
    assert result["ticker"] == "AAPL"
    assert result["company_name"] == "Apple Inc."

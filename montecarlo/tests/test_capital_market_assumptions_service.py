from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.allocator import EligibleUniverseResponse
from app.services import capital_market_assumptions_service, investor_policy_service


def test_capital_market_assumptions_service_builds_baseline_and_views() -> None:
    policy = investor_policy_service.build_investor_policy(
        {
            "amount": 100_000,
            "base_currency": "USD",
            "risk_aversion": 0.40,
            "investment_horizon_years": 5,
            "liquidity_needs": "medium",
            "objective_type": "balanced",
            "candidate_tickers": ["AAPL", "TLT"],
        }
    )
    eligibility = EligibleUniverseResponse(
        criteria={
            "heuristic_version": "v1",
            "min_market_cap": 2_000_000_000.0,
            "min_volume_avg_30d": 500_000.0,
            "allowed_asset_classes": [],
            "allowed_currencies": [],
            "require_price": True,
            "require_market_cap_for_equities": True,
            "require_volume_proxy": True,
            "require_cost_proxy": False,
        },
        eligible_assets=[
            {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "asset_class": "equity",
                "currency": "USD",
                "price": 190.0,
                "price_change_1m": 0.04,
                "price_change_1y": 0.20,
                "market_cap": 2_800_000_000_000.0,
                "volume_avg_30d": 50_000_000.0,
                "dividend_yield": 0.006,
                "volatility_1y": 0.22,
                "sharpe_1y": 0.9,
                "liquidity_tier": "high",
                "data_quality_score": 1.0,
                "cost_proxy_available": True,
                "notes": [],
            },
            {
                "ticker": "TLT",
                "name": "iShares 20+ Year Treasury Bond ETF",
                "asset_class": "fixed_income",
                "currency": "USD",
                "price": 92.0,
                "price_change_1m": -0.01,
                "price_change_1y": 0.03,
                "market_cap": 20_000_000_000.0,
                "volume_avg_30d": 8_000_000.0,
                "dividend_yield": 0.035,
                "volatility_1y": 0.14,
                "sharpe_1y": 0.2,
                "liquidity_tier": "high",
                "data_quality_score": 0.95,
                "cost_proxy_available": True,
                "notes": [],
            },
        ],
        rejected_assets=[],
        warnings=[],
    )

    result = capital_market_assumptions_service.build_capital_market_assumptions(
        eligibility=eligibility,
        policy=policy,
    )

    assert result.methodology_version == "cma_v1"
    assert len(result.assumptions) == 2
    aapl = result.assumptions[0]
    assert aapl.ticker == "AAPL"
    assert aapl.baseline_expected_return > policy.risk_free_rate_used
    assert aapl.expected_return >= aapl.baseline_expected_return
    assert aapl.confidence >= 0.5
    assert any(view.source == "historical_momentum" for view in aapl.views)
    assert any(view.source == "quality_proxy" for view in aapl.views)

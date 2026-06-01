from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.universe import InstrumentResponse
from app.services import investable_universe_service, investor_policy_service


def test_investable_universe_service_applies_explicit_liquidity_and_quality_rules(monkeypatch) -> None:
    policy = investor_policy_service.build_investor_policy(
        {
            "amount": 100_000,
            "base_currency": "USD",
            "risk_aversion": 0.70,
            "investment_horizon_years": 5,
            "liquidity_needs": "medium",
            "objective_type": "balanced",
            "allowed_asset_classes": ["equity"],
            "candidate_tickers": ["AAPL", "MSFT", "SMOL"],
        }
    )

    details = {
        "AAPL": InstrumentResponse(
            ticker="AAPL",
            name="Apple Inc.",
            asset_class="equity",
            currency="USD",
            price=190.0,
            market_cap=2_800_000_000_000.0,
            volume_avg_30d=50_000_000.0,
            volatility_1y=0.22,
        ),
        "MSFT": InstrumentResponse(
            ticker="MSFT",
            name="Microsoft Corp.",
            asset_class="equity",
            currency="USD",
            price=420.0,
            market_cap=2_500_000_000_000.0,
            volume_avg_30d=30_000_000.0,
            volatility_1y=0.20,
        ),
        "SMOL": InstrumentResponse(
            ticker="SMOL",
            name="Small Liquidity Co.",
            asset_class="equity",
            currency="USD",
            price=8.0,
            market_cap=100_000_000.0,
            volume_avg_30d=25_000.0,
            volatility_1y=0.70,
        ),
    }

    monkeypatch.setattr(
        investable_universe_service,
        "get_instrument_detail",
        lambda ticker: details.get(ticker),
    )

    result = investable_universe_service.build_eligible_universe(
        req={
            "amount": 100_000,
            "base_currency": "USD",
            "risk_aversion": 0.70,
            "investment_horizon_years": 5,
            "liquidity_needs": "medium",
            "objective_type": "balanced",
            "allowed_asset_classes": ["equity"],
            "candidate_tickers": ["AAPL", "MSFT", "SMOL"],
        },
        policy=policy,
    )

    assert [asset.ticker for asset in result.eligible_assets] == ["AAPL", "MSFT"]
    assert result.rejected_assets[0].ticker == "SMOL"
    assert "average_volume_below_threshold" in result.rejected_assets[0].rejection_reasons
    assert "market_cap_below_threshold" in result.rejected_assets[0].rejection_reasons
    assert result.criteria.min_volume_avg_30d == 500_000.0

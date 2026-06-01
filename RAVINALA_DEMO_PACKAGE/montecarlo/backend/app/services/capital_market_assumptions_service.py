"""
services/capital_market_assumptions_service.py - explicit expected-return assumptions.

This slice is intentionally honest:
- it produces a simple baseline plus transparent view adjustments
- ML predictions can be optionally fused as an additional view (confidence-weighted)
- it does not claim a full Black-Litterman engine
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.risk.conventions import CONVENTIONS
from app.schemas.allocator import (
    AssetCapitalMarketAssumption,
    CapitalMarketAssumptionsResponse,
    CapitalMarketView,
    EligibleUniverseResponse,
    InvestorPolicy,
    MLPredictionInput,
)

# Blend factor: ML view gets at most ML_BLEND_FACTOR weight at full confidence (1.0).
# At typical val_directional_accuracy of 0.55 → ml_weight = 0.55 × 0.40 = 0.22.
# CMA baseline always retains at least (1 - ML_BLEND_FACTOR) = 60% weight.
_ML_BLEND_FACTOR: float = 0.40
_ML_ANNUALIZED_CAP: float = 0.35   # max ±35% annualized from ML signal
_ML_IMPACT_CAP: float = 0.12       # blend can shift expected_return by at most ±12pp


ASSET_CLASS_PREMIUMS = {
    "equity": 0.050,
    "fixed_income": 0.015,
    "commodity": 0.020,
    "crypto": 0.080,
    "real_estate": 0.035,
    "cash": 0.000,
    "other": 0.020,
}


def _clip(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _baseline_expected_return(asset_class: str, risk_free_rate: float) -> float:
    premium = ASSET_CLASS_PREMIUMS.get(asset_class.lower(), ASSET_CLASS_PREMIUMS["other"])
    return risk_free_rate + premium


def _momentum_view(price_change_1m: float | None, price_change_1y: float | None) -> CapitalMarketView | None:
    if price_change_1m is None and price_change_1y is None:
        return None
    signal_value = 0.0
    rationales: list[str] = []
    confidence = 0.35
    if price_change_1m is not None:
        signal_value += _clip(price_change_1m * 0.25, -0.02, 0.02)
        rationales.append(f"1m momentum={price_change_1m:.2%}")
        confidence += 0.10
    if price_change_1y is not None:
        signal_value += _clip(price_change_1y * 0.15, -0.04, 0.04)
        rationales.append(f"1y trend={price_change_1y:.2%}")
        confidence += 0.15
    return CapitalMarketView(
        source="historical_momentum",
        signal="positive" if signal_value >= 0 else "negative",
        annualized_impact=round(signal_value, 4),
        confidence=_clip(confidence, 0.0, 0.75),
        rationale=", ".join(rationales),
    )


def _income_view(dividend_yield: float | None) -> CapitalMarketView | None:
    if dividend_yield is None or dividend_yield <= 0:
        return None
    impact = _clip(dividend_yield * 0.50, 0.0, 0.03)
    return CapitalMarketView(
        source="income_carry",
        signal="positive",
        annualized_impact=round(impact, 4),
        confidence=0.45,
        rationale=f"dividend_yield={dividend_yield:.2%}",
    )


def _ml_view(
    ml: MLPredictionInput,
    cma_expected_return: float,
) -> tuple[CapitalMarketView, float] | None:
    """
    Build a CapitalMarketView from an ML prediction and return (view, blended_return).

    Blend formula (documented):
        ml_annualized = clip(predicted_return × (252 / horizon_days), ±_ML_ANNUALIZED_CAP)
        ml_weight     = confidence × _ML_BLEND_FACTOR
        blended       = (1 - ml_weight) × cma_return + ml_weight × ml_annualized
        impact        = clip(blended - cma_return, ±_ML_IMPACT_CAP)

    Returns None if confidence is None/0 (legacy artifact — view skipped).
    """
    if ml.confidence is None or ml.confidence <= 0:
        return None

    ml_annualized = _clip(
        ml.predicted_return * (CONVENTIONS.ann_factor_return / max(ml.horizon_days, 1)),
        -_ML_ANNUALIZED_CAP,
        _ML_ANNUALIZED_CAP,
    )
    ml_weight = ml.confidence * _ML_BLEND_FACTOR
    blended_raw = (1.0 - ml_weight) * cma_expected_return + ml_weight * ml_annualized
    impact = _clip(blended_raw - cma_expected_return, -_ML_IMPACT_CAP, _ML_IMPACT_CAP)
    blended = cma_expected_return + impact

    direction = "positive" if ml.predicted_return >= 0 else "negative"
    view = CapitalMarketView(
        source="ml_prediction",
        signal=direction,
        annualized_impact=round(impact, 4),
        confidence=round(ml.confidence, 3),
        rationale=(
            f"ML predicted_return={ml.predicted_return:.4f} over {ml.horizon_days}d "
            f"(annualized={ml_annualized:.2%}), confidence={ml.confidence:.2f}, "
            f"ml_weight={ml_weight:.3f} (blend_factor={_ML_BLEND_FACTOR}), "
            f"source={ml.source}"
        ),
    )
    return view, round(_clip(blended, -0.20, 0.30), 4)


def _quality_view(sharpe_1y: float | None) -> CapitalMarketView | None:
    if sharpe_1y is None:
        return None
    impact = _clip(sharpe_1y * 0.01, -0.015, 0.015)
    return CapitalMarketView(
        source="quality_proxy",
        signal="positive" if impact >= 0 else "negative",
        annualized_impact=round(impact, 4),
        confidence=0.30,
        rationale=f"sharpe_1y={sharpe_1y:.2f}",
    )


def build_capital_market_assumptions(
    *,
    eligibility: EligibleUniverseResponse,
    policy: InvestorPolicy,
    ml_views: dict[str, MLPredictionInput] | None = None,
) -> CapitalMarketAssumptionsResponse:
    """
    Build explicit expected-return assumptions for eligible assets.

    When `ml_views` is provided, ML predictions are fused as a confidence-weighted
    view on top of the CMA baseline for each matching ticker.
    """
    assumptions: list[AssetCapitalMarketAssumption] = []
    warnings: list[str] = [
        "capital market assumptions v1 are explanatory and preparatory; "
        "the legacy optimizer does not yet ingest these views directly",
    ]
    if not ml_views:
        warnings.append(
            "no ML predictions provided — pass ml_predictions in the request "
            "to fuse model signals into CMA expected returns"
        )

    ml_signals_applied = 0
    ml_index: dict[str, MLPredictionInput] = ml_views or {}

    for asset in eligibility.eligible_assets:
        baseline = _baseline_expected_return(asset.asset_class, policy.risk_free_rate_used)
        market_views = [
            view
            for view in (
                _momentum_view(asset.price_change_1m, asset.price_change_1y),
                _income_view(asset.dividend_yield),
                _quality_view(asset.sharpe_1y),
            )
            if view is not None
        ]
        view_adjustment = sum(view.annualized_impact for view in market_views)
        cma_expected = _clip(baseline + view_adjustment, -0.20, 0.30)

        # ── ML view fusion ────────────────────────────────────────────────────
        all_views = list(market_views)
        final_expected = cma_expected
        ml_signal = ml_index.get(asset.ticker)
        if ml_signal is not None:
            ml_result = _ml_view(ml_signal, cma_expected)
            if ml_result is not None:
                ml_view_obj, final_expected = ml_result
                all_views.append(ml_view_obj)
                ml_signals_applied += 1

        confidence = _clip(
            0.30
            + asset.data_quality_score * 0.30
            + sum(view.confidence for view in all_views) * 0.15,
            0.20,
            0.85,
        )
        assumption_warnings: list[str] = []
        if not market_views:
            assumption_warnings.append("no enrichment views available beyond the asset-class baseline")
        if asset.volatility_1y is None:
            assumption_warnings.append("volatility proxy missing; risk-aware calibration remains partial")

        methodology = "baseline_risk_free_plus_asset_class_premium_with_light_views_v1"
        if ml_signal is not None and ml_signal.confidence:
            methodology = (
                "baseline_risk_free_plus_asset_class_premium_with_light_views_and_ml_blend_v1"
            )

        assumptions.append(
            AssetCapitalMarketAssumption(
                ticker=asset.ticker,
                name=asset.name,
                asset_class=asset.asset_class,
                baseline_expected_return=round(baseline, 4),
                expected_return=round(final_expected, 4),
                confidence=round(confidence, 2),
                volatility_proxy=asset.volatility_1y,
                methodology=methodology,
                views=all_views,
                warnings=assumption_warnings,
            )
        )

    return CapitalMarketAssumptionsResponse(
        methodology_version="cma_v1",
        risk_free_rate_used=policy.risk_free_rate_used,
        investment_horizon_years=policy.investment_horizon_years,
        assumptions=assumptions,
        warnings=warnings,
        ml_signals_applied=ml_signals_applied,
    )


__all__ = ["build_capital_market_assumptions"]

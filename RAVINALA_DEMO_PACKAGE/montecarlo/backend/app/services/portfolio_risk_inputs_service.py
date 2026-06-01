"""
services/portfolio_risk_inputs_service.py - canonical allocator risk-input payloads.

Builds the historical, covariance-based risk payload used by the allocator
pipeline before optimization. This slice is intentionally explicit about its
limits: it is not a factor model, not benchmark-relative risk, and not a full
stress engine.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from app.risk.conventions import CONVENTIONS
from app.schemas.allocator import (
    AllocationCandidateRiskDiagnostics,
    AssetRiskInput,
    CorrelationPair,
    EligibleUniverseResponse,
    InvestorPolicy,
    PortfolioRiskBudget,
    PortfolioRiskInputsResponse,
    RiskGovernanceSummary,
    UniverseRiskDiagnostics,
)
from app.services.portfolio_optimization_service import (
    covariance_estimator_name,
    load_market_risk_inputs_frame,
)

_METHODOLOGY_VERSION = "portfolio_risk_inputs_v1"
_RISK_MODEL_TYPE = "historical_covariance_allocator_v1"
_DATA_SOURCE = "yfinance"


def _to_float(value: float | np.floating | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _max_drawdown_proxy(returns: pd.Series) -> float | None:
    clean = returns.dropna()
    if clean.empty:
        return None
    equity = (1.0 + clean).cumprod()
    drawdowns = (equity / equity.cummax()) - 1.0
    return float(abs(drawdowns.min()))


def _downside_volatility(returns: pd.Series) -> float | None:
    clean = returns.dropna()
    if clean.empty:
        return None
    downside = clean[clean < 0]
    if downside.empty:
        return 0.0
    return float(downside.std() * CONVENTIONS.ann_factor_vol)


def _tail_loss_metric(returns: pd.Series, confidence: float = 0.95) -> tuple[float | None, float | None]:
    clean = returns.dropna()
    if len(clean) < 20:
        return None, None
    threshold = float(np.percentile(clean, (1.0 - confidence) * 100.0))
    tail = clean[clean <= threshold]
    var_loss = float(-threshold)
    cvar_loss = float(-tail.mean()) if len(tail) else None
    return var_loss, cvar_loss


def _matrix_to_nested_dict(frame: pd.DataFrame, tickers: Iterable[str]) -> dict[str, dict[str, float]]:
    ordered = list(tickers)
    trimmed = frame.loc[ordered, ordered]
    return {
        row: {column: float(trimmed.loc[row, column]) for column in ordered}
        for row in ordered
    }


def _top_correlation_pairs(correlation_matrix: pd.DataFrame, *, limit: int = 5) -> list[CorrelationPair]:
    pairs: list[CorrelationPair] = []
    columns = list(correlation_matrix.columns)
    for left_idx, left_ticker in enumerate(columns):
        for right_ticker in columns[left_idx + 1 :]:
            corr = float(correlation_matrix.loc[left_ticker, right_ticker])
            pairs.append(
                CorrelationPair(
                    left_ticker=left_ticker,
                    right_ticker=right_ticker,
                    correlation=corr,
                    absolute_correlation=abs(corr),
                )
            )
    pairs.sort(key=lambda item: item.absolute_correlation, reverse=True)
    return pairs[:limit]


def _concentration_limit(*, asset_count: int, risk_profile: str) -> tuple[float, float]:
    base_target_names = {
        "conservative": 8.0,
        "moderate": 6.0,
        "aggressive": 5.0,
    }.get(risk_profile, 6.0)
    equal_weight_floor = max(float(asset_count), 1.0)
    target_names = min(equal_weight_floor, base_target_names) if asset_count else base_target_names
    hhi_limit = max(1.0 / max(target_names, 1.0), 1.0 / max(equal_weight_floor, 1.0))
    return float(hhi_limit), float(1.0 / hhi_limit) if hhi_limit > 0 else 0.0


def _risk_budget(*, policy: InvestorPolicy, asset_count: int) -> PortfolioRiskBudget:
    concentration_hhi_soft_limit, effective_name_floor = _concentration_limit(
        asset_count=asset_count,
        risk_profile=policy.risk_profile.value,
    )
    return PortfolioRiskBudget(
        target_volatility=policy.target_volatility,
        max_drawdown_tolerance=policy.max_drawdown_tolerance,
        max_single_name_weight=policy.max_weight,
        min_weight=policy.min_weight,
        cash_buffer_weight=policy.cash_buffer_weight,
        concentration_hhi_soft_limit=concentration_hhi_soft_limit,
        effective_name_floor=effective_name_floor,
    )


def build_portfolio_risk_inputs(
    *,
    eligibility: EligibleUniverseResponse,
    policy: InvestorPolicy,
) -> PortfolioRiskInputsResponse:
    """
    Build a canonical allocator risk payload from the eligible universe.

    This slice stays honest: historical covariance, drawdown proxies, and
    correlation diagnostics only. No factor model or benchmark-relative risk.
    """
    requested_tickers = [asset.ticker for asset in eligibility.eligible_assets]
    if len(requested_tickers) < 2:
        raise ValueError("at least two eligible assets are required to build portfolio risk inputs")

    returns, individual_vols, cov_matrix = load_market_risk_inputs_frame(
        tickers=requested_tickers,
        lookback_days=policy.lookback_days,
    )
    used_tickers = list(returns.columns)
    dropped_tickers = [ticker for ticker in requested_tickers if ticker not in used_tickers]
    if len(used_tickers) < 2:
        raise ValueError("risk inputs require at least two assets with usable return history")

    correlation_matrix = returns.corr()
    eligibility_by_ticker = {asset.ticker: asset for asset in eligibility.eligible_assets}
    asset_risk_inputs: list[AssetRiskInput] = []
    warnings = list(eligibility.warnings)

    for ticker in used_tickers:
        asset = eligibility_by_ticker[ticker]
        asset_returns = returns[ticker]
        var_95_1d, cvar_95_1d = _tail_loss_metric(asset_returns)
        asset_risk_inputs.append(
            AssetRiskInput(
                ticker=ticker,
                name=asset.name,
                asset_class=asset.asset_class,
                annualized_volatility=float(individual_vols[ticker]),
                downside_volatility=_downside_volatility(asset_returns),
                max_drawdown_proxy=_max_drawdown_proxy(asset_returns),
                var_95_1d=var_95_1d,
                cvar_95_1d=cvar_95_1d,
                data_points_used=int(asset_returns.dropna().shape[0]),
            )
        )

    if dropped_tickers:
        warnings.append(
            "some eligible tickers were dropped from the risk model because sufficient return history was unavailable: "
            + ", ".join(dropped_tickers)
        )
    if len(returns) < policy.lookback_days:
        warnings.append(
            "historical risk inputs use a shorter effective history than requested lookback_days because provider data was shorter"
        )

    corr_values = correlation_matrix.where(~np.eye(len(correlation_matrix), dtype=bool)).stack()
    average_pairwise_correlation = float(corr_values.mean()) if not corr_values.empty else None
    max_pairwise_correlation = float(corr_values.abs().max()) if not corr_values.empty else None
    volatility_dispersion = (
        float(individual_vols.max() - individual_vols.min())
        if not individual_vols.empty
        else None
    )

    return PortfolioRiskInputsResponse(
        methodology_version=_METHODOLOGY_VERSION,
        risk_model_type=_RISK_MODEL_TYPE,
        data_source=_DATA_SOURCE,
        lookback_days=policy.lookback_days,
        observation_count=int(len(returns)),
        annualization_factor=CONVENTIONS.trading_days_per_year,
        risk_free_rate_used=policy.risk_free_rate_used,
        benchmark_preference=policy.benchmark_preference,
        tickers_used=used_tickers,
        dropped_tickers=dropped_tickers,
        asset_risk_inputs=asset_risk_inputs,
        covariance_matrix=_matrix_to_nested_dict(cov_matrix, used_tickers),
        correlation_matrix=_matrix_to_nested_dict(correlation_matrix, used_tickers),
        top_correlation_pairs=_top_correlation_pairs(correlation_matrix),
        risk_budget=_risk_budget(policy=policy, asset_count=len(used_tickers)),
        universe_risk_diagnostics=UniverseRiskDiagnostics(
            asset_count=len(used_tickers),
            observation_count=int(len(returns)),
            average_pairwise_correlation=average_pairwise_correlation,
            max_pairwise_correlation=max_pairwise_correlation,
            volatility_dispersion=volatility_dispersion,
        ),
        governance_summary=RiskGovernanceSummary(
            model_type=_RISK_MODEL_TYPE,
            covariance_estimator=covariance_estimator_name(),
            concentration_support="post_optimization_only",
            scenario_support="deferred",
            limitations=[
                "historical covariance only; no factor model, no tracking-error model and no benchmark-relative decomposition",
                "concentration is evaluated after candidate portfolios are generated, not as a pre-optimization portfolio fact",
                "allocator stress/scenario engine remains deferred in this slice",
            ],
        ),
        warnings=warnings,
    )


def build_candidate_risk_diagnostics(
    *,
    candidate_weights: dict[str, float],
    risk_inputs: PortfolioRiskInputsResponse,
) -> AllocationCandidateRiskDiagnostics:
    """Compute post-optimization concentration and budget diagnostics for one candidate."""
    ordered = [ticker for ticker in risk_inputs.tickers_used if ticker in candidate_weights]
    if not ordered:
        return AllocationCandidateRiskDiagnostics()

    weights = np.array([float(candidate_weights[ticker]) for ticker in ordered], dtype=float)
    covariance = pd.DataFrame(risk_inputs.covariance_matrix).loc[ordered, ordered]
    portfolio_volatility = float(np.sqrt(weights @ covariance.values @ weights))
    concentration_hhi = float(np.sum(np.square(weights)))
    effective_number_of_names = float(1.0 / concentration_hhi) if concentration_hhi > 0 else None
    max_single_name_weight = float(weights.max()) if len(weights) else None

    asset_drawdown_map = {
        item.ticker: float(item.max_drawdown_proxy or 0.0)
        for item in risk_inputs.asset_risk_inputs
    }
    weighted_drawdown_proxy = float(
        sum(float(candidate_weights[ticker]) * asset_drawdown_map.get(ticker, 0.0) for ticker in ordered)
    )

    budget = risk_inputs.risk_budget
    breaches: list[str] = []
    if max_single_name_weight is not None and max_single_name_weight > budget.max_single_name_weight + 1e-9:
        breaches.append("max_single_name_weight")
    if concentration_hhi > budget.concentration_hhi_soft_limit + 1e-9:
        breaches.append("concentration_hhi_soft_limit")
    if budget.target_volatility is not None and portfolio_volatility > budget.target_volatility + 1e-9:
        breaches.append("target_volatility")
    if weighted_drawdown_proxy > budget.max_drawdown_tolerance + 1e-9:
        breaches.append("weighted_drawdown_proxy")

    # Q5.4 — Governance: standard corrective actions per breach type
    _BREACH_ACTIONS: dict[str, str] = {
        "max_single_name_weight": (
            "Reduce the largest position to at or below the max_single_name_weight limit; "
            "reallocate excess weight to remaining eligible tickers."
        ),
        "concentration_hhi_soft_limit": (
            "Increase diversification: add more tickers or cap top weights; "
            "target HHI below the soft limit."
        ),
        "target_volatility": (
            "Reduce exposure to high-volatility assets or increase allocation to lower-risk "
            "asset classes (e.g. fixed income, cash) to bring portfolio volatility within target."
        ),
        "weighted_drawdown_proxy": (
            "Review assets with high historical drawdown; consider reducing or replacing "
            "positions with elevated max_drawdown_proxy values."
        ),
    }
    breach_recommended_actions = {
        breach: _BREACH_ACTIONS[breach]
        for breach in breaches
        if breach in _BREACH_ACTIONS
    }

    return AllocationCandidateRiskDiagnostics(
        portfolio_volatility=portfolio_volatility,
        concentration_hhi=concentration_hhi,
        effective_number_of_names=effective_number_of_names,
        max_single_name_weight=max_single_name_weight,
        weighted_drawdown_proxy=weighted_drawdown_proxy,
        target_volatility_gap=(
            portfolio_volatility - budget.target_volatility
            if budget.target_volatility is not None
            else None
        ),
        risk_budget_breaches=breaches,
        breach_recommended_actions=breach_recommended_actions,
    )


__all__ = [
    "build_candidate_risk_diagnostics",
    "build_portfolio_risk_inputs",
]

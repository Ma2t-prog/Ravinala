"""
services/portfolio_optimization_service.py - portfolio optimization orchestration.

Owns two paths:
- legacy optimizer bridge for `/portfolio/optimize`
- allocator-only optimization from explicit expected-return assumptions
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from app.providers.yfinance_adapter import YFinanceProvider
from app.risk.conventions import CONVENTIONS
from app.schemas.allocator import AssetClassConstraintInput
from app.schemas.portfolio import AssetWeight, EfficientFrontierPoint, OptimizeRequest
from app.services.legacy_quant_bridge import get_legacy_attr

try:
    from sklearn.covariance import LedoitWolf

    _HAS_SKLEARN = True
except ImportError:  # pragma: no cover - optional dependency
    _HAS_SKLEARN = False


def _load_optimizer():
    """Lazy-load the legacy optimizer from `src/genesix`."""
    optimizer_cls = get_legacy_attr("genesix.optimizer", "PortfolioOptimizer")
    return optimizer_cls()


def _period_for_lookback(lookback_days: int) -> str:
    if lookback_days <= 252:
        return "2y"
    if lookback_days <= 504:
        return "3y"
    return "5y"


def _extract_close_prices(data: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    if isinstance(data.columns, pd.MultiIndex):
        first_level = data.columns.get_level_values(0)
        if "Close" in first_level:
            closes = data["Close"].copy()
        elif "Adj Close" in first_level:
            closes = data["Adj Close"].copy()
        else:
            raise ValueError("Close prices are unavailable in provider payload")
    else:
        if "Close" in data.columns:
            closes = data[["Close"]].rename(columns={"Close": tickers[0]})
        else:
            closes = data.copy()

    if isinstance(closes, pd.Series):
        closes = closes.to_frame(name=tickers[0])
    if isinstance(closes.columns, pd.MultiIndex):
        closes.columns = closes.columns.get_level_values(-1)
    return closes


def covariance_estimator_name() -> str:
    return "ledoit_wolf" if _HAS_SKLEARN else "sample_covariance"


def load_market_risk_inputs_frame(
    *,
    tickers: list[str],
    lookback_days: int,
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    provider = YFinanceProvider()
    raw = provider.fetch_prices_batch(tickers, period=_period_for_lookback(lookback_days))
    closes = _extract_close_prices(raw, tickers)
    closes = closes.loc[:, [ticker for ticker in tickers if ticker in closes.columns]]
    closes = closes.tail(lookback_days + 1).dropna(how="all")
    if closes.empty:
        raise ValueError("No usable close prices returned for optimization")

    returns = closes.pct_change().dropna(how="any")
    if returns.empty or len(returns) < 20:
        raise ValueError("Insufficient return history for optimization")

    individual_vols = returns.std() * CONVENTIONS.ann_factor_vol
    if _HAS_SKLEARN and len(returns) > len(returns.columns):
        shrink = LedoitWolf().fit(returns.values)
        cov_matrix = pd.DataFrame(
            shrink.covariance_ * CONVENTIONS.trading_days_per_year,
            index=returns.columns,
            columns=returns.columns,
        )
    else:
        cov_matrix = returns.cov() * CONVENTIONS.trading_days_per_year
    return returns, individual_vols, cov_matrix


def _generate_efficient_frontier(
    expected_returns: pd.Series,
    cov_matrix: pd.DataFrame,
    risk_free_rate: float,
    bounds: tuple[tuple[float, float], ...],
    *,
    n_points: int = 25,
) -> list[EfficientFrontierPoint]:
    frontier: list[EfficientFrontierPoint] = []
    lower = float(expected_returns.min()) * 0.75
    upper = float(expected_returns.max()) * 1.10
    if lower >= upper:
        upper = lower + 0.01

    for target_return in np.linspace(lower, upper, n_points):
        constraints = [
            {"type": "eq", "fun": lambda x: np.sum(x) - 1},
            {"type": "eq", "fun": lambda x, tr=target_return: x @ expected_returns.values - tr},
        ]
        result = minimize(
            lambda x: float(x @ cov_matrix.values @ x),
            np.ones(len(expected_returns)) / len(expected_returns),
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 300},
        )
        if not result.success:
            continue
        portfolio_vol = float(np.sqrt(result.x @ cov_matrix.values @ result.x))
        frontier.append(
            EfficientFrontierPoint(
                expected_return=target_return * 100,
                volatility=portfolio_vol * 100,
            )
        )
    return frontier


def _optimize_from_expected_returns(
    *,
    expected_returns: pd.Series,
    cov_matrix: pd.DataFrame,
    individual_vols: pd.Series,
    objective: str,
    risk_free_rate_used: float,
    max_weight: float,
    min_weight: float,
) -> dict[str, Any]:
    n_assets = len(expected_returns)
    bounds = tuple((min_weight, max_weight) for _ in range(n_assets))
    x0 = np.array([1.0 / n_assets] * n_assets)
    constraints = [{"type": "eq", "fun": lambda x: np.sum(x) - 1}]

    if objective == "min_variance":
        objective_fn = lambda x: float(x @ cov_matrix.values @ x)
    elif objective == "risk_parity":
        def objective_fn(x):
            portfolio_vol = np.sqrt(x @ cov_matrix.values @ x)
            if portfolio_vol <= 0:
                return 1e10
            marginal_contrib = cov_matrix.values @ x / portfolio_vol
            risk_contrib = x * marginal_contrib
            return float(np.sum((risk_contrib - np.mean(risk_contrib)) ** 2))
    else:
        def objective_fn(x):
            portfolio_return = float(x @ expected_returns.values)
            portfolio_vol = float(np.sqrt(x @ cov_matrix.values @ x))
            if portfolio_vol <= 0:
                return 1e10
            return -((portfolio_return - risk_free_rate_used) / portfolio_vol)

    result = minimize(
        objective_fn,
        x0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 1000},
    )
    if not result.success:
        raise ValueError(f"assumption-aware optimization failed: {result.message}")

    weights = result.x
    portfolio_return = float(weights @ expected_returns.values)
    portfolio_vol = float(np.sqrt(weights @ cov_matrix.values @ weights))
    sharpe = (
        (portfolio_return - risk_free_rate_used) / portfolio_vol
        if portfolio_vol > 0
        else 0.0
    )
    diversification_ratio = (
        float(weights @ individual_vols.values) / portfolio_vol
        if portfolio_vol > 0
        else 1.0
    )

    asset_details = []
    for ticker, weight in zip(expected_returns.index, weights):
        marginal_contrib = cov_matrix.loc[ticker].values @ weights
        risk_contrib = float(weight * marginal_contrib / portfolio_vol) if portfolio_vol > 0 else 0.0
        asset_details.append(
            {
                "ticker": ticker,
                "weight": float(weight),
                "expected_return": float(expected_returns[ticker] * 100),
                "volatility": float(individual_vols[ticker] * 100),
                "risk_contribution": risk_contrib * 100,
            }
        )

    return {
        "weights": {ticker: float(weight) for ticker, weight in zip(expected_returns.index, weights)},
        "expected_return": portfolio_return * 100,
        "expected_volatility": portfolio_vol * 100,
        "sharpe_ratio": sharpe,
        "diversification_ratio": diversification_ratio,
        "efficient_frontier": {
            "points": [
                {
                    "return": point.expected_return,
                    "volatility": point.volatility,
                }
                for point in _generate_efficient_frontier(
                    expected_returns,
                    cov_matrix,
                    risk_free_rate_used,
                    bounds,
                )
            ]
        },
        "asset_details": asset_details,
    }


def _normalize_optimization_result(
    result: dict[str, Any],
    *,
    objective: str,
    risk_free_rate_used: float,
) -> dict[str, Any]:
    weights = []
    for asset_detail in result.get("asset_details", []):
        weights.append(
            AssetWeight(
                ticker=asset_detail["ticker"],
                weight=asset_detail["weight"],
                expected_return=asset_detail.get("expected_return"),
                volatility=asset_detail.get("volatility"),
            )
        )

    if not weights and "weights" in result:
        for ticker, weight in result["weights"].items():
            weights.append(AssetWeight(ticker=ticker, weight=weight))

    frontier = []
    for point in result.get("efficient_frontier", {}).get("points", []):
        frontier.append(
            EfficientFrontierPoint(
                expected_return=point.get("return", point.get("expected_return", 0)),
                volatility=point.get("volatility", point.get("risk", 0)),
            )
        )

    return {
        "objective": objective,
        "weights": weights,
        "expected_return": result.get("expected_return", 0),
        "expected_volatility": result.get("expected_volatility", 0),
        "sharpe_ratio": result.get("sharpe_ratio", 0),
        "risk_free_rate_used": risk_free_rate_used,
        "diversification_ratio": result.get("diversification_ratio"),
        "efficient_frontier": frontier,
    }


def _weight_map_from_payload(weights: list[AssetWeight] | list[dict[str, Any]]) -> dict[str, float]:
    weight_map: dict[str, float] = {}
    for item in weights:
        ticker = item.ticker if hasattr(item, "ticker") else item["ticker"]
        weight = float(item.weight if hasattr(item, "weight") else item["weight"])
        if weight > 0:
            weight_map[str(ticker)] = weight
    return weight_map


def _risk_inputs_field(risk_inputs, name: str, default=None):
    if isinstance(risk_inputs, dict):
        return risk_inputs.get(name, default)
    return getattr(risk_inputs, name, default)


def _normalize_weight_map(weight_map: dict[str, float]) -> dict[str, float]:
    positive = {ticker: float(weight) for ticker, weight in weight_map.items() if float(weight) > 1e-12}
    total = float(sum(positive.values()))
    if total <= 0:
        raise ValueError("constraint-adjusted candidate lost all positive weights")
    return {ticker: weight / total for ticker, weight in positive.items()}


def _redistribute_weight(
    *,
    weight_map: dict[str, float],
    recipients: list[str],
    amount: float,
    max_weight: float,
) -> dict[str, float]:
    if amount <= 1e-12:
        return weight_map

    updated = dict(weight_map)
    remaining = float(amount)
    eligible = list(recipients)
    while remaining > 1e-10 and eligible:
        current_total = sum(max(updated.get(ticker, 0.0), 0.0) for ticker in eligible)
        if current_total <= 0:
            shares = {ticker: 1.0 / len(eligible) for ticker in eligible}
        else:
            shares = {
                ticker: max(updated.get(ticker, 0.0), 0.0) / current_total
                for ticker in eligible
            }

        applied = 0.0
        next_round: list[str] = []
        for ticker in eligible:
            capacity = max(0.0, max_weight - updated.get(ticker, 0.0))
            if capacity <= 1e-12:
                continue
            increment = min(capacity, remaining * shares[ticker])
            if increment > 0:
                updated[ticker] = updated.get(ticker, 0.0) + increment
                applied += increment
            if max_weight - updated.get(ticker, 0.0) > 1e-12:
                next_round.append(ticker)
        if applied <= 1e-12:
            break
        remaining -= applied
        eligible = next_round

    if remaining > 1e-8:
        raise ValueError("allocator constraints are infeasible under current max_weight bounds")
    return updated


def _remove_weight(
    *,
    weight_map: dict[str, float],
    donors: list[str],
    amount: float,
    min_weight: float,
) -> dict[str, float]:
    if amount <= 1e-12:
        return weight_map

    updated = dict(weight_map)
    remaining = float(amount)
    eligible = list(donors)
    while remaining > 1e-10 and eligible:
        removable_total = sum(max(updated.get(ticker, 0.0) - min_weight, 0.0) for ticker in eligible)
        if removable_total <= 1e-12:
            break
        applied = 0.0
        next_round: list[str] = []
        for ticker in eligible:
            removable = max(updated.get(ticker, 0.0) - min_weight, 0.0)
            if removable <= 1e-12:
                continue
            decrement = min(removable, remaining * (removable / removable_total))
            if decrement > 0:
                updated[ticker] = updated.get(ticker, 0.0) - decrement
                applied += decrement
            if updated.get(ticker, 0.0) - min_weight > 1e-12:
                next_round.append(ticker)
        if applied <= 1e-12:
            break
        remaining -= applied
        eligible = next_round

    if remaining > 1e-8:
        raise ValueError("allocator constraints are infeasible under current min_weight bounds")
    return updated


def _enforce_max_selected_assets(
    *,
    weight_map: dict[str, float],
    max_selected_assets: int | None,
    asset_class_constraints: list[AssetClassConstraintInput] | None = None,
    asset_class_by_ticker: dict[str, str] | None = None,
) -> tuple[dict[str, float], bool]:
    normalized = _normalize_weight_map(weight_map)
    if max_selected_assets is None or len(normalized) <= max_selected_assets:
        return normalized, False
    ordered = [ticker for ticker, _ in sorted(normalized.items(), key=lambda item: item[1], reverse=True)]
    normalized_asset_class_by_ticker = {
        str(ticker): str(asset_class).lower()
        for ticker, asset_class in (asset_class_by_ticker or {}).items()
    }

    protected: list[str] = []
    for constraint in asset_class_constraints or []:
        asset_class = constraint.asset_class
        class_members = [
            ticker
            for ticker in ordered
            if normalized_asset_class_by_ticker.get(ticker) == asset_class
        ]
        if constraint.min_weight is not None and class_members:
            protected.append(class_members[0])
        if constraint.max_weight is not None and constraint.max_weight < 1.0:
            outside_members = [
                ticker
                for ticker in ordered
                if normalized_asset_class_by_ticker.get(ticker) != asset_class
            ]
            if outside_members:
                protected.append(outside_members[0])

    keep_order: list[str] = []
    seen: set[str] = set()
    for ticker in protected + ordered:
        if ticker in seen:
            continue
        keep_order.append(ticker)
        seen.add(ticker)
        if len(keep_order) >= max_selected_assets:
            break

    keep = {ticker: normalized[ticker] for ticker in keep_order}
    return _normalize_weight_map(keep), True


def _enforce_asset_class_constraints(
    *,
    weight_map: dict[str, float],
    asset_class_constraints: list[AssetClassConstraintInput],
    asset_class_by_ticker: dict[str, str],
    max_weight: float,
    min_weight: float,
) -> tuple[dict[str, float], list[str]]:
    updated = _normalize_weight_map(weight_map)
    applied: list[str] = []
    if not asset_class_constraints:
        return updated, applied

    constraint_map = {item.asset_class: item for item in asset_class_constraints}

    for asset_class, constraint in constraint_map.items():
        class_members = [ticker for ticker, cls in asset_class_by_ticker.items() if cls == asset_class and ticker in updated]
        other_members = [ticker for ticker in updated if ticker not in class_members]
        class_weight = float(sum(updated.get(ticker, 0.0) for ticker in class_members))

        if constraint.max_weight is not None and class_weight > constraint.max_weight + 1e-9:
            if not class_members:
                raise ValueError(f"asset class max constraint for '{asset_class}' is infeasible without eligible assets")
            target = float(constraint.max_weight)
            scale = target / class_weight if class_weight > 0 else 0.0
            before = dict(updated)
            for ticker in class_members:
                updated[ticker] = updated[ticker] * scale
            released = float(sum(before[ticker] - updated[ticker] for ticker in class_members))
            updated = _redistribute_weight(
                weight_map=updated,
                recipients=other_members,
                amount=released,
                max_weight=max_weight,
            )
            applied.append(f"asset_class_max:{asset_class}")

        class_weight = float(sum(updated.get(ticker, 0.0) for ticker in class_members))
        if constraint.min_weight is not None and class_weight < constraint.min_weight - 1e-9:
            if not class_members:
                raise ValueError(f"asset class min constraint for '{asset_class}' is infeasible without eligible assets")
            needed = float(constraint.min_weight - class_weight)
            updated = _remove_weight(
                weight_map=updated,
                donors=other_members,
                amount=needed,
                min_weight=min_weight,
            )
            updated = _redistribute_weight(
                weight_map=updated,
                recipients=class_members,
                amount=needed,
                max_weight=max_weight,
            )
            applied.append(f"asset_class_min:{asset_class}")

    return _normalize_weight_map(updated), applied


def _evaluate_weight_map(
    *,
    weight_map: dict[str, float],
    ordered_tickers: list[str],
    expected_returns_series: pd.Series,
    covariance_frame: pd.DataFrame,
    individual_vols: pd.Series,
    objective: str,
    risk_free_rate_used: float,
) -> dict[str, Any]:
    weights = np.array([float(weight_map[ticker]) for ticker in ordered_tickers], dtype=float)
    portfolio_return = float(weights @ expected_returns_series.loc[ordered_tickers].values)
    portfolio_vol = float(np.sqrt(weights @ covariance_frame.loc[ordered_tickers, ordered_tickers].values @ weights))
    sharpe = ((portfolio_return - risk_free_rate_used) / portfolio_vol) if portfolio_vol > 0 else 0.0
    diversification_ratio = (
        float(weights @ individual_vols.loc[ordered_tickers].values) / portfolio_vol
        if portfolio_vol > 0
        else 1.0
    )
    asset_details = [
        {
            "ticker": ticker,
            "weight": float(weight_map[ticker]),
            "expected_return": float(expected_returns_series.loc[ticker] * 100),
            "volatility": float(individual_vols.loc[ticker] * 100),
        }
        for ticker in ordered_tickers
        if weight_map.get(ticker, 0.0) > 0
    ]
    return {
        "objective": objective,
        "weights": asset_details,
        "expected_return": portfolio_return * 100,
        "expected_volatility": portfolio_vol * 100,
        "sharpe_ratio": sharpe,
        "risk_free_rate_used": risk_free_rate_used,
        "diversification_ratio": diversification_ratio,
    }


def _apply_allocator_constraints(
    *,
    payload: dict[str, Any],
    expected_returns: dict[str, float],
    risk_inputs,
    objective: str,
    risk_free_rate_used: float,
    max_weight: float,
    min_weight: float,
    max_selected_assets: int | None,
    asset_class_constraints: list[AssetClassConstraintInput],
    asset_class_by_ticker: dict[str, str],
) -> tuple[dict[str, Any], list[str]]:
    weight_map = _weight_map_from_payload(payload.get("weights", []))
    adjusted_map, cardinality_applied = _enforce_max_selected_assets(
        weight_map=weight_map,
        max_selected_assets=max_selected_assets,
        asset_class_constraints=asset_class_constraints,
        asset_class_by_ticker=asset_class_by_ticker,
    )
    adjusted_map, asset_class_applied = _enforce_asset_class_constraints(
        weight_map=adjusted_map,
        asset_class_constraints=asset_class_constraints,
        asset_class_by_ticker=asset_class_by_ticker,
        max_weight=max_weight,
        min_weight=min_weight,
    )

    ordered_tickers = [ticker for ticker in payload.get("weights", []) if False]
    # preserve the original order of candidate weights while filtering to kept names
    original_order = [
        item.ticker if hasattr(item, "ticker") else item["ticker"]
        for item in payload.get("weights", [])
    ]
    ordered_tickers = [ticker for ticker in original_order if ticker in adjusted_map]
    if len(ordered_tickers) < 2:
        raise ValueError("constraint-adjusted candidate lost too many assets to remain allocable")

    expected_returns_series = pd.Series(
        {ticker: float(expected_returns[ticker]) for ticker in ordered_tickers},
        dtype=float,
    )
    covariance_frame = pd.DataFrame(_risk_inputs_field(risk_inputs, "covariance_matrix", {})).loc[
        ordered_tickers, ordered_tickers
    ]
    volatility_map = {
        (asset["ticker"] if isinstance(asset, dict) else asset.ticker): float(
            asset["annualized_volatility"] if isinstance(asset, dict) else asset.annualized_volatility
        )
        for asset in _risk_inputs_field(risk_inputs, "asset_risk_inputs", [])
        if (asset["ticker"] if isinstance(asset, dict) else asset.ticker) in ordered_tickers
    }
    individual_vols = pd.Series({ticker: volatility_map[ticker] for ticker in ordered_tickers}, dtype=float)
    reevaluated = _evaluate_weight_map(
        weight_map=adjusted_map,
        ordered_tickers=ordered_tickers,
        expected_returns_series=expected_returns_series,
        covariance_frame=covariance_frame,
        individual_vols=individual_vols,
        objective=objective,
        risk_free_rate_used=risk_free_rate_used,
    )
    reevaluated["efficient_frontier"] = payload.get("efficient_frontier", [])

    applied_constraints: list[str] = []
    if cardinality_applied:
        applied_constraints.append("max_selected_assets")
    applied_constraints.extend(asset_class_applied)
    return reevaluated, applied_constraints


def run_portfolio_optimization(req: OptimizeRequest) -> dict[str, Any]:
    """Run optimization from a validated request model."""
    risk_free_rate_used = (
        req.risk_free_rate
        if req.risk_free_rate is not None
        else CONVENTIONS.risk_free_rate
    )
    return run_portfolio_optimization_payload(
        tickers=req.tickers,
        objective=req.objective.value,
        risk_free_rate=risk_free_rate_used,
        lookback_days=req.lookback_days,
        max_weight=req.max_weight,
        min_weight=req.min_weight,
    )


def run_portfolio_optimization_payload(
    *,
    tickers: list[str],
    objective: str = "max_sharpe",
    risk_free_rate: float | None = None,
    lookback_days: int = 252,
    max_weight: float = 1.0,
    min_weight: float = 0.0,
) -> dict[str, Any]:
    """Run legacy optimization and return a normalized serialisable payload."""
    optimizer = _load_optimizer()
    risk_free_rate_used = (
        risk_free_rate
        if risk_free_rate is not None
        else CONVENTIONS.risk_free_rate
    )
    constraints = {
        "max_weight": max_weight,
        "min_weight": min_weight,
    }

    result = optimizer.optimize(
        assets=tickers,
        objective=objective,
        constraints=constraints,
        risk_free_rate=risk_free_rate_used,
        lookback_days=lookback_days,
    )

    return _normalize_optimization_result(
        result,
        objective=objective,
        risk_free_rate_used=risk_free_rate_used,
    )


def run_portfolio_optimization_with_assumptions_payload(
    *,
    tickers: list[str],
    expected_returns: dict[str, float],
    objective: str = "max_sharpe",
    risk_free_rate: float | None = None,
    lookback_days: int = 252,
    max_weight: float = 1.0,
    min_weight: float = 0.0,
) -> dict[str, Any]:
    """
    Run allocator optimization from explicit expected-return assumptions.

    `expected_returns` must be annualized decimals, e.g. `0.08` for 8%.
    """
    ordered_tickers = [ticker for ticker in tickers if ticker in expected_returns]
    if len(ordered_tickers) < 2:
        raise ValueError("at least two tickers with explicit expected returns are required")

    risk_free_rate_used = (
        risk_free_rate
        if risk_free_rate is not None
        else CONVENTIONS.risk_free_rate
    )
    _, individual_vols, cov_matrix = load_market_risk_inputs_frame(
        tickers=ordered_tickers,
        lookback_days=lookback_days,
    )
    expected_returns_series = pd.Series(
        {ticker: float(expected_returns[ticker]) for ticker in ordered_tickers},
        dtype=float,
    )
    result = _optimize_from_expected_returns(
        expected_returns=expected_returns_series,
        cov_matrix=cov_matrix.loc[ordered_tickers, ordered_tickers],
        individual_vols=individual_vols.loc[ordered_tickers],
        objective=objective,
        risk_free_rate_used=risk_free_rate_used,
        max_weight=max_weight,
        min_weight=min_weight,
    )
    return _normalize_optimization_result(
        result,
        objective=objective,
        risk_free_rate_used=risk_free_rate_used,
    )


def run_portfolio_optimization_with_risk_inputs_payload(
    *,
    tickers: list[str],
    expected_returns: dict[str, float],
    risk_inputs,
    objective: str = "max_sharpe",
    risk_free_rate: float | None = None,
    max_weight: float = 1.0,
    min_weight: float = 0.0,
) -> dict[str, Any]:
    """Run allocator optimization from explicit expected returns and canonical risk inputs."""
    ordered_tickers = [
        ticker
        for ticker in tickers
        if ticker in expected_returns and ticker in _risk_inputs_field(risk_inputs, "tickers_used", [])
    ]
    if len(ordered_tickers) < 2:
        raise ValueError("at least two tickers with risk inputs and explicit expected returns are required")

    risk_free_rate_used = (
        risk_free_rate
        if risk_free_rate is not None
        else CONVENTIONS.risk_free_rate
    )
    covariance_frame = pd.DataFrame(_risk_inputs_field(risk_inputs, "covariance_matrix", {})).loc[
        ordered_tickers, ordered_tickers
    ]
    volatility_map = {
        (asset["ticker"] if isinstance(asset, dict) else asset.ticker): float(
            asset["annualized_volatility"] if isinstance(asset, dict) else asset.annualized_volatility
        )
        for asset in _risk_inputs_field(risk_inputs, "asset_risk_inputs", [])
    }
    individual_vols = pd.Series(
        {ticker: volatility_map[ticker] for ticker in ordered_tickers},
        dtype=float,
    )
    expected_returns_series = pd.Series(
        {ticker: float(expected_returns[ticker]) for ticker in ordered_tickers},
        dtype=float,
    )
    result = _optimize_from_expected_returns(
        expected_returns=expected_returns_series,
        cov_matrix=covariance_frame,
        individual_vols=individual_vols,
        objective=objective,
        risk_free_rate_used=risk_free_rate_used,
        max_weight=max_weight,
        min_weight=min_weight,
    )
    return _normalize_optimization_result(
        result,
        objective=objective,
        risk_free_rate_used=risk_free_rate_used,
    )


def run_allocator_candidate_optimizations_payload(
    *,
    tickers: list[str],
    expected_returns: dict[str, float],
    selected_objective: str,
    risk_inputs=None,
    risk_free_rate: float | None = None,
    lookback_days: int = 252,
    max_weight: float = 1.0,
    min_weight: float = 0.0,
    max_selected_assets: int | None = None,
    asset_class_constraints: list[AssetClassConstraintInput] | None = None,
    asset_class_by_ticker: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Run the allocator-only candidate set from explicit expected-return assumptions.

    Keeps `/portfolio/optimize` on the legacy path while giving `/allocator/*`
    a richer candidate comparison layer.
    """
    candidate_specs = [
        ("max_sharpe_assumption_aware", "max_sharpe", "best risk-adjusted expected return candidate"),
        ("min_variance_assumption_aware", "min_variance", "lowest expected volatility candidate"),
        ("risk_parity_assumption_aware", "risk_parity", "balanced risk-contribution candidate"),
    ]
    candidates: list[dict[str, Any]] = []
    warnings: list[str] = []
    normalized_asset_class_constraints = [
        item if isinstance(item, AssetClassConstraintInput) else AssetClassConstraintInput(**item)
        for item in (asset_class_constraints or [])
    ]
    normalized_asset_class_by_ticker = {
        str(ticker): str(asset_class).lower()
        for ticker, asset_class in (asset_class_by_ticker or {}).items()
    }

    for candidate_id, objective, tradeoff_summary in candidate_specs:
        try:
            if risk_inputs is not None:
                payload = run_portfolio_optimization_with_risk_inputs_payload(
                    tickers=tickers,
                    expected_returns=expected_returns,
                    risk_inputs=risk_inputs,
                    objective=objective,
                    risk_free_rate=risk_free_rate,
                    max_weight=max_weight,
                    min_weight=min_weight,
                )
            else:
                payload = run_portfolio_optimization_with_assumptions_payload(
                    tickers=tickers,
                    expected_returns=expected_returns,
                    objective=objective,
                    risk_free_rate=risk_free_rate,
                    lookback_days=lookback_days,
                    max_weight=max_weight,
                    min_weight=min_weight,
                )
            applied_constraints: list[str] = []
            if max_selected_assets is not None or normalized_asset_class_constraints:
                if risk_inputs is None:
                    raise ValueError("rich allocator constraints require canonical risk inputs")
                payload, applied_constraints = _apply_allocator_constraints(
                    payload=payload,
                    expected_returns=expected_returns,
                    risk_inputs=risk_inputs,
                    objective=objective,
                    risk_free_rate_used=payload["risk_free_rate_used"],
                    max_weight=max_weight,
                    min_weight=min_weight,
                    max_selected_assets=max_selected_assets,
                    asset_class_constraints=normalized_asset_class_constraints,
                    asset_class_by_ticker=normalized_asset_class_by_ticker,
                )
            candidates.append(
                {
                    "candidate_id": candidate_id,
                    "objective": objective,
                    "tradeoff_summary": (
                        tradeoff_summary
                        if not applied_constraints
                        else tradeoff_summary + f" (constraint-adjusted: {', '.join(applied_constraints)})"
                    ),
                    "applied_constraints": applied_constraints,
                    **payload,
                }
            )
        except Exception as exc:
            warnings.append(f"{candidate_id} unavailable: {exc}")

    if not candidates:
        raise ValueError("no allocator candidate portfolio could be generated from current assumptions")

    selected = next(
        (candidate for candidate in candidates if candidate["objective"] == selected_objective),
        None,
    )
    if selected is None:
        selected = candidates[0]
        warnings.append(
            f"requested objective '{selected_objective}' was unavailable; fell back to '{selected['candidate_id']}'"
        )

    return {
        "selected_candidate_id": selected["candidate_id"],
        "selected_objective": selected["objective"],
        "selected_payload": selected,
        "candidates": candidates,
        "warnings": warnings,
    }


__all__ = [
    "covariance_estimator_name",
    "load_market_risk_inputs_frame",
    "run_portfolio_optimization",
    "run_portfolio_optimization_payload",
    "run_allocator_candidate_optimizations_payload",
    "run_portfolio_optimization_with_assumptions_payload",
    "run_portfolio_optimization_with_risk_inputs_payload",
]

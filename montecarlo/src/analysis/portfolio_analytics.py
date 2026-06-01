"""
portfolio_analytics.py — Portfolio optimizer using scipy (Markowitz + Black-Litterman).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from scipy.optimize import minimize

from .core import DARK_THEME


def _load_quant_conventions():
    """Load shared quant conventions without importing heavy genesix package init."""
    module_path = (
        Path(__file__).resolve().parents[1]
        / "genesix"
        / "utils"
        / "quant_conventions.py"
    )
    spec = spec_from_file_location("src_shared_quant_conventions", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load quant conventions from {module_path}")
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_QC = _load_quant_conventions()
RISK_FREE_RATE = _QC.RISK_FREE_RATE
ANNUALIZATION_FACTOR_RETURN = _QC.ANNUALIZATION_FACTOR_RETURN
ANNUALIZATION_FACTOR_VOL = _QC.ANNUALIZATION_FACTOR_VOL

_C = DARK_THEME


class PortfolioAnalytics:
    """Mean-variance portfolio optimization and Black-Litterman model."""

    # ─────────────────────────────────────────────────────────────────────────
    # DATA
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    @st.cache_data(ttl=300)
    def get_returns(symbols: List[str], period: str = "3y") -> pd.DataFrame:
        """Fetch daily log returns for a list of symbols.

        Returns:
            DataFrame of daily log returns.
        """
        try:
            raw = yf.download(symbols, period=period, interval="1d",
                               auto_adjust=True, progress=False)["Close"]
        except Exception:
            return pd.DataFrame()

        if isinstance(raw, pd.Series):
            raw = raw.to_frame(name=symbols[0])

        raw = raw.dropna(how="all").ffill()
        return np.log(raw / raw.shift(1)).dropna()

    # ─────────────────────────────────────────────────────────────────────────
    # MARKOWITZ OPTIMIZATION (scipy — not random sampling)
    # ─────────────────────────────────────────────────────────────────────────

    def markowitz_optimize(
        self,
        symbols: List[str],
        target: str = "max_sharpe",  # 'max_sharpe' | 'min_vol' | 'max_return'
        risk_free: float = RISK_FREE_RATE,
        constraints: Optional[List[Dict]] = None,
        bounds: Optional[Tuple] = None,
    ) -> Dict:
        """Run mean-variance optimization with scipy.

        Args:
            symbols: List of tickers.
            target: Objective function.
            risk_free: Risk-free rate (annualized).
            constraints: Additional scipy constraints.
            bounds: Weight bounds per asset. Default (0, 1) for long-only.

        Returns:
            Dict with optimal weights, expected return, volatility, sharpe,
            efficient frontier data.
        """
        returns = self.get_returns(symbols)
        if returns.empty or len(returns.columns) < 2:
            return {}

        mu = returns.mean() * ANNUALIZATION_FACTOR_RETURN          # annualized expected returns
        cov = returns.cov() * ANNUALIZATION_FACTOR_RETURN          # annualized covariance
        n = len(symbols)

        if bounds is None:
            bounds = tuple((0.0, 1.0) for _ in range(n))

        base_constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
        if constraints:
            base_constraints.extend(constraints)

        def neg_sharpe(w: np.ndarray) -> float:
            ret = float(np.dot(w, mu.values))
            vol = float(np.sqrt(w @ cov.values @ w))
            return -(ret - risk_free) / vol if vol > 0 else 0.0

        def portfolio_vol(w: np.ndarray) -> float:
            return float(np.sqrt(w @ cov.values @ w))

        def neg_return(w: np.ndarray) -> float:
            return -float(np.dot(w, mu.values))

        obj_fns = {
            "max_sharpe": neg_sharpe,
            "min_vol":    portfolio_vol,
            "max_return": neg_return,
        }
        obj_fn = obj_fns.get(target, neg_sharpe)

        w0 = np.ones(n) / n
        result = minimize(
            obj_fn,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=base_constraints,
            options={"maxiter": 1000, "ftol": 1e-9},
        )

        if not result.success:
            # Fall back to equal weight
            weights = np.ones(n) / n
        else:
            weights = result.x
            weights = np.clip(weights, 0, 1)
            weights /= weights.sum()

        exp_return = float(np.dot(weights, mu.values))
        exp_vol = float(np.sqrt(weights @ cov.values @ weights))
        sharpe = (exp_return - risk_free) / exp_vol if exp_vol > 0 else 0

        weight_dict = {s: round(float(w), 4) for s, w in zip(symbols, weights)}

        # Efficient frontier (100 points)
        ef_targets = np.linspace(float(mu.min()), float(mu.max()), 60)
        ef_vols, ef_rets = [], []
        for target_ret in ef_targets:
            ef_constraints = base_constraints + [
                {"type": "eq", "fun": lambda w, r=target_ret: np.dot(w, mu.values) - r}
            ]
            ef_result = minimize(
                portfolio_vol, w0, method="SLSQP",
                bounds=bounds, constraints=ef_constraints,
                options={"maxiter": 500, "ftol": 1e-8},
            )
            if ef_result.success:
                ef_vols.append(float(portfolio_vol(ef_result.x)) * 100)
                ef_rets.append(float(target_ret) * 100)

        return {
            "weights":      weight_dict,
            "exp_return":   round(exp_return * 100, 2),
            "exp_vol":      round(exp_vol * 100, 2),
            "sharpe":       round(sharpe, 3),
            "target":       target,
            "ef_vols":      ef_vols,
            "ef_rets":      ef_rets,
            "mu":           {s: round(float(v) * 100, 2) for s, v in mu.items()},
            "corr_matrix":  returns.corr().round(3),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # BLACK-LITTERMAN
    # ─────────────────────────────────────────────────────────────────────────

    def black_litterman_optimize(
        self,
        symbols: List[str],
        views: Optional[Dict[str, float]] = None,
        view_confidence: float = 0.5,
        risk_aversion: float = 2.5,
        risk_free: float = RISK_FREE_RATE,
    ) -> Dict:
        """Black-Litterman portfolio optimization.

        Args:
            symbols: List of tickers.
            views: Dict {ticker: expected_return_pct} representing investor views.
                   e.g., {'AAPL': 15.0, 'MSFT': 10.0} means you expect 15% / 10% return.
            view_confidence: Confidence in views (0–1). Higher = more weight on views.
            risk_aversion: Risk aversion parameter (lambda).
            risk_free: Risk-free rate.

        Returns:
            Dict with BL-adjusted returns, optimal weights, metrics.
        """
        returns = self.get_returns(symbols)
        if returns.empty or len(returns.columns) < 2:
            return {}

        n = len(symbols)
        cov = returns.cov().values * ANNUALIZATION_FACTOR_RETURN
        mu_hist = returns.mean().values * ANNUALIZATION_FACTOR_RETURN

        # Market-cap equilibrium weights (equal weight if no market cap data)
        w_eq = np.ones(n) / n
        Pi = risk_aversion * cov @ w_eq  # implied excess returns

        if views:
            # Build view matrix P and view vector Q
            valid_views = {s: v / 100 for s, v in views.items() if s in symbols}
            k = len(valid_views)
            if k > 0:
                P = np.zeros((k, n))
                Q = np.zeros(k)
                sym_idx = {s: i for i, s in enumerate(symbols)}
                for j, (sym, ret) in enumerate(valid_views.items()):
                    P[j, sym_idx[sym]] = 1.0
                    Q[j] = ret

                # Omega — diagonal uncertainty matrix
                tau = 0.025
                sigma_views = np.diag(np.diag(P @ (tau * cov) @ P.T))

                # BL formula
                term1 = np.linalg.inv(tau * cov)
                term2 = P.T @ np.linalg.inv(sigma_views) @ P
                mu_bl = np.linalg.inv(term1 + term2) @ (
                    term1 @ Pi + P.T @ np.linalg.inv(sigma_views) @ Q
                )
            else:
                mu_bl = Pi
        else:
            mu_bl = Pi

        # Optimize with BL returns
        mu_series = pd.Series(mu_bl, index=symbols)
        cov_pd = pd.DataFrame(cov, index=symbols, columns=symbols)

        def neg_sharpe(w: np.ndarray) -> float:
            ret = float(np.dot(w, mu_bl))
            vol = float(np.sqrt(w @ cov @ w))
            return -(ret - risk_free) / vol if vol > 0 else 0

        w0 = np.ones(n) / n
        bounds = tuple((0.0, 1.0) for _ in range(n))
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]

        result = minimize(
            neg_sharpe, w0, method="SLSQP",
            bounds=bounds, constraints=constraints,
            options={"maxiter": 1000},
        )

        weights = result.x if result.success else w0
        weights = np.clip(weights, 0, 1)
        weights /= weights.sum()

        exp_return = float(np.dot(weights, mu_bl))
        exp_vol = float(np.sqrt(weights @ cov @ weights))
        sharpe = (exp_return - risk_free) / exp_vol if exp_vol > 0 else 0

        return {
            "weights":      {s: round(float(w), 4) for s, w in zip(symbols, weights)},
            "bl_returns":   {s: round(float(r) * 100, 2) for s, r in zip(symbols, mu_bl)},
            "hist_returns": {s: round(float(r) * 100, 2) for s, r in zip(symbols, mu_hist)},
            "exp_return":   round(exp_return * 100, 2),
            "exp_vol":      round(exp_vol * 100, 2),
            "sharpe":       round(sharpe, 3),
            "views_used":   views or {},
        }

    # ─────────────────────────────────────────────────────────────────────────
    # RISK METRICS
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def portfolio_metrics(weights: Dict[str, float],
                            returns_df: pd.DataFrame) -> Dict:
        """Compute portfolio-level risk metrics.

        Args:
            weights: Dict symbol → weight.
            returns_df: DataFrame of daily returns.

        Returns:
            Dict with VaR, CVaR, max drawdown, contribution per asset.
        """
        syms = list(weights.keys())
        w = np.array([weights[s] for s in syms])
        rets = returns_df[syms].dropna()
        if rets.empty:
            return {}

        port_returns = rets @ w

        # VaR / CVaR at 95% and 99%
        var_95 = float(np.percentile(port_returns, 5) * 100)
        var_99 = float(np.percentile(port_returns, 1) * 100)
        cvar_95 = float(port_returns[port_returns <= np.percentile(port_returns, 5)].mean() * 100)
        cvar_99 = float(port_returns[port_returns <= np.percentile(port_returns, 1)].mean() * 100)

        # Equity curve and max drawdown
        equity = (1 + port_returns).cumprod()
        peak = equity.cummax()
        dd = (equity - peak) / peak
        max_dd = float(dd.min() * 100)

        # Risk contribution per asset
        cov = rets.cov().values * ANNUALIZATION_FACTOR_RETURN
        total_vol = float(np.sqrt(w @ cov @ w))
        marginal_risk = cov @ w
        contrib = w * marginal_risk / total_vol if total_vol > 0 else np.zeros(len(w))
        risk_contrib = {s: round(float(c) * 100, 2) for s, c in zip(syms, contrib)}

        return {
            "var_95":        round(var_95, 2),
            "var_99":        round(var_99, 2),
            "cvar_95":       round(cvar_95, 2),
            "cvar_99":       round(cvar_99, 2),
            "max_drawdown":  round(max_dd, 2),
            "total_vol_ann": round(total_vol * 100, 2),
            "risk_contrib":  risk_contrib,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # VISUALIZATIONS
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def render_efficient_frontier(result: Dict, symbols: List[str]) -> go.Figure:
        """Plot the efficient frontier with the optimal portfolio marked."""
        fig = go.Figure()

        ef_vols = result.get("ef_vols", [])
        ef_rets = result.get("ef_rets", [])

        if ef_vols and ef_rets:
            fig.add_trace(go.Scatter(
                x=ef_vols, y=ef_rets,
                name="Efficient Frontier",
                mode="lines",
                line=dict(color=_C["blue"], width=2),
            ))

        # Individual assets
        mu = result.get("mu", {})
        for sym in symbols:
            if sym in mu:
                try:
                    returns_data = PortfolioAnalytics.get_returns([sym])
                    if not returns_data.empty:
                        asset_vol = float(returns_data.std().iloc[0]) * ANNUALIZATION_FACTOR_VOL * 100
                        fig.add_trace(go.Scatter(
                            x=[asset_vol], y=[mu[sym]],
                            name=sym,
                            mode="markers+text",
                            text=[sym],
                            textposition="top center",
                            marker=dict(size=10, color=_C["yellow"]),
                        ))
                except Exception:
                    pass

        # Optimal portfolio
        fig.add_trace(go.Scatter(
            x=[result["exp_vol"]],
            y=[result["exp_return"]],
            name=f"Optimal ({result['target']})",
            mode="markers",
            marker=dict(size=15, color=_C["green"], symbol="star", line=dict(width=2, color="white")),
        ))

        fig.update_layout(
            paper_bgcolor=_C["bg"],
            plot_bgcolor=_C["panel"],
            font=dict(color=_C["text"]),
            title="<b>Efficient Frontier</b>",
            xaxis_title="Annualized Volatility (%)",
            yaxis_title="Expected Return (%)",
            xaxis=dict(gridcolor=_C["border"]),
            yaxis=dict(gridcolor=_C["border"]),
            height=450,
            legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        return fig

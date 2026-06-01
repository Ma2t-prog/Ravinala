"""Ravinala by TSIVAHINY Matthias — Portfolio Optimization Module (Mean-CVaR, Black-Litterman, Risk Decomposition)."""

import json
import warnings
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.optimize import minimize
from scipy.stats import norm

warnings.filterwarnings("ignore")


class PortfolioDataFetcher:
    """Fetches market data and computes returns and covariance matrices."""

    def __init__(self, tickers: list) -> None:
        """
        Initialize the data fetcher.

        Args:
            tickers: List of ticker symbols to fetch data for.
        """
        self.tickers = tickers

    def fetch_returns(self, period: str = "2y") -> pd.DataFrame:
        """
        Download price data and compute daily log returns.

        Args:
            period: Period string accepted by yfinance (e.g. '1y', '2y', '5y').

        Returns:
            DataFrame of daily log returns with tickers as columns.

        Raises:
            ValueError: If no valid data could be fetched for any ticker.
        """
        try:
            raw = yf.download(
                self.tickers,
                period=period,
                auto_adjust=True,
                progress=False,
                threads=True,
            )
            if raw.empty:
                raise ValueError(f"No data returned for tickers: {self.tickers}")

            if isinstance(raw.columns, pd.MultiIndex):
                prices = raw["Close"]
            else:
                prices = raw[["Close"]] if "Close" in raw.columns else raw

            prices = prices.dropna(how="all")
            log_returns = np.log(prices / prices.shift(1)).dropna()

            if log_returns.empty:
                raise ValueError("Log returns DataFrame is empty after cleaning.")

            return log_returns

        except Exception as exc:
            raise ValueError(f"Failed to fetch returns: {exc}") from exc

    def fetch_covariance(self, returns: pd.DataFrame) -> np.ndarray:
        """
        Compute the annualized sample covariance matrix from daily returns.

        Args:
            returns: DataFrame of daily log returns.

        Returns:
            Annualized covariance matrix as a numpy array.
        """
        return returns.cov().values * 252

    def fetch_current_prices(self) -> dict:
        """
        Fetch the most recent closing price for each ticker.

        Returns:
            Dictionary mapping ticker symbol to its latest closing price.
        """
        prices: dict = {}
        for ticker in self.tickers:
            try:
                data = yf.download(
                    ticker,
                    period="5d",
                    auto_adjust=True,
                    progress=False,
                    threads=False,
                )
                if not data.empty:
                    close = data["Close"].dropna()
                    if not close.empty:
                        prices[ticker] = float(close.iloc[-1])
                    else:
                        prices[ticker] = float("nan")
                else:
                    prices[ticker] = float("nan")
            except Exception:
                prices[ticker] = float("nan")
        return prices


class MeanCVaROptimizer:
    """Mean-CVaR portfolio optimizer using scipy (no cvxpy dependency)."""

    def __init__(self, returns: pd.DataFrame, confidence_level: float = 0.95) -> None:
        """
        Initialize the Mean-CVaR optimizer.

        Args:
            returns: DataFrame of daily log returns with tickers as columns.
            confidence_level: Confidence level for CVaR computation (e.g. 0.95).
        """
        self.returns = returns
        self.confidence_level = confidence_level
        self.tickers = list(returns.columns)
        self.n_assets = len(self.tickers)
        self._returns_array = returns.values

    def _compute_cvar(self, weights: np.ndarray, returns: pd.DataFrame) -> float:
        """
        Compute the Conditional Value-at-Risk (CVaR) for a given weight vector.

        Args:
            weights: Array of portfolio weights.
            returns: DataFrame of asset returns.

        Returns:
            CVaR as a positive float (loss metric).
        """
        portfolio_returns = returns.values @ weights
        cutoff = np.quantile(portfolio_returns, 1.0 - self.confidence_level)
        tail_returns = portfolio_returns[portfolio_returns <= cutoff]
        if len(tail_returns) == 0:
            return 0.0
        return float(-np.mean(tail_returns))

    def _portfolio_return(self, weights: np.ndarray, returns: pd.DataFrame) -> float:
        """
        Compute the mean annualized portfolio return.

        Args:
            weights: Array of portfolio weights.
            returns: DataFrame of asset returns.

        Returns:
            Annualized expected return as a float.
        """
        return float(np.mean(returns.values @ weights) * 252)

    def optimize(
        self,
        target_return: Optional[float] = None,
        min_weight: float = 0.0,
        max_weight: float = 1.0,
    ) -> dict:
        """
        Minimize CVaR subject to budget and optional return constraints.

        Args:
            target_return: Minimum required annualized expected return. If None,
                no return constraint is applied.
            min_weight: Minimum weight per asset.
            max_weight: Maximum weight per asset.

        Returns:
            Dictionary with keys:
                - "weights": dict mapping ticker to optimal weight
                - "expected_return": annualized expected return
                - "cvar": portfolio CVaR
                - "sharpe": Sharpe ratio (return / daily_vol * sqrt(252))
        """
        x0 = np.full(self.n_assets, 1.0 / self.n_assets)
        bounds = [(min_weight, max_weight)] * self.n_assets
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

        if target_return is not None:
            constraints.append(
                {
                    "type": "ineq",
                    "fun": lambda w: self._portfolio_return(w, self.returns) - target_return,
                }
            )

        result = minimize(
            fun=lambda w: self._compute_cvar(w, self.returns),
            x0=x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": 1e-9, "maxiter": 1000},
        )

        weights = result.x
        weights = np.clip(weights, min_weight, max_weight)
        weights /= weights.sum()

        exp_return = self._portfolio_return(weights, self.returns)
        cvar = self._compute_cvar(weights, self.returns)

        portfolio_daily = self.returns.values @ weights
        daily_vol = float(np.std(portfolio_daily, ddof=1))
        daily_mean = float(np.mean(portfolio_daily))
        sharpe = (daily_mean * 252) / (daily_vol * np.sqrt(252)) if daily_vol > 0 else 0.0

        return {
            "weights": {t: float(w) for t, w in zip(self.tickers, weights)},
            "expected_return": exp_return,
            "cvar": cvar,
            "sharpe": sharpe,
        }

    def efficient_frontier(self, n_points: int = 30) -> pd.DataFrame:
        """
        Compute the efficient frontier by sweeping target returns.

        Args:
            n_points: Number of points on the frontier.

        Returns:
            DataFrame with columns: ["expected_return", "cvar", "sharpe", "weights_json"].
        """
        mean_returns = self.returns.mean().values * 252
        min_ret = float(np.min(mean_returns))
        max_ret = float(np.max(mean_returns))
        targets = np.linspace(min_ret, max_ret, n_points)

        rows = []
        for target in targets:
            try:
                result = self.optimize(target_return=float(target))
                rows.append(
                    {
                        "expected_return": result["expected_return"],
                        "cvar": result["cvar"],
                        "sharpe": result["sharpe"],
                        "weights_json": json.dumps(result["weights"]),
                    }
                )
            except Exception:
                continue

        return pd.DataFrame(rows, columns=["expected_return", "cvar", "sharpe", "weights_json"])


class RiskDecomposer:
    """Decomposes portfolio risk into per-asset contributions and diversification metrics."""

    def __init__(
        self,
        weights: np.ndarray,
        cov_matrix: np.ndarray,
        returns: pd.DataFrame,
        tickers: list,
    ) -> None:
        """
        Initialize the risk decomposer.

        Args:
            weights: Array of portfolio weights (must sum to 1).
            cov_matrix: Annualized covariance matrix (n_assets x n_assets).
            returns: DataFrame of daily log returns.
            tickers: List of ticker symbols matching the weight/covariance ordering.
        """
        self.weights = np.asarray(weights, dtype=float)
        self.cov_matrix = np.asarray(cov_matrix, dtype=float)
        self.returns = returns
        self.tickers = tickers

    def component_var(self, confidence: float = 0.95) -> dict:
        """
        Compute marginal and component VaR contributions for each asset.

        Args:
            confidence: Confidence level for VaR (e.g. 0.95).

        Returns:
            Dictionary with keys:
                - "total_var": float, annualized portfolio VaR
                - "components": dict mapping ticker to
                  {"component_var": float, "pct_contribution": float}
        """
        sigma_p = float(np.sqrt(self.weights @ self.cov_matrix @ self.weights))
        if sigma_p == 0.0:
            sigma_p = 1e-10

        z = norm.ppf(confidence)
        marginal_var = (self.cov_matrix @ self.weights) / sigma_p * z
        component_var = self.weights * marginal_var * np.sqrt(252)
        total_var = float(sigma_p * np.sqrt(252) * z)

        components = {}
        for i, ticker in enumerate(self.tickers):
            pct = float(component_var[i] / total_var * 100) if total_var != 0 else 0.0
            components[ticker] = {
                "component_var": float(component_var[i]),
                "pct_contribution": pct,
            }

        return {"total_var": total_var, "components": components}

    def diversification_ratio(self) -> float:
        """
        Compute the diversification ratio of the portfolio.

        Returns:
            DR = weighted sum of individual volatilities / portfolio volatility.
        """
        individual_vols = np.sqrt(np.diag(self.cov_matrix))
        weighted_avg_vol = float(self.weights @ individual_vols)
        portfolio_vol = float(np.sqrt(self.weights @ self.cov_matrix @ self.weights))
        if portfolio_vol == 0.0:
            return 1.0
        return weighted_avg_vol / portfolio_vol

    def correlation_breakdown_impact(self, stress_correlation: float = 0.95) -> dict:
        """
        Assess the volatility impact of a uniform correlation stress scenario.

        Args:
            stress_correlation: Uniform pairwise correlation to apply in the
                stressed covariance matrix.

        Returns:
            Dictionary with keys:
                - "base_vol": annualized portfolio volatility under base covariance
                - "stressed_vol": annualized portfolio volatility under stress
                - "vol_increase_pct": percentage increase from base to stressed vol
        """
        vols = np.sqrt(np.diag(self.cov_matrix))
        stressed_cov = stress_correlation * np.outer(vols, vols)
        np.fill_diagonal(stressed_cov, vols ** 2)

        base_vol = float(np.sqrt(self.weights @ self.cov_matrix @ self.weights) * np.sqrt(252))
        stressed_vol = float(np.sqrt(self.weights @ stressed_cov @ self.weights) * np.sqrt(252))

        vol_increase_pct = (
            float((stressed_vol - base_vol) / base_vol * 100) if base_vol != 0 else 0.0
        )

        return {
            "base_vol": base_vol,
            "stressed_vol": stressed_vol,
            "vol_increase_pct": vol_increase_pct,
        }


class BlackLittermanOptimizer:
    """Classic Black-Litterman portfolio optimizer."""

    def __init__(
        self,
        tickers: list,
        market_weights: np.ndarray,
        cov_matrix: np.ndarray,
        risk_aversion: float = 2.5,
        tau: float = 0.05,
    ) -> None:
        """
        Initialize the Black-Litterman optimizer.

        Args:
            tickers: List of ticker symbols.
            market_weights: Market-cap weights for each asset.
            cov_matrix: Annualized covariance matrix (n_assets x n_assets).
            risk_aversion: Risk aversion coefficient (lambda).
            tau: Scalar scaling the uncertainty of the prior.
        """
        self.tickers = tickers
        self.n_assets = len(tickers)
        self.market_weights = np.asarray(market_weights, dtype=float)
        self.cov_matrix = np.asarray(cov_matrix, dtype=float)
        self.risk_aversion = risk_aversion
        self.tau = tau
        self._views: list = []

    def compute_equilibrium_returns(self) -> np.ndarray:
        """
        Compute the CAPM implied equilibrium excess returns (Pi).

        Returns:
            Array of implied equilibrium returns: Pi = lambda * Sigma @ w_market.
        """
        return self.risk_aversion * self.cov_matrix @ self.market_weights

    def add_view(
        self,
        assets: list,
        weights_in_view: list,
        expected_outperformance: float,
        confidence: float = 0.5,
    ) -> None:
        """
        Register an investor view on a linear combination of assets.

        Args:
            assets: List of tickers involved in the view.
            weights_in_view: Corresponding weights for the view portfolio (P row).
            expected_outperformance: Expected return (or relative outperformance) of
                the view, expressed as an annualized decimal.
            confidence: Investor confidence in the view in [0, 1]. Higher values
                reduce the view uncertainty omega.
        """
        p_row = np.zeros(self.n_assets, dtype=float)
        for asset, w in zip(assets, weights_in_view):
            if asset in self.tickers:
                idx = self.tickers.index(asset)
                p_row[idx] = w

        p_row_2d = p_row.reshape(1, -1)
        omega_diag = float(
            (1.0 - confidence) / max(confidence, 1e-10)
            * self.tau
            * float(p_row_2d @ self.cov_matrix @ p_row_2d.T)
        )

        self._views.append(
            {
                "P_row": p_row,
                "q": float(expected_outperformance),
                "omega_diag": max(omega_diag, 1e-10),
            }
        )

    def optimize(self) -> dict:
        """
        Compute the Black-Litterman posterior and derive optimal weights.

        Returns:
            Dictionary with keys:
                - "weights": dict mapping ticker to optimal weight
                - "posterior_returns": dict mapping ticker to posterior expected return
                - "prior_returns": dict mapping ticker to implied equilibrium return
        """
        pi = self.compute_equilibrium_returns()
        tau_sigma = self.tau * self.cov_matrix
        tau_sigma_inv = np.linalg.inv(tau_sigma)

        if not self._views:
            mu_bl = pi.copy()
        else:
            n_views = len(self._views)
            P = np.vstack([v["P_row"] for v in self._views])
            q = np.array([v["q"] for v in self._views], dtype=float)
            omega = np.diag([v["omega_diag"] for v in self._views])
            omega_inv = np.diag(1.0 / np.array([v["omega_diag"] for v in self._views]))

            m = tau_sigma_inv + P.T @ omega_inv @ P
            m_inv = np.linalg.inv(m)
            mu_bl = m_inv @ (tau_sigma_inv @ pi + P.T @ omega_inv @ q)

        sigma_inv = np.linalg.inv(self.risk_aversion * self.cov_matrix)
        raw_weights = sigma_inv @ mu_bl
        weight_sum = np.sum(raw_weights)
        if abs(weight_sum) < 1e-10:
            optimal_weights = np.full(self.n_assets, 1.0 / self.n_assets)
        else:
            optimal_weights = raw_weights / weight_sum

        return {
            "weights": {t: float(w) for t, w in zip(self.tickers, optimal_weights)},
            "posterior_returns": {t: float(r) for t, r in zip(self.tickers, mu_bl)},
            "prior_returns": {t: float(r) for t, r in zip(self.tickers, pi)},
        }


class TailRiskHedger:
    """Provides tail risk hedging analysis using put options and VaR contributions."""

    def __init__(self, portfolio_value: float, portfolio_vol: float) -> None:
        """
        Initialize the tail risk hedger.

        Args:
            portfolio_value: Total portfolio value in currency units.
            portfolio_vol: Annualized portfolio volatility as a decimal (e.g. 0.15).
        """
        self.portfolio_value = portfolio_value
        self.portfolio_vol = portfolio_vol

    @staticmethod
    def _black_scholes_put(
        spot: float,
        strike: float,
        maturity: float,
        rate: float,
        vol: float,
    ) -> float:
        """
        Price a European put option using the Black-Scholes formula.

        Args:
            spot: Current underlying price.
            strike: Option strike price.
            maturity: Time to maturity in years.
            rate: Continuously compounded risk-free rate.
            vol: Annualized implied volatility of the underlying.

        Returns:
            Put option price.
        """
        if vol <= 0 or maturity <= 0 or spot <= 0:
            return max(strike * np.exp(-rate * maturity) - spot, 0.0)

        sqrt_t = np.sqrt(maturity)
        d1 = (np.log(spot / strike) + (rate + 0.5 * vol ** 2) * maturity) / (vol * sqrt_t)
        d2 = d1 - vol * sqrt_t
        put_price = (
            strike * np.exp(-rate * maturity) * norm.cdf(-d2) - spot * norm.cdf(-d1)
        )
        return float(max(put_price, 0.0))

    def suggest_put_hedge(
        self,
        spot: float,
        current_vol: float,
        hedge_ratio: float = 0.10,
    ) -> dict:
        """
        Suggest a protective put hedge for a given hedge ratio.

        The optimal strike is set at 90% of spot (10% OTM put), priced with a
        three-month Black-Scholes model at a 4% risk-free rate.

        Args:
            spot: Current price of the portfolio or index used as hedge vehicle.
            current_vol: Current annualized implied volatility (e.g. 0.20 for 20%).
            hedge_ratio: Fraction of portfolio notional to protect.

        Returns:
            Dictionary with keys:
                - "put_strike": strike of the recommended put
                - "put_price": Black-Scholes put price per contract unit
                - "annual_hedge_cost_pct": annualised cost as % of portfolio value
                - "contracts_needed": number of contracts (rounded to nearest int)
                - "protection_level": protected notional value
        """
        maturity = 0.25
        rate = 0.04
        put_strike = 0.90 * spot
        put_price = self._black_scholes_put(spot, put_strike, maturity, rate, current_vol)

        protected_notional = self.portfolio_value * hedge_ratio
        contracts_needed = protected_notional / spot
        hedge_cost = put_price * contracts_needed
        annual_hedge_cost_pct = (hedge_cost * 4.0 / self.portfolio_value) * 100.0

        return {
            "put_strike": float(put_strike),
            "put_price": float(put_price),
            "annual_hedge_cost_pct": float(annual_hedge_cost_pct),
            "contracts_needed": int(round(contracts_needed)),
            "protection_level": float(protected_notional),
        }

    def marginal_contribution_to_var(
        self, weights: np.ndarray, cov: np.ndarray
    ) -> np.ndarray:
        """
        Compute the marginal contribution of each asset to portfolio variance.

        Args:
            weights: Array of portfolio weights.
            cov: Covariance matrix of asset returns.

        Returns:
            Array of marginal variance contributions: (Sigma @ w) / (w.T @ Sigma @ w).
        """
        weights = np.asarray(weights, dtype=float)
        portfolio_variance = float(weights @ cov @ weights)
        if portfolio_variance == 0.0:
            return np.zeros_like(weights)
        return (cov @ weights) / portfolio_variance

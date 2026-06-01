"""
Portfolio Optimization Lab — Ravinala v2.0
Backend classes + Streamlit UI for institutional-grade portfolio optimization.
"""
from __future__ import annotations

import warnings
warnings.filterwarnings('ignore')
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import scipy.optimize as sco
import scipy.stats as ss
from scipy.optimize import linprog
from scipy.spatial.distance import squareform
from scipy.cluster.hierarchy import linkage, leaves_list
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st

try:
    from sklearn.covariance import LedoitWolf
    _SKLEARN_OK = True
except ImportError:
    _SKLEARN_OK = False

# ─────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────
ANN_FACTOR: Dict[str, int] = {'daily': 252, 'weekly': 52, 'monthly': 12}

_BG    = "#0A0A0F"
_CARD  = "#13131E"
_ACC   = "#00D9A6"
_BLUE  = "#3B82F6"
_AMBER = "#F59E0B"
_RED   = "#EF4444"
_GRID  = "rgba(255,255,255,0.04)"
_FONT  = "rgba(255,255,255,0.72)"

_BASE = dict(
    paper_bgcolor=_BG, plot_bgcolor=_BG,
    font=dict(color=_FONT, family="Inter, system-ui, sans-serif"),
    margin=dict(l=0, r=0, t=30, b=0),
    template="plotly_dark",
)

# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def _nearest_psd(A: np.ndarray) -> np.ndarray:
    B = (A + A.T) / 2
    _, s, V = np.linalg.svd(B)
    H = V.T @ np.diag(np.maximum(s, 0)) @ V
    return (B + H) / 2 + np.eye(A.shape[0]) * 1e-8


def _max_drawdown(returns: Union[pd.Series, np.ndarray]) -> float:
    r = pd.Series(returns)
    cum = (1 + r).cumprod()
    dd = (cum - cum.cummax()) / (cum.cummax() + 1e-10)
    return float(dd.min())


def _sortino(returns: Union[pd.Series, np.ndarray], rf: float, ann: int) -> float:
    r = pd.Series(returns)
    excess = r - rf / ann
    down = excess[excess < 0]
    if len(down) == 0 or down.std() == 0:
        return 0.0
    return float(excess.mean() / down.std() * np.sqrt(ann))


def _calmar(returns: Union[pd.Series, np.ndarray], ann: int) -> float:
    r = pd.Series(returns)
    cagr = (1 + r).prod() ** (ann / max(len(r), 1)) - 1
    mdd = abs(_max_drawdown(r))
    return float(cagr / mdd) if mdd > 1e-10 else 0.0


def _cvar_from_returns(returns: Union[pd.Series, np.ndarray], alpha: float = 0.05) -> float:
    r = np.array(returns)
    var = float(np.quantile(r, alpha))
    tail = r[r <= var]
    return float(tail.mean()) if len(tail) > 0 else var


# ─────────────────────────────────────────────────────────────────
# MarketDataLoader
# ─────────────────────────────────────────────────────────────────

class MarketDataLoader:
    """Fetch and pre-process market data via yfinance."""

    _IMAP = {'daily': '1d', 'weekly': '1wk', 'monthly': '1mo'}

    def fetch(
        self,
        tickers: List[str],
        period: str = '5y',
        frequency: str = 'daily',
    ) -> Tuple[pd.DataFrame, List[str]]:
        """Download adjusted close prices. Returns (prices_df, valid_tickers)."""
        interval = self._IMAP.get(frequency, '1d')
        frames: Dict[str, pd.Series] = {}
        invalid: List[str] = []

        for tkr in tickers:
            try:
                raw = yf.Ticker(tkr).history(
                    period=period, interval=interval, auto_adjust=True
                )
                if raw.empty or len(raw) < 5:
                    invalid.append(tkr)
                    continue
                s = raw['Close'].copy()
                if s.index.tz is not None:
                    s.index = s.index.tz_localize(None)
                frames[tkr] = s
            except Exception:
                invalid.append(tkr)

        if invalid:
            st.warning(f"Could not fetch data for: {', '.join(invalid)}")
        if not frames:
            return pd.DataFrame(), []

        prices = pd.DataFrame(frames)
        prices = prices.ffill().bfill().dropna()
        return prices, list(prices.columns)

    @staticmethod
    def compute_returns(prices: pd.DataFrame, method: str = 'log') -> pd.DataFrame:
        if method == 'log':
            return np.log(prices / prices.shift(1)).dropna()
        return prices.pct_change().dropna()

    def compute_stats(
        self,
        returns: pd.DataFrame,
        risk_free: float = 0.035,
        frequency: str = 'daily',
    ) -> pd.DataFrame:
        ann = ANN_FACTOR.get(frequency, 252)
        rows = []
        for col in returns.columns:
            r = returns[col].dropna()
            cagr = (1 + r).prod() ** (ann / max(len(r), 1)) - 1
            vol  = r.std() * np.sqrt(ann)
            sr   = (cagr - risk_free) / vol if vol > 0 else 0.0
            rows.append({
                'Ticker':   col,
                'CAGR':     cagr,
                'Vol':      vol,
                'Sharpe':   sr,
                'Sortino':  _sortino(r, risk_free, ann),
                'MaxDD':    _max_drawdown(r),
                'Calmar':   _calmar(r, ann),
                'Skewness': float(ss.skew(r)),
                'Kurtosis': float(ss.kurtosis(r)),
            })
        return pd.DataFrame(rows).set_index('Ticker')


# ─────────────────────────────────────────────────────────────────
# PortfolioOptimizer
# ─────────────────────────────────────────────────────────────────

class PortfolioOptimizer:
    """Multi-method portfolio optimizer."""

    def __init__(
        self,
        returns: pd.DataFrame,
        risk_free_rate: float = 0.035,
        cov_method: str = 'sample',
        frequency: str = 'daily',
    ):
        self.returns    = returns.dropna()
        self.rf         = risk_free_rate
        self.cov_method = cov_method
        self.frequency  = frequency
        self.ann        = ANN_FACTOR.get(frequency, 252)
        self.tickers    = list(returns.columns)
        self.n          = len(self.tickers)
        self.mu         = self.returns.mean().values * self.ann
        self.cov        = self._estimate_cov()

    def _estimate_cov(self) -> np.ndarray:
        r = self.returns.values
        if self.cov_method == 'ledoit_wolf' and _SKLEARN_OK:
            cov = LedoitWolf().fit(r).covariance_ * self.ann
        elif self.cov_method == 'ewma':
            span = min(126, len(r) // 2)
            ewm_df = self.returns.ewm(span=span).cov()
            last_dt = ewm_df.index.get_level_values(0)[-1]
            cov = ewm_df.loc[last_dt].values * self.ann
        elif self.cov_method == 'shrinkage':
            S = np.cov(r.T) * self.ann
            mu_d = np.trace(S) / self.n
            cov = 0.9 * S + 0.1 * mu_d * np.eye(self.n)
        else:
            cov = np.cov(r.T) * self.ann
        # Ensure 2D (edge case: single asset)
        cov = np.atleast_2d(cov)
        if cov.shape[0] > 1 and np.any(np.linalg.eigvalsh(cov) < 0):
            cov = _nearest_psd(cov)
        return cov

    def _perf(self, w: np.ndarray) -> Tuple[float, float, float]:
        ret = float(w @ self.mu)
        vol = float(np.sqrt(max(w @ self.cov @ w, 1e-12)))
        sr  = (ret - self.rf) / vol
        return ret, vol, sr

    def _metrics(self, w: np.ndarray) -> dict:
        ret, vol, sr = self._perf(w)
        port_r = pd.Series(self.returns.values @ w)
        return {
            'weights':         w,
            'tickers':         self.tickers,
            'expected_return': ret,
            'volatility':      vol,
            'sharpe':          sr,
            'sortino':         _sortino(port_r, self.rf, self.ann),
            'max_drawdown':    _max_drawdown(port_r),
            'cvar_95':         _cvar_from_returns(port_r),
        }

    def _cons_bounds(self, c: Optional[dict]) -> Tuple[list, list]:
        lo      = c.get('long_only', True)  if c else True
        max_w   = c.get('max_weight', 1.0) if c else 1.0
        min_w   = c.get('min_weight', 0.0) if c else 0.0
        max_to  = c.get('max_turnover')    if c else None
        cur_w   = c.get('current_weights') if c else None
        lb = min_w if lo else -max_w
        bounds = [(lb, max_w)] * self.n
        cons = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
        if max_to is not None and cur_w is not None:
            cw = np.array(cur_w)
            cons.append({'type': 'ineq',
                         'fun': lambda w: max_to - np.sum(np.abs(w - cw)) / 2})
        return cons, bounds

    def _minimize(self, obj, cons, bounds, n_tries: int = 3) -> np.ndarray:
        best = None
        for _ in range(n_tries):
            x0 = np.random.dirichlet(np.ones(self.n))
            r = sco.minimize(obj, x0, method='SLSQP', bounds=bounds,
                             constraints=cons,
                             options={'ftol': 1e-9, 'maxiter': 1000})
            if r.success and (best is None or r.fun < best.fun):
                best = r
        return best.x if best is not None and best.success else np.ones(self.n) / self.n

    def max_sharpe(self, constraints: Optional[dict] = None) -> dict:
        cons, bounds = self._cons_bounds(constraints)
        def obj(w):
            ret, vol, _ = self._perf(w)
            return -(ret - self.rf) / (vol + 1e-10)
        w = self._minimize(obj, cons, bounds)
        w = np.maximum(w, 0); w /= w.sum()
        return self._metrics(w)

    def min_variance(self, constraints: Optional[dict] = None) -> dict:
        cons, bounds = self._cons_bounds(constraints)
        w = self._minimize(lambda w: float(w @ self.cov @ w), cons, bounds)
        w = np.maximum(w, 0); w /= w.sum()
        return self._metrics(w)

    def max_return(self, target_vol: float, constraints: Optional[dict] = None) -> dict:
        cons, bounds = self._cons_bounds(constraints)
        cons = cons + [{'type': 'ineq',
                        'fun': lambda w: target_vol - np.sqrt(max(w @ self.cov @ w, 0))}]
        w = self._minimize(lambda w: -float(w @ self.mu), cons, bounds)
        w = np.maximum(w, 0); w /= w.sum()
        return self._metrics(w)

    def min_vol_for_target_return(self, target_return: float,
                                   constraints: Optional[dict] = None) -> dict:
        cons, bounds = self._cons_bounds(constraints)
        cons = cons + [{'type': 'ineq',
                        'fun': lambda w: float(w @ self.mu) - target_return}]
        w = self._minimize(lambda w: float(w @ self.cov @ w), cons, bounds)
        w = np.maximum(w, 0); w /= w.sum()
        return self._metrics(w)

    def equal_weight(self, constraints: Optional[dict] = None) -> dict:
        return self._metrics(np.ones(self.n) / self.n)

    def inverse_vol(self, constraints: Optional[dict] = None) -> dict:
        vols = np.sqrt(np.diag(self.cov))
        w = (1 / vols) / (1 / vols).sum()
        return self._metrics(w)

    def risk_parity(self, constraints: Optional[dict] = None) -> dict:
        def obj(w):
            pv = np.sqrt(max(w @ self.cov @ w, 1e-12))
            rc = w * (self.cov @ w) / pv
            target = np.ones(self.n) / self.n
            return float(np.sum((rc / (rc.sum() + 1e-10) - target) ** 2))
        cons = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
        bounds = [(1e-4, 1.0)] * self.n
        best = None
        for _ in range(5):
            x0 = np.random.dirichlet(np.ones(self.n))
            r = sco.minimize(obj, x0, method='SLSQP', bounds=bounds,
                             constraints=cons, options={'ftol': 1e-10, 'maxiter': 2000})
            if r.success and (best is None or r.fun < best.fun):
                best = r
        w = best.x if best is not None else np.ones(self.n) / self.n
        w = np.maximum(w, 0); w /= w.sum()
        return self._metrics(w)

    def hierarchical_risk_parity(self, constraints: Optional[dict] = None) -> dict:
        corr = self.returns.corr().values
        np.fill_diagonal(corr, 1.0)
        dist = np.sqrt(np.clip((1 - corr) / 2, 0, 1))
        np.fill_diagonal(dist, 0)
        condensed = squareform(dist, checks=False)
        Z = linkage(condensed, method='ward')
        order = leaves_list(Z)
        ordered = [self.tickers[i] for i in order]
        cov_df = pd.DataFrame(self.cov, index=self.tickers, columns=self.tickers)
        cov_ord = cov_df.loc[ordered, ordered].values

        def _cv(idx):
            sub = cov_ord[np.ix_(idx, idx)]
            v = np.sqrt(np.diag(sub))
            w = (1 / v) / (1 / v).sum()
            return float(w @ sub @ w)

        def _alloc(idx):
            if len(idx) == 1:
                return np.array([1.0])
            sp = len(idx) // 2
            L, R = idx[:sp], idx[sp:]
            vL, vR = _cv(L), _cv(R)
            a = 1 - vL / (vL + vR)
            res = np.zeros(len(idx))
            res[:sp] = _alloc(L) * a
            res[sp:] = _alloc(R) * (1 - a)
            return res

        w_ord = _alloc(list(range(len(ordered))))
        w = np.zeros(self.n)
        for i, orig in enumerate(order):
            w[orig] = w_ord[i]
        w = np.maximum(w, 0); w /= w.sum()
        return self._metrics(w)

    def black_litterman(
        self,
        views: Dict[str, float],
        tau: float = 0.05,
        confidence: Optional[List[float]] = None,
    ) -> dict:
        va = [a for a in views if a in self.tickers]
        if not va:
            return self.max_sharpe()
        Q = np.array([views[a] for a in va])
        k = len(va)
        P = np.zeros((k, self.n))
        for i, a in enumerate(va):
            P[i, self.tickers.index(a)] = 1.0
        w_mkt = np.ones(self.n) / self.n
        Pi = 2.5 * self.cov @ w_mkt
        conf = np.maximum((confidence or [0.5] * k)[:k], 0.01)
        Omega = np.diag([tau * float(P[i] @ self.cov @ P[i]) / conf[i] for i in range(k)])
        try:
            tS_inv = np.linalg.inv(tau * self.cov)
            Om_inv = np.linalg.inv(Omega)
            M = np.linalg.inv(tS_inv + P.T @ Om_inv @ P)
            mu_bl = M @ (tS_inv @ Pi + P.T @ Om_inv @ Q)
        except np.linalg.LinAlgError:
            return self.max_sharpe()
        orig = self.mu.copy()
        self.mu = mu_bl
        result = self.max_sharpe()
        self.mu = orig
        result.update({'bl_mu': mu_bl, 'equilibrium_mu': Pi, 'prior_mu': orig})
        return result

    def cvar_optimization(self, alpha: float = 0.05,
                          constraints: Optional[dict] = None) -> dict:
        R = self.returns.values
        T, n = R.shape
        n_v = n + T + 1
        c = np.zeros(n_v)
        c[n:n+T] = 1.0 / (T * alpha)
        c[n+T]   = 1.0
        A_ub = np.zeros((T, n_v))
        A_ub[:, :n] = -R
        A_ub[np.arange(T), n + np.arange(T)] = -1
        A_ub[:, n+T] = -1
        b_ub = np.zeros(T)
        A_eq = np.zeros((1, n_v)); A_eq[0, :n] = 1.0
        b_eq = np.array([1.0])
        lo  = (constraints or {}).get('long_only', True)
        mxw = (constraints or {}).get('max_weight', 1.0)
        mnw = (constraints or {}).get('min_weight', 0.0)
        lb  = mnw if lo else -mxw
        bnds = [(lb, mxw)] * n + [(0, None)] * T + [(None, None)]
        res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                      bounds=bnds, method='highs')
        w = np.maximum(res.x[:n], 0) if res.success else np.ones(n) / n
        w /= w.sum() + 1e-10
        return self._metrics(w)

    def max_diversification(self, constraints: Optional[dict] = None) -> dict:
        vols = np.sqrt(np.diag(self.cov))
        cons, bounds = self._cons_bounds(constraints)
        def obj(w):
            return -(w @ vols) / (np.sqrt(max(w @ self.cov @ w, 1e-12)) + 1e-10)
        w = self._minimize(obj, cons, bounds)
        w = np.maximum(w, 0); w /= w.sum()
        return self._metrics(w)

    def mean_cvar(self, target_cvar: float, alpha: float = 0.05) -> dict:
        R = self.returns.values
        cons = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
        def cvar_con(w):
            pr = R @ w
            v  = np.quantile(pr, alpha)
            cv = float(pr[pr <= v].mean()) if (pr <= v).any() else v
            return target_cvar - abs(cv)
        cons.append({'type': 'ineq', 'fun': cvar_con})
        bounds = [(0, 1)] * self.n
        w = self._minimize(lambda w: -float(w @ self.mu), cons, bounds)
        w = np.maximum(w, 0); w /= w.sum()
        return self._metrics(w)

    def efficient_frontier(self, n_points: int = 50,
                            constraints: Optional[dict] = None) -> pd.DataFrame:
        try:
            ret_min = self.min_variance(constraints)['expected_return']
            ret_max = float(self.mu.max()) * 0.99
            targets = np.linspace(ret_min * 1.01, ret_max, n_points)
        except Exception:
            return pd.DataFrame()
        rows = []
        for t in targets:
            try:
                res = self.min_vol_for_target_return(t, constraints)
                row = {'return': res['expected_return'], 'volatility': res['volatility'],
                       'sharpe': res['sharpe']}
                for i, tk in enumerate(self.tickers):
                    row[f'w_{tk}'] = res['weights'][i]
                rows.append(row)
            except Exception:
                continue
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    @staticmethod
    def build_constraints(n_assets: int, long_only: bool = True,
                          max_weight: float = 1.0, min_weight: float = 0.0,
                          max_turnover: Optional[float] = None,
                          current_weights: Optional[np.ndarray] = None) -> dict:
        return dict(long_only=long_only, max_weight=max_weight,
                    min_weight=min_weight, max_turnover=max_turnover,
                    current_weights=current_weights)


# ─────────────────────────────────────────────────────────────────
# PortfolioRiskAnalyzer
# ─────────────────────────────────────────────────────────────────

class PortfolioRiskAnalyzer:
    """Portfolio risk analysis suite."""

    def __init__(self, returns: pd.DataFrame, weights: np.ndarray,
                 risk_free_rate: float = 0.035, frequency: str = 'daily'):
        self.returns   = returns.dropna()
        self.weights   = np.array(weights)
        self.rf        = risk_free_rate
        self.frequency = frequency
        self.ann       = ANN_FACTOR.get(frequency, 252)
        self._pr       = self.portfolio_returns()

    def portfolio_returns(self) -> pd.Series:
        return pd.Series(self.returns.values @ self.weights, index=self.returns.index)

    def rolling_metrics(self, window: int = 252) -> pd.DataFrame:
        p = self._pr
        rm  = p.rolling(window).mean() * self.ann
        rs  = p.rolling(window).std()  * np.sqrt(self.ann)
        rsh = (rm - self.rf) / (rs + 1e-10)
        cum = (1 + p).cumprod()
        rdd = (cum - cum.cummax()) / (cum.cummax() + 1e-10)
        return pd.DataFrame({'rolling_return': rm, 'rolling_vol': rs,
                             'rolling_sharpe': rsh, 'rolling_drawdown': rdd})

    def drawdown_analysis(self) -> dict:
        p = self._pr
        cum = (1 + p).cumprod()
        dd  = (cum - cum.cummax()) / (cum.cummax() + 1e-10)
        trough = dd.idxmin()
        peak   = cum[:trough].idxmax() if len(cum[:trough]) > 0 else trough
        post   = cum[trough:]
        peak_val = float(cum[trough]) / (1 + float(dd[trough]))
        rec_mask = post >= peak_val
        rec_date = rec_mask.index[rec_mask][0] if rec_mask.any() else None
        return {'drawdown_series': dd, 'cum_returns': cum,
                'max_drawdown': float(dd.min()),
                'peak_date': peak, 'trough_date': trough, 'recovery_date': rec_date}

    def var_cvar(self, alpha: float = 0.05, method: str = 'historical') -> dict:
        p = self._pr
        if method == 'parametric':
            mu, sig = p.mean(), p.std()
            v95 = float(ss.norm.ppf(alpha, mu, sig))
            v99 = float(ss.norm.ppf(0.01, mu, sig))
            c95 = float(mu - sig * ss.norm.pdf(ss.norm.ppf(alpha)) / alpha)
            c99 = float(mu - sig * ss.norm.pdf(ss.norm.ppf(0.01)) / 0.01)
        elif method == 'cornish_fisher':
            mu, sig = p.mean(), p.std()
            sk, ku = float(ss.skew(p)), float(ss.kurtosis(p))
            def _cf(q):
                z = ss.norm.ppf(q)
                return float(mu + sig * (z + (z**2-1)*sk/6
                             + (z**3-3*z)*(ku)/24 - (2*z**3-5*z)*sk**2/36))
            v95, v99 = _cf(alpha), _cf(0.01)
            c95 = float(p[p <= v95].mean()) if (p <= v95).any() else v95
            c99 = float(p[p <= v99].mean()) if (p <= v99).any() else v99
        elif method == 'monte_carlo':
            sim = np.random.normal(p.mean(), p.std(), 10_000)
            v95 = float(np.quantile(sim, alpha))
            v99 = float(np.quantile(sim, 0.01))
            c95 = float(sim[sim <= v95].mean())
            c99 = float(sim[sim <= v99].mean())
        else:  # historical
            v95 = float(np.quantile(p, alpha))
            v99 = float(np.quantile(p, 0.01))
            c95 = float(p[p <= v95].mean()) if (p <= v95).any() else v95
            c99 = float(p[p <= v99].mean()) if (p <= v99).any() else v99
        return {'var_95': v95, 'cvar_95': c95, 'var_99': v99, 'cvar_99': c99, 'method': method}

    def stress_test(self, scenarios: Optional[dict] = None) -> pd.DataFrame:
        p = self._pr
        rows = []
        historical = {
            "COVID Crash (Feb–Mar 2020)":  ("2020-02-19", "2020-03-23"),
            "COVID Recovery (Q4 2020)":    ("2020-03-23", "2020-12-31"),
            "GFC 2008–2009":               ("2008-09-01", "2009-03-09"),
            "Taper Tantrum 2013":          ("2013-05-22", "2013-06-24"),
            "China Slowdown 2015":         ("2015-08-10", "2015-08-26"),
            "Rate Hike Cycle 2022":        ("2021-12-31", "2022-10-14"),
        }
        for name, (s, e) in historical.items():
            mask = (p.index >= s) & (p.index <= e)
            if mask.sum() > 2:
                rows.append({'Scenario': name, 'Type': 'Historical',
                             'Portfolio Return': float((1 + p[mask]).prod() - 1),
                             'Max Daily Loss': float(p[mask].min()),
                             'Days': int(mask.sum())})
        for name, shock in {
            "Equity Crash −30%":    -0.30,
            "Rate Shock +200bps":   -0.12,
            "Vol Spike (VIX +50%)": -0.08,
            "Deflation Shock":      -0.15,
        }.items():
            rows.append({'Scenario': name, 'Type': 'Parametric',
                         'Portfolio Return': float(shock),
                         'Max Daily Loss': float(shock), 'Days': 0})
        if scenarios:
            for name, shock in scenarios.items():
                rows.append({'Scenario': name, 'Type': 'Custom',
                             'Portfolio Return': float(shock),
                             'Max Daily Loss': float(shock), 'Days': 0})
        return pd.DataFrame(rows).set_index('Scenario') if rows else pd.DataFrame()

    def risk_contribution(self) -> pd.DataFrame:
        w   = self.weights
        cov = self.returns.cov().values * self.ann
        pv  = float(np.sqrt(max(w @ cov @ w, 1e-12)))
        mrc = cov @ w / pv
        crc = w * mrc
        return pd.DataFrame({
            'Weight': w, 'Marginal RC': mrc,
            'Component RC': crc, 'Risk %': crc / (pv + 1e-10) * 100,
        }, index=self.returns.columns)

    def tail_analysis(self) -> dict:
        p = self._pr.dropna()
        jb, jp = ss.jarque_bera(p)
        tq = ss.norm.ppf(np.linspace(0.01, 0.99, len(p)))
        eq = np.sort(p.values)
        return {'skewness': float(ss.skew(p)), 'kurtosis': float(ss.kurtosis(p)),
                'jb_stat': float(jb), 'jb_pvalue': float(jp), 'is_normal': jp > 0.05,
                'qq_theoretical': tq, 'qq_empirical': eq}

    def regime_detection(self, n_regimes: int = 2) -> dict:
        p = self._pr.dropna()
        w = min(21, len(p) // 4)
        rv = p.rolling(w).std() * np.sqrt(self.ann)
        rv = rv.dropna()
        thr = rv.median()
        regime = (rv > thr).astype(int)
        labels = {0: 'Low Vol (Bull)', 1: 'High Vol (Bear)'}
        stats = {}
        for r in range(n_regimes):
            mask = regime == r
            rr = p.reindex(mask.index)[mask]
            if len(rr) > 2:
                stats[labels[r]] = {
                    'n_obs': int(mask.sum()),
                    'ann_return': float(rr.mean() * self.ann),
                    'ann_vol': float(rr.std() * np.sqrt(self.ann)),
                    'sharpe': float((rr.mean() * self.ann - self.rf) /
                                    (rr.std() * np.sqrt(self.ann) + 1e-10)),
                    'max_dd': float(_max_drawdown(rr)),
                }
        return {'regime_series': regime, 'rolling_vol': rv,
                'stats': stats, 'threshold': float(thr), 'portfolio_returns': p}


# ─────────────────────────────────────────────────────────────────
# PortfolioBacktester
# ─────────────────────────────────────────────────────────────────

class PortfolioBacktester:
    """Walk-forward portfolio backtester with rebalancing."""

    _RMAP = {'daily': 1, 'weekly': 5, 'monthly': 21, 'quarterly': 63, 'yearly': 252}

    def __init__(self, prices: pd.DataFrame, risk_free_rate: float = 0.035,
                 frequency: str = 'daily'):
        self.prices    = prices.dropna()
        self.rf        = risk_free_rate
        self.frequency = frequency
        self.ann       = ANN_FACTOR.get(frequency, 252)

    def backtest(self, strategy: str, rebalance_freq: str = 'monthly',
                 lookback: int = 252, initial_capital: float = 100_000,
                 transaction_cost_bps: float = 10,
                 constraints: Optional[dict] = None,
                 cov_method: str = 'sample') -> dict:
        returns = np.log(self.prices / self.prices.shift(1)).dropna()
        n = len(self.prices.columns)
        step = self._RMAP.get(rebalance_freq, 21)
        tc_rate = transaction_cost_bps / 10_000

        n_obs = len(returns)
        vals = np.full(n_obs + 1, float(initial_capital))
        cur_w = np.ones(n) / n

        w_list, w_dates, to_list, tc_list = [], [], [], []

        for i, (date, row) in enumerate(returns.iterrows()):
            if i >= lookback and i % step == 0:
                hist = returns.iloc[max(0, i - lookback):i]
                try:
                    opt = PortfolioOptimizer(hist, self.rf, cov_method, self.frequency)
                    fn = getattr(opt, strategy, None)
                    new_w = fn(constraints)['weights'] if fn else cur_w.copy()
                    if np.isnan(new_w).any():
                        raise ValueError
                except Exception:
                    new_w = cur_w.copy()
                turnover = float(np.sum(np.abs(new_w - cur_w))) / 2
                tc_cost  = turnover * tc_rate
                vals[i] *= (1 - tc_cost)
                w_list.append(new_w.copy())
                w_dates.append(date)
                to_list.append(turnover)
                tc_list.append(tc_cost * vals[i])
                cur_w = new_w
            vals[i + 1] = vals[i] * (1 + float(row.values @ cur_w))

        ec = pd.Series(vals[1:], index=returns.index)
        rets = ec.pct_change().dropna()
        cagr = float((ec.iloc[-1] / initial_capital) ** (self.ann / max(len(rets), 1)) - 1)
        vol  = float(rets.std() * np.sqrt(self.ann))
        sr   = (cagr - self.rf) / (vol + 1e-10)
        mdd  = _max_drawdown(rets)
        v95  = float(np.quantile(rets, 0.05))
        c95  = float(rets[rets <= v95].mean()) if (rets <= v95).any() else v95
        mo   = ec.resample('ME').last().pct_change().dropna()
        wdf  = pd.DataFrame(w_list, index=w_dates, columns=self.prices.columns) \
               if w_list else pd.DataFrame()
        return {
            'equity_curve':      ec,
            'weights_history':   wdf,
            'turnover_history':  pd.Series(to_list, index=w_dates),
            'transaction_costs': pd.Series(tc_list, index=w_dates),
            'monthly_returns':   mo,
            'metrics': {
                'total_return': float(ec.iloc[-1] / initial_capital - 1),
                'cagr': cagr, 'volatility': vol, 'sharpe': sr,
                'sortino': _sortino(rets, self.rf, self.ann),
                'max_drawdown': mdd, 'calmar': cagr / abs(mdd) if abs(mdd) > 1e-10 else 0,
                'var_95': v95, 'cvar_95': c95,
                'avg_turnover': float(np.mean(to_list)) if to_list else 0,
                'total_tc': float(np.sum(tc_list)) if tc_list else 0,
                'best_month': float(mo.max()) if len(mo) else 0,
                'worst_month': float(mo.min()) if len(mo) else 0,
                'pct_pos_months': float((mo > 0).mean()) if len(mo) else 0,
                'skewness': float(ss.skew(rets)) if len(rets) > 3 else 0,
                'kurtosis': float(ss.kurtosis(rets)) if len(rets) > 3 else 0,
            },
        }

    def compare_strategies(self, strategies: List[str], **kwargs) -> pd.DataFrame:
        rows = []
        for s in strategies:
            try:
                r = self.backtest(s, **kwargs)
                m = dict(r['metrics']); m['strategy'] = s
                rows.append(m)
            except Exception as e:
                rows.append({'strategy': s, 'error': str(e)})
        return pd.DataFrame(rows).set_index('strategy') if rows else pd.DataFrame()

    def benchmark_comparison(self, benchmark_ticker: str, weights: np.ndarray,
                             rebalance_freq: str = 'monthly') -> dict:
        try:
            yrs = max(len(self.prices) // 252 + 1, 2)
            bm  = yf.Ticker(benchmark_ticker).history(period=f'{yrs}y', interval='1d',
                                                       auto_adjust=True)
            if bm.empty: return {}
            bm_r = bm['Close'].reindex(self.prices.index).ffill().pct_change().dropna()
        except Exception:
            return {}
        pr = pd.Series(np.log(self.prices / self.prices.shift(1)).dropna().values @ weights,
                       index=self.prices.index[1:])
        idx = pr.index.intersection(bm_r.index)
        pr, br = pr[idx], bm_r[idx]
        cov_m = np.cov(pr.values, br.values)
        beta  = float(cov_m[0, 1] / (cov_m[1, 1] + 1e-10))
        alpha = float(pr.mean() - beta * br.mean()) * self.ann
        te    = float((pr - br).std() * np.sqrt(self.ann))
        up    = pr[br > 0].mean() / br[br > 0].mean() if (br > 0).any() else 0
        dn    = pr[br < 0].mean() / br[br < 0].mean() if (br < 0).any() else 0
        return {'beta': beta, 'alpha': alpha, 'tracking_error': te,
                'information_ratio': alpha / te if te > 0 else 0,
                'up_capture': float(up), 'down_capture': float(dn),
                'active_return': float((pr - br).mean() * self.ann)}


# ─────────────────────────────────────────────────────────────────
# CACHED DATA FETCH
# ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_data(tickers_key: str, period: str, frequency: str):
    loader = MarketDataLoader()
    return loader.fetch(tickers_key.split('|'), period, frequency)


# ─────────────────────────────────────────────────────────────────
# CHART HELPERS
# ─────────────────────────────────────────────────────────────────

def _chart_layout(**kw) -> dict:
    d = dict(_BASE)
    d.update(kw)
    return d


def _corr_heatmap(corr: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Heatmap(
        z=corr.values, x=list(corr.columns), y=list(corr.index),
        colorscale='RdYlGn', zmid=0, zmin=-1, zmax=1,
        text=np.round(corr.values, 2), texttemplate='%{text}',
        colorbar=dict(title='ρ'),
    ))
    fig.update_layout(**_chart_layout(title='Correlation Matrix', height=400))
    return fig


def _weights_bar(weights: np.ndarray, tickers: List[str],
                 title: str = 'Optimal Weights') -> go.Figure:
    colors = [_ACC if w >= 0 else _RED for w in weights]
    fig = go.Figure(go.Bar(
        x=tickers, y=weights * 100,
        marker_color=colors, text=[f'{w:.1f}%' for w in weights * 100],
        textposition='outside',
    ))
    fig.update_layout(**_chart_layout(title=title, height=350,
                                      yaxis=dict(title='Weight (%)', gridcolor=_GRID),
                                      xaxis=dict(gridcolor=_GRID)))
    return fig


def _ef_chart(ef: pd.DataFrame, tangent: Optional[dict] = None,
              gmv: Optional[dict] = None, rf: float = 0.035,
              indiv_stats: Optional[pd.DataFrame] = None) -> go.Figure:
    fig = go.Figure()
    if not ef.empty:
        fig.add_trace(go.Scatter(
            x=ef['volatility'] * 100, y=ef['return'] * 100,
            mode='lines', line=dict(color=_ACC, width=2), name='Efficient Frontier',
        ))
        # CML
        if tangent:
            max_vol = ef['volatility'].max() * 100 * 1.5
            fig.add_trace(go.Scatter(
                x=[0, max_vol],
                y=[rf * 100, rf * 100 + tangent['sharpe'] * max_vol],
                mode='lines', line=dict(color=_BLUE, width=1, dash='dash'), name='CML',
            ))
    if tangent:
        fig.add_trace(go.Scatter(
            x=[tangent['volatility'] * 100], y=[tangent['expected_return'] * 100],
            mode='markers', marker=dict(color=_AMBER, size=14, symbol='star'),
            name='Tangent Portfolio',
        ))
    if gmv:
        fig.add_trace(go.Scatter(
            x=[gmv['volatility'] * 100], y=[gmv['expected_return'] * 100],
            mode='markers', marker=dict(color=_ACC, size=12, symbol='triangle-up'),
            name='Min Variance',
        ))
    if indiv_stats is not None and not indiv_stats.empty:
        fig.add_trace(go.Scatter(
            x=indiv_stats['Vol'] * 100, y=indiv_stats['CAGR'] * 100,
            mode='markers+text', text=indiv_stats.index,
            textposition='top center',
            marker=dict(color=_BLUE, size=8), name='Assets',
        ))
    fig.update_layout(**_chart_layout(
        title='Efficient Frontier', height=450,
        xaxis=dict(title='Volatility (%)', gridcolor=_GRID),
        yaxis=dict(title='Expected Return (%)', gridcolor=_GRID),
    ))
    return fig


def _equity_chart(curves: Dict[str, pd.Series]) -> go.Figure:
    palette = [_ACC, _BLUE, _AMBER, _RED, '#8B5CF6', '#EC4899', '#14B8A6']
    fig = go.Figure()
    for i, (name, ec) in enumerate(curves.items()):
        norm = ec / ec.iloc[0] * 100
        fig.add_trace(go.Scatter(
            x=norm.index, y=norm.values,
            mode='lines', name=name,
            line=dict(color=palette[i % len(palette)], width=2),
        ))
    fig.update_layout(**_chart_layout(
        title='Strategy Performance (rebased to 100)', height=420,
        xaxis=dict(gridcolor=_GRID),
        yaxis=dict(title='Value (rebased)', gridcolor=_GRID),
        legend=dict(bgcolor='rgba(0,0,0,0)'),
    ))
    return fig


def _monthly_heatmap(monthly_rets: pd.Series, title: str = 'Monthly Returns (%)') -> go.Figure:
    if monthly_rets.empty:
        return go.Figure()
    df = pd.DataFrame({
        'year': monthly_rets.index.year,
        'month': monthly_rets.index.month,
        'ret': monthly_rets.values * 100,
    })
    pivot = df.pivot_table(index='year', columns='month', values='ret', aggfunc='sum')
    mnames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    pivot.columns = [mnames[m - 1] for m in pivot.columns]
    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=list(pivot.columns), y=[str(y) for y in pivot.index],
        colorscale='RdYlGn', zmid=0,
        text=np.round(pivot.values, 1), texttemplate='%{text}%',
        colorbar=dict(title='Return %'),
    ))
    fig.update_layout(**_chart_layout(title=title, height=350))
    return fig


# ─────────────────────────────────────────────────────────────────
# SUB-TAB RENDERERS
# ─────────────────────────────────────────────────────────────────

_METHODS = {
    'Max Sharpe':          'max_sharpe',
    'Min Variance':        'min_variance',
    'Risk Parity':         'risk_parity',
    'HRP':                 'hierarchical_risk_parity',
    'Equal Weight':        'equal_weight',
    'Inverse Vol':         'inverse_vol',
    'Max Diversification': 'max_diversification',
    'CVaR Minimize':       'cvar_optimization',
}

_COV_METHODS = ['sample', 'ledoit_wolf', 'ewma', 'shrinkage']


def _subtab_setup(tab):
    with tab:
        st.markdown("### Portfolio Setup")
        c1, c2 = st.columns([2, 1])
        with c1:
            tickers_raw = st.text_input(
                "Tickers (comma-separated)",
                value="AAPL,MSFT,GOOGL,AMZN,GLD,TLT",
                key="_po_tkr_input",
                help="E.g.: AAPL, MSFT, LVMH.PA, ^GSPC, GLD, TLT",
            )
        with c2:
            frequency = st.selectbox("Frequency", ['daily', 'weekly', 'monthly'],
                                     key="_po_freq")

        cc1, cc2, cc3, cc4 = st.columns(4)
        with cc1:
            period_yr = st.slider("History (years)", 1, 10, 5, key="_po_period_yr")
        with cc2:
            rf_rate = st.number_input("Risk-Free Rate (%)", 0.0, 20.0, 3.5, 0.1,
                                      key="_po_rf") / 100
        with cc3:
            amount = st.number_input("Investment (€)", 10_000, 100_000_000,
                                     100_000, 10_000, key="_po_amount")
        with cc4:
            ret_method = st.selectbox("Return Type", ['log', 'arithmetic'],
                                      key="_po_ret_method")

        load = st.button("Load & Analyze", type="primary", key="_po_load_btn")

        if load:
            tickers = [t.strip().upper() for t in tickers_raw.split(',') if t.strip()]
            period_map = {1: '1y', 2: '2y', 3: '3y', 4: '4y', 5: '5y',
                          6: '6y', 7: '7y', 8: '8y', 9: '9y', 10: '10y'}
            period_str = period_map.get(period_yr, '5y')
            with st.spinner("Fetching market data…"):
                prices, valid = _fetch_data('|'.join(tickers), period_str, frequency)
            if prices.empty or len(valid) == 0:
                st.error("No valid data fetched. Check your tickers.")
                return
            loader = MarketDataLoader()
            returns = loader.compute_returns(prices, method=ret_method)
            stats   = loader.compute_stats(returns, rf_rate, frequency)
            st.session_state.update({
                '_po_prices': prices, '_po_returns': returns,
                '_po_stats': stats, '_po_valid': valid,
                '_po_freq': frequency, '_po_rf': rf_rate,
                '_po_amount': amount,
            })
            st.success(f"Loaded {len(valid)} assets, {len(prices)} periods.")

        if '_po_returns' not in st.session_state:
            st.info("Enter tickers and click **Load & Analyze** to begin.")
            return

        prices  = st.session_state['_po_prices']
        returns = st.session_state['_po_returns']
        stats   = st.session_state['_po_stats']
        valid   = st.session_state['_po_valid']

        st.markdown("---")
        st.markdown("#### Asset Statistics")
        fmt = {
            'CAGR': '{:.2%}', 'Vol': '{:.2%}', 'Sharpe': '{:.2f}',
            'Sortino': '{:.2f}', 'MaxDD': '{:.2%}', 'Calmar': '{:.2f}',
            'Skewness': '{:.2f}', 'Kurtosis': '{:.2f}',
        }
        st.dataframe(stats.style.format(fmt), width="stretch")

        st.markdown("#### Correlation Matrix")
        st.plotly_chart(_corr_heatmap(returns.corr()), width="stretch")

        st.markdown("#### Normalized Prices (base 100)")
        norm = prices / prices.iloc[0] * 100
        fig_norm = go.Figure()
        pal = [_ACC, _BLUE, _AMBER, _RED, '#8B5CF6', '#EC4899', '#14B8A6']
        for i, col in enumerate(norm.columns):
            fig_norm.add_trace(go.Scatter(
                x=norm.index, y=norm[col], mode='lines', name=col,
                line=dict(color=pal[i % len(pal)], width=1.5),
            ))
        fig_norm.update_layout(**_chart_layout(
            title='Normalized Prices', height=400,
            xaxis=dict(gridcolor=_GRID), yaxis=dict(gridcolor=_GRID),
            legend=dict(bgcolor='rgba(0,0,0,0)'),
        ))
        st.plotly_chart(fig_norm, width="stretch")

        st.markdown("#### Return Distributions")
        fig_dist = go.Figure()
        for i, col in enumerate(returns.columns):
            fig_dist.add_trace(go.Violin(
                y=returns[col], name=col,
                box_visible=True, meanline_visible=True,
                line_color=pal[i % len(pal)],
            ))
        fig_dist.update_layout(**_chart_layout(
            title='Return Distributions', height=400,
            yaxis=dict(title='Return', gridcolor=_GRID),
        ))
        st.plotly_chart(fig_dist, width="stretch")


def _subtab_optimize(tab):
    with tab:
        if '_po_returns' not in st.session_state:
            st.info("Load data first in **Setup & Data**.")
            return

        returns = st.session_state['_po_returns']
        valid   = st.session_state['_po_valid']
        rf      = st.session_state.get('_po_rf', 0.035)
        freq    = st.session_state.get('_po_freq', 'daily')
        amount  = st.session_state.get('_po_amount', 100_000)

        c1, c2 = st.columns(2)
        with c1:
            method_name = st.selectbox("Optimization Method", list(_METHODS.keys()),
                                       key="_po_method")
        with c2:
            cov_m = st.selectbox("Covariance Estimator", _COV_METHODS, key="_po_cov")

        with st.expander("Constraints"):
            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                long_only = st.checkbox("Long Only", True, key="_po_lo")
            with cc2:
                max_w = st.slider("Max Weight/Asset (%)", 5, 100, 40, 5,
                                  key="_po_maxw") / 100
            with cc3:
                min_w = st.slider("Min Weight/Asset (%)", 0, 20, 0, 1,
                                  key="_po_minw") / 100

        if st.button("Optimize", type="primary", key="_po_opt_btn"):
            cons = PortfolioOptimizer.build_constraints(
                len(valid), long_only=long_only, max_weight=max_w, min_weight=min_w
            )
            with st.spinner("Optimizing…"):
                try:
                    opt = PortfolioOptimizer(returns, rf, cov_m, freq)
                    fn  = getattr(opt, _METHODS[method_name])
                    res = fn(cons)
                    ef  = opt.efficient_frontier(n_points=60, constraints=cons)
                    gmv = opt.min_variance(cons)
                    ew  = opt.equal_weight()
                    rp  = opt.risk_parity()
                    st.session_state.update({
                        '_po_opt_result': res, '_po_ef': ef,
                        '_po_gmv': gmv, '_po_ew': ew, '_po_rp': rp,
                        '_po_opt_obj': opt,
                    })
                except Exception as e:
                    st.error(f"Optimization failed: {e}")

        if '_po_opt_result' not in st.session_state:
            return

        res   = st.session_state['_po_opt_result']
        ef    = st.session_state.get('_po_ef', pd.DataFrame())
        gmv   = st.session_state.get('_po_gmv')
        ew    = st.session_state.get('_po_ew')
        rp    = st.session_state.get('_po_rp')
        stats = st.session_state.get('_po_stats')

        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Expected Return", f"{res['expected_return']:.2%}")
        m2.metric("Volatility",      f"{res['volatility']:.2%}")
        m3.metric("Sharpe",          f"{res['sharpe']:.2f}")
        m4.metric("Sortino",         f"{res['sortino']:.2f}")
        m5.metric("Max Drawdown",    f"{res['max_drawdown']:.2%}")
        m6.metric("CVaR 95%",        f"{res['cvar_95']:.2%}")

        c_left, c_right = st.columns(2)
        with c_left:
            st.plotly_chart(_weights_bar(res['weights'], res['tickers']),
                            width="stretch")
        with c_right:
            fig_pie = go.Figure(go.Pie(
                labels=res['tickers'], values=res['weights'] * 100,
                hole=0.4, textinfo='label+percent',
                marker=dict(colors=[_ACC, _BLUE, _AMBER, _RED, '#8B5CF6',
                                    '#EC4899', '#14B8A6']),
            ))
            fig_pie.update_layout(**_chart_layout(title='Allocation', height=350))
            st.plotly_chart(fig_pie, width="stretch")

        st.plotly_chart(
            _ef_chart(ef, tangent=res, gmv=gmv, rf=rf, indiv_stats=stats),
            width="stretch",
        )

        st.markdown("#### Quick Comparison")
        compare_data = {
            'Method': [method_name, 'Equal Weight', 'Min Variance', 'Risk Parity'],
            'Return': [res['expected_return'], ew['expected_return'],
                       gmv['expected_return'], rp['expected_return']],
            'Vol': [res['volatility'], ew['volatility'], gmv['volatility'], rp['volatility']],
            'Sharpe': [res['sharpe'], ew['sharpe'], gmv['sharpe'], rp['sharpe']],
            'MaxDD': [res['max_drawdown'], ew['max_drawdown'], gmv['max_drawdown'], rp['max_drawdown']],
        }
        cdf = pd.DataFrame(compare_data).set_index('Method')
        st.dataframe(cdf.style.format(
            {'Return': '{:.2%}', 'Vol': '{:.2%}', 'Sharpe': '{:.2f}', 'MaxDD': '{:.2%}'}
        ), width="stretch")

        st.markdown("#### Weights Table")
        wdf = pd.DataFrame({
            'Ticker': res['tickers'],
            'Weight': [f"{w:.2%}" for w in res['weights']],
            'Value (€)': [f"€{w * amount:,.0f}" for w in res['weights']],
        })
        st.dataframe(wdf.set_index('Ticker'), width="stretch")


def _subtab_risk(tab):
    with tab:
        if '_po_opt_result' not in st.session_state:
            st.info("Run optimization first in **Optimize**.")
            return

        res     = st.session_state['_po_opt_result']
        returns = st.session_state['_po_returns']
        freq    = st.session_state.get('_po_freq', 'daily')
        rf      = st.session_state.get('_po_rf', 0.035)
        risk    = PortfolioRiskAnalyzer(returns, res['weights'], rf, freq)

        st.markdown("#### VaR / CVaR Comparison")
        var_rows = []
        for m in ['historical', 'parametric', 'cornish_fisher', 'monte_carlo']:
            try:
                v = risk.var_cvar(method=m)
                var_rows.append({
                    'Method': m.replace('_', ' ').title(),
                    'VaR 95%': v['var_95'], 'CVaR 95%': v['cvar_95'],
                    'VaR 99%': v['var_99'], 'CVaR 99%': v['cvar_99'],
                })
            except Exception:
                pass
        if var_rows:
            vdf = pd.DataFrame(var_rows).set_index('Method')
            st.dataframe(vdf.style.format('{:.3%}'), width="stretch")

        st.markdown("#### Drawdown Analysis")
        dd_res = risk.drawdown_analysis()
        d1, d2, d3 = st.columns(3)
        d1.metric("Max Drawdown", f"{dd_res['max_drawdown']:.2%}")
        if dd_res['peak_date']:
            d2.metric("Peak Date", str(dd_res['peak_date'])[:10])
        if dd_res['trough_date']:
            d3.metric("Trough Date", str(dd_res['trough_date'])[:10])
        dd_s = dd_res['drawdown_series']
        fig_dd = go.Figure(go.Scatter(
            x=dd_s.index, y=dd_s.values * 100,
            fill='tozeroy', mode='lines',
            line=dict(color=_RED, width=1),
            fillcolor=f'rgba(239,68,68,0.15)',
        ))
        fig_dd.update_layout(**_chart_layout(
            title='Underwater Chart', height=300,
            yaxis=dict(title='Drawdown (%)', gridcolor=_GRID),
            xaxis=dict(gridcolor=_GRID),
        ))
        st.plotly_chart(fig_dd, width="stretch")

        st.markdown("#### Risk Contribution")
        rc = risk.risk_contribution()
        fig_rc = go.Figure(go.Bar(
            x=list(rc.index), y=rc['Risk %'],
            marker_color=_ACC, text=rc['Risk %'].round(1),
            texttemplate='%{text:.1f}%', textposition='outside',
        ))
        fig_rc.update_layout(**_chart_layout(
            title='Component Risk Contribution (%)', height=350,
            yaxis=dict(title='Risk %', gridcolor=_GRID),
            xaxis=dict(gridcolor=_GRID),
        ))
        st.plotly_chart(fig_rc, width="stretch")
        st.dataframe(rc.style.format({
            'Weight': '{:.2%}', 'Marginal RC': '{:.4f}',
            'Component RC': '{:.4f}', 'Risk %': '{:.2f}',
        }), width="stretch")

        st.markdown("#### Stress Tests")
        st_res = risk.stress_test()
        if not st_res.empty:
            fig_st = go.Figure(go.Bar(
                x=st_res.index,
                y=st_res['Portfolio Return'] * 100,
                marker_color=[_RED if v < 0 else _ACC
                              for v in st_res['Portfolio Return']],
                text=[f"{v:.1%}" for v in st_res['Portfolio Return']],
                textposition='outside',
            ))
            fig_st.update_layout(**_chart_layout(
                title='Stress Test Results', height=400,
                yaxis=dict(title='Portfolio Return (%)', gridcolor=_GRID),
                xaxis=dict(tickangle=-30, gridcolor=_GRID),
            ))
            st.plotly_chart(fig_st, width="stretch")
            st.dataframe(st_res.style.format({
                'Portfolio Return': '{:.2%}', 'Max Daily Loss': '{:.2%}',
            }), width="stretch")

        c_left, c_right = st.columns(2)
        with c_left:
            st.markdown("#### Tail Analysis")
            ta = risk.tail_analysis()
            t1, t2 = st.columns(2)
            t1.metric("Skewness", f"{ta['skewness']:.3f}")
            t2.metric("Excess Kurtosis", f"{ta['kurtosis']:.3f}")
            st.caption(
                f"Jarque-Bera p-value: {ta['jb_pvalue']:.4f} — "
                f"{'Normal (PASS)' if ta['is_normal'] else 'Non-Normal (FAIL)'}"
            )
            fig_qq = go.Figure()
            fig_qq.add_trace(go.Scatter(
                x=ta['qq_theoretical'], y=ta['qq_empirical'],
                mode='markers', marker=dict(color=_ACC, size=3), name='QQ',
            ))
            x_rng = [ta['qq_theoretical'].min(), ta['qq_theoretical'].max()]
            fig_qq.add_trace(go.Scatter(
                x=x_rng, y=x_rng, mode='lines',
                line=dict(color=_RED, dash='dash'), name='Normal',
            ))
            fig_qq.update_layout(**_chart_layout(
                title='QQ-Plot vs Normal', height=300,
                xaxis=dict(title='Theoretical', gridcolor=_GRID),
                yaxis=dict(title='Empirical', gridcolor=_GRID),
            ))
            st.plotly_chart(fig_qq, width="stretch")

        with c_right:
            st.markdown("#### Regime Detection")
            reg = risk.regime_detection()
            for name, s in reg['stats'].items():
                with st.expander(name):
                    r1, r2, r3 = st.columns(3)
                    r1.metric("Ann. Return", f"{s['ann_return']:.2%}")
                    r2.metric("Ann. Vol", f"{s['ann_vol']:.2%}")
                    r3.metric("Sharpe", f"{s['sharpe']:.2f}")
            pr = reg['portfolio_returns']
            rs = reg['regime_series'].reindex(pr.index).fillna(0)
            fig_reg = go.Figure()
            fig_reg.add_trace(go.Scatter(
                x=pr.index, y=(1 + pr).cumprod() * 100,
                mode='lines', line=dict(color=_FONT, width=1), name='Portfolio',
            ))
            bull_mask = rs == 0
            fig_reg.add_trace(go.Scatter(
                x=pr.index[bull_mask], y=((1 + pr).cumprod() * 100)[bull_mask],
                mode='markers', marker=dict(color=_ACC, size=3), name='Low Vol',
            ))
            bear_mask = rs == 1
            fig_reg.add_trace(go.Scatter(
                x=pr.index[bear_mask], y=((1 + pr).cumprod() * 100)[bear_mask],
                mode='markers', marker=dict(color=_RED, size=3), name='High Vol',
            ))
            fig_reg.update_layout(**_chart_layout(
                title='Regime Classification', height=300,
                xaxis=dict(gridcolor=_GRID), yaxis=dict(gridcolor=_GRID),
                legend=dict(bgcolor='rgba(0,0,0,0)'),
            ))
            st.plotly_chart(fig_reg, width="stretch")


def _subtab_backtest(tab):
    with tab:
        if '_po_prices' not in st.session_state:
            st.info("Load data first in **Setup & Data**.")
            return

        prices = st.session_state['_po_prices']
        freq   = st.session_state.get('_po_freq', 'daily')
        rf     = st.session_state.get('_po_rf', 0.035)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            strats = st.multiselect(
                "Strategies", list(_METHODS.keys()),
                default=['Max Sharpe', 'Equal Weight', 'Risk Parity'],
                key="_po_bt_strats",
            )
        with c2:
            rb_freq = st.selectbox("Rebalance", ['monthly', 'quarterly', 'weekly', 'yearly'],
                                   key="_po_bt_rbfreq")
        with c3:
            tc_bps = st.number_input("Transaction Cost (bps)", 0, 100, 10, 1,
                                     key="_po_bt_tc")
        with c4:
            cap = st.number_input("Initial Capital (€)", 10_000, 10_000_000,
                                  100_000, 10_000, key="_po_bt_cap")

        c5, c6 = st.columns(2)
        with c5:
            lb = st.slider("Lookback (days)", 60, 756, 252, 21, key="_po_bt_lb")
        with c6:
            bm_ticker = st.text_input("Benchmark Ticker (optional)", "SPY",
                                      key="_po_bt_bm")

        if st.button("Run Backtest", type="primary", key="_po_bt_btn"):
            if not strats:
                st.warning("Select at least one strategy.")
                return
            bt = PortfolioBacktester(prices, rf, freq)
            results = {}
            with st.spinner("Backtesting…"):
                for s in strats:
                    try:
                        results[s] = bt.backtest(
                            _METHODS[s], rebalance_freq=rb_freq, lookback=lb,
                            initial_capital=float(cap), transaction_cost_bps=tc_bps,
                        )
                    except Exception as e:
                        st.warning(f"{s}: {e}")
            st.session_state['_po_bt_results'] = results
            st.session_state['_po_bt_bm_ticker'] = bm_ticker
            st.session_state['_po_bt_obj'] = bt

        if '_po_bt_results' not in st.session_state:
            return

        results = st.session_state['_po_bt_results']
        bt      = st.session_state.get('_po_bt_obj')

        # Equity curves
        curves = {s: r['equity_curve'] for s, r in results.items()}
        st.plotly_chart(_equity_chart(curves), width="stretch")

        # Metrics table
        st.markdown("#### Strategy Comparison")
        metric_rows = {}
        for s, r in results.items():
            m = r['metrics']
            metric_rows[s] = {
                'CAGR': m['cagr'], 'Vol': m['volatility'], 'Sharpe': m['sharpe'],
                'Sortino': m['sortino'], 'MaxDD': m['max_drawdown'],
                'Calmar': m['calmar'], 'VaR 95%': m['var_95'],
                'CVaR 95%': m['cvar_95'], 'Avg Turnover': m['avg_turnover'],
                'Best Month': m['best_month'], 'Worst Month': m['worst_month'],
                '% Pos Months': m['pct_pos_months'],
            }
        mdf = pd.DataFrame(metric_rows).T
        fmt_map = {c: '{:.2%}' for c in mdf.columns}
        fmt_map['Sharpe'] = '{:.2f}'; fmt_map['Sortino'] = '{:.2f}'
        fmt_map['Calmar'] = '{:.2f}'; fmt_map['Avg Turnover'] = '{:.2%}'
        st.dataframe(mdf.style.format(fmt_map), width="stretch")

        # Monthly return heatmap for first strategy
        first = next(iter(results.values()))
        st.plotly_chart(
            _monthly_heatmap(first['monthly_returns'], f"Monthly Returns — {next(iter(results))}"),
            width="stretch",
        )

        # Weights history
        if not first['weights_history'].empty:
            st.markdown("#### Weight Evolution")
            wh = first['weights_history']
            fig_wh = go.Figure()
            pal = [_ACC, _BLUE, _AMBER, _RED, '#8B5CF6', '#EC4899', '#14B8A6']
            for i, col in enumerate(wh.columns):
                fig_wh.add_trace(go.Scatter(
                    x=wh.index, y=wh[col] * 100,
                    mode='lines', name=col, stackgroup='one',
                    line=dict(width=0.5), fillcolor=pal[i % len(pal)],
                ))
            fig_wh.update_layout(**_chart_layout(
                title='Weight Evolution (stacked area)', height=350,
                yaxis=dict(title='Weight (%)', gridcolor=_GRID),
                xaxis=dict(gridcolor=_GRID),
                legend=dict(bgcolor='rgba(0,0,0,0)'),
            ))
            st.plotly_chart(fig_wh, width="stretch")

        # Benchmark comparison
        bm_t = st.session_state.get('_po_bt_bm_ticker', '')
        if bm_t and bt and '_po_opt_result' in st.session_state:
            w = st.session_state['_po_opt_result']['weights']
            with st.spinner(f"Comparing vs {bm_t}…"):
                bm_res = bt.benchmark_comparison(bm_t, w)
            if bm_res:
                st.markdown(f"#### Benchmark Comparison vs {bm_t}")
                b1, b2, b3, b4 = st.columns(4)
                b1.metric("Beta",             f"{bm_res['beta']:.2f}")
                b2.metric("Alpha (ann.)",      f"{bm_res['alpha']:.2%}")
                b3.metric("Tracking Error",   f"{bm_res['tracking_error']:.2%}")
                b4.metric("Info Ratio",        f"{bm_res['information_ratio']:.2f}")
                bb1, bb2 = st.columns(2)
                bb1.metric("Up Capture",   f"{bm_res['up_capture']:.2%}")
                bb2.metric("Down Capture", f"{bm_res['down_capture']:.2%}")


def _subtab_bl(tab):
    with tab:
        if '_po_returns' not in st.session_state:
            st.info("Load data first in **Setup & Data**.")
            return

        returns = st.session_state['_po_returns']
        valid   = st.session_state['_po_valid']
        rf      = st.session_state.get('_po_rf', 0.035)
        freq    = st.session_state.get('_po_freq', 'daily')

        st.markdown("""
        **Black-Litterman** incorporates your return views (absolute) into the optimization.
        Leave an asset at 0% to use the equilibrium return.
        """)

        tau = st.slider("τ (prior uncertainty)", 0.01, 0.20, 0.05, 0.01, key="_po_bl_tau")

        st.markdown("#### Your Return Views")
        views: Dict[str, float] = {}
        confidence: List[float] = []

        cols_per_row = 3
        rows = [valid[i:i+cols_per_row] for i in range(0, len(valid), cols_per_row)]
        for row in rows:
            cols = st.columns(cols_per_row)
            for j, tkr in enumerate(row):
                with cols[j]:
                    v = st.number_input(f"{tkr} view (%)", -50.0, 100.0, 0.0, 0.5,
                                        key=f"_po_bl_v_{tkr}") / 100
                    c = st.slider(f"Confidence", 0.0, 1.0, 0.5, 0.05,
                                  key=f"_po_bl_c_{tkr}")
                    if abs(v) > 1e-6:
                        views[tkr] = v
                        confidence.append(c)

        if st.button("Apply Black-Litterman", type="primary", key="_po_bl_btn"):
            if not views:
                st.warning("Enter at least one non-zero view.")
            else:
                with st.spinner("Computing Black-Litterman posterior…"):
                    try:
                        opt = PortfolioOptimizer(returns, rf, 'sample', freq)
                        bl  = opt.black_litterman(views, tau=tau, confidence=confidence)
                        st.session_state['_po_bl_result'] = bl
                    except Exception as e:
                        st.error(f"BL error: {e}")

        if '_po_bl_result' not in st.session_state:
            return

        bl = st.session_state['_po_bl_result']

        m1, m2, m3 = st.columns(3)
        m1.metric("BL Expected Return", f"{bl['expected_return']:.2%}")
        m2.metric("BL Volatility",      f"{bl['volatility']:.2%}")
        m3.metric("BL Sharpe",          f"{bl['sharpe']:.2f}")

        # Return comparison chart
        eq_mu = bl.get('equilibrium_mu', np.zeros(len(valid)))
        bl_mu = bl.get('bl_mu', np.zeros(len(valid)))
        pr_mu = bl.get('prior_mu', np.zeros(len(valid)))

        fig_mu = go.Figure()
        fig_mu.add_trace(go.Bar(
            name='Equilibrium', x=valid, y=eq_mu * 100, marker_color=_BLUE,
        ))
        fig_mu.add_trace(go.Bar(
            name='Historical', x=valid, y=pr_mu * 100, marker_color=_FONT,
        ))
        fig_mu.add_trace(go.Bar(
            name='BL Posterior', x=valid, y=bl_mu * 100, marker_color=_ACC,
        ))
        fig_mu.update_layout(**_chart_layout(
            title='Expected Returns: Equilibrium vs Historical vs BL Posterior',
            height=380, barmode='group',
            yaxis=dict(title='Annual Return (%)', gridcolor=_GRID),
            xaxis=dict(gridcolor=_GRID),
            legend=dict(bgcolor='rgba(0,0,0,0)'),
        ))
        st.plotly_chart(fig_mu, width="stretch")

        st.plotly_chart(_weights_bar(bl['weights'], bl['tickers'], 'BL Optimal Weights'),
                        width="stretch")


def _subtab_report(tab):
    with tab:
        if '_po_opt_result' not in st.session_state:
            st.info("Run optimization first in **Optimize**.")
            return

        res    = st.session_state['_po_opt_result']
        rf     = st.session_state.get('_po_rf', 0.035)
        amount = st.session_state.get('_po_amount', 100_000)
        freq   = st.session_state.get('_po_freq', 'daily')

        st.markdown("## Portfolio Report")
        st.markdown("---")

        st.markdown("### Executive Summary")
        e1, e2, e3, e4, e5, e6 = st.columns(6)
        e1.metric("Expected Return", f"{res['expected_return']:.2%}")
        e2.metric("Volatility",      f"{res['volatility']:.2%}")
        e3.metric("Sharpe Ratio",    f"{res['sharpe']:.2f}")
        e4.metric("Sortino Ratio",   f"{res['sortino']:.2f}")
        e5.metric("Max Drawdown",    f"{res['max_drawdown']:.2%}")
        e6.metric("CVaR 95%",        f"{res['cvar_95']:.2%}")

        st.markdown("### Recommended Allocation")
        alloc_df = pd.DataFrame({
            'Ticker': res['tickers'],
            'Weight': [f"{w:.2%}" for w in res['weights']],
            'Amount (€)': [f"€{w * amount:,.2f}" for w in res['weights']],
            'Shares Value': [f"€{w * amount:,.0f}" for w in res['weights']],
        }).set_index('Ticker')
        st.dataframe(alloc_df, width="stretch")

        # Key risks
        st.markdown("### Key Risks Identified")
        risks = []
        if res['max_drawdown'] < -0.20:
            risks.append(f"**Drawdown Risk**: Max drawdown of {res['max_drawdown']:.1%} -- "
                         "portfolio susceptible to large losses.")
        if res['cvar_95'] < -0.03:
            risks.append(f"**Tail Risk**: CVaR 95% = {res['cvar_95']:.2%} -- "
                         "expected loss in worst 5% of days exceeds 3%.")
        w_arr = np.array(res['weights'])
        if w_arr.max() > 0.40:
            top = res['tickers'][int(w_arr.argmax())]
            risks.append(f"**Concentration Risk**: {top} has weight {w_arr.max():.1%} -- "
                         "consider diversifying.")
        if not risks:
            risks = ["No major risk flags identified."]
        for r in risks[:3]:
            st.markdown(r)

        # Export
        st.markdown("### Export")
        csv_data = pd.DataFrame({
            'Ticker': res['tickers'],
            'Weight': res['weights'],
            'Amount_EUR': [w * amount for w in res['weights']],
        })
        csv_bytes = csv_data.to_csv(index=False).encode()
        st.download_button(
            "Download Allocation (CSV)", csv_bytes,
            file_name="portfolio_allocation.csv", mime="text/csv",
        )

        # Full metrics CSV
        metrics_csv = pd.DataFrame([{
            'expected_return': res['expected_return'],
            'volatility': res['volatility'],
            'sharpe': res['sharpe'],
            'sortino': res['sortino'],
            'max_drawdown': res['max_drawdown'],
            'cvar_95': res['cvar_95'],
            'risk_free_rate': rf,
            'investment_amount': amount,
        }]).to_csv(index=False).encode()
        st.download_button(
            "Download Metrics (CSV)", metrics_csv,
            file_name="portfolio_metrics.csv", mime="text/csv",
        )


# ─────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────

def render_portfolio_optimizer_tab():
    """Render the full Portfolio Optimization Lab tab."""
    st.markdown("## Portfolio Optimization Lab")
    st.markdown(
        "*Institutional-grade portfolio optimization: Max Sharpe, Risk Parity, HRP, "
        "Black-Litterman, CVaR — with full risk analytics and backtesting.*"
    )

    tabs = st.tabs([
        "Setup & Data",
        "Optimize",
        "Risk Deep Dive",
        "Backtest",
        "Views & BL",
        "Report",
    ])

    _subtab_setup(tabs[0])
    _subtab_optimize(tabs[1])
    _subtab_risk(tabs[2])
    _subtab_backtest(tabs[3])
    _subtab_bl(tabs[4])
    _subtab_report(tabs[5])
